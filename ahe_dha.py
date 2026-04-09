"""
AHE-DHA (Adaptive Hybrid Encryption with Dynamic Hash Anchoring) Module
========================================================================
Core encryption engine for BlockMedChain.

Components:
1. Data Sensitivity Score (SS)
2. Session-Based Symmetric Keys (Ks) -- AES-256-GCM per transaction
3. RSA Asymmetric Wrapper -- encrypts session key with recipient's public RSA key
4. Time-Chained Hash Anchors (THA) -- SHA-256 chain with timestamps
5. Access Sensitivity Weights (alpha, beta, gamma)
"""

import os
import json
import time
import hashlib
from datetime import datetime, timezone
from typing import Tuple

from cryptography.hazmat.primitives.asymmetric import rsa, padding as asym_padding
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


# ---------------------------------------------------------------------------
# 1. Data Sensitivity Score (SS)
# ---------------------------------------------------------------------------

# Each field in the healthcare dataset is assigned a sensitivity weight.
# Higher weight = more sensitive data.
FIELD_SENSITIVITY = {
    "Name":               0.7,
    "Age":                0.3,
    "Gender":             0.2,
    "Blood Type":         0.5,
    "Medical Condition":  1.0,
    "Date of Admission":  0.4,
    "Doctor":             0.4,
    "Hospital":           0.3,
    "Insurance Provider": 0.6,
    "Billing Amount":     0.8,
    "Room Number":        0.2,
    "Admission Type":     0.5,
    "Discharge Date":     0.4,
    "Medication":         0.9,
    "Test Results":       1.0,
}


def sensitivity_score(record: dict) -> float:
    """Compute the Data Sensitivity Score (SS) for a single patient record.

    SS = sum(weight_i) / count(fields)   -- normalised to [0, 1]
    """
    total_weight = 0.0
    field_count = 0
    for field, value in record.items():
        if field in FIELD_SENSITIVITY and value not in (None, "", "NaN"):
            total_weight += FIELD_SENSITIVITY[field]
            field_count += 1
    if field_count == 0:
        return 0.0
    return round(total_weight / field_count, 4)


# ---------------------------------------------------------------------------
# 2. Session-Based Symmetric Key (Ks) -- AES-256-GCM
# ---------------------------------------------------------------------------

def generate_session_key() -> bytes:
    """Generate a random 256-bit AES key for this transaction."""
    return AESGCM.generate_key(bit_length=256)


def aes_encrypt(plaintext: bytes, key: bytes) -> Tuple[bytes, bytes]:
    """Encrypt *plaintext* with AES-256-GCM.

    Returns (nonce, ciphertext).  The nonce is 12 bytes (96 bits).
    """
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)
    ciphertext = aesgcm.encrypt(nonce, plaintext, None)
    return nonce, ciphertext


def aes_decrypt(nonce: bytes, ciphertext: bytes, key: bytes) -> bytes:
    """Decrypt AES-256-GCM ciphertext."""
    aesgcm = AESGCM(key)
    return aesgcm.decrypt(nonce, ciphertext, None)


# ---------------------------------------------------------------------------
# 3. RSA Asymmetric Wrapper
# ---------------------------------------------------------------------------

def generate_rsa_keypair() -> Tuple[rsa.RSAPrivateKey, rsa.RSAPublicKey]:
    """Generate a 2048-bit RSA key pair."""
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return private_key, private_key.public_key()


def rsa_encrypt_session_key(session_key: bytes, public_key: rsa.RSAPublicKey) -> bytes:
    """Encrypt the AES session key with the recipient's RSA public key."""
    return public_key.encrypt(
        session_key,
        asym_padding.OAEP(
            mgf=asym_padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None,
        ),
    )


def rsa_decrypt_session_key(encrypted_key: bytes, private_key: rsa.RSAPrivateKey) -> bytes:
    """Decrypt the AES session key with the holder's RSA private key."""
    return private_key.decrypt(
        encrypted_key,
        asym_padding.OAEP(
            mgf=asym_padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None,
        ),
    )


def serialize_public_key(public_key: rsa.RSAPublicKey) -> bytes:
    """Serialize an RSA public key to PEM format."""
    return public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )


