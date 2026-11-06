"""
Database configuration and helper functions for DocuTrace.
Uses SQLite for robust local data storage with Firebase Cloud sync.
"""

import sqlite3
import os
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import cloud_db

DB_NAME = "docutrace.db"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, DB_NAME)


def get_db():
    """Get a database connection with dict-like row access."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initialize SQLite database tables if they do not exist."""
    conn = get_db()
    cursor = conn.cursor()

    # Users Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT DEFAULT 'user',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Documents Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            doc_id TEXT UNIQUE NOT NULL,
            title TEXT NOT NULL,
            description TEXT,
            category TEXT DEFAULT 'General',
            original_filename TEXT NOT NULL,
            stored_filename TEXT NOT NULL,
            file_size INTEGER NOT NULL,
            file_type TEXT,
            sha256_hash TEXT NOT NULL,
            qr_code_path TEXT NOT NULL,
            user_id INTEGER,
            status TEXT DEFAULT 'Active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)

    # Blockchain Blocks Table (Persistent Blockchain Storage)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS blockchain_blocks (
            block_index INTEGER PRIMARY KEY,
            timestamp TEXT NOT NULL,
            doc_id TEXT,
            doc_hash TEXT NOT NULL,
            title TEXT NOT NULL,
            uploader TEXT NOT NULL,
            previous_hash TEXT NOT NULL,
            nonce INTEGER NOT NULL,
            hash TEXT NOT NULL
        )
    """)

    # Verification Logs Table (Audit Trail)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS verification_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            doc_id TEXT,
            verified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            ip_address TEXT DEFAULT '127.0.0.1',
            method TEXT NOT NULL,
            result TEXT NOT NULL,
            input_hash TEXT
        )
    """)

    conn.commit()

    # Ensure default admin user is 'manoj' with password 'manoj9345'
    admin_pwd_hash = generate_password_hash("manoj9345")
    
    # Check if a user with username 'manoj' already exists in database
    cursor.execute("SELECT id FROM users WHERE username = 'manoj'")
    manoj_user = cursor.fetchone()

    if manoj_user:
        # Update existing user 'manoj' to admin and set password
        cursor.execute("""
            UPDATE users
            SET password_hash = ?, role = 'admin'
            WHERE id = ?
        """, (admin_pwd_hash, manoj_user[0]))
    else:
        # Check if there is an old 'admin' account to rename
        cursor.execute("SELECT id FROM users WHERE role = 'admin' OR username = 'admin' LIMIT 1")
        existing_admin = cursor.fetchone()
        if existing_admin:
            try:
                cursor.execute("""
                    UPDATE users
                    SET username = 'manoj', email = 'manoj@docutrace.org', password_hash = ?, role = 'admin'
                    WHERE id = ?
                """, (admin_pwd_hash, existing_admin[0]))
            except sqlite3.IntegrityError:
                pass
        else:
            try:
                cursor.execute("""
                    INSERT INTO users (username, email, password_hash, role)
                    VALUES ('manoj', 'manoj@docutrace.org', ?, 'admin')
                """, (admin_pwd_hash,))
            except sqlite3.IntegrityError:
                pass
    conn.commit()
    conn.close()

    # Synchronize admin account to Firebase Cloud Firestore if connected
    try:
        if cloud_db.is_cloud_connected()["connected"]:
            cloud_db.cloud_update_admin("manoj", admin_pwd_hash)
    except Exception:
        pass


# ---------------- USER HELPERS ---------------- #

def create_user(username, email, password, role="issuer"):
    """
    Register a new user with hashed password.
    Saves to Firebase Cloud Firestore when connected, and maintains local SQLite sync.
    """
    password_hash = generate_password_hash(password)

    # 1. Cloud Firestore write if connected
    cloud_status = cloud_db.is_cloud_connected()
    if cloud_status["connected"]:
        cloud_id, cloud_err = cloud_db.cloud_create_user(username, email, password_hash, role)
        if cloud_err:
            return None, cloud_err

    # 2. Local SQLite sync for relationships and offline resilience
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO users (username, email, password_hash, role)
            VALUES (?, ?, ?, ?)
        """, (username, email, password_hash, role))
        conn.commit()
        user_id = cursor.lastrowid
        return user_id, None
    except sqlite3.IntegrityError as e:
        if "username" in str(e):
            return None, "Username already exists."
        elif "email" in str(e):
            return None, "Email address already registered."
        return None, "Registration failed: User details already exist."
    finally:
        conn.close()


def authenticate_user(username_or_email, password):
    """
    Authenticate user by username or email.
    Checks Firebase Cloud Firestore first when online, with fallback to SQLite.
    """
    cloud_status = cloud_db.is_cloud_connected()

    # 1. Check Cloud Firestore if connected
    if cloud_status["connected"]:
        cloud_user = cloud_db.cloud_authenticate_user(username_or_email, password)
        if cloud_user:
            # Ensure local SQLite has mirror record for foreign keys
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM users WHERE username = ?", (cloud_user["username"],))
            row = cursor.fetchone()
            if not row:
                cursor.execute("""
                    INSERT INTO users (username, email, password_hash, role)
                    VALUES (?, ?, ?, ?)
                """, (cloud_user["username"], cloud_user["email"], generate_password_hash(password), cloud_user["role"]))
                conn.commit()
                local_id = cursor.lastrowid
            else:
                local_id = row[0]
            conn.close()

            cloud_user["id"] = local_id
            return cloud_user

    # 2. Local SQLite check (Default / Fallback)
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM users 
        WHERE username = ? OR email = ?
    """, (username_or_email, username_or_email))
    user = cursor.fetchone()
    conn.close()

    if user and check_password_hash(user["password_hash"], password):
        return dict(user)
    return None


