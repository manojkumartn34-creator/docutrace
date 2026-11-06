"""
DOCUTRACE – Document Verification & Authenticity Tracking System
Flask Application Entrypoint & Route Handlers
"""

import os
import hashlib
import uuid
import socket
from functools import wraps
from datetime import datetime
from flask import (
    Flask, render_template, request, redirect, url_for,
    flash, session, send_from_directory, jsonify
)
from werkzeug.utils import secure_filename
import qrcode

import database as db
import cloud_db
from blockchain import Blockchain

# ---------------- APPLICATION SETUP ---------------- #

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
QR_FOLDER = os.path.join(BASE_DIR, "static", "qrcodes")

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(QR_FOLDER, exist_ok=True)

app = Flask(__name__)
app.secret_key = os.environ.get("DOCUTRACE_SECRET", "docutrace-secure-secret-key-2026")
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["QR_FOLDER"] = QR_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 32 * 1024 * 1024  # 32 MB max file size

ALLOWED_EXTENSIONS = {"pdf", "png", "jpg", "jpeg", "docx", "txt", "csv", "xlsx"}

# Initialize SQLite database schema
db.init_db()

# Initialize Blockchain ledger
blockchain = Blockchain(difficulty=2)


# ---------------- UTILITY FUNCTIONS ---------------- #

def allowed_file(filename):
    """Check if file extension is allowed."""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def compute_file_sha256(file_path):
    """Compute SHA-256 hash of a file using buffered streaming chunks."""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            sha256_hash.update(chunk)
    return sha256_hash.hexdigest().lower()


def compute_stream_sha256(stream):
    """Compute SHA-256 hash directly from an in-memory or upload stream."""
    sha256_hash = hashlib.sha256()
    stream.seek(0)
    for chunk in iter(lambda: stream.read(65536), b""):
        sha256_hash.update(chunk)
    stream.seek(0)
    return sha256_hash.hexdigest().lower()


def get_lan_ip():
    """Detect the local Wi-Fi / Ethernet LAN IP of this computer."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def generate_qr_code(doc_id, host_url):
    """
    Generate a dynamic QR Code encoding the direct verification URL.
    Replaces 127.0.0.1/localhost with the machine's LAN IP so phones
    and other devices on the same Wi-Fi can scan and open it immediately.
    """
    lan_ip = get_lan_ip()
    reachable_url = host_url
    if "127.0.0.1" in reachable_url or "localhost" in reachable_url:
        reachable_url = reachable_url.replace("127.0.0.1", lan_ip).replace("localhost", lan_ip)

    verification_url = f"{reachable_url.rstrip('/')}/verify/{doc_id}"
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=4,
    )
    qr.add_data(verification_url)
    qr.make(fit=True)

    img = qr.make_image(fill_color="#1e293b", back_color="white")
    qr_filename = f"{doc_id}.png"
    qr_full_path = os.path.join(QR_FOLDER, qr_filename)
    img.save(qr_full_path)

    return f"qrcodes/{qr_filename}"


def login_required(f):
    """Decorator to require login for specific routes."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to access this page.", "warning")
            return redirect(url_for("login", next=request.url))
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    """Decorator to require administrator privileges."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to access this page.", "warning")
            return redirect(url_for("login", next=request.url))
        if session.get("role") != "admin":
            flash("Administrator privileges required to access this page.", "danger")
            return redirect(url_for("dashboard"))
        return f(*args, **kwargs)
    return decorated_function


# ---------------- CONTEXT PROCESSOR ---------------- #

@app.context_processor
def inject_global_vars():
    """Inject commonly used variables into all templates."""
    user = None
    if "user_id" in session:
        user = db.get_user_by_id(session["user_id"])
    stats = db.get_system_stats()
    cloud_status = cloud_db.is_cloud_connected()
    lan_ip = get_lan_ip()
    return dict(
        current_user=user,
        system_stats=stats,
        cloud_status=cloud_status,
        lan_ip=lan_ip,
        current_year=datetime.utcnow().year
    )


# ---------------- PUBLIC ROUTES ---------------- #

@app.route("/")
def index():
    """Home landing page with system overview and instant verify widget."""
    stats = db.get_system_stats()
    recent_verifications = db.get_verification_logs(limit=5)
    return render_template("index.html", stats=stats, recent_verifications=recent_verifications)


@app.route("/register", methods=["GET", "POST"])
def register():
    """User registration page."""
    if "user_id" in session:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        if not username or not email or not password:
            flash("All fields are required.", "danger")
            return render_template("register.html")

        if password != confirm_password:
            flash("Passwords do not match.", "danger")
            return render_template("register.html")

        if len(password) < 6:
            flash("Password must be at least 6 characters long.", "danger")
            return render_template("register.html")

        role = request.form.get("role", "issuer").strip().lower()
        if role not in ["issuer", "verifier"]:
            role = "issuer"

        user_id, error = db.create_user(username, email, password, role=role)
        if error:
            flash(error, "danger")
            return render_template("register.html")

        session["user_id"] = user_id
        session["username"] = username
        session["role"] = role
        flash(f"Registration successful as {role.capitalize()}! Welcome to DocuTrace.", "success")
        return redirect(url_for("dashboard"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    """User authentication page."""
    if "user_id" in session:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        identifier = request.form.get("identifier", "").strip()
        password = request.form.get("password", "")

        user = db.authenticate_user(identifier, password)
        if user:
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session["role"] = user["role"]
            flash(f"Welcome back, {user['username']}!", "success")
            next_url = request.args.get("next")
            return redirect(next_url or url_for("dashboard"))
        else:
            flash("Invalid username/email or password.", "danger")

    return render_template("login.html")


@app.route("/logout")
def logout():
    """Logs out the active user."""
    session.clear()
    flash("You have been securely logged out.", "info")
    return redirect(url_for("index"))


# ---------------- DASHBOARD & DOCUMENT MANAGEMENT ---------------- #

@app.route("/dashboard")
@login_required
def dashboard():
    """Main dashboard displaying user's documents and stats."""
    user_id = session["user_id"]
    is_admin = session.get("role") == "admin"

    if is_admin:
        documents = db.get_all_documents()
    else:
        documents = db.get_user_documents(user_id)

    stats = db.get_system_stats()
    return render_template("dashboard.html", documents=documents, stats=stats, is_admin=is_admin)


