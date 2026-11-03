"""Turn an uploaded brand book (PDF, Word, Markdown or text) into reviewable guideline passages.

Nothing is added until the Admin has looked at every passage. Imported passages get new ids
(G7, G8, ...). They are used by the AI layer and shown to reviewers; the exact-match rules for
G1 to G6 are not changed by an import.
"""
import re

from app.core import knowledge
from app.core.redaction import has_pii

MAX_PASSAGES = 30       # per import
MAX_CHARS = 1200        # per passage
MIN_CHARS = 30
MAX_TITLE = 60

_MD_HEADING = re.compile(r"^\s{0,3}#{1,6}\s+(.+?)\s*#*\s*$")
_NUMBERED = re.compile(r"^\s*(?:\d{1,2}(?:\.\d{1,2})*[.)]|[A-Z]\d{0,2}[.)])\s+(\S.{2,66})$")


def _heading_title(line, prev_blank, prev_end_sentence, has_next):
    """The heading text if this line looks like a heading, else None."""
    s = line.strip()
    if not s:
        return None
    m = _MD_HEADING.match(line)
    if m:
        return m.group(1).strip()
    if len(s) > 70:
        return None
    m = _NUMBERED.match(line)
    if m and s[-1] not in ".;,":
        return m.group(1).strip()
    letters = [c for c in s if c.isalpha()]
    if len(letters) >= 3 and s.upper() == s and len(s) <= 60:
        return s.title()
    words = s.split()
    if (has_next and 1 <= len(words) <= 6 and s[0].isupper() and s[-1] not in ".,;!?"
            and (prev_blank or prev_end_sentence)):
        return s
    return None


def _clean_title(title):
    t = re.sub(r"^G\d+\s*[:.\-]?\s*", "", title.strip())      # no clashing guideline ids
    t = re.sub(r"\s+", " ", t).strip(" :-")
    return (t[:MAX_TITLE].rstrip() or "Untitled")


def _tidy(body_lines):
    body = "\n".join(body_lines).strip()
    body = re.sub(r"(?<!\n)\n(?!\n)", " ", body)             # hard-wrapped lines become one paragraph
    body = re.sub(r"[ \t]+", " ", body)
    return re.sub(r"\n{2,}", "\n\n", body).strip()


def _split_long(title, text):
    if len(text) <= MAX_CHARS:
        return [(title, text)]
    parts, cur = [], ""
    for sentence in re.split(r"(?<=[.!?])\s+", text):
        if cur and len(cur) + len(sentence) + 1 > MAX_CHARS:
            parts.append(cur)
            cur = sentence
        else:
            cur = (cur + " " + sentence).strip()
    if cur:
        parts.append(cur)
    return [(title if i == 0 else "%s (part %d)" % (title[:MAX_TITLE - 10], i + 1), t[:MAX_CHARS])
            for i, t in enumerate(parts)]


def _by_headings(text):
    lines = text.splitlines()
    sections, title, body = [], None, []
    prev_blank, prev_end = True, False
    for i, line in enumerate(lines):
        has_next = i + 1 < len(lines) and bool(lines[i + 1].strip())
        h = _heading_title(line, prev_blank, prev_end, has_next)
        if h:
            if title is not None or any(b.strip() for b in body):
                sections.append((title or "Introduction", _tidy(body)))
            title, body = h, []
        else:
            body.append(line)
        prev_blank = not line.strip()
        prev_end = line.strip()[-1:] in (".", "!", "?")
    sections.append((title or "Introduction", _tidy(body)))
    return [(t, b) for t, b in sections if b]


def _by_paragraphs(text):
    paras = [re.sub(r"\s+", " ", p).strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    if len(paras) < 2:                                    # a PDF with no blank lines at all
        paras = [re.sub(r"\s+", " ", " ".join(text.splitlines())).strip()]
    chunks, cur = [], ""
    for p in paras:
        if cur and len(cur) + len(p) > 700:
            chunks.append(cur)
            cur = p
        else:
            cur = (cur + " " + p).strip()
    if cur:
        chunks.append(cur)
    out = []
    for n, c in enumerate(chunks, 1):
        first = re.split(r"(?<=[.!?])\s", c, maxsplit=1)[0]
        out.append((" ".join(first.split()[:7]).rstrip(".,;:") or "Section %d" % n, c))
    return out


def split_passages(text):
    """List of {"title", "text"} found in the document, at most MAX_PASSAGES."""
    text = (text or "").replace("\r\n", "\n").replace("\r", "\n").strip()
    if not text:
        return []
    sections = _by_headings(text)
    if len(sections) < 2:
        sections = _by_paragraphs(text)
    out = []
    for title, body in sections:
        for t, b in _split_long(_clean_title(title), body):
            out.append({"title": _clean_title(t), "text": b})
    return out[:MAX_PASSAGES]


def _norm(s):
    return re.sub(r"\W+", " ", s.lower()).strip()


def prepare(passages, existing):
    """Rows for the preview table: {"use", "title", "text", "note"}. Doubtful ones start unticked."""
    seen = {_norm(p["text"]) for p in existing}
    rows = []
    for p in passages:
        note, use = "", True
        n = _norm(p["text"])
        if len(p["text"]) < MIN_CHARS:
            note, use = "Too short to be a useful guideline.", False
        elif n in seen:
            note, use = "Already in the guidelines.", False
        elif has_pii(p["text"]) or has_pii(p["title"]):
            note, use = ("Contains an email, phone number, link or ID number, so it is left out. "
                         "Remove that detail to include it."), False
        seen.add(n)
        rows.append({"use": use, "title": p["title"], "text": p["text"], "note": note})
    return rows


def check_rows(rows):
    """(chosen rows, problems). Only ticked rows are checked."""
    chosen, problems = [], []
    for i, r in enumerate(rows, 1):
        if not r.get("use"):
            continue
        title, text = str(r.get("title") or "").strip(), str(r.get("text") or "").strip()
        if not 3 <= len(title) <= MAX_TITLE:
            problems.append("Row %d: the title needs 3 to %d characters." % (i, MAX_TITLE))
        elif not MIN_CHARS <= len(text) <= MAX_CHARS:
            problems.append("Row %d: the text needs %d to %d characters." % (i, MIN_CHARS, MAX_CHARS))
        elif has_pii(text) or has_pii(title):
            problems.append("Row %d still contains an email, phone number, link or ID number." % i)
        else:
            chosen.append({"title": title, "text": text})
    return chosen, problems


def commit(rows):
    """Add the ticked rows to the guidelines and return the new ids."""
    chosen, problems = check_rows(rows)
    if problems:
        raise ValueError(" ".join(problems))
    if not chosen:
        raise ValueError("Tick at least one passage.")
    passages = knowledge.load_guidelines()
    if len(passages) + len(chosen) > knowledge.MAX_GUIDELINES:
        raise ValueError("The guidelines can hold at most %d passages." % knowledge.MAX_GUIDELINES)
    ids = []
    for c in chosen:
        pid = knowledge.next_guideline_id(passages)
        passages.append({"id": pid, "title": c["title"], "text": c["text"]})
        ids.append(pid)
    knowledge.save_guidelines(passages)
    return ids