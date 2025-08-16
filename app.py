# app.py
import os, json, sqlite3, datetime, secrets
from flask import Flask, request, send_from_directory, redirect, abort

APP_DIR    = os.path.dirname(os.path.abspath(__file__))
DB_PATH    = os.path.join(APP_DIR, os.environ.get("DB_PATH", "quotes.db"))
UPLOAD_DIR = os.path.join(APP_DIR, "uploads")

app = Flask(__name__, static_folder=".", static_url_path="")

os.makedirs(UPLOAD_DIR, exist_ok=True)

# --- DB helpers --------------------------------------------------------------
def ensure_db():
    """Create DB + table if missing (safe to call many times)."""
    with sqlite3.connect(DB_PATH) as con:
        con.execute("""
        CREATE TABLE IF NOT EXISTS quotes (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT,
            name       TEXT,
            email      TEXT,
            phone      TEXT,
            details    TEXT,
            files_json TEXT,
            ip         TEXT,
            ua         TEXT
        )""")
        con.commit()

def insert_quote(row):
    ensure_db()
    with sqlite3.connect(DB_PATH) as con:
        con.execute("""INSERT INTO quotes
            (created_at, name, email, phone, details, files_json, ip, ua)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)""", row)
        con.commit()

ensure_db()

# --- Static passthrough ------------------------------------------------------
@app.get("/")
def root():
    return send_from_directory(".", "index.html")

@app.route("/<path:filename>")
def static_passthrough(filename):
    # Serve any file that actually exists in the repo
    full = os.path.join(APP_DIR, filename)
    if os.path.isfile(full):
        return send_from_directory(".", filename)
    abort(404)

@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    return send_from_directory(UPLOAD_DIR, filename)

# --- Health (Render) ---------------------------------------------------------
@app.get("/health")
def health():
    return {"ok": True}

# --- Quote endpoint ----------------------------------------------------------
@app.post("/quote")
def quote():
    try:
        name    = (request.form.get("name") or "").strip()
        email   = (request.form.get("email") or "").strip()
        phone   = (request.form.get("phone") or "").strip()
        details = (request.form.get("details") or "").strip()

        if not name or not email:
            return "Name and email are required.", 400

        # Save any uploaded images (support several common field names)
        saved = []
        for key in ("attachments", "images", "files"):
            files = request.files.getlist(key)
            for f in files:
                if not f or not f.filename:
                    continue
                ext   = os.path.splitext(f.filename)[1].lower()[:10]
                fname = f"{datetime.datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{secrets.token_hex(4)}{ext}"
                path  = os.path.join(UPLOAD_DIR, fname)
                f.save(path)
                saved.append({"filename": fname, "url": f"/uploads/{fname}"})

        created_at = datetime.datetime.utcnow().isoformat(timespec="seconds") + "Z"
        ip = request.headers.get("X-Forwarded-For", request.remote_addr)
        ua = (request.headers.get("User-Agent") or "")[:300]

        insert_quote((
            created_at, name, email, phone, details, json.dumps(saved), ip, ua
        ))

        # Redirect to thank-you page (303 to avoid re-POST on back)
        return redirect("/thank-you.html", code=303)

    except Exception:
        app.logger.exception("Quote submit failed")
        return "Server error (db).", 500

if __name__ == "__main__":
    # Local dev
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