@app.route("/admin/users")
@admin_required
def admin_users():
    """Admin User Management – lists all registered users with their roles."""
    users = db.get_all_users()
    stats = db.get_system_stats()
    return render_template("admin_users.html", users=users, stats=stats)


@app.route("/admin/users/<int:user_id>/role", methods=["POST"])
@admin_required
def admin_change_role(user_id):
    """Admin action to update a user's role."""
    new_role = request.form.get("role", "").strip().lower()
    if new_role not in ["admin", "issuer", "verifier", "user"]:
        flash("Invalid role selected.", "danger")
        return redirect(url_for("admin_users"))

    success = db.update_user_role(user_id, new_role)
    if success:
        flash(f"User #{user_id} role updated to '{new_role}'.", "success")
    else:
        flash("Failed to update user role.", "danger")
    return redirect(url_for("admin_users"))


@app.route("/upload", methods=["GET", "POST"])
@login_required
def upload():
    """
    Upload a document, calculate its SHA-256 digital fingerprint,
    record it on the blockchain, and generate a dynamic QR code.
    """
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        category = request.form.get("category", "General")
        file = request.files.get("document")

        if not title:
            flash("Document title is required.", "danger")
            return render_template("upload.html")

        if not file or file.filename == "":
            flash("Please select a document file to upload.", "danger")
            return render_template("upload.html")

        if not allowed_file(file.filename):
            flash(f"Unsupported file format. Allowed: {', '.join(ALLOWED_EXTENSIONS)}", "danger")
            return render_template("upload.html")

        # 1. Generate unique Document Tracking ID
        year = datetime.utcnow().strftime("%Y")
        random_suffix = uuid.uuid4().hex[:6].upper()
        doc_id = f"DOC-{year}-{random_suffix}"

        # 2. Secure file saving
        original_filename = secure_filename(file.filename)
        extension = original_filename.rsplit(".", 1)[1].lower() if "." in original_filename else ""
        stored_filename = f"{doc_id}.{extension}"
        file_path = os.path.join(app.config["UPLOAD_FOLDER"], stored_filename)
        file.save(file_path)

        # 3. Calculate SHA-256 Hash
        file_size = os.path.getsize(file_path)
        sha256_hash = compute_file_sha256(file_path)

        # Check if identical document hash already exists in database
        existing_doc = db.get_document_by_hash(sha256_hash)
        if existing_doc:
            flash(f"Notice: A document with an identical cryptographic hash is already registered (ID: {existing_doc['doc_id']}). Registering as a new tracked version.", "warning")

        # 4. Generate dynamic QR code
        qr_code_rel_path = generate_qr_code(doc_id, request.host_url)

        # 5. Record on Blockchain (Proof of Work & Block Creation)
        uploader_name = session.get("username", "Unknown")
        mined_block = blockchain.add_document_block(
            doc_id=doc_id,
            doc_hash=sha256_hash,
            title=title,
            uploader=uploader_name
        )

        # 6. Save metadata to SQLite
        db.save_document(
            doc_id=doc_id,
            title=title,
            description=description,
            category=category,
            original_filename=original_filename,
            stored_filename=stored_filename,
            file_size=file_size,
            file_type=extension.upper(),
            sha256_hash=sha256_hash,
            qr_code_path=qr_code_rel_path,
            user_id=session["user_id"]
        )

        flash(f"Document successfully registered and mined onto Blockchain Block #{mined_block.index}!", "success")
        return redirect(url_for("document_detail", doc_id=doc_id))

    return render_template("upload.html")


