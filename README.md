# BlockMedChain

A blockchain-based secure health records management system that combines **AHE-DHA encryption** (Adaptive Hybrid Encryption with Dynamic Hash Anchoring) with **Ethereum smart contracts** to give patients full control over their electronic health records.

---

## Problem

Traditional EHR systems store sensitive medical data in centralized databases controlled by hospitals and insurers. Patients have little visibility into who accesses their records, data breaches expose millions of records annually, and interoperability between providers remains poor.

## Solution

BlockMedChain decentralizes health record management by:

- **Encrypting** records off-chain using a multi-layered AHE-DHA scheme (AES-256-GCM + RSA-2048 + SHA-256 hash chains)
- **Anchoring** tamper-proof hashes on an Ethereum blockchain
- **Granting patients** direct control over who can access their data
- **Providing** a full audit trail of every access and modification event

---

## Architecture

```
Patient / Provider (Browser)
        |
   Flask REST API (port 5555)
        |
   +---------+-----------+
   |                     |
AHE-DHA Encryption   Web3.py
   |                     |
Off-chain Storage    Ethereum (Ganache)
(encrypted JSON)     Smart Contracts
```

### Core Components

| Component | Description |
|---|---|
| **AHE-DHA Encryption** (`ahe_dha.py`) | Adaptive hybrid encryption with sensitivity-based key sizing, AES-256-GCM session keys, RSA-2048 key wrapping, and time-chained SHA-256 hash anchors |
| **Smart Contracts** (`contracts/`) | Three Solidity contracts — PatientRegistry, EHRStorage, and AccessControl — deployed via Truffle |
| **Off-chain Storage** (`offchain_storage.py`) | Encrypted health records stored as JSON files; only the SHA-256 hash lives on-chain |
| **Flask API** (`app.py`) | REST endpoints for registration, upload, retrieval, access control, and audit |
| **Frontend Dashboard** (`templates/`, `static/`) | Multi-page Jinja2 app with patient, provider, and audit views |

---

## Features

### Patient Registration
Register patients on the blockchain with a wallet address. RSA key pairs are automatically generated for encryption/decryption.

### Encrypt and Upload Records
Health records are encrypted using AHE-DHA before being stored off-chain. The encryption adapts based on data sensitivity scoring (alpha=0.4, beta=0.35, gamma=0.25 weighting). A SHA-256 hash of the encrypted data is anchored on-chain for integrity verification.

### Retrieve and Decrypt Records
Providers with granted access can retrieve records. The system verifies the on-chain hash against the off-chain data before decrypting, ensuring tamper detection.

### Access Control
Patients grant or revoke access to specific providers directly through the smart contract. No intermediary or admin can override patient decisions.

### Audit Trail
Every registration, upload, access grant, and revocation is logged as an on-chain event. The audit view presents a complete, immutable timeline for any patient.

---

## AHE-DHA Encryption Details

**Adaptive Hybrid Encryption with Dynamic Hash Anchoring** is a multi-layered scheme:

1. **Sensitivity Scoring** — Each record is scored based on data type, content, and context to determine encryption parameters
2. **AES-256-GCM** — Symmetric session key encrypts the record payload (fast, authenticated encryption)
3. **RSA-2048 Key Wrapping** — The AES session key is encrypted with the patient's RSA public key (only the patient's private key can unwrap it)
4. **SHA-256 Hash Chains** — Each record's hash is chained to the previous, creating a time-ordered integrity chain that detects tampering or reordering
5. **Access Sensitivity Weights** — Access decisions factor in requester role, data sensitivity, and context using configurable weights

---

## Tech Stack

| Layer | Technology |
|---|---|
| Blockchain | Ethereum (Ganache local), Solidity 0.8.21 |
| Smart Contract Framework | Truffle |
| Backend | Python, Flask, Web3.py |
| Encryption | PyCryptodome (AES-256-GCM, RSA-2048, SHA-256) |
| Frontend | HTML/CSS/JS, Jinja2 templates |
| Fonts | Fraunces (headings), DM Sans (body), Azeret Mono (data) |

---

## Project Structure

```
BlockMedChain/
├── ahe_dha.py              # AHE-DHA encryption module
├── offchain_storage.py     # Off-chain encrypted file storage
├── app.py                  # Flask REST API
├── contracts/
│   ├── PatientRegistry.sol # Patient registration contract
│   ├── EHRStorage.sol      # EHR hash storage contract
│   └── AccessControl.sol   # Patient-controlled access contract
├── migrations/
│   └── 1_deploy_contracts.js
├── templates/
│   ├── base.html           # Shared layout with sidebar
│   ├── patient.html        # Registration, upload, access control
│   ├── provider.html       # Record retrieval and decryption
│   └── audit.html          # Audit trail timeline
├── static/
│   ├── style.css           # Full stylesheet with responsive design
│   └── app.js              # Frontend logic and API calls
├── truffle-config.js       # Truffle/Solidity config (EVM: london)
├── keys/                   # Generated RSA key pairs (per patient)
└── offchain_data/          # Encrypted record JSON files
```

---

## Prerequisites

- Python 3.9+
- Node.js 16+
- [Ganache](https://trufflesuite.com/ganache/) running on port 7545
- Truffle (`npm install -g truffle`)

## Setup

1. **Install Python dependencies**
   ```bash
   python -m venv venv
   source venv/Scripts/activate   # Windows
   pip install flask web3 pycryptodome
   ```

2. **Start Ganache** on port 7545 with default settings

3. **Deploy smart contracts**
   ```bash
   truffle migrate --reset
   ```

4. **Run the application**
   ```bash
   python app.py
   ```

5. **Open** `http://127.0.0.1:5555` in your browser

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/patient` | Patient dashboard |
| `GET` | `/provider` | Provider dashboard |
| `GET` | `/audit` | Audit trail viewer |
| `GET` | `/api/status` | Health check and blockchain connection status |
| `POST` | `/register` | Register a patient on-chain |
| `POST` | `/upload` | Encrypt and upload a health record |
| `GET` | `/retrieve/<patient_id>/<record_id>` | Retrieve and decrypt a record |
| `POST` | `/grant-access` | Grant a provider access to patient records |
| `POST` | `/revoke-access` | Revoke provider access |
| `GET` | `/audit/<patient_id>` | Get full audit trail for a patient |

---

## License

This project was built for academic and research purposes.
