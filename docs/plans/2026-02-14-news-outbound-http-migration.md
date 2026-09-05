# News Outbound HTTP Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move Hacker News, Product Hunt, and Dev.to public-data fetches from direct async httpx clients to `outbound_http` executed through `asyncio.to_thread`, preserving output and fallback behavior while isolating per-story failures.

**Architecture:** Keep the three public async functions unchanged. Build each synchronous outbound request through the shared singleton and wrap it in `asyncio.to_thread`; parse JSON/XML in the async function, and use per-item exception handling plus `asyncio.gather(..., return_exceptions=True)` for HN stories.

**Tech Stack:** Python, asyncio, httpx response-compatible `HttpResponse`, pytest/pytest-asyncio.

**Spec:** Existing migration requirement and `backend/tests/test_source_http_migration.py`.

## Global Constraints

- Do not migrate or alter LLM `AsyncOpenAI` calls.
- `content.py` must not contain `httpx.AsyncClient` or `httpx.Client` construction.
- Preserve existing return fields and top-level fallback values (`[]`/`{}`).
- A failed individual HN story must not fail the entire HN result.
- No git commit.

---

### Task 1: Regression tests for HN parsing and failure isolation

**Files:**
- Modify: `backend/tests/test_source_http_migration.py`

- [ ] **Step 1: Write tests** using `monkeypatch` on `core.content.outbound_http.get_json`, asserting HN IDs are parsed into the existing `title`/`score`/`url` fields and one item exception leaves other stories returned.
- [ ] **Step 2: Run focused tests** with `pytest backend/tests/test_source_http_migration.py -q`; expected RED because the current implementation calls `AsyncClient` and does not use the patched outbound helper.

### Task 2: Migrate news fetchers to shared outbound HTTP

**Files:**
- Modify: `backend/core/content.py:567-714`

**Interfaces:**
- Consumes: `outbound_http.get_json` and `outbound_http.get_text`, each invoked via `asyncio.to_thread`.
- Produces: unchanged `fetch_hn_top_stories(limit) -> list[dict]`, `fetch_ph_top_product() -> dict`, and `fetch_devto_top(limit) -> list[dict]`.

- [ ] **Step 1: Import `asyncio` and outbound policy/singleton without touching LLM client code.**
- [ ] **Step 2: Replace HN list/item HTTP calls with `to_thread`; parse JSON and gather item tasks with `return_exceptions=True`, filtering failures.
- [ ] **Step 3: Replace Product Hunt RSS request with `to_thread(outbound_http.get_text)` and preserve XML parsing/fallback.
- [ ] **Step 4: Replace Dev.to JSON request with `to_thread(outbound_http.get_json)` and preserve field coercion/fallback.
- [ ] **Step 5: Run focused regression and migration tests; expected PASS.

### Task 3: Review and verification

**Files:**
- Review: `backend/core/content.py`, `backend/tests/test_source_http_migration.py`

- [ ] **Step 1: Run source scan and relevant backend tests, including outbound HTTP tests.**
- [ ] **Step 2: Inspect diff for accidental LLM changes, preserved fields/fallbacks, and no unrelated edits; report remaining risks without committing.**
