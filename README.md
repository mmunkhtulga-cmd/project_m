# Mouse finder

Pick a gaming mouse that actually fits your hand. Enter your hand size, grip and budget, and the app ranks
mice from a specification database by how well their measured size and shape match you, then explains each
ranking with charts.

Live app: _add your Streamlit Cloud link here_

## Run it

    pip install -r requirements.txt
    streamlit run app.py

## Deploy on Streamlit Cloud

1. Push this folder to a GitHub repo. It must include `mouse_db.csv`, `prices.csv`, `links.csv`,
   `requirements.txt` and `.streamlit/config.toml` (the theme).
2. On share.streamlit.io choose New app, pick the repo, set the main file to `app.py`, and deploy.

## How the app works

Hand size -> grip (relaxed, aggressive or pincer claw, palm, fingertip, or "not sure") -> budget -> results.

Results are split into tabs:

| Tab | What it shows |
|---|---|
| Top matches | The 3 best mice as cards: weight class, connection, grips it suits, why it matches, price, shop links |
| Compare | Size map (your ideal vs each mouse), price vs match score, and a stacked bar of how each score is built |
| Full list | Ranked table of up to 40 mice, downloadable as CSV |
| Dataset | Source, cleaning steps with live row counts, missing-value table, weight and length charts |
| About | Purpose, scoring rules, limits |

The sidebar filters (budget, hand, connection, shape, max weight, weight preference, newer tech, results per
brand, brand tier points) update every tab live.

## Dataset

`mouse_db.csv` (semicolon separated). One row per mouse. Set `DATA_SOURCE` in `core.py` to the exact source and
the date you downloaded it. Columns the app uses:

| Column | Used for |
|---|---|
| Name, Brand | Display, brand tier, editor's choice, price lookup |
| Length, Width, Height (mm) | Hand fit |
| Weight (grams) | Weight class and weight bonus |
| Shape, Hump placement | Grip fit (symmetrical/ergonomic, hump position) |
| Hand compatibility | Right, left or ambidextrous filter |
| Connectivity | Wired or wireless filter |
| Sensor, Tracking speed (IPS), Polling rate (Hz) | Modernity score and the old-sensor filter |
| Material | Price estimate |

Derived in `core.load_db()`: `Tier`, `Editor`, `Modernity`, `Era`, `Price`, `Price source`.

### Cleaning and processing

1. Measurements converted to numbers. Missing weight is filled with the median, missing polling rate with 1000 Hz.
2. Rows outside 75 to 140 mm long or 45 to 80 mm wide are dropped (rings, trackballs, oversized devices).
3. Mice with a PAW3335, PAW3370 or older PixArt sensor, or a generic or unlabelled sensor, are dropped
   (1,533 rows in the original file, 1,174 used). Editor's choice mice are always kept.
4. Split brand names are repaired (for example "Attack" + "Shark" -> "Attack Shark").
5. Each mouse gets a brand tier, an editor's choice flag, and a modernity score inferred from sensor speed and
   polling rate (the data has no release year).
6. Prices from `prices.csv` are marked verified; every other mouse gets a labelled estimate.

The Dataset tab shows these counts live, so they always match the file.

### Scoring

`score = hand fit (0-70) + newer tech + weight bonus + brand points + editor's choice + budget edge/penalty`

- Fit compares length, width, height, hump position and shape with the ideal for the grip (ratios of hand size).
  Relaxed claw prefers a mid-center hump, aggressive claw a moderate to aggressive back hump, pincer claw a
  shorter mouse with a moderate back hump.
- Weight classes: ultralight 50 g and below, light 51 to 65 g, medium 66 to 80 g, heavy 81 g and up.
- Budget: a mouse is shown if its price is within budget plus its tier's stretch (Top 10%, Mid 5%). Going over
  budget costs 40 points per 100% over. ATK A9 Air, F1 V2 Ultimate/Extreme, Zero, Ghost, U2 V2, Z1 V2 and X1 V2
  get +4 when the budget is $80 or less.
- "Not sure": curated universal mice plus any symmetrical mouse that fits palm, claw and fingertip well.

Tune everything at the top of `core.py` (`TIER_BRANDS`, `EDITORS_PICKS`, `EDITORS_PATTERNS`,
`EDITORS_SENSOR_RULES`, `VALUE_PATTERN`, `UNIVERSAL`, `GRIPS`, `WEIGHT_CLASSES`).

## Files

| File | What it does |
|---|---|
| `app.py` | Streamlit UI, charts, tabs |
| `core.py` | Data loading and cleaning, tiers, scoring, universal picks, links |
| `prices.csv` | `Name,Price_USD,Source,Updated`. Seeded from MaxGaming (US), checked 2026-11-15; "(sale)" prices will change |
| `links.csv` | `Name,MaxGaming_URL,Amazon_URL`. Exact product pages; without one the button searches instead |
| `fetch_prices.py` | Optional: builds `prices.csv` from Shopify store feeds or Google Shopping (SerpAPI) |
| `.streamlit/config.toml` | Theme (palette, square corners) |

## Limits

Fit targets are community rules of thumb, not lab measurements. Release dates are inferred from specs. Prices
not in `prices.csv` are estimates. Nothing here was hands-on tested.
