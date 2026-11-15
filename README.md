# Life Tracker & Goal Planner

A multi-user Streamlit app where every user sets up their own **habits, weekly goals and monthly targets**.
Data is stored in SQLite, scoped per user (`user_id`), and passwords are hashed with PBKDF2.

## Features
- **Accounts** — sign up, log in, log out; every user only sees their own data
- **Dashboard** — KPI cards with week-over-week change, daily completion chart, habit performance, category breakdown, 14-day history
- **Daily Habits** — weekly checkbox grid (saves as you tick), consistency per habit, daily notes
- **Weekly Goals** — sprint board with status, priority, expected impact, reflection and overdue tracking
- **Monthly Targets** — month-wise targets with progress notes and done flag
- **Manage Habits** — add, edit, pause or delete your own habits (starter pack included)
- **Settings** — JSON data export, account deletion

## Run locally
```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```
The database file `data/tracker.db` is created automatically (change the path with the `TRACKER_DB` environment variable).

## Push to GitHub
```bash
git init
git add .
git commit -m "Life Tracker app"
git branch -M main
git remote add origin https://github.com/<username>/life-tracker.git
git push -u origin main
```

## Deploy
- **Streamlit Community Cloud**: connect the repo and set the main file to `app.py`.
  The filesystem there is ephemeral, so SQLite data can be lost on restart or redeploy.
  For production use a persistent database (Supabase/Postgres) or a host with a persistent disk (Render disk, AWS EC2/EBS).
  All database code lives in `db.py`, so that is the only file you would need to change.
- **Your own server / AWS EC2**: `streamlit run app.py --server.port 8501`, and back up the `data/` folder.

## Project layout
```
app.py                    UI (pages, charts, styling)
db.py                     SQLite storage, auth, per-user queries
.streamlit/config.toml    Theme
requirements.txt
```
