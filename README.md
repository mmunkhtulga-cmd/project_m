# Mouse finder

    pip install -r requirements.txt
    streamlit run app.py

Hand size -> grip (or "not sure") -> budget -> top 3 matches as cards. The full ranked list is a toggle.

| File | What it does |
|---|---|
| `app.py` | Streamlit UI (dark card layout) |
| `core.py` | Database cleaning, brand tiers, editor's picks, sensor rule, scoring, universal picks, links, images |
| `images/` | Product photos the cards show (built by `prepare_images.py`) |
| `prepare_images.py` | Matches a folder of photos to database names, crops and converts them |
| `images_needed.csv` | Mice that still have no photo, editor's choice and universal picks first |
| `prices.csv` | `Name,Price_USD,Source,Updated`. Listed mice show a real price; everything else is an estimate |
| `links.csv` | `Name,MaxGaming_URL,Amazon_URL`: exact product pages. Without one, the button searches instead |
| `fetch_prices.py` | Builds `prices.csv` from Shopify store feeds or Google Shopping (SerpAPI) |

## Database rule

Mice with a PAW3335, PAW3370 or older PixArt sensor, and mice with generic or unlabelled sensors, are removed
on load (1,174 of 1,533 mice remain). Proprietary sensors (HERO, BAMF, XS-1, Focus, TrueMove...) and PAW3311
are kept. Editor's choice mice are never removed. Edit `OUTDATED_SENSOR` / `GENERIC_SENSORS` in `core.py`.

## Not sure of my grip

A curated list of universal-shape mice by hand length (`UNIVERSAL` in `core.py`):

- Small (< 17.5 cm): Hitscan Hyperlight
- Medium (17.5 - 19.5 cm): Logitech G Pro X Superlight 1 and 2, Razer Viper V3 Pro and V4 Pro, RAWM Leviathan V4
- Large (> 19.5 cm): the medium list plus MelGeek Horus

They are ranked by their average score across palm, claw and fingertip. Budget only flags them ("Above your budget").

## Photos

    python prepare_images.py path/to/photos     # file names ~ database names, e.g. ENDGAME_GEAR_OP18K.webp

Names that don't match exactly go in `ALIASES`. v2 revisions reuse the original's photo until they get their own
(`SHARED`; listed in `images/manifest.csv`). The card tile takes the photo's background colour.

## Prices and links

    python fetch_prices.py shopify --dry-run
    python fetch_prices.py shopify --store https://BRAND-STORE --brand "Pulsar"
    SERPAPI_KEY=xxxx python fetch_prices.py serpapi --limit 90

`prices.csv` is seeded with MaxGaming (US) prices for the Endgame Gear mice and the Lamzu Maya X, checked on
2026-11-15. Entries marked "(sale)" are clearance prices and will change. Set `AMAZON_TAG` in `core.py` to add
your Amazon Associates tag to Amazon links.

## Brand tiers, editor's choice, hand fit

See the top of `core.py`: `TIER_BRANDS`, `NAME_RULES` (ROG recent only, RAWM recent only, Zowie wireless first,
Akitsu mid, Corsair Sabre mid), `EDITORS_PICKS` and `EDITORS_PATTERNS` (Lamzu Thorn and Atlantis Mini families),
`FIT_FORGIVENESS`. Points and budget stretch can also be changed live in the sidebar.
