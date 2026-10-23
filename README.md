# CareerLens

A single-user, local career workspace built with FastAPI, SQLite, vanilla HTML/CSS/JavaScript, locally bundled Mozilla PDF.js, Google's official `google-genai` SDK, and ReportLab. Upload a PDF, discover actual published jobs, prepare a fact-grounded resume for one role, compare required-skill coverage, and save every version.

## Run locally

Python **3.12 or newer** is required. This checkout was built and tested on Python **3.13.2**.

```sh
git clone https://github.com/QuantumGod007/CareerLens_demo.git
cd CareerLens_demo
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
# For the exact versions verified in this checkout, use requirements.lock.txt instead.
# Only for a fresh checkout without an existing .env:
cp -n .env.example .env
```

Edit `.env` locally:

```dotenv
GEMINI_API_KEY=your_key_here
GEMINI_MODEL=gemini-2.5-flash
GREENHOUSE_BOARDS=stripe,cloudflare
LEVER_BOARDS=spotify
DATA_DIR=./data
```

Keep your API key in the local, ignored `.env` file. Never put credentials in frontend JavaScript or commit `.env`.

Start the app:

```sh
.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Open **http://127.0.0.1:8000**. API documentation is at **http://127.0.0.1:8000/api/docs**. Keep the server bound to loopback; this MVP has no authentication. Use `--reload` during development if desired. Restart after changing `.env`.

## Use the workspace

1. Upload an unlocked PDF resume (up to 10 MB and 15 pages) and enter a preferred role.
2. Gemini processes the PDF natively, including scanned documents, and saves a structured profile. Review or edit it in **My resume**, then use **Confirm profile & find jobs**. Edits require confirmation again.
3. **Find jobs** fetches published listings from the configured company boards. Search by role, optionally filter by location or early-career titles, and inspect a listing in the split view.
4. **Analyse & enhance** extracts evidenced requirements, tailors the saved facts, independently verifies proposed rewrites, generates a PDF, and saves a new job-specific record. This can take a minute or two.
5. Inspect **Role analysis**, **Resume comparison**, **Skill coverage**, and both actual PDF previews. Download the tailored version.
6. In **Review application**, answer the local review questions and optionally run a **simulated submission**. The local test receiver stores the answers and a receipt. **No employer receives this test.** Use the employer's original link to apply manually.
7. Reopen any saved assessment from **Application history**. Older profiles, job descriptions, assessments, answers, and PDFs remain associated with their own records, including after restarting the server or replacing the main resume.

## Configure real public sources

There are two adapters, with no scraping service or extra API keys:

- Greenhouse: `GET https://boards-api.greenhouse.io/v1/boards/{board}/jobs?content=true`
- Lever: `GET https://api.lever.co/v0/postings/{board}?mode=json`

Use **board identifiers**, not full URLs. Comma-separated values add companies; an empty value disables that provider. For example, `GREENHOUSE_BOARDS=stripe` and `LEVER_BOARDS=` fetch only Stripe's Greenhouse board. Board ownership and identifiers can change. A source's status and live listing count appear beside the results; unavailable boards never turn into invented listings.

The defaults were checked during development. They are examples of actual public employers, not a promise of internships, freshers' eligibility, specific locations, or permanent availability. The sources are fetched again on every search. Duplicate links are removed while preserving job identifiers in query strings such as `gh_jid`.

Ranking uses role-title words, a small transparent role synonym map, the number of candidate skills appearing in the description, and early-career title signals. It is a deterministic discovery heuristic, **not a fit percentage**. The interface explains the actual signals. At most 10 matching jobs are returned. A broader search or different companies may be necessary when no suitable roles exist.

PDF previews render locally using the bundled Mozilla PDF.js library and its included fonts/maps. No Node installation or frontend build is required to run the app.

Public GET APIs do not provide the complete employer application form in this implementation. Review questions are clearly identified as **local test questions**, not actual employer-required fields.

## Resume accuracy and coverage

The original PDF is sent to Gemini once per upload, not once per job. Contact details, links and skills are copied directly from the saved profile into every tailored PDF. Every tailored fact references an existing fact ID. Unknown IDs and duplicates are rejected, unexplained omissions are restored, and new metrics or skill changes are blocked. Gemini may select fewer projects only with an explicit JD-based reason accepted by an independent check; excluded projects remain in the original profile and change log. Education, experience and other qualifications cannot be excluded. Exact repeated text is removed and related bullets share one project/experience heading. Rewrites also require an independent Gemini entailment check and local guards that preserve names, technical terms, scope qualifiers and metrics. If verification fails or is unavailable, the original wording is retained. Tailoring can still reorder sections and facts without changing claims. When no content improvement passes verification, the UI reports that source wording was retained. Selected JD snapshots, profile versions and assessment PDFs remain linked; stale profiles/listings and overlapping AI operations are rejected.

AI extraction and requirement classification can make mistakes. Review the editable profile, original PDF, evidence excerpts and final PDF. The application deliberately favors retaining factual wording over speculative improvements. It does not add missing skills or invent experience.

The local required-skill formula is:

```text
Distinct matched explicit required skills / distinct explicit required skills * 100
```

Both original and tailored versions use **the same saved job requirements**. Preferred skills, general responsibilities and implied qualifications do not increase the denominator. Every accepted skill has a quote found in the actual saved job description. Matching uses explicit text, documented aliases and narrow evidence categories. A named programming language such as Python can support a broad “programming” requirement; named tools such as ChatGPT can support “AI tools”. The app shows the exact evidence for each accepted match and does not infer communication skills or AI-tool experience from a generic project. Skill aliases are boundary-aware: JavaScript is not Java, C++ is not C, and PostgreSQL alone is not SQL. With no explicit required skills, coverage is **N/A**. A reordered resume can legitimately receive an unchanged score.

