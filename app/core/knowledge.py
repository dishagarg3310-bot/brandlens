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


# ------------------------------------------------------------ editing the guidelines
CORE_IDS = ("G1", "G2", "G3", "G4", "G5", "G6")   # the rule engine cites these, so they cannot be removed
MAX_GUIDELINES = 60


def _clean_text(text):
    """A passage must never contain a line that looks like a new '## G7 Title' heading."""
    lines = []
    for line in str(text).splitlines():
        lines.append(line.lstrip().lstrip("#").strip() if line.lstrip().startswith("#") else line.rstrip())
    return "\n".join(lines).strip()


def save_guidelines(passages, path=None):
    """Write the guidelines back in the standard format (keeps the title line of the file)."""
    path = Path(path) if path else BRAND_DIR / "guidelines.md"
    header = "# Brand Guidelines"
    if path.exists():
        first = path.read_text(encoding="utf-8").split("\n", 1)[0].strip()
        if first.startswith("# "):
            header = first
    blocks = [header]
    for p in passages:
        title = re.sub(r"\s+", " ", p["title"]).strip()
        blocks.append("## %s %s\n%s" % (p["id"], title, _clean_text(p["text"])))
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text("\n\n".join(blocks) + "\n", encoding="utf-8")
    tmp.replace(path)


def next_guideline_id(passages):
    return "G%d" % (max([int(p["id"][1:]) for p in passages] + [0]) + 1)


def remove_guideline(guideline_id):
    if guideline_id in CORE_IDS:
        raise ValueError("%s is used by the rule engine and cannot be removed." % guideline_id)
    passages = load_guidelines()
    kept = [p for p in passages if p["id"] != guideline_id]
    if len(kept) == len(passages):
        raise ValueError("%s was not found." % guideline_id)
    save_guidelines(kept)


def set_palette_sentence(colours):
    """Keep the 'Brand colours: ...' sentence of G5 in step with the palette editor, so the image
    check, the rules and the AI all read the same colours."""
    if not colours:
        return False
    sentence = "Brand colours: " + ", ".join("%s %s" % (c["name"].lower(), c["hex"].upper()) for c in colours) + "."
    passages = load_guidelines()
    for p in passages:
        if p["id"] == "G5":
            pattern = r"Brand colours?:[^.\n]*\."
            if re.search(pattern, p["text"], re.I):
                p["text"] = re.sub(pattern, lambda m: sentence, p["text"], count=1, flags=re.I)
            else:
                p["text"] = sentence + " " + p["text"]
            save_guidelines(passages)
            return True
    return False