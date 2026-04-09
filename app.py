"""
BlockMedChain -- Flask REST API
================================
Connects the AHE-DHA encryption engine, off-chain storage, and on-chain
smart contracts into a unified backend.

Endpoints:
    POST   /register          Register a new patient
    POST   /upload            Encrypt record, store off-chain, write hash on-chain
    GET    /retrieve/<id>     Fetch hash from chain, verify, decrypt off-chain file
    POST   /grant-access      Patient grants provider access via smart contract
    POST   /revoke-access     Patient revokes provider access via smart contract
    GET    /audit/<id>        Full audit trail for a patient (on-chain events)

Start:
    python app.py
"""

import json
import hashlib
from pathlib import Path

from flask import Flask, request, jsonify, render_template
from web3 import Web3

from ahe_dha import (
    generate_rsa_keypair,
    serialize_public_key,
    serialize_private_key,
    load_public_key,
    load_private_key,
    sensitivity_score,
    check_access,
    access_sensitivity_weight,
    HashChain,
)
from offchain_storage import (
    store_record,
    retrieve_record,
    verify_integrity,
    list_patient_records,
    generate_record_id,
    STORAGE_ROOT,
)

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

app = Flask(__name__)

PROJECT_ROOT = Path(__file__).parent

# Ganache connection
GANACHE_URL = "http://127.0.0.1:7545"
w3 = Web3(Web3.HTTPProvider(GANACHE_URL))

# Global hash chain (in production this would be persisted)
hash_chain = HashChain()

# In-memory key store: patient_id -> { "private_key": RSAPrivateKey, "public_key": RSAPublicKey }
# In production, private keys would be held by the patient, not the server.
key_store: dict = {}

# Key files directory
KEYS_DIR = PROJECT_ROOT / "keys"
KEYS_DIR.mkdir(exist_ok=True)


# ---------------------------------------------------------------------------
# Contract loading helpers
# ---------------------------------------------------------------------------

def load_contract(name: str):
    """Load a deployed Truffle contract by name."""
    artifact_path = PROJECT_ROOT / "build" / "contracts" / f"{name}.json"
    with open(artifact_path) as f:
        artifact = json.load(f)

    abi = artifact["abi"]
    # Get the deployed address from the network map (Ganache network id)
    networks = artifact.get("networks", {})
    if not networks:
        raise RuntimeError(
            f"Contract {name} has not been deployed yet. "
            f"Run: npx truffle migrate --network development"
        )
    # Use the latest deployment
    network_id = list(networks.keys())[-1]
    address = networks[network_id]["address"]
    return w3.eth.contract(address=Web3.to_checksum_address(address), abi=abi)


def load_contracts():
    """Load all three contracts. Returns None for each if not yet deployed."""
    try:
        registry = load_contract("PatientRegistry")
        ehr_storage = load_contract("EHRStorage")
        access_ctrl = load_contract("AccessControl")
        return registry, ehr_storage, access_ctrl
    except RuntimeError as e:
        print(f"WARNING: {e}")
        return None, None, None


# Attempt to load contracts at startup (may fail if not yet deployed)
patient_registry, ehr_storage, access_control = load_contracts()


def require_contracts():
    """Ensure contracts are loaded; reload if needed."""
    global patient_registry, ehr_storage, access_control
    if patient_registry is None:
        patient_registry, ehr_storage, access_control = load_contracts()
    if patient_registry is None:
        raise RuntimeError("Contracts not deployed. Run: npx truffle migrate --network development")


def get_account(index: int = 0) -> str:
    """Get a Ganache account by index."""
    return w3.eth.accounts[index]


def patient_id_to_bytes32(patient_id: str) -> bytes:
    """Convert a string patient ID to bytes32 for the contract."""
    return Web3.solidity_keccak(["string"], [patient_id])


def record_id_to_bytes32(record_id: str) -> bytes:
    return Web3.solidity_keccak(["string"], [record_id])


def hash_to_bytes32(hex_hash: str) -> bytes:
    """Convert a hex SHA-256 hash string to bytes32."""
    return bytes.fromhex(hex_hash[:64])


# ---------------------------------------------------------------------------
# Helpers: key management
# ---------------------------------------------------------------------------

