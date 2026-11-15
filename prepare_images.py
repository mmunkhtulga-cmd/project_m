#!/usr/bin/env python3
"""
Turn a folder of product photos into the images/ folder the app reads.

    python prepare_images.py                      # reads ./mice_images, writes ./images
    python prepare_images.py path/to/photos

File names are matched to database names ignoring case, spaces and punctuation
(ENDGAME_GEAR_OP18K.webp -> "Endgame Gear OP1 8k"). Names that don't match exactly can be
added to ALIASES. Each photo is trimmed of empty margins, padded to a square and saved as a
600 px WebP, and its background colour is stored so the card tile blends with it.

v2 revisions share the photo of the original when no photo of their own exists (listed in
SHARED, flagged "shared_from" in images/manifest.csv). Replace them whenever you have the real one.

It also writes images_needed.csv: editor's choice, universal-shape and shortlisted mice that
still have no photo, so you know what to send next.
"""
pip install -r requirements.txt
from __future__ import annotations
import csv
import re
import sys
from pathlib import Path

from PIL import Image, ImageChops

import core

OUT = core.IMAGES_DIR
SIZE = 600

# file stem (normalised) -> database name, for files that don't match exactly
ALIASES = {
    "endgamegearxmw4k": "Endgame Gear XM2w 4k",
    "razerdeathadderv3wired": "Razer DeathAdder V3",
}
# database name -> database name whose photo it reuses (same shell, newer revision)
SHARED = {
    "Endgame Gear OP1 8k v2": "Endgame Gear OP1 8k",
    "Endgame Gear OP1w 4k v2": "Endgame Gear OP1w 4k",
    "Endgame Gear XM2 8k v2": "Endgame Gear XM2 8k",
    "Endgame Gear XM2w 4k v2": "Endgame Gear XM2w 4k",
}


def norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", s.lower())


def background(im: Image.Image):
    """(rgb tuple or None when transparent) taken from the corners."""
    rgba = im.convert("RGBA")
    corners = [rgba.getpixel(p) for p in [(1, 1), (rgba.width - 2, 1), (1, rgba.height - 2),
                                          (rgba.width - 2, rgba.height - 2)]]
    if all(c[3] < 10 for c in corners):
        return None
    c = corners[0]
    return (c[0], c[1], c[2])


def trim_and_square(im: Image.Image):
    bg = background(im)
    rgba = im.convert("RGBA")
    if bg is None:
        mask = rgba.split()[3].point(lambda a: 255 if a > 10 else 0)
    else:
        solid = Image.new("RGB", rgba.size, bg)
        diff = ImageChops.difference(rgba.convert("RGB"), solid).convert("L")
        mask = diff.point(lambda v: 255 if v > 24 else 0)
    box = mask.getbbox()
    # keep low-resolution photos as they are: cropping would only blow up the blur
    if box and (box[2] - box[0]) >= 220 and (box[3] - box[1]) >= 120:
        pad = int(0.08 * max(box[2] - box[0], box[3] - box[1]))
        box = (max(0, box[0] - pad), max(0, box[1] - pad),
               min(rgba.width, box[2] + pad), min(rgba.height, box[3] + pad))
        rgba = rgba.crop(box)
    side = max(rgba.size)
    canvas = Image.new("RGBA", (side, side), (0, 0, 0, 0) if bg is None else bg + (255,))
    canvas.paste(rgba, ((side - rgba.width) // 2, (side - rgba.height) // 2), rgba)
    canvas = canvas.resize((SIZE, SIZE), Image.LANCZOS)
    return canvas, bg


def main(src: Path) -> None:
    db = core.load_db()
    by_norm = {norm(n): n for n in db["Name"]}
    OUT.mkdir(exist_ok=True)
    manifest, unmatched, done = {}, [], {}

    for f in sorted(src.glob("*")):
        if f.suffix.lower() not in (".webp", ".png", ".jpg", ".jpeg"):
            continue
        key = norm(f.stem)
        name = ALIASES.get(key) or by_norm.get(key)
        if not name:
            unmatched.append(f.name)
            continue
        canvas, bg = trim_and_square(Image.open(f))
        slug = core.slugify(name)
        canvas.save(OUT / f"{slug}.webp", "WEBP", quality=86, method=6)
        bg_hex = "" if bg is None else "#%02x%02x%02x" % bg
        manifest[slug] = (name, bg_hex, "")
        done[name] = (f.name, slug, bg_hex)

    for name, source in SHARED.items():
        if name in by_norm.values() and name not in done and source in done:
            slug = core.slugify(name)
            src_slug = done[source][1]
            (OUT / f"{slug}.webp").write_bytes((OUT / f"{src_slug}.webp").read_bytes())
            manifest[slug] = (name, done[source][2], source)

    with open(OUT / "manifest.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["slug", "name", "bg", "shared_from"])
        for slug, (name, bg_hex, shared) in sorted(manifest.items()):
            w.writerow([slug, name, bg_hex, shared])

    # what still needs a photo
    have = {v[0] for v in manifest.values()}
    names = list(dict.fromkeys(
        db.loc[db["Editor"], "Name"].tolist()
        + [n for lst in core.UNIVERSAL.values() for n in lst]))
    needed = [(n, "editor's choice / universal") for n in names if n not in have]
    try:
        import fetch_prices
        needed += [(n, "shortlist") for n in fetch_prices.shortlist() if n not in have and n not in names]
    except Exception:
        pass
    with open(core.HERE / "images_needed.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["Name", "Why"])
        w.writerows(needed)

    print(f"matched {len(done)} photos, reused {sum(1 for v in manifest.values() if v[2])} for v2 revisions")
    if unmatched:
        print("no database match for:", ", ".join(unmatched))
    print(f"{len(needed)} mice still need a photo -> images_needed.csv")


if __name__ == "__main__":
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else core.HERE / "mice_images")
