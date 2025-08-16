# app.py  — GrillShine minimal backend
import os, json, sqlite3, datetime, secrets, logging, csv, io
from flask import Flask, request, send_from_directory, redirect, abort, jsonify, Response

# -------------------------------------------------------------------
# Paths / env (Render: /tmp is always writable)
# -------------------------------------------------------------------
APP_DIR     = os.path.dirname(os.path.abspath(__file__))
DB_PATH     = os.environ.get("DB_PATH", "/tmp/quotes.db")
UPLOAD_DIR  = os.environ.get("UPLOAD_DIR", "/tmp/uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Serve files from project root at /
app = Flask(__name__, static_folder=".", static_url_path="")
app.logger.setLevel(logging.INFO)

# -------------------------------------------------------------------
# DB helpers
# -------------------------------------------------------------------
def ensure_db():
    """Create DB and required columns; migrate legacy cols if needed."""
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
        # legacy migration: file_paths -> files_json
        if "file_paths" in cols:
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

def fetch_quotes():
    ensure_db()
    with sqlite3.connect(DB_PATH) as con:
        con.row_factory = sqlite3.Row
        rows = con.execute("""
            SELECT id, created_at, name, email, phone, details, files_json, ip, ua
            FROM quotes
            ORDER BY id DESC
        """).fetchall()
    data = []
    for r in rows:
        d = dict(r)
        # parse attachments list
        try:
            d["files"] = json.loads(d.get("files_json") or "[]")
        except Exception:
            d["files"] = []
        data.append(d)
    return data

ensure_db()

# -------------------------------------------------------------------
# Static / pages
# -------------------------------------------------------------------
@app.get("/")
def root():
    return send_from_directory(".", "index.html")

# Explicit mappings for admin pages (so /admin works)
@app.get("/admin")
@app.get("/admin/")
def admin_html():
    return send_from_directory(".", "admin.html")

@app.get("/admin/quotes")
def admin_quotes_html():
    return send_from_directory(".", "admin-quotes.html")

# Serve any other file in the repo (assets, subpages, etc.)
@app.route("/<path:filename>")
def static_passthrough(filename):
    full = os.path.join(APP_DIR, filename)
    if os.path.isfile(full):
        return send_from_directory(".", filename)
    abort(404)

# Uploaded files (saved into /tmp/uploads)
@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    return send_from_directory(UPLOAD_DIR, filename)

@app.get("/health")
def health():
    return {"ok": True}

# -------------------------------------------------------------------
# API: quotes
# -------------------------------------------------------------------
@app.get("/api/quotes")
def api_quotes():
    """Return all quotes (newest first) as JSON for the admin UI."""
    return jsonify(fetch_quotes())

@app.get("/api/quotes.csv")
def api_quotes_csv():
    """Simple CSV export."""
    rows = fetch_quotes()
    fields = ["id", "created_at", "name", "email", "phone", "details", "ip", "ua", "files_json"]
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    for r in rows:
        writer.writerow(r)
    out = buf.getvalue()
    return Response(
        out,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=quotes.csv"}
    )

# -------------------------------------------------------------------
# POST /quote — saves form and uploads, then redirects to /thank-you.html
# -------------------------------------------------------------------
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
        ip = (request.headers.get("X-Forwarded-For") or request.remote_addr or "").split(",")[0].strip()
        ua = (request.headers.get("User-Agent") or "")[:300]

        insert_quote(created_at, name, email, phone, details, json.dumps(saved), ip, ua)

        # 303 avoids resubmitting POST if user navigates back
        return redirect("/thank-you.html", code=303)

    except Exception:
        app.logger.exception("DB error when saving quote")
        return "Server error (db).", 500

# -------------------------------------------------------------------
# Entrypoint
# -------------------------------------------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
