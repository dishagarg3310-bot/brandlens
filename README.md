# BrandLens: Pre-Publication Brand Governance
CodeStar 3.0, Round 2 (The Build). Solo project by Disha Agrawal.

Live demo: https://brandlens-xqbfsskvbgvx3ttpzrwd9n.streamlit.app/
Demo roles (switch in the sidebar): Creator, Manager, Reviewer, Admin. No password needed.

## What works end to end
Creator writes a draft -> automated review -> findings with explanation, cited rule/fact and suggested fix -> Accept / Dispute -> Submit -> Manager approves or requests changes -> comments, revision history and audit trail.

## Architecture
- Frontend: Streamlit (role-based screens, findings cards, comments, version history)
- Storage: SQLite (users, drafts, versions, findings, comments, audit log)
- Review engine: rule layer (terminology, claims vs approved facts, tone, disclosure, accessibility) -> findings with severity, rule ID and fact ID
- AI layer: [off by default / on, using Claude API]. AI only suggests; humans approve.
- Principle: every finding cites an approved rule or fact (evidence-or-silence).

## Main technical decisions
1. Rules first, AI second: predictable, fast, no hallucinated flags.
2. SQLite: zero setup, fits a single-developer MVP; PostgreSQL later.
3. Human control: no automatic edits or approvals; every action is logged with user and time.
4. Synthetic brand (GreenLeaf Organics) so no confidential data is used.

## Libraries and services
[List from requirements.txt]. AI service: [Anthropic Claude API / none in this build].

## Three improvements (Round 3)
1. Insights dashboard (repeated mistakes, unclear guidelines)
2. Image review and PDF/DOCX upload
3. Reliability and privacy (evaluation report, redaction before AI calls)

## User testing
[Name/role, date, 2-3 lines of feedback, what I changed.] (Add 2-3 real testers.)

## Contribution
Solo: design, backend, review engine, UI, testing, deployment by Disha Agrawal.

## Disclosures
AI assistance: Claude (Anthropic) was used for planning and code assistance; I reviewed and tested the code. No code was written before the build window. Reused: open-source libraries listed above.

## Run locally
pip install -r requirements.txt
streamlit run streamlit_app.py