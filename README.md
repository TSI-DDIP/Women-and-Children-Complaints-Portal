# Tenkasi Petition Portal (Flask)

A simple petition redressal and management portal for Tenkasi District Administration.

## Features
- Public registration/login with mobile + password
- Submit petition with Taluk/Firka/Village picker
- Limits: 1 petition per 15 days; max 2 per calendar month
- Track petitions by ID or mobile
- Officer login via PIN to review and update status with filters

## Tech
- Python, Flask, SQLite
- Gunicorn for production

## Local development
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export SECRET_KEY="dev-secret"
export OFFICER_PIN="thfvcbdkiem3640"
python app.py
# open http://localhost:5000
```

## Deploy on Render
- Commit this repo
- Create a new Web Service
  - Environment: Python
  - Build Command: `pip install -r requirements.txt`
  - Start Command: `gunicorn app:app`
  - Add Env Vars:
    - `SECRET_KEY` (Generate)
    - `OFFICER_PIN` = `thfvcbdkiem3640`
- Or use `render.yaml` for Blueprint Deploys.

## Environment variables
- `SECRET_KEY` (required)
- `OFFICER_PIN` (defaults to the provided PIN if not set)

## Notes
- SQLite DB file: `complaints.db` in app root
- DB schema is auto-initialized on first run