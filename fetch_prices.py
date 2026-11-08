#!/usr/bin/env python3
"""
Build prices.csv with real USD prices for the mice the app can actually recommend.

Two sources (use either or both; results merge into prices.csv):

  1) shopify  - free. Many brands run Shopify stores that publish /products.json.
                python fetch_prices.py shopify --store https://example-brand.com --brand "Brand"

  2) serpapi  - Google Shopping results through SerpAPI (needs SERPAPI_KEY, has a free tier).
                SERPAPI_KEY=xxxx python fetch_prices.py serpapi

Only a shortlist is priced (the mice that rank in the top few for every grip, hand size and
budget bucket), not all ~1500 models. Use --all to price everything, --dry-run to just list.

Be a good citizen: respect each site's terms and robots.txt, keep the delay, and use this
for personal price-checking. Prices in other currencies: pass --rate (e.g. --rate 0.14 for CNY).
Not tested against the live services from the build sandbox, only against sample responses.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import statistics
import sys
import time
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

import pandas as pd

import core

CACHE = core.HERE / "prices_cache.json"
UA = {"User-Agent": "Mozilla/5.0 (personal price check for a mouse recommender)"}
NOISE = {"mouse", "gaming", "esports", "the", "new", "edition", "wireless"}
ACCESSORY = ("pad", "skates", "glides", "feet", "grip tape", "cable", "dongle", "receiver",
             "case", "sleeve", "bundle", "mousepad", "battery", "shell", "cover")


def http_get_json(url: str, timeout: int = 25) -> dict:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def tokens(s: str) -> set[str]:
    return {t for t in re.sub(r"[^a-z0-9]+", " ", s.lower()).split() if t not in NOISE}


def match_name(title: str, names: dict[str, set[str]]) -> str | None:
    """Pick the most specific database name whose tokens all appear in the title."""
    t = tokens(title)
    hits = [(len(tok), n) for n, tok in names.items() if tok and tok <= t]
    return max(hits)[1] if hits else None


# ---------------------------------------------------------------- shortlist
def shortlist(per_bucket: int = 6) -> list[str]:
    db = core.load_db()
    cfg = core.TIER_DEFAULTS
    names: list[str] = []
    for grip in core.GRIPS:
        for ln, wd in core.HAND_PRESETS.values():
            sc = core.score(db, grip, ln * 10, wd * 10, cfg)
            for budget in (40, 70, 100, 150):
                recs = core.recommend(sc, budget, cfg, False, 2, per_bucket)
                names += recs["Name"].tolist()
    return list(dict.fromkeys(names))


# ---------------------------------------------------------------- providers
def shopify_prices(store: str, brand: str, names: list[str], rate: float) -> dict[str, float]:
    index = {n: tokens(n) for n in names if n.lower().startswith(brand.lower())}
    out: dict[str, float] = {}
    page = 1
    while True:
        data = http_get_json(f"{store.rstrip('/')}/products.json?limit=250&page={page}")
        products = data.get("products", [])
        if not products:
            break
        for p in products:
            title = p.get("title", "")
            if any(w in f"{title} {p.get('product_type', '')}".lower() for w in ACCESSORY):
                continue
            prices = [float(v["price"]) for v in p.get("variants", [])
                      if v.get("price") not in (None, "") and float(v["price"]) > 0]
            full = title if title.lower().startswith(brand.lower()) else f"{brand} {title}"
            name = match_name(full, index)
            if name and prices:
                out[name] = round(min(prices) * rate, 2)
        page += 1
        time.sleep(1)
    return out


def serpapi_price(name: str, key: str, rate: float, gl: str = "us") -> float | None:
    q = urllib.parse.urlencode({"engine": "google_shopping", "q": f"{name} gaming mouse",
                                "gl": gl, "hl": "en", "api_key": key})
    data = http_get_json(f"https://serpapi.com/search.json?{q}")
    want = tokens(name)
    prices = []
    for r in data.get("shopping_results", []):
        price = r.get("extracted_price")
        if price and price >= 15 and want <= tokens(r.get("title", "")) \
                and not any(w in r.get("title", "").lower() for w in ACCESSORY):
            prices.append(price * rate)
    return round(statistics.median(prices[:5]), 2) if prices else None


# ---------------------------------------------------------------- storage
def load_cache() -> dict:
    return json.loads(CACHE.read_text()) if CACHE.exists() else {}


def write_prices(cache: dict) -> None:
    rows = {}
    existing = core.read_prices(core.PRICES_PATH) if core.PRICES_PATH.exists() else None
    if existing is not None:
        for n, p in zip(existing["Name"], existing["Price_USD"]):
            rows[n] = (p, "manual", "")
    for n, v in cache.items():
        rows[n] = (v["price"], v["source"], v["date"])
    df = pd.DataFrame([(n, *v) for n, v in rows.items()], columns=["Name", "Price_USD", "Source", "Updated"])
    df.sort_values("Name").to_csv(core.PRICES_PATH, index=False)
    print(f"Wrote {len(df)} prices to {core.PRICES_PATH.name}")


# ---------------------------------------------------------------- main
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("provider", choices=["shopify", "serpapi"])
    ap.add_argument("--store", help="shopify: store URL, e.g. https://example-brand.com")
    ap.add_argument("--brand", help="shopify: brand name as in the database, e.g. Pulsar")
    ap.add_argument("--rate", type=float, default=1.0, help="multiply prices by this to get USD")
    ap.add_argument("--all", action="store_true", help="price every non-dated mouse, not just the shortlist")
    ap.add_argument("--per-bucket", type=int, default=6)
    ap.add_argument("--limit", type=int, default=0, help="serpapi: max lookups this run")
    ap.add_argument("--refresh", action="store_true", help="re-fetch names already in the cache")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)

    if a.all:
        names = core.load_db().query("Era != 'Dated'")["Name"].tolist()
    else:
        names = shortlist(a.per_bucket)
    print(f"{len(names)} mice to price")
    if a.dry_run:
        print("\n".join(names))
        return 0

    cache, today = load_cache(), date.today().isoformat()
    if a.provider == "shopify":
        if not (a.store and a.brand):
            sys.exit("shopify needs --store and --brand")
        found = shopify_prices(a.store, a.brand, names, a.rate)
        for n, p in found.items():
            cache[n] = dict(price=p, source=f"shopify:{a.brand}", date=today)
        print(f"Matched {len(found)} products")
    else:
        key = os.environ.get("SERPAPI_KEY")
        if not key:
            sys.exit("Set SERPAPI_KEY first.")
        todo = [n for n in names if a.refresh or n not in cache]
        todo = todo[: a.limit] if a.limit else todo
        for i, n in enumerate(todo, 1):
            try:
                p = serpapi_price(n, key, a.rate)
            except Exception as e:  # network / quota; keep what we have
                print(f"  stopped at {n}: {e}")
                break
            print(f"[{i}/{len(todo)}] {n}: {p if p else 'no match'}")
            if p:
                cache[n] = dict(price=p, source="serpapi", date=today)
            CACHE.write_text(json.dumps(cache, indent=1))
            time.sleep(1.2)
    CACHE.write_text(json.dumps(cache, indent=1))
    write_prices(cache)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
