"""
Core logic for the mouse recommender (no Streamlit imports, so it can be
tested and reused by fetch_prices.py).

Raw score = fit (0-70) + newer tech (0-10/20/30) + weight bonus (0-7) + brand points + editor's choice
Displayed score = raw as a % of the best possible total
Eligibility   = price <= budget * (1 + tier stretch)  and  era is not "Dated"
"""
from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).parent
DB_PATH = HERE / "mouse_db.csv"
PRICES_PATH = HERE / "prices.csv"

# ----------------------------------------------------------------------------
# BRANDS  (edit freely)
# ----------------------------------------------------------------------------
# The database splits some multi-word brands ("Attack" | "Shark RS3 Ultra").
BRAND_FIX = {
    "Attack": "Attack Shark", "Dark": "Dark Project", "be": "be quiet!",
    "Press": "Press Play", "Dream": "Dream Machines", "Turtle": "Turtle Beach",
    "Endgame": "Endgame Gear", "Cooler": "Cooler Master", "Angry": "Angry Miao",
}
TIER_BRANDS = {
    "Top": ["Razer", "Logitech", "LAMZU", "Hitscan", "CRDRAKO", "Pulsar", "Endgame Gear",
            "Arbiter", "MelGeek", "Ninjutso", "Teevolution", "VAXEE"],
    "Mid": ["ATK", "MCHOSE", "VGN", "VXE", "Finalmouse", "WALLHACK", "Keychron", "HyperX",
            "UNIUS", "Scyrox", "IPI", "WLMOUSE", "Waizowl", "G-Wolves",
            # other name brands
            "SteelSeries", "Glorious", "ROCCAT", "Cooler Master", "Alienware", "MSI",
            "Turtle Beach", "Xtrfy", "Cherry", "Fnatic"],
    "Low-mid": ["Attack Shark", "AULA", "Corsair", "AJAZZ", "RK", "Darmoshark", "EWEADN",
                "Redragon", "Delux"],
}
# Model-level exceptions, checked first (first match wins): (regex on full name, tier, connectivity or None)
NAME_RULES = [
    (r"akitsu", "Mid", None),                                              # Arbiter's Akitsu is mid tier
    (r"^ASUS ROG (Keris II|Harpe II|Harpe Ace (Extreme|Mini))", "Top", None),  # only recent ROG
    (r"^ASUS", "Mid", None),
    (r"^RAWM (ER21|Leviathan V4)", "Top", None),                           # only recent RAWM
    (r"^RAWM", "Other", None),
    (r"^Zowie", "Top", "Wireless"),                                        # Zowie wireless takes priority
    (r"^Zowie", "Mid", None),
    (r"^Corsair Sabre", "Mid", None),                                      # Sabre lineup is mid tier
]
# Editor's choice mice (exact names as they appear in the database). They get bonus points
# and are never hidden as "Dated". Add new names here as the database grows.
EDITORS_PICKS = [
    "Hitscan Hyperlight",
    "Logitech G Pro X Superlight", "Logitech G Pro X Superlight 2", "Logitech G Pro X2 Superstrike",
    "Razer DeathAdder V3 HyperSpeed", "Razer DeathAdder V3", "Razer DeathAdder V4 Pro",
    "Razer Viper V3 Pro", "Razer Viper V4 Pro",
    "Endgame Gear OP1 8k", "Endgame Gear OP1 8k v2", "Endgame Gear XM2 8k", "Endgame Gear XM2 8k v2",
    "Endgame Gear OP1w 4k", "Endgame Gear OP1w 4k v2", "Endgame Gear XM2w 4k", "Endgame Gear XM2w 4k v2",
    "LAMZU MAYA X", "LAMZU MAYA", "LAMZU MAYA 4K",
    "ATK F1 V2 Extreme", "ATK F1 V2 Ultimate", "ATK F1 V2 Ultra Max", "ATK F1 V3",
    "ATK A9 Air", "ATK A9 Air+", "ATK Phantom",
    "RAWM Leviathan V4", "MelGeek Horus",
]
EDITOR_POINTS = 10
# tier -> (budget stretch %, brand points)
TIER_DEFAULTS = {"Top": (20, 8), "Mid": (10, 5), "Other": (0, 0), "Low-mid": (0, -4)}
TIER_LABEL = {"Top": "Top", "Mid": "Mid / enthusiast", "Other": "Other", "Low-mid": "Low to mid"}

