"""
Mouse finder.   Run:  streamlit run app.py

Hand size -> grip (or "not sure") -> budget -> results in tabs: top matches, charts, full list,
dataset documentation, and an explanation of the score. Logic lives in core.py.
Prices: prices.csv / fetch_prices.py.
Exact retailer pages: links.csv.
"""
import html

import altair as alt
import pandas as pd
import streamlit as st

import core

st.set_page_config(page_title="Mouse finder", layout="wide")
S = st.session_state

CSS = r"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
:root { --ink:#232C33; --ink2:#4A5560; --bg:#232C33; --surf:#2B363F; --surf2:#313E48; --teal:#5A7D7C; --blue:#A0C1D1; --lav:#B5B2C2; --ice:#DADFF7; }
html, body, .stApp, .stApp button, .stApp input, .stApp label { font-family: 'Inter', system-ui, -apple-system, 'Segoe UI', sans-serif; }
.block-container { max-width: 1180px; padding-top: 4.5rem; }
footer, #MainMenu { visibility: hidden; }
.mf-step { color: var(--teal); font-size: .72rem; font-weight: 700; letter-spacing: .14em; }
.mf-q { font-size: 2rem; font-weight: 800; letter-spacing: -.02em; margin: .3rem 0 .4rem; color: var(--ink); }
.mf-sub { color: var(--ink2); margin: 0 0 1.2rem; max-width: 52ch; }
.mf-head { display: flex; justify-content: space-between; color: var(--teal); font-size: .7rem; font-weight: 700; letter-spacing: .14em; margin: 1.2rem 0 .7rem; padding-bottom: .5rem; border-bottom: 1px solid var(--teal); }
.mf-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 14px; margin-bottom: 16px; align-items: stretch; }
.mf-card { display: flex; flex-direction: column; background: var(--surf); border: 1px solid var(--teal); border-radius: 0; padding: 18px; color: var(--ice); }
.mf-hero { border: 2px solid var(--blue); }
.mf-card .mf-brand { color: var(--blue); }
.mf-top { display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px; }
.mf-tag { padding: 4px 10px; font-size: .66rem; font-weight: 800; letter-spacing: .12em; text-transform: uppercase; background: var(--lav); color: var(--bg); }
.mf-hero .mf-tag { background: var(--ice); }
.mf-rank { font-size: 1.5rem; font-weight: 800; color: var(--teal); line-height: 1; }
.mf-hero .mf-rank { color: var(--blue); }
.mf-brand { color: var(--teal); font-size: .7rem; font-weight: 700; letter-spacing: .14em; text-transform: uppercase; }
.mf-name { font-size: 1.45rem; font-weight: 800; letter-spacing: -.02em; line-height: 1.15; margin: .25rem 0 .9rem; color: var(--ice); }
.mf-tiles { display: grid; grid-template-columns: repeat(3, 1fr); gap: 6px; margin-bottom: 12px; }
.mf-tile { background: var(--bg); border: 1px solid var(--teal); border-radius: 0; padding: 10px 6px; min-height: 64px; display: flex; flex-direction: column; justify-content: center; align-items: center; text-align: center; }
.mf-tile b { font-size: .92rem; font-weight: 800; color: var(--ice); line-height: 1.15; }
.mf-tile span { font-size: .6rem; font-weight: 700; letter-spacing: .12em; color: var(--blue); margin-top: 4px; }
.mf-id { display: flex; justify-content: space-between; align-items: flex-start; gap: 10px; }
.mf-icon { width: 64px; height: 64px; flex: none; object-fit: cover; border: 1px solid var(--teal); border-radius: 0; background: #fff; }
.mf-badges { display: flex; flex-wrap: wrap; gap: 6px; margin: 0 0 12px; }
.mf-shape { padding: 3px 9px; font-size: .68rem; font-weight: 700; letter-spacing: .08em; text-transform: uppercase; border: 1px solid var(--blue); color: var(--blue); }
.mf-ergonomic { background: var(--lav); border-color: var(--lav); color: var(--bg); }
.mf-hybrid { border-color: var(--lav); color: var(--lav); }
.mf-high { padding: 3px 9px; font-size: .68rem; font-weight: 700; letter-spacing: .08em; text-transform: uppercase; border: 1px solid var(--lav); color: var(--lav); }
.mf-edit { padding: 3px 9px; font-size: .68rem; font-weight: 700; letter-spacing: .08em; text-transform: uppercase; background: var(--teal); color: var(--ice); }
.mf-desc { color: var(--lav); font-size: .86rem; margin: 0 0 12px; }
.mf-why-k { color: var(--blue); font-size: .66rem; font-weight: 800; letter-spacing: .14em; }
.mf-list { margin: .4rem 0 .9rem; padding: 0; list-style: none; }
.mf-list li { color: var(--ice); font-size: .82rem; padding: 2px 0 2px 18px; position: relative; }
.mf-list li::before { content: ""; position: absolute; left: 0; top: .62em; width: 7px; height: 7px; background: var(--blue); }
.mf-spacer { flex: 1; }
.mf-price { font-size: 1.35rem; font-weight: 800; color: var(--ice); margin: 4px 0 10px; }
.mf-price small { font-size: .76rem; font-weight: 500; color: var(--lav); margin-left: 4px; }
.mf-warn { color: var(--ice); background: var(--teal); display: inline-block; padding: 2px 8px; font-size: .72rem; font-weight: 700; margin: -4px 0 10px; }
.mf-actions { display: flex; flex-direction: column; gap: 8px; }
.mf-btn { display: block; text-align: center; padding: 11px 12px; border-radius: 0; font-size: .85rem; font-weight: 700; text-decoration: none !important; color: var(--ice) !important; background: transparent; border: 1px solid var(--teal); }
.mf-btn:hover { background: var(--surf2); border-color: var(--blue); }
.mf-primary { background: var(--blue); border-color: var(--blue); color: var(--bg) !important; }
.mf-primary:hover { background: var(--ice); border-color: var(--ice); }
.mf-details { border: 1px solid var(--teal); border-radius: 0; background: var(--bg); }
.mf-details summary { cursor: pointer; padding: 10px 12px; text-align: center; font-size: .85rem; font-weight: 700; color: var(--ice); list-style: none; }
.mf-details summary::-webkit-details-marker { display: none; }
.mf-table { width: 100%; border-collapse: collapse; font-size: .78rem; margin: 0 0 6px; }
.mf-table td { padding: 6px 10px; border-top: 1px solid var(--surf2); color: var(--ice); }
.mf-table td:first-child { color: var(--blue); }
.mf-table td:last-child { text-align: right; color: var(--lav); }
@media (max-width: 900px) { .mf-grid { grid-template-columns: 1fr; } }
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

WEIGHT_HELP = ("Ultralight shows only mice up to 50 g. Light shows only mice from 51 to 65 g. "
               "Don't mind shows every weight (up to the max weight).")
SHAPE_CHOICES = ["Any", "Symmetrical", "Ergonomic"]
SHAPE_HELP = ("Symmetrical mice work for either hand. Ergonomic mice are sculpted for one hand. "
              "Hybrid mice are included in both choices.")
GRIP_CHOICES = list(core.GRIPS) + ["Not sure"]
GRIP_CAPTIONS = [g["blurb"] for g in core.GRIPS.values()] + [
    "We'll show mice with universal shapes that work for any grip, picked for your hand size."]

# ----------------------------------------------------------------------------
# State. S.P holds every answer. Streamlit forgets a widget's value when the widget
# isn't drawn on a step, so widgets are re-seeded from P (bind) and saved back (keep).
# ----------------------------------------------------------------------------
if "P" not in S:
    S.P = dict(
        w_grip=None, w_len=18.5, w_wid=8.5, w_budget=70, w_hand="Right", w_conn="Any",
        w_shape="Any", w_maxw=100, w_wpref="Don't mind", w_recency="Medium",
        w_perbrand=2, w_list=False, w_rows=15, p_editor=core.EDITOR_POINTS, p_highly=core.HIGHLY_POINTS,
        **{f"s_{t}": v[0] for t, v in core.TIER_DEFAULTS.items()},
        **{f"p_{t}": v[1] for t, v in core.TIER_DEFAULTS.items()},
    )
    S.step = 1
P = S.P


def bind(*keys):
    for k in keys:
        if k not in S:
            S[k] = P[k]


def keep(*keys):
    for k in keys:
        if S.get(k) is not None:
            P[k] = S[k]


def restore(key):
    """Segmented controls can be deselected; put the last choice back."""
    if S.get(key) is None:
        S[key] = P[key]


def sync():
    """Save every live widget value. Button callbacks run before the script body, so a value
    typed just before clicking Next would otherwise be lost."""
    for k in list(P):
        if k.startswith(("w_", "s_", "p_")) and S.get(k) is not None:
            P[k] = S[k]


def go(step):
    sync()
    S.step = step


def set_hand(length, width):
    S.w_len, S.w_wid = length, width


def start_over():
    S.clear()


@st.cache_data
def base_db():
    return core.load_db()


def tier_config():
    return {t: (P[f"s_{t}"], P[f"p_{t}"]) for t in core.TIER_DEFAULTS}


def get_db():
    prices = core.read_prices(core.PRICES_PATH) if core.PRICES_PATH.exists() else None
    return core.apply_prices(base_db(), prices)


def eligible_pool(db):
    hands = {"Right": ["Right", "Ambidextrous"], "Left": ["Left", "Ambidextrous"]}[P["w_hand"]]
    pool = db[db["Hand compatibility"].isin(hands) & (db["Weight (grams)"] <= P["w_maxw"])
              & core.weight_ok(db, P["w_wpref"])]
    if P["w_conn"] != "Any":
        pool = pool[pool["Connectivity"] == P["w_conn"]]
    if P["w_shape"] != "Any":
        pool = pool[pool["Shape"].isin([P["w_shape"], "Hybrid"])]
    return pool


def run_recommend(n=40, per_brand=None):
    """(scored pool, recommendations). 'Not sure' returns the curated universal picks for the hand size."""
    pool = eligible_pool(get_db())
    L, W = P["w_len"] * 10, P["w_wid"] * 10
    if P["w_grip"] == "Not sure":
        recs = core.universal_picks(pool, L, W, tier_config(), P["w_wpref"], P["w_recency"], P["p_editor"],
                                   P["p_highly"])
        return recs, recs
    sc = core.score(pool, P["w_grip"], L, W, tier_config(), P["w_wpref"], P["w_recency"], P["p_editor"],
                   budget=P["w_budget"], highly_pts=P["p_highly"])
    recs = core.recommend(sc, P["w_budget"], tier_config(), per_brand or P["w_perbrand"], n)
    return sc, recs


def centered():
    _, mid, _ = st.columns([1, 2, 1])
    return mid


def step_head(n, title, sub):
    st.markdown(f'<div class="mf-step">STEP {n} OF 3</div><h1 class="mf-q">{title}</h1>'
                f'<p class="mf-sub">{sub}</p>', unsafe_allow_html=True)


# ----------------------------------------------------------------------------
# Steps
# ----------------------------------------------------------------------------
def step_hand():
    with centered():
        st.markdown('<div class="mf-brand">MOUSE FINDER</div>'
                    f'<p class="mf-sub">Match your hand and grip against the measured size and shape of '
                    f'{len(base_db()):,} gaming mice, then see the best fits for your budget.</p>',
                    unsafe_allow_html=True)
        step_head(1, "How big is your hand?",
                  "Length: wrist crease to the tip of your middle finger, hand flat. "
                  "Width: across the knuckles, thumb not included.")
        bind("w_len", "w_wid")
        a, b = st.columns(2)
        a.number_input("Length (cm)", 13.0, 25.0, step=0.1, key="w_len")
        b.number_input("Width (cm)", 6.0, 12.5, step=0.1, key="w_wid")
        keep("w_len", "w_wid")
        ratio = S.w_wid / S.w_len
        if not 0.40 <= ratio <= 0.54:
            st.warning("Your width looks unusual for your length. Measure across the knuckles "
                       "without the thumb (usually 8 to 9 cm for a 17 to 19 cm hand) and check "
                       "both numbers.")
        st.caption("No ruler handy? Pick the closest size:")
        for col, (name, (ln, wd)) in zip(st.columns(3), core.HAND_PRESETS.items()):
            col.button(f"{name} ({ln:g} x {wd:g})", key=f"hp_{name}", on_click=set_hand,
                       args=(ln, wd), width="stretch")
        st.write("")
        st.button("Next", type="primary", on_click=go, args=(2,))
    guide = core.IMAGES_DIR / "ui" / "hand_measure.webp"
    if guide.exists():
        with st.expander("How to measure your hand", expanded=True):
            st.image(str(guide), width="stretch")


def step_grip():
    with centered():
        step_head(2, "How do you hold your mouse?", "Pick the grip that feels closest to yours.")
        bind("w_grip")
        st.radio("Grip style", GRIP_CHOICES, index=None, key="w_grip", captions=GRIP_CAPTIONS,
                 label_visibility="collapsed")
        keep("w_grip")
        if S.w_grip == "Not sure":
            st.caption(f"Hand size bracket: {core.hand_bracket(P['w_len'] * 10)}. "
                       "The universal picks are chosen for this bracket.")
        elif S.w_grip:
            t = core.targets(S.w_grip, P["w_len"] * 10, P["w_wid"] * 10)
            st.caption(f"For your hand, look for a mouse about {t['length']:.0f} mm long "
                       f"and {t['width']:.0f} mm wide.")
        a, b, _ = st.columns([1, 1, 3])
        a.button("Back", on_click=go, args=(1,))
        b.button("Next", type="primary", on_click=go, args=(3,), disabled=not S.w_grip)
    guide = core.IMAGES_DIR / "ui" / "grip_visual.webp"
    if guide.exists():
        with st.expander("What each grip looks like", expanded=True):
            st.image(str(guide), width="stretch")


def step_budget():
    with centered():
        step_head(3, "What's your budget?", "We only suggest mice that fit your hand and your price range.")
        bind("w_budget", "w_hand", "w_conn", "w_shape", "w_wpref")
        st.slider("Budget (USD)", 15, 250, step=5, key="w_budget")
        caps = core.budget_caps(S.w_budget, tier_config())
        st.caption(f"Top-tier brands can be suggested up to ${caps['Top']}, "
                   f"mid-tier brands up to ${caps['Mid']}, everything else up to ${caps['Other']}.")
        st.segmented_control("Hand", ["Right", "Left"], key="w_hand", on_change=restore, args=("w_hand",))
        st.segmented_control("Connection", ["Any", "Wireless", "Wired"], key="w_conn",
                             on_change=restore, args=("w_conn",))
        st.segmented_control("Shape preference", SHAPE_CHOICES, key="w_shape", on_change=restore,
                             args=("w_shape",), format_func=lambda x: "No preference" if x == "Any" else x,
                             help=SHAPE_HELP)
        st.segmented_control("Weight", list(core.WEIGHT_POINTS), key="w_wpref",
                             on_change=restore, args=("w_wpref",), help=WEIGHT_HELP)
        keep("w_budget", "w_hand", "w_conn", "w_shape", "w_wpref")
        _, recs = run_recommend(n=999, per_brand=999)
        st.caption(f"{len(recs)} mice match so far.")
        a, b, _ = st.columns([1, 2, 2])
        a.button("Back", on_click=go, args=(2,))
        b.button("Show recommendations", type="primary", on_click=go, args=("results",))


# ----------------------------------------------------------------------------
# Result cards (HTML kept on one line: blank lines or indents would break Markdown's HTML block)
# ----------------------------------------------------------------------------
def e(x):
    return html.escape(str(x))


def price_block(r):
    over = '<div class="mf-warn">Above your budget</div>' if r["Price"] > P["w_budget"] else ""
    if r["Price source"] == "verified":
        where = f" at {e(r['Price where'])}" if r.get("Price where") else ""
        return f'<div class="mf-price">${r["Price"]:,.2f}<small>{where.strip()}</small></div>{over}'
    return f'<div class="mf-price">~${r["Price"]:.0f}<small>estimate</small></div>{over}'


def buttons(name):
    links = core.retailer_links(name)
    (mg, mg_exact), (az, az_exact) = links["maxgaming"], links["amazon"]
    a = 'target="_blank" rel="noopener noreferrer"'
    return (f'<a class="mf-btn mf-primary" href="{e(mg)}" {a}>'
            f'{"View price on MaxGaming" if mg_exact else "Search MaxGaming"} &#8599;</a>'
            f'<a class="mf-btn" href="{e(az)}" {a}>{"Also at Amazon" if az_exact else "Search Amazon"} &#8599;</a>')


def fit_details(r):
    t = core.targets(P["w_grip"], P["w_len"] * 10, P["w_wid"] * 10)
    pts = tier_config()[r["Tier"]][1]
    sensor = r["Sensor"] if isinstance(r["Sensor"], str) else "Unknown"
    rows = [
        ("Length", f'{r["Length (mm)"]:.0f} mm', f'ideal ~{t["length"]:.0f}'),
        ("Width", f'{r["Width (mm)"]:.0f} mm', f'ideal ~{t["width"]:.0f}'),
        ("Height", f'{r["Height (mm)"]:.0f} mm', f'ideal ~{t["height"]:.0f}'),
        ("Weight", f'{r["Weight (grams)"]:.0f} g', ""),
        ("Shape", r["Shape"], f'{r["Hump placement"].replace(" - ", ", ").lower()} hump'),
        ("Sensor", sensor, f'{r["Polling rate (Hz)"]:.0f} Hz'),
        ("Brand tier", core.TIER_LABEL[r["Tier"]], f"{pts:+d} pts" if pts else ""),
    ]
    body = "".join(f"<tr><td>{e(a)}</td><td>{e(b)}</td><td>{e(c)}</td></tr>" for a, b, c in rows)
    return (f'<details class="mf-details"><summary>Fit details</summary>'
            f'<table class="mf-table">{body}</table></details>')


def tile(value, label):
    return f'<div class="mf-tile"><b>{e(value)}</b><span>{e(label)}</span></div>'


def card(r, rank, universal):
    brand, model = core.split_name(r["Name"], r["Brand"])
    label = {1: "Best match", 2: "Second-best"}.get(rank, f"Match #{rank}")
    grip = "All" if universal else " / ".join(core.suits(r))
    tiles = tile(f'{r["Weight (grams)"]:.0f} g', core.weight_class(r["Weight (grams)"]).upper()) + tile(r["Connectivity"], "CONNECTION") + tile(grip, "GRIP")
    shape = str(r["Shape"])
    badges = f'<span class="mf-shape mf-{e(shape.lower())}">{e(shape)}</span>'
    if r["Editor"]:
        badges += '<span class="mf-edit">Editor\'s choice</span>'
    elif r["Highly"]:
        badges += '<span class="mf-high">Highly recommended</span>'
    icon = core.mouse_icon(r["Name"])
    ident = f'<div class="mf-brand">{e(brand)}</div><div class="mf-name">{e(model)}</div>'
    if icon:
        ident = f'<div class="mf-id"><div>{ident}</div><img class="mf-icon" src="{icon}" alt=""></div>'

    why = core.why_chips(r, P["w_grip"], P["w_len"] * 10, P["w_conn"], P["w_budget"])[:3]
    items = "".join(f"<li>{e(w)}</li>" for w in why)
    cls = "mf-card mf-hero" if rank == 1 else "mf-card"
    return (f'<div class="{cls}"><div class="mf-top"><span class="mf-tag">{label}</span>'
            f'<span class="mf-rank">0{rank}</span></div>'
            f'{ident}'
            f'<div class="mf-badges">{badges}</div><div class="mf-tiles">{tiles}</div>'
            f'<p class="mf-desc">{e(core.describe(r, universal))}</p>'
            f'<div class="mf-why-k">WHY IT MATCHES</div><ul class="mf-list">{items}</ul>'
            f'<div class="mf-spacer"></div>{price_block(r)}'
            f'<div class="mf-actions">{buttons(r["Name"])}{fit_details(r)}</div></div>')


# ----------------------------------------------------------------------------
# Results
# ----------------------------------------------------------------------------
CLASS_SCALE = alt.Scale(domain=["Ultralight", "Light", "Medium", "Heavy"],
                        range=["#5A7D7C", "#7FA6BA", "#9A94B0", "#232C33"])
SHAPE_SCALE = alt.Scale(domain=["Symmetrical", "Hybrid", "Ergonomic"], range=["circle", "square", "triangle-up"])
PARTS = {"Fit": "Hand fit", "Recency": "Newer tech", "Weight bonus": "Weight", "Brand pts": "Brand",
         "Editor pts": "Award", "Grip adj": "Grip focus", "Budget adj": "Budget edge / penalty"}
PART_COLORS = ["#5A7D7C", "#A0C1D1", "#B5B2C2", "#232C33", "#E3C98B", "#8FB3A3", "#D98C8C"]


def sidebar():
    with st.sidebar:
        st.subheader("Filters")
        bind("w_budget", "w_maxw", "w_recency", "w_perbrand", "w_shape", "w_hand", "w_conn", "w_wpref")
        st.slider("Budget (USD)", 15, 250, step=5, key="w_budget")
        st.segmented_control("Hand", ["Right", "Left"], key="w_hand", on_change=restore, args=("w_hand",))
        st.segmented_control("Connection", ["Any", "Wireless", "Wired"], key="w_conn",
                             on_change=restore, args=("w_conn",))
        st.segmented_control("Shape preference", SHAPE_CHOICES, key="w_shape", on_change=restore,
                             args=("w_shape",), format_func=lambda x: "No preference" if x == "Any" else x,
                             help=SHAPE_HELP)
        st.slider("Max weight (g)", 30, 120, step=5, key="w_maxw")
        st.selectbox("Weight", list(core.WEIGHT_POINTS), key="w_wpref", help=WEIGHT_HELP)
        st.selectbox("Favor newer tech", list(core.RECENCY_POINTS), key="w_recency",
                     help="How many points a current sensor and polling rate are worth.")
        st.slider("Max results per brand", 1, 5, key="w_perbrand")
        keep("w_budget", "w_hand", "w_conn", "w_shape", "w_maxw", "w_wpref", "w_recency", "w_perbrand")

        with st.expander("Advanced: brand tiers and points"):
            keys = [f"s_{t}" for t in core.TIER_DEFAULTS] + [f"p_{t}" for t in core.TIER_DEFAULTS]
            bind(*keys, "p_editor", "p_highly")
            for t in core.TIER_DEFAULTS:
                a, b = st.columns(2)
                a.number_input(f"{core.TIER_LABEL[t]}: stretch %", 0, 50, step=5, key=f"s_{t}")
                b.number_input(f"{core.TIER_LABEL[t]}: points", -20, 20, step=1, key=f"p_{t}")
            st.number_input("Editor's choice bonus", 0, 30, step=1, key="p_editor")
            st.number_input("Highly recommended bonus", 0, 30, step=1, key="p_highly")
            st.caption("Stretch lets a tier be suggested a little above your budget.")
            keep(*keys, "p_editor", "p_highly")


def chart_data(recs):
    d = recs.copy()
    d["Class"] = d["Weight (grams)"].map(core.weight_class)
    return d.rename(columns={"Length (mm)": "Length", "Width (mm)": "Width", "Weight (grams)": "Weight"})


def chart_fit_map(recs, target):
    d = chart_data(recs)
    tip = ["Name", "Shape", alt.Tooltip("Length:Q", format=".0f"), alt.Tooltip("Width:Q", format=".0f"),
           alt.Tooltip("Weight:Q", format=".0f"), alt.Tooltip("Price:Q", format="$.0f"),
           alt.Tooltip("Score:Q", format=".0f")]
    pts = alt.Chart(d).mark_point(filled=True, opacity=.9, stroke="#FFFFFF", strokeWidth=1).encode(
        x=alt.X("Length:Q", title="Length (mm)", scale=alt.Scale(zero=False, padding=12)),
        y=alt.Y("Width:Q", title="Width (mm)", scale=alt.Scale(zero=False, padding=12)),
        size=alt.Size("Score:Q", scale=alt.Scale(range=[70, 420]), legend=None),
        color=alt.Color("Class:N", scale=CLASS_SCALE, legend=alt.Legend(title="Weight class")),
        shape=alt.Shape("Shape:N", scale=SHAPE_SCALE, legend=alt.Legend(title="Shape")), tooltip=tip)
    ideal = alt.Chart(pd.DataFrame({"Length": [target["length"]], "Width": [target["width"]],
                                    "Name": ["Ideal size for your hand"]})
                      ).mark_point(shape="cross", size=380, filled=True, color="#232C33"
                                   ).encode(x="Length:Q", y="Width:Q", tooltip=["Name"])
    return (pts + ideal).properties(height=340).interactive()


def chart_value(recs, budget):
    d = chart_data(recs)
    pts = alt.Chart(d).mark_point(filled=True, size=120, opacity=.9, stroke="#FFFFFF", strokeWidth=1).encode(
        x=alt.X("Price:Q", title="Price (USD)", scale=alt.Scale(zero=False)),
        y=alt.Y("Score:Q", title="Match score", scale=alt.Scale(zero=False)),
        color=alt.Color("Class:N", scale=CLASS_SCALE, legend=alt.Legend(title="Weight class")),
        shape=alt.Shape("Shape:N", scale=SHAPE_SCALE, legend=alt.Legend(title="Shape")),
        tooltip=["Name", "Shape", alt.Tooltip("Price:Q", format="$.0f"), alt.Tooltip("Score:Q", format=".0f"),
                 alt.Tooltip("Weight:Q", format=".0f")])
    rule = alt.Chart(pd.DataFrame({"Budget": [budget]})).mark_rule(strokeDash=[5, 4], color="#5A7D7C"
                                                                     ).encode(x="Budget:Q")
    return (pts + rule).properties(height=340).interactive()


def chart_breakdown(recs, n=8):
    top = recs.head(n)
    rows = [{"Mouse": r["Name"], "Part": label, "Points": float(r[col])}
            for _, r in top.iterrows() for col, label in PARTS.items()]
    return alt.Chart(pd.DataFrame(rows)).mark_bar().encode(
        y=alt.Y("Mouse:N", sort=list(top["Name"]), title=None),
        x=alt.X("sum(Points):Q", title="Points"),
        color=alt.Color("Part:N", scale=alt.Scale(domain=list(PARTS.values()), range=PART_COLORS),
                        legend=alt.Legend(title=None, orient="bottom")),
        tooltip=["Mouse", "Part", alt.Tooltip("Points:Q", format=".1f")]
    ).properties(height=34 * len(top) + 60)


def chart_weight_classes(db):
    order = ["Ultralight", "Light", "Medium", "Heavy"]
    d = db["Weight (grams)"].map(core.weight_class).value_counts().reindex(order, fill_value=0)
    d = pd.DataFrame({"Class": d.index, "Mice": d.values})
    return alt.Chart(d).mark_bar().encode(
        x=alt.X("Class:N", sort=order, title=None, axis=alt.Axis(labelAngle=0)), y=alt.Y("Mice:Q"),
        color=alt.Color("Class:N", scale=CLASS_SCALE, legend=None), tooltip=["Class", "Mice"]
    ).properties(height=260)


def chart_lengths(db, target_len):
    d = db[["Length (mm)"]].rename(columns={"Length (mm)": "Length"})
    bars = alt.Chart(d).mark_bar(color="#5A7D7C").encode(
        x=alt.X("Length:Q", bin=alt.Bin(step=2), title="Length (mm)"), y=alt.Y("count()", title="Mice"))
    rule = alt.Chart(pd.DataFrame({"Ideal": [target_len]})).mark_rule(color="#232C33", strokeWidth=3
                                                                      ).encode(x="Ideal:Q")
    return (bars + rule).properties(height=260)


def insights(recs, target):
    best = recs.iloc[0]
    closest = recs.loc[(recs["Length (mm)"] - target["length"]).abs().idxmin()]
    lightest = recs.loc[recs["Weight (grams)"].idxmin()]
    cheapest = recs.loc[recs["Price"].idxmin()]
    return [
        f"**Best overall:** {best['Name']} ({best['Score']:.0f}% match, ${best['Price']:.0f}).",
        f"**Closest size to your ideal:** {closest['Name']}, {closest['Length (mm)']:.0f} mm long "
        f"against an ideal of about {target['length']:.0f} mm.",
        f"**Lightest:** {lightest['Name']} at {lightest['Weight (grams)']:.0f} g "
        f"({core.weight_class(lightest['Weight (grams)']).lower()}).",
        f"**Cheapest:** {cheapest['Name']} at about ${cheapest['Price']:.0f}.",
    ]


def tab_top(recs, universal):
    top = list(recs.head(3).iterrows())
    st.markdown('<div class="mf-head"><span>TOP MATCHES</span><span>BEST FIT FIRST</span></div>',
                unsafe_allow_html=True)
    cards = "".join(card(r, rank, universal) for rank, (_, r) in enumerate(top, start=1))
    st.markdown(f'<div class="mf-grid">{cards}</div>', unsafe_allow_html=True)


def tab_compare(recs, target, universal):
    st.markdown("##### Where the matches sit")
    for line in insights(recs, target):
        st.markdown(f"- {line}")
    a, b = st.columns(2, gap="medium")
    with a:
        st.markdown("**Size map**")
        st.altair_chart(chart_fit_map(recs, target), width="stretch")
        st.caption("The dark cross is the ideal size for your hand and grip. Closer is a better fit; "
                   "bigger dots score higher. Circles are symmetrical mice, squares hybrid, triangles ergonomic. "
                   "Drag to pan, scroll to zoom, hover for details.")
    with b:
        st.markdown("**Price vs match score**")
        st.altair_chart(chart_value(recs, P["w_budget"]), width="stretch")
        st.caption("Dashed line is your budget. Look top-left for the best value: high score, low price.")
    st.markdown("**Why the top mice rank where they do**")
    if universal:
        st.caption("Universal picks are averaged over every grip, so there is no single score breakdown.")
    else:
        st.altair_chart(chart_breakdown(recs), width="stretch")
        st.caption("Each bar adds up to the mouse's raw score: hand fit (up to 70), newer tech, weight, "
                   "brand tier, editor's choice, and the budget edge or penalty.")


def tab_list(recs):
    bind("w_rows")
    st.slider("Rows", 3, 40, key="w_rows")
    keep("w_rows")
    table = recs.head(S.w_rows)[
        ["Name", "Tier", "Award", "Score", "Price", "Price source", "Length (mm)", "Width (mm)",
         "Height (mm)", "Weight (grams)", "Shape", "Hump placement", "Sensor",
         "Polling rate (Hz)", "Connectivity"]].copy()
    table["Tier"] = table["Tier"].map(core.TIER_LABEL)
    table.index = table.index + 1
    st.dataframe(table, width="stretch", column_config={
        "Score": st.column_config.NumberColumn("Match", format="%.0f"),
        "Price": st.column_config.NumberColumn("Price (USD)", format="$%.0f"),
        "Tier": "Brand tier",
    })
    st.download_button("Download as CSV", table.to_csv().encode(), "mouse_matches.csv", "text/csv")


def tab_dataset(target):
    base = base_db()
    rep = base.attrs.get("report")
    db = get_db()
    st.markdown("##### The dataset")
    st.markdown(f"{core.DATA_SOURCE}. Each row is one mouse. The app uses its length, width, height, weight, "
                "shape, hump placement, hand compatibility, connectivity, sensor, polling rate, tracking "
                "speed and material. Prices come from `prices.csv` (verified) or a tier-based estimate.")
    if rep:
        a, b, c, d = st.columns(4)
        a.metric("Rows in file", f"{rep['raw']:,}")
        b.metric("Removed", f"{rep['outliers'] + rep['outdated'] + rep.get('excluded', 0):,}")
        c.metric("Mice used", f"{rep['kept']:,}")
        d.metric("Verified prices", f"{int((db['Price source'] == 'verified').sum()):,}")
        st.markdown("##### How the data is cleaned")
        st.markdown(
            f"1. **Types and gaps:** measurements are converted to numbers. Missing weight is filled with the "
            f"median, missing polling rate with 1000 Hz.\n"
            f"2. **Outliers:** {rep['outliers']:,} rows outside 75 to 140 mm long or 45 to 80 mm wide "
            f"(rings, trackballs, oversized devices) are dropped.\n"
            f"3. **Old tech:** {rep['outdated']:,} rows with a PAW3335, PAW3370 or older sensor, or a generic "
            f"or unlabelled one, are dropped. Editor's choice mice are always kept. "
            f"{rep.get('excluded', 0):,} superseded models (Endgame Gear OP1 and XM2 v1) are also dropped.\n"
            f"4. **Enrichment:** brand names are repaired, every mouse gets a brand tier, and a modernity "
            f"score is inferred from sensor speed and polling rate because the data has no release year.\n"
            f"5. **Prices:** merged from `prices.csv`; the rest get an estimate that is labelled as one.")
        miss = pd.DataFrame({"Column": list(rep["missing"]), "Missing in raw file": list(rep["missing"].values())})
        miss["Share"] = (miss["Missing in raw file"] / rep["raw"]).map("{:.1%}".format)
        st.markdown("##### Data quality")
        st.dataframe(miss, hide_index=True, width="stretch")
    a, b = st.columns(2, gap="medium")
    with a:
        st.markdown("**Mice by weight class**")
        st.altair_chart(chart_weight_classes(db), width="stretch")
        st.caption("Ultralight is 50 g and below, light 51 to 65 g, medium 66 to 80 g, heavy 81 g and up.")
    with b:
        st.markdown("**Mouse lengths in the dataset**")
        st.altair_chart(chart_lengths(db, target["length"]), width="stretch")
        st.caption("The dark line is the ideal length for your hand and grip.")


def tab_about(target):
    cfg = tier_config()
    st.markdown("##### Purpose")
    st.markdown("Choosing a gaming mouse is mostly a fit problem, but reviews rarely say which hands and grips "
                "a mouse suits. This app turns measured mouse dimensions into a ranked shortlist for your hand "
                "size, grip and budget, and explains every ranking.")
    st.markdown("##### How the match score works")
    st.markdown(
        f"- **Hand fit (up to 70):** length, width, height, hump position and shape against the ideal for "
        f"your grip. Your target is about {target['length']:.0f} mm long and {target['width']:.0f} mm wide. "
        f"Longer than ideal is penalized less than shorter. Poor fits are dropped.\n"
        f"- **Claw grips:** relaxed claw prefers a mid-center hump, aggressive claw a moderate to aggressive "
        f"back hump, pincer claw a shorter mouse with a moderate back hump.\n"
        f"- **Grip focus:** Endgame Gear OP1 is built for claw and fingertip, XM2 for claw and palm, LAMZU "
        f"Atlantis Mini for claw and aggressive claw. They get +{core.GRIP_FOCUS_PTS} points for those grips "
        f"and -{core.GRIP_FOCUS_PTS} for the others.\n"
        f"- **Newer tech (up to {core.RECENCY_POINTS[P['w_recency']]}):** sensor generation and polling rate.\n"
        f"- **Weight (up to {core.WEIGHT_POINTS[P['w_wpref']]}):** \"Ultralight\" shows only mice of 50 g and "
        f"below, \"Light\" only 51 to 65 g, \"Don't mind\" every weight.\n"
        f"- **Brand tier:** " + ", ".join(f"{core.TIER_LABEL[k]} {v[1]:+d}" for k, v in cfg.items())
        + f". **Editor's choice:** +{P['p_editor']}. **Highly recommended:** +{P['p_highly']}.\n"
        f"- **Budget:** a mouse is shown if its price is within your budget plus its tier's stretch "
        f"({', '.join(f'{core.TIER_LABEL[k]} ${v}' for k, v in core.budget_caps(P['w_budget'], cfg).items())}). "
        f"Going over budget costs points, and selected ATK value mice get a small edge at ${core.VALUE_BUDGET_MAX} "
        f"or less.\n"
        f"- **Not sure of your grip:** curated universal-shape mice plus any symmetrical mouse that fits palm, "
        f"claw and fingertip well, ranked by their average score.")
    st.markdown("##### Limits")
    st.markdown("Fit targets are community rules of thumb, not lab measurements. Release years are inferred from "
                "specs. Estimated prices are rough; only mice listed in `prices.csv` have checked prices.")


def step_results():
    sidebar()
    universal = P["w_grip"] == "Not sure"
    st.markdown('<h1 class="mf-q" style="font-size:1.7rem">Recommended mice</h1>', unsafe_allow_html=True)
    st.write((("Universal shapes" if universal else f"{P['w_grip']} grip")
              + f", hand {P['w_len']:.1f} x {P['w_wid']:.1f} cm, budget ${P['w_budget']}"))
    a, b, c, d, _ = st.columns([1, 1, 1, 1, 4])
    a.button("Edit hand", on_click=go, args=(1,), width="stretch")
    b.button("Edit grip", on_click=go, args=(2,), width="stretch")
    c.button("Edit budget", on_click=go, args=(3,), width="stretch")
    d.button("Start over", on_click=start_over, width="stretch")

    scored, recs = run_recommend(n=40)
    if recs.empty:
        if universal:
            st.warning("None of the universal-shape picks for your hand size pass your filters "
                       "(hand, connection, shape or weight). Loosen them in the sidebar.")
            return
        cf = core.cheapest_fit(scored)
        msg = ("Nothing fits that hand, grip and budget. Raise the budget or loosen the filters "
               "in the sidebar.")
        if cf is not None:
            msg += f" The cheapest mouse that fits is {cf['Name']}, at about ${cf['Price']:.0f}."
        st.warning(msg)
        return

    recs = core.grip_fits(recs, P["w_len"] * 10, P["w_wid"] * 10)
    target = core.targets(P["w_grip"], P["w_len"] * 10, P["w_wid"] * 10)
    n_all = len(run_recommend(n=999, per_brand=999)[1])
    m1, m2, m3 = st.columns(3)
    m1.metric("Mice that match", f"{n_all:,}")
    m2.metric("Best match score", f"{recs['Score'].iloc[0]:.0f}%")
    m3.metric("Median price of matches", f"${recs['Price'].median():.0f}")

    t_top, t_cmp, t_data, t_about = st.tabs(["Top matches", "Compare", "Dataset", "About"])
    with t_top:
        tab_top(recs, universal)
    with t_cmp:
        tab_compare(recs, target, universal)
    with t_data:
        tab_dataset(target)
    with t_about:
        tab_about(target)

    bind("w_list")
    st.toggle("Show full ranked list", key="w_list")
    keep("w_list")
    if S.w_list:
        tab_list(recs)


# ----------------------------------------------------------------------------
if S.step == "results" and not P["w_grip"]:
    S.step = 2

{1: step_hand, 2: step_grip, 3: step_budget}.get(S.step, step_results)()
