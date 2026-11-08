"""
Mouse Recommender (draft)
Run:  streamlit run app.py

Inputs : grip style, hand size, budget slider (+ a few filters)
Scoring: shape fit (0-80) + spec bonus (0-~13) + brand points (-/+)
Budget : top brands may stretch past the slider, low-tier brands may not.

NOTE: the database has NO price column. Prices are ESTIMATED from brand tier +
features unless you provide real ones (prices.csv next to this file, or upload
one in the sidebar). Columns: Name,Price_USD
"""
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

HERE = Path(__file__).parent
DB_PATH = HERE / "mouse_db.csv"
PRICES_PATH = HERE / "prices.csv"

# ----------------------------------------------------------------------------
# CONFIG  (edit freely)
# ----------------------------------------------------------------------------
# The DB splits some multi-word brands ("Attack" | "Shark RS3 Ultra"); fix them.
BRAND_FIX = {
    "Attack": "Attack Shark", "Dark": "Dark Project", "be": "be quiet!",
    "Press": "Press Play", "Dream": "Dream Machines", "Turtle": "Turtle Beach",
    "Endgame": "Endgame Gear", "Cooler": "Cooler Master", "Angry": "Angry Miao",
}

# Tier -> brands. Anything not listed is "Neutral".
TIER_BRANDS = {
    "Top": ["Logitech", "Razer", "Zowie", "Finalmouse", "VAXEE", "Endgame Gear",
            "SteelSeries", "Pulsar", "LAMZU", "G-Wolves", "Corsair", "ASUS"],
    "Good": ["ATK", "VGN", "MCHOSE", "Keychron", "Glorious", "HyperX", "Rapoo",
             "Hator", "Ninjutso", "Waizowl", "WLMOUSE", "Kysona", "Xtrfy"],
    "Low": ["Attack Shark", "AJAZZ", "RK", "Darmoshark", "EWEADN", "Redragon", "Delux"],
}
# Defaults, editable in the sidebar: (budget stretch %, brand points)
TIER_DEFAULTS = {
    "Top": (20, 8),      # may be recommended up to 20% over the slider, +8 pts
    "Good": (10, 5),     # consistent-quality brands: +5 pts, 10% stretch
    "Neutral": (0, 0),
    "Low": (0, -6),      # fewer points, no stretch
}

# Target mouse dimensions as a fraction of hand size, per grip (rule-of-thumb
# community heuristics, NOT validated science - tune to taste).
GRIPS = {
    "Palm":      dict(len_r=0.67, wid_r=0.74, height=41.0),
    "Claw":      dict(len_r=0.64, wid_r=0.72, height=39.5),
    "Fingertip": dict(len_r=0.60, wid_r=0.68, height=37.5),
}
HUMP_SCORE = {  # how well each hump placement suits each grip (0-1)
    "Palm":      {"Back - moderate": 1.0, "Center": 0.9, "Back - aggressive": 0.8, "Back - minimal": 0.7},
    "Claw":      {"Back - aggressive": 1.0, "Back - moderate": 1.0, "Back - minimal": 0.8, "Center": 0.6},
    "Fingertip": {"Back - minimal": 1.0, "Center": 0.9, "Back - moderate": 0.7, "Back - aggressive": 0.4},
}
SHAPE_SCORE = {
    "Palm":      {"Ergonomic": 1.0, "Hybrid": 0.9, "Symmetrical": 0.85},
    "Claw":      {"Symmetrical": 1.0, "Hybrid": 0.9, "Ergonomic": 0.7},
    "Fingertip": {"Symmetrical": 1.0, "Hybrid": 0.8, "Ergonomic": 0.5},
}
FLAGSHIP_SENSORS = ("PAW3950", "PAW3955", "PAW3395", "PAW3399", "PAW3398",
                    "XS-1", "Focus Pro", "MARKSMAN", "HERO 25K")


# ----------------------------------------------------------------------------
# DATA
# ----------------------------------------------------------------------------
def brand_tier(brand: str) -> str:
    for tier, brands in TIER_BRANDS.items():
        if brand.lower() in (b.lower() for b in brands):
            return tier
    return "Neutral"


def is_flagship(sensor) -> bool:
    return isinstance(sensor, str) and any(f.lower() in sensor.lower() for f in FLAGSHIP_SENSORS)


def estimate_price(row) -> float:
    """Very rough USD estimate from tier + features. Replace with real prices."""
    base = {"Top": 50, "Good": 32, "Neutral": 22, "Low": 15}[row["Tier"]]
    p = base
    p += 22 if row["Connectivity"] == "Wireless" else 0
    p += 10 if is_flagship(row["Sensor"]) else 0
    p += 8 if row["Polling rate (Hz)"] >= 4000 else 0
    w = row["Weight (grams)"]
    p += 8 if w <= 50 else (4 if w <= 60 else 0)
    mat = str(row["Material"]).lower()
    p += 25 if "magnesium" in mat else (10 if "carbon" in mat else 0)
    if row["Tier"] == "Top":
        p *= 1.2
    return max(10.0, round(p))


