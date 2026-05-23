# SPEC-003: PDF Full-Text Acquisition Strategy

**Status:** Draft
**Date:** 2026-05-23
**Branch:** `analysis/bibliography-pdf-collection`
**Scope:** Stage 3 (Source Verification) + Stage 4 (Deep Reading)

## Problem

The skill currently cannot obtain full-text PDFs for papers behind paywalls
(ACM, IEEE, Springer, Elsevier) or for arXiv papers that lack HTML rendering.
Sources behind paywalls are marked `PARTIAL (paywall)` and only their abstracts
contribute to synthesis — a severe selection bias in non-CS domains.

The skill also has no fallback when `arxiv.org/html/{id}` returns 404 (older
papers, exotic formats). The PDF binary exists at `arxiv.org/pdf/{id}.pdf` but
the pipeline never fetches it.

## Strategy: Two-Phase Fallback Chain

```
DOI available?
  ├─ YES → Phase 1: Unpaywall API (legal, fast, no parsing needed)
  │         ├─ best_oa_location.url_for_pdf exists? → download PDF → read_file
  │         └─ null/empty → Phase 2
  └─ NO  → Phase 2: Sci-Hub (shadow library, requires HTML parsing)

Phase 2: Sci-Hub
  ├─ Resolve DOI via https://sci-hub.{domain}/{DOI}
  ├─ Parse HTML to extract PDF URL
  ├─ Download PDF → read_file
  └─ Fallback: mark as UNVERIFIABLE
```

**Design principle:** Unpaywall first — it's legal, fast, and provides direct
PDF URLs with no HTML scraping. Sci-Hub is the fallback of last resort, gated
behind an explicit opt-in config flag (off by default).

---

## Phase 1: Unpaywall API

### Endpoint

```
GET https://api.unpaywall.org/v2/{DOI}?email={USER_EMAIL}
```

- **Rate limit:** 100k calls/day (free tier, no key required)
- **Email:** Required as query parameter. The orchestrator reads it from
  `.deepseek/deepseek-research.toml` → `unpaywall_email`.
- **Response:** JSON object matching the Unpaywall v2 schema.

### Relevant Response Fields

| Field | Path | Description |
|-------|------|-------------|
| OA status | `is_oa` | `true` if any OA copy exists |
| OA status type | `oa_status` | `gold`, `hybrid`, `bronze`, `green`, or `closed` |
| Best location | `best_oa_location` | OA Location object with highest priority |
| PDF URL | `best_oa_location.url_for_pdf` | Direct URL to PDF (may be `null`) |
| Landing page | `best_oa_location.url_for_landing_page` | Fallback if no PDF URL |
| Host type | `best_oa_location.host_type` | `publisher` or `repository` |
| License | `best_oa_location.license` | e.g. `cc-by`, `cc-by-nc`, etc. |
| Version | `best_oa_location.version` | `publishedVersion`, `acceptedVersion`, `submittedVersion` |

### Example Response (trimmed)

```json
{
  "doi": "10.1038/nature12373",
  "is_oa": true,
  "oa_status": "green",
  "best_oa_location": {
    "url_for_pdf": "https://europepmc.org/articles/pmc3790963?pdf=render",
    "url_for_landing_page": "https://doi.org/10.1038/nature12373",
    "host_type": "repository",
    "license": "cc-by",
    "version": "publishedVersion",
    "is_best": true
  },
  "oa_locations": [...],
  "title": "High-resolution mapping of global surface water...",
  "published_date": "2016-12-07",
  "journal_name": "Nature"
}
```

### Integration Point: Stage 3 (Source Verification)

For each source with a DOI:

1. Call `fetch_url("https://api.unpaywall.org/v2/{doi}?email={email}")`.
2. If `is_oa: true` AND `best_oa_location.url_for_pdf` is non-null:
   - Record the PDF URL in `03-source-verification.md`.
   - Add a `pdf_url` field to the source table.
   - Downgrade RoB concern about accessibility from "paywall" to "resolved via OA".
3. If `is_oa: false` and config flag `allow_scihub: true`:
   - Proceed to Phase 2.
4. Otherwise: mark as `PARTIAL (paywall, no OA copy found)`.

### Config Additions

```toml
# .deepseek/deepseek-research.toml

# Email for Unpaywall API (required; Unpaywall TOS mandate it)
unpaywall_email = "researcher@example.com"

# Enable Sci-Hub fallback for paywalled papers without OA copies
# OFF by default — user must explicitly opt in
allow_scihub = false

# Sci-Hub base domain (auto-resolved if empty)
scihub_domain = ""
```

### Output Artifact Changes

`03-source-verification.md` gains columns:

