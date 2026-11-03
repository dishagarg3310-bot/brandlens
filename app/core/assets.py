"""Reusable brand assets: the colour palette and a library of approved images.

* Colours are stored here with names and also written into the 'Brand colours:' sentence of
  guideline G5, so the image check, the rules and the AI all read the same palette.
* Approved images are saved with approved alt text and usage notes. Creators can download them,
  and an uploaded image that is identical to an approved one is recognised in the image review.
"""
import hashlib
import io
import json
import re
from pathlib import Path

from app.core import knowledge

MAX_COLOURS = 12
MAX_IMAGES = 12
MAX_IMAGE_BYTES = 2 * 1024 * 1024
MAX_PIXELS = 25_000_000
HEX = re.compile(r"^#[0-9A-Fa-f]{6}$")
NAME = re.compile(r"^[A-Za-z][A-Za-z0-9 \-]{0,29}$")        # no dots: the name goes into a sentence
KINDS = {"PNG": ".png", "JPEG": ".jpg", "WEBP": ".webp"}


def _json_path():
    return knowledge.BRAND_DIR / "assets.json"


def _dir():
    return knowledge.BRAND_DIR / "assets"


def _default_colours():
    """Start from whatever colours guideline G5 already lists."""
    for p in knowledge.load_guidelines():
        if p["id"] == "G5":
            found = re.findall(r"([A-Za-z][A-Za-z \-]{0,28}?)\s+(#[0-9A-Fa-f]{6})", p["text"])
            return [{"name": n.strip().lower(), "hex": h.upper()} for n, h in found]
    return []


def load_assets():
    path = _json_path()
    data = {}
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            data = {}
    colours = data.get("colours") if isinstance(data.get("colours"), list) else None
    images = data.get("images") if isinstance(data.get("images"), list) else []
    return {"colours": colours if colours is not None else _default_colours(), "images": images}


def _save(data):
    path = _json_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    tmp.replace(path)


# --------------------------------------------------------------------------- colours
def check_colour(name, hex_code, existing):
    name, hex_code = (name or "").strip(), (hex_code or "").strip()
    if not NAME.match(name):
        return "Give the colour a short name (letters, numbers, spaces; no full stops)."
    if not HEX.match(hex_code):
        return "The colour code must look like #2E7D32."
    if any(c["hex"].upper() == hex_code.upper() for c in existing):
        return "This colour is already in the palette."
    if any(c["name"].lower() == name.lower() for c in existing):
        return "A colour with this name already exists."
    if len(existing) >= MAX_COLOURS:
        return "The palette can hold at most %d colours." % MAX_COLOURS
    return None


def add_colour(name, hex_code):
    data = load_assets()
    problem = check_colour(name, hex_code, data["colours"])
    if problem:
        raise ValueError(problem)
    data["colours"].append({"name": name.strip().lower(), "hex": hex_code.strip().upper()})
    _save(data)
    knowledge.set_palette_sentence(data["colours"])


def remove_colours(hex_codes):
    data = load_assets()
    keep = [c for c in data["colours"] if c["hex"].upper() not in {h.upper() for h in hex_codes}]
    if not keep:
        raise ValueError("Keep at least one colour in the palette.")
    data["colours"] = keep
    _save(data)
    knowledge.set_palette_sentence(keep)


# ---------------------------------------------------------------------------- images
def _open_image(data):
    from PIL import Image

    if len(data) > MAX_IMAGE_BYTES:
        raise ValueError("The image is larger than %d MB." % (MAX_IMAGE_BYTES // (1024 * 1024)))
    try:
        img = Image.open(io.BytesIO(data))
        img.verify()
        img = Image.open(io.BytesIO(data))
    except Exception:
        raise ValueError("This file is not a readable PNG, JPG or WEBP image.")
    if img.format not in KINDS:
        raise ValueError("Only PNG, JPG or WEBP images can be added.")
    if img.width * img.height > MAX_PIXELS:
        raise ValueError("The image has too many pixels.")
    return img


def add_image(name, alt, usage, data, filename=""):
    from app.core.documents import bad_alt_text

    name, alt, usage = (name or "").strip(), (alt or "").strip(), (usage or "").strip()
    if not 3 <= len(name) <= 50:
        raise ValueError("Give the image a name of 3 to 50 characters.")
    problem = bad_alt_text(alt)
    if problem or len(alt) > 250:
        raise ValueError("Approved images need good alt text (describe what the image shows, at most 250 characters).")
    if len(usage) > 200:
        raise ValueError("Keep the usage note under 200 characters.")
    img = _open_image(data)
    store = load_assets()
    if len(store["images"]) >= MAX_IMAGES:
        raise ValueError("The library can hold at most %d images." % MAX_IMAGES)
    digest = hashlib.sha256(data).hexdigest()
    if any(i["sha256"] == digest for i in store["images"]):
        raise ValueError("This exact image is already in the library.")
    n = max([int(i["id"][1:]) for i in store["images"]] + [0]) + 1
    fname = "asset_%d%s" % (n, KINDS[img.format])
    _dir().mkdir(parents=True, exist_ok=True)
    (_dir() / fname).write_bytes(data)
    store["images"].append({"id": "A%d" % n, "name": name, "file": fname, "alt": alt, "usage": usage,
                            "sha256": digest, "width": img.width, "height": img.height})
    _save(store)
    return "A%d" % n


def remove_image(asset_id):
    store = load_assets()
    gone = [i for i in store["images"] if i["id"] == asset_id]
    if not gone:
        raise ValueError("That image was not found.")
    store["images"] = [i for i in store["images"] if i["id"] != asset_id]
    _save(store)
    try:
        (_dir() / Path(gone[0]["file"]).name).unlink()
    except OSError:
        pass


def image_bytes(asset):
    return (_dir() / Path(asset["file"]).name).read_bytes()      # Path(...).name: never leave the folder


def match_asset(data):
    """The approved image that is byte-for-byte identical to this upload, or None."""
    digest = hashlib.sha256(data).hexdigest()
    for i in load_assets()["images"]:
        if i["sha256"] == digest:
            return i
    return None