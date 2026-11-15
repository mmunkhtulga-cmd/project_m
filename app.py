"""
Mouse finder.   Run:  streamlit run app.py

Hand size -> grip (or "not sure") -> budget -> top matches as cards (full list optional).
Logic lives in core.py. Photos: images/ (prepare_images.py). Prices: prices.csv / fetch_prices.py.
Exact retailer pages: links.csv.
"""
import html
import io

import streamlit as st

import core

st.set_page_config(page_title="Mouse finder", layout="wide")
S = st.session_state

CSS = r"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
html, body, .stApp, .stApp button, .stApp input, .stApp label { font-family: 'Inter', system-ui, -apple-system, 'Segoe UI', sans-serif; }
.block-container { max-width: 1180px; padding-top: 2rem; }
footer, #MainMenu { visibility: hidden; }
.mf-step { color: #7E8B9D; font-size: .72rem; font-weight: 700; letter-spacing: .14em; }
.mf-q { font-size: 2rem; font-weight: 800; letter-spacing: -.02em; margin: .3rem 0 .4rem; color: #F2F5F9; }
.mf-sub { color: #8B97A8; margin: 0 0 1.2rem; max-width: 52ch; }
.mf-head { display: flex; justify-content: space-between; color: #7E8B9D; font-size: .7rem; font-weight: 700; letter-spacing: .14em; margin: 1.2rem 0 .7rem; }
.mf-card { display: flex; background: #121821; border: 1px solid #232D3B; border-radius: 18px; overflow: hidden; margin-bottom: 16px; color: #E8EDF3; }
.mf-hero { border-color: #2D6B52; background: linear-gradient(120deg, #12261F 0%, #121821 42%); box-shadow: 0 0 0 1px rgba(53,194,139,.12), 0 18px 50px rgba(0,0,0,.35); }
.mf-img { position: relative; flex: 0 0 34%; min-height: 250px; display: flex; align-items: center; justify-content: center; padding: 22px; background: #E9EDF2; }
.mf-small .mf-img { flex: 0 0 36%; min-height: 220px; }
.mf-img img { max-width: 100%; max-height: 230px; object-fit: contain; }
.mf-noimg { background: linear-gradient(160deg, #1A2330, #0F151D); flex-direction: column; gap: 6px; }
.mf-initial { font-size: 3.2rem; font-weight: 800; color: #2B384A; }
.mf-soon { font-size: .7rem; color: #6F7C8F; letter-spacing: .1em; text-transform: uppercase; }
.mf-badge, .mf-rank { position: absolute; top: 14px; padding: 4px 10px; border-radius: 999px; font-size: .68rem; font-weight: 700; background: rgba(11,15,20,.84); color: #DCE3EC; border: 1px solid rgba(255,255,255,.14); }
.mf-badge { left: 14px; }
.mf-rank { right: 14px; }
.mf-hero .mf-badge { color: #7CE3B7; border-color: rgba(124,227,183,.4); }
.mf-main { flex: 1; min-width: 0; padding: 24px 26px; }
.mf-brand { color: #8B97A8; font-size: .7rem; font-weight: 700; letter-spacing: .14em; text-transform: uppercase; }
.mf-name { font-size: 1.9rem; font-weight: 800; letter-spacing: -.02em; line-height: 1.1; margin: .25rem 0 .7rem; color: #F2F5F9; }
.mf-small .mf-name { font-size: 1.3rem; }
.mf-chips { display: flex; flex-wrap: wrap; gap: 6px; margin: .2rem 0 .8rem; }
.mf-chip { padding: 3px 10px; border-radius: 999px; font-size: .74rem; font-weight: 600; background: #1A222D; border: 1px solid #2A3442; color: #C8D1DD; }
.mf-gold { color: #F5C96A; border-color: #5B4A22; background: #241E10; }
.mf-green .mf-chip { color: #7CE3B7; border-color: #2D6B52; background: #12261F; }
.mf-desc { color: #A7B2C0; font-size: .92rem; margin: 0 0 1rem; }
.mf-why { border: 1px solid #2A4A6B; background: linear-gradient(135deg, #142235, #101A28); border-radius: 14px; padding: 14px 16px; }
.mf-why-k { color: #6FA8FF; font-size: .68rem; font-weight: 800; letter-spacing: .14em; }
.mf-why-h { font-size: 1.05rem; font-weight: 700; margin: .25rem 0; color: #F2F5F9; }
.mf-why p { color: #9FB0C6; font-size: .86rem; margin: 0 0 .6rem; }
.mf-why .mf-chips { margin-bottom: 0; }
.mf-side { flex: 0 0 27%; padding: 24px 24px 24px 0; display: flex; flex-direction: column; gap: 10px; }
.mf-price { font-size: 1.35rem; font-weight: 800; color: #F2F5F9; }
.mf-price small { font-size: .78rem; font-weight: 500; color: #8B97A8; margin-left: 4px; }
.mf-warn { color: #F5C96A; font-size: .76rem; font-weight: 600; margin-top: -4px; }
.mf-btn { display: block; text-align: center; padding: 12px 14px; border-radius: 12px; font-size: .88rem; font-weight: 700; text-decoration: none !important; color: #E8EDF3 !important; background: #161E29; border: 1px solid #2A3442; }
.mf-btn:hover { border-color: #3F5068; background: #1B2431; }
.mf-primary { background: linear-gradient(180deg, #2F86FF, #1E6AE6); border-color: #3C8CFF; color: #fff !important; }
.mf-primary:hover { background: linear-gradient(180deg, #4093FF, #2673EE); }
.mf-details { border: 1px solid #2A3442; border-radius: 12px; background: #161E29; }
.mf-details summary { cursor: pointer; padding: 11px 14px; text-align: center; font-size: .88rem; font-weight: 700; color: #E8EDF3; list-style: none; }
.mf-details summary::-webkit-details-marker { display: none; }
.mf-table { width: 100%; border-collapse: collapse; font-size: .8rem; margin: 0 0 6px; }
.mf-table td { padding: 6px 14px; border-top: 1px solid #222C3A; color: #C8D1DD; }
.mf-table td:first-child { color: #8B97A8; }
.mf-table td:last-child { text-align: right; color: #8B97A8; }
.mf-list { margin: .4rem 0 .9rem; padding: 0; list-style: none; }
.mf-list li { color: #C8D1DD; font-size: .84rem; padding: 2px 0 2px 22px; position: relative; }
.mf-list li::before { content: "✓"; position: absolute; left: 0; color: #35C28B; font-weight: 800; }
.mf-small .mf-main { padding: 20px 22px 0; }
.mf-small .mf-actions { display: flex; flex-direction: column; gap: 10px; padding: 0 22px 22px; }
@media (max-width: 900px) {
  .mf-card { flex-direction: column; }
  .mf-img, .mf-small .mf-img { flex: 0 0 auto; min-height: 200px; }
  .mf-side { padding: 0 24px 24px; }
  .mf-main { padding: 20px; }
}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

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
        w_shape="Any", w_maxw=100, w_wpref="Prefer light", w_recency="Medium",
        w_perbrand=2, w_list=False, w_rows=15, p_editor=core.EDITOR_POINTS, prices_bytes=None,
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


def run_recommend(n=40, per_brand=None):
    """(scored pool, recommendations). 'Not sure' returns the curated universal picks for the hand size."""
    pool = eligible_pool(get_db())
    L, W = P["w_len"] * 10, P["w_wid"] * 10
    if P["w_grip"] == "Not sure":
        recs = core.universal_picks(pool, L, W, tier_config(), P["w_wpref"], P["w_recency"], P["p_editor"])
        return recs, recs
    sc = core.score(pool, P["w_grip"], L, W, tier_config(), P["w_wpref"], P["w_recency"], P["p_editor"])
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


def step_budget():
    with centered():
        step_head(3, "What's your budget?", "We only suggest mice that fit your hand and your price range.")
        bind("w_budget", "w_hand", "w_conn", "w_wpref")
        st.slider("Budget (USD)", 15, 250, step=5, key="w_budget")
        caps = core.budget_caps(S.w_budget, tier_config())
        st.caption(f"Top-tier brands can be suggested up to ${caps['Top']}, "
                   f"mid-tier brands up to ${caps['Mid']}, everything else up to ${caps['Other']}.")
        st.segmented_control("Hand", ["Right", "Left"], key="w_hand", on_change=restore, args=("w_hand",))
        st.segmented_control("Connection", ["Any", "Wireless", "Wired"], key="w_conn",
                             on_change=restore, args=("w_conn",))
        st.segmented_control("Weight", list(core.WEIGHT_POINTS), key="w_wpref",
                             on_change=restore, args=("w_wpref",))
        keep("w_budget", "w_hand", "w_conn", "w_wpref")
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


def chips(items, cls="", gold=()):
    out = "".join(f'<span class="mf-chip{" mf-gold" if i in gold else ""}">{e(i)}</span>' for i in items)
    return f'<div class="mf-chips {cls}">{out}</div>'


def image_tile(r, rank):
    label = {1: "Best match", 2: "Second-best match"}.get(rank, f"Match #{rank}")
    badges = f'<span class="mf-badge">{label}</span><span class="mf-rank">#{rank}</span>'
    data = core.image_data(r["Name"])
    if data:
        uri, bg = data
        style = f' style="background:{bg}"' if bg else ""
        return f'<div class="mf-img"{style}>{badges}<img src="{uri}" alt="{e(r["Name"])}"></div>'
    return (f'<div class="mf-img mf-noimg">{badges}<span class="mf-initial">{e(r["Brand"][:1])}</span>'
            f'<span class="mf-soon">Photo coming soon</span></div>')


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


def card_parts(r, universal):
    brand, model = core.split_name(r["Name"], r["Brand"])
    grips = "All grips" if universal else " / ".join(core.suits(r)) + " grip"
    spec = [f'{r["Weight (grams)"]:.0f} g', r["Connectivity"], grips]
    if r["Editor"]:
        spec.append("Editor's choice")
    return brand, model, chips(spec, gold=("Editor's choice",)), e(core.describe(r, universal))


def hero_card(r, universal):
    brand, model, spec, desc = card_parts(r, universal)
    L = P["w_len"] * 10
    why = core.why_chips(r, P["w_grip"], L, P["w_conn"], P["w_budget"])
    if universal:
        para = f"A universal shape that suits {core.hand_bracket(L).lower()} hands whichever grip you end up using."
    else:
        para = (f"It matches your {P['w_grip'].lower()} grip, {P['w_len']:.1f} cm hand and "
                f"${P['w_budget']} budget more closely than anything else we looked at.")
    return (f'<div class="mf-card mf-hero">{image_tile(r, 1)}'
            f'<div class="mf-main"><div class="mf-brand">{e(brand)}</div><div class="mf-name">{e(model)}</div>'
            f'{spec}<p class="mf-desc">{desc}</p>'
            f'<div class="mf-why"><div class="mf-why-k">WHY THIS RANKS FIRST</div>'
            f'<div class="mf-why-h">The closest overall fit for your profile</div><p>{e(para)}</p>'
            f'{chips(why, "mf-green")}</div></div>'
            f'<div class="mf-side">{price_block(r)}{buttons(r["Name"])}{fit_details(r)}</div></div>')


def small_card(r, rank, universal):
    brand, model, spec, desc = card_parts(r, universal)
    why = core.why_chips(r, P["w_grip"], P["w_len"] * 10, P["w_conn"], P["w_budget"])[:3]
    items = "".join(f"<li>{e(w)}</li>" for w in why)
    return (f'<div class="mf-card mf-small">{image_tile(r, rank)}'
            f'<div style="flex:1;min-width:0"><div class="mf-main"><div class="mf-brand">{e(brand)}</div>'
            f'<div class="mf-name">{e(model)}</div>{spec}<p class="mf-desc">{desc}</p>'
            f'<div class="mf-brand">WHY IT MATCHES</div><ul class="mf-list">{items}</ul>{price_block(r)}</div>'
            f'<div class="mf-actions">{buttons(r["Name"])}{fit_details(r)}</div></div></div>')


# ----------------------------------------------------------------------------
# Results
# ----------------------------------------------------------------------------
def sidebar():
    with st.sidebar:
        st.subheader("Filters")
        bind("w_budget", "w_maxw", "w_recency", "w_perbrand", "w_shape", "w_hand", "w_conn", "w_wpref")
        st.slider("Budget (USD)", 15, 250, step=5, key="w_budget")
        st.segmented_control("Hand", ["Right", "Left"], key="w_hand", on_change=restore, args=("w_hand",))
        st.segmented_control("Connection", ["Any", "Wireless", "Wired"], key="w_conn",
                             on_change=restore, args=("w_conn",))
        st.segmented_control("Shape", ["Any", "Symmetrical", "Ergonomic"], key="w_shape",
                             on_change=restore, args=("w_shape",))
        st.slider("Max weight (g)", 30, 120, step=5, key="w_maxw")
        st.selectbox("Weight preference", list(core.WEIGHT_POINTS), key="w_wpref")
        st.selectbox("Favor newer tech", list(core.RECENCY_POINTS), key="w_recency",
                     help="How many points a current sensor and polling rate are worth.")
        st.slider("Max results per brand", 1, 5, key="w_perbrand")
        keep("w_budget", "w_hand", "w_conn", "w_shape", "w_maxw", "w_wpref", "w_recency", "w_perbrand")

        with st.expander("Brand tiers and points"):
            keys = [f"s_{t}" for t in core.TIER_DEFAULTS] + [f"p_{t}" for t in core.TIER_DEFAULTS]
            bind(*keys, "p_editor")
            for t in core.TIER_DEFAULTS:
                a, b = st.columns(2)
                a.number_input(f"{core.TIER_LABEL[t]}: stretch %", 0, 50, step=5, key=f"s_{t}")
                b.number_input(f"{core.TIER_LABEL[t]}: points", -20, 20, step=1, key=f"p_{t}")
            st.number_input("Editor's choice bonus", 0, 30, step=1, key="p_editor")
            st.caption("Stretch lets a tier be suggested a little above your budget.")
            keep(*keys, "p_editor")

        with st.expander("Real prices"):
            st.caption("Upload a CSV with the columns Name and Price_USD (optional: Source), "
                       "or build one with fetch_prices.py.")
            up = st.file_uploader("Prices file", type="csv", label_visibility="collapsed")
            if up is not None:
                P["prices_bytes"] = up.getvalue()
            if P["prices_bytes"]:
                st.success("Using your price file.")


def step_results():
    sidebar()
    universal = P["w_grip"] == "Not sure"
    st.markdown('<h1 class="mf-q" style="font-size:1.7rem">Recommended mice</h1>', unsafe_allow_html=True)
    st.write(("Universal shapes" if universal else f"{P['w_grip']} grip")
             + f", hand {P['w_len']:.1f} x {P['w_wid']:.1f} cm, budget ${P['w_budget']}")
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
    top = list(recs.head(3).iterrows())
    st.markdown('<div class="mf-head"><span>TOP MATCHES</span><span>BEST FIT FIRST</span></div>',
                unsafe_allow_html=True)
    st.markdown(hero_card(top[0][1], universal), unsafe_allow_html=True)
    if len(top) > 1:
        for col, (rank, (_, r)) in zip(st.columns(2, gap="medium"), enumerate(top[1:], start=2)):
            with col:
                st.markdown(small_card(r, rank, universal), unsafe_allow_html=True)
    if (recs.head(3)["Price source"] == "estimate").any():
        st.caption("Prices marked as estimates are guesses because the database has no price data. "
                   "Add real prices in the sidebar, or run fetch_prices.py, for an accurate budget filter.")
    if any(core.image_data(n) is None for n in recs.head(3)["Name"]):
        st.caption("Some photos are still missing. See images_needed.csv.")

    bind("w_list")
    st.toggle("Show full ranked list", key="w_list")
    keep("w_list")
    if S.w_list:
        bind("w_rows")
        st.slider("Rows", 3, 40, key="w_rows")
        keep("w_rows")
        table = recs.head(S.w_rows)[
            ["Name", "Tier", "Editor", "Score", "Price", "Price source", "Length (mm)", "Width (mm)",
             "Height (mm)", "Weight (grams)", "Shape", "Hump placement", "Sensor",
             "Polling rate (Hz)", "Connectivity"]].copy()
        table["Tier"] = table["Tier"].map(core.TIER_LABEL)
        table["Editor"] = table["Editor"].map({True: "Yes", False: ""})
        table.index = table.index + 1
        st.dataframe(table, width="stretch", column_config={
            "Score": st.column_config.NumberColumn("Match", format="%.0f"),
            "Price": st.column_config.NumberColumn("Price (USD)", format="$%.0f"),
            "Tier": "Brand tier", "Editor": "Editor's choice",
        })
        st.download_button("Download as CSV", table.to_csv().encode(), "mouse_matches.csv", "text/csv")

    with st.expander("How the match score works"):
        t = core.targets(P["w_grip"], P["w_len"] * 10, P["w_wid"] * 10)
        cfg = tier_config()
        st.markdown(
            f"- **Fit (up to 70):** length, width, height, hump position and shape. Your target is about "
            f"{t['length']:.0f} mm long and {t['width']:.0f} mm wide. Longer than ideal is penalized less "
            f"than shorter. Poor fits are dropped. Top-tier brands and editor's choice mice get a small "
            f"allowance on fit (only within 10 mm of the ideal length) because they are proven designs.\n"
            f"- **Newer tech (up to {core.RECENCY_POINTS[P['w_recency']]}):** sensor generation and polling "
            f"rate. Mice with PAW3335, PAW3370 or older sensors are not in the database at all; "
            f"proprietary gaming sensors and PAW3311 are kept.\n"
            f"- **Weight (up to {core.WEIGHT_POINTS[P['w_wpref']]}):** lighter scores higher if you prefer that.\n"
            f"- **Brand tier:** " + ", ".join(f"{core.TIER_LABEL[k]} {v[1]:+d}" for k, v in cfg.items())
            + f".\n- **Editor's choice:** +{P['p_editor']}.\n"
            f"- **Budget:** a mouse is shown if its price is at most your budget plus its tier's stretch "
            f"({', '.join(f'{core.TIER_LABEL[k]} ${v}' for k, v in core.budget_caps(P['w_budget'], cfg).items())}).\n"
            f"- **Not sure of your grip:** a curated list of universal-shape mice for your hand size, "
            f"ranked by their average score across palm, claw and fingertip. Budget only flags them.")


# ----------------------------------------------------------------------------
if S.step == "results" and not P["w_grip"]:
    S.step = 2

{1: step_hand, 2: step_grip, 3: step_budget}.get(S.step, step_results)()