```
| Source ID | Accessibility | OA Status | PDF URL | RoB |
|-----------|--------------|-----------|---------|-----|
| S15       | OA (green)   | repository | https://europepmc.org/... | Low |
| S16       | Sci-Hub      | —         | /tmp/dsr-pdfs/s16.pdf   | Low |
```

---

## Phase 2: Sci-Hub (Shadow Library)

### Precondition

Config flag `allow_scihub = true` MUST be set. If absent, the pipeline
stops at Phase 1 and marks the source as `PARTIAL`.

### Mechanism

Sci-Hub serves papers by DOI via a simple URL pattern:

```
https://sci-hub.{domain}/{DOI}
```

Where `{domain}` is one of the currently active mirrors. The response is an
HTML page containing either:
- An `<iframe>` or `<embed>` pointing to the PDF (most common).
- A direct redirect to the PDF.
- A captcha or block page (rare; retry with different domain).

The PDF binary is downloaded and saved to `{session_dir}/pdfs/{source_id}.pdf`,
then read via `read_file` (which uses the built-in pure-Rust PDF extractor).

### Domain Resolution

Sci-Hub domains change frequently. The pipeline should:

1. Use the configured `scihub_domain` if set.
2. Otherwise, attempt known-good domains in order:
   - `sci-hub.st`
   - `sci-hub.se`
   - `sci-hub.ru`
3. If all fail, consult a mirror list endpoint (e.g. `sci-hub.shop` or
   `sci-hub.pub` which publish current domains) via `fetch_url` and retry.

### Download Protocol (conceptual — implemented in helpers.py)

```python
# Pseudocode for the Sci-Hub resolution step
# Runs inside code_execution, not exec_shell

import re
from urllib.parse import urljoin

def resolve_scihub_pdf(doi: str, domain: str) -> str | None:
    """
    Returns a direct PDF URL from Sci-Hub, or None.
    
    1. Fetch https://{domain}/{doi}
    2. Search HTML for:
       - <iframe src="...pdf...">
       - <embed src="...pdf...">
       - <a href="...pdf..."> with download/content-type hints
    3. Return the absolute PDF URL.
    """
    ...

def download_pdf(url: str, output_path: str) -> bool:
    """
    Download PDF binary via Python requests.
    Returns True on success.
    """
    ...
```

### Integration Point: Stage 3 (Source Verification)

The orchestrator calls:

```
code_execution(code='''
import sys; sys.path.insert(0, "{SKILL_DIR}/scripts")
from helpers import resolve_fulltext

result = resolve_fulltext(
    doi="{doi}",
    output_dir="{session_dir}/pdfs/",
    source_id="{source_id}",
    unpaywall_email="{unpaywall_email}",
    allow_scihub={allow_scihub},
    scihub_domain="{scihub_domain}"
)
print(result)  # JSON: {"status": "oa"/"scihub"/"unavailable", "pdf_path": "...", "pdf_url": "..."}
''')
```

### Fallback: arXiv PDF

For arXiv sources where the HTML rendering is unavailable (404 on
`arxiv.org/html/{id}`), add a direct arXiv PDF fallback that does NOT require
DOI resolution:

```
fetch_url("https://arxiv.org/pdf/{arxiv_id}.pdf", format="raw")
→ save to {session_dir}/pdfs/{source_id}.pdf
→ read_file("{session_dir}/pdfs/{source_id}.pdf")
```

This is a pure improvement with zero external dependencies — `read_file`
already extracts PDF text via the built-in Rust extractor.

### Edge Cases

| Case | Handling |
|------|----------|
| Sci-Hub returns captcha | Retry with next domain; if all fail, mark UNVERIFIABLE |
| PDF is scanned (image-only) | `read_file` OCR extraction may return empty/garbled; mark `FAILED — scanned PDF` in deep read |
| PDF > 50MB | Skip; mark as `TOO_LARGE` |
| DOI not found on Sci-Hub | Sci-Hub returns 404 or error page; mark UNVERIFIABLE |
| Unpaywall returns `is_oa: true` but PDF URL 404s | Fall through to Sci-Hub (if enabled) |
| Multiple OA locations available | Prefer `host_type=repository` over `publisher` (fewer redirects); prefer `version=publishedVersion` |

---

## Modified Pipeline Flow

### Stage 2 (Source Discovery) — Unchanged

Sub-agents continue to discover sources normally. No PDF fetching here.

### Stage 3 (Source Verification) — Extended

For each source:

1. **Accessibility check (existing):** `fetch_url` on the source URL.
2. **NEW: DOI extraction.** If the source metadata includes a DOI, extract it.
   - arXiv papers: DOI is usually in the abstract page or can be inferred
     from the arxiv ID via Crossref API.
