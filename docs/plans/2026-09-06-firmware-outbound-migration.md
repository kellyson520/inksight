# Firmware Outbound Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Route firmware release and firmware URL checks through the shared OutboundHttp policy.

**Architecture:** Keep firmware cache and response normalization in `core/firmware_service.py`; delegate network I/O to `core/outbound_http.py`. Add only the missing async HEAD primitive needed for reachability validation.

**Tech Stack:** Python 3.10+, httpx, pytest, FastAPI.

**Spec:** Existing firmware service behavior and `backend/core/outbound_http.py` request policy.

## Global Constraints

- Preserve GitHub request headers, cache semantics, and firmware response schema.
- Preserve HEAD then ranged GET fallback behavior for firmware URL validation.
- Do not weaken URL safety or redirect policy.
- Add regression tests before production changes.

---

### Task 1: Add failing delegation tests

**Files:**
- Modify: `backend/tests/test_market_and_firmware_services.py`
- Inspect: `backend/core/firmware_service.py`

**Interfaces:**
- `load_firmware_releases(force_refresh=True)` delegates JSON retrieval to shared outbound service.
- `validate_firmware_url(url)` delegates HEAD/range GET to shared outbound service.

- [ ] Write tests patching the shared outbound methods and asserting calls/headers.
- [ ] Run the focused tests and observe failure because firmware service constructs `httpx.AsyncClient` directly.

### Task 2: Implement minimal shared outbound HEAD support and firmware migration

**Files:**
- Modify: `backend/core/outbound_http.py`
- Modify: `backend/core/firmware_service.py`

**Interfaces:**
- Add `async def head(url, *, headers=None, timeout=None, follow_redirects=False) -> httpx.Response` to the shared outbound adapter.
- Route firmware release JSON through `outbound_http.get_json(...)`.
- Route firmware URL HEAD and ranged GET through shared outbound methods while preserving fallback behavior.

- [ ] Run focused tests and verify they pass.
- [ ] Run firmware regression suite.

### Task 3: Verify and commit

**Files:**
- No additional source files.

- [ ] Run local backend suite.
- [ ] Run Docker backend suite.
- [ ] Run `git diff --check` and clean runtime artifacts.
- [ ] Commit and push with message `feat(http): migrate firmware service to outbound policy`.