@st.cache_data
def load_db() -> pd.DataFrame:
    df = pd.read_csv(DB_PATH, sep=";")
    for c in ["Length (mm)", "Width (mm)", "Height (mm)", "Weight (grams)", "Polling rate (Hz)"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["Weight (grams)"] = df["Weight (grams)"].fillna(df["Weight (grams)"].median())
    df["Polling rate (Hz)"] = df["Polling rate (Hz)"].fillna(1000)
    # drop non-mouse outliers (rings, trackballs, giant devices)
    df = df[df["Length (mm)"].between(75, 140) & df["Width (mm)"].between(45, 80)].copy()
    df["Brand"] = df["Brand"].replace(BRAND_FIX)
    df["Tier"] = df["Brand"].map(brand_tier)
    df["Price"] = df.apply(estimate_price, axis=1)
    df["Price source"] = "estimate"
    return df.reset_index(drop=True)


def read_prices(src) -> pd.DataFrame | None:
    try:
        p = pd.read_csv(src, sep=None, engine="python")
        p.columns = [c.strip() for c in p.columns]
        return p[["Name", "Price_USD"]].dropna()
    except Exception:
        return None


def apply_price_overrides(df: pd.DataFrame, prices: pd.DataFrame | None) -> pd.DataFrame:
    if prices is None or prices.empty:
        return df
    df = df.copy()
    m = dict(zip(prices["Name"].str.lower().str.strip(), prices["Price_USD"]))
    key = df["Name"].str.lower()
    hit = key.isin(m)
    df.loc[hit, "Price"] = key[hit].map(m).astype(float)
    df.loc[hit, "Price source"] = "your csv"
    return df


# ----------------------------------------------------------------------------
# SCORING
# ----------------------------------------------------------------------------
def gauss(delta, sigma):
    return np.exp(-0.5 * (delta / sigma) ** 2)


def score(df, grip, hand_len, hand_wid, tier_cfg, weight_pref):
    g = GRIPS[grip]
    out = df.copy()
    out["s_len"] = gauss(out["Length (mm)"] - hand_len * g["len_r"], 5.0)
    out["s_wid"] = gauss(out["Width (mm)"] - hand_wid * g["wid_r"], 3.0)
    out["s_hgt"] = gauss(out["Height (mm)"] - g["height"], 3.0)
    out["s_hump"] = out["Hump placement"].map(HUMP_SCORE[grip]).fillna(0.6)
    out["s_shape"] = out["Shape"].map(SHAPE_SCORE[grip]).fillna(0.85)
    fit = (0.38 * out["s_len"] + 0.18 * out["s_wid"] + 0.12 * out["s_hgt"]
           + 0.20 * out["s_hump"] + 0.12 * out["s_shape"])
    out["Fit"] = 80 * fit

    flagship = out["Sensor"].map(is_flagship)
    spec = 5 * flagship + 3 * (out["Polling rate (Hz)"] >= 4000)
    wmax = {"Don't care": 0, "Prefer light": 4, "Ultralight": 7}[weight_pref]
    spec = spec + wmax * ((80 - out["Weight (grams)"]) / 40).clip(0, 1)
    out["Specs"] = spec

    out["Brand pts"] = out["Tier"].map(lambda t: tier_cfg[t][1])
    out["Score"] = (out["Fit"] + out["Specs"] + out["Brand pts"]).clip(0, 100)
    out["Budget cap"] = None
    return out


def recommend(df, budget, tier_cfg, max_per_brand, n):
    caps = df["Tier"].map(lambda t: budget * (1 + tier_cfg[t][0] / 100))
    df = df.assign(**{"Budget cap": caps.round(0)})
    df = df[df["Price"] <= df["Budget cap"]].sort_values("Score", ascending=False)
    df = df.groupby("Brand", sort=False).head(max_per_brand)
    return df.sort_values("Score", ascending=False).head(n).reset_index(drop=True)


# ----------------------------------------------------------------------------
# UI
# ----------------------------------------------------------------------------
def main():
    st.set_page_config(page_title="Mouse Recommender", page_icon="🖱️", layout="wide")
    st.title("🖱️ Mouse Recommender")
    st.caption("Pick your grip, hand size and budget. Brand reputation nudges the ranking.")

    db = load_db()

    with st.sidebar:
        st.header("You")
        grip = st.radio("Grip style", list(GRIPS), index=1, horizontal=True,
                        help="Palm: whole palm rests on the mouse. Claw: palm on the back, "
                             "fingers arched. Fingertip: only fingertips touch, palm floats.")
        c1, c2 = st.columns(2)
        hand_len = c1.number_input("Hand length (cm)", 14.0, 24.0, 18.5, 0.1,
                                   help="Wrist crease to middle fingertip") * 10
        hand_wid = c2.number_input("Hand width (cm)", 6.5, 12.0, 8.5, 0.1,
                                   help="Across the knuckles, thumb excluded") * 10

        st.header("Budget")
        budget = st.slider("Budget (USD)", 15, 200, 70, 5)

        st.header("Filters")
        hand = st.selectbox("Handedness", ["Right", "Left"])
        conn = st.selectbox("Connectivity", ["Any", "Wireless", "Wired"])
        shape_f = st.selectbox("Shape", ["Any", "Symmetrical", "Ergonomic"])
        max_w = st.slider("Max weight (g)", 30, 120, 90, 5)
        weight_pref = st.selectbox("Weight preference", ["Don't care", "Prefer light", "Ultralight"], index=1)
        max_per_brand = st.slider("Max results per brand", 1, 5, 2)
        n_results = st.slider("Results to show", 5, 30, 10)

        with st.expander("Brand tiers (stretch % / points)"):
            tier_cfg = {}
            for t, (s0, p0) in TIER_DEFAULTS.items():
                a, b = st.columns(2)
                s = a.number_input(f"{t}: stretch %", 0, 50, s0, 5, key=f"s_{t}")
                p = b.number_input(f"{t}: points", -20, 20, p0, 1, key=f"p_{t}")
                tier_cfg[t] = (s, p)
            st.caption("Stretch = how far past the slider a tier's mice may be recommended.")

        with st.expander("Real prices (recommended)"):
            st.caption("The database has no prices, so they are estimated. Upload a CSV "
                       "with columns `Name,Price_USD` (e.g. `ATK F1 V2 Ultra Max,95`).")
            up = st.file_uploader("prices.csv", type="csv")

    prices = read_prices(up) if up else (read_prices(PRICES_PATH) if PRICES_PATH.exists() else None)
    db = apply_price_overrides(db, prices)

    # hard filters
    pool = db[db["Hand compatibility"].isin([hand, "Ambidextrous"])]
    pool = pool[pool["Weight (grams)"] <= max_w]
    if conn != "Any":
        pool = pool[pool["Connectivity"] == conn]
    if shape_f != "Any":
        pool = pool[pool["Shape"].isin([shape_f, "Hybrid"])]

    scored = score(pool, grip, hand_len, hand_wid, tier_cfg, weight_pref)
    recs = recommend(scored, budget, tier_cfg, max_per_brand, n_results)

    if recs.empty:
        st.warning("Nothing matches. Raise the budget or loosen the filters.")
        return

    est_share = (recs["Price source"] == "estimate").mean()
    if est_share:
        st.info("Prices shown are **estimates** (no price data in the database). "
                "Upload real prices in the sidebar for accurate budget filtering.")

    st.subheader("Top picks")
    cols = st.columns(3)
    for col, (_, r) in zip(cols, recs.head(3).iterrows()):
        with col, st.container(border=True):
            st.markdown(f"**{r['Name']}**")
            st.metric("Score", f"{r['Score']:.0f}/100")
            over = r["Price"] > budget
            st.write(f"💲 {r['Price']:.0f} USD" + (" · ⬆️ stretch pick" if over else "")
                     + f" ({'est.' if r['Price source'] == 'estimate' else 'your csv'})")
            st.caption(f"{r['Tier']} brand · {r['Length (mm)']:.0f}×{r['Width (mm)']:.0f}×"
                       f"{r['Height (mm)']:.0f} mm · {r['Weight (grams)']:.0f} g")
            st.caption(f"{r['Shape']} · hump: {r['Hump placement']} · {r['Connectivity']}")
            st.caption(f"Fit {r['Fit']:.0f} + specs {r['Specs']:.0f} + brand {r['Brand pts']:+.0f}")

    st.subheader("All results")
    table = recs[["Name", "Tier", "Score", "Fit", "Specs", "Brand pts", "Price", "Price source",
                  "Length (mm)", "Width (mm)", "Height (mm)", "Weight (grams)", "Shape",
                  "Hump placement", "Sensor", "Polling rate (Hz)", "Connectivity"]].copy()
    table.index = table.index + 1
    st.dataframe(
        table, width="stretch",
        column_config={
            "Score": st.column_config.ProgressColumn("Score", min_value=0, max_value=100, format="%.0f"),
            "Fit": st.column_config.NumberColumn(format="%.0f"),
            "Specs": st.column_config.NumberColumn(format="%.0f"),
            "Price": st.column_config.NumberColumn("Price (USD)", format="$%.0f"),
        },
    )

    with st.expander("How scoring works"):
        g = GRIPS[grip]
        st.markdown(
            f"- **Fit (0–80):** length, width, height, hump placement and shape vs. your "
            f"{grip.lower()} grip. Target for you ≈ {hand_len * g['len_r']:.0f} mm long, "
            f"{hand_wid * g['wid_r']:.0f} mm wide, {g['height']:.0f} mm tall.\n"
            f"- **Specs (~0–15):** flagship sensor, 4k/8k polling, weight preference.\n"
            f"- **Brand points:** " + ", ".join(f"{t} {c[1]:+d}" for t, c in tier_cfg.items()) + ".\n"
            f"- **Budget:** a mouse is eligible if its price ≤ slider × (1 + tier stretch): "
            + ", ".join(f"{t} ≤ ${budget * (1 + c[0] / 100):.0f}" for t, c in tier_cfg.items()) + ".\n"
            "- Size ratios and hump/shape preferences are rule-of-thumb heuristics; tune them at the top of `app.py`."
        )


if __name__ == "__main__":
    main()