def get_or_create_keys(patient_id: str):
    """Get existing or generate new RSA key pair for a patient."""
    if patient_id in key_store:
        return key_store[patient_id]

    # Check on disk
    pub_path = KEYS_DIR / f"{patient_id}_pub.pem"
    priv_path = KEYS_DIR / f"{patient_id}_priv.pem"

    if pub_path.exists() and priv_path.exists():
        public_key = load_public_key(pub_path.read_bytes())
        private_key = load_private_key(priv_path.read_bytes())
    else:
        private_key, public_key = generate_rsa_keypair()
        pub_path.write_bytes(serialize_public_key(public_key))
        priv_path.write_bytes(serialize_private_key(private_key))

    key_store[patient_id] = {"private_key": private_key, "public_key": public_key}
    return key_store[patient_id]


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/register", methods=["POST"])
def register_patient():
    """Register a new patient.

    Body JSON:
        {
            "patient_id": "patient_001",
            "metadata": { ... optional demographic fields ... },
            "account_index": 0          // Ganache account index to use as wallet
        }
    """
    data = request.get_json()
    patient_id = data.get("patient_id")
    metadata = data.get("metadata", {})
    account_index = data.get("account_index", 0)

    if not patient_id:
        return jsonify({"error": "patient_id is required"}), 400

    require_contracts()

    # Generate RSA keys for this patient
    keys = get_or_create_keys(patient_id)

    # Prepare on-chain data
    pid_bytes32 = patient_id_to_bytes32(patient_id)
    metadata_hash = Web3.solidity_keccak(["string"], [json.dumps(metadata, sort_keys=True)])
    wallet = get_account(account_index)

    try:
        tx_hash = patient_registry.functions.registerPatient(
            pid_bytes32, metadata_hash
        ).transact({"from": wallet})
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    except Exception as e:
        return jsonify({"error": str(e)}), 400

    return jsonify({
        "status": "registered",
        "patient_id": patient_id,
        "wallet": wallet,
        "tx_hash": receipt.transactionHash.hex(),
        "gas_used": receipt.gasUsed,
        "public_key_pem": serialize_public_key(keys["public_key"]).decode(),
    }), 201


@app.route("/upload", methods=["POST"])
def upload_record():
    """Encrypt a record, store off-chain, write hash on-chain.

    Body JSON:
        {
            "patient_id": "patient_001",
            "record": { ... EHR fields ... },
            "provider_account_index": 1     // Ganache account index for the provider
        }
    """
    data = request.get_json()
    patient_id = data.get("patient_id")
    record = data.get("record")
    provider_index = data.get("provider_account_index", 1)

    if not patient_id or not record:
        return jsonify({"error": "patient_id and record are required"}), 400

    require_contracts()

    keys = get_or_create_keys(patient_id)

    # Compute sensitivity
    ss = sensitivity_score(record)

    # Store off-chain (encrypts via AHE-DHA internally)
    record_id, file_path, data_hash = store_record(
        record, patient_id, keys["public_key"], hash_chain
    )

    # Write hash on-chain
    rid_bytes32 = record_id_to_bytes32(record_id)
    pid_bytes32 = patient_id_to_bytes32(patient_id)
    hash_bytes32 = hash_to_bytes32(data_hash)
    provider_wallet = get_account(provider_index)

    try:
        tx_hash = ehr_storage.functions.uploadRecord(
            rid_bytes32, pid_bytes32, hash_bytes32, file_path
        ).transact({"from": provider_wallet})
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    except Exception as e:
        return jsonify({"error": str(e)}), 400

    return jsonify({
        "status": "uploaded",
        "record_id": record_id,
        "patient_id": patient_id,
        "file_path": file_path,
        "data_hash": data_hash,
        "sensitivity_score": ss,
        "tx_hash": receipt.transactionHash.hex(),
        "gas_used": receipt.gasUsed,
    }), 201


@app.route("/retrieve/<patient_id>/<record_id>", methods=["GET"])
def retrieve(patient_id, record_id):
    """Fetch hash from chain, verify integrity, decrypt off-chain file."""
    require_contracts()

    keys = get_or_create_keys(patient_id)

    # Get on-chain record
    rid_bytes32 = record_id_to_bytes32(record_id)
    on_chain = ehr_storage.functions.getRecord(rid_bytes32).call()
    # on_chain = (patientId, dataHash, storageRef, provider, timestamp, exists)

    if not on_chain[5]:  # exists
        return jsonify({"error": "Record not found on-chain"}), 404

    stored_hash = on_chain[1].hex()

    # Verify off-chain integrity against on-chain hash
    integrity_ok = verify_integrity(record_id, patient_id, stored_hash)

    # Decrypt
    try:
        decrypted, actual_hash = retrieve_record(
            record_id, patient_id, keys["private_key"]
        )
    except FileNotFoundError:
        return jsonify({"error": "Off-chain file not found"}), 404

    return jsonify({
        "status": "retrieved",
        "record_id": record_id,
        "patient_id": patient_id,
        "integrity_verified": integrity_ok,
        "on_chain_hash": stored_hash,
        "provider": on_chain[3],
        "timestamp": on_chain[4],
        "record": decrypted,
    })


@app.route("/grant-access", methods=["POST"])
def grant_access():
    """Patient grants a provider access to their records.

    Body JSON:
        {
            "patient_id": "patient_001",
            "patient_account_index": 0,
            "provider_address": "0x..."
        }
    """
    data = request.get_json()
    patient_id = data.get("patient_id")
    patient_index = data.get("patient_account_index", 0)
    provider_address = data.get("provider_address")

    if not patient_id or not provider_address:
        return jsonify({"error": "patient_id and provider_address are required"}), 400

    require_contracts()

    pid_bytes32 = patient_id_to_bytes32(patient_id)
    patient_wallet = get_account(patient_index)

    try:
        tx_hash = access_control.functions.grantAccess(
            pid_bytes32, Web3.to_checksum_address(provider_address)
        ).transact({"from": patient_wallet})
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    except Exception as e:
        return jsonify({"error": str(e)}), 400

    return jsonify({
        "status": "access_granted",
        "patient_id": patient_id,
        "provider": provider_address,
        "tx_hash": receipt.transactionHash.hex(),
        "gas_used": receipt.gasUsed,
    })


