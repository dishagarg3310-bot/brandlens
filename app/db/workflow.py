from app.db.database import _execute, _now, _query, log


MAX_COMMENT = 2000

# (current status, new status) -> roles allowed to make that move
TRANSITIONS = {
    ("draft", "in_review"): {"Creator"},
    ("changes_requested", "in_review"): {"Creator"},
    ("draft", "draft"): {"Creator"},               # saving a new version
    ("changes_requested", "draft"): {"Creator"},
    ("in_review", "approved"): {"Manager", "Reviewer"},
    ("in_review", "changes_requested"): {"Manager", "Reviewer"},
}


def get_status(draft_id):
    rows = _query("SELECT status FROM drafts WHERE id = ?", (draft_id,))
    return rows[0]["status"] if rows else None


def set_status(draft_id, status, actor, role, detail=""):
    """Move a draft to a new status. Returns False (and changes nothing) when the move is not
    allowed for this role from the draft's current status, e.g. approving twice or approving a
    draft that was never submitted. The rule lives here, not only in the buttons."""
    current = get_status(draft_id)
    if current is None or role not in TRANSITIONS.get((current, status), set()):
        return False
    _execute("UPDATE drafts SET status = ? WHERE id = ?", (status, draft_id))
    log(draft_id, actor, role, "status_" + status, detail)
    return True


def add_comment(draft_id, author, role, body):
    body = (body or "").strip()[:MAX_COMMENT]
    if not body or get_status(draft_id) is None:
        return False
    _execute(
        "INSERT INTO comments (draft_id, author, role, body, created_at) VALUES (?, ?, ?, ?, ?)",
        (draft_id, author, role, body, _now()),
    )
    log(draft_id, author, role, "comment", body[:80])
    return True


def list_comments(draft_id):
    return _query("SELECT * FROM comments WHERE draft_id = ? ORDER BY id", (draft_id,))


def list_versions(draft_id):
    return _query("SELECT * FROM versions WHERE draft_id = ? ORDER BY version_no DESC", (draft_id,))


def list_audit(draft_id):
    return _query("SELECT * FROM audit WHERE draft_id = ? ORDER BY id DESC", (draft_id,))