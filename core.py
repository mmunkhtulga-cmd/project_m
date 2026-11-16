"""
Core logic for the mouse recommender (no Streamlit imports, so it can be
tested and reused by fetch_prices.py).

Raw score = fit (0-70) + newer tech (0-10/20/30) + weight bonus (0-7) + brand points + editor's choice
Displayed score = raw as a % of the best possible total
Eligibility   = price <= budget * (1 + tier stretch). Mice with outdated sensors are removed
                from the database on load (see OUTDATED_SENSOR), so there is no "dated" toggle.
"""
from __future__ import annotations

import re
import urllib.parse
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).parent
DB_PATH = HERE / "mouse_db.csv"
PRICES_PATH = HERE / "prices.csv"
LINKS_PATH = HERE / "links.csv"          # optional: Name,MaxGaming_URL,Amazon_URL (exact product pages)
DATA_SOURCE = "mouse_db.csv: specification database of gaming mice (dimensions, weight, shape, sensor, connectivity)"
AMAZON_TAG = ""                          # your Amazon Associates tag, e.g. "yourtag-20" (optional)

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
# Whole families of editor's choice mice (regex on the full name)
EDITORS_PATTERNS = [r"^LAMZU Thorn", r"^LAMZU Atlantis Mini",      # not the regular Atlantis
                    r"^Scyrox V(6|8)\b", r"^MCHOSE L7( Pro)?\b"]
# Editor's choice by name AND sensor: (regex on name, regex on sensor). Recent ATK mice with PAW3950/3955.
EDITORS_SENSOR_RULES = [(r"^ATK\b", r"3950|3955")]
# Budget edge: these ATK mice get VALUE_EDGE_PTS extra points when the budget is <= VALUE_BUDGET_MAX.
VALUE_PATTERN = r"^ATK (?:A9 Air|F1 V2 (?:Ultimate|Extreme)|Zero|Ghost|U2 V2|Z1 V2|X1 V2)"
VALUE_EDGE_PTS = 4
VALUE_BUDGET_MAX = 80
# Superseded models removed from the database (regex on name): the v1 OP1 and XM2 (their v2 stays).
EXCLUDE_PATTERNS = [r"^Endgame Gear (?:OP1|XM2)\w* \d+k$"]
# Grip focus: mice built for specific grips. (regex on name, grip families it is made for).
# A matching grip gets +GRIP_FOCUS_PTS, any other grip gets -GRIP_FOCUS_PTS. Entries are a family (Palm, Claw,
# Fingertip) or one exact grip (e.g. "Aggressive claw"); "Claw" covers all three claw types.
GRIP_FOCUS = [(r"^Endgame Gear OP1", ["Claw", "Fingertip"]),
              (r"^Endgame Gear XM2", ["Claw", "Palm"]),
              (r"^LAMZU Atlantis Mini", ["Claw", "Aggressive claw"])]
GRIP_FOCUS_PTS = 3
# Over-budget penalty: points lost per 100% over budget (a mouse 10% over loses 4 points).
OVER_BUDGET_PEN = 40
EDITOR_POINTS = 10

# "Not sure of my grip": universal-shape mice, by hand size (hand length: <17.5 small, <19.5 medium)
_MEDIUM_UP = ["Logitech G Pro X Superlight", "Logitech G Pro X Superlight 2", "Razer Viper V3 Pro",
              "Razer Viper V4 Pro", "RAWM Leviathan V4"]
UNIVERSAL = {
    "Small": ["Hitscan Hyperlight"],
    "Medium": _MEDIUM_UP,
    "Large": _MEDIUM_UP + ["MelGeek Horus"],
}
BRACKET_LIMITS_MM = (175, 195)
# Universal picks are the curated names above plus any symmetrical mouse in the pool whose hand
# average fit across palm, claw and fingertip is at least UNIVERSAL_MIN_FIT (of 70). Best UNIVERSAL_MAX kept.
UNIVERSAL_MIN_FIT = 40
UNIVERSAL_MAX = 12

