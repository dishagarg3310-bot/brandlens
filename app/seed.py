from app.core.rules import review_text
from app.db import database as db
from app.db import workflow as wf

RIYA = ("Riya (Creator)", "Creator")
ARJUN = ("Arjun (Manager)", "Manager")
MEERA = ("Meera (Reviewer)", "Reviewer")


def _new(title, content):
    did = db.create_draft(title, RIYA[0])
    vid, _ = db.add_version(did, content, RIYA[0])
    db.save_findings(vid, review_text(content))
    db.log(did, RIYA[0], RIYA[1], "review_run", "demo data")
    return did, vid


def _resolve(did, vid, dispute_cats=()):
    for f in db.get_findings(vid):
        status = "disputed" if f["category"] in dispute_cats else "accepted"
        db.set_finding_status(f["id"], status, RIYA[0], RIYA[1], did)


def seed_demo():
    if db.list_drafts():
        return

    # A: waiting for a decision (Manager / Reviewer queue)
    did, vid = _new(
        "Diwali offer post",
        "Diwali special: our BEST cosmetics are now cheap! Get 25% off on everything. "
        "Users love the gentle formula.",
    )
    _resolve(did, vid, dispute_cats=("Tone",))
    wf.set_status(did, "in_review", RIYA[0], RIYA[1], "version 1")

    # B: changes requested by the manager
    did, vid = _new(
        "Moisturiser product page",
        "Our new moisturiser is clinically proven to cure dry skin. "
        "Guaranteed results for all customers!",
    )
    wf.add_comment(
        did, ARJUN[0], ARJUN[1],
        "Please remove the medical and guarantee claims. Use the dermatologist-tested "
        "fact (F4) instead and resubmit.",
    )
    wf.set_status(did, "changes_requested", ARJUN[0], ARJUN[1], "changes requested")

    # C: approved, with two versions and a reviewer comment
    did, vid = _new(
        "Cruelty-free certification post",
        "We are proud to be certified cruelty-free by PETA India. "
        "Our cosmetics use packaging made from 70% recycled material.",
    )
    _resolve(did, vid)
    new = (
        "We are proud to be certified cruelty-free by PETA India. "
        "Our skincare uses packaging made from 70% recycled material."
    )
    vid2, vno = db.add_version(did, new, RIYA[0])
    fs = review_text(new)
    db.save_findings(vid2, fs)
    db.log(did, RIYA[0], RIYA[1], "new_version", "v%d, %d findings" % (vno, len(fs)))
    wf.set_status(did, "in_review", RIYA[0], RIYA[1], "version %d" % vno)
    wf.add_comment(did, MEERA[0], MEERA[1], "Both claims match approved facts F5 and F6. Approved.")
    wf.set_status(did, "approved", MEERA[0], MEERA[1], "approved")