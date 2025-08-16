import os, csv, io, smtplib, sys
from datetime import datetime
from email.message import EmailMessage

from flask import Flask, request, redirect, url_for, session, send_file, render_template
from sqlalchemy import create_engine, text
from werkzeug.utils import secure_filename
from email_validator import validate_email, EmailNotValidError
from dotenv import load_dotenv

# -------------------------------------------------
# Env / Config
# -------------------------------------------------
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///quotes.db")
engine = create_engine(DATABASE_URL, future=True)

ADMIN_USER = os.getenv("ADMIN_USER", "admin")
ADMIN_PASS = os.getenv("ADMIN_PASS", "password123")
SECRET_KEY  = os.getenv("SECRET_KEY", "devkey_change_me")

# SMTP (use your @grillshine.com host later; bypass enabled via DISABLE_SMTP)
MAIL_SERVER   = os.getenv("MAIL_SERVER", "smtp.gmail.com")
MAIL_PORT     = int(os.getenv("MAIL_PORT", "587"))
MAIL_USE_TLS  = os.getenv("MAIL_USE_TLS", "true").lower() == "true"
MAIL_USERNAME = os.getenv("MAIL_USERNAME")
MAIL_PASSWORD = os.getenv("MAIL_PASSWORD")
MAIL_FROM     = os.getenv("MAIL_FROM", MAIL_USERNAME or "no-reply@localhost")
ADMIN_EMAIL   = os.getenv("ADMIN_EMAIL")
DISABLE_SMTP  = os.getenv("DISABLE_SMTP", "false").lower() == "true"  # <— BYPASS SWITCH

# Local uploads
UPLOAD_DIR  = os.getenv("UPLOAD_DIR", "uploads")
ALLOWED_EXTS = {"jpg","jpeg","png","gif","webp","heic","heif"}
os.makedirs(UPLOAD_DIR, exist_ok=True)

app = Flask(__name__, static_folder=".", static_url_path="")
app.secret_key = SECRET_KEY
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16 MB

def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTS

# -------------------------------------------------
# DB bootstrap (SQLite/Postgres)
# -------------------------------------------------
def init_db():
    backend = engine.url.get_backend_name()
    if backend == "sqlite":
        ddl = """
        CREATE TABLE IF NOT EXISTS quotes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            phone TEXT,
            details TEXT,
            images TEXT,
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
            details TEXT,
            images TEXT,
            created_at TIMESTAMP NOT NULL
        )
        """
    with engine.begin() as conn:
        conn.execute(text(ddl))

init_db()

# -------------------------------------------------
# Email helpers (dev-safe)
# -------------------------------------------------
def _dev_print(subject, to, html_body, text_body=None):
    print("\n=== DEV EMAIL (SMTP DISABLED or CREDS MISSING) ===", file=sys.stderr)
    print(f"TO: {to}", file=sys.stderr)
    print(f"SUBJECT: {subject}", file=sys.stderr)
    if text_body:
        print(f"\nTEXT:\n{text_body}", file=sys.stderr)
    print(f"\nHTML:\n{html_body}\n", file=sys.stderr)
    print("=== END DEV EMAIL ===\n", file=sys.stderr)

def send_email(subject: str, to: str, html_body: str, text_body: str | None = None, reply_to: str | None = None):
    """
    Dev-safe sender.
    If DISABLE_SMTP is true OR creds are missing, just print to console.
    """
    if DISABLE_SMTP or not (MAIL_USERNAME and MAIL_PASSWORD):
        _dev_print(subject, to, html_body, text_body)
        return

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = MAIL_FROM
    msg["To"] = to
    if reply_to:
        msg["Reply-To"] = reply_to
    if text_body:
        msg.set_content(text_body)
    msg.add_alternative(html_body, subtype="html")

    if MAIL_USE_TLS:
        with smtplib.SMTP(MAIL_SERVER, MAIL_PORT) as s:
            s.starttls()
            s.login(MAIL_USERNAME, MAIL_PASSWORD)
            s.send_message(msg)
    else:
        with smtplib.SMTP_SSL(MAIL_SERVER, MAIL_PORT) as s:
            s.login(MAIL_USERNAME, MAIL_PASSWORD)
            s.send_message(msg)

def notify_admin(subject: str, html_body: str, text_body: str | None = None):
    if ADMIN_EMAIL:
        send_email(subject, ADMIN_EMAIL, html_body, text_body)

# -------------------------------------------------
# Public pages (served as static files)
# -------------------------------------------------
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

