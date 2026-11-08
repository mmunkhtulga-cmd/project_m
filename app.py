"""
Mouse finder - step-by-step Streamlit app.
Run:  streamlit run app.py

Flow: hand size -> grip -> budget -> matches (full ranked list is optional).
Logic lives in core.py. Real prices: prices.csv / sidebar upload / fetch_prices.py
"""
import html
import io

import streamlit as st

import core

st.set_page_config(page_title="Mouse finder", page_icon="🖱️", layout="wide")

INK, ACCENT, MUTED = "#12161C", "#2B59FF", "#5F6B7A"

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;600;800&display=swap');
.stApp h1, .stApp h2, .stApp h3, .stApp [data-testid="stMarkdownContainer"] p,
.stApp .stButton button, .stApp label {{ font-family: 'Manrope', sans-serif; }}
.block-container {{ max-width: 1100px; padding-top: 2rem; }}
footer, #MainMenu {{ visibility: hidden; }}
div[data-testid="stVerticalBlockBorderWrapper"] {{ border-radius: 14px; background: #fff; }}
.brandmark {{ font-weight: 800; letter-spacing: -0.01em; color: {INK}; font-size: 1.05rem; }}
.stepper {{ display: flex; gap: 8px; margin: 10px 0 26px; }}
.stepper span {{ flex: 1; padding-top: 8px; border-top: 3px solid #D5DBE3; color: {MUTED};
                 font-size: .85rem; font-weight: 600; }}
.stepper span.done {{ border-color: {ACCENT}80; color: {INK}; }}
.stepper span.on {{ border-color: {ACCENT}; color: {INK}; }}
.q {{ font-size: 2.1rem; font-weight: 800; letter-spacing: -0.02em; line-height: 1.15; margin: 0 0 6px; color: {INK}; }}
.sub {{ color: {MUTED}; margin: 0 0 18px; max-width: 46ch; }}
.score {{ font-size: 2.4rem; font-weight: 800; letter-spacing: -0.03em; line-height: 1; color: {INK}; }}
.score small {{ font-size: .9rem; font-weight: 600; color: {MUTED}; margin-left: 4px; }}
.name {{ font-size: 1.12rem; font-weight: 800; line-height: 1.25; margin: 6px 0 10px; color: {INK}; }}
.price {{ font-weight: 700; color: {INK}; margin: 8px 0 12px; }}
.price small {{ color: {MUTED}; font-weight: 600; }}
.dim {{ margin: 8px 0 4px; }}
.dimlab {{ display: flex; justify-content: space-between; font-size: .8rem; color: {MUTED}; font-weight: 600; }}
.dimlab b {{ color: {INK}; }}
.track {{ position: relative; height: 8px; border-radius: 4px; background: #E3E8EE; margin-top: 4px; }}
.track .ideal {{ position: absolute; left: 39%; width: 22%; top: 0; bottom: 0; background: {ACCENT}33; border-radius: 4px; }}
.track .dot {{ position: absolute; top: -3px; width: 14px; height: 14px; margin-left: -7px; border-radius: 50%;
               background: {ACCENT}; border: 2px solid #fff; box-shadow: 0 0 0 1px {ACCENT}; }}
.legend {{ font-size: .78rem; color: {MUTED}; margin-top: 10px; }}
.reasons {{ margin: 12px 0 0; padding-left: 18px; font-size: .88rem; color: {INK}; }}
.reasons li {{ margin: 2px 0; }}
</style>
""", unsafe_allow_html=True)

S = st.session_state

# ----------------------------------------------------------------------------
# State: S.P holds every answer. Streamlit drops a widget's value when the widget
# isn't rendered on a step, so widgets are re-seeded from P (bind) and saved back (keep).
# ----------------------------------------------------------------------------
if "P" not in S:
    S.P = dict(
        grip=None, w_len=18.5, w_wid=8.5, w_budget=70, w_hand="Right", w_conn="Any",
        w_shape="Any", w_maxw=100, w_wpref="Prefer light", w_recency="Medium",
        w_dated=False, w_perbrand=2, w_list=False, w_rows=15, prices_bytes=None,
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


def go(step):
    S.step = step


def pick_grip(g):
    P["grip"] = g
    S.step = 3


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
    prices = core.read_prices(io.BytesIO(P["prices_bytes"])) if P["prices_bytes"] else None
    if prices is None and core.PRICES_PATH.exists():
        prices = core.read_prices(core.PRICES_PATH)
    return core.apply_prices(base_db(), prices)


def eligible_pool(db):
    hands = {"Right": ["Right", "Ambidextrous"], "Left": ["Left", "Ambidextrous"]}[P["w_hand"]]
    pool = db[db["Hand compatibility"].isin(hands) & (db["Weight (grams)"] <= P["w_maxw"])]
    if P["w_conn"] != "Any":
        pool = pool[pool["Connectivity"] == P["w_conn"]]
    if P["w_shape"] != "Any":
        pool = pool[pool["Shape"].isin([P["w_shape"], "Hybrid"])]
    return pool


def run_recommend(n=25, per_brand=None):
    pool = eligible_pool(get_db())
    sc = core.score(pool, P["grip"], P["w_len"] * 10, P["w_wid"] * 10, tier_config(),
                    P["w_wpref"], P["w_recency"])
    recs = core.recommend(sc, P["w_budget"], tier_config(), P["w_dated"],
                          per_brand or P["w_perbrand"], n)
    return sc, recs


# ----------------------------------------------------------------------------
# Shared UI pieces
# ----------------------------------------------------------------------------
HAND_SVG = f"""
<svg viewBox="0 0 250 270" width="100%" style="max-width:270px" xmlns="http://www.w3.org/2000/svg"
     role="img" aria-label="Measure length from the wrist crease to the middle fingertip, and width across the knuckles">
 <g fill="#E4E9EF" stroke="{INK}" stroke-width="1.6" stroke-linejoin="round">
  <rect x="64" y="52" width="21" height="86" rx="10.5"/>
  <rect x="87" y="30" width="21" height="108" rx="10.5"/>
  <rect x="110" y="46" width="21" height="92" rx="10.5"/>
  <rect x="133" y="74" width="21" height="64" rx="10.5"/>
  <rect x="20" y="150" width="24" height="76" rx="12" transform="rotate(-30 32 188)"/>
  <rect x="64" y="118" width="96" height="106" rx="24"/>
 </g>
 <line x1="46" y1="224" x2="178" y2="224" stroke="{INK}" stroke-width="1.6" stroke-dasharray="4 4"/>
 <g stroke="{ACCENT}" stroke-width="2.2" fill="none" stroke-linecap="round">
  <line x1="204" y1="30" x2="204" y2="224"/><line x1="197" y1="30" x2="211" y2="30"/><line x1="197" y1="224" x2="211" y2="224"/>
  <line x1="108" y1="30" x2="197" y2="30" stroke-width="1" stroke-dasharray="3 4"/>
  <line x1="64" y1="104" x2="160" y2="104"/><line x1="64" y1="97" x2="64" y2="111"/><line x1="160" y1="97" x2="160" y2="111"/>
 </g>
 <g fill="{ACCENT}" font-family="Manrope, sans-serif" font-size="12" font-weight="700">
  <text x="224" y="132" transform="rotate(90 224 132)" text-anchor="middle">Length</text>
  <text x="112" y="92" text-anchor="middle">Width</text>
  <text x="112" y="244" text-anchor="middle" fill="{MUTED}" font-weight="600">wrist crease</text>
 </g>
</svg>
"""


def header(step):
    labels = ["Hand", "Grip", "Budget"]
    cls = ["done" if i + 1 < step else ("on" if i + 1 == step else "") for i in range(3)]
    steps = "".join(f'<span class="{c}">{i + 1}. {l}</span>' for i, (l, c) in enumerate(zip(labels, cls)))
    st.markdown('<div class="brandmark">Mouse finder</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="stepper">{steps}</div>', unsafe_allow_html=True)


def question(title, sub):
    st.markdown(f'<p class="q">{title}</p><p class="sub">{sub}</p>', unsafe_allow_html=True)


def dim_bar(label, actual, target, span):
    lo, hi = target - span, target + span
    pos = min(max((actual - lo) / (hi - lo), 0), 1) * 100
    return (f'<div class="dim"><div class="dimlab"><span>{label}</span><b>{actual:.0f} mm</b></div>'
            f'<div class="track"><i class="ideal"></i><i class="dot" style="left:{pos:.0f}%"></i></div></div>')


# ----------------------------------------------------------------------------
# Step 1: hand
# ----------------------------------------------------------------------------
def step_hand():
    header(1)
    left, right = st.columns([3, 2], gap="large")
    with left:
        question("How big is your hand?",
                 "Mouse size depends on your hand more than anything else. Measure once and we'll do the rest.")
        bind("w_len", "w_wid")
        a, b = st.columns(2)
        a.number_input("Length (cm)", 13.0, 25.0, step=0.1, key="w_len",
                       help="Wrist crease to the tip of your middle finger, hand flat.")
        b.number_input("Width (cm)", 6.0, 12.5, step=0.1, key="w_wid",
                       help="Across the knuckles, thumb excluded.")
        keep("w_len", "w_wid")
        st.caption("Don't have a ruler? Pick the closest size.")
        cols = st.columns(3)
        for col, (name, (ln, wd)) in zip(cols, core.HAND_PRESETS.items()):
            col.button(f"{name} · {ln:g} × {wd:g}", key=f"hp_{name}", on_click=set_hand, args=(ln, wd),
                       width="stretch")
        st.write("")
        st.button("Continue", type="primary", on_click=go, args=(2,))
    with right:
        st.markdown(HAND_SVG, unsafe_allow_html=True)


# ----------------------------------------------------------------------------
# Step 2: grip
# ----------------------------------------------------------------------------
def step_grip():
    header(2)
    question("How do you hold your mouse?",
             "Most people use one of three grips. Pick the one that feels closest to yours.")
    cols = st.columns(3, gap="medium")
    for col, (name, g) in zip(cols, core.GRIPS.items()):
        t = core.targets(name, P["w_len"] * 10, P["w_wid"] * 10)
        with col, st.container(border=True):
            st.markdown(f"### {name}")
            st.write(g["blurb"])
            st.caption(f"{g['best']} For your hand, aim for about {t['length']:.0f} mm long.")
            selected = P["grip"] == name
            st.button("Selected" if selected else f"Use {name.lower()} grip", key=f"grip_{name}",
                      type="primary" if selected else "secondary", on_click=pick_grip, args=(name,),
                      width="stretch")
    with st.expander("Not sure which grip you use?"):
        st.write("Rest your hand on a mouse the way you do when you play. If your whole palm is on it, "
                 "that's palm. If your palm touches only the back and your fingers arch, that's claw. "
                 "If your palm hovers and just your fingertips touch, that's fingertip.")
    st.write("")
    st.button("Back", on_click=go, args=(1,))


# ----------------------------------------------------------------------------
# Step 3: budget
# ----------------------------------------------------------------------------
def step_budget():
    header(3)
    left, right = st.columns([3, 2], gap="large")
    with left:
        question("What's your budget?", "We only show mice that fit your hand and your price range.")
        bind("w_budget", "w_hand", "w_conn", "w_wpref")
        st.slider("Budget (USD)", 15, 250, step=5, key="w_budget")
        caps = core.budget_caps(S.w_budget, tier_config())
        st.caption(f"Top brands can go up to ${caps['Top']}, trusted brands up to ${caps['Good']}. "
                   f"Everything else stays within ${caps['Neutral']}.")
        st.segmented_control("Hand", ["Right", "Left"], key="w_hand", width="stretch", on_change=restore, args=("w_hand",))
        st.segmented_control("Connection", ["Any", "Wireless", "Wired"], key="w_conn", width="stretch", on_change=restore, args=("w_conn",))
        st.segmented_control("Weight", list(core.WEIGHT_POINTS), key="w_wpref", width="stretch", on_change=restore, args=("w_wpref",))
        keep("w_budget", "w_hand", "w_conn", "w_wpref")
        c1, c2, _ = st.columns([1, 2, 3])
        c1.button("Back", on_click=go, args=(2,))
        c2.button("Show my mice", type="primary", on_click=go, args=("results",))
    with right:
        with st.container(border=True):
            _, recs = run_recommend(n=999, per_brand=999)
            st.markdown(f'<div class="score">{len(recs)}</div>', unsafe_allow_html=True)
            st.write(f"current mice fit your {P['grip'].lower()} grip and a ${P['w_budget']} budget.")
            st.caption("Older sensors and poor fits are already filtered out.")


# ----------------------------------------------------------------------------
# Results
# ----------------------------------------------------------------------------
def sidebar_refine():
    with st.sidebar:
        st.markdown("### Refine")
        bind("w_budget", "w_maxw", "w_recency", "w_dated", "w_perbrand", "w_shape",
             "w_hand", "w_conn", "w_wpref")
        st.slider("Budget (USD)", 15, 250, step=5, key="w_budget")
        st.segmented_control("Hand", ["Right", "Left"], key="w_hand", width="stretch", on_change=restore, args=("w_hand",))
        st.segmented_control("Connection", ["Any", "Wireless", "Wired"], key="w_conn", width="stretch", on_change=restore, args=("w_conn",))
        st.segmented_control("Shape", ["Any", "Symmetrical", "Ergonomic"], key="w_shape", width="stretch", on_change=restore, args=("w_shape",))
        st.slider("Max weight (g)", 30, 120, step=5, key="w_maxw")
        st.selectbox("Weight preference", list(core.WEIGHT_POINTS), key="w_wpref")
        st.selectbox("Favor newer tech", list(core.RECENCY_POINTS), key="w_recency",
                     help="How many points a current sensor and polling rate are worth.")
        st.toggle("Include dated mice", key="w_dated",
                  help="Mice with 2016-2019 era sensors. Hidden by default.")
        st.slider("Max results per brand", 1, 5, key="w_perbrand")
        keep("w_budget", "w_hand", "w_conn", "w_shape", "w_maxw", "w_wpref", "w_recency",
             "w_dated", "w_perbrand")

        with st.expander("Brand tiers"):
            tier_keys = [f"s_{t}" for t in core.TIER_DEFAULTS] + [f"p_{t}" for t in core.TIER_DEFAULTS]
            bind(*tier_keys)
            for t in core.TIER_DEFAULTS:
                a, b = st.columns(2)
                a.number_input(f"{t} stretch %", 0, 50, step=5, key=f"s_{t}")
                b.number_input(f"{t} points", -20, 20, step=1, key=f"p_{t}")
            st.caption("Stretch lets a tier be recommended slightly above your budget.")
            keep(*tier_keys)

        with st.expander("Real prices"):
            st.caption("Upload a CSV with `Name,Price_USD`, or run `fetch_prices.py` to build one.")
            up = st.file_uploader("prices.csv", type="csv", label_visibility="collapsed")
            if up is not None:
                P["prices_bytes"] = up.getvalue()
            if P["prices_bytes"]:
                st.success("Using your price file.")


def result_card(rank, r, budget):
    t = core.targets(P["grip"], P["w_len"] * 10, P["w_wid"] * 10)
    stretch = r["Price"] > budget
    verified = r["Price source"] == "verified"
    badges = [f":blue-badge[{core.TIER_LABEL[r['Tier']]}]",
              f":green-badge[{r['Era']} tech]" if r["Era"] == "Current" else f":gray-badge[{r['Era']} tech]"]
    if stretch:
        badges.append(":orange-badge[Above budget]")
    with st.container(border=True):
        st.markdown(":primary-badge[Best match]" if rank == 1 else f":gray-badge[#{rank}]")
        st.markdown(f'<div class="name">{html.escape(r["Name"])}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="score">{r["Score"]:.0f}<small>/100 match</small></div>', unsafe_allow_html=True)
        price = (f'${r["Price"]:.0f} <small>verified</small>' if verified
                 else f'about ${r["Price"]:.0f} <small>estimate</small>')
        st.markdown(f'<div class="price">{price}</div>', unsafe_allow_html=True)
        st.markdown(" ".join(badges))
        st.markdown(dim_bar("Length", r["Length (mm)"], t["length"], 14)
                    + dim_bar("Width", r["Width (mm)"], t["width"], 8)
                    + dim_bar("Height", r["Height (mm)"], t["height"], 6), unsafe_allow_html=True)
        items = "".join(f"<li>{html.escape(x)}</li>" for x in core.reasons(
            r, P["grip"], P["w_len"] * 10, P["w_wid"] * 10, tier_config()))
        st.markdown(f'<ul class="reasons">{items}</ul>', unsafe_allow_html=True)
        st.caption(f"{r['Weight (grams)']:.0f} g · {r['Shape'].lower()} · {r['Connectivity'].lower()}")


def step_results():
    sidebar_refine()
    st.markdown('<div class="brandmark">Mouse finder</div>', unsafe_allow_html=True)
    top = st.columns([4, 1, 1, 1, 1], vertical_alignment="center")
    top[0].markdown(
        f'<p class="q" style="font-size:1.8rem;margin:14px 0 0">Your matches</p>'
        f'<p class="sub" style="margin:4px 0 0">{P["grip"]} grip · hand {P["w_len"]:.1f} × {P["w_wid"]:.1f} cm · '
        f'${P["w_budget"]} budget</p>', unsafe_allow_html=True)
    top[1].button("Hand", on_click=go, args=(1,), width="stretch")
    top[2].button("Grip", on_click=go, args=(2,), width="stretch")
    top[3].button("Budget", on_click=go, args=(3,), width="stretch")
    top[4].button("Start over", on_click=start_over, width="stretch")
    st.write("")

    scored, recs = run_recommend(n=40)
    if recs.empty:
        cf = core.cheapest_fit(scored, P["w_dated"])
        msg = ("Nothing fits that hand, grip and budget. Try raising the budget or loosening "
               "the filters in the sidebar.")
        if cf is not None:
            msg += f" The cheapest current mouse that fits is {cf['Name']}, at about ${cf['Price']:.0f}."
        st.warning(msg)
        return

    if (recs.head(3)["Price source"] == "estimate").any():
        st.info("Some prices are estimates because the database has no price data. "
                "Upload real prices in the sidebar, or run fetch_prices.py, for an accurate budget filter.")

    cols = st.columns(3, gap="medium")
    for i, (col, (_, r)) in enumerate(zip(cols, recs.head(3).iterrows()), start=1):
        with col:
            result_card(i, r, P["w_budget"])
    st.markdown('<div class="legend">On each size bar, the shaded band is the ideal range for your hand '
                'and the dot is where this mouse sits.</div>', unsafe_allow_html=True)

    st.write("")
    bind("w_list")
    st.toggle("Show full ranked list", key="w_list")
    keep("w_list")
    if S.w_list:
        bind("w_rows")
        st.slider("Rows", 5, 40, key="w_rows")
        keep("w_rows")
        table = recs.head(S.w_rows)[
            ["Name", "Tier", "Score", "Era", "Price", "Price source", "Length (mm)", "Width (mm)",
             "Height (mm)", "Weight (grams)", "Shape", "Hump placement", "Sensor",
             "Polling rate (Hz)", "Connectivity"]].copy()
        table["Tier"] = table["Tier"].map(core.TIER_LABEL)
        table.index = table.index + 1
        st.dataframe(table, width="stretch", column_config={
            "Score": st.column_config.ProgressColumn("Match", min_value=0, max_value=100, format="%.0f"),
            "Price": st.column_config.NumberColumn("Price (USD)", format="$%.0f"),
            "Tier": "Brand tier",
        })
        st.download_button("Download as CSV", table.to_csv().encode(), "mouse_matches.csv", "text/csv")

    with st.expander("How the match score works"):
        t = core.targets(P["grip"], P["w_len"] * 10, P["w_wid"] * 10)
        cfg = tier_config()
        st.markdown(
            f"- **Fit (up to 70):** length, width, height, hump position and shape against your "
            f"{P['grip'].lower()} grip. Your target is about {t['length']:.0f} mm long and {t['width']:.0f} mm wide.\n"
            f"- **Newer tech (up to {core.RECENCY_POINTS[P['w_recency']]}):** sensor generation and polling rate. "
            f"The database has no release dates, so age is inferred from the tech. Dated mice are hidden unless you include them.\n"
            f"- **Weight (up to {core.WEIGHT_POINTS[P['w_wpref']]}):** lighter mice score higher if you prefer that.\n"
            f"- **Brand points:** " + ", ".join(f"{k} {v[1]:+d}" for k, v in cfg.items()) + ".\n"
            f"- **Budget:** a mouse is shown if its price is at most your budget plus its tier's stretch "
            f"({', '.join(f'{k} ${v}' for k, v in core.budget_caps(P['w_budget'], cfg).items())}).")


# ----------------------------------------------------------------------------
# Router
# ----------------------------------------------------------------------------
if S.step == "results" and not P["grip"]:
    S.step = 2

if S.step in (1, 2, 3):
    _, mid, _ = st.columns([1, 6, 1])
    with mid:
        {1: step_hand, 2: step_grip, 3: step_budget}[S.step]()
else:
    step_results()
