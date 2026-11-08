# Mouse finder

    pip install -r requirements.txt
    streamlit run app.py

Flow: hand size -> grip -> budget -> matches (full ranked list is a toggle).

| File | What it does |
|---|---|
| `app.py` | Streamlit UI (step-by-step flow, results, sidebar refinements) |
| `core.py` | Data cleaning, modernity, scoring, budget rules. Tune brand tiers, grip ratios, sensor ratings here |
| `fetch_prices.py` | Builds `prices.csv` with real prices (Shopify store feeds or Google Shopping via SerpAPI) |
| `prices.csv` | `Name,Price_USD`. Anything listed here is shown as "verified"; everything else is estimated |
| `mouse_db.csv` | Your database (semicolon separated) |

## Real prices

    python fetch_prices.py shopify --dry-run                      # list the ~120 mice worth pricing
    python fetch_prices.py shopify --store https://BRAND-STORE --brand "Pulsar"
    SERPAPI_KEY=xxxx python fetch_prices.py serpapi --limit 90    # resumable, cached in prices_cache.json

You can also type prices straight into `prices.csv` or upload a file in the app sidebar.

## How "older mice" are handled

The database has no release year, so age is inferred from the sensor (via tracking speed, with a few
sensors pinned by hand) and polling rate. Mice below the "Dated" line are hidden unless you switch
on "Include dated mice". Current tech earns up to 10/20/30 points (Low/Medium/High).
