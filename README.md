\# BrandLens



Pre-publication brand governance platform, built for CodeStar 3.0 (Round 2).



\*\*Live app:\*\* https://brandlens-xqbfsskvbgvx3ttpzrwd9n.streamlit.app/

(No login needed. Use the demo-role switcher in the left sidebar. Three demo drafts are pre-loaded.)



\## What it does

A content draft is checked \*\*before publication\*\* against a brand's approved guidelines, approved facts and glossary. Every finding explains what is wrong, cites the guideline or approved fact behind it, and suggests a fix. Nothing is changed or approved automatically; a human decides.



\*\*Core workflow:\*\* Creator writes a draft, automated review runs, findings come back with sources, the Creator accepts or disputes each finding and submits, a Manager or Reviewer approves or requests changes, and the approved copy can be downloaded.



\## Completed features (Round 2)

\- Review of text drafts: terminology, tone (ALL CAPS, exclamation marks), unsupported promotional claims, accessibility (non-descriptive links, reading level) and disclosures (offer end date, #ad on sponsored posts)

\- Every finding shows severity, flagged text, suggested fix, the guideline (G1-G6) and, where relevant, the approved fact (F1-F6) behind it

\- Claim verification table for reviewers (claim, verdict, approved fact, creator decision)

\- Optional AI review layer (Anthropic Claude) for tone, messaging and claims that keyword rules miss. An AI finding is kept only if it cites a valid guideline id and quotes text that really exists in the draft; otherwise it is dropped. AI findings carry an "AI-suggested" tag. The layer is on only when an API key is configured; without it the app runs on rule checks alone.

\- Role-based views: Creator, Manager (approval queue), Reviewer (risk-sorted queue with claim verification) and Admin (knowledge base)

\- Accept or dispute findings, submit for review, approve, request changes

\- Comments, full revision history (every edit saves a new version and is re-reviewed) and an audit trail of every action

\- Admin can add an approved fact or a banned term, applied to the next review

\- Download of the approved copy with an AI-assisted / human-approved note



\## Planned for Round 3

1\. \*\*Image and document review:\*\* PDF, DOCX and image upload with OCR, alt-text, colour-contrast and brand-palette checks.

2\. \*\*Insights dashboard:\*\* recurring mistakes over time and the guidelines that are disputed most often (a sign that they are unclear).

3\. \*\*Reliability and privacy:\*\* evaluation on about 50 labelled samples with precision and recall, redaction of sensitive details before any AI call, and a persistent database.



\## Technology

Python, Streamlit (UI), SQLite (drafts, versions, findings, comments, audit), pandas, textstat (readability), Anthropic Python SDK (optional AI layer), deployed on Streamlit Community Cloud. Brand knowledge is in `data/sample\_brand/` (guidelines.md, facts.csv, glossary.csv) for a fictional brand, GreenLeaf Organics, so no real confidential data is used.



\## Architecture

\- `app/core/knowledge.py` loads guidelines (as passages with IDs), approved facts and the glossary

\- `app/core/rules.py` deterministic rule layer; every finding carries its source

\- `app/core/llm.py` optional AI layer with citation and text validation

\- `app/core/review.py` runs rules, then the AI layer (with a per-session cap), merges and numbers the findings

\- `app/db/database.py` and `app/db/workflow.py` storage, status changes, comments, versions, audit

\- `app/ui.py`, `app/views.py`, `app/main\_ui.py` Streamlit screens for each role

\- `app/seed.py` loads three demo drafts on a fresh database



\## Changes from the Round 1 plan

\- One Streamlit app instead of Streamlit + FastAPI, to keep a single reliable link.

\- Login replaced by a demo-role switcher so every role can be tried without help.

\- The guideline set is small, so all passages are passed to the AI layer; embeddings-based retrieval is deferred.

\- Because the Round 2 window is short, image review, document upload and the insights dashboard moved to Round 3.



\## Known limitations

\- Rule checks use keyword and pattern matching; the AI layer is advisory and can be wrong, which is why every finding can be disputed.

\- Demo roles are not real authentication.

\- The database is on temporary storage, so data resets when the hosted app restarts (demo drafts are reloaded automatically).



\## AI use and disclosure

\- AI assistance (Claude by Anthropic) was used during development, for example to help write and review code, and is used inside the product as the optional review layer.

\- Initial project setup (skeleton, sample data, first rule module, basic screen) was done before the 10:00 AM opening on 26 Oct; all other features were built during Round 2.

\- Libraries: Streamlit, pandas, textstat, scikit-learn and the Anthropic SDK are used under their licences.



\## Run locally



&#x20;   python -m venv venv

&#x20;   venv\\Scripts\\activate

&#x20;   pip install -r requirements.txt

&#x20;   streamlit run streamlit\_app.py



Optional: set `ANTHROPIC\_API\_KEY` (in `.streamlit/secrets.toml` or as an environment variable) to enable the AI layer.

## Testing

    python -m unittest -v

28 automated tests cover the rule layer: terminology, claims linked to approved facts, tone, accessibility and disclosures, plus checks that every finding cites a guideline and quotes text that really exists in the draft.