def serialize_private_key(private_key: rsa.RSAPrivateKey, password: bytes | None = None) -> bytes:
    """Serialize an RSA private key to PEM format."""
    enc = serialization.BestAvailableEncryption(password) if password else serialization.NoEncryption()
    return private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=enc,
    )


def load_public_key(pem_data: bytes) -> rsa.RSAPublicKey:
    return serialization.load_pem_public_key(pem_data)


def load_private_key(pem_data: bytes, password: bytes | None = None) -> rsa.RSAPrivateKey:
    return serialization.load_pem_private_key(pem_data, password=password)


# ---------------------------------------------------------------------------
# 4. Time-Chained Hash Anchors (THA)
# ---------------------------------------------------------------------------

class HashChain:
    """Maintains an append-only chain of SHA-256 hashes linked by timestamps.

    Each anchor = SHA-256( previous_hash || timestamp || data_hash )
    """

    def __init__(self):
        # Genesis anchor
        self.chain: list[dict] = []
        genesis_hash = hashlib.sha256(b"GENESIS").hexdigest()
        self.chain.append({
            "index": 0,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data_hash": "0" * 64,
            "previous_hash": "0" * 64,
            "anchor_hash": genesis_hash,
        })

    @property
    def latest_hash(self) -> str:
        return self.chain[-1]["anchor_hash"]

    def add_anchor(self, data: bytes) -> dict:
        """Hash *data* and chain it to the previous anchor with a timestamp."""
        data_hash = hashlib.sha256(data).hexdigest()
        timestamp = datetime.now(timezone.utc).isoformat()
        previous_hash = self.latest_hash

        combined = f"{previous_hash}{timestamp}{data_hash}".encode()
        anchor_hash = hashlib.sha256(combined).hexdigest()

        anchor = {
            "index": len(self.chain),
            "timestamp": timestamp,
            "data_hash": data_hash,
            "previous_hash": previous_hash,
            "anchor_hash": anchor_hash,
        }
        self.chain.append(anchor)
        return anchor

    def verify_chain(self) -> bool:
        """Verify the integrity of the entire chain."""
        for i in range(1, len(self.chain)):
            prev = self.chain[i - 1]
            curr = self.chain[i]
            if curr["previous_hash"] != prev["anchor_hash"]:
                return False
            combined = f"{curr['previous_hash']}{curr['timestamp']}{curr['data_hash']}".encode()
            if hashlib.sha256(combined).hexdigest() != curr["anchor_hash"]:
                return False
        return True


# ---------------------------------------------------------------------------
# 5. Access Sensitivity Weights (alpha, beta, gamma)
# ---------------------------------------------------------------------------

# Role-based weight: how much trust the role receives
ROLE_WEIGHTS = {
    "patient":    1.0,   # full access to own data
    "doctor":     0.8,
    "nurse":      0.6,
    "researcher": 0.4,
    "admin":      0.3,
}

# Regulation multiplier (stricter regulation -> lower multiplier -> harder access)
REGULATION_WEIGHTS = {
    "HIPAA":  0.5,
    "GDPR":   0.4,
    "default": 0.7,
}


def access_sensitivity_weight(
    record: dict,
    role: str,
    regulation: str = "HIPAA",
) -> float:
    """Compute a composite access weight W.

    W = alpha * SS  +  beta * role_weight  +  gamma * regulation_weight

    where alpha + beta + gamma = 1.

    If W >= threshold (0.5), access is recommended; otherwise deny.
    """
    alpha = 0.4   # data sensitivity contribution
    beta = 0.35   # role trust contribution
    gamma = 0.25  # regulation strictness contribution

    ss = sensitivity_score(record)
    rw = ROLE_WEIGHTS.get(role, 0.2)
    reg = REGULATION_WEIGHTS.get(regulation, REGULATION_WEIGHTS["default"])

    # For SS: higher sensitivity should *lower* the access score (harder to access)
    # So we invert it: (1 - SS)
    w = alpha * (1 - ss) + beta * rw + gamma * reg

    return round(w, 4)


