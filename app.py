"""Life Tracker & Goal Planner — multi-user Streamlit app.

Run:  streamlit run app.py
"""
import json
import re
from datetime import date, timedelta

import altair as alt
import pandas as pd
import streamlit as st

import db

st.set_page_config(page_title="Life Tracker", page_icon=":material/insights:", layout="wide")


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

# One brand colour for the whole app (login page, sidebar, buttons, charts).
# Change BRAND here AND primaryColor in .streamlit/config.toml to re-theme everything.
BRAND = "#4F46E5"        # main colour
BRAND_DARK = "#4338CA"   # hover / pressed
BRAND_SOFT = "#EEF2FF"   # light tint for backgrounds
BRAND_LINE = "#C7D2FE"   # light tint for borders
BLUE, SLATE, GRID = BRAND, "#64748B", "#E2E8F0"
STATUS_COLORS = {"Met Goal": "#2F9E6E", "On Track": "#D99A2B", "Needs Focus": "#D65A5A"}

STARTER_HABITS = [
    ("Morning Meditation (15 min)", "Mindfulness", "Right after waking up; sit by the window with a timer"),
    ("Daily Exercise (45 min)", "Health", "Alternate strength training and cardio"),
    ("Read Non-Fiction (20 min)", "Productivity", "After lunch or before bed"),
    ("Drink 2.5L Water", "Health", "Keep a filled 1L bottle on your desk"),
    ("Plan Day & Top 3 Priorities", "Productivity", "Write them down before checking email"),
    ("10,000 Steps", "Health", "Walk during afternoon calls"),
    ("Deep Work Session (90 min)", "Productivity", "Phone on Do Not Disturb, in another room"),
    ("Evening Gratitude & Journaling", "Mindfulness", "Write 3 wins and 1 reflection"),
    ("No Screens 30 Min Before Bed", "Mindfulness", "Dock the phone away from the bed"),
    ("Review Daily Budget & Expenses", "Finance", "Log all of today's transactions"),
]