Original coverage normally uses locally extracted text from the original PDF. When the PDF has little or no extractable text, it uses the saved Gemini transcription and labels that baseline. Tailored coverage uses text extracted from the **actual generated PDF**, not just the proposed AI output. User profile edits can change future tailored content; the original PDF baseline remains the original uploaded document.

Older saved assessments show coverage recalculated with the current checker, alongside their previously saved percentages. This is a read-only calculation using the same saved text and job requirements; the SQLite record and PDF remain untouched. **Prepare updated version** uses your current saved profile and the same saved job requirements to create a separate assessment and PDF with the latest tailoring and formatting. It does not rerun requirement classification or change the comparison denominator.

PDF text extractability, contact retention, detected section reading order, and full fact retention are reported **separately** from skill coverage. Page breaks or unusual source layout can trigger a review flag. Always inspect the visual previews for clipping or unusual ordering. This is **not an official employer ATS score**, a hiring prediction, or a shortlisting guarantee.

## Project layout

```text
app/
  main.py                  FastAPI routes, same-origin protections, static frontend
  config.py                Local environment settings
  models.py                Validated candidate and AI response schemas
  services/
    gemini.py              PDF extraction, evidenced analysis, guarded tailoring
    discovery.py           Source orchestration, filtering, deduplication, ranking
    scoring.py             Deterministic skill coverage and readability checks
    pdf.py                 Portable, text-extractable ReportLab PDFs
    store.py               SQLite persistence and immutable assessment snapshots
  sources/
    greenhouse.py          Greenhouse public Job Board adapter
    lever.py               Lever public Postings adapter
  static/
    index.html             Semantic application shell
    styles.css             Responsive design tokens and styles
    app.js                 Functional frontend, state, forms, comparison and previews
scripts/live_smoke.py       Opt-in Gemini + live-source integration check
tests/                     Offline automated regression tests
.env.example               Configuration template without credentials
requirements.txt           Python dependencies
```

Generated PDFs use a consistent single-column A4 template: **DejaVu Sans**, 10.2 pt body, 10 pt section headings, 22 pt name, and 9 pt contact details. Gemini tailors content; Python controls font, spacing and page breaks. The original uploaded PDF is preserved.

## Local storage and security

`DATA_DIR` is created automatically. SQLite stores structured profile data, listings, per-job snapshots, coverage, changes, timestamps, and local simulation answers. Uploaded PDFs and generated resumes are separate files under `uploads/` and `resumes/`; file contents are never stored in SQLite. The data directory, test outputs, `.env` and virtual environment are ignored by Git. Uploaded file paths use generated IDs instead of user filenames.

Resumes are sent to Google's Gemini API for extraction; structured profile and job data are sent for analysis, tailoring and verification. Data is not sent to employers. API keys stay in the Python backend, are not included in API responses, and are not printed in application errors. Cross-origin writes are rejected, allowed hosts are limited to localhost, and external content is rendered as escaped text. There are no CDN dependencies, analytics, remote fonts, background job fetches, authentication, payments, or deployment infrastructure.

## Tests and live verification

Offline regression tests use explicit test doubles and fixture listings; they never claim to verify a live provider:

```sh
.venv/bin/python -m pytest -q
node --check app/static/app.js
```

The separate opt-in integration check **uses Gemini API credits** and real public job endpoints. It creates a fictional resume labelled **TEST ONLY** and stores all of its data under ignored `tmp/live-smoke/`, leaving the main workspace empty:

```sh
.venv/bin/python scripts/live_smoke.py
```

It checks native PDF extraction, live discovery, real Gemini analysis/tailoring, factual retention, the coverage formula, PDF downloads, simulated submission, and persistence after creating a new app instance. Its machine-readable report is `tmp/live-smoke/report.json`. Sources or Gemini can be unavailable; a failure is reported rather than replaced with a successful fixture. See `VERIFICATION.md` for the checks completed on this checkout.

## Troubleshooting

- **Key rejected:** replace `GEMINI_API_KEY`, check project/API permissions in AI Studio, and restart.
- **Quota or billing error:** check your project's rate limits and available credits in AI Studio. This does not erase saved work.
- **Model unavailable:** change `GEMINI_MODEL` to a PDF-capable model available to your project and restart.
- **Unreadable or locked PDF:** export an unlocked PDF. Scans can be interpreted by Gemini, but local extractability may still be flagged for review.
- **No jobs:** broaden the title, remove filters, or configure different supported company boards. The app searches those boards, not the entire web.
- **Port occupied:** use `--port 8002`, then open that port's localhost address.
- **Slow analysis:** several Gemini calls run in sequence to extract requirements, propose edits and verify edits. The app serializes AI operations to protect profile consistency. Keep the tab open until it finishes.
- **PDF preview unavailable in your browser:** use the dialog's **Download PDF** action.
- **Python certificate errors:** install current `certifi` in the virtual environment; do not disable TLS certificate verification.

Official API references: [Gemini structured output](https://ai.google.dev/gemini-api/docs/structured-output), [Gemini PDF processing](https://ai.google.dev/gemini-api/docs/document-processing), [Greenhouse Job Board API](https://docs.greenhouse.io/job-board.html), [Lever Postings API](https://github.com/lever/postings-api).
