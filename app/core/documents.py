"""Document and image intake for BrandLens.

Reads text from .txt, .md, .docx and .pdf files and checks images against the
brand guidelines. Follows the same rule as the rest of the product: a finding is
raised only when it can cite a guideline (evidence-or-silence), and uploaded files
are never executed, only parsed, with strict size limits.
"""
import io
import re
import zipfile
import xml.etree.ElementTree as ET

from app.core.knowledge import load_guidelines
from app.core.rules import _finding

MAX_BYTES = 5 * 1024 * 1024
MAX_PAGES = 30
MAX_CHARS = 20000
MAX_XML_BYTES = 10 * 1024 * 1024
MAX_PIXELS = 50_000_000
MAIN_COLOR_SHARE = 0.30     # a colour must cover this much of the image to count as its background
TEXT_MIN_CONTRAST = 4.5     # WCAG 2.1 AA for normal text
GRAPHIC_MIN_CONTRAST = 3.0  # WCAG 2.1 AA for graphics and UI parts
OCR_PAGES = 5        # scanned PDFs: only the first pages are read, to keep it quick
OCR_TIMEOUT = 20     # seconds for one page or image
OCR_BUDGET = 40      # seconds in total for one file
OCR_MAX_SIDE = 2400  # larger images are shrunk before reading
TEXT_TYPES = (".txt", ".md", ".docx", ".pdf")
IMAGE_TYPES = (".png", ".jpg", ".jpeg", ".webp")

WP_NS = "{http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing}"
FILENAME_LIKE = re.compile(r"\.(png|jpe?g|gif|bmp|webp|svg|tiff?)$", re.I)
GENERIC_ALT = {"image", "picture", "photo", "img", "graphic", "pic", "logo image"}


# ------------------------------------------------------------------------ OCR
WINDOWS_TESSERACT = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
_ocr_state = {}


def ocr_available():
    """True when text recognition can run on this server. OCR runs locally with Tesseract:
    nothing is sent to an outside service."""
    if "ok" not in _ocr_state:
        try:
            import os
            import pytesseract

            if os.path.exists(WINDOWS_TESSERACT):
                pytesseract.pytesseract.tesseract_cmd = WINDOWS_TESSERACT
            pytesseract.get_tesseract_version()
            have = set(pytesseract.get_languages(config=""))
            _ocr_state["lang"] = "+".join(l for l in ("eng", "hin") if l in have) or "eng"
            _ocr_state["ok"] = True
        except Exception:
            _ocr_state["ok"] = False
    return _ocr_state["ok"]


def _ocr_image(img):
    """Text read from a PIL image, or "" if nothing could be read."""
    if not ocr_available():
        return ""
    try:
        import pytesseract

        img = img.convert("RGB")
        if max(img.size) > OCR_MAX_SIDE:
            img.thumbnail((OCR_MAX_SIDE, OCR_MAX_SIDE))
        text = pytesseract.image_to_string(img, lang=_ocr_state["lang"], timeout=OCR_TIMEOUT)
    except Exception:
        return ""
    return re.sub(r"\n{3,}", "\n\n", text).strip()


# ------------------------------------------------------------------ alt text
def bad_alt_text(alt):
    alt = (alt or "").strip()
    if len(alt) < 4:
        return True
    if FILENAME_LIKE.search(alt):
        return True
    if alt.lower() in GENERIC_ALT:
        return True
    return False


# --------------------------------------------------------------------- text
def extract_document(filename, data, passages=None):
    """Return {"text", "notes", "findings"} for a .txt, .md, .docx or .pdf file."""
    passages = passages or load_guidelines()
    name = (filename or "").lower()
    if len(data) > MAX_BYTES:
        raise ValueError("The file is larger than 5 MB.")
    notes, findings = [], []
    if name.endswith((".txt", ".md")):
        text = data.decode("utf-8", errors="replace")
    elif name.endswith(".docx"):
        text, findings = _read_docx(data, passages)
    elif name.endswith(".pdf"):
        text = _read_pdf(data, notes)
    else:
        raise ValueError("Unsupported file type. Please use .txt, .md, .docx or .pdf.")
    text = text.strip()
    if len(text) > MAX_CHARS:
        text = text[:MAX_CHARS]
        notes.append("Only the first %d characters were checked." % MAX_CHARS)
    if not text:
        notes.append("No readable text was found in this file.")
    return {"text": text, "notes": notes, "findings": findings}


