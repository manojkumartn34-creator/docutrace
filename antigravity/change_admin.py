"""
DOCUTRACE – Admin Credentials Management Tool
Allows you to update the administrator username and password easily.
"""

import sqlite3
import os
import sys
from werkzeug.security import generate_password_hash
import cloud_db

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "docutrace.db")


def update_admin():
    print("=" * 60)
    print("     DOCUTRACE – UPDATE ADMIN USERNAME & PASSWORD")
    print("=" * 60)

    if not os.path.exists(DB_PATH):
        print("[!] Database 'docutrace.db' not found.")
        print("    Please run 'python run.py' first to initialize the database.")
        sys.exit(1)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Find the current admin account
    cursor.execute("SELECT id, username, email FROM users WHERE role = 'admin' LIMIT 1")
    admin = cursor.fetchone()

    current_name = admin[1] if admin else "admin"
    print(f"Current Admin Username: {current_name}\n")

    new_username = input(f"Enter new username (Press Enter to keep '{current_name}'): ").strip()
    if not new_username:
        new_username = current_name

    new_password = input("Enter new password: ").strip()
    while not new_password or len(new_password) < 4:
        print("[!] Password must be at least 4 characters long.")
        new_password = input("Enter new password: ").strip()

    new_hash = generate_password_hash(new_password)

    if admin:
        cursor.execute("""
            UPDATE users
            SET username = ?, password_hash = ?
            WHERE id = ?
        """, (new_username, new_hash, admin[0]))
    else:
        cursor.execute("""
            INSERT INTO users (username, email, password_hash, role)
            VALUES (?, ?, ?, 'admin')
        """, (new_username, f"{new_username}@docutrace.org", new_hash))

    conn.commit()
    conn.close()

    # Sync with Firebase Cloud Firestore if connected
    cloud_status = cloud_db.is_cloud_connected()
    if cloud_status["connected"]:
        success, msg = cloud_db.cloud_update_admin(new_username, new_hash)
        print(f" [☁️] Cloud Sync: {msg}")
    else:
        print(f" [ℹ️] Cloud Status: {cloud_status['message']}")

    print("\n" + "=" * 60)
    print(" [✓] Admin credentials updated successfully!")
    print(f"     New Username: {new_username}")
    print(f"     New Password: {new_password}")
    print("=" * 60)
    print("You can now log in at http://127.0.0.1:5000/login with these credentials.\n")


if __name__ == "__main__":
    update_admin()
