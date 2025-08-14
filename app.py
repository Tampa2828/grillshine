import os, csv, io
from datetime import datetime
from flask import Flask, request, redirect, url_for, session, send_file
from sqlalchemy import create_engine, text

# --- Config ---
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///quotes.db")
engine = create_engine(DATABASE_URL, future=True)

ADMIN_USER = os.getenv("ADMIN_USER", "admin")
ADMIN_PASS = os.getenv("ADMIN_PASS", "password123")
SECRET_KEY = os.getenv("SECRET_KEY", "devkey_change_me")

app = Flask(__name__, static_folder='.', static_url_path='')
app.secret_key = SECRET_KEY

# --- DB bootstrap (portable for SQLite/Postgres) ---
def init_db():
    backend = engine.url.get_backend_name()  # "sqlite", "postgresql", etc.
    if backend == "sqlite":
        ddl = """
        CREATE TABLE IF NOT EXISTS quotes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            phone TEXT,
            created_at TEXT NOT NULL
        )
        """
    else:
        ddl = """
        CREATE TABLE IF NOT EXISTS quotes (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            phone TEXT,
            created_at TIMESTAMP NOT NULL
        )
        """
    with engine.begin() as conn:
        conn.execute(text(ddl))

init_db()

# --- Public pages (serve your existing files) ---
@app.get("/")
def home():
    return app.send_static_file("index.html")

@app.get("/about")
def about():
    return app.send_static_file("about.html")

@app.get("/before-after")
def before_after():
    return app.send_static_file("before-after.html")

@app.get("/faq")
def faq():
    return app.send_static_file("faq.html")

@app.get("/thank-you")
def thank_you():
    return app.send_static_file("thank-you.html")

# --- Form handler ---
@app.post("/quote")
def quote():
    name  = (request.form.get("name") or "").strip()
    email = (request.form.get("email") or "").strip()
    phone = (request.form.get("phone") or "").strip()

    if not name or not email or "@" not in email:
        # if invalid, send back to the form with an error indicator (optional)
        return redirect(url_for("home") + "#quote?err=1")

    with engine.begin() as conn:
        conn.execute(
            text("INSERT INTO quotes (name, email, phone, created_at) VALUES (:n,:e,:p,:c)"),
            {
                "n": name,
                "e": email,
                "p": phone,
                "c": datetime.utcnow().isoformat(timespec="seconds")
            }
        )

    # Redirect to a real thank-you page
    return redirect(url_for("thank_you"))

# --- Admin auth (simple) ---
@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        if request.form.get("username") == ADMIN_USER and request.form.get("password") == ADMIN_PASS:
            session["admin"] = True
            return redirect(url_for("admin_dashboard"))
        return (
            '<p style="color:#ff8484;font-family:system-ui">Invalid credentials</p>' + LOGIN_FORM
        )
    return LOGIN_FORM

LOGIN_FORM = """
<!doctype html><meta charset="utf-8">
<title>Admin Login</title>
<style>
body{font-family:Inter,system-ui,sans-serif;background:#0f0f0f;color:#fff;
display:grid;place-items:center;height:100vh;margin:0}
.card{background:#1a1a1a;border:1px solid rgba(255,209,102,.25);padding:20px;border-radius:12px;min-width:320px}
label{display:block;margin:8px 0 4px}
input{width:100%;padding:10px;border-radius:8px;border:1px solid rgba(255,209,102,.25);background:#0e0e0e;color:#fff}
button{margin-top:12px;padding:10px 14px;border-radius:8px;border:1px solid #FFD166;background:#FFD166;color:#2a2000;font-weight:700;cursor:pointer}
a{color:#FFD166;text-decoration:none}
</style>
<div class="card">
  <h2 style="color:#FFD166;margin:0 0 8px">GrillShine — Admin</h2>
  <form method="POST">
    <label>Username</label><input name="username" autofocus>
    <label>Password</label><input name="password" type="password">
    <button type="submit">Login</button>
  </form>
</div>
"""

@app.get("/admin/logout")
def admin_logout():
    session.clear()
    return redirect(url_for("admin_login"))

@app.get("/admin")
@app.get("/admin/dashboard")
def admin_dashboard():
    if not session.get("admin"):
        return redirect(url_for("admin_login"))
    with engine.begin() as conn:
        rows = conn.execute(text(
            "SELECT id, name, email, phone, created_at FROM quotes ORDER BY id DESC"
        )).all()
    rows_html = ''.join(
        f"<tr><td>{r.id}</td><td>{r.name}</td><td>{r.email}</td><td>{r.phone or ''}</td><td>{r.created_at}</td>"
        f"<td><a href='{url_for('admin_delete', qid=r.id)}' onclick='return confirm(\"Delete?\")'>Delete</a></td></tr>"
        for r in rows
    )
    return f"""
    <!doctype html><meta charset="utf-8">
    <title>Admin — Quotes</title>
    <style>
      body{{font-family:Inter,system-ui,sans-serif;background:#0f0f0f;color:#fff;margin:0;padding:20px}}
      a{{color:#FFD166;text-decoration:none}}
      .top{{display:flex;justify-content:space-between;align-items:center;margin-bottom:12px}}
      table{{width:100%;border-collapse:collapse;background:#1a1a1a;border:1px solid rgba(255,209,102,.25);border-radius:12px;overflow:hidden}}
      th,td{{padding:10px;border-bottom:1px solid rgba(255,209,102,.15)}} th{{color:#FFD166;text-align:left}}
      .btn{{display:inline-block;padding:8px 12px;border:1px solid #FFD166;border-radius:8px}}
    </style>
    <div class="top">
      <h2 style="color:#FFD166;margin:0">Quote Requests</h2>
      <div>
        <a class="btn" href="{url_for('admin_export')}">Export CSV</a>
        <a class="btn" href="{url_for('admin_logout')}">Logout</a>
      </div>
    </div>
    <table><thead><tr><th>ID</th><th>Name</th><th>Email</th><th>Phone</th><th>Created</th><th>Actions</th></tr></thead>
    <tbody>{rows_html or "<tr><td colspan=6 style='padding:16px'>No entries yet.</td></tr>"}</tbody></table>
    """

@app.get("/admin/delete/<int:qid>")
def admin_delete(qid):
    if not session.get("admin"):
        return redirect(url_for("admin_login"))
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM quotes WHERE id=:id"), {"id": qid})
    return redirect(url_for("admin_dashboard"))

@app.get("/admin/export")
def admin_export():
    if not session.get("admin"):
        return redirect(url_for("admin_login"))
    with engine.begin() as conn:
        rows = conn.execute(text("SELECT id, name, email, phone, created_at FROM quotes ORDER BY id DESC")).all()
    output = io.StringIO()
    w = csv.writer(output)
    w.writerow(["id","name","email","phone","created_at"])
    for r in rows:
        w.writerow([r.id, r.name, r.email, r.phone or "", r.created_at])
    mem = io.BytesIO(output.getvalue().encode("utf-8"))
    return send_file(mem, mimetype="text/csv", as_attachment=True, download_name="quotes.csv")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
