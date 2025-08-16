# app.py
import os, json, sqlite3, datetime, secrets, logging
from flask import Flask, request, send_from_directory, redirect, abort

# Writable defaults (Render always allows /tmp)
DB_PATH     = os.environ.get("DB_PATH", "/tmp/quotes.db")
UPLOAD_DIR  = os.environ.get("UPLOAD_DIR", "/tmp/uploads")

APP_DIR     = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__, static_folder=".", static_url_path="")
app.logger.setLevel(logging.INFO)

os.makedirs(UPLOAD_DIR, exist_ok=True)

# -------------------- DB helpers --------------------
def ensure_db():
    """Create DB and required columns; migrate legacy cols."""
    with sqlite3.connect(DB_PATH) as con:
        cur = con.cursor()
        cur.execute("""
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
        )
        """)
        # ensure columns exist (and migrate if needed)
        cur.execute("PRAGMA table_info(quotes)")
        cols = {row[1] for row in cur.fetchall()}
        if "files_json" not in cols:
            cur.execute("ALTER TABLE quotes ADD COLUMN files_json TEXT")
        if "file_paths" in cols and "files_json" in cols:
            # migrate any old data to files_json once
            cur.execute("UPDATE quotes SET files_json = COALESCE(files_json, file_paths)")
        con.commit()

def insert_quote(created_at, name, email, phone, details, files_json, ip, ua):
    ensure_db()
    with sqlite3.connect(DB_PATH) as con:
        con.execute("""
            INSERT INTO quotes
            (created_at, name, email, phone, details, files_json, ip, ua)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (created_at, name, email, phone, details, files_json, ip, ua))
        con.commit()

ensure_db()

# -------------------- Static passthrough --------------------
@app.get("/")
def root():
    return send_from_directory(".", "index.html")

@app.route("/<path:filename>")
def static_passthrough(filename):
    full = os.path.join(APP_DIR, filename)
    if os.path.isfile(full):
        return send_from_directory(".", filename)
    abort(404)

@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    return send_from_directory(UPLOAD_DIR, filename)

@app.get("/health")
def health():
    return {"ok": True}

# -------------------- /quote --------------------
@app.post("/quote")
def quote():
    try:
        name    = (request.form.get("name") or "").strip()
        email   = (request.form.get("email") or "").strip()
        phone   = (request.form.get("phone") or "").strip()
        details = (request.form.get("details") or "").strip()

        if not name or not email:
            return "Name and email are required.", 400

        # Save attachments from common field names
        saved = []
        for key in ("attachments", "images", "files"):
            for f in request.files.getlist(key):
                if not f or not f.filename:
                    continue
                ext   = os.path.splitext(f.filename)[1][:10]
                fname = f"{datetime.datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{secrets.token_hex(4)}{ext}"
                path  = os.path.join(UPLOAD_DIR, fname)
                f.save(path)
                saved.append({"filename": fname, "url": f"/uploads/{fname}"})

        created_at = datetime.datetime.utcnow().isoformat(timespec="seconds") + "Z"
        ip = request.headers.get("X-Forwarded-For", request.remote_addr)
        ua = (request.headers.get("User-Agent") or "")[:300]

        insert_quote(created_at, name, email, phone, details, json.dumps(saved), ip, ua)

        # 303: avoids resubmitting POST if user goes Back
        return redirect("/thank-you.html", code=303)

    except Exception:
        app.logger.exception("DB error when saving quote")
        return "Server error (db).", 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
