"""Redact personal data before any text is sent to an external AI service.

redact(text) -> (safe_text, mapping), where mapping maps each placeholder such as
[EMAIL_1] back to the original value. restore() puts the originals back, so findings
returned by the AI can be located in the creator's real draft.
"""
import re

# Order matters: emails are replaced before UPI-style handles.
_PATTERNS = [
    ("EMAIL", re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")),
    ("URL", re.compile(r"(?:https?://|www\.)[^\s<>\"']+")),
    ("UPI", re.compile(r"\b[\w.-]{2,}@[a-z]{2,}\b")),
    ("ID", re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b|\b\d{4}\s\d{4}\s\d{4}\b")),  # PAN, Aadhaar-style
    ("PHONE", re.compile(r"(?<!\w)(?:\+91[\s-]?|0)?[6-9]\d{4}[\s-]?\d{5}(?!\d)")),
]


def redact(text):
    mapping = {}
    seen = {}
    counters = {}

    def make(kind):
        def repl(m):
            original = m.group(0)
            key = (kind, original)
            if key not in seen:
                counters[kind] = counters.get(kind, 0) + 1
                token = "[%s_%d]" % (kind, counters[kind])
                seen[key] = token
                mapping[token] = original
            return seen[key]

        return repl

    out = text
    for kind, pattern in _PATTERNS:
        out = pattern.sub(make(kind), out)
    return out, mapping


def restore(text, mapping):
    for token, original in mapping.items():
        text = text.replace(token, original)
    return text


def has_pii(text):
    return bool(redact(text)[1])
