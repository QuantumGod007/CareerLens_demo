# Verification record

Verified locally on **23 October 2026**, using Python **3.13.2**. The application targets Python **3.12+**; Python 3.12 was not separately executed on the development machine.

## Automated checks

`python -m pytest -q`: **31 passed**.

The suite covers:

- Boundary-aware skill matching, aliases, explicit evidence categories, partial coverage and N/A.
- Equivalent scores after reordering and transparent recalculation of older results without modifying saved records.
- Gemini schema simplification, supported paraphrases, rejected metrics/tools/entities, protected qualifiers, omitted-fact recovery and verifier-outage fallback.
- Greenhouse and Lever response parsing, role/location filtering, query-based job identifiers, deduplication and visible source failures.
- PDF upload validation, text/contact/fact retention, multipage output and Greek character rendering with the bundled DejaVu font.
- Download responses, history persistence, separate assessment versions and immutable prior PDFs.
- Reusing saved requirements without another extraction or requirements-analysis request.
- Local simulated submissions, required answer validation and cross-origin write rejection.

Python compilation and JavaScript syntax checks passed. The test client emits an upstream Starlette deprecation warning about its httpx backend; the tests complete successfully.

## Live integration checks

The opt-in `scripts/live_smoke.py` completed with real Gemini calls and public career endpoints using a fictional candidate explicitly labelled **TEST ONLY**. Its data stays under the ignored `tmp/live-smoke/` directory.

- Native Gemini PDF extraction returned six skills and four facts from the fictional PDF.
- Stripe and Cloudflare Greenhouse boards and Spotify's Lever board returned published listings. The latest full check examined 1,264 listings and returned 10 ranked results; these counts change over time.
- Real job analysis and guarded tailoring completed for a published role.
- Both resume versions were checked against the same saved requirements, with explicit match evidence and no forced score increase.
- PDF download, local simulated submission and history persistence after reopening the app passed.
- A separate live Gemini fact-check accepted a structurally different but equivalent rewrite of a fictional project fact.

Live checks use API credits and depend on current Gemini quotas and source availability. They are separate from the offline regression suite. No employer application was submitted.

## Visual and interaction checks

The overview, resume summary/editor, upload validation, job results/details, history, role analysis, comparison, coverage, review form and actual PDF preview were inspected in the in-app browser at mobile/tablet widths. DOM inspection found no unexpected horizontal overflow or browser console errors.

The review form produced a clearly labelled local simulation receipt. PDF.js rendered the actual generated PDFs locally. Generated pages were independently rendered through Poppler and checked for margins, hierarchy, page breaks, footer alignment and retained content. Unicode checks caught and resolved missing glyphs in the original font; generated PDFs now use bundled DejaVu Sans.

Native desktop-browser control was unavailable, so a full-width desktop screenshot was not captured. Desktop responsive grids are implemented, but that specific visual check remains unverified.

## Practical limits

This is a single-user local MVP, without authentication or cloud deployment. Only configured Greenhouse/Lever company boards are searched, not the entire web. AI extraction and requirement classification can make mistakes and remain reviewable. Coverage is a local evidence check, not an official employer ATS score or a hiring prediction. Application submission is deliberately simulated.

API keys, candidate documents, databases, generated resumes, local assessment details and test artifacts are excluded from the source repository.