# Sensors that are dropped from the database: PAW3335 / PAW3370 and older PixArt parts, plus
# generic or unlabelled sensors. Proprietary gaming sensors (HERO, BAMF, XS-1, Focus, TrueMove...)
# and PAW3311 are kept on purpose. Editor's choice mice are never dropped.
OUTDATED_SENSOR = (r"^(PMW|ADNS|A3\d|PAW3335|PAW3370|PAW3327|PAW3315|PAW3305|PAW3212|PAW3104"
                   r"|PAW3333|PAW3318|PAW3328)")
GENERIC_SENSORS = {"4G", "3G Laser", "8925", "8960", "A825", "S203", "S205", "S6006", "S9808", "AM010",
                   "BlueTrack", "Laser Engine", "MLT04", "Optical", "BC3332-A", "BC3332-S", "AIM-WL",
                   "AL530", "VB010411", "SDNS3988", "1855", "Advanced Optical Tracking", "AI", "F1", "Core"}
# tier -> (budget stretch %, brand points)
TIER_DEFAULTS = {"Top": (10, 8), "Mid": (5, 5), "Other": (0, 0), "Low-mid": (0, -4)}
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
    "Relaxed claw": dict(
        len_r=0.65, wid_r=0.72, height=40.0, len_sig=(5.0, 7.0),
        blurb="Fingers arched, but more of your palm rests on the mouse. Hump toward the middle.",
        best="Medium mice with a mid-center hump.",
    ),
    "Aggressive claw": dict(
        len_r=0.64, wid_r=0.72, height=39.5, len_sig=(5.0, 6.5),
        blurb="Fingers strongly arched, palm touches only at the back of the mouse.",
        best="Medium mice with a moderate to aggressive back hump.",
    ),
    "Pincer claw": dict(
        len_r=0.62, wid_r=0.70, height=38.5, len_sig=(5.0, 6.0),
        blurb="Between claw and fingertip: tight, high-arched fingers and very little palm contact.",
        best="Shorter, lower mice with a moderate back hump.",
    ),
    "Fingertip": dict(
        len_r=0.60, wid_r=0.68, height=37.5, len_sig=(5.0, 6.0),
        blurb="Only your fingertips touch the mouse. Your palm floats above it.",
        best="Short, low, light mice.",
    ),
}
# Grip families: the three claw types count as one when averaging over "all grips".
FAMILIES = {"Palm": ["Palm"], "Claw": ["Relaxed claw", "Aggressive claw", "Pincer claw"],
            "Fingertip": ["Fingertip"]}
HAND_PRESETS = {"Small": (17.0, 7.8), "Medium": (18.5, 8.5), "Large": (20.0, 9.3)}

