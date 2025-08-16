# app.py
import os, sqlite3, logging, datetime
from pathlib import Path
from flask import Flask, request, redirect, send_from_directory, abort
from werkzeug.utils import secure_filename

# ---------- Paths & setup ----------
BASE_DIR   = Path(__file__).resolve().parent
DB_PATH    = BASE_DIR / "quotes.db"
UPLOAD_DIR = BASE_DIR / "uploads"         # use /tmp on Render if you prefer: Path("/tmp/uploads")

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("grillshine")

# ---------- Flask ----------
app = Flask(__name__, static_folder=str(BASE_DIR), static_url_path="")

# Serve index and any static asset from the repo root
@app.get("/")
def home():
    return send_from_directory(BASE_DIR, "index.html")

@app.get("/<path:filename>")
def static_files(filename):
    # allow serving /assets/*, subpages, thank-you.html, etc.
    full = BASE_DIR / filename
    if full.exists():
        return send_from_directory(BASE_DIR, filename)
    abort(404)

@app.get("/healthz")
def healthz():
    return "ok", 200

# ---------- DB ----------
def init_db():
    con = sqlite3.connect(DB_PATH)
    try:
        con.execute("""
            CREATE TABLE IF NOT EXISTS quotes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                name TEXT NOT NULL,
                email TEXT NOT NULL,
                phone TEXT,
                details TEXT,
                file_paths TEXT
            )
        """)
        con.commit()
    finally:
        con.close()

init_db()

def save_quote(name, email, phone, details, file_paths):
    con = sqlite3.connect(DB_PATH)
    try:
        con.execute(
            "INSERT INTO quotes (created_at, name, email, phone, details, file_paths) VALUES (?,?,?,?,?,?)",
            (datetime.datetime.utcnow().isoformat(timespec="seconds")+"Z",
             name, email, phone, details, ",".join(file_paths) if file_paths else "")
        )
        con.commit()
    finally:
        con.close()

# ---------- Email (optional – won’t crash if missing) ----------
def try_send_emails(payload, attachments):
    """
    Best-effort: if email_utils is present and configured, send.
    If not, just log a warning and continue (don’t 500 the request).
    """
    try:
        from email_utils import send_admin_email, send_customer_email  # your own module
    except Exception as e:
        log.warning("Email not sent (email_utils import/config issue): %s", e)
        return

    try:
        send_admin_email(payload, attachments=attachments)
    except Exception as e:
        log.warning("Failed sending admin email: %s", e)

    try:
        send_customer_email(payload)
    except Exception as e:
        log.warning("Failed sending customer confirmation: %s", e)

# ---------- Helpers ----------
ALLOWED_EXT = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".heic", ".heif"}
def allowed_ext(filename: str) -> bool:
    return Path(filename).suffix.lower() in ALLOWED_EXT

# ---------- Quote endpoint ----------
@app.post("/quote")
def quote():
    # Basic form fields
    name    = (request.form.get("name") or "").strip()
    email   = (request.form.get("email") or "").strip()
    phone   = (request.form.get("phone") or "").strip()
    details = (request.form.get("details") or "").strip()

    if not name or not email:
        log.info("Missing required fields: name=%r email=%r", name, email)
        return "Name and email are required.", 400

    # Save attachments (input name 'attachments' in your form)
    saved_paths = []
    try:
        files = request.files.getlist("attachments")
        for f in files or []:
            if not f or not f.filename:
                continue
            if not allowed_ext(f.filename):
                log.info("Skipping file with disallowed extension: %s", f.filename)
                continue
            safe_name = secure_filename(f.filename)
            # prefix timestamp to avoid collisions
            dest = UPLOAD_DIR / f"{int(datetime.datetime.utcnow().timestamp())}_{safe_name}"
            f.save(dest)
            saved_paths.append(str(dest.relative_to(BASE_DIR)))
    except Exception as e:
        # Don’t fail the request if file handling hiccups; just log it
        log.warning("File upload save failed: %s", e)

    # Store in DB (always works even if email fails)
    try:
        save_quote(name, email, phone, details, saved_paths)
    except Exception as e:
        log.error("DB error when saving quote: %s", e, exc_info=True)
        return "Server error (db).", 500

    # Fire-and-forget emails (log warning if not configured)
    payload = {"name": name, "email": email, "phone": phone, "details": details}
    try_send_emails(payload, attachments=[BASE_DIR / p for p in saved_paths])

    # Always redirect to thank-you page (static file in repo root)
    return redirect("/thank-you.html", code=303)


# For local dev: python app.py
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
