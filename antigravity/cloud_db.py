"""
DOCUTRACE – Firebase Cloud Firestore Storage Module
Stores and authenticates user login details in Google Firebase Cloud Firestore.
Provides graceful local fallback when credentials are not yet configured.
"""

import os
from datetime import datetime
from werkzeug.security import check_password_hash

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FIREBASE_CONFIG_PATH = os.path.join(BASE_DIR, "firebase_config.json")

# Module state
_firestore_client = None
_cloud_connected = False
_cloud_error_message = ""

# Attempt Firebase Initialization
try:
    import firebase_admin
    from firebase_admin import credentials, firestore

    # Check if firebase_config.json exists
    if os.path.exists(FIREBASE_CONFIG_PATH):
        try:
            # Avoid re-initialization if already initialized
            if not firebase_admin._apps:
                cred = credentials.Certificate(FIREBASE_CONFIG_PATH)
                firebase_admin.initialize_app(cred)
            _firestore_client = firestore.client()
            _cloud_connected = True
            _cloud_error_message = "Connected to Firebase Cloud Firestore"
        except Exception as e:
            _cloud_connected = False
            _cloud_error_message = f"Firebase initialization error: {str(e)}"
    else:
        _cloud_connected = False
        _cloud_error_message = "firebase_config.json not found in project directory. Running in Local Mode."

except ImportError:
    _cloud_connected = False
    _cloud_error_message = "firebase-admin library not installed. Run 'pip install firebase-admin'."


def is_cloud_connected():
    """Returns the current connection status to Firebase Cloud Firestore."""
    return {
        "connected": _cloud_connected,
        "provider": "Firebase Cloud Firestore",
        "message": _cloud_error_message
    }


def cloud_create_user(username, email, password_hash, role="user"):
    """
    Registers a new user into Firebase Cloud Firestore 'users' collection.
    Returns: (doc_id, error_message)
    """
    if not _cloud_connected or _firestore_client is None:
        return None, "Cloud Firestore is not connected."

    try:
        users_ref = _firestore_client.collection("users")

        # Check if username already exists in Cloud Firestore
        username_query = users_ref.where("username", "==", username).limit(1).stream()
        if any(username_query):
            return None, "Username already exists in Cloud Firestore."

        # Check if email already exists in Cloud Firestore
        email_query = users_ref.where("email", "==", email.lower()).limit(1).stream()
        if any(email_query):
            return None, "Email address already registered in Cloud Firestore."

        # Create new user document in Cloud Firestore
        user_data = {
            "username": username,
            "email": email.lower(),
            "password_hash": password_hash,
            "role": role,
            "created_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        }
        timestamp, doc_ref = users_ref.add(user_data)
        return doc_ref.id, None

    except Exception as e:
        return None, f"Cloud Firestore write error: {str(e)}"


def cloud_authenticate_user(identifier, password):
    """
    Authenticates a user against Firebase Cloud Firestore by username or email.
    Returns: user dict with credentials if valid, else None.
    """
    if not _cloud_connected or _firestore_client is None:
        return None

    try:
        users_ref = _firestore_client.collection("users")

        # Search by username
        docs = list(users_ref.where("username", "==", identifier).limit(1).stream())

        # If not found, search by email
        if not docs:
            docs = list(users_ref.where("email", "==", identifier.lower()).limit(1).stream())

        if docs:
            user_doc = docs[0]
            user_data = user_doc.to_dict()
            stored_hash = user_data.get("password_hash", "")

            if check_password_hash(stored_hash, password):
                return {
                    "id": user_doc.id,
                    "username": user_data.get("username"),
                    "email": user_data.get("email"),
                    "role": user_data.get("role", "user"),
                    "created_at": user_data.get("created_at"),
                    "is_cloud_user": True
                }

        return None

    except Exception as e:
        print(f"[!] Cloud Firestore auth error: {e}")
        return None


def cloud_update_admin(username, password_hash):
    """
    Creates or updates the administrator credentials in Firebase Cloud Firestore.
    """
    if not _cloud_connected or _firestore_client is None:
        return False, "Cloud Firestore is not connected."

    try:
        users_ref = _firestore_client.collection("users")
        admin_docs = list(users_ref.where("role", "==", "admin").limit(1).stream())

        admin_data = {
            "username": username,
            "email": f"{username}@docutrace.org",
            "password_hash": password_hash,
            "role": "admin",
            "updated_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        }

        if admin_docs:
            admin_doc = admin_docs[0]
            users_ref.document(admin_doc.id).update(admin_data)
            return True, f"Admin updated in Cloud Firestore (Document ID: {admin_doc.id})"
        else:
            admin_data["created_at"] = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
            timestamp, doc_ref = users_ref.add(admin_data)
            return True, f"Admin created in Cloud Firestore (Document ID: {doc_ref.id})"

    except Exception as e:
        return False, f"Cloud Firestore admin update error: {str(e)}"