HUMP_SCORE = {
    "Palm":      {"Back - moderate": 1.0, "Center": 0.9, "Back - aggressive": 0.8, "Back - minimal": 0.7},
    "Relaxed claw":    {"Center": 1.0, "Back - minimal": 0.85, "Back - moderate": 0.75, "Back - aggressive": 0.5},
    "Aggressive claw": {"Back - aggressive": 1.0, "Back - moderate": 1.0, "Back - minimal": 0.7, "Center": 0.45},
    "Pincer claw":     {"Back - moderate": 1.0, "Back - minimal": 0.9, "Back - aggressive": 0.85, "Center": 0.6},
    "Fingertip": {"Back - minimal": 1.0, "Center": 0.9, "Back - moderate": 0.7, "Back - aggressive": 0.4},
}
SHAPE_SCORE = {
    "Palm":      {"Ergonomic": 1.0, "Hybrid": 0.9, "Symmetrical": 0.85},
    "Relaxed claw":    {"Symmetrical": 1.0, "Hybrid": 0.9, "Ergonomic": 0.7},
    "Aggressive claw": {"Symmetrical": 1.0, "Hybrid": 0.9, "Ergonomic": 0.7},
    "Pincer claw":     {"Symmetrical": 1.0, "Hybrid": 0.9, "Ergonomic": 0.7},
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
    if grip == "Not sure":   # universal shapes: average over the three grips
        ts = [{k: sum(targets(g, hand_len_mm, hand_wid_mm)[k] for g in m) / len(m)
               for k in ("length", "width", "height")} for m in FAMILIES.values()]
        return {k: sum(t[k] for t in ts) / len(ts) for k in ("length", "width", "height")}
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


MISSING_COLS = ["Length (mm)", "Width (mm)", "Height (mm)", "Weight (grams)", "Polling rate (Hz)",
                "Tracking speed (IPS)", "Sensor"]


def load_db() -> pd.DataFrame:
    df = pd.read_csv(DB_PATH, sep=";")
    raw_rows = len(df)
    for c in ["Length (mm)", "Width (mm)", "Height (mm)", "Weight (grams)",
              "Polling rate (Hz)", "Tracking speed (IPS)"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    missing = {c: int(df[c].isna().sum()) for c in MISSING_COLS if c in df.columns}   # before filling
    df["Weight (grams)"] = df["Weight (grams)"].fillna(df["Weight (grams)"].median())
    df["Polling rate (Hz)"] = df["Polling rate (Hz)"].fillna(1000)
    # drop non-mouse outliers (rings, trackballs, oversized devices)
    df = df[df["Length (mm)"].between(75, 140) & df["Width (mm)"].between(45, 80)].copy()
    n_outliers = raw_rows - len(df)
    gone = df["Name"].apply(lambda n: any(re.search(p, n, flags=re.I) for p in EXCLUDE_PATTERNS))
    n_excluded = int(gone.sum())
    df = df[~gone].copy()
    df["Brand"] = df["Brand"].replace(BRAND_FIX)
    df["Tier"] = [classify(b, n, c) for b, n, c in zip(df["Brand"], df["Name"], df["Connectivity"])]
    picks = {n.lower() for n in EDITORS_PICKS}
    df["Editor"] = (df["Name"].str.lower().isin(picks)
                    | df["Name"].apply(lambda n: any(re.search(p, n, flags=re.I) for p in EDITORS_PATTERNS)))
    for name_re, sensor_re in EDITORS_SENSOR_RULES:
        df["Editor"] |= (df["Name"].str.contains(name_re, flags=re.I, regex=True, na=False)
                         & df["Sensor"].fillna("").astype(str).str.contains(sensor_re, regex=True))
    sensor = df["Sensor"].fillna("")
    outdated = sensor.str.match(OUTDATED_SENSOR) | sensor.isin(GENERIC_SENSORS) | (sensor == "")
    n_before = len(df)
    df = df[~outdated | df["Editor"]].copy()
    n_old = n_before - len(df)
    df["Modernity"] = (0.7 * df.apply(lambda r: sensor_score(r["Sensor"], r["Tracking speed (IPS)"]), axis=1)
                       + 0.3 * df["Polling rate (Hz)"].map(polling_score))
    df["Era"] = df["Modernity"].map(era_label)
    df["Price"] = df.apply(estimate_price, axis=1)
    df["Price source"] = "estimate"
    df = df.reset_index(drop=True)
    df.attrs["report"] = dict(raw=raw_rows, outliers=n_outliers, excluded=n_excluded, outdated=n_old, kept=len(df), missing=missing)
    return df


def read_prices(src) -> pd.DataFrame | None:
    """Read a prices file with at least Name,Price_USD columns."""
    try:
        p = pd.read_csv(src, sep=None, engine="python")
        p.columns = [c.strip() for c in p.columns]
        cols = ["Name", "Price_USD"] + (["Source"] if "Source" in p.columns else [])
        return p[cols].dropna(subset=["Name", "Price_USD"])
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
    df["Price where"] = ""
    if "Source" in prices.columns:
        where = dict(zip(prices["Name"].str.lower().str.strip(), prices["Source"].fillna("")))
        df.loc[hit, "Price where"] = key[hit].map(where).fillna("")
    return df


# ----------------------------------------------------------------------------
# SCORING
# ----------------------------------------------------------------------------
def _gauss(delta, sigma):
    return np.exp(-0.5 * (delta / sigma) ** 2)


RECENCY_POINTS = {"Low": 10, "Medium": 20, "High": 30}
WEIGHT_POINTS = {"Don't mind": 0, "Prefer light": 4, "Ultralight": 7}
# Weight classes (grams). Ultralight <= 50, light 51-65, medium 66-80, heavy 81+.
WEIGHT_CLASSES = [(50, "Ultralight"), (65, "Light"), (80, "Medium")]
# Weight bonus ramp per preference: (full points up to, zero points from). "Prefer light" fully
# rewards anything up to 65 g; "Ultralight" only rewards 50 g and below.
WEIGHT_RAMP = {"Don't mind": (0, 1), "Prefer light": (65, 80), "Ultralight": (50, 65)}


def weight_class(grams) -> str:
    return next((name for limit, name in WEIGHT_CLASSES if round(grams) <= limit), "Heavy")


def _fit(df, grip, hand_len_mm, hand_wid_mm):
    """Hand fit (0-70) of every row for one grip, plus the pieces the cards need."""
    t = targets(grip, hand_len_mm, hand_wid_mm)
    d_len = df["Length (mm)"] - t["length"]
    s_len = _gauss(d_len, np.where(d_len < 0, GRIPS[grip]["len_sig"][0], GRIPS[grip]["len_sig"][1]))
    s_wid = _gauss(df["Width (mm)"] - t["width"], WIDTH_SIGMA)
    s_hgt = _gauss(df["Height (mm)"] - t["height"], 3.0)
    s_hump = df["Hump placement"].map(HUMP_SCORE[grip]).fillna(0.6)
    s_shape = df["Shape"].map(SHAPE_SCORE[grip]).fillna(0.85)
    fit_raw = 70 * (0.40 * s_len + 0.18 * s_wid + 0.12 * s_hgt + 0.18 * s_hump + 0.12 * s_shape)
    return fit_raw, d_len, s_len, s_wid, s_hump


def grip_family(grip: str) -> str:
    return next((f for f, members in FAMILIES.items() if grip in members), grip)


def grip_focus(name: str):
    """Grip families a mouse is built for, or None."""
    return next((g for pattern, g in GRIP_FOCUS if re.search(pattern, name, flags=re.I)), None)


def score(df, grip, hand_len_mm, hand_wid_mm, tier_cfg, weight_pref="Prefer light", recency="Medium",
          editor_pts=EDITOR_POINTS, budget=None):
    out = df.copy()
    fit_raw, d_len, s_len, s_wid, s_hump = _fit(out, grip, hand_len_mm, hand_wid_mm)
    out["s_len"], out["s_wid"], out["s_hump"] = s_len, s_wid, s_hump
    out["Fit raw"] = fit_raw
    allow = 1 - (1 - np.where(out["Tier"] == "Top", FIT_FORGIVENESS["Top"], 0.0)) \
                * (1 - np.where(out["Editor"], FIT_FORGIVENESS["Editor"], 0.0))
    allow = allow * (np.abs(d_len) <= FORGIVE_WITHIN_MM)
    out["Fit"] = out["Fit raw"] + allow * (70 - out["Fit raw"])
    out["Recency"] = RECENCY_POINTS[recency] * out["Modernity"]
    full, zero = WEIGHT_RAMP[weight_pref]
    out["Weight bonus"] = WEIGHT_POINTS[weight_pref] * ((zero - out["Weight (grams)"]) / (zero - full)).clip(0, 1)
    out["Brand pts"] = out["Tier"].map(lambda k: tier_cfg[k][1])
    out["Editor pts"] = np.where(out["Editor"], editor_pts, 0)
    out["Raw"] = out["Fit"] + out["Recency"] + out["Weight bonus"] + out["Brand pts"] + out["Editor pts"]
    fam = grip_family(grip)
    out["Grip adj"] = out["Name"].map(grip_focus).map(
        lambda f: 0.0 if f is None else (GRIP_FOCUS_PTS if (fam in f or grip in f) else -GRIP_FOCUS_PTS)).astype(float)
    out["Raw"] += out["Grip adj"]
    out["Budget adj"] = 0.0
    if budget:
        if budget <= VALUE_BUDGET_MAX:
            out["Budget adj"] += VALUE_EDGE_PTS * out["Name"].str.contains(VALUE_PATTERN, flags=re.I, regex=True)
        out["Budget adj"] -= OVER_BUDGET_PEN * ((out["Price"] - budget) / budget).clip(lower=0)
        out["Raw"] += out["Budget adj"]
    # Display score: share of the best possible total under the current settings, so a
    # perfect-fit editor's choice from a top brand reads 100 and the rest stay distinguishable.
    out["Score"] = (out["Raw"] / _best(tier_cfg, weight_pref, recency, editor_pts) * 100).clip(0, 100)
    return out


def _best(tier_cfg, weight_pref, recency, editor_pts):
    return (70 + RECENCY_POINTS[recency] + WEIGHT_POINTS[weight_pref]
            + max(v[1] for v in tier_cfg.values()) + editor_pts)


def budget_caps(budget, tier_cfg) -> dict:
    return {k: round(budget * (1 + v[0] / 100)) for k, v in tier_cfg.items()}


MIN_FIT = 35  # out of 70: below this a mouse simply doesn't suit the hand/grip


def recommend(scored, budget, tier_cfg, max_per_brand=2, n=10):
    caps = scored["Tier"].map(budget_caps(budget, tier_cfg))
    out = scored.assign(**{"Budget cap": caps})
    out = out[(out["Price"] <= out["Budget cap"]) & (out["Fit"] >= MIN_FIT)]
    out = out.sort_values("Raw", ascending=False)
    out = out.groupby("Brand", sort=False).head(max_per_brand)
    return out.sort_values("Raw", ascending=False).head(n).reset_index(drop=True)


def cheapest_fit(scored):
    """Cheapest mouse that fits the hand (used to explain an empty result)."""
    pool = scored[scored["Fit"] >= MIN_FIT]
    return None if pool.empty else pool.sort_values("Price").iloc[0]


# ----------------------------------------------------------------------------
# "NOT SURE OF MY GRIP"
# ----------------------------------------------------------------------------
def hand_bracket(hand_len_mm: float) -> str:
    return "Small" if hand_len_mm < BRACKET_LIMITS_MM[0] else ("Medium" if hand_len_mm < BRACKET_LIMITS_MM[1] else "Large")


def universal_picks(pool, hand_len_mm, hand_wid_mm, tier_cfg, weight_pref="Prefer light",
                    recency="Medium", editor_pts=EDITOR_POINTS):
    """Curated universal-shape mice for this hand size, ranked by their average score over all grips.
    Budget is not a hard filter here (the list is curated); the UI flags picks above budget."""
    names = UNIVERSAL[hand_bracket(hand_len_mm)]
    fits = pd.concat([pd.concat([_fit(pool, g, hand_len_mm, hand_wid_mm)[0] for g in m], axis=1).mean(axis=1)
                      for m in FAMILIES.values()], axis=1).mean(axis=1)
    cand = pool[pool["Name"].isin(names) | ((pool["Shape"] == "Symmetrical") & (fits >= UNIVERSAL_MIN_FIT))]
    if cand.empty:
        return cand.assign(Raw=[], Score=[])
    raws, base = [], None
    for members in FAMILIES.values():
        fam = [score(cand, g, hand_len_mm, hand_wid_mm, tier_cfg, weight_pref, recency, editor_pts) for g in members]
        raws.append(pd.concat([f.set_index("Name")["Raw"] for f in fam], axis=1).mean(axis=1))
        if members[0] == FAMILIES["Claw"][0]:
            base = fam[0]
    out = base.copy()
    out["Raw"] = out["Name"].map(pd.concat(raws, axis=1).mean(axis=1))
    out["Score"] = (out["Raw"] / _best(tier_cfg, weight_pref, recency, editor_pts) * 100).clip(0, 100)
    return out.sort_values("Raw", ascending=False).head(UNIVERSAL_MAX).reset_index(drop=True)


# ----------------------------------------------------------------------------
# CARD HELPERS (text, links)
# ----------------------------------------------------------------------------
def split_name(name: str, brand: str):
    model = name[len(brand):].strip() if name.lower().startswith(brand.lower()) else name
    return brand, (model or name)


def grip_fits(rows, hand_len_mm, hand_wid_mm):
    """Add fit_<grip> columns (raw hand fit 0-70 for each grip)."""
    rows = rows.copy()
    for g in GRIPS:
        rows[f"fit_{g}"] = _fit(rows, g, hand_len_mm, hand_wid_mm)[0].values
    return rows


GOOD_FIT = 49   # 70% of the 70 fit points counts as "suits this grip"


def suits(row) -> list[str]:
    focus = grip_focus(row["Name"])
    if focus:
        return list(focus)
    ok = [g for g in GRIPS if row.get(f"fit_{g}", 0) >= GOOD_FIT]
    if not ok:
        ok = [max(GRIPS, key=lambda g: row.get(f"fit_{g}", 0))]
    if all(g in ok for g in FAMILIES["Claw"]):
        ok = [g for g in ok if g not in FAMILIES["Claw"]]
        ok.insert(1 if "Palm" in ok else 0, "Claw")
    return ok


def describe(row, universal=False) -> str:
    if universal:
        return "Universal shape that works for palm, claw and fingertip."
    length = row["Length (mm)"]
    size = "Compact" if length < 114 else ("Mid-size" if length < 122 else "Full-size")
    shape = f" {row['Shape'].lower()}" if row["Shape"] in ("Symmetrical", "Hybrid", "Ergonomic") else ""
    grips = " / ".join(g.lower() for g in suits(row))
    return f"{size}{shape} {row['Connectivity'].lower()} mouse for {grips}."


def why_chips(row, grip, hand_len_mm, conn_pref, budget) -> list[str]:
    chips = []
    cm = int(hand_len_mm // 10)
    chips.append(f"{cm}-{cm + 1} cm ({hand_bracket(hand_len_mm)}) hand")
    if grip == "Not sure":
        chips.append("Universal shape")
    elif row.get(f"fit_{grip}", 0) >= GOOD_FIT:
        chips.append(f"{grip} grip support")
    if row["Editor"]:
        chips.append("Editor's choice")
    if budget <= VALUE_BUDGET_MAX and re.search(VALUE_PATTERN, row["Name"], flags=re.I):
        chips.append("Budget value pick")
    if conn_pref != "Any" and row["Connectivity"] == conn_pref:
        chips.append(f"{conn_pref} preference")
    if row["Polling rate (Hz)"] >= 4000:
        chips.append(f"{row['Polling rate (Hz)'] / 1000:.0f}K polling")
    if row["Price"] <= budget:
        chips.append("Within budget")
    return chips[:5]


@lru_cache(maxsize=1)
def _links_table():
    if not LINKS_PATH.exists():
        return {}
    try:
        t = pd.read_csv(LINKS_PATH).fillna("")
        return {r["Name"].lower().strip(): (r.get("MaxGaming_URL", ""), r.get("Amazon_URL", ""))
                for _, r in t.iterrows()}
    except Exception:
        return {}


def retailer_links(name: str) -> dict:
    """{'maxgaming': (url, exact), 'amazon': (url, exact)}. Without an exact product page in
    links.csv the buttons fall back to a search, and the UI labels them as searches."""
    mg, az = _links_table().get(name.lower().strip(), ("", ""))
    q = urllib.parse.quote_plus(name)
    tag = f"&tag={AMAZON_TAG}" if AMAZON_TAG else ""
    return dict(
        maxgaming=(mg or f"https://www.google.com/search?q=site%3Aus.maxgaming.com+{q}", bool(mg)),
        amazon=((az + (tag.replace("&", "?" if "?" not in az else "&", 1) if az and AMAZON_TAG and "tag=" not in az else ""))
                if az else f"https://www.amazon.com/s?k={q}{tag}", bool(az)),
    )