PAGES = {
    "Dashboard": ":material/dashboard:",
    "Daily Habits": ":material/task_alt:",
    "Weekly Goals": ":material/flag:",
    "Monthly Targets": ":material/calendar_month:",
    "Manage Habits": ":material/tune:",
    "Settings": ":material/settings:",
}

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
:root { --brand:__BRAND__; --brand-dark:__BRAND_DARK__; --brand-soft:__BRAND_SOFT__; --brand-line:__BRAND_LINE__; }
html, body, [class*="css"], .stMarkdown, button, input, textarea { font-family:'Inter',sans-serif; }
#MainMenu, footer { visibility:hidden; }
header[data-testid="stHeader"] { background:transparent; }
.block-container { padding-top:3.2rem; max-width:1240px; }
.stApp { background:linear-gradient(180deg, var(--brand-soft) 0%, #F8FAFC 320px); }

/* page header */
.ph { margin-bottom:1.2rem; padding:.2rem 0 .9rem 14px; border-bottom:1px solid var(--brand-line);
      border-left:5px solid var(--brand); }
.ph .t { font-size:1.6rem; font-weight:700; color:var(--brand); letter-spacing:-.01em; }
.ph .s { font-size:.9rem; color:#64748B; margin-top:2px; }

/* section label */
.sec { font-size:.74rem; font-weight:700; letter-spacing:.07em; text-transform:uppercase;
       color:var(--brand); margin:1.5rem 0 .55rem; }

/* KPI cards */
.kpi { background:#fff; border:1px solid var(--brand-line); border-top:4px solid var(--brand);
       border-radius:10px; padding:16px 18px; height:100%; }
.kpi .l { font-size:.72rem; font-weight:600; letter-spacing:.06em; text-transform:uppercase; color:#64748B; }
.kpi .v { font-size:1.9rem; font-weight:700; color:var(--brand); line-height:1.25; margin-top:2px; }
.kpi .s { font-size:.8rem; color:#64748B; }
.kpi .s.up { color:#2F9E6E; font-weight:600; }
.kpi .s.down { color:#D65A5A; font-weight:600; }
.kpi .bar { height:5px; border-radius:99px; background:var(--brand-soft); margin-top:12px; }
.kpi .bar span { display:block; height:100%; border-radius:99px; background:var(--brand); }

/* day cards */
.dayrow { display:grid; grid-template-columns:repeat(7,1fr); gap:10px; }
.daycard { background:#fff; border:1px solid var(--brand-line); border-bottom:3px solid var(--c);
           border-radius:10px; padding:10px 6px; text-align:center; }
.daycard.today { border-color:var(--brand); border-bottom-color:var(--c); box-shadow:0 0 0 1px var(--brand);
                 background:var(--brand-soft); }
.daycard .dn { font-weight:600; font-size:.85rem; color:var(--brand); }
.daycard .dd { font-size:.7rem; color:#94A3B8; }
.daycard .dv { font-size:1.25rem; font-weight:700; color:#0F172A; margin-top:3px; }
.daycard .ds { font-size:.7rem; font-weight:600; color:var(--c); }
@media (max-width:760px){ .dayrow { grid-template-columns:repeat(4,1fr); } }

.empty { background:#fff; border:1px dashed var(--brand-line); border-radius:10px; padding:28px; text-align:center; color:#475569; }
.empty b { color:var(--brand); font-size:1.02rem; }

/* sidebar */
section[data-testid="stSidebar"] { background:var(--brand-soft); border-right:1px solid var(--brand-line); }
.brand { font-size:1.15rem; font-weight:700; color:var(--brand); }
.brand-sub { font-size:.74rem; color:#64748B; margin-bottom:.9rem; }
.userchip { display:flex; align-items:center; gap:10px; padding:9px 11px; border-radius:10px; margin:.2rem 0 1rem;
            background:#fff; border:1px solid var(--brand-line); }
.avatar { width:32px; height:32px; border-radius:50%; display:flex; align-items:center; justify-content:center;
          color:#fff; font-weight:600; font-size:.85rem; background:var(--brand); }
.userchip .n { font-weight:600; font-size:.88rem; line-height:1.1; color:#0F172A; }
.userchip .r { font-size:.7rem; color:#94A3B8; }
section[data-testid="stSidebar"] div[role="radiogroup"] { gap:2px; }
section[data-testid="stSidebar"] div[role="radiogroup"] label { padding:8px 10px; border-radius:8px; width:100%; cursor:pointer; }
section[data-testid="stSidebar"] div[role="radiogroup"] label:hover:not([data-selected="true"]) { background:#fff; }
section[data-testid="stSidebar"] label[data-testid="stRadioOption"] > div > div:first-child { display:none; }
section[data-testid="stSidebar"] label[data-testid="stRadioOption"][data-selected="true"] { background:var(--brand); }
section[data-testid="stSidebar"] label[data-testid="stRadioOption"][data-selected="true"] p { color:#fff; font-weight:600; }

/* controls */
.stButton > button, .stDownloadButton > button { border-radius:8px; font-weight:600; }
.stButton > button[kind="primary"], .stDownloadButton > button[kind="primary"],
.stFormSubmitButton > button[kind="primary"] { background:var(--brand); border-color:var(--brand); color:#fff; }
.stButton > button[kind="primary"]:hover, .stFormSubmitButton > button[kind="primary"]:hover
  { background:var(--brand-dark); border-color:var(--brand-dark); color:#fff; }
.stButton > button:not([kind="primary"]) { border-color:var(--brand-line); color:var(--brand); }
.stButton > button:not([kind="primary"]):hover { border-color:var(--brand); color:var(--brand-dark); background:#fff; }
div[data-testid="stDataFrame"], div[data-testid="stDataEditor"] { border-radius:10px; overflow:hidden; }
.stTabs [data-baseweb="tab"] { font-weight:600; }
.stTabs [aria-selected="true"] { color:var(--brand); }
.stTabs [data-baseweb="tab-highlight"] { background-color:var(--brand); }

/* login page */
.login-hero { text-align:center; margin-bottom:1.2rem; }
.login-logo { width:58px; height:58px; margin:0 auto 12px; border-radius:16px; background:var(--brand);
              color:#fff; display:flex; align-items:center; justify-content:center; font-size:1.7rem; font-weight:700;
              box-shadow:0 8px 20px rgba(79,70,229,.35); }
.login-hero .t { font-size:1.8rem; font-weight:700; color:var(--brand); letter-spacing:-.01em; }
.login-hero .s { font-size:.95rem; color:#64748B; margin-top:4px; }
.st-key-authcard { border-top:4px solid var(--brand) !important; background:#fff;
    box-shadow:0 10px 30px rgba(79,70,229,.15); border-radius:12px; }
.login-band { position:fixed; top:0; left:0; right:0; height:6px; background:var(--brand); z-index:999; }
</style>
"""
for _k, _v in {"__BRAND__": BRAND, "__BRAND_DARK__": BRAND_DARK,
               "__BRAND_SOFT__": BRAND_SOFT, "__BRAND_LINE__": BRAND_LINE}.items():
    CSS = CSS.replace(_k, _v)
st.markdown(CSS, unsafe_allow_html=True)


# -------------------------------------------------------------------- helpers
def page_header(title, subtitle=""):
    st.markdown(f'<div class="ph"><div class="t">{title}</div><div class="s">{subtitle}</div></div>',
                unsafe_allow_html=True)


def section(title):
    st.markdown(f'<div class="sec">{title}</div>', unsafe_allow_html=True)


def kpi(label, value, sub="", progress=None, tone=""):
    bar = ""
    if progress is not None:
        bar = f'<div class="bar"><span style="width:{min(max(progress, 0), 100):.0f}%"></span></div>'
    return (f'<div class="kpi"><div class="l">{label}</div><div class="v">{value}</div>'
            f'<div class="s {tone}">{sub}</div>{bar}</div>')


def kpi_row(items):
    for col, item in zip(st.columns(len(items)), items):
        col.markdown(kpi(*item), unsafe_allow_html=True)


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


def week_consistency(uid, wk, habits):
    days = [wk + timedelta(i) for i in range(7)]
    done = db.get_done(uid, days[0], days[-1])
    total = sum((h["id"], d.isoformat()) in done for h in habits for d in days)
    return pct(total, len(habits) * 7), total


def day_cards(days, counts, n):
    cells = []
    for d, c in zip(days, counts):
        s = day_status(pct(c, n))
        today = " today" if d == date.today() else ""
        cells.append(
            f'<div class="daycard{today}" style="--c:{STATUS_COLORS[s]}">'
            f'<div class="dn">{DAYS[d.weekday()]}</div><div class="dd">{d:%d %b}</div>'
            f'<div class="dv">{c}/{n}</div><div class="ds">{s}</div></div>')
    st.markdown(f'<div class="dayrow">{"".join(cells)}</div>', unsafe_allow_html=True)


def empty_state(title, text):
    st.markdown(f'<div class="empty"><b>{title}</b><br>{text}</div>', unsafe_allow_html=True)


def style_chart(chart):
    return (chart.configure_view(strokeWidth=0)
            .configure_axis(gridColor=GRID, domain=False, tickColor=GRID,
                            labelColor=SLATE, labelFontSize=11, titleColor=SLATE)
            .configure_legend(labelColor=SLATE, labelFontSize=11, symbolType="square"))


def table_editor(table, uid, key, config, scope_col=None, scope_val=None,
                 date_cols=(), bool_cols=(), text_cols=(), defaults=None):
    """Editable table (add / edit rows; no delete) backed by the DB."""
    cols = ["id"] + db.COLS[table]
    df = pd.DataFrame(db.list_rows(table, uid, scope_col, scope_val), columns=cols)
    if scope_col:
        df = df.drop(columns=[scope_col])
    for c in text_cols:
        df[c] = df[c].fillna("").astype(str)
    for c in date_cols:
        df[c] = pd.to_datetime(df[c], errors="coerce").dt.date
    for c in bool_cols:
        df[c] = df[c].fillna(0).astype(bool)

    vkey = f"{key}_ver"
    ver = st.session_state.get(vkey, 0)
    cfg = {"id": None, **config}
    try:  # "add" = users can add rows but not delete them (newer Streamlit)
        edited = st.data_editor(df, num_rows="add", hide_index=True,
                                column_config=cfg, key=f"{key}_{ver}", width="stretch")
    except Exception:  # older Streamlit: fall back; db.save_rows never deletes anyway
        edited = st.data_editor(df, num_rows="dynamic", hide_index=True,
                                column_config=cfg, key=f"{key}_{ver}", width="stretch")
    if st.button("Save changes", key=f"{key}_save", type="primary", icon=":material/save:"):
        records = edited.to_dict("records")
        for r in records:
            for k, v in (defaults or {}).items():
                if pd.isna(r.get(k)) or r.get(k) == "":
                    r[k] = v
            r["id"] = None if pd.isna(r.get("id")) else int(r["id"])
        db.save_rows(table, uid, records, scope_col, scope_val)
        st.session_state[vkey] = ver + 1  # reset editor state after save
        st.toast("Changes saved", icon=":material/check_circle:")
        st.rerun()


# ------------------------------------------------------------------------ auth
def auth_view():
    _, mid, _ = st.columns([1, 1.15, 1])
    with mid:
        st.markdown('<div class="login-band"></div><div style="height:6vh"></div>', unsafe_allow_html=True)
        st.markdown('<div class="login-hero"><div class="login-logo">L</div>'
                    '<div class="t">Life Tracker</div>'
                    '<div class="s">Daily habits, weekly objectives and monthly targets in one workspace.</div></div>',
                    unsafe_allow_html=True)
        with st.container(border=True, key="authcard"):
            t_login, t_signup = st.tabs(["Log in", "Create account"])
            with t_login:
                with st.form("login", border=False):
                    u = st.text_input("Username")
                    p = st.text_input("Password", type="password")
                    if st.form_submit_button("Log in", type="primary", width="stretch"):
                        user = db.authenticate(u, p)
                        if user:
                            st.session_state["user"] = user
                            st.rerun()
                        st.error("Incorrect username or password.")
            with t_signup:
                with st.form("signup", border=False):
                    u = st.text_input("Username", help="3-30 characters: letters, numbers, _ or .")
                    p1 = st.text_input("Password", type="password", help="At least 6 characters")
                    p2 = st.text_input("Confirm password", type="password")
                    if st.form_submit_button("Create account", type="primary", width="stretch"):
                        if not re.fullmatch(r"[A-Za-z0-9_.]{3,30}", u.strip()):
                            st.error("Username must be 3-30 characters: letters, numbers, _ or .")
                        elif len(p1) < 6:
                            st.error("Password must be at least 6 characters.")
                        elif p1 != p2:
                            st.error("Passwords do not match.")
                        else:
                            ok, msg = db.create_user(u, p1)
                            (st.success if ok else st.error)(msg)


# ------------------------------------------------------------------- dashboard
def page_dashboard(uid, ref, username):
    wk = week_start(ref)
    days = [wk + timedelta(i) for i in range(7)]
    page_header("Dashboard", f"Week of {days[0]:%d %b} – {days[-1]:%d %b %Y} &nbsp;·&nbsp; {username}")

    habits = active_habits(uid)
    n = len(habits)
    done = db.get_done(uid, days[0], days[-1])
    day_counts = [sum((h["id"], d.isoformat()) in done for h in habits) for d in days]
    consistency = pct(sum(day_counts), n * 7)
    prev, prev_total = week_consistency(uid, wk - timedelta(days=7), habits)

    if n and prev_total:
        diff = consistency - prev
        delta, tone = f"{'▲' if diff >= 0 else '▼'} {abs(diff):.1f} pts vs previous week", "up" if diff >= 0 else "down"
    else:
        delta, tone = "No previous-week data", ""

    goals = db.list_rows("weekly_goals", uid, "week_start", wk.isoformat())
    g_done = sum(g["status"] == "Completed" for g in goals)
    targets = db.list_rows("monthly_targets", uid, "month", ref.strftime("%Y-%m"))
    t_done = sum(bool(t["done"]) for t in targets)

    kpi_row([
        ("Active habits", n, "Tracked daily"),
        ("Weekly consistency", f"{consistency:.1f}%", delta, consistency, tone),
        ("Sprint completion", f"{pct(g_done, len(goals)):.0f}%", f"{g_done} of {len(goals)} goals completed",
         pct(g_done, len(goals))),
        ("Monthly targets", f"{pct(t_done, len(targets)):.0f}%", f"{t_done} of {len(targets)} achieved",
         pct(t_done, len(targets))),
    ])

    if n == 0:
        st.write("")
        empty_state("No habits yet",
                    "Open <b>Manage Habits</b> in the sidebar to add your own or load the starter pack.")
        return

    section("This week")
    day_cards(days, day_counts, n)

    left, right = st.columns(2, gap="large")
    rates = [pct(c, n) for c in day_counts]
    with left:
        section("Daily completion rate")
        wdf = pd.DataFrame({"Day": DAYS, "Rate": rates, "Done": day_counts,
                            "Label": [f"{r:.0f}%" for r in rates],
                            "Status": [day_status(r) for r in rates]})
        x = alt.X("Day:N", sort=DAYS, title=None, axis=alt.Axis(labelAngle=0))
        bars = alt.Chart(wdf).mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4, size=34).encode(
            x=x, y=alt.Y("Rate:Q", scale=alt.Scale(domain=[0, 110]), title=None,
                         axis=alt.Axis(values=[0, 25, 50, 75, 100])),
            color=alt.Color("Status:N", legend=alt.Legend(orient="bottom", title=None),
                            scale=alt.Scale(domain=list(STATUS_COLORS), range=list(STATUS_COLORS.values()))),
            tooltip=["Day", alt.Tooltip("Rate:Q", format=".0f", title="Rate %"), "Done", "Status"])
        labels = alt.Chart(wdf).mark_text(dy=-8, fontSize=11, color="#475569").encode(
            x=x, y="Rate:Q", text="Label:N")
        goal = alt.Chart(pd.DataFrame({"y": [80]})).mark_rule(strokeDash=[4, 4], color=BRAND).encode(y="y:Q")
        st.altair_chart(style_chart((bars + labels + goal).properties(height=290)), width="stretch")
        st.caption("Dashed line: 80% target. Met Goal ≥ 80%, On Track ≥ 70%.")
    with right:
        section("Habit performance (days completed of 7)")
        pdf = pd.DataFrame({
            "Habit": [h["name"] for h in habits],
            "Days": [sum((h["id"], d.isoformat()) in done for d in days) for h in habits]})
        hb = alt.Chart(pdf).mark_bar(cornerRadiusTopRight=4, cornerRadiusBottomRight=4, size=16, color=BLUE).encode(
            y=alt.Y("Habit:N", sort="-x", title=None, axis=alt.Axis(labelLimit=230)),
            x=alt.X("Days:Q", scale=alt.Scale(domain=[0, 7.6]), title=None,
                    axis=alt.Axis(values=list(range(8)), format="d")),
            tooltip=["Habit", "Days"])
        ht = alt.Chart(pdf).mark_text(align="left", dx=5, fontSize=11, color="#475569").encode(
            y=alt.Y("Habit:N", sort="-x"), x="Days:Q", text=alt.Text("Days:Q", format="d"))
        st.altair_chart(style_chart((hb + ht).properties(height=max(200, 27 * n + 30))), width="stretch")
        st.caption("Sorted from most to least consistent this week.")

    section("Category breakdown")
    groups = {}
    for h in habits:
        dd = sum((h["id"], d.isoformat()) in done for d in days)
        groups.setdefault(h["category"] or "Other", []).append(dd)
    cdf = pd.DataFrame([{"Category": k, "Habits": len(v), "Share": round(pct(len(v), n), 1),
                         "Avg days done": round(sum(v) / len(v), 1)} for k, v in groups.items()])
    st.dataframe(cdf, hide_index=True, width="stretch", column_config={
        "Share": st.column_config.ProgressColumn("Share of habits", min_value=0, max_value=100, format="%.0f%%"),
        "Avg days done": st.column_config.NumberColumn("Avg days done (of 7)", format="%.1f")})

    section("History — last 14 days")
    start = ref - timedelta(days=13)
    h_done = db.get_done(uid, start, ref)
    notes = db.get_notes(uid, start, ref)
    rows = []
    for i in range(14):
        d = start + timedelta(i)
        c = sum((h["id"], d.isoformat()) in h_done for h in habits)
        r = pct(c, n)
        rows.append({"Date": d, "Day": DAYS[d.weekday()], "Completed": c, "Total": n,
                     "Completion": round(r, 1), "Status": day_status(r),
                     "Notes": notes.get(d.isoformat(), "")})
    hist = pd.DataFrame(rows)
    base = alt.Chart(hist).encode(x=alt.X("Date:T", title=None, axis=alt.Axis(format="%d %b")))
    line = base.mark_line(color=BLUE, strokeWidth=2.5, interpolate="monotone").encode(
        y=alt.Y("Completion:Q", scale=alt.Scale(domain=[0, 100]), title=None))
    pts = base.mark_circle(size=55, color=BLUE).encode(
        y="Completion:Q", tooltip=[alt.Tooltip("Date:T", format="%a, %d %b"),
                                   alt.Tooltip("Completion:Q", format=".0f", title="Completion %"), "Status"])
    rule = alt.Chart(pd.DataFrame({"y": [80]})).mark_rule(strokeDash=[4, 4], color=BRAND).encode(y="y:Q")
    st.altair_chart(style_chart((line + pts + rule).properties(height=240)), width="stretch")
    st.dataframe(hist, hide_index=True, width="stretch", column_config={
        "Date": st.column_config.DateColumn("Date", format="DD MMM YYYY"),
        "Completion": st.column_config.ProgressColumn("Completion", min_value=0, max_value=100, format="%.0f%%"),
        "Notes": st.column_config.TextColumn("Focus / Habit Notes", width="large")})
    st.caption(f"14-day average completion: {hist['Completion'].mean():.1f}%. "
               "Total = number of habits currently active.")


# ---------------------------------------------------------------- daily habits
def page_habits(uid, ref):
    wk = week_start(ref)
    days = [wk + timedelta(i) for i in range(7)]
    labels = [f"{DAYS[i]} {days[i].day}" for i in range(7)]
    page_header("Daily Habits",
                f"Week of {days[0]:%d %b} – {days[-1]:%d %b %Y} &nbsp;·&nbsp; changes are saved as you tick")
    habits = active_habits(uid)
    if not habits:
        empty_state("No habits to track yet",
                    "Go to <b>Manage Habits</b> to add habits or load the starter pack.")
        return

    done = db.get_done(uid, days[0], days[-1])
    df = pd.DataFrame(
        [{"Habit": h["name"], "Category": h["category"] or "Other",
          **{labels[i]: (h["id"], days[i].isoformat()) in done for i in range(7)}}
         for h in habits])

    n = len(habits)
    ints = df[labels].astype(int)
    days_done = [int(v) for v in ints.sum(axis=1)]
    day_counts = [int(v) for v in ints.sum(axis=0)]
    avg = pct(sum(days_done), n * 7)
    perfect = sum(d == 7 for d in days_done)
    kpi_row([
        ("Total habits", n, "Active this week"),
        ("Average consistency", f"{avg:.1f}%", "Across all habits", avg),
        ("Perfect habits", f"{perfect} / {n}", "Completed all 7 days", pct(perfect, n)),
    ])
    section("Weekly check-in")
    edited = st.data_editor(
        df, hide_index=True, width="stretch", key=f"grid_{wk}",
        disabled=["Habit", "Category"],
        column_config={"Habit": st.column_config.TextColumn("Habit", width="medium"),
                       "Category": st.column_config.TextColumn("Category", width="small"),
                       **{l: st.column_config.CheckboxColumn(l, width="small") for l in labels}})
    changed = False
    for i, h in enumerate(habits):
        for j, lab in enumerate(labels):
            new, old = bool(edited.iloc[i][lab]), bool(df.iloc[i][lab])
            if new != old:
                db.set_log(uid, h["id"], days[j], new)
                changed = True
    if changed:
        st.rerun()

    section("Consistency by habit")
    summary = pd.DataFrame({
        "Habit": [h["name"] for h in habits],
        "Days Done": days_done,
        "Consistency": [pct(d, 7) for d in days_done],
        "Cue / Note": [h["cue"] or "" for h in habits],
    })
    st.dataframe(summary, hide_index=True, width="stretch", column_config={
        "Consistency": st.column_config.ProgressColumn(
            "Consistency", min_value=0, max_value=100, format="%.0f%%"),
        "Cue / Note": st.column_config.TextColumn("Cue / Note", width="large")})

    section("Daily totals")
    day_cards(days, day_counts, n)

    st.write("")
    with st.expander("Daily focus note"):
        pick = st.selectbox("Day", days, index=days.index(ref) if ref in days else 0,
                            format_func=lambda d: f"{DAYS[d.weekday()]} {d:%d %b}")
        existing = db.get_notes(uid, pick, pick).get(pick.isoformat(), "")
        note = st.text_area("Note", value=existing, key=f"note_{pick}",
                            placeholder="What went well today? What got in the way?")
        if st.button("Save note", icon=":material/save:"):
            db.set_note(uid, pick, note)
            st.toast("Note saved", icon=":material/check_circle:")


# ----------------------------------------------------------------- weekly goals
def page_weekly(uid, ref):
    wk = week_start(ref)
    page_header("Weekly Goals",
                f"Sprint week {wk:%d %b} – {wk + timedelta(days=6):%d %b %Y} &nbsp;·&nbsp; change the week from the sidebar date")
    goals = db.list_rows("weekly_goals", uid, "week_start", wk.isoformat())
    total = len(goals)
    comp = sum(g["status"] == "Completed" for g in goals)
    prog = sum(g["status"] == "In Progress" for g in goals)
    overdue = sum(1 for g in goals if g["status"] != "Completed" and g["target_date"]
                  and g["target_date"] < date.today().isoformat())
    kpi_row([
        ("Total goals", total, f"{sum(g['priority'] == 'High' for g in goals)} high priority"),
        ("Completed", comp, "Delivered this sprint", pct(comp, total)),
        ("In progress", prog, f"{total - comp - prog} not started", pct(prog, total)),
        ("Overdue", overdue, "Past target date, not completed", None, "down" if overdue else ""),
    ])
    section("Sprint board")
    st.caption("Click a cell to edit. Use the empty row at the bottom to add a goal. "
               "Then click Save changes.")
    table_editor(
        "weekly_goals", uid, "wg", scope_col="week_start", scope_val=wk.isoformat(),
        date_cols=("target_date",), text_cols=("impact", "notes"),
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
    month = ref.strftime("%Y-%m")
    page_header("Monthly Targets", f"{ref:%B %Y} &nbsp;·&nbsp; change the month from the sidebar date")
    targets = db.list_rows("monthly_targets", uid, "month", month)
    total = len(targets)
    ach = sum(bool(t["done"]) for t in targets)
    high = [t for t in targets if t["priority"] == "High"]
    high_done = sum(bool(t["done"]) for t in high)
    kpi_row([
        ("Total targets", total, "Set for this month"),
        ("Achieved", ach, "Marked done", pct(ach, total)),
        ("Achievement rate", f"{pct(ach, total):.0f}%", "Achieved / total", pct(ach, total)),
        ("High priority done", f"{high_done} / {len(high)}", "Most important first", pct(high_done, len(high))),
    ])
    section("Targets")
    st.caption("Click a cell to edit. Use the empty row at the bottom to add a target. "
               "Then click Save changes.")
    table_editor(
        "monthly_targets", uid, "mt", scope_col="month", scope_val=month,
        bool_cols=("done",), text_cols=("description", "progress", "notes"),
        defaults={"priority": "Medium", "done": False},
        config={
            "focus_area": st.column_config.SelectboxColumn("Focus Area", options=CATS, required=True),
            "description": st.column_config.TextColumn("Target Description", width="large"),
            "priority": st.column_config.SelectboxColumn("Priority", options=PRIORITIES),
            "progress": st.column_config.TextColumn("Current Progress / Metric", width="medium"),
            "done": st.column_config.CheckboxColumn("Done"),
            "notes": st.column_config.TextColumn("Key Results & Review Notes", width="large"),
        })


# --------------------------------------------------------------- manage habits
def page_manage(uid):
    page_header("Manage Habits", "Add, rename or pause the habits you track")
    st.caption("Untick Active to pause a habit; its history is always kept.")
    if not db.list_rows("habits", uid):
        empty_state("Start with a ready-made routine",
                    "Load 10 common habits, then edit them to fit your day.")
        if st.button("Load starter habits", type="primary", icon=":material/playlist_add:"):
            db.save_rows("habits", uid, [
                {"id": None, "name": n, "category": c, "cue": q, "active": True}
                for n, c, q in STARTER_HABITS])
            st.rerun()
        st.write("")
    table_editor(
        "habits", uid, "hb", bool_cols=("active",), text_cols=("cue",),
        defaults={"category": "Other", "active": True, "cue": ""},
        config={
            "name": st.column_config.TextColumn("Habit / Daily Task", required=True, width="large"),
            "category": st.column_config.SelectboxColumn("Category", options=CATS),
            "cue": st.column_config.TextColumn("Cue / Note", width="large"),
            "active": st.column_config.CheckboxColumn("Active"),
        })


# --------------------------------------------------------------------- settings
def page_settings(uid, username):
    page_header("Settings", "Export a copy of your data")
    with st.container(border=True):
        st.subheader("Export data")
        st.caption("Download everything stored for your account (habits, logs, goals, targets, notes) as JSON.")
        st.download_button("Download my data", json.dumps(db.export_user(uid), indent=2, default=str),
                           file_name=f"{username}_tracker_data.json", mime="application/json",
                           icon=":material/download:")


# ------------------------------------------------------------------------ main
if "user" not in st.session_state:
    auth_view()
    st.stop()

user = st.session_state["user"]
uid = user["id"]

# New users automatically get the default habits (they can edit them in Manage Habits).
if not db.list_rows("habits", uid):
    db.save_rows("habits", uid, [
        {"id": None, "name": n, "category": c, "cue": q, "active": True}
        for n, c, q in STARTER_HABITS])
with st.sidebar:
    st.markdown('<div class="brand">Life Tracker</div><div class="brand-sub">Goals &amp; habits workspace</div>',
                unsafe_allow_html=True)
    st.markdown(
        f'<div class="userchip"><div class="avatar">{user["username"][0].upper()}</div>'
        f'<div><div class="n">{user["username"]}</div><div class="r">Signed in</div></div></div>',
        unsafe_allow_html=True)
    page = st.radio("Navigation", list(PAGES), format_func=lambda k: f"{PAGES[k]} {k}",
                    label_visibility="collapsed")
    st.divider()
    ref = st.date_input("Reporting date", value=date.today(),
                        help="The week and month shown on every page are based on this date.")
    if st.button("Log out", width="stretch", icon=":material/logout:"):
        st.session_state.clear()
        st.rerun()

{
    "Dashboard": lambda: page_dashboard(uid, ref, user["username"]),
    "Daily Habits": lambda: page_habits(uid, ref),
    "Weekly Goals": lambda: page_weekly(uid, ref),
    "Monthly Targets": lambda: page_monthly(uid, ref),
    "Manage Habits": lambda: page_manage(uid),
    "Settings": lambda: page_settings(uid, user["username"]),
}[page]()
