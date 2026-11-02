import io
import unittest
import zipfile

from PIL import Image

from app.core import documents as d


def png(color, size=(200, 200)):
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, "PNG")
    return buf.getvalue()


def make_pdf(text):
    content = "BT /F1 12 Tf 72 720 Td (%s) Tj ET" % text
    objs = [
        "<< /Type /Catalog /Pages 2 0 R >>",
        "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R "
        "/Resources << /Font << /F1 5 0 R >> >> >>",
        "<< /Length %d >>\nstream\n%s\nendstream" % (len(content), content),
        "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out = b"%PDF-1.4\n"
    offsets = []
    for i, o in enumerate(objs, 1):
        offsets.append(len(out))
        out += ("%d 0 obj\n%s\nendobj\n" % (i, o)).encode("latin-1")
    xref = len(out)
    out += ("xref\n0 %d\n0000000000 65535 f \n" % (len(objs) + 1)).encode()
    for off in offsets:
        out += ("%010d 00000 n \n" % off).encode()
    out += ("trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objs) + 1, xref)).encode()
    return out


def make_docx(paragraphs, table_rows=None, picture=False):
    from docx import Document

    doc = Document()
    for p in paragraphs:
        doc.add_paragraph(p)
    if table_rows:
        t = doc.add_table(rows=len(table_rows), cols=len(table_rows[0]))
        for r, row in enumerate(table_rows):
            for c, val in enumerate(row):
                t.cell(r, c).text = val
    if picture:
        doc.add_picture(io.BytesIO(png("#2E7D32")))
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


class TextExtractionTests(unittest.TestCase):
    def test_txt(self):
        r = d.extract_document("post.txt", "Hello customers".encode("utf-8"))
        self.assertEqual(r["text"], "Hello customers")

    def test_docx_text_and_table(self):
        data = make_docx(["Our cosmetics are lovely."], table_rows=[["Price", "Rs. 499"]])
        r = d.extract_document("a.docx", data)
        self.assertIn("Our cosmetics are lovely.", r["text"])
        self.assertIn("Price | Rs. 499", r["text"])

    def test_docx_image_without_real_alt_text_is_flagged(self):
        r = d.extract_document("a.docx", make_docx(["Hi"], picture=True))
        self.assertEqual(len(r["findings"]), 1)
        self.assertEqual(r["findings"][0]["rule_id"], "G4")
        self.assertIn("alt text", r["findings"][0]["message"])

    def test_docx_without_images_has_no_findings(self):
        self.assertEqual(d.extract_document("a.docx", make_docx(["Hi"]))["findings"], [])

    def test_pdf_text(self):
        r = d.extract_document("a.pdf", make_pdf("Our best cream"))
        self.assertIn("Our best cream", r["text"])

    def test_pdf_without_text_adds_a_note(self):
        r = d.extract_document("a.pdf", make_pdf(""))
        self.assertEqual(r["text"], "")
        self.assertTrue(any("no selectable text" in n for n in r["notes"]))


class SafetyTests(unittest.TestCase):
    def test_unsupported_type(self):
        with self.assertRaises(ValueError):
            d.extract_document("virus.exe", b"MZ")

    def test_too_large(self):
        with self.assertRaises(ValueError):
            d.extract_document("a.txt", b"x" * (d.MAX_BYTES + 1))

    def test_damaged_docx(self):
        with self.assertRaises(ValueError):
            d.extract_document("a.docx", b"not a zip")

    def test_docx_with_entity_declarations_is_rejected(self):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as z:
            z.writestr("word/document.xml", '<?xml version="1.0"?><!DOCTYPE x [<!ENTITY a "b">]><x/>')
        with self.assertRaises(ValueError):
            d.extract_document("a.docx", buf.getvalue())

    def test_garbage_pdf(self):
        with self.assertRaises(ValueError):
            d.extract_document("a.pdf", b"nope")

    def test_long_text_is_truncated_with_a_note(self):
        r = d.extract_document("a.txt", ("word " * 10000).encode())
        self.assertEqual(len(r["text"]), d.MAX_CHARS)
        self.assertTrue(r["notes"])


class AltTextTests(unittest.TestCase):
    def test_bad_alt_text(self):
        for bad in ["", "  ", "img", "image", "IMG_2043.jpg", "photo"]:
            self.assertTrue(d.bad_alt_text(bad), bad)

    def test_good_alt_text(self):
        self.assertFalse(d.bad_alt_text("Green leaf logo on a cream background"))


class ImageTests(unittest.TestCase):
    ALT = "A jar of moisturiser on a cream background"

    def test_on_brand_image_with_alt_text_has_no_findings(self):
        r = d.review_image("a.png", png("#2E7D32"), self.ALT)
        self.assertEqual(r["findings"], [])
        self.assertTrue(r["info"]["palette_match"])

    def test_off_brand_colours_are_flagged_with_the_guideline(self):
        r = d.review_image("a.png", png("#FF00FF"), self.ALT)
        visual = [f for f in r["findings"] if f["category"] == "Visual"]
        self.assertEqual([f["rule_id"] for f in visual], ["G5"])
        self.assertFalse(r["info"]["palette_match"])

    def test_missing_alt_text_is_flagged(self):
        r = d.review_image("a.png", png("#2E7D32"), "")
        self.assertEqual([f["rule_id"] for f in r["findings"]], ["G4"])

    def test_both_problems_are_numbered(self):
        r = d.review_image("a.png", png("#FF00FF"), "")
        ids = [f["id"] for f in r["findings"]]
        self.assertEqual(ids, ["R%d" % i for i in range(1, len(ids) + 1)])
        self.assertGreaterEqual(len(ids), 2)

    def test_not_an_image(self):
        with self.assertRaises(ValueError):
            d.review_image("a.png", b"not an image", self.ALT)

    def test_transparent_png_does_not_crash(self):
        buf = io.BytesIO()
        Image.new("RGBA", (50, 50), (0, 0, 0, 0)).save(buf, "PNG")
        d.review_image("a.png", buf.getvalue(), self.ALT)

    def test_palette_is_read_from_the_guidelines(self):
        from app.core.knowledge import load_guidelines
        self.assertEqual(
            [c.upper() for c in d.brand_palette(load_guidelines())], ["#2E7D32", "#F5F0E6", "#263238"])

    def test_contrast_ratio(self):
        self.assertAlmostEqual(d.contrast_ratio((0, 0, 0), (255, 255, 255)), 21.0, places=1)
        self.assertAlmostEqual(d.contrast_ratio((10, 10, 10), (10, 10, 10)), 1.0, places=2)

    def test_readable_image_reports_its_text_contrast(self):
        r = d.review_image("a.png", png("#2E7D32"), self.ALT)   # white text on brand green is 5.1:1
        self.assertGreaterEqual(r["info"]["text_contrast"], 4.5)
        self.assertEqual(r["findings"], [])

    def test_mid_tone_background_gets_a_text_contrast_finding(self):
        r = d.review_image("a.png", png("#EF6C00"), self.ALT)   # orange: neither white nor dark text reaches 4.5:1
        msgs = [f["message"] for f in r["findings"] if f["category"] == "Accessibility"]
        self.assertTrue(any("4.5:1" in m for m in msgs), msgs)
        self.assertLess(r["info"]["text_contrast"], 4.5)

    def test_flat_low_contrast_image_is_flagged(self):
        from PIL import Image
        img = Image.new("RGB", (100, 100), (120, 120, 120))
        for x in range(50, 100):
            for y in range(100):
                img.putpixel((x, y), (130, 130, 130))
        buf = io.BytesIO()
        img.save(buf, "PNG")
        r = d.review_image("a.png", buf.getvalue(), self.ALT)
        self.assertTrue(any("close in brightness" in f["message"] for f in r["findings"]))


def _text_image(lines=("Our BEST cosmetics are", "100% natural. Buy NOW!")):
    from PIL import ImageDraw, ImageFont

    img = Image.new("RGB", (1000, 300), "white")
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 54)
    except OSError:
        font = ImageFont.load_default()
    for i, line in enumerate(lines):
        draw.text((30, 40 + i * 110), line, fill="black", font=font)
    return img


@unittest.skipUnless(d.ocr_available(), "Tesseract is not installed on this machine")
class OcrTests(unittest.TestCase):
    def test_text_inside_an_image_is_read(self):
        buf = io.BytesIO()
        _text_image().save(buf, "PNG")
        r = d.review_image("poster.png", buf.getvalue(), "A poster")
        self.assertIn("natural", r["text"])
        self.assertTrue(any("OCR" in n for n in r["notes"]))

    def test_scanned_pdf_is_read_with_ocr(self):
        buf = io.BytesIO()
        _text_image().save(buf, "PDF")
        r = d.extract_document("scan.pdf", buf.getvalue())
        self.assertIn("cosmetics", r["text"])
        self.assertTrue(any("scan" in n for n in r["notes"]))

    def test_an_image_with_no_text_says_so(self):
        buf = io.BytesIO()
        Image.new("RGB", (300, 300), "white").save(buf, "PNG")
        r = d.review_image("blank.png", buf.getvalue(), "A blank card")
        self.assertEqual(r["text"], "")
        self.assertTrue(any("No text was found" in n for n in r["notes"]))


class OcrFallback(unittest.TestCase):
    """When OCR is not installed the product must still work and say so."""

    def setUp(self):
        from unittest import mock
        p = mock.patch.dict(d._ocr_state, {"ok": False})
        p.start()
        self.addCleanup(p.stop)

    def test_image_review_still_runs_and_explains(self):
        buf = io.BytesIO()
        Image.new("RGB", (100, 100), "#2E7D32").save(buf, "PNG")
        r = d.review_image("a.png", buf.getvalue(), "A green square")
        self.assertEqual(r["text"], "")
        self.assertTrue(any("not installed" in n for n in r["notes"]))

    def test_scanned_pdf_gives_a_clear_note(self):
        buf = io.BytesIO()
        _text_image().save(buf, "PDF")
        r = d.extract_document("scan.pdf", buf.getvalue())
        self.assertEqual(r["text"], "")
        self.assertTrue(any("not installed" in n for n in r["notes"]))


if __name__ == "__main__":
    unittest.main()