@app.route("/document/<doc_id>")
@login_required
def document_detail(doc_id):
    """View details, cryptographic fingerprint, QR code, and blockchain proof for a document."""
    doc = db.get_document_by_id(doc_id)
    if not doc:
        flash("Document not found.", "danger")
        return redirect(url_for("dashboard"))

    # Fetch corresponding blockchain block
    block = blockchain.find_block_by_doc_id(doc_id)
    return render_template("document_detail.html", doc=doc, block=block)


@app.route("/download/<doc_id>")
@login_required
def download_file(doc_id):
    """Download the original uploaded document."""
    doc = db.get_document_by_id(doc_id)
    if not doc:
        flash("Document not found.", "danger")
        return redirect(url_for("dashboard"))

    return send_from_directory(
        app.config["UPLOAD_FOLDER"],
        doc["stored_filename"],
        as_attachment=True,
        download_name=doc["original_filename"]
    )


@app.route("/download-qr/<doc_id>")
def download_qr(doc_id):
    """Download the generated QR code image."""
    qr_filename = f"{doc_id}.png"
    return send_from_directory(
        app.config["QR_FOLDER"],
        qr_filename,
        as_attachment=True,
        download_name=f"QR_{doc_id}.png"
    )


@app.route("/delete/<doc_id>", methods=["POST"])
@login_required
def delete_doc(doc_id):
    """Delete a document record and uploaded file."""
    is_admin = session.get("role") == "admin"
    user_id = session["user_id"]

    doc = db.get_document_by_id(doc_id)
    if not doc:
        flash("Document not found.", "danger")
        return redirect(url_for("dashboard"))

    if not is_admin and doc["user_id"] != user_id:
        flash("Unauthorized to delete this document.", "danger")
        return redirect(url_for("dashboard"))

    # Remove physical file if exists
    try:
        file_path = os.path.join(app.config["UPLOAD_FOLDER"], doc["stored_filename"])
        if os.path.exists(file_path):
            os.remove(file_path)
    except Exception as e:
        app.logger.error(f"Error removing file: {e}")

    db.delete_document(doc_id, user_id=user_id, is_admin=is_admin)
    flash(f"Document {doc_id} was removed from the active database. (Note: Blockchain block remains permanently in the ledger for tamper-evident provenance).", "info")
    return redirect(url_for("dashboard"))


# ---------------- VERIFICATION ENGINE ---------------- #

