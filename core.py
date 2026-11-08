"""
Core logic for the mouse recommender (no Streamlit imports, so it can be
tested and reused by fetch_prices.py).

Score (0-100) = fit (0-70) + modernity (0-20/30) + weight bonus (0-7) + brand points
Eligibility   = price <= budget * (1 + tier stretch)  and  era is not "Dated"
"""
from __future__ import annotations

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
    "Top": ["Logitech", "Razer", "Zowie", "Finalmouse", "VAXEE", "Endgame Gear",
            "SteelSeries", "Pulsar", "LAMZU", "G-Wolves", "Corsair", "ASUS"],
    "Good": ["ATK", "VGN", "MCHOSE", "Keychron", "Glorious", "HyperX", "Rapoo",
             "Hator", "Ninjutso", "Waizowl", "WLMOUSE", "Kysona", "Xtrfy"],
    "Low": ["Attack Shark", "AJAZZ", "RK", "Darmoshark", "EWEADN", "Redragon", "Delux"],
}
# tier -> (budget stretch %, brand points)
TIER_DEFAULTS = {"Top": (20, 8), "Good": (10, 5), "Neutral": (0, 0), "Low": (0, -6)}
TIER_LABEL = {"Top": "Top brand", "Good": "Trusted brand", "Neutral": "Other brand", "Low": "Budget brand"}

# ----------------------------------------------------------------------------
# GRIPS & HANDS
# ----------------------------------------------------------------------------
# Target mouse size as a fraction of hand size (community rule of thumb, tune freely).
GRIPS = {
    "Palm": dict(
        len_r=0.67, wid_r=0.74, height=41.0,
        blurb="Your whole palm rests on the mouse and your fingers lie flat on the buttons.",
        best="Longer, taller mice with a rounded hump.",
    ),
    "Claw": dict(
        len_r=0.64, wid_r=0.72, height=39.5,
        blurb="The back of your palm touches the mouse while your fingers arch over the buttons.",
        best="Medium mice with the hump toward the back.",
    ),
    "Fingertip": dict(
        len_r=0.60, wid_r=0.68, height=37.5,
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


def targets(grip: str, hand_len_mm: float, hand_wid_mm: float) -> dict:
    g = GRIPS[grip]
    return dict(length=hand_len_mm * g["len_r"], width=hand_wid_mm * g["wid_r"], height=g["height"])


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
def brand_tier(brand: str) -> str:
    for tier, brands in TIER_BRANDS.items():
        if brand.lower() in (b.lower() for b in brands):
            return tier
    return "Neutral"


def estimate_price(row) -> float:
    """Rough USD guess from tier + tech. Only a placeholder until real prices exist."""
    p = {"Top": 45, "Good": 28, "Neutral": 20, "Low": 14}[row["Tier"]]
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
    df["Tier"] = df["Brand"].map(brand_tier)
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


def score(df, grip, hand_len_mm, hand_wid_mm, tier_cfg, weight_pref="Prefer light", recency="Medium"):
    t = targets(grip, hand_len_mm, hand_wid_mm)
    out = df.copy()
    s_len = _gauss(out["Length (mm)"] - t["length"], 5.0)
    s_wid = _gauss(out["Width (mm)"] - t["width"], 3.0)
    s_hgt = _gauss(out["Height (mm)"] - t["height"], 3.0)
    s_hump = out["Hump placement"].map(HUMP_SCORE[grip]).fillna(0.6)
    s_shape = out["Shape"].map(SHAPE_SCORE[grip]).fillna(0.85)
    out["s_len"], out["s_wid"], out["s_hump"] = s_len, s_wid, s_hump
    out["Fit"] = 70 * (0.40 * s_len + 0.18 * s_wid + 0.12 * s_hgt + 0.18 * s_hump + 0.12 * s_shape)
    out["Recency"] = RECENCY_POINTS[recency] * out["Modernity"]
    out["Weight bonus"] = WEIGHT_POINTS[weight_pref] * ((80 - out["Weight (grams)"]) / 40).clip(0, 1)
    out["Brand pts"] = out["Tier"].map(lambda k: tier_cfg[k][1])
    out["Raw"] = out["Fit"] + out["Recency"] + out["Weight bonus"] + out["Brand pts"]
    out["Score"] = out["Raw"].clip(0, 100)   # display score; "Raw" keeps ties ordered
    return out


def budget_caps(budget, tier_cfg) -> dict:
    return {k: round(budget * (1 + v[0] / 100)) for k, v in tier_cfg.items()}


MIN_FIT = 35  # out of 70: below this a mouse simply doesn't suit the hand/grip


def recommend(scored, budget, tier_cfg, include_dated=False, max_per_brand=2, n=10):
    caps = scored["Tier"].map(budget_caps(budget, tier_cfg))
    out = scored.assign(**{"Budget cap": caps})
    out = out[(out["Price"] <= out["Budget cap"]) & (out["Fit"] >= MIN_FIT)]
    if not include_dated:
        out = out[out["Era"] != "Dated"]
    out = out.sort_values("Raw", ascending=False)
    out = out.groupby("Brand", sort=False).head(max_per_brand)
    return out.sort_values("Raw", ascending=False).head(n).reset_index(drop=True)


def cheapest_fit(scored, include_dated=False):
    """Cheapest mouse that fits the hand (used to explain an empty result)."""
    pool = scored[scored["Fit"] >= MIN_FIT]
    if not include_dated:
        pool = pool[pool["Era"] != "Dated"]
    return None if pool.empty else pool.sort_values("Price").iloc[0]


def reasons(row, grip, hand_len_mm, hand_wid_mm, tier_cfg) -> list[str]:
    t = targets(grip, hand_len_mm, hand_wid_mm)
    out = []
    dl = row["Length (mm)"] - t["length"]
    if abs(dl) <= 4:
        out.append(f"Length ({row['Length (mm)']:.0f} mm) is right for your hand")
    elif dl > 0:
        out.append(f"A little long for your hand (+{dl:.0f} mm)")
    else:
        out.append(f"A little short for your hand ({dl:.0f} mm)")
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
        out.append(f"{TIER_LABEL[row['Tier']]} ({pts:+d} pts)")
    return out[:4]