def _read_docx(data, passages):
    from docx import Document

    try:
        zf = zipfile.ZipFile(io.BytesIO(data))
        info = zf.getinfo("word/document.xml")
    except (zipfile.BadZipFile, KeyError):
        raise ValueError("This .docx file is damaged or is not a real Word file.")
    if info.file_size > MAX_XML_BYTES:
        raise ValueError("This Word file is too large to check safely.")
    xml_bytes = zf.read("word/document.xml")
    if b"<!DOCTYPE" in xml_bytes or b"<!ENTITY" in xml_bytes:
        raise ValueError("This Word file contains unsafe content and was not opened.")
    try:
        doc = Document(io.BytesIO(data))
    except Exception:
        raise ValueError("This .docx file could not be read.")
    parts = [p.text for p in doc.paragraphs if p.text.strip()]
    for table in doc.tables:
        for row in table.rows:
            cells = [c.text.strip() for c in row.cells if c.text.strip()]
            if cells:
                parts.append(" | ".join(cells))
    return "\n".join(parts), _docx_image_findings(xml_bytes, passages)


def _docx_image_findings(xml_bytes, passages):
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError:
        return []
    total, bad = 0, 0
    for el in root.iter(WP_NS + "docPr"):
        total += 1
        if bad_alt_text(el.get("descr", "")):
            bad += 1
    if not bad:
        return []
    return [_finding(
        "Accessibility", "medium", "G4", "", None, None,
        "%d of %d image(s) in this document have no useful alt text." % (bad, total),
        "describe what each image shows in one short sentence", passages)]


def _read_pdf(data, notes):
    import pdfplumber

    parts = []
    try:
        with pdfplumber.open(io.BytesIO(data)) as pdf:
            pages = pdf.pages
            if len(pages) > MAX_PAGES:
                notes.append("Only the first %d pages were read." % MAX_PAGES)
            for page in pages[:MAX_PAGES]:
                t = page.extract_text() or ""
                if t.strip():
                    parts.append(t)
            if not parts:
                parts = _ocr_pdf_pages(pages, notes)
    except Exception:
        raise ValueError("This PDF could not be read.")
    return "\n".join(parts)


def _ocr_pdf_pages(pages, notes):
    """A PDF with no selectable text is usually a scan: read its first pages with OCR."""
    import time

    if not ocr_available():
        notes.append("This PDF has no selectable text (it may be a scan) and text recognition (OCR) "
                     "is not installed on this server.")
        return []
    out, start = [], time.time()
    wanted = pages[:OCR_PAGES]
    for page in wanted:
        if time.time() - start > OCR_BUDGET:
            break
        try:
            text = _ocr_image(page.to_image(resolution=150).original)
        except Exception:
            text = ""
        if text:
            out.append(text)
    if out:
        extra = " Only the first %d pages were read." % OCR_PAGES if len(pages) > OCR_PAGES else ""
        notes.append("This PDF is a scan, so its text was read with OCR on this server." + extra +
                     " Please check the text for reading mistakes before you run the review.")
    else:
        notes.append("This PDF has no selectable text and OCR could not read any text from it.")
    return out