@app.route("/verify", methods=["GET", "POST"])
def verify():
    """
    Public Document Verification Portal.
    Supports two verification methods:
    1. File Upload: Recomputes SHA-256 hash and compares against the blockchain.
    2. Document ID: Look up record by unique Tracking ID.
    """
    verification_result = None

    if request.method == "POST":
        method = request.form.get("verification_method")
        ip_addr = request.remote_addr or "127.0.0.1"

        if method == "file":
            uploaded_file = request.files.get("verify_file")
            if not uploaded_file or uploaded_file.filename == "":
                flash("Please choose a file to verify.", "danger")
                return render_template("verify.html", result=None)

            # Recompute SHA-256 hash
            computed_hash = compute_stream_sha256(uploaded_file)
            matched_block = blockchain.find_block_by_doc_hash(computed_hash)
            doc_record = db.get_document_by_hash(computed_hash)

            if matched_block:
                status = "VERIFIED"
                message = "AUTHENTIC DOCUMENT: The cryptographic SHA-256 hash matches the immutable blockchain record exactly. No tampering or alteration detected."
                db.log_verification(
                    doc_id=matched_block.doc_id,
                    method="FILE_UPLOAD",
                    result="VERIFIED",
                    input_hash=computed_hash,
                    ip_address=ip_addr
                )
                verification_result = {
                    "status": "VERIFIED",
                    "title": matched_block.title,
                    "doc_id": matched_block.doc_id,
                    "computed_hash": computed_hash,
                    "blockchain_hash": matched_block.doc_hash,
                    "block_index": matched_block.index,
                    "timestamp": matched_block.timestamp,
                    "uploader": matched_block.uploader,
                    "message": message,
                    "doc_record": doc_record
                }
            else:
                # Document hash not in blockchain -> Tampered or Unregistered
                # Check if user provided an optional doc_id or filename to verify against
                hint_doc_id = request.form.get("hint_doc_id", "").strip().upper()
                existing_doc_by_id = db.get_document_by_id(hint_doc_id) if hint_doc_id else None

                if existing_doc_by_id:
                    status = "TAMPERED"
                    message = f"TAMPERING DETECTED! This file claims to be '{hint_doc_id}', but its computed SHA-256 hash differs from the authentic blockchain record. The document has been modified, forged, or corrupted."
                    db.log_verification(
                        doc_id=hint_doc_id,
                        method="FILE_UPLOAD",
                        result="TAMPERED",
                        input_hash=computed_hash,
                        ip_address=ip_addr
                    )
                    verification_result = {
                        "status": "TAMPERED",
                        "doc_id": hint_doc_id,
                        "title": existing_doc_by_id["title"],
                        "computed_hash": computed_hash,
                        "blockchain_hash": existing_doc_by_id["sha256_hash"],
                        "message": message,
                        "doc_record": existing_doc_by_id
                    }
                else:
                    status = "NOT_FOUND"
                    message = "UNREGISTERED OR FORGED: This document's SHA-256 fingerprint was not found in the DocuTrace blockchain ledger. The file may be unauthenticated or counterfeit."
                    db.log_verification(
                        doc_id=None,
                        method="FILE_UPLOAD",
                        result="NOT_FOUND",
                        input_hash=computed_hash,
                        ip_address=ip_addr
                    )
                    verification_result = {
                        "status": "NOT_FOUND",
                        "computed_hash": computed_hash,
                        "message": message
                    }

        elif method == "id":
            search_id = request.form.get("doc_id", "").strip().upper()
            if not search_id:
                flash("Please enter a Document Tracking ID.", "danger")
                return render_template("verify.html", result=None)

            block = blockchain.find_block_by_doc_id(search_id)
            doc_record = db.get_document_by_id(search_id)

            if block:
                status = "VERIFIED"
                message = "AUTHENTIC RECORD FOUND: Document is registered on the DocuTrace blockchain."
                db.log_verification(
                    doc_id=search_id,
                    method="ID_LOOKUP",
                    result="VERIFIED",
                    input_hash=block.doc_hash,
                    ip_address=ip_addr
                )
                verification_result = {
                    "status": "VERIFIED",
                    "doc_id": block.doc_id,
                    "title": block.title,
                    "blockchain_hash": block.doc_hash,
                    "block_index": block.index,
                    "timestamp": block.timestamp,
                    "uploader": block.uploader,
                    "message": message,
                    "doc_record": doc_record
                }
            else:
                status = "NOT_FOUND"
                message = f"DOCUMENT NOT FOUND: No blockchain entry found for Tracking ID '{search_id}'."
                db.log_verification(
                    doc_id=search_id,
                    method="ID_LOOKUP",
                    result="NOT_FOUND",
                    input_hash=None,
                    ip_address=ip_addr
                )
                verification_result = {
                    "status": "NOT_FOUND",
                    "doc_id": search_id,
                    "message": message
                }

    return render_template("verify.html", result=verification_result)