3. **NEW: Unpaywall lookup.** If DOI exists, call Unpaywall API.
4. **NEW: OA PDF download.** If `url_for_pdf` exists, download PDF to
   `{session_dir}/pdfs/{source_id}.pdf`.
5. **NEW: Sci-Hub fallback.** If `allow_scihub=true` and no OA copy, attempt
   Sci-Hub resolution.
6. **NEW: arXiv PDF fallback.** If the source is an arXiv paper and the HTML
   page returns 404, fetch `arxiv.org/pdf/{id}.pdf` directly.
7. Record accessibility, OA status, and PDF path in the verification table.

### Stage 4 (Deep Reading) — Modified

For papers (T1-T4):

- **Existing:** `rlm_open(file_path=...)` or `rlm_open(url=...)`
- **NEW:** When `pdf_path` exists from Stage 3, prefer
  `rlm_open(file_path="{pdf_path}")` — local files are faster and don't depend
  on network.
- **NEW:** When `pdf_path` does NOT exist but a PDF URL is known, use
  `rlm_open(url="{pdf_url}")`.
- **Existing (unchanged):** When only HTML URL is available, use that.

### Stage 5 (Synthesis) — Light Change

- Methodological Note gains a line:
  > "X of Y sources were accessed via Open Access repositories (Unpaywall);
  > Z sources required Sci-Hub access. See `03-source-verification.md` for
  > per-source accessibility details."

---

## Implementation Plan

### Files to Create/Modify

| File | Action | Purpose |
|------|--------|---------|
| `scripts/fulltext.py` | **Create** | `resolve_fulltext()` — Unpaywall + Sci-Hub + arXiv PDF orchestration |
| `scripts/helpers.py` | **Modify** | Re-export or wrap `resolve_fulltext` for `code_execution` calls |
| `SKILL.md` | **Modify** | Stage 3 §: add DOI extraction + Unpaywall + Sci-Hub steps |
| `references/pipeline-detail.md` | **Modify** | Stage 3 §: detailed Unpaywall/Sci-Hub protocol |
| `templates/source-verification.md` | **Modify** | Add `pdf_url` and `oa_status` columns to verification table |
| `templates/report.md` | **Modify** | Methodological Note: add OA/Sci-Hub accessibility stats |
| `references/error-recovery.md` | **Modify** | Add Sci-Hub captcha/domain failure recovery procedures |
| `AGENTS.md` | **Modify** | Record `allow_scihub` gate in development constraints |

### New Config Variables

```toml
# .deepseek/deepseek-research.toml additions

# Unpaywall API email (required for OA lookup)
unpaywall_email = ""

# Allow Sci-Hub fallback (default: false)
allow_scihub = false

# Sci-Hub domain override (auto-detected if empty)
scihub_domain = ""
```

### Dependency Notes

- **No new Python packages required.** Unpaywall is a plain REST API callable
  via `fetch_url`. Sci-Hub PDF download uses `fetch_url` + regex/HTML parsing
  that can run inside `code_execution` with stdlib only (`urllib`, `re`).
- **`read_file` already extracts PDF text** via built-in Rust extractor — no
  new PDF parsing dependency.
- **Rate limits:** Unpaywall free tier = 100k/day. One call per DOI. For a
  typical session with 30 sources (of which ~15 have DOIs), this is negligible.
- **Sci-Hub reliability:** Expect ~15% failure rate (captcha, domain blocks).
  The pipeline already handles UNVERIFIABLE sources gracefully.

---

## Ethical & Legal Notes

### Unpaywall
- Legal, non-controversial. Uses publicly available OA metadata.
- Requires email per TOS. No API key needed.

### Sci-Hub
- Operates in a legal gray area in most jurisdictions. The `allow_scihub`
  flag is **off by default** and must be explicitly enabled by the user.
- The skill does NOT bundle Sci-Hub domains, scripts, or credentials —
  domain resolution happens at runtime.
- The `allow_scihub` flag is documented as "use at your own risk" in
  config comments.

### arXiv PDF
- Completely legal. arXiv TOS permit bulk downloading for research.
- Rate limit: arXiv asks for one request per 5 seconds for bulk access.
  Single-paper fetches are unrestricted.

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Unpaywall API downtime | Low | Medium | Fall through to Sci-Hub (if enabled) or mark UNVERIFIABLE |
| Sci-Hub domain blocked | High | Medium | Multi-domain fallback; mirror list refresh |
| Sci-Hub captcha | Medium | Low | Mark single source UNVERIFIABLE; continue pipeline |
| Large PDF OOM during extraction | Low | High | Size check before download (>50MB skip) |
| Scanned PDF unreadable | Medium | Low | `read_file` returns empty → `FAILED — scanned PDF` |
| User sets `allow_scihub` unaware of legal risk | High | Medium | Config comment warns; methodological note documents usage |