@app.route("/revoke-access", methods=["POST"])
def revoke_access():
    """Patient revokes a provider's access.

    Body JSON:
        {
            "patient_id": "patient_001",
            "patient_account_index": 0,
            "provider_address": "0x..."
        }
    """
    data = request.get_json()
    patient_id = data.get("patient_id")
    patient_index = data.get("patient_account_index", 0)
    provider_address = data.get("provider_address")

    if not patient_id or not provider_address:
        return jsonify({"error": "patient_id and provider_address are required"}), 400

    require_contracts()

    pid_bytes32 = patient_id_to_bytes32(patient_id)
    patient_wallet = get_account(patient_index)

    try:
        tx_hash = access_control.functions.revokeAccess(
            pid_bytes32, Web3.to_checksum_address(provider_address)
        ).transact({"from": patient_wallet})
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    except Exception as e:
        return jsonify({"error": str(e)}), 400

    return jsonify({
        "status": "access_revoked",
        "patient_id": patient_id,
        "provider": provider_address,
        "tx_hash": receipt.transactionHash.hex(),
        "gas_used": receipt.gasUsed,
    })


@app.route("/audit/<patient_id>", methods=["GET"])
def audit_trail(patient_id):
    """Return full audit trail for a patient from on-chain events."""
    require_contracts()

    pid_bytes32 = patient_id_to_bytes32(patient_id)
    trail = []

    # 1. Registration events
    reg_filter = patient_registry.events.PatientRegistered.create_filter(
        from_block=0, argument_filters={"patientId": pid_bytes32}
    )
    for event in reg_filter.get_all_entries():
        trail.append({
            "event": "PatientRegistered",
            "wallet": event.args.wallet,
            "metadataHash": event.args.metadataHash.hex(),
            "timestamp": event.args.timestamp,
            "block": event.blockNumber,
            "tx_hash": event.transactionHash.hex(),
        })

    # 2. Record upload events
    upload_filter = ehr_storage.events.RecordUploaded.create_filter(
        from_block=0, argument_filters={"patientId": pid_bytes32}
    )
    for event in upload_filter.get_all_entries():
        trail.append({
            "event": "RecordUploaded",
            "recordId": event.args.recordId.hex(),
            "provider": event.args.provider,
            "dataHash": event.args.dataHash.hex(),
            "storageRef": event.args.storageRef,
            "timestamp": event.args.timestamp,
            "block": event.blockNumber,
            "tx_hash": event.transactionHash.hex(),
        })

    # 3. Access granted events
    grant_filter = access_control.events.AccessGranted.create_filter(
        from_block=0, argument_filters={"patientId": pid_bytes32}
    )
    for event in grant_filter.get_all_entries():
        trail.append({
            "event": "AccessGranted",
            "provider": event.args.provider,
            "timestamp": event.args.timestamp,
            "block": event.blockNumber,
            "tx_hash": event.transactionHash.hex(),
        })

    # 4. Access revoked events
    revoke_filter = access_control.events.AccessRevoked.create_filter(
        from_block=0, argument_filters={"patientId": pid_bytes32}
    )
    for event in revoke_filter.get_all_entries():
        trail.append({
            "event": "AccessRevoked",
            "provider": event.args.provider,
            "timestamp": event.args.timestamp,
            "block": event.blockNumber,
            "tx_hash": event.transactionHash.hex(),
        })

    # Sort by block number, then by event order
    trail.sort(key=lambda e: (e["block"], e["timestamp"]))

    return jsonify({
        "patient_id": patient_id,
        "total_events": len(trail),
        "audit_trail": trail,
    })


# ---------------------------------------------------------------------------
# Health / status
# ---------------------------------------------------------------------------

@app.route("/", methods=["GET"])
def index():
    return render_template("patient.html")


@app.route("/patient", methods=["GET"])
def patient_view():
    return render_template("patient.html")


@app.route("/provider", methods=["GET"])
def provider_view():
    return render_template("provider.html")


@app.route("/audit", methods=["GET"])
def audit_view():
    return render_template("audit.html")


@app.route("/api/status", methods=["GET"])
def api_status():
    ganache_connected = w3.is_connected()
    contracts_loaded = patient_registry is not None
    return jsonify({
        "app": "BlockMedChain",
        "ganache_connected": ganache_connected,
        "contracts_deployed": contracts_loaded,
        "accounts": w3.eth.accounts[:5] if ganache_connected else [],
        "hash_chain_length": len(hash_chain.chain),
    })


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("\n=== BlockMedChain API ===")
    print(f"Ganache: {GANACHE_URL} (connected: {w3.is_connected()})")
    print(f"Contracts loaded: {patient_registry is not None}")
    print(f"Off-chain storage: {STORAGE_ROOT}")
    print()
    app.run(debug=True, port=5555)
