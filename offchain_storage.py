"""
Off-chain Storage Module
========================
Handles writing and reading encrypted EHR envelopes to/from local storage.
Each encrypted record is stored as a JSON file. The file's SHA-256 hash
is returned so it can be anchored on-chain via EHRStorage.sol.

Directory layout:
    offchain_data/
        <patient_id>/
            <record_id>.json    # encrypted envelope from ahe_dha.encrypt_record()
"""

import os
import json
import hashlib
import uuid
from pathlib import Path
from typing import Tuple

from ahe_dha import encrypt_record, decrypt_record, HashChain
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicKey, RSAPrivateKey

# Default storage root (relative to project dir)
STORAGE_ROOT = Path(__file__).parent / "offchain_data"


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def generate_record_id() -> str:
    """Generate a unique record ID."""
    return uuid.uuid4().hex


def sha256_of_bytes(data: bytes) -> str:
    """Return the hex SHA-256 digest of raw bytes."""
    return hashlib.sha256(data).hexdigest()


# ---------------------------------------------------------------------------
# Store
# ---------------------------------------------------------------------------

def store_record(
    record: dict,
    patient_id: str,
    recipient_public_key: RSAPublicKey,
    hash_chain: HashChain,
    record_id: str | None = None,
    storage_root: Path = STORAGE_ROOT,
) -> Tuple[str, str, str]:
    """Encrypt a patient record and persist it off-chain.

    Steps:
        1. Encrypt the record with AHE-DHA (AES-256 + RSA + hash anchor)
        2. Serialize the envelope to JSON
        3. Write to  offchain_data/<patient_id>/<record_id>.json
        4. Compute SHA-256 of the stored file bytes

    Returns:
        (record_id, file_path, data_hash)
        - record_id:  unique identifier for this record
        - file_path:  relative path to the stored file (the "storage ref")
        - data_hash:  SHA-256 hex digest of the file contents (goes on-chain)
    """
    if record_id is None:
        record_id = generate_record_id()

    # 1. Encrypt
    envelope = encrypt_record(record, recipient_public_key, hash_chain)

    # 2. Serialize
    envelope_bytes = json.dumps(envelope, ensure_ascii=False, indent=2).encode("utf-8")

    # 3. Write to disk
    patient_dir = storage_root / patient_id
    _ensure_dir(patient_dir)
    file_path = patient_dir / f"{record_id}.json"
    file_path.write_bytes(envelope_bytes)

    # 4. Hash
    data_hash = sha256_of_bytes(envelope_bytes)

    # Return relative path as the storage reference
    rel_path = str(file_path.relative_to(storage_root.parent))

    return record_id, rel_path, data_hash


# ---------------------------------------------------------------------------
# Retrieve
# ---------------------------------------------------------------------------

def retrieve_record(
    record_id: str,
    patient_id: str,
    recipient_private_key: RSAPrivateKey,
    storage_root: Path = STORAGE_ROOT,
) -> Tuple[dict, str]:
    """Read an encrypted envelope from off-chain storage, verify, and decrypt.

    Returns:
        (decrypted_record, data_hash)
    """
    file_path = storage_root / patient_id / f"{record_id}.json"
    if not file_path.exists():
        raise FileNotFoundError(f"No off-chain record at {file_path}")

    envelope_bytes = file_path.read_bytes()
    data_hash = sha256_of_bytes(envelope_bytes)

    envelope = json.loads(envelope_bytes)
    decrypted = decrypt_record(envelope, recipient_private_key)

    return decrypted, data_hash


# ---------------------------------------------------------------------------
# Verify
# ---------------------------------------------------------------------------

def verify_integrity(
    record_id: str,
    patient_id: str,
    expected_hash: str,
    storage_root: Path = STORAGE_ROOT,
) -> bool:
    """Check that the file on disk still matches the hash stored on-chain."""
    file_path = storage_root / patient_id / f"{record_id}.json"
    if not file_path.exists():
        return False
    actual_hash = sha256_of_bytes(file_path.read_bytes())
    return actual_hash == expected_hash


# ---------------------------------------------------------------------------
# List
# ---------------------------------------------------------------------------

def list_patient_records(patient_id: str, storage_root: Path = STORAGE_ROOT) -> list[str]:
    """Return all record IDs stored for a patient."""
    patient_dir = storage_root / patient_id
    if not patient_dir.exists():
        return []
    return [f.stem for f in patient_dir.glob("*.json")]


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import shutil
    from ahe_dha import generate_rsa_keypair, HashChain

    print("=== Off-chain Storage Self-Test ===\n")

    # Setup
    test_root = Path(__file__).parent / "offchain_data_test"
    private_key, public_key = generate_rsa_keypair()
    chain = HashChain()
    patient_id = "patient_001"

    sample = {
        "Name": "Bobby Jackson",
        "Age": 30,
        "Gender": "Male",
        "Blood Type": "B-",
        "Medical Condition": "Cancer",
        "Date of Admission": "2024-01-31",
        "Doctor": "Matthew Smith",
        "Hospital": "Sons and Miller",
        "Insurance Provider": "Blue Cross",
        "Billing Amount": 18856.28,
        "Room Number": 328,
        "Admission Type": "Urgent",
        "Discharge Date": "2024-02-02",
        "Medication": "Paracetamol",
        "Test Results": "Normal",
    }

    # Store
    record_id, file_path, data_hash = store_record(
        sample, patient_id, public_key, chain, storage_root=test_root
    )
    print(f"Stored record:  {record_id}")
    print(f"File path:      {file_path}")
    print(f"Data hash:      {data_hash[:32]}...")

    # List
    records = list_patient_records(patient_id, storage_root=test_root)
    print(f"Patient records: {records}")

    # Verify integrity
    ok = verify_integrity(record_id, patient_id, data_hash, storage_root=test_root)
    print(f"Integrity check: {'PASS' if ok else 'FAIL'}")

    # Retrieve and decrypt
    decrypted, retrieved_hash = retrieve_record(
        record_id, patient_id, private_key, storage_root=test_root
    )
    assert decrypted == sample, "Decrypted record does not match original!"
    assert retrieved_hash == data_hash, "Hash mismatch on retrieval!"
    print(f"Decryption:      OK (matches original)")
    print(f"Hash on retrieve: matches stored hash")

    # Store a second record
    sample2 = {**sample, "Name": "Leslie Terry", "Medical Condition": "Obesity"}
    rid2, fp2, dh2 = store_record(
        sample2, patient_id, public_key, chain, storage_root=test_root
    )
    records = list_patient_records(patient_id, storage_root=test_root)
    print(f"\nStored 2nd record: {rid2}")
    print(f"Patient now has {len(records)} records")

    # Hash chain integrity
    assert chain.verify_chain(), "Hash chain broken!"
    print(f"Hash chain length: {len(chain.chain)} (genesis + {len(chain.chain)-1} records)")
    print(f"Hash chain integrity: VALID")

    # Cleanup test directory
    shutil.rmtree(test_root)
    print(f"\nCleaned up test directory")
    print("\n=== All tests passed ===")
