"""Life Tracker & Goal Planner — multi-user Streamlit app.

Run:  streamlit run app.py
"""
import json
import re
from datetime import date, timedelta

import pandas as pd
import streamlit as st

import db

st.set_page_config(page_title="Life Tracker & Goal Planner", page_icon="🎯", layout="wide")


@st.cache_resource
def _init():
    db.init_db()
    return True


_init()

# ------------------------------------------------------------------ constants
DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
CATS = ["Health", "Mindfulness", "Productivity", "Finance", "Personal Growth",
        "Career & Wealth", "Relationships", "Other"]
PRIORITIES = ["High", "Medium", "Low"]
GOAL_STATUS = ["Not Started", "In Progress", "Completed"]
STARTER_HABITS = [
    ("Morning Meditation (15 min)", "Mindfulness", "Uthte hi, timer laga ke baitho"),
    ("Daily Exercise (45 min)", "Health", "Strength aur cardio alternate karo"),
    ("Read Non-Fiction (20 min)", "Productivity", "Sone se pehle ya lunch ke baad"),
    ("Drink 2.5L Water", "Health", "1L bottle hamesha desk pe"),
    ("Plan Day & Top 3 Priorities", "Productivity", "Email dekhne se pehle"),
    ("10,000 Steps", "Health", "Calls ke beech walking"),
    ("Deep Work Session (90 min)", "Productivity", "Phone DND pe, dusre room me"),
    ("Evening Gratitude & Journaling", "Mindfulness", "3 wins + 1 reflection"),
    ("No Screens 30 Min Before Bed", "Mindfulness", "Phone bed se door"),
    ("Review Daily Budget & Expenses", "Finance", "Saare transactions log karo"),
]

