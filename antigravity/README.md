# DOCUTRACE – Document Verification & Authenticity Tracking System

**DOCUTRACE** is a web-based document management, verification, and authenticity tracking platform designed to eliminate document forgery, unauthorized modifications, and fraudulent credentials.

The system uses **Python Flask** for the backend, **SQLite** for relational metadata and audit storage, **HTML5/CSS3/JavaScript** for the responsive user interface, cryptographic **SHA-256 hashing**, and an **immutable Python Blockchain ledger** paired with dynamic **QR codes**.

---

## 🌟 Main Key Features

1. **Secure User Login & Registration**
   - Protected user authentication with salted PBKDF2 password hashing.
   - Role-based separation: Document Issuers & System Administrators.
   - Session protection on document management routes.

2. **Digital Document Upload & SHA-256 Hashing**
   - Streaming hash calculation for files of any size (PDF, Word, PNG, JPG, CSV, etc.).
   - Generates unique Tracking IDs (`DOC-YYYY-XXXXXX`).
   - Generates unique cryptographic digital fingerprints.

3. **Blockchain-Based Verification Ledger**
   - Built-in, persistent cryptographic blockchain (`Block` and `Blockchain` engine).
   - Proof-of-Work (PoW) consensus mechanism with difficulty targeting.
   - Immutable block linkage (`previous_hash` chained to `current_hash`).
   - Live **Blockchain Explorer** with cryptographic chain audit verification.

4. **Dynamic QR Code Generation & Tamper Detection**
   - Generates high-resolution QR codes linking to the real-time verification portal.
   - Dual-mode verification:
     - **File Upload Verification**: Re-computes SHA-256 digest of any file and matches it against the blockchain ledger.
     - **Tracking ID / QR Scan**: Instant lookup of document authenticity and block provenance.
   - Flags files immediately as **AUTHENTIC (VERIFIED)**, **TAMPERED (MODIFIED)**, or **UNAUTHENTICATED (FORGED)**.

---

## 🏗️ Project Architecture & Directory Structure

```text
d:/antigravity/
├── app.py                      # Core Flask web application & API routing
├── blockchain.py               # Custom Blockchain ledger & Proof-of-Work implementation
├── database.py                 # SQLite database schema, queries, and helper functions
├── requirements.txt            # Python dependencies (Flask, qrcode, Pillow, etc.)
├── run.py                      # One-click startup script with automatic demo seeding
├── sample_documents/           # Test documents for instant tamper demonstration
│   ├── Degree_Certificate_Original.txt
│   ├── Degree_Certificate_Tampered.txt
│   └── Employment_Contract.txt
├── static/
│   ├── css/
│   │   └── style.css           # Modern dark-mode responsive glassmorphism UI
│   ├── js/
│   │   └── main.js             # Drag-and-drop file upload, live SHA-256 preview, audit
│   └── qrcodes/                # Auto-generated QR code image files
├── templates/
│   ├── base.html               # Main layout template with navigation & footer
│   ├── index.html              # Landing page with stats & quick verify
│   ├── login.html              # User login
│   ├── register.html           # User registration
│   ├── dashboard.html          # Document management portal
│   ├── upload.html             # Document upload & hash generation
│   ├── document_detail.html    # Full document profile & QR code preview
│   ├── verify.html             # Verification engine (File Upload + ID lookup)
│   └── blockchain.html         # Live Blockchain ledger explorer
└── uploads/                    # Secure storage directory for uploaded documents
```

---

## 🚀 Quick Start Guide

### 1. Install Dependencies
Open your command terminal (PowerShell or Command Prompt) and install the required Python packages:

```bash
pip install -r requirements.txt
```

### 2. Run the Application
Execute the one-click launcher:

```bash
python run.py
```
*(Alternatively, you can run `python app.py`)*

### 3. Open in Browser
Visit: **[http://127.0.0.1:5000](http://127.0.0.1:5000)**

---

## 🔑 Default Administrator Credentials
- **Username**: `manoj`
- **Password**: `manoj9345`
*(Or click "Create Free Account" to register any new account).*

---

## 🧪 Demonstration & Testing Guide

### Test 1: Verify an Authentic Document
1. Go to the **Verify Document** page (`/verify`).
2. Under the **Verify via File Upload** tab, upload `sample_documents/Degree_Certificate_Original.txt`.
3. Click **Calculate SHA-256 & Verify Against Blockchain**.
4. **Expected Result**: **AUTHENTIC DOCUMENT VERIFIED** (Green shield badge, matching blockchain hash, block height, and timestamp).

### Test 2: Detect a Tampered / Forged Document
1. Go to the **Verify Document** page (`/verify`).
2. Upload `sample_documents/Degree_Certificate_Tampered.txt`.
3. In the "Expected Document ID" field, enter `DOC-2024-DEMO01`.
4. Click **Calculate SHA-256 & Verify Against Blockchain**.
5. **Expected Result**: **TAMPERING DETECTED!** (Red alert badge showing the exact mismatch between the authentic blockchain hash and the modified file hash).

### Test 3: QR Code Verification
1. Log in and open any document in your **Dashboard**.
2. Click **Details** to view the document's generated dynamic QR code.
3. Click **Public Verification Page** or scan the QR code with your mobile phone camera.
4. **Expected Result**: Instantly loads the verified certificate record with cryptographic validation details.

### Test 4: Blockchain Explorer & Chain Audit
1. Navigate to **Blockchain Explorer** in the top navigation bar.
2. View the sequence of chained blocks with their `previous_hash` and mined `hash`.
3. Click the **Run Cryptographic Audit** button to verify the integrity of the chain link.

---

## 📡 REST API Endpoints

- **POST `/api/verify-hash`**: External verification endpoint
  ```json
  // Request
  { "hash": "d2c8...0f" }
  
  // Response (200 OK)
  {
    "verified": true,
    "status": "AUTHENTIC",
    "doc_id": "DOC-2024-DEMO01",
    "title": "Bachelor Degree Certificate",
    "block_index": 1,
    "timestamp": "2024-06-15 10:00:00 UTC"
  }
  ```
- **GET `/api/validate-chain`**: Returns cryptographic health and length of the blockchain ledger.
