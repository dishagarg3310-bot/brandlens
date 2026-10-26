import sqlite3
from contextlib import closing
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[2] / "data" / "brandlens.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS drafts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    creator TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'draft',
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS versions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    draft_id INTEGER NOT NULL,
    version_no INTEGER NOT NULL,
    content TEXT NOT NULL,
    created_by TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS findings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    version_id INTEGER NOT NULL,
    code TEXT,
    category TEXT,
    severity TEXT,
    rule_id TEXT,
    rule_title TEXT,
    rule_text TEXT,
    fact_id TEXT,
    fact_text TEXT,
    span_start INTEGER,
    span_end INTEGER,
    text TEXT,
    message TEXT,
    suggestion TEXT,
    source TEXT,
    status TEXT NOT NULL DEFAULT 'open'
);
CREATE TABLE IF NOT EXISTS comments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    draft_id INTEGER NOT NULL,
    author TEXT NOT NULL,
    role TEXT NOT NULL,
    body TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS audit (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    draft_id INTEGER,
    actor TEXT NOT NULL,
    role TEXT NOT NULL,
    action TEXT NOT NULL,
    detail TEXT,
    created_at TEXT NOT NULL
);
"""


def _conn():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def _now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def init_db():
    with closing(_conn()) as c:
        c.executescript(SCHEMA)
        c.commit()


def _query(sql, params=()):
    with closing(_conn()) as c:
        return c.execute(sql, params).fetchall()


def _execute(sql, params=()):
    with closing(_conn()) as c:
        cur = c.execute(sql, params)
        c.commit()
        return cur.lastrowid


def create_draft(title, creator):
    return _execute(
        "INSERT INTO drafts (title, creator, status, created_at) VALUES (?, ?, 'draft', ?)",
        (title, creator, _now()),
    )


def add_version(draft_id, content, author):
    rows = _query("SELECT COALESCE(MAX(version_no), 0) AS m FROM versions WHERE draft_id = ?", (draft_id,))
    vno = rows[0]["m"] + 1
    vid = _execute(
        "INSERT INTO versions (draft_id, version_no, content, created_by, created_at) VALUES (?, ?, ?, ?, ?)",
        (draft_id, vno, content, author, _now()),
    )
    return vid, vno


def save_findings(version_id, findings):
    for f in findings:
        span = f.get("span")
        _execute(
            "INSERT INTO findings (version_id, code, category, severity, rule_id, rule_title, rule_text, "
            "fact_id, fact_text, span_start, span_end, text, message, suggestion, source, status) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'open')",
            (version_id, f.get("id"), f["category"], f["severity"], f["rule_id"], f["rule_title"],
             f["rule_text"], f["fact_id"], f["fact_text"],
             span[0] if span else None, span[1] if span else None,
             f["text"], f["message"], f["suggestion"], f["source"]),
        )


def list_drafts():
    return _query("SELECT * FROM drafts ORDER BY id DESC")


def get_draft(draft_id):
    rows = _query("SELECT * FROM drafts WHERE id = ?", (draft_id,))
    return rows[0] if rows else None


def latest_version(draft_id):
    rows = _query("SELECT * FROM versions WHERE draft_id = ? ORDER BY version_no DESC LIMIT 1", (draft_id,))
    return rows[0] if rows else None


def get_findings(version_id):
    return _query("SELECT * FROM findings WHERE version_id = ? ORDER BY id", (version_id,))


def set_finding_status(finding_id, status, actor, role, draft_id):
    _execute("UPDATE findings SET status = ? WHERE id = ?", (status, finding_id))
    log(draft_id, actor, role, "finding_" + status, "finding #%d" % finding_id)


def log(draft_id, actor, role, action, detail=""):
    _execute(
        "INSERT INTO audit (draft_id, actor, role, action, detail, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (draft_id, actor, role, action, detail, _now()),
    )
