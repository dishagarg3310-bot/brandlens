# BrandLens: Pre-Publication Brand Governance

**Catch it before you publish it: every flag explained, every fix suggested, every decision human.**

CodeStar 3.0, Round 3 (The Finish) | Problem statement by Inkloom AI | Team: dishagarg3310 | Solo project by Disha Agrawal

| | |
|---|---|
| **Live product** | https://brandlens-xqbfsskvbgvx3ttpzrwd9n.streamlit.app |
| **Source code** | https://github.com/dishagarg3310-bot/brandlens |

---

## Try it in 60 seconds (for judges)

Open the live link. After the short welcome animation you land on the sign-in page. Press any role card to enter with one click, or type the details below.

| Role | Username | Password | What this role does |
|---|---|---|---|
| Creator | `riya` | `Creator@123` | Writes or uploads a draft, fixes the findings, submits it |
| Manager | `arjun` | `Manager@123` | Approves a draft or asks for changes |
| Reviewer | `meera` | `Reviewer@123` | Checks risky claims against approved facts |
| Admin | `sana` | `Admin@123` | Manages guidelines, facts and terms, sees insights |

These are demo accounts for a **fictional brand** (GreenLeaf Organics). No real or confidential data exists in the product. They are public on purpose so you can test every role.

**Suggested path**

1. Enter as **Creator**. Press **Load sample post**, then **Run review**. A progress bar at the top and a "Next:" box tell you what to do at every step.
2. Press **Accept** or **Dispute** on each finding, then **Submit for review**.
3. Press **Switch role**, enter as **Manager**. The first draft waiting for a decision opens by itself. Press **Approve** or **Request changes**.
4. Enter as **Reviewer** to see the claim-verification table, and as **Admin** to see the knowledge base and the insights dashboard.
5. Try the **upload** box as Creator: a PDF, a Word file, or a poster image with text on it (the text is read with OCR).

The three drafts that are already loaded let you explore every role straight away.

---

## What it does

BrandLens reviews content **before** it is published against an organisation's approved guidelines, facts and terminology. Every finding says:

- what is wrong, in plain language,
- **why**, and which guideline (for example G3) or approved fact it is based on,
- how to fix it, with a before/after view.

The draft then moves through a role-based human approval workflow. The system only suggests. A person accepts, disputes, approves or rejects, and every action is logged with who and when.

## Features

**Review engine**
- Checks tone, terminology, unproven or absolute claims, accessibility, visual identity and missing disclosures
- Claim check against approved facts, with the approved alternative shown
- Optional AI layer for subtler tone and messaging issues, always tied to a guideline passage (see "AI and privacy")
- Brand health score (0 to 100) with a severity chart
- Inline highlighted draft, severity-sorted finding cards

**Content formats**
- Paste text, or upload **PDF, Word (.docx), TXT, Markdown, PNG, JPG**
- Scanned PDFs and text inside images are read with **OCR** (runs on the server, nothing is sent out)
- Image checks: alt text quality, brand colour palette, and WCAG contrast
- Word files: images without alt text are flagged

**Workflow and control**
- Four roles with one-click demo sign-in and real password sign-in (hashed passwords, lockout after repeated failures)
- Accept or dispute each finding, submit, approve or request changes
- Comments, version history (every edit is a new version), full audit log
- Risk-sorted approval queue, reviewer claim table
- Workflow rules are enforced in the code, not only in the buttons (for example a draft cannot be approved twice, or approved before it is submitted)
- Download any review as a Markdown report or a CSV

**Governance insights**
- Most repeated mistakes by rule and category, trend over time
- Per-creator view ("Your recurring mistakes")
- **Possibly unclear guidelines:** rules that creators dispute often are flagged, so the admin knows which guideline to rewrite

**Admin**
- View and extend guidelines, approved facts and preferred terms
- Activity log

## Architecture

```
Streamlit UI (sign-in, welcome animation, role pages, progress bar)
        |
Workflow layer  (guarded status changes, comments, versions, audit log)   app/db/workflow.py
        |
Review pipeline                                                           app/core/review.py
   |-- Rule engine   (terminology, claims vs facts, tone, accessibility)  app/core/rules.py
   |-- Document and image intake (PDF, DOCX, OCR, alt text, contrast)     app/core/documents.py
   '-- Optional AI layer
         redaction  ->  retrieval of relevant passages  ->  LLM  ->  validation
         app/core/redaction.py   app/core/retrieval.py     app/core/llm.py
        |
SQLite (drafts, versions, findings, comments, audit log)                  app/db/database.py
```