# ----------------------------------------------------------------------------
# GRIPS & HANDS
# ----------------------------------------------------------------------------
# Target mouse size as a fraction of hand size (community rule of thumb, tune freely).
GRIPS = {
    "Palm": dict(
        len_r=0.67, wid_r=0.74, height=41.0, len_sig=(4.5, 8.0),
        blurb="Your whole palm rests on the mouse and your fingers lie flat on the buttons.",
        best="Longer, taller mice with a rounded hump.",
    ),
    "Claw": dict(
        len_r=0.64, wid_r=0.72, height=39.5, len_sig=(5.0, 6.5),
        blurb="The back of your palm touches the mouse while your fingers arch over the buttons.",
        best="Medium mice with the hump toward the back.",
    ),
    "Fingertip": dict(
        len_r=0.60, wid_r=0.68, height=37.5, len_sig=(5.0, 6.0),
        blurb="Only your fingertips touch the mouse. Your palm floats above it.",
        best="Short, low, light mice.",
    ),
}
HAND_PRESETS = {"Small": (17.0, 7.8), "Medium": (18.5, 8.5), "Large": (20.0, 9.3)}

HUMP_SCORE = {
    "Palm":      {"Back - moderate": 1.0, "Center": 0.9, "Back - aggressive": 0.8, "Back - minimal": 0.7},
    "Claw":      {"Back - aggressive": 1.0, "Back - moderate": 1.0, "Back - minimal": 0.8, "Center": 0.6},
    "Fingertip": {"Back - minimal": 1.0, "Center": 0.9, "Back - moderate": 0.7, "Back - aggressive": 0.4},
}
SHAPE_SCORE = {
    "Palm":      {"Ergonomic": 1.0, "Hybrid": 0.9, "Symmetrical": 0.85},
    "Claw":      {"Symmetrical": 1.0, "Hybrid": 0.9, "Ergonomic": 0.7},
    "Fingertip": {"Symmetrical": 1.0, "Hybrid": 0.8, "Ergonomic": 0.5},
}


# Length: (tolerance when the mouse is shorter than ideal, when it is longer). A longer mouse is
# easier to live with than a shorter one, so the long side is more forgiving.
# Width: the target is kept inside the range real mice come in, and tolerance is a bit wider.
WIDTH_RANGE = (56.0, 70.0)
WIDTH_SIGMA = 4.5
# Top-tier brands and editor's choice mice are proven designs, so they get a small allowance on
# hand fit: this share of the gap to a perfect fit is forgiven (combined when both apply).
FIT_FORGIVENESS = {"Top": 0.08, "Editor": 0.12}
FORGIVE_WITHIN_MM = 10.0   # no allowance when the mouse is further than this from the ideal length


def targets(grip: str, hand_len_mm: float, hand_wid_mm: float) -> dict:
    g = GRIPS[grip]
    width = min(max(hand_wid_mm * g["wid_r"], WIDTH_RANGE[0]), WIDTH_RANGE[1])
    return dict(length=hand_len_mm * g["len_r"], width=width, height=g["height"])


# ----------------------------------------------------------------------------
# MODERNITY  (the database has no release year, so we infer age from the tech)
# ----------------------------------------------------------------------------
# Sensor generation is read from tracking speed (IPS): 750+ is today's flagship
# class, ~650 the 2021-23 flagships, <400 is 2016-19 tech. A few well-known
# sensors are pinned by hand where IPS misleads.
SENSOR_PIN = {"Focus Pro 45K": 1.00, "PAW3311": 0.50, "PAW3335": 0.55, "PAW3370": 0.55, "PMW3360": 0.30,
              "PMW3389": 0.40, "PMW3325": 0.15, "PAW3327": 0.25}
IPS_BANDS = ((750, 1.00), (650, 0.85), (450, 0.60), (400, 0.50), (300, 0.40), (200, 0.25))
ERA_CURRENT, ERA_MAINSTREAM = 0.70, 0.50


def sensor_score(sensor, ips) -> float:
    if isinstance(sensor, str) and sensor.strip() in SENSOR_PIN:
        return SENSOR_PIN[sensor.strip()]
    if pd.isna(ips):
        return 0.35
    for threshold, value in IPS_BANDS:
        if ips >= threshold:
            return value
    return 0.10


def polling_score(hz) -> float:
    if hz >= 4000:
        return 1.0
    if hz >= 2000:
        return 0.75
    if hz >= 1000:
        return 0.5
    return 0.1


def era_label(m: float) -> str:
    return "Current" if m >= ERA_CURRENT else ("Mainstream" if m >= ERA_MAINSTREAM else "Dated")


