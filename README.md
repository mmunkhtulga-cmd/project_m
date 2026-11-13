# Mouse finder

    pip install -r requirements.txt
    streamlit run app.py

Hand size -> grip -> budget -> recommendations. The full ranked list is a toggle on the results page.

| File | What it does |
|---|---|
| `app.py` | Streamlit UI |
| `core.py` | Data cleaning, brand tiers, editor's picks, scoring. Edit tiers and picks here |
| `fetch_prices.py` | Builds `prices.csv` with real prices (Shopify store feeds or Google Shopping via SerpAPI) |
| `prices.csv` | `Name,Price_USD`. Listed mice show a real price, everything else is estimated |
| `mouse_db.csv` | The database (semicolon separated) |

## Brand tiers (core.py: TIER_BRANDS, NAME_RULES)

- **Top (+8 points, budget stretch 20%):** Razer, Logitech, Lamzu, Hitscan, CRDRAKO, Pulsar, Endgame Gear,
  Arbiter, MelGeek, Ninjutso, Teevolution, Vaxee. Model rules: ROG only Keris II / Harpe II / Harpe Ace Extreme+Mini,
  RAWM only ER21 and Leviathan V4, Zowie wireless only.
- **Mid / enthusiast (+5, stretch 10%):** ATK, MCHOSE, VGN, VXE, Finalmouse, WALLHACK, Keychron, HyperX, UNIUS, Scyrox,
  IPI, WLMOUSE, Waizowl, G-Wolves, Akitsu, other name brands (SteelSeries, Glorious, ROCCAT, Cooler Master...),
  other ASUS, Zowie wired, Corsair Sabre.
- **Low to mid (-4, no stretch):** Attack Shark, AULA, AJAZZ, RK, Darmoshark, EWEADN, Redragon, Delux, other Corsair.
- **Other (0):** every brand not listed, plus older RAWM.
- **Editor's choice (+10, never hidden as dated):** see `EDITORS_PICKS`. Not in this database yet:
  ATK F1 V3, ATK Phantom, Logitech "Compact", UNIUS White Lotus, WALLHACK. Add exact names when the database updates.

All points and stretch percentages can be changed live in the sidebar (Brand tiers and points).

## Older mice

The database has no release year, so age is inferred from the sensor (through tracking speed, a few sensors
pinned by hand) and the polling rate. "Dated" mice are hidden unless you switch on "Include dated mice".

## Real prices

    python fetch_prices.py shopify --dry-run
    python fetch_prices.py shopify --store https://BRAND-STORE --brand "Pulsar"
    SERPAPI_KEY=xxxx python fetch_prices.py serpapi --limit 90

Editor's choice mice are always on the shortlist. You can also edit `prices.csv` by hand.