# -------------------------------------------------
# Form handler (save + email)
# -------------------------------------------------
@app.post("/quote")
def quote():
    name    = (request.form.get("name") or "").strip()
    email   = (request.form.get("email") or "").strip()
    phone   = (request.form.get("phone") or "").strip()
    details = (request.form.get("details") or "").strip()

    # robust email validation + normalization
    try:
        email = validate_email(email).normalized
    except EmailNotValidError:
        return redirect(url_for("home") + "#quote?err=invalid_email")

    if not name:
        return redirect(url_for("home") + "#quote?err=name")

    # Save images locally
    image_urls = []
    if "images" in request.files:
        for f in request.files.getlist("images"):
            if not f or not f.filename:
                continue
            if not allowed_file(f.filename):
                continue
            filename = secure_filename(f.filename)
            unique   = datetime.utcnow().strftime("%Y%m%d%H%M%S%f") + "_" + filename
            save_path = os.path.join(UPLOAD_DIR, unique)
            try:
                f.save(save_path)
                image_urls.append(f"/{UPLOAD_DIR}/{unique}")
            except Exception as e:
                print("Image save failed:", e)

    # DB insert
    created = datetime.utcnow().isoformat(timespec="seconds")
    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO quotes (name, email, phone, details, images, created_at)
            VALUES (:n,:e,:p,:d,:i,:c)
        """), {"n": name, "e": email, "p": phone, "d": details, "i": ",".join(image_urls), "c": created})

    # Render email templates from templates/emails/*
    cust_html = render_template("emails/customer_confirmation.html", name=name)
    send_email(
        subject="We received your Grill Shine quote request",
        to=email,
        html_body=cust_html,
        text_body=f"Hi {name}, we received your Grill Shine quote request and will reach out shortly.\n— Grill Shine"
    )

    admin_html = render_template(
        "emails/admin_new_quote.html",
        name=name, email=email, phone=phone, message=details
    )
    notify_admin(
        subject=f"[Grill Shine] New quote from {name}",
        html_body=admin_html,
        text_body=f"New quote:\nName: {name}\nEmail: {email}\nPhone: {phone}\n\nDetails:\n{details or '—'}"
    )

    return redirect(url_for("thank_you"))

# -------------------------------------------------
# Admin auth
# -------------------------------------------------
@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        if request.form.get("username") == ADMIN_USER and request.form.get("password") == ADMIN_PASS:
            session["admin"] = True
            return redirect(url_for("admin_dashboard"))
        return ('<p style="color:#ff8484;font-family:system-ui">Invalid credentials</p>' + LOGIN_FORM)
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

# -------------------------------------------------
# Admin dashboard
# -------------------------------------------------
@app.get("/admin")
@app.get("/admin/dashboard")
def admin_dashboard():
    if not session.get("admin"):
        return redirect(url_for("admin_login"))
    with engine.begin() as conn:
        rows = conn.execute(text(
            "SELECT id, name, email, phone, details, images, created_at FROM quotes ORDER BY id DESC"
        )).all()

    rows_html = ""
    for r in rows:
        img_html = ""
        if r.images:
            for url in r.images.split(","):
                url = (url or "").strip()
                if url:
                    img_html += (
                        f"<a href='{url}' target='_blank'>"
                        f"<img src='{url}' style='max-width:80px;max-height:80px;margin:2px;border-radius:6px;'></a>"
                    )
        rows_html += f"""
        <tr>
            <td>{r.id}</td>
            <td>{r.name}</td>
            <td>{r.email}</td>
            <td>{r.phone or ''}</td>
            <td style="max-width:320px;white-space:pre-wrap">{(r.details or '')}</td>
            <td>{img_html}</td>
            <td>{r.created_at}</td>
            <td><a href='{url_for('admin_delete', qid=r.id)}' onclick='return confirm("Delete?")'>Delete</a></td>
        </tr>
        """

    return f"""
    <!doctype html><meta charset="utf-8">
    <title>Admin — Quotes</title>
    <style>
      body{{font-family:Inter,system-ui,sans-serif;background:#0f0f0f;color:#fff;margin:0;padding:20px}}
      a{{color:#FFD166;text-decoration:none}}
      .top{{display:flex;justify-content:space-between;align-items:center;margin-bottom:12px}}
      table{{width:100%;border-collapse:collapse;background:#1a1a1a;border:1px solid rgba(255,209,102,.25);border-radius:12px;overflow:hidden}}
      th,td{{padding:10px;border-bottom:1px solid rgba(255,209,102,.15);vertical-align:top}} th{{color:#FFD166;text-align:left}}
      .btn{{display:inline-block;padding:8px 12px;border:1px solid #FFD166;border-radius:8px}}
      img{{display:block}}
    </style>
    <div class="top">
      <h2 style="color:#FFD166;margin:0">Quote Requests</h2>
      <div>
        <a class="btn" href="{url_for('admin_export')}">Export CSV</a>
        <a class="btn" href="{url_for('admin_logout')}">Logout</a>
      </div>
    </div>
    <table>
      <thead><tr><th>ID</th><th>Name</th><th>Email</th><th>Phone</th><th>Details</th><th>Images</th><th>Created</th><th>Actions</th></tr></thead>
      <tbody>{rows_html or "<tr><td colspan=8 style='padding:16px'>No entries yet.</td></tr>"}</tbody>
    </table>
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
        rows = conn.execute(text(
            "SELECT id, name, email, phone, details, images, created_at FROM quotes ORDER BY id DESC"
        )).all()
    output = io.StringIO()
    w = csv.writer(output)
    w.writerow(["id","name","email","phone","details","images","created_at"])
    for r in rows:
        w.writerow([r.id, r.name, r.email, r.phone or "", r.details or "", r.images or "", r.created_at])
    mem = io.BytesIO(output.getvalue().encode("utf-8"))
    return send_file(mem, mimetype="text/csv", as_attachment=True, download_name="quotes.csv")

# -------------------------------------------------
# Dev test endpoint (verify without a password)
# -------------------------------------------------
@app.get("/dev/send-test-email")
def dev_send_test():
    send_email("Test from Grill Shine", ADMIN_EMAIL or "you@example.com",
               "<p>Test body</p>", "Test body (text)")
    return "Sent (or printed to console if no SMTP creds / SMTP disabled)."

# -------------------------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))