def check_access(record: dict, role: str, regulation: str = "HIPAA", threshold: float = 0.5) -> bool:
    """Return True if the role is allowed access under the given regulation."""
    return access_sensitivity_weight(record, role, regulation) >= threshold


# ---------------------------------------------------------------------------
# 6. Unified Encrypt / Decrypt Interface
# ---------------------------------------------------------------------------

def encrypt_record(
    record: dict,
    recipient_public_key: rsa.RSAPublicKey,
    hash_chain: HashChain,
) -> dict:
    """Full AHE-DHA encryption pipeline for a single patient record.

    1. Compute sensitivity score
    2. Generate a one-time AES-256 session key
    3. Encrypt the record JSON with AES-GCM
    4. Wrap the session key with the recipient's RSA public key
    5. Add a time-chained hash anchor for the ciphertext

    Returns a dict (the "envelope") containing everything needed to store
    and later decrypt the record.
    """
    ss = sensitivity_score(record)

    # Serialize record to JSON bytes
    plaintext = json.dumps(record, ensure_ascii=False).encode("utf-8")

    # AES encryption
    session_key = generate_session_key()
    nonce, ciphertext = aes_encrypt(plaintext, session_key)

    # RSA-wrap the session key
    encrypted_session_key = rsa_encrypt_session_key(session_key, recipient_public_key)

    # Hash anchor
    anchor = hash_chain.add_anchor(ciphertext)

    return {
        "sensitivity_score": ss,
        "nonce": nonce.hex(),
        "ciphertext": ciphertext.hex(),
        "encrypted_session_key": encrypted_session_key.hex(),
        "anchor": anchor,
    }


def decrypt_record(
    envelope: dict,
    recipient_private_key: rsa.RSAPrivateKey,
) -> dict:
    """Reverse the AHE-DHA pipeline and return the original record dict."""
    # Recover AES session key
    encrypted_session_key = bytes.fromhex(envelope["encrypted_session_key"])
    session_key = rsa_decrypt_session_key(encrypted_session_key, recipient_private_key)

    # Decrypt the record
    nonce = bytes.fromhex(envelope["nonce"])
    ciphertext = bytes.fromhex(envelope["ciphertext"])
    plaintext = aes_decrypt(nonce, ciphertext, session_key)

    return json.loads(plaintext)


# ---------------------------------------------------------------------------
# Quick self-test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Sample record from the Kaggle dataset
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

    print("=== AHE-DHA Self-Test ===\n")

    # Sensitivity score
    ss = sensitivity_score(sample)
    print(f"Sensitivity Score (SS): {ss}")

    # Access checks
    for role in ("patient", "doctor", "nurse", "researcher", "admin"):
        w = access_sensitivity_weight(sample, role)
        ok = check_access(sample, role)
        print(f"  Role={role:12s}  W={w:.4f}  Access={'GRANTED' if ok else 'DENIED'}")

    # Key generation
    private_key, public_key = generate_rsa_keypair()
    print(f"\nRSA key pair generated (2048-bit)")

    # Encrypt
    chain = HashChain()
    envelope = encrypt_record(sample, public_key, chain)
    print(f"Encrypted envelope keys: {list(envelope.keys())}")
    print(f"Hash chain length: {len(chain.chain)} (genesis + 1 record)")
    print(f"Anchor hash: {envelope['anchor']['anchor_hash'][:32]}...")

    # Decrypt
    recovered = decrypt_record(envelope, private_key)
    assert recovered == sample, "Decryption mismatch!"
    print(f"\nDecrypted record matches original: OK")

    # Chain integrity
    assert chain.verify_chain(), "Hash chain verification failed!"
    print(f"Hash chain integrity: VALID")

    # Timing
    import timeit
    n = 100
    t = timeit.timeit(lambda: encrypt_record(sample, public_key, chain), number=n)
    print(f"\nEncrypt x{n}: {t:.3f}s ({t/n*1000:.1f}ms per record)")
    t = timeit.timeit(lambda: decrypt_record(envelope, private_key), number=n)
    print(f"Decrypt x{n}: {t:.3f}s ({t/n*1000:.1f}ms per record)")

    print("\n=== All tests passed ===")
