from app.db.database import _execute, _now, _query, log


def set_status(draft_id, status, actor, role, detail=""):
    _execute("UPDATE drafts SET status = ? WHERE id = ?", (status, draft_id))
    log(draft_id, actor, role, "status_" + status, detail)


def add_comment(draft_id, author, role, body):
    _execute(
        "INSERT INTO comments (draft_id, author, role, body, created_at) VALUES (?, ?, ?, ?, ?)",
        (draft_id, author, role, body, _now()),
    )
    log(draft_id, author, role, "comment", body[:80])


def list_comments(draft_id):
    return _query("SELECT * FROM comments WHERE draft_id = ? ORDER BY id", (draft_id,))


def list_versions(draft_id):
    return _query("SELECT * FROM versions WHERE draft_id = ? ORDER BY version_no DESC", (draft_id,))


def list_audit(draft_id):
    return _query("SELECT * FROM audit WHERE draft_id = ? ORDER BY id DESC", (draft_id,))