CSS = """
<style>
.kpi{border-radius:14px;padding:16px 18px;
     background:linear-gradient(135deg,rgba(99,102,241,.20),rgba(14,165,233,.12));
     border:1px solid rgba(128,128,128,.25);height:100%}
.kpi .l{font-size:.75rem;opacity:.75;letter-spacing:.05em;text-transform:uppercase}
.kpi .v{font-size:2.1rem;font-weight:700;line-height:1.25}
.kpi .s{font-size:.8rem;opacity:.7}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


# -------------------------------------------------------------------- helpers
def kpi(label, value, sub=""):
    return (f'<div class="kpi"><div class="l">{label}</div>'
            f'<div class="v">{value}</div><div class="s">{sub}</div></div>')


def kpi_row(items):
    for col, (label, value, sub) in zip(st.columns(len(items)), items):
        col.markdown(kpi(label, value, sub), unsafe_allow_html=True)


def week_start(d: date) -> date:
    return d - timedelta(days=d.weekday())


def pct(a, b):
    return (a / b * 100) if b else 0.0


def day_status(rate):
    if rate >= 80:
        return "Met Goal"
    if rate >= 70:
        return "On Track"
    return "Needs Focus"


def active_habits(uid):
    return [h for h in db.list_rows("habits", uid) if h["active"]]


def table_editor(table, uid, key, config, scope_col=None, scope_val=None,
                 date_cols=(), bool_cols=(), defaults=None):
    """Editable table (add / edit / delete rows) backed by the DB."""
    cols = ["id"] + db.COLS[table]
    df = pd.DataFrame(db.list_rows(table, uid, scope_col, scope_val), columns=cols)
    if scope_col:
        df = df.drop(columns=[scope_col])
    for c in date_cols:
        df[c] = pd.to_datetime(df[c], errors="coerce").dt.date
    for c in bool_cols:
        df[c] = df[c].fillna(0).astype(bool)

    vkey = f"{key}_ver"
    ver = st.session_state.get(vkey, 0)
    cfg = {"id": None, **config}
    edited = st.data_editor(df, num_rows="dynamic", hide_index=True,
                            column_config=cfg, key=f"{key}_{ver}", width="stretch")
    if st.button("💾 Save changes", key=f"{key}_save", type="primary"):
        records = edited.to_dict("records")
        for r in records:
            for k, v in (defaults or {}).items():
                if pd.isna(r.get(k)):
                    r[k] = v
            r["id"] = None if pd.isna(r.get("id")) else int(r["id"])
        db.save_rows(table, uid, records, scope_col, scope_val)
        st.session_state[vkey] = ver + 1  # reset editor state after save
        st.toast("Saved ✅")
        st.rerun()


# ------------------------------------------------------------------------ auth
def auth_view():
    st.title("🎯 Life Tracker & Goal Planner")
    st.caption("Apni habits, weekly goals aur monthly targets — sab ek jagah.")
    t_login, t_signup = st.tabs(["Login", "Sign up"])
    with t_login:
        with st.form("login"):
            u = st.text_input("Username")
            p = st.text_input("Password", type="password")
            if st.form_submit_button("Login", type="primary"):
                user = db.authenticate(u, p)
                if user:
                    st.session_state["user"] = user
                    st.rerun()
                st.error("Username ya password galat hai.")
    with t_signup:
        with st.form("signup"):
            u = st.text_input("Naya username (3-30, letters/numbers/_ .)")
            p1 = st.text_input("Password (min 6)", type="password")
            p2 = st.text_input("Password dobara", type="password")
            if st.form_submit_button("Account banao"):
                if not re.fullmatch(r"[A-Za-z0-9_.]{3,30}", u.strip()):
                    st.error("Username 3-30 chars ka ho, sirf letters/numbers/_ .")
                elif len(p1) < 6:
                    st.error("Password kam se kam 6 characters ka rakho.")
                elif p1 != p2:
                    st.error("Dono passwords match nahi kar rahe.")
                else:
                    ok, msg = db.create_user(u, p1)
                    (st.success if ok else st.error)(msg)


# ------------------------------------------------------------------- dashboard
def page_dashboard(uid, ref):
    st.header("📊 Executive Dashboard & Life Analytics")
    wk = week_start(ref)
    days = [wk + timedelta(i) for i in range(7)]
    habits = active_habits(uid)
    n = len(habits)
    done = db.get_done(uid, days[0], days[-1])
    day_counts = [sum((h["id"], d.isoformat()) in done for h in habits) for d in days]
    consistency = pct(sum(day_counts), n * 7)

    goals = db.list_rows("weekly_goals", uid, "week_start", wk.isoformat())
    g_done = sum(g["status"] == "Completed" for g in goals)
    targets = db.list_rows("monthly_targets", uid, "month", ref.strftime("%Y-%m"))
    t_done = sum(bool(t["done"]) for t in targets)

    st.caption(f"Week: {days[0]:%d %b} – {days[-1]:%d %b %Y}   |   Month: {ref:%B %Y}")
    kpi_row([
        ("🎯 Active Habits", n, "Manage Habits se badlo"),
        ("📈 Weekly Consistency", f"{consistency:.1f}%", "is hafte ka average"),
        ("⚡ Weekly Sprint Goals", f"{pct(g_done, len(goals)):.0f}%", f"{g_done}/{len(goals)} complete"),
        ("🏆 Monthly Targets", f"{pct(t_done, len(targets)):.0f}%", f"{t_done}/{len(targets)} achieved"),
    ])
    if n == 0:
        st.info("Abhi koi habit nahi hai. **🌿 Manage Habits** page pe jaake habits add karo.")
        return

    st.subheader("Day-wise completion (is hafte)")
    rates = [pct(c, n) for c in day_counts]
    left, right = st.columns([3, 2])
    left.bar_chart(pd.DataFrame({"Completion %": rates}, index=DAYS))
    right.dataframe(pd.DataFrame({
        "Day": DAYS, "Tasks Done": day_counts, "Daily Target": n,
        "Rate %": [round(r, 1) for r in rates], "Status": [day_status(r) for r in rates],
    }), hide_index=True, width="stretch")

    st.subheader("Category breakdown")
    groups = {}
    for h in habits:
        dd = sum((h["id"], d.isoformat()) in done for d in days)
        groups.setdefault(h["category"] or "Other", []).append(dd)
    st.dataframe(pd.DataFrame([
        {"Life Category": k, "Habits": len(v), "% Share": round(pct(len(v), n), 1),
         "Avg Days Done": round(sum(v) / len(v), 1)} for k, v in groups.items()
    ]), hide_index=True, width="stretch")

    st.subheader("Historical log (last 14 days)")
    start = ref - timedelta(days=13)
    h_done = db.get_done(uid, start, ref)
    notes = db.get_notes(uid, start, ref)
    rows = []
    for i in range(14):
        d = start + timedelta(i)
        c = sum((h["id"], d.isoformat()) in h_done for h in habits)
        r = pct(c, n)
        rows.append({"Date": d, "Day": DAYS[d.weekday()], "Tasks Completed": c,
                     "Total Tasks": n, "Completion %": round(r, 1),
                     "Status": day_status(r), "Notes": notes.get(d.isoformat(), "")})
    hist = pd.DataFrame(rows)
    st.line_chart(hist.set_index("Date")["Completion %"])
    st.dataframe(hist, hide_index=True, width="stretch")
    st.caption(f"Historical average: {hist['Completion %'].mean():.1f}% "
               "(Total tasks = abhi ke active habits)")


# ---------------------------------------------------------------- daily habits
def page_habits(uid, ref):
    st.header("✅ Daily Habits & Routine Tracker")
    wk = week_start(ref)
    days = [wk + timedelta(i) for i in range(7)]
    labels = [f"{DAYS[i]} {days[i].day}" for i in range(7)]
    habits = active_habits(uid)
    if not habits:
        st.info("Pehle **🌿 Manage Habits** me habits add karo (ya starter pack load karo).")
        return
    st.caption(f"Week: {days[0]:%d %b} – {days[-1]:%d %b %Y} — checkbox tick karte hi save ho jata hai.")

    done = db.get_done(uid, days[0], days[-1])
    df = pd.DataFrame(
        [{"Habit": h["name"], "Category": h["category"] or "Other",
          **{labels[i]: (h["id"], days[i].isoformat()) in done for i in range(7)}}
         for h in habits])
    edited = st.data_editor(
        df, hide_index=True, width="stretch", key=f"grid_{wk}",
        disabled=["Habit", "Category"],
        column_config={l: st.column_config.CheckboxColumn(l) for l in labels})

    changed = False
    for i, h in enumerate(habits):
        for j, lab in enumerate(labels):
            new, old = bool(edited.iloc[i][lab]), bool(df.iloc[i][lab])
            if new != old:
                db.set_log(uid, h["id"], days[j], new)
                changed = True
    if changed:
        st.rerun()

    n = len(habits)
    day_counts = [int(df[l].sum()) for l in labels]
    days_done = [int(df.iloc[i][labels].sum()) for i in range(n)]
    kpi_row([
        ("Total Habits", n, ""),
        ("Avg Consistency", f"{pct(sum(days_done), n * 7):.1f}%", "is hafte"),
        ("Perfect Habits (7/7)", f"{sum(d == 7 for d in days_done)} / {n}", ""),
    ])
    st.write("")
    summary = pd.DataFrame({
        "Habit": [h["name"] for h in habits],
        "Days Done": days_done,
        "Consistency": [pct(d, 7) for d in days_done],
        "Cue / Note": [h["cue"] or "" for h in habits],
    })
    st.dataframe(summary, hide_index=True, width="stretch", column_config={
        "Consistency": st.column_config.ProgressColumn(
            "Consistency", min_value=0, max_value=100, format="%.0f%%")})
    st.dataframe(pd.DataFrame(
        [[str(c) for c in day_counts], [str(n)] * 7,
         [f"{pct(c, n):.0f}%" for c in day_counts]],
        index=["Habits Completed", "Daily Target", "Success Rate"], columns=DAYS),
        width="stretch")

    with st.expander("📝 Daily focus / habit note"):
        pick = st.selectbox("Din chuno", days, index=days.index(ref) if ref in days else 0,
                            format_func=lambda d: f"{DAYS[d.weekday()]} {d:%d %b}")
        existing = db.get_notes(uid, pick, pick).get(pick.isoformat(), "")
        note = st.text_area("Note", value=existing, key=f"note_{pick}")
        if st.button("Note save karo"):
            db.set_note(uid, pick, note)
            st.toast("Note saved ✅")


# ----------------------------------------------------------------- weekly goals
def page_weekly(uid, ref):
    st.header("🎯 Weekly Goals & Sprint Tracker")
    wk = week_start(ref)
    st.caption(f"Sprint week: {wk:%d %b} – {wk + timedelta(days=6):%d %b %Y}  "
               "(sidebar ki date se week badlo). Naya row add karne ke liye table ke neeche '+' dabao.")
    goals = db.list_rows("weekly_goals", uid, "week_start", wk.isoformat())
    total = len(goals)
    comp = sum(g["status"] == "Completed" for g in goals)
    kpi_row([
        ("Total Goals", total, ""),
        ("Completed", comp, ""),
        ("Pending / In Progress", total - comp, ""),
        ("Sprint Completion", f"{pct(comp, total):.0f}%",
         f"{sum(g['priority'] == 'High' for g in goals)} high priority"),
    ])
    st.write("")
    table_editor(
        "weekly_goals", uid, "wg", scope_col="week_start", scope_val=wk.isoformat(),
        date_cols=("target_date",),
        defaults={"status": "Not Started", "priority": "Medium", "category": "Other"},
        config={
            "goal": st.column_config.TextColumn("Goal / Deliverable", required=True, width="large"),
            "category": st.column_config.SelectboxColumn("Category", options=CATS),
            "target_date": st.column_config.DateColumn("Target Date"),
            "status": st.column_config.SelectboxColumn("Status", options=GOAL_STATUS),
            "priority": st.column_config.SelectboxColumn("Priority", options=PRIORITIES),
            "impact": st.column_config.TextColumn("Expected Impact / Success Metric", width="large"),
            "notes": st.column_config.TextColumn("Outcome & Reflection", width="large"),
        })


# --------------------------------------------------------------- monthly targets
def page_monthly(uid, ref):
    st.header("🏆 Monthly Targets & Long-Term Objectives")
    month = ref.strftime("%Y-%m")
    st.caption(f"Month: {ref:%B %Y} (sidebar ki date se month badlo).")
    targets = db.list_rows("monthly_targets", uid, "month", month)
    total = len(targets)
    ach = sum(bool(t["done"]) for t in targets)
    high = [t for t in targets if t["priority"] == "High"]
    kpi_row([
        ("Total Targets", total, ""),
        ("Achieved", ach, ""),
        ("Achievement Rate", f"{pct(ach, total):.0f}%", ""),
        ("High Priority Done", f"{sum(bool(t['done']) for t in high)} / {len(high)}", ""),
    ])
    st.write("")
    table_editor(
        "monthly_targets", uid, "mt", scope_col="month", scope_val=month,
        bool_cols=("done",),
        defaults={"priority": "Medium", "done": False},
        config={
            "focus_area": st.column_config.SelectboxColumn("Focus Area", options=CATS, required=True),
            "description": st.column_config.TextColumn("Target Description", width="large"),
            "priority": st.column_config.SelectboxColumn("Priority", options=PRIORITIES),
            "progress": st.column_config.TextColumn("Current Progress / Metric", width="medium"),
            "done": st.column_config.CheckboxColumn("Done?"),
            "notes": st.column_config.TextColumn("Key Results & Review Notes", width="large"),
        })


# --------------------------------------------------------------- manage habits
def page_manage(uid):
    st.header("🌿 Manage Habits")
    st.caption("Apni habits yahan add / edit / delete karo. 'Active' band karoge to habit grid se hat jayegi "
               "(history safe rehti hai). Row delete karne se uske logs bhi delete ho jate hain.")
    if not db.list_rows("habits", uid):
        if st.button("✨ Starter habits load karo (10)"):
            db.save_rows("habits", uid, [
                {"id": None, "name": n, "category": c, "cue": q, "active": True}
                for n, c, q in STARTER_HABITS])
            st.rerun()
    table_editor(
        "habits", uid, "hb", bool_cols=("active",),
        defaults={"category": "Other", "active": True, "cue": ""},
        config={
            "name": st.column_config.TextColumn("Habit / Daily Task", required=True, width="large"),
            "category": st.column_config.SelectboxColumn("Category", options=CATS),
            "cue": st.column_config.TextColumn("Cue / Note", width="large"),
            "active": st.column_config.CheckboxColumn("Active"),
        })


# --------------------------------------------------------------------- settings
def page_settings(uid, username):
    st.header("⚙️ Settings")
    st.subheader("Data export")
    st.download_button("⬇️ Apna poora data (JSON)",
                       json.dumps(db.export_user(uid), indent=2, default=str),
                       file_name=f"{username}_tracker_data.json", mime="application/json")
    st.subheader("Danger zone")
    confirm = st.text_input(f"Account delete karne ke liye username type karo: **{username}**")
    if st.button("🗑️ Account aur saara data delete karo"):
        if confirm.strip().lower() == username.lower():
            db.delete_user(uid)
            st.session_state.clear()
            st.rerun()
        else:
            st.error("Username match nahi hua.")


# ------------------------------------------------------------------------ main
if "user" not in st.session_state:
    auth_view()
    st.stop()

user = st.session_state["user"]
uid = user["id"]
with st.sidebar:
    st.markdown(f"### 👤 {user['username']}")
    page = st.radio("Menu", ["📊 Dashboard", "✅ Daily Habits", "🎯 Weekly Goals",
                             "🏆 Monthly Targets", "🌿 Manage Habits", "⚙️ Settings"])
    ref = st.date_input("📅 Date (week/month isse set hoga)", value=date.today())
    if st.button("Logout"):
        st.session_state.clear()
        st.rerun()

{
    "📊 Dashboard": lambda: page_dashboard(uid, ref),
    "✅ Daily Habits": lambda: page_habits(uid, ref),
    "🎯 Weekly Goals": lambda: page_weekly(uid, ref),
    "🏆 Monthly Targets": lambda: page_monthly(uid, ref),
    "🌿 Manage Habits": lambda: page_manage(uid),
    "⚙️ Settings": lambda: page_settings(uid, user["username"]),
}[page]()
