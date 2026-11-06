"""
DOCUTRACE – Application Launcher and Initializer
Sets up database, verifies folders, seeds initial demonstration document,
and starts the Flask web server.
"""

import os
import sys
import shutil
import uuid
from datetime import datetime

# Check dependencies
try:
    import flask
    import werkzeug
    import qrcode
    from PIL import Image
except ImportError as e:
    print(f"\n[!] Missing dependency: {e.name}")
    print("Please install requirements using:")
    print("    pip install -r requirements.txt\n")
    sys.exit(1)

import database as db
from blockchain import Blockchain

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
QR_FOLDER = os.path.join(BASE_DIR, "static", "qrcodes")

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(QR_FOLDER, exist_ok=True)


def seed_demo_data():
    """Seeds an initial authentic document if system is freshly initialized."""
    conn = db.get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM documents")
    count = cursor.fetchone()[0]
    conn.close()

    if count == 0:
        print("[*] Seeding initial demonstration document into DocuTrace...")
        sample_path = os.path.join(BASE_DIR, "sample_documents", "Degree_Certificate_Original.txt")
        if os.path.exists(sample_path):
            doc_id = "DOC-2024-DEMO01"
            stored_filename = f"{doc_id}.txt"
            target_upload = os.path.join(UPLOAD_FOLDER, stored_filename)
            shutil.copyfile(sample_path, target_upload)

            # Compute hash
            import hashlib
            with open(target_upload, "rb") as f:
                sha256_hash = hashlib.sha256(f.read()).hexdigest().lower()

            # Generate QR Code
            verification_url = f"http://127.0.0.1:5000/verify/{doc_id}"
            qr = qrcode.QRCode(version=1, box_size=10, border=4)
            qr.add_data(verification_url)
            qr.make(fit=True)
            img = qr.make_image(fill_color="#1e293b", back_color="white")
            qr_filename = f"{doc_id}.png"
            img.save(os.path.join(QR_FOLDER, qr_filename))

            # Mine Block on Blockchain
            bc = Blockchain(difficulty=2)
            block = bc.add_document_block(
                doc_id=doc_id,
                doc_hash=sha256_hash,
                title="Bachelor Degree Certificate - Metropolitan University",
                uploader="admin"
            )

            # Save in SQLite
            db.save_document(
                doc_id=doc_id,
                title="Bachelor Degree Certificate - Metropolitan University",
                description="Official degree certificate issued to Manoj Kumar, B.Tech Computer Science & Engineering.",
                category="Academic",
                original_filename="Degree_Certificate_Original.txt",
                stored_filename=stored_filename,
                file_size=os.path.getsize(target_upload),
                file_type="TXT",
                sha256_hash=sha256_hash,
                qr_code_path=f"qrcodes/{qr_filename}",
                user_id=1
            )
            print(f"[✓] Demo Document seeded! Tracking ID: {doc_id} (Mined on Block #{block.index})")


def main():
    print("=" * 70)
    print("       DOCUTRACE – DOCUMENT VERIFICATION & AUTHENTICITY TRACKING")
    print("=" * 70)
    print(" [*] Initializing SQLite database schema...")
    db.init_db()

    print(" [*] Checking blockchain ledger state...")
    bc = Blockchain(difficulty=2)
    is_valid, msg = bc.is_chain_valid()
    print(f" [✓] Blockchain Status: {msg} (Current Height: {len(bc.chain)} blocks)")

    print(" [*] Checking cloud storage state...")
    import cloud_db
    cloud_status = cloud_db.is_cloud_connected()
    if cloud_status["connected"]:
        print(f" [✓] Cloud Storage: Connected to {cloud_status['provider']}")
    else:
        print(f" [ℹ] Cloud Storage: Local Mode ({cloud_status['message']})")

    seed_demo_data()

    from app import app, get_lan_ip
    lan_ip = get_lan_ip()

    print("\n [✓] Starting DocuTrace Flask Web Server (Multi-User & Multi-Device Enabled)...")
    print(f" [✓] Local Machine Access: http://localhost:5000")
    print(f" [✓] Mobile / Wi-Fi Access: http://{lan_ip}:5000")
    print(f"     (Open on any phone, tablet, or PC connected to the same Wi-Fi)")
    print(" [✓] Default Admin Account: manoj / manoj9345")
    print("=" * 70)

    app.run(host="0.0.0.0", port=5000, debug=True, threaded=True)


if __name__ == "__main__":
    main()