### Main technical decisions

1. **Evidence-or-silence.** A finding is shown only with the rule or approved fact behind it. An AI finding that does not cite a real retrieved passage is dropped.
2. **Rules first, AI second.** A deterministic engine is predictable, fast and testable. The AI layer adds subtle cases on top and can fail without breaking anything.
3. **Human control.** Nothing is edited or approved automatically. The AI only suggests.
4. **Fail safe.** If the AI service is slow or down, the review continues with rule checks and the screen says so. If OCR is not installed, the rest still works and the screen says so.
5. **Streamlit and SQLite.** The quickest way for one developer to ship a complete, deployable workflow.

## AI and privacy

- The AI layer is **optional**. There is an "Also ask the AI layer" checkbox on the Creator screen, and the sidebar and the banner show whether it is on.
- **Before any outside call**, emails, links, UPI ids, phone numbers and PAN or Aadhaar-style numbers are replaced with placeholders such as `[EMAIL_1]`. The AI never sees the originals.
- **Retrieval:** the AI sees only the few guideline passages and approved facts most relevant to the draft, not the whole brand book.
- Supported providers (set one key): **Google Gemini** (free tier) or **Anthropic Claude**. If no key is set, the product runs on rule checks alone.
- Limits: 8 AI calls per session, 10 second wait, the same text is not sent twice.
- **OCR runs locally** with Tesseract. Uploaded files are parsed, never executed, and have strict size limits (5 MB, 30 pages, 20,000 characters).
- Uploaded drafts are stored in the app's SQLite database only. The demo brand is fictional.

## Run it on your own computer

Needs Python 3.10 or newer (tested on 3.12).

```bash
git clone https://github.com/dishagarg3310-bot/brandlens.git
cd brandlens

python -m venv venv
venv\Scripts\activate            # Windows
# source venv/bin/activate       # macOS or Linux

pip install -r requirements.txt
streamlit run streamlit_app.py
```

Open http://localhost:8501. The database is created and filled with three demo drafts on first start. To reset it, stop the app and delete `data/brandlens.db`.

**Optional: AI layer.** Create `.streamlit/secrets.toml` (this file is git-ignored; never commit it):

```toml
GEMINI_API_KEY = "your-key"
GEMINI_MODEL = "a-fast-flash-model-name"
# or, instead of Gemini:
# ANTHROPIC_API_KEY = "your-key"
```

`python tools/check_gemini.py` lists the models your key can use and times each one.

**Optional: OCR.** Install Tesseract (Windows: the UB Mannheim installer; Ubuntu: `sudo apt install tesseract-ocr tesseract-ocr-hin`; macOS: `brew install tesseract`). Without it everything still works and the app says that text recognition is not installed.

### Deploy on Streamlit Community Cloud

1. Push the repository to GitHub. Main file: `streamlit_app.py`.
2. `requirements.txt` installs the Python libraries and `packages.txt` installs Tesseract. Do not delete either.
3. In the app settings, add the keys above under **Secrets**.

## Testing

```bash
python -m unittest discover -s tests
```

**114 automated tests** (3 OCR tests are skipped on machines without Tesseract):

| File | Covers |
|---|---|
| `test_rules.py`, `test_score.py` | rule engine, scoring |
| `test_ai_layer.py`, `test_provider.py` | redaction, retrieval, AI validation, provider switching, AI failures |
| `test_documents.py` | PDF, DOCX, images, OCR, contrast, hostile and corrupt files |
| `test_insights.py` | repeated mistakes, unclear-guideline detection |
| `test_robustness.py` | what a user might do: empty or huge text, HTML and markdown injection, repeated clicks, wrong role, empty database, whole-app flows for every role |

**Evaluation of the review engine** (`python -m evaluation.run_eval`, add `--ai` for the AI layer, `--set holdout` for unseen posts):

| Set | Mode | Precision | Recall |
|---|---|---|---|
| Development, 51 posts (rules were tuned on these) | rules only | 100% | 100% |
| Development, 51 posts | rules and AI | 98% | 100% |
| **Held-out, 15 new posts written after tuning** | rules only | 77% | 62% |

