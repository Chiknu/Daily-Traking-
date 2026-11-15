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
OK, WARN, BAD = "#16A34A", "#F59E0B", "#EF4444"      # completed / in progress / missed
STATUS_COLORS = {"Met Goal": OK, "On Track": WARN, "Needs Focus": BAD}

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
:root { --brand:__BRAND__; --brand-dark:__BRAND_DARK__; --brand-soft:__BRAND_SOFT__; --brand-line:__BRAND_LINE__;
        --bg:#F7F8FC; --card:#FFFFFF; --line:#E6E8EF; --ink:#111827; --mute:#6B7280; --ok:#16A34A; --ok-soft:#DCFCE7; }
html, body, [class*="css"], .stMarkdown, button, input, textarea { font-family:'Inter',sans-serif; }
#MainMenu, footer { visibility:hidden; }
header[data-testid="stHeader"] { background:transparent; }
.stApp { background:var(--bg); }
.block-container { padding-top:3rem; padding-bottom:4rem; max-width:1240px; }

/* page header */
.ph { margin-bottom:1.8rem; }
.ph .t { font-size:1.9rem; font-weight:700; color:var(--ink); letter-spacing:-.02em; }
.ph .s { font-size:.92rem; color:var(--mute); margin-top:4px; }

/* section label */
.sec { font-size:1.02rem; font-weight:600; color:var(--ink); margin:2.4rem 0 .8rem; }

/* KPI cards */
.kpi { background:var(--card); border:1px solid var(--line); border-radius:16px; padding:20px 22px; min-height:150px; box-sizing:border-box; }
.kpi .l { font-size:.78rem; font-weight:500; color:var(--mute); }
.kpi .v { font-size:2rem; font-weight:700; color:var(--ink); line-height:1.2; margin-top:6px; }
.kpi .s { font-size:.8rem; color:var(--mute); margin-top:2px; }
.kpi .s.up { color:var(--ok); font-weight:600; }
.kpi .s.down { color:#EF4444; font-weight:600; }
.kpi .bar { height:6px; border-radius:99px; background:#EEF0F5; margin-top:14px; }
.kpi .bar span { display:block; height:100%; border-radius:99px; background:var(--ok); }
.kpi.hero { background:var(--brand); border-color:var(--brand); }
.kpi.hero .l, .kpi.hero .s { color:rgba(255,255,255,.8); }
.kpi.hero .v { color:#fff; }
.kpi.hero .bar { background:rgba(255,255,255,.28); }
.kpi.hero .bar span { background:#fff; }

/* day cards */
.dayrow { display:grid; grid-template-columns:repeat(7,1fr); gap:12px; }
.daycard { background:var(--card); border:1px solid var(--line); border-radius:16px; padding:14px 6px; text-align:center; }
.daycard.today { border-color:var(--brand); box-shadow:0 0 0 1px var(--brand); }
.daycard .dn { font-weight:600; font-size:.85rem; color:var(--ink); }
.daycard .dd { font-size:.7rem; color:#9CA3AF; }
.daycard .dv { font-size:1.25rem; font-weight:700; color:var(--ink); margin-top:4px; }
.daycard .ds { display:inline-block; margin-top:4px; padding:1px 9px; border-radius:99px; font-size:.68rem; font-weight:600;
               color:var(--c); background:color-mix(in srgb, var(--c) 12%, white); }
@media (max-width:760px){ .dayrow { grid-template-columns:repeat(4,1fr); } }

.empty { background:var(--card); border:1px dashed #D1D5DB; border-radius:16px; padding:32px; text-align:center; color:var(--mute); }
.empty b { color:var(--ink); font-size:1.02rem; }

/* sidebar */
section[data-testid="stSidebar"] { background:#F1F3FF; border-right:1px solid #E0E7FF; }
.brand { font-size:1.2rem; font-weight:700; color:var(--brand); }
.brand-sub { font-size:.74rem; color:var(--mute); margin-bottom:1rem; }
.userchip { display:flex; align-items:center; gap:10px; padding:10px 12px; border-radius:14px; margin:.2rem 0 1.2rem;
            background:#fff; border:1px solid #E0E7FF; }
.avatar { width:34px; height:34px; border-radius:50%; display:flex; align-items:center; justify-content:center;
          color:#fff; font-weight:600; font-size:.85rem; background:var(--brand); }
.userchip .n { font-weight:600; font-size:.88rem; line-height:1.1; color:var(--ink); }
.userchip .r { font-size:.7rem; color:var(--mute); }
section[data-testid="stSidebar"] div[role="radiogroup"] { gap:4px; }
section[data-testid="stSidebar"] div[role="radiogroup"] label p { color:#334155; }
section[data-testid="stSidebar"] div[role="radiogroup"] label { padding:10px 12px; border-radius:10px; width:100%; cursor:pointer; }
section[data-testid="stSidebar"] div[role="radiogroup"] label:hover:not([data-selected="true"]) { background:#E0E7FF; }
section[data-testid="stSidebar"] label[data-testid="stRadioOption"] > div > div:first-child { display:none; }
section[data-testid="stSidebar"] label[data-testid="stRadioOption"][data-selected="true"] { background:#4F46E5; }
section[data-testid="stSidebar"] div[role="radiogroup"] label[data-testid="stRadioOption"][data-selected="true"] p { color:#fff !important; font-weight:600; }

/* controls */
.stButton > button, .stDownloadButton > button { border-radius:10px; font-weight:600; }
.stButton > button[kind="primary"], .stDownloadButton > button[kind="primary"],
.stFormSubmitButton > button[kind="primary"] { background:var(--brand); border-color:var(--brand); color:#fff; }
.stButton > button[kind="primary"]:hover, .stFormSubmitButton > button[kind="primary"]:hover
  { background:var(--brand-dark); border-color:var(--brand-dark); color:#fff; }
.stButton > button:not([kind="primary"]) { background:#fff; border-color:var(--line); color:var(--ink); }
.stButton > button:not([kind="primary"]):hover { border-color:var(--brand); color:var(--brand); background:#fff; }
div[data-testid="stDataFrame"], div[data-testid="stDataEditor"] { border:1px solid var(--line); border-radius:16px; overflow:hidden; background:#fff; }
.stTabs [data-baseweb="tab"] { font-weight:600; }
.stTabs [aria-selected="true"] { color:var(--brand); }
.stTabs [data-baseweb="tab-highlight"] { background-color:var(--brand); }
div[data-testid="stVerticalBlockBorderWrapper"] { border-radius:16px; }
div[data-testid="stExpander"] { background:#fff; border-radius:16px; }
div[data-testid="stAlert"] { border-radius:12px; }
.stCaption, [data-testid="stCaptionContainer"] { color:var(--mute); }

/* tinted summary cards */
.kpi.t-purple { background:#F1EEFF; border-color:#DDD6FE; } .kpi.t-purple .v { color:#4F46E5; }
.kpi.t-green  { background:#E8F8EE; border-color:#BBF7D0; } .kpi.t-green .v  { color:#16A34A; }
.kpi.t-orange { background:#FFF4E5; border-color:#FED7AA; } .kpi.t-orange .v { color:#D97706; }
.kpi.t-green .bar, .kpi.t-orange .bar { background:rgba(255,255,255,.7); }
.kpi.t-orange .bar span { background:#F59E0B; }
.kpi.plain .v { color:var(--ink); }
.kpi .list { margin-top:6px; font-size:.82rem; color:var(--ink); line-height:1.55; }
.kpi .list b { color:#EF4444; font-weight:600; }
.kpi .big { font-size:1.15rem; font-weight:700; color:var(--ink); line-height:1.3; margin-top:8px; }

/* weekly check-in grid */
.gh { text-align:center; font-size:.72rem; color:var(--mute); font-weight:600; line-height:1.2; }
.gh b { display:block; font-size:1.05rem; color:var(--ink); }
.gh.today b { color:#0284C7; }
.gh.today { color:#0284C7; }
.hname { font-size:.9rem; font-weight:600; color:var(--ink); }
.hname span { display:block; font-size:.72rem; font-weight:500; color:var(--mute); }
[class*="st-key-chk-"] { border-radius:10px; padding:8px 0; display:flex; justify-content:center; min-height:40px; }
[class*="st-key-chk-missed"]  { background:#FEF2F2; }
[class*="st-key-chk-pending"] { background:#F1F5F9; }
[class*="st-key-chk-today"]   { background:#E0F2FE; }
[class*="st-key-chk-"]:has(input:checked) { background:#DCFCE7 !important; }
[class*="st-key-chk-"] label[data-selected="true"] > div:first-of-type { background-color:#16A34A !important; border-color:#16A34A !important; }
[class*="st-key-chk-"] { width:100% !important; }
.glegend { display:flex; gap:16px; flex-wrap:wrap; font-size:.75rem; color:var(--mute); margin-top:.6rem; }
.glegend i { display:inline-block; width:11px; height:11px; border-radius:3px; margin-right:5px; vertical-align:-1px; }

/* consistency table */
.ptable { background:#fff; border:1px solid var(--line); border-radius:16px; padding:6px 20px; }
.prow { display:grid; grid-template-columns:2.2fr .7fr 2.2fr .7fr 2.6fr; gap:14px; align-items:center;
        padding:13px 0; border-bottom:1px solid #F0F1F6; font-size:.88rem; }
.prow:last-child { border-bottom:0; }
.prow.head { font-size:.72rem; font-weight:600; color:var(--mute); text-transform:uppercase; letter-spacing:.05em; padding:12px 0; }
.prow .nm { font-weight:600; color:var(--ink); } .prow .cue { color:var(--mute); font-size:.82rem; }
.pbar { height:9px; border-radius:99px; background:#EEF0F5; } .pbar span { display:block; height:100%; border-radius:99px; }
.prow .pc { font-weight:700; }

/* login page */
.login-hero { text-align:center; margin-bottom:1.4rem; }
.login-logo { width:58px; height:58px; margin:0 auto 14px; border-radius:16px; background:var(--brand);
              color:#fff; display:flex; align-items:center; justify-content:center; font-size:1.7rem; font-weight:700;
              box-shadow:0 8px 20px rgba(79,70,229,.30); }
.login-hero .t { font-size:1.8rem; font-weight:700; color:var(--ink); letter-spacing:-.02em; }
.login-hero .s { font-size:.95rem; color:var(--mute); margin-top:4px; }
.st-key-authcard { background:#fff; border:1px solid var(--line) !important; border-radius:18px;
    box-shadow:0 10px 30px rgba(17,24,39,.06); padding:.4rem .3rem; }
.login-band { position:fixed; top:0; left:0; right:0; height:5px; background:var(--brand); z-index:999; }
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


def kpi(label, value, sub="", progress=None, tone="", hero=False, tint="", raw=""):
    bar = ""
    if progress is not None:
        bar = f'<div class="bar"><span style="width:{min(max(progress, 0), 100):.0f}%"></span></div>'
    cls = " hero" if hero else (f" t-{tint}" if tint else "")
    body = raw or f'<div class="s {tone}">{sub}</div>{bar}'
    return f'<div class="kpi{cls}"><div class="l">{label}</div><div class="v">{value}</div>{body}</div>'


def kpi_row(items, tints=None):
    """tints=None -> first card is solid brand; tints=['purple','green','orange'] -> soft tinted cards."""
    for i, (col, item) in enumerate(zip(st.columns(len(items), gap="medium"), items)):
        label, value, sub, progress, tone = (list(item) + [None] * 5)[:5]
        col.markdown(kpi(label, value, sub or "", progress, tone or "",
                         hero=(tints is None and i == 0), tint=(tints[i] if tints else "")),
                     unsafe_allow_html=True)


def perf_color(rate):
    """Colour a habit by how consistent it was."""
    if rate <= 30:
        return BAD
    if rate <= 60:
        return "#F97316"
    if rate <= 85:
        return "#3B82F6"
    return OK


def streak_days(uid, habits, ref):
    """Consecutive days (ending at ref) with at least 80% of habits done."""
    if not habits:
        return 0
    start = ref - timedelta(days=60)
    done = db.get_done(uid, start, ref)

    def ok(d):
        return pct(sum((h["id"], d.isoformat()) in done for h in habits), len(habits)) >= 80

    d = ref
    if d == date.today() and not ok(d):   # today is still in progress
        d -= timedelta(days=1)
    s = 0
    while d >= start and ok(d):
        s += 1
        d -= timedelta(days=1)
    return s


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
    page_header(f"Hello, {username}", f"Dashboard &nbsp;·&nbsp; week of {days[0]:%d %b} – {days[-1]:%d %b %Y}")

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

    # ---- highlights
    habit_days = [(h["name"], sum((h["id"], d.isoformat()) in done for d in days)) for h in habits]
    best = max(habit_days, key=lambda x: x[1])
    weakest = sorted(habit_days, key=lambda x: x[1])[:3]
    ti = days.index(ref)
    today_rate = pct(day_counts[ti], n)
    stk = streak_days(uid, habits, ref)
    section("Highlights")
    c1, c2, c3, c4 = st.columns(4, gap="medium")
    c1.markdown(kpi("Today's focus", f"{today_rate:.0f}%", f"{day_counts[ti]} of {n} habits completed",
                    today_rate, tint="purple"), unsafe_allow_html=True)
    c2.markdown(kpi("Weekly streak", f"{stk} day{'s' if stk != 1 else ''}",
                    "Consecutive days with 80%+ done", None, tint="orange"), unsafe_allow_html=True)
    c3.markdown(kpi("Best habit", "", tint="green",
                    raw=f'<div class="big">{best[0] if best[1] else "—"}</div>'
                        f'<div class="s">{best[1]} of 7 days this week</div>'), unsafe_allow_html=True)
    lst = "<br>".join(f"{nm} &nbsp;<b>{d}/7</b>" for nm, d in weakest)
    c4.markdown(kpi("Needs attention", "", raw=f'<div class="list">{lst}</div>'), unsafe_allow_html=True)

    section("This week")
    day_cards(days, day_counts, n)

    left, right = st.columns(2, gap="large")
    rates = [pct(c, n) for c in day_counts]
    with left:
        section("Weekly performance")
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
        goal = alt.Chart(pd.DataFrame({"y": [80]})).mark_rule(strokeDash=[4, 4], color="#9CA3AF").encode(y="y:Q")
        trend = alt.Chart(wdf).mark_line(color=BRAND, strokeWidth=2.5, point=alt.OverlayMarkDef(color=BRAND, size=55),
                                         interpolate="monotone").encode(x=x, y="Rate:Q")
        st.altair_chart(style_chart((bars + trend + labels + goal).properties(height=290)), width="stretch")
        st.caption("Bars: daily completion (Mon–Sun), line: trend. Dashed line: 80% target. "
                   "Green ≥ 80%, amber ≥ 70%, red below.")
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
    rule = alt.Chart(pd.DataFrame({"y": [80]})).mark_rule(strokeDash=[4, 4], color="#9CA3AF").encode(y="y:Q")
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
    n = len(habits)
    days_done = [sum((h["id"], d.isoformat()) in done for d in days) for h in habits]
    day_counts = [sum((h["id"], d.isoformat()) in done for h in habits) for d in days]
    avg = pct(sum(days_done), n * 7)
    perfect = sum(d == 7 for d in days_done)
    kpi_row([
        ("Total habits", n, "Active habits"),
        ("Consistency", f"{avg:.0f}%", "Weekly average", avg),
        ("Perfect", f"{perfect}/{n}", "All 7 days", pct(perfect, n)),
    ], tints=["purple", "green", "orange"])

    section("Weekly check-in")
    today = date.today()

    def toggle(hid, day, key):
        db.set_log(uid, hid, day, st.session_state[key])

    with st.container(border=True):
        cols = st.columns([2.6] + [1] * 7, gap="small", vertical_alignment="center")
        cols[0].markdown('<div class="gh" style="text-align:left">HABIT</div>', unsafe_allow_html=True)
        for j, d in enumerate(days):
            cls = " today" if d == today else ""
            cols[j + 1].markdown(f'<div class="gh{cls}">{DAYS[j]}<b>{d.day}</b></div>', unsafe_allow_html=True)
        for i, h in enumerate(habits):
            cols = st.columns([2.6] + [1] * 7, gap="small", vertical_alignment="center")
            cols[0].markdown(f'<div class="hname">{h["name"]}<span>{h["category"] or "Other"} · {days_done[i]}/7 days</span></div>',
                             unsafe_allow_html=True)
            for j, d in enumerate(days):
                state = "today" if d == today else ("missed" if d < today else "pending")
                key = f"chk-{state}-d{j}-h{h['id']}-{wk}"
                cols[j + 1].checkbox(f"{h['name']} {d}", value=(h["id"], d.isoformat()) in done, key=key,
                                     label_visibility="collapsed", on_change=toggle, args=(h["id"], d, key))
    st.markdown(
        '<div class="glegend"><span><i style="background:#DCFCE7;border:1px solid #16A34A"></i>Completed</span>'
        '<span><i style="background:#FEF2F2;border:1px solid #FCA5A5"></i>Missed</span>'
        '<span><i style="background:#F1F5F9;border:1px solid #CBD5E1"></i>Upcoming</span>'
        '<span><i style="background:#E0F2FE;border:1px solid #7DD3FC"></i>Today</span></div>',
        unsafe_allow_html=True)

    section("Consistency by habit")
    rows = ['<div class="prow head"><div>Habit</div><div>Days</div><div>Progress</div><div>%</div><div>Cue / Note</div></div>']
    for h, dd in zip(habits, days_done):
        r = pct(dd, 7)
        c = perf_color(r)
        rows.append(f'<div class="prow"><div class="nm">{h["name"]}</div><div>{dd}/7</div>'
                    f'<div class="pbar"><span style="width:{r:.0f}%;background:{c}"></span></div>'
                    f'<div class="pc" style="color:{c}">{r:.0f}%</div><div class="cue">{h["cue"] or ""}</div></div>')
    st.markdown(f'<div class="ptable">{"".join(rows)}</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="glegend"><span><i style="background:#EF4444"></i>0–30% Red</span>'
        '<span><i style="background:#F97316"></i>31–60% Orange</span>'
        '<span><i style="background:#3B82F6"></i>61–85% Blue</span>'
        '<span><i style="background:#16A34A"></i>86–100% Green</span></div>', unsafe_allow_html=True)

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
