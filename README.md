# BrandLens: Pre-Publication Brand Governance

Catch it before you publish it: every flag explained, every fix suggested, every decision human.

CodeStar 3.0, Round 2 (The Build) | Team: dishagarg3310 | Solo project by Disha Agrawal

**Live demo:** https://brandlens-xqbfsskvbgvx3ttpzrwd9n.streamlit.app
**Repository:** https://github.com/dishagarg3310-bot/brandlens

## What it does

BrandLens reviews a draft before publication against an organisation's approved guidelines, facts and terminology. Every finding says what is wrong, why, which rule or approved fact it is based on, and a suggested fix. Humans accept, dispute, approve or reject. Nothing is changed or approved automatically.

## Try it in 60 seconds

No login needed. Switch roles in the left sidebar.

1. Stay on **Creator**, press **Load sample post**, then **Run review**.
2. Accept or dispute each finding, then press **Submit for review**.
3. Switch to **Manager**, open the submitted draft from the queue, then **Approve** or **Request changes**.
4. **Reviewer** sees a claim-verification table. **Admin** manages the brand knowledge and sees the activity log.

Note: Approve / Request changes appear only for drafts that have been submitted. Pick a submitted draft from the queue.

## Features (working in the live link)

- Four roles: Creator, Manager, Reviewer, Admin
- Draft creation, sample-post loader, versioned drafts
- Rule-based review: unproven claims, terminology, tone, accessibility, missing disclosures
- Each finding shows severity, plain-language explanation, cited rule (e.g. G3) and suggested fix, with a before/after view
- Claim check against the approved fact base, with the approved alternative shown
- Accept / Dispute per finding, logged
- Submit for review, Manager approve / request changes
- Comments per draft, version history, audit log
- Brand health score (0-100) with severity chart
- Approval queue sorted by risk, Reviewer claim-verification table
- Admin knowledge base: guidelines, approved facts, terms, activity log
- Colour theme applied on every page

## Architecture

```
Streamlit UI (role-based pages)
        |
Workflow layer (submit, approve, comments, versioning, audit)
        |
Review engine (rules: terminology, claims vs facts, tone, accessibility, disclosure)
        |
SQLite (users, drafts, versions, findings, comments, audit log)
```

Demo data: a fictional brand, **GreenLeaf Organics**, in `data/sample_brand`. No real or confidential data is used.

## Main technical decisions

1. **Evidence-or-silence:** a finding is shown only with the rule or approved fact behind it.
2. **Rules first, AI later:** a deterministic engine is predictable, fast and cannot invent false flags. The AI layer is planned for Round 3.
3. **Human control:** AI never edits or approves content. Every accept, dispute, approval and comment is logged with user and time.
4. **Streamlit + SQLite:** the fastest way for a solo developer to ship a complete, deployable workflow.

## Tech stack, libraries and services

- Python, Streamlit (UI), SQLite (storage)
- Libraries: see `requirements.txt`
- Hosting: Streamlit Community Cloud (free tier)
- AI models / external APIs: **none in this build** (sidebar shows "AI review layer: off")
- Tests: `python -m unittest` (28 tests)

## What changed from the Round 1 plan

- Planned FastAPI, ChromaDB retrieval, local embeddings and an LLM judgement layer. In this build I prioritised a complete, reliable human workflow (draft -> findings -> approval -> audit), so the engine is rule-based and the AI layer is off.
- Dropped the separate FastAPI backend to keep the solo build simple.
- Added: risk-sorted approval queue, brand health score, plain-language finding cards, colour themes.
- Moved to Round 3, as planned: image review, PDF/DOCX upload, insights dashboard.

## Known limitations (what does not work yet)

- No AI judgement layer, retrieval over guidelines or redaction yet.
- Text drafts only; no image, PDF or DOCX review.
- No insights dashboard yet.
- Login is a demo role switcher, not real authentication.
- Data may reset when the free Streamlit Cloud app restarts; demo drafts reload automatically.
- Rule checks are keyword/pattern based and can miss subtle tone issues.

## Testing

**Automated:** 28 unit tests (`python -m unittest`).

**Manual testing of the deployed app (by me, all four roles, 27-28 Oct 2026):**

- Found that a Reviewer/Manager opening a draft still in *Draft* status sees "Waiting for the Creator to resolve findings and submit" and no Approve button. This is the intended rule (approval only after submission), but it was not obvious which draft to pick. Documented in "Try it" above; clearer wording planned.
- Found that the colour theme was applied only on the draft screen, so Admin and Reviewer pages looked different. Fixed by applying the theme once for the whole app.
- Found the findings cards were hard to read (code-like "Source: G3", duplicate "BEST", unclear "Suggested fix"). Rewrote them with plain-language labels, severity sorting and a before/after view.
- Found the role badge looked cut off; redesigned it per role with larger text and role colours.

**User feedback from other people:** not collected yet. Structured user testing with a small group is planned for Round 3 and results will be reported then.

## Responsible design

- Human oversight: AI only suggests; approvals and overrides are human and logged.
- Privacy: synthetic demo brand only; no customer data is used.
- Explainability: each finding shows its rule or approved fact.
- Disclosure: the interface states that the AI layer is off in this build.

## Contribution

Solo project. Design, review engine, backend, UI, testing and deployment by Disha Agrawal.

## Disclosures

- AI assistance: Claude (Anthropic) was used for planning and coding help. I reviewed, tested and deployed the code myself.
- No product code was written before the official build window.
- Reused: open-source libraries listed in `requirements.txt`.

## Run locally

```
pip install -r requirements.txt
streamlit run streamlit_app.py
```

## Round 3 plan

1. Governance insights dashboard (repeated mistakes, unclear guidelines)
2. Image and document review (PNG/JPG, PDF, DOCX)
3. Retrieval-backed AI judgement with privacy redaction and an evaluation report