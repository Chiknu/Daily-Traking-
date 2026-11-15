# 🎯 Life Tracker & Goal Planner

Multi-user Streamlit app: har user apni **habits, weekly goals aur monthly targets** khud set karta hai.
Data SQLite me store hota hai, har user ka data alag (user_id se scoped), passwords PBKDF2 se hashed.

## Features
- 🔐 Signup / Login / Logout
- 📊 Dashboard — KPI cards (HTML/CSS), day-wise completion, category breakdown, 14-day history
- ✅ Daily Habits — weekly checkbox grid (auto-save), consistency, daily notes
- 🎯 Weekly Goals — sprint tracker (status, priority, impact, reflection)
- 🏆 Monthly Targets — month-wise targets with progress & done
- 🌿 Manage Habits — apni habits add/edit/delete (starter pack ke saath)
- ⚙️ Settings — JSON export, account delete

## Local run
```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```
DB file `data/tracker.db` apne aap ban jati hai (`TRACKER_DB` env var se path badal sakte ho).

## GitHub pe daalna
```bash
git init
git add .
git commit -m "Life Tracker app"
git branch -M main
git remote add origin https://github.com/<username>/life-tracker.git
git push -u origin main
```

## Deploy
- **Streamlit Community Cloud**: repo connect karo, main file `app.py`.
  ⚠️ Yahan filesystem ephemeral hai — restart/redeploy pe SQLite data ud sakta hai.
  Production ke liye persistent DB (Supabase/Postgres) ya persistent disk wala host (Render disk, AWS EC2/EBS) use karo;
  saara DB code `db.py` me hai, sirf wahi badalna padega.
- **Apna server / AWS EC2**: `streamlit run app.py --server.port 8501` + `data/` folder ka backup.
