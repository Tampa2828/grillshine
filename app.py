# app.py
import os, json, sqlite3, datetime as dt
from pathlib import Path
from flask import Flask, request, redirect, send_from_directory, jsonify, abort

# ---------- paths ----------
ROOT = Path(__file__).resolve().parent
STATIC_DIR = ROOT  # serve project root (index.html, assets/, etc.)
UPLOAD_DIR = ROOT / "static" / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
JSON_LOG = ROOT / "static" / "quotes.json"   # admin-quotes.html can fetch this

DB_PATH = ROOT / "quotes.db"

# ---------- app ----------
app = Flask(
    __name__,
    static_folder=str(STATIC_DIR),
    static_url_path=""  # so /assets/... and root files are served
)

ALLOWED_EXTS = {"png", "jpg", "jpeg", "webp", "gif", "heic", "heif"}
MAX_FILES = 8

def allowed(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[-1].lower() in ALLOWED_EXTS

# ---------- db ----------
def init_db():
    with sqlite3.connect(DB_PATH) as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS quotes (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              name TEXT,
              email TEXT,
              phone TEXT,
              details TEXT,
              files_json TEXT,
              created_at TEXT
            )
        """)
init_db()

def insert_quote(name, email, phone, details, files):
    with sqlite3.connect(DB_PATH) as con:
        con.execute(
            "INSERT INTO quotes (name, email, phone, details, files_json, created_at) VALUES (?,?,?,?,?,?)",
            (name, email, phone, details, json.dumps(files), dt.datetime.utcnow().isoformat())
        )

def read_quotes(limit=500):
    with sqlite3.connect(DB_PATH) as con:
        con.row_factory = sqlite3.Row
        rows = con.execute(
            "SELECT id, name, email, phone, details, files_json, created_at FROM quotes ORDER BY id DESC LIMIT ?",
            (limit,)
        ).fetchall()
    quotes = []
    for r in rows:
        files = []
        try:
            files = json.loads(r["files_json"]) if r["files_json"] else []
        except Exception:
            pass
        quotes.append({
            "id": r["id"],
            "name": r["name"],
            "email": r["email"],
            "phone": r["phone"],
            "details": r["details"],
            "files": files,
            "created_at": r["created_at"],
        })
    return quotes

# ---------- routes ----------
@app.route("/")
def root():
    # Let static serve index.html from project root
    return send_from_directory(STATIC_DIR, "index.html")

@app.post("/quote")
def quote():
    # fields
    name = (request.form.get("name") or "").strip()
    email = (request.form.get("email") or "").strip()
    phone = (request.form.get("phone") or "").strip()
    details = (request.form.get("details") or "").strip()

    # basic validation
    if not name or not email:
        # send them back to form; you could render a message instead
        return redirect("/index.html#quote")

    # store uploaded images
    saved_files = []
    files = request.files.getlist("images")
    if files:
        files = files[:MAX_FILES]
        date_folder = dt.datetime.utcnow().strftime("%Y-%m-%d")
        folder = UPLOAD_DIR / date_folder
        folder.mkdir(parents=True, exist_ok=True)

        for f in files:
            if not f or not f.filename:
                continue
            if not allowed(f.filename):
                continue
            ext = f.filename.rsplit(".", 1)[-1].lower()
            stamp = dt.datetime.utcnow().strftime("%Y%m%d-%H%M%S-%f")
            safe_name = f"{stamp}.{ext}"
            path = folder / safe_name
            f.save(path)
            # relative path so admin page can display
            rel = f"/static/uploads/{date_folder}/{safe_name}"
            saved_files.append(rel)

    # write to DB
    insert_quote(name, email, phone, details, saved_files)

    # also append to JSON log for admin-quotes.html
    try:
        JSON_LOG.parent.mkdir(parents=True, exist_ok=True)
        existing = []
        if JSON_LOG.exists():
            existing = json.loads(JSON_LOG.read_text(encoding="utf-8"))
        entry = {
            "id": int(dt.datetime.utcnow().timestamp()),
            "name": name, "email": email, "phone": phone,
            "details": details, "files": saved_files,
            "created_at": dt.datetime.utcnow().isoformat()
        }
        existing.insert(0, entry)  # newest first
        JSON_LOG.write_text(json.dumps(existing[:1000], indent=2), encoding="utf-8")
    except Exception as e:
        print("Failed to update quotes.json:", e)

    # TODO: hook up real emails here if desired
    # from email_utils import send_admin_email, send_customer_email
    # send_admin_email(entry)
    # send_customer_email(entry)

    # redirect to thank-you page
    return redirect("/thank-you.html")

@app.get("/admin/quotes.json")
def admin_quotes_json():
    # simple JSON view from SQLite (no auth for now; you can add a token check)
    return jsonify(read_quotes())

# Optional: clear JSON log (protect with env token)
@app.post("/admin/clear-json")
def clear_json():
    token = request.args.get("token", "")
    if token != os.environ.get("ADMIN_CLEAR_TOKEN", ""):
        return abort(403)
    JSON_LOG.write_text("[]", encoding="utf-8")
    return jsonify({"ok": True})

# Serve thank-you explicitly if needed
@app.get("/thank-you.html")
def thankyou():
    return send_from_directory(STATIC_DIR, "thank-you.html")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
