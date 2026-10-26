import csv
import re
from pathlib import Path

BRAND_DIR = Path(__file__).resolve().parents[2] / "data" / "sample_brand"


def load_guidelines(path=None):
    path = Path(path) if path else BRAND_DIR / "guidelines.md"
    text = path.read_text(encoding="utf-8")
    passages = []
    for block in re.split(r"\n(?=## )", text):
        m = re.match(r"## (G\d+) (.+?)\n(.*)", block, re.S)
        if m:
            passages.append(
                {"id": m.group(1), "title": m.group(2).strip(), "text": m.group(3).strip()}
            )
    return passages


def load_glossary(path=None):
    path = Path(path) if path else BRAND_DIR / "glossary.csv"
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load_facts(path=None):
    path = Path(path) if path else BRAND_DIR / "facts.csv"
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))