# ----------------------------------------------------------------------------
# DATA
# ----------------------------------------------------------------------------
def classify(brand: str, name: str, connectivity: str) -> str:
    for pattern, tier, conn in NAME_RULES:
        if re.search(pattern, name, flags=re.I) and (conn is None or conn == connectivity):
            return tier
    for tier, brands in TIER_BRANDS.items():
        if brand.lower() in (b.lower() for b in brands):
            return tier
    return "Other"


def estimate_price(row) -> float:
    """Rough USD guess from tier + tech. Only a placeholder until real prices exist."""
    p = {"Top": 45, "Mid": 30, "Other": 20, "Low-mid": 14}[row["Tier"]]
    p += 22 if row["Connectivity"] == "Wireless" else 0
    p += 28 * row["Modernity"]
    w = row["Weight (grams)"]
    p += 8 if w <= 50 else (4 if w <= 60 else 0)
    mat = str(row["Material"]).lower()
    p += 25 if "magnesium" in mat else (10 if "carbon" in mat else 0)
    if row["Tier"] == "Top":
        p *= 1.2
    return float(max(10, 5 * round(p / 5)))


def load_db() -> pd.DataFrame:
    df = pd.read_csv(DB_PATH, sep=";")
    for c in ["Length (mm)", "Width (mm)", "Height (mm)", "Weight (grams)",
              "Polling rate (Hz)", "Tracking speed (IPS)"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["Weight (grams)"] = df["Weight (grams)"].fillna(df["Weight (grams)"].median())
    df["Polling rate (Hz)"] = df["Polling rate (Hz)"].fillna(1000)
    # drop non-mouse outliers (rings, trackballs, oversized devices)
    df = df[df["Length (mm)"].between(75, 140) & df["Width (mm)"].between(45, 80)].copy()
    df["Brand"] = df["Brand"].replace(BRAND_FIX)
    df["Tier"] = [classify(b, n, c) for b, n, c in zip(df["Brand"], df["Name"], df["Connectivity"])]
    picks = {n.lower() for n in EDITORS_PICKS}
    df["Editor"] = df["Name"].str.lower().isin(picks)
    df["Modernity"] = (0.7 * df.apply(lambda r: sensor_score(r["Sensor"], r["Tracking speed (IPS)"]), axis=1)
                       + 0.3 * df["Polling rate (Hz)"].map(polling_score))
    df["Era"] = df["Modernity"].map(era_label)
    df["Price"] = df.apply(estimate_price, axis=1)
    df["Price source"] = "estimate"
    return df.reset_index(drop=True)


def read_prices(src) -> pd.DataFrame | None:
    """Read a prices file with at least Name,Price_USD columns."""
    try:
        p = pd.read_csv(src, sep=None, engine="python")
        p.columns = [c.strip() for c in p.columns]
        return p[["Name", "Price_USD"]].dropna()
    except Exception:
        return None


def apply_prices(df: pd.DataFrame, prices: pd.DataFrame | None) -> pd.DataFrame:
    if prices is None or prices.empty:
        return df
    df = df.copy()
    lookup = dict(zip(prices["Name"].str.lower().str.strip(), prices["Price_USD"]))
    key = df["Name"].str.lower().str.strip()
    hit = key.isin(lookup)
    df.loc[hit, "Price"] = key[hit].map(lookup).astype(float)
    df.loc[hit, "Price source"] = "verified"
    return df


# ----------------------------------------------------------------------------
# SCORING
# ----------------------------------------------------------------------------
def _gauss(delta, sigma):
    return np.exp(-0.5 * (delta / sigma) ** 2)


RECENCY_POINTS = {"Low": 10, "Medium": 20, "High": 30}
WEIGHT_POINTS = {"Don't mind": 0, "Prefer light": 4, "Ultralight": 7}


def score(df, grip, hand_len_mm, hand_wid_mm, tier_cfg, weight_pref="Prefer light", recency="Medium",
          editor_pts=EDITOR_POINTS):
    t = targets(grip, hand_len_mm, hand_wid_mm)
    out = df.copy()
    d_len = out["Length (mm)"] - t["length"]
    s_len = _gauss(d_len, np.where(d_len < 0, GRIPS[grip]["len_sig"][0], GRIPS[grip]["len_sig"][1]))
    s_wid = _gauss(out["Width (mm)"] - t["width"], WIDTH_SIGMA)
    s_hgt = _gauss(out["Height (mm)"] - t["height"], 3.0)
    s_hump = out["Hump placement"].map(HUMP_SCORE[grip]).fillna(0.6)
    s_shape = out["Shape"].map(SHAPE_SCORE[grip]).fillna(0.85)
    out["s_len"], out["s_wid"], out["s_hump"] = s_len, s_wid, s_hump
    out["Fit raw"] = 70 * (0.40 * s_len + 0.18 * s_wid + 0.12 * s_hgt + 0.18 * s_hump + 0.12 * s_shape)
    allow = 1 - (1 - np.where(out["Tier"] == "Top", FIT_FORGIVENESS["Top"], 0.0)) \
                * (1 - np.where(out["Editor"], FIT_FORGIVENESS["Editor"], 0.0))
    allow = allow * (np.abs(d_len) <= FORGIVE_WITHIN_MM)
    out["Fit"] = out["Fit raw"] + allow * (70 - out["Fit raw"])
    out["Recency"] = RECENCY_POINTS[recency] * out["Modernity"]
    out["Weight bonus"] = WEIGHT_POINTS[weight_pref] * ((80 - out["Weight (grams)"]) / 40).clip(0, 1)
    out["Brand pts"] = out["Tier"].map(lambda k: tier_cfg[k][1])
    out["Editor pts"] = np.where(out["Editor"], editor_pts, 0)
    out["Raw"] = out["Fit"] + out["Recency"] + out["Weight bonus"] + out["Brand pts"] + out["Editor pts"]
    # Display score: share of the best possible total under the current settings, so a
    # perfect-fit editor's choice from a top brand reads 100 and the rest stay distinguishable.
    best = (70 + RECENCY_POINTS[recency] + WEIGHT_POINTS[weight_pref]
            + max(v[1] for v in tier_cfg.values()) + editor_pts)
    out["Score"] = (out["Raw"] / best * 100).clip(0, 100)
    return out


def budget_caps(budget, tier_cfg) -> dict:
    return {k: round(budget * (1 + v[0] / 100)) for k, v in tier_cfg.items()}


MIN_FIT = 35  # out of 70: below this a mouse simply doesn't suit the hand/grip


def recommend(scored, budget, tier_cfg, include_dated=False, max_per_brand=2, n=10):
    caps = scored["Tier"].map(budget_caps(budget, tier_cfg))
    out = scored.assign(**{"Budget cap": caps})
    out = out[(out["Price"] <= out["Budget cap"]) & (out["Fit"] >= MIN_FIT)]
    if not include_dated:
        out = out[(out["Era"] != "Dated") | out["Editor"]]
    out = out.sort_values("Raw", ascending=False)
    out = out.groupby("Brand", sort=False).head(max_per_brand)
    return out.sort_values("Raw", ascending=False).head(n).reset_index(drop=True)


def cheapest_fit(scored, include_dated=False):
    """Cheapest mouse that fits the hand (used to explain an empty result)."""
    pool = scored[scored["Fit"] >= MIN_FIT]
    if not include_dated:
        pool = pool[(pool["Era"] != "Dated") | pool["Editor"]]
    return None if pool.empty else pool.sort_values("Price").iloc[0]


def reasons(row, grip, hand_len_mm, hand_wid_mm, tier_cfg) -> list[str]:
    t = targets(grip, hand_len_mm, hand_wid_mm)
    out = []
    if row["Editor"]:
        out.append("Editor's choice")
    dl = row["Length (mm)"] - t["length"]
    if abs(dl) <= 4:
        out.append(f"Length ({row['Length (mm)']:.0f} mm) is right for your hand")
    elif dl > 0:
        out.append(f"Runs long for your hand (+{dl:.0f} mm)")
    else:
        out.append(f"Runs short for your hand ({dl:.0f} mm)")
    dw = row["Width (mm)"] - t["width"]
    if abs(dw) > 6:
        out.append(f"{'Wider' if dw > 0 else 'Narrower'} than ideal ({dw:+.0f} mm)")
    if row["Fit raw"] < MIN_FIT:
        out.append("Borderline fit, included as a proven design")
    if row["s_hump"] >= 0.9:
        out.append(f"{row['Hump placement'].replace(' - ', ', ').lower()} hump suits {grip.lower()} grip")
    tech = [str(row["Sensor"])] if isinstance(row["Sensor"], str) else []
    if row["Polling rate (Hz)"] >= 4000:
        tech.append(f"{row['Polling rate (Hz)'] / 1000:.0f}K polling")
    if tech:
        out.append(f"{row['Era']} tech: " + ", ".join(tech))
    if row["Weight (grams)"] <= 55:
        out.append(f"Light at {row['Weight (grams)']:.0f} g")
    pts = tier_cfg[row["Tier"]][1]
    if pts:
        out.append(f"{TIER_LABEL[row['Tier']]} brand tier ({pts:+d} pts)")
    return out[:6]
