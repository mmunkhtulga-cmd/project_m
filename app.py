"""
Mouse finder.   Run:  streamlit run app.py

Hand size -> grip -> budget -> recommendations (full ranked list is optional).
Logic lives in core.py. Real prices: prices.csv, sidebar upload, or fetch_prices.py
"""
import io

import streamlit as st

import core

st.set_page_config(page_title="Mouse finder", layout="wide")
S = st.session_state

# ----------------------------------------------------------------------------
# State. S.P holds every answer. Streamlit forgets a widget's value when the widget
# isn't drawn on a step, so widgets are re-seeded from P (bind) and saved back (keep).
# ----------------------------------------------------------------------------
if "P" not in S:
    S.P = dict(
        w_grip=None, w_len=18.5, w_wid=8.5, w_budget=70, w_hand="Right", w_conn="Any",
        w_shape="Any", w_maxw=100, w_wpref="Prefer light", w_recency="Medium",
        w_dated=False, w_perbrand=2, w_list=False, w_rows=15, p_editor=core.EDITOR_POINTS,
        prices_bytes=None,
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
    sc = core.score(pool, P["w_grip"], P["w_len"] * 10, P["w_wid"] * 10, tier_config(),
                    P["w_wpref"], P["w_recency"], P["p_editor"])
    recs = core.recommend(sc, P["w_budget"], tier_config(), P["w_dated"],
                          per_brand or P["w_perbrand"], n)
    return sc, recs


def centered():
    """Narrow column for the question steps."""
    _, mid, _ = st.columns([1, 2, 1])
    return mid


# ----------------------------------------------------------------------------
# Steps
# ----------------------------------------------------------------------------
def step_hand():
    with centered():
        st.caption("Step 1 of 3")
        st.header("Hand size")
        st.write("Length: wrist crease to the tip of your middle finger, hand flat. "
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
        st.caption("Step 2 of 3")
        st.header("Grip style")
        bind("w_grip")
        st.radio("How do you hold your mouse?", list(core.GRIPS), index=None, key="w_grip",
                 captions=[g["blurb"] for g in core.GRIPS.values()])
        keep("w_grip")
        if S.w_grip:
            t = core.targets(S.w_grip, P["w_len"] * 10, P["w_wid"] * 10)
            st.caption(f"For your hand, look for a mouse about {t['length']:.0f} mm long "
                       f"and {t['width']:.0f} mm wide.")
        a, b, _ = st.columns([1, 1, 3])
        a.button("Back", on_click=go, args=(1,))
        b.button("Next", type="primary", on_click=go, args=(3,), disabled=not S.w_grip)


def step_budget():
    with centered():
        st.caption("Step 3 of 3")
        st.header("Budget")
        bind("w_budget", "w_hand", "w_conn", "w_wpref")
        st.slider("Budget (USD)", 15, 250, step=5, key="w_budget")
        caps = core.budget_caps(S.w_budget, tier_config())
        st.caption(f"Top-tier brands can be suggested up to ${caps['Top']}, "
                   f"mid-tier brands up to ${caps['Mid']}, everything else up to ${caps['Other']}.")
        st.segmented_control("Hand", ["Right", "Left"], key="w_hand", on_change=restore,
                             args=("w_hand",))
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
# Results
# ----------------------------------------------------------------------------
def sidebar():
    with st.sidebar:
        st.subheader("Filters")
        bind("w_budget", "w_maxw", "w_recency", "w_dated", "w_perbrand", "w_shape",
             "w_hand", "w_conn", "w_wpref")
        st.slider("Budget (USD)", 15, 250, step=5, key="w_budget")
        st.segmented_control("Hand", ["Right", "Left"], key="w_hand", on_change=restore,
                             args=("w_hand",))
        st.segmented_control("Connection", ["Any", "Wireless", "Wired"], key="w_conn",
                             on_change=restore, args=("w_conn",))
        st.segmented_control("Shape", ["Any", "Symmetrical", "Ergonomic"], key="w_shape",
                             on_change=restore, args=("w_shape",))
        st.slider("Max weight (g)", 30, 120, step=5, key="w_maxw")
        st.selectbox("Weight preference", list(core.WEIGHT_POINTS), key="w_wpref")
        st.selectbox("Favor newer tech", list(core.RECENCY_POINTS), key="w_recency",
                     help="How many points a current sensor and polling rate are worth.")
        st.toggle("Include dated mice", key="w_dated",
                  help="Mice with older sensors (roughly 2016 to 2019). Hidden by default; "
                       "editor's choice mice are never hidden.")
        st.slider("Max results per brand", 1, 5, key="w_perbrand")
        keep("w_budget", "w_hand", "w_conn", "w_shape", "w_maxw", "w_wpref", "w_recency",
             "w_dated", "w_perbrand")

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
            st.caption("Upload a CSV with the columns Name and Price_USD, "
                       "or build one with fetch_prices.py.")
            up = st.file_uploader("Prices file", type="csv", label_visibility="collapsed")
            if up is not None:
                P["prices_bytes"] = up.getvalue()
            if P["prices_bytes"]:
                st.success("Using your price file.")


def price_text(r):
    return (f"${r['Price']:.0f}" if r["Price source"] == "verified"
            else f"~${r['Price']:.0f} (estimate)")


def show_pick(rank, r):
    st.subheader(f"{rank}. {r['Name']}")
    bits = [price_text(r),
            f"{r['Length (mm)']:.0f} x {r['Width (mm)']:.0f} x {r['Height (mm)']:.0f} mm",
            f"{r['Weight (grams)']:.0f} g", r["Connectivity"], r["Shape"], f"match {r['Score']:.0f}"]
    if r["Price"] > P["w_budget"]:
        bits.insert(1, "above your budget")
    st.write(" | ".join(bits))
    why = core.reasons(r, P["w_grip"], P["w_len"] * 10, P["w_wid"] * 10, tier_config())
    st.caption("; ".join(why))


def step_results():
    sidebar()
    st.title("Recommended mice")
    st.write(f"{P['w_grip']} grip, hand {P['w_len']:.1f} x {P['w_wid']:.1f} cm, "
             f"budget ${P['w_budget']}")
    a, b, c, d, _ = st.columns([1, 1, 1, 1, 4])
    a.button("Edit hand", on_click=go, args=(1,), width="stretch")
    b.button("Edit grip", on_click=go, args=(2,), width="stretch")
    c.button("Edit budget", on_click=go, args=(3,), width="stretch")
    d.button("Start over", on_click=start_over, width="stretch")

    scored, recs = run_recommend(n=40)
    if recs.empty:
        cf = core.cheapest_fit(scored, P["w_dated"])
        msg = ("Nothing fits that hand, grip and budget. Raise the budget or loosen the filters "
               "in the sidebar.")
        if cf is not None:
            msg += f" The cheapest mouse that fits is {cf['Name']}, at about ${cf['Price']:.0f}."
        st.warning(msg)
        return

    if (recs.head(3)["Price source"] == "estimate").any():
        st.caption("Prices marked as estimates are guesses, because the database has no price data. "
                   "Add real prices in the sidebar for an accurate budget filter.")
    for i, (_, r) in enumerate(recs.head(3).iterrows(), start=1):
        st.divider()
        show_pick(i, r)
    st.divider()

    bind("w_list")
    st.toggle("Show full ranked list", key="w_list")
    keep("w_list")
    if S.w_list:
        bind("w_rows")
        st.slider("Rows", 5, 40, key="w_rows")
        keep("w_rows")
        table = recs.head(S.w_rows)[
            ["Name", "Tier", "Editor", "Score", "Era", "Price", "Price source", "Length (mm)",
             "Width (mm)", "Height (mm)", "Weight (grams)", "Shape", "Hump placement", "Sensor",
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
            f"- **Fit (up to 70):** length, width, height, hump position and shape for a "
            f"{P['w_grip'].lower()} grip. Your target is about {t['length']:.0f} mm long and "
            f"{t['width']:.0f} mm wide. Longer than ideal is penalized less than shorter. "
            f"Poor fits are dropped. Top-tier brands and editor's choice mice get a small allowance "
            f"on fit (only within 10 mm of the ideal length) because they are proven designs.\n"
            f"- **Newer tech (up to {core.RECENCY_POINTS[P['w_recency']]}):** sensor generation and "
            f"polling rate. The database has no release dates, so age is inferred from the tech. "
            f"Dated mice are hidden unless you include them.\n"
            f"- **Weight (up to {core.WEIGHT_POINTS[P['w_wpref']]}):** lighter scores higher if you "
            f"prefer that.\n"
            f"- **Brand tier:** " + ", ".join(f"{core.TIER_LABEL[k]} {v[1]:+d}" for k, v in cfg.items())
            + f".\n- **Editor's choice:** +{P['p_editor']}.\n"
            f"- **Budget:** a mouse is shown if its price is at most your budget plus its tier's "
            f"stretch ({', '.join(f'{core.TIER_LABEL[k]} ${v}' for k, v in core.budget_caps(P['w_budget'], cfg).items())}).")


# ----------------------------------------------------------------------------
if S.step == "results" and not P["w_grip"]:
    S.step = 2

{1: step_hand, 2: step_grip, 3: step_budget}.get(S.step, step_results)()