@app.route("/verify/<doc_id>")
def verify_direct(doc_id):
    """
    Direct verification landing page (triggered when scanning the document's QR code).
    """
    search_id = doc_id.strip().upper()
    block = blockchain.find_block_by_doc_id(search_id)
    doc_record = db.get_document_by_id(search_id)
    ip_addr = request.remote_addr or "127.0.0.1"

    if block:
        status = "VERIFIED"
        message = "AUTHENTIC DOCUMENT: Verified via instant QR Code scan against the DocuTrace Blockchain."
        db.log_verification(
            doc_id=search_id,
            method="QR_SCAN",
            result="VERIFIED",
            input_hash=block.doc_hash,
            ip_address=ip_addr
        )
        result = {
            "status": "VERIFIED",
            "doc_id": block.doc_id,
            "title": block.title,
            "blockchain_hash": block.doc_hash,
            "block_index": block.index,
            "timestamp": block.timestamp,
            "uploader": block.uploader,
            "message": message,
            "doc_record": doc_record
        }
    else:
        status = "NOT_FOUND"
        message = f"DOCUMENT NOT FOUND: No blockchain record found for ID '{search_id}'."
        db.log_verification(
            doc_id=search_id,
            method="QR_SCAN",
            result="NOT_FOUND",
            input_hash=None,
            ip_address=ip_addr
        )
        result = {
            "status": "NOT_FOUND",
            "doc_id": search_id,
            "message": message
        }

    return render_template("verify.html", result=result, auto_verified=True)


# ---------------- BLOCKCHAIN EXPLORER ---------------- #

@app.route("/blockchain")
def blockchain_explorer():
    """Live interactive Blockchain Explorer."""
    chain_data = blockchain.get_chain_data()
    is_valid, message = blockchain.is_chain_valid()
    return render_template(
        "blockchain.html",
        chain=chain_data,
        is_valid=is_valid,
        validation_message=message
    )


@app.route("/api/validate-chain", methods=["GET"])
def api_validate_chain():
    """API endpoint to run a real-time cryptographic audit on the blockchain."""
    is_valid, message = blockchain.is_chain_valid()
    return jsonify({
        "is_valid": is_valid,
        "message": message,
        "chain_length": len(blockchain.chain),
        "difficulty": blockchain.difficulty
    })


# ---------------- API FOR PROGRAMMATIC VERIFICATION ---------------- #

@app.route("/api/verify-hash", methods=["POST"])
def api_verify_hash():
    """API endpoint for verifying document hash externally."""
    data = request.get_json(silent=True) or {}
    sha256_hash = data.get("hash", "").strip().lower()

    if not sha256_hash:
        return jsonify({"error": "Missing 'hash' parameter in JSON payload."}), 400

    block = blockchain.find_block_by_doc_hash(sha256_hash)
    if block:
        return jsonify({
            "verified": True,
            "status": "AUTHENTIC",
            "doc_id": block.doc_id,
            "title": block.title,
            "uploader": block.uploader,
            "block_index": block.index,
            "block_hash": block.hash,
            "timestamp": block.timestamp
        })
    else:
        return jsonify({
            "verified": False,
            "status": "UNREGISTERED_OR_TAMPERED",
            "message": "Hash does not match any authenticated blockchain record."
        }), 404


# ---------------- ERROR HANDLERS ---------------- #

@app.errorhandler(404)
def not_found_error(error):
    return render_template("index.html", error_message="The requested page does not exist."), 404


@app.errorhandler(413)
def request_entity_too_large(error):
    flash("File is too large. Maximum allowed size is 32MB.", "danger")
    return redirect(url_for("upload"))


if __name__ == "__main__":
    lan_ip = get_lan_ip()
    print("=" * 65)
    print("  DOCUTRACE – Document Verification & Authenticity Tracking")
    print("  [✓] Local Machine Access: http://localhost:5000")
    print(f"  [✓] Multi-Device / LAN:  http://{lan_ip}:5000")
    print("      (Open this address on phones or laptops on the same Wi-Fi)")
    print("=" * 65)
    app.run(host="0.0.0.0", port=5000, debug=True, threaded=True)