The held-out result is the honest one for rules alone: keyword rules miss new wordings, which is exactly why the AI layer exists. Full reports are in `evaluation/`. On the development set the one AI "false alarm" (post P42) is a defensible off-tone finding that the labels did not include; it was not relabelled to improve the score.

## Security and accessibility

- Passwords are salted PBKDF2-SHA256 hashes, compared in constant time; five wrong tries lock the form for a minute. The demo credentials are public on purpose; a real deployment would use single sign-on.
- Allowed status changes and who may make them are enforced in `app/db/workflow.py`.
- Everything a user types is escaped before it is shown. No API keys are stored in the repository.
- Accessibility is part of the product: alt text, link text, reading level and WCAG contrast are checked in the content. The interface uses a progress bar and a plain "Next:" instruction, and the welcome animation is skipped for people who set "reduce motion".

## Known limitations

- Sign-in uses a fixed list of demo accounts (no self-service sign-up). A production version would use SSO and a user database.
- SQLite on the free Streamlit Cloud tier can reset when the app restarts; the demo drafts reload automatically.
- Rule checks are keyword and pattern based. The AI layer helps, but it depends on an outside free-tier service whose speed varies; when it is slow the review continues with rule checks.
- OCR reads clean printed text well. Photos, handwriting and very small text can contain mistakes, so the app asks the user to check the extracted text.
- Scanned PDFs: only the first 5 pages are read with OCR.
- Contrast is estimated from the image's dominant colours, not from the exact text and background pixels.
- One brand per deployment. English and Hinglish are tested; other languages are not.

## Roadmap

1. **Apply accepted fixes:** one click applies only the fixes the creator accepted and saves a new version, with a before and after score.
2. **"What the AI saw" panel:** shows the redacted text sent, which passages were retrieved, and which provider answered.
3. **Channel checks:** length, hashtags and disclosure rules per platform (Instagram, LinkedIn, X, email).
4. **Two-key approval:** high-risk claims need both a Manager and a Reviewer.
5. Self-service sign-up with Creator as the default role, and roles assigned by an Admin.
6. A persistent database (for example Postgres) and single sign-on.
7. Text-level contrast from OCR boxes, more Indian languages, and multi-brand workspaces.

## What changed since Round 2

- **Improvement 1, governance insights dashboard:** repeated mistakes, per-creator view, possibly unclear guidelines.
- **Improvement 2, image and document review:** PDF, DOCX, images, OCR for scans and images, alt text, palette and WCAG contrast.
- **Improvement 3, retrieval-backed AI judgement:** redaction, retrieval, citation check, an evaluation report with precision and recall, and a held-out set.
- Real sign-in with roles, server-side workflow rules, robustness fixes found by testing, downloadable reports, a clearer interface (progress bar, "Next:" box, one-click demo sign-in) and a new visual design.

## Project structure

```
streamlit_app.py        entry point
app/
  main_ui.py            page layout and sidebar
  ui.py, views.py       draft screens, queue, claim table, admin
  design.py             welcome animation, banner, progress bar, sign-in look
  auth.py               sign-in
  insights.py           governance insights
  export.py             report and CSV download
  seed.py               demo drafts
  core/                 review, rules, documents (PDF, DOCX, OCR, images),
                        llm, retrieval, redaction, score, knowledge
  db/                   database, workflow
data/sample_brand/      guidelines.md, facts.csv, glossary.csv (fictional brand)
evaluation/             labelled sets, run_eval.py, reports
tests/                  automated tests
tools/check_gemini.py   find a fast Gemini model for your key
requirements.txt  packages.txt  .streamlit/config.toml
```

## Disclosures

- **AI assistance:** Claude (Anthropic) was used for planning and coding help. I reviewed, tested and deployed the code myself.
- **External services in the product:** Google Gemini or Anthropic Claude for the optional AI layer (text is redacted first); Google Fonts for the welcome animation. Both are optional and the product works without them.
- **Libraries:** Streamlit, pandas, scikit-learn, pdfplumber, python-docx, Pillow, pytesseract (Tesseract OCR), textstat, python-dotenv, anthropic. Licences are those of each library.
- **Data:** the brand, guidelines, facts and sample posts are synthetic and written for this project.
- **Contribution:** solo project. Design, review engine, workflow, interface, testing and deployment by Disha Agrawal (Banasthali Vidyapith, B.Tech Computer Science and Engineering).