def get_user_by_id(user_id):
    """Fetch user by ID."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, email, role, created_at FROM users WHERE id = ?", (user_id,))
    user = cursor.fetchone()
    conn.close()
    return dict(user) if user else None


def get_all_users():
    """Retrieve all users along with their count of issued documents."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT u.id, u.username, u.email, u.role, u.created_at,
               COUNT(d.id) as doc_count
        FROM users u
        LEFT JOIN documents d ON u.id = d.user_id
        GROUP BY u.id
        ORDER BY u.created_at DESC
    """)
    users = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return users


def update_user_role(user_id, new_role):
    """Update role of a user (admin only)."""
    if new_role not in ["admin", "issuer", "verifier", "user"]:
        return False
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET role = ? WHERE id = ?", (new_role, user_id))
    updated = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return updated


# ---------------- DOCUMENT HELPERS ---------------- #

def save_document(doc_id, title, description, category, original_filename, stored_filename, file_size, file_type, sha256_hash, qr_code_path, user_id):
    """Save document metadata to database."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO documents (
            doc_id, title, description, category,
            original_filename, stored_filename, file_size,
            file_type, sha256_hash, qr_code_path, user_id
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        doc_id, title, description, category,
        original_filename, stored_filename, file_size,
        file_type, sha256_hash, qr_code_path, user_id
    ))
    conn.commit()
    conn.close()


def get_document_by_id(doc_id):
    """Get document by unique tracking ID."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT d.*, u.username as uploader_username, u.email as uploader_email
        FROM documents d
        LEFT JOIN users u ON d.user_id = u.id
        WHERE d.doc_id = ?
    """, (doc_id,))
    doc = cursor.fetchone()
    conn.close()
    return dict(doc) if doc else None


def get_document_by_hash(sha256_hash):
    """Get document by exact SHA-256 hash."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT d.*, u.username as uploader_username
        FROM documents d
        LEFT JOIN users u ON d.user_id = u.id
        WHERE d.sha256_hash = ?
    """, (sha256_hash,))
    doc = cursor.fetchone()
    conn.close()
    return dict(doc) if doc else None


def get_user_documents(user_id):
    """Get all documents uploaded by a specific user."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM documents
        WHERE user_id = ?
        ORDER BY created_at DESC
    """, (user_id,))
    docs = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return docs


def get_all_documents():
    """Get all documents across the system with uploader info."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT d.*, u.username as uploader_username
        FROM documents d
        LEFT JOIN users u ON d.user_id = u.id
        ORDER BY d.created_at DESC
    """)
    docs = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return docs


def delete_document(doc_id, user_id=None, is_admin=False):
    """Delete a document record if authorized."""
    conn = get_db()
    cursor = conn.cursor()
    if is_admin:
        cursor.execute("DELETE FROM documents WHERE doc_id = ?", (doc_id,))
    else:
        cursor.execute("DELETE FROM documents WHERE doc_id = ? AND user_id = ?", (doc_id, user_id))
    deleted = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return deleted


# ---------------- BLOCKCHAIN PERSISTENCE HELPERS ---------------- #

def save_block_to_db(block_index, timestamp, doc_id, doc_hash, title, uploader, previous_hash, nonce, current_hash):
    """Persist a single block to the database."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO blockchain_blocks (
            block_index, timestamp, doc_id, doc_hash, title, uploader, previous_hash, nonce, hash
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (block_index, timestamp, doc_id, doc_hash, title, uploader, previous_hash, nonce, current_hash))
    conn.commit()
    conn.close()


def get_all_blocks_from_db():
    """Retrieve all blockchain blocks ordered by block index."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM blockchain_blocks ORDER BY block_index ASC")
    blocks = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return blocks


# ---------------- AUDIT & VERIFICATION LOGS ---------------- #

def log_verification(doc_id, method, result, input_hash=None, ip_address="127.0.0.1"):
    """Record an audit trail log for every verification attempt."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO verification_logs (doc_id, method, result, input_hash, ip_address)
        VALUES (?, ?, ?, ?, ?)
    """, (doc_id, method, result, input_hash, ip_address))
    conn.commit()
    conn.close()


def get_verification_logs(limit=25):
    """Retrieve recent verification attempts for the audit trail."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT v.*, d.title as doc_title
        FROM verification_logs v
        LEFT JOIN documents d ON v.doc_id = d.doc_id
        ORDER BY v.verified_at DESC
        LIMIT ?
    """, (limit,))
    logs = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return logs


def get_system_stats():
    """Retrieve high-level dashboard metrics."""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM documents")
    total_docs = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM blockchain_blocks")
    total_blocks = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM verification_logs WHERE result = 'VERIFIED'")
    verified_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM verification_logs WHERE result = 'TAMPERED'")
    tampered_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0]

    conn.close()

    return {
        "total_documents": total_docs,
        "total_blocks": total_blocks,
        "verified_verifications": verified_count,
        "tampered_verifications": tampered_count,
        "total_users": total_users
    }