# ------------------------------------------------------------------- images
def hex_to_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _luminance(rgb):
    def ch(v):
        v = v / 255.0
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    r, g, b = (ch(x) for x in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_ratio(c1, c2):
    """WCAG contrast ratio between two RGB colours (1 to 21)."""
    l1, l2 = _luminance(c1), _luminance(c2)
    hi, lo = max(l1, l2), min(l1, l2)
    return (hi + 0.05) / (lo + 0.05)


def brand_palette(passages):
    for p in passages:
        if p["id"] == "G5":
            return list(dict.fromkeys(re.findall(r"#[0-9A-Fa-f]{6}", p["text"])))
    return []


def _distance(a, b):
    return sum((x - y) ** 2 for x, y in zip(a, b)) ** 0.5


def dominant_colors(img, n=6):
    from PIL import Image

    rgb = img.convert("RGBA")
    bg = Image.new("RGBA", rgb.size, (255, 255, 255, 255))
    rgb = Image.alpha_composite(bg, rgb).convert("RGB")
    rgb.thumbnail((120, 120))
    q = rgb.quantize(colors=n, method=Image.Quantize.MEDIANCUT)
    pal = q.getpalette()
    counts = sorted(q.getcolors(), reverse=True)
    total = float(sum(c for c, _ in counts)) or 1.0
    return [((pal[i * 3], pal[i * 3 + 1], pal[i * 3 + 2]), c / total) for c, i in counts]


def review_image(filename, data, alt_text, passages=None):
    """Check an uploaded image. Returns {"findings", "info", "text", "notes"}.

    "text" is whatever OCR could read inside the image (empty if none or OCR is off)."""
    from PIL import Image

    passages = passages or load_guidelines()
    if len(data) > MAX_BYTES:
        raise ValueError("The image is larger than 5 MB.")
    try:
        img = Image.open(io.BytesIO(data))
        width, height = img.size
        if width * height > MAX_PIXELS:
            raise ValueError("The image is too large to check safely.")
        img.load()
    except ValueError:
        raise
    except Exception:
        raise ValueError("This file is not a valid image.")

    notes = []
    approved = None
    try:
        from app.core import assets
        approved = assets.match_asset(data)
    except Exception:
        approved = None
    if approved:
        notes.append("This is the approved brand image '%s'. Its approved alt text is used." % approved["name"])
        if not (alt_text or "").strip():
            alt_text = approved["alt"]
    ocr_text = _ocr_image(img)
    if not ocr_available():
        notes.append("Text recognition (OCR) is not installed on this server, so only the alt text, colours "
                     "and contrast of this image were checked.")
    elif ocr_text:
        notes.append("Text read from the image with OCR. Please check it for reading mistakes before you "
                     "run the review.")
    else:
        notes.append("No text was found inside this image.")

    findings = []
    if bad_alt_text(alt_text):
        findings.append(_finding(
            "Accessibility", "medium", "G4", "", None, None,
            "This image has no useful alt text.",
            "write one short sentence describing what the image shows", passages))

    palette = brand_palette(passages)
    colors = dominant_colors(img)
    prominent = [rgb for rgb, share in colors if share >= 0.08]
    matched = True if approved else None
    if palette and not approved:
        matched = any(_distance(rgb, hex_to_rgb(b)) <= 60 for rgb in prominent for b in palette)
        if not matched:
            findings.append(_finding(
                "Visual", "low", "G5", "", None, None,
                "The main colours of this image do not match the brand palette (%s)." % ", ".join(palette),
                "use the brand colours, or confirm with the brand owner that this image is an approved exception",
                passages))
    # Contrast (WCAG 2.1 AA), measured on the image's own colours; no text recognition needed.
    text_contrast = None
    if colors and colors[0][1] >= MAIN_COLOR_SHARE:
        main = colors[0][0]
        dark = min((hex_to_rgb(b) for b in palette), key=_luminance) if palette else (0, 0, 0)
        text_contrast = max(contrast_ratio(main, (255, 255, 255)), contrast_ratio(main, dark))
        if text_contrast < TEXT_MIN_CONTRAST:
            findings.append(_finding(
                "Accessibility", "medium", "G4", "", None, None,
                "The main colour of this image (#%02X%02X%02X) gives only %.1f:1 contrast with white or "
                "dark brand text, below the 4.5:1 WCAG AA minimum. Text placed on it may be hard to read."
                % (main + (int(text_contrast * 10) / 10.0,)),
                "put text on a solid cream or dark panel, or lighten or darken the image behind the text",
                passages))
    if len(prominent) >= 2:
        spread = max(contrast_ratio(a, b) for a in prominent for b in prominent)
        if spread < GRAPHIC_MIN_CONTRAST:
            findings.append(_finding(
                "Accessibility", "low", "G4", "", None, None,
                "The main colours of this image are very close in brightness (%.1f:1), below the 3:1 "
                "WCAG minimum for graphics. Shapes or text may blend into the background." % (int(spread * 10) / 10.0),
                "increase the difference between the light and dark areas", passages))
    for i, f in enumerate(findings, 1):
        f["id"] = "R%d" % i
    info = {
        "width": width, "height": height, "format": img.format,
        "swatches": ["#%02X%02X%02X" % rgb for rgb, share in colors if share >= 0.05],
        "palette_match": matched,
        "approved_asset": approved["name"] if approved else None,
        "text_contrast": (int(text_contrast * 10) / 10.0) if text_contrast is not None else None,
    }
    return {"findings": findings, "info": info, "text": ocr_text, "notes": notes}