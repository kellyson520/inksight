# Location Nominatim Outbound Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Route Nominatim location search through the shared `OutboundHttp` policy while preserving its async API, query parameters, User-Agent, list response shape, and retry behavior.

**Architecture:** Keep `_fetch_nominatim()` as the async tenacity-decorated boundary. Build the encoded query URL, execute synchronous `outbound_http.get_json()` in `asyncio.to_thread()`, pass the existing Nominatim User-Agent and a bounded no-redirect `RequestPolicy`, then normalize non-list JSON to an empty list as before.

**Tech Stack:** Python 3.10+, asyncio, httpx, pytest, OutboundHttp.

**Spec:** Existing `backend/core/location_service.py` behavior and the round-29 migration objective.

## Global Constraints

- Do not change the public `_fetch_nominatim()` signature.
- Do not introduce a second HTTP client or weaken OutboundHttp URL/DNS/response safety.
- Preserve `_NOMINATIM_USER_AGENT` on the request.
- Preserve `countrycodes`, locale, limit, format, and addressdetails query semantics.
- Preserve list normalization and tenacity retry behavior.
- Verify locally and in Docker before commit.

---

### Task 1: Add the failing delegation regression test

**Files:**
- Create: `backend/tests/test_location_nominatim_outbound.py`

**Interfaces:**
- Consumes: `core.location_service._fetch_nominatim`
- Produces: A regression test proving the shared outbound adapter receives the encoded Nominatim request and User-Agent.

- [ ] **Step 1: Write the failing test**

```python
@pytest.mark.asyncio
async def test_nominatim_uses_shared_outbound_http():
    response = type("Response", (), {"json": lambda self: [{"display_name": "杭州"}]})()
    with patch("core.location_service.outbound_http.get_json", return_value=response) as get_json:
        result = await _fetch_nominatim("杭州", count=3, country_codes="cn", locale="zh")
    assert result == [{"display_name": "杭州"}]
    get_json.assert_called_once()
    url = get_json.call_args.args[0]
    assert "q=%E6%9D%AD%E5%B7%9E" in url
    assert "limit=3" in url
    assert "countrycodes=cn" in url
    assert get_json.call_args.kwargs["headers"]["User-Agent"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=backend pytest backend/tests/test_location_nominatim_outbound.py -q`
Expected: FAIL because `_fetch_nominatim()` still calls `httpx.AsyncClient` and no shared adapter call occurs.

### Task 2: Implement the smallest shared-outbound migration

**Files:**
- Modify: `backend/core/location_service.py:353-379`

**Interfaces:**
- Consumes: `outbound_http.get_json(url, headers=..., policy=...) -> HttpResponse`
- Produces: `_fetch_nominatim(...) -> list[dict]` with unchanged signature and normalization.

- [ ] **Step 1: Build the encoded URL and call OutboundHttp**

Use `urlencode(params)` and execute:

```python
response = await asyncio.to_thread(
    outbound_http.get_json,
    f"{_NOMINATIM_SEARCH_URL}?{urlencode(params)}",
    headers={"User-Agent": _NOMINATIM_USER_AGENT},
    policy=RequestPolicy(timeout=5.0, max_attempts=1, follow_redirects=False),
)
data = response.json()
return data if isinstance(data, list) else []
```

- [ ] **Step 2: Run the focused test**

Run: `PYTHONPATH=backend pytest backend/tests/test_location_nominatim_outbound.py -q`
Expected: PASS.

### Task 3: Run regression and inspect the diff

**Files:**
- Modify only files listed above.

- [ ] **Step 1: Run local regression**

Run: `PYTHONPATH=backend pytest backend/tests/test_location_nominatim_outbound.py backend/tests/test_location_outbound_migration.py backend/tests/test_locations_api.py backend/tests/test_unit_context.py backend/tests/test_outbound_http.py backend/tests/test_outbound_dns_safety.py backend/tests/test_outbound_redirect_safety.py -q`
Expected: All tests pass with exit code 0.

- [ ] **Step 2: Run Docker regression**

Run the same test list through `docker exec -w /app/backend inksight pytest ... -q`.
Expected: All tests pass with exit code 0.

- [ ] **Step 3: Run static checks**

Run: `python3 -m py_compile backend/core/location_service.py && git diff --check && git status --short`
Expected: Compile and diff checks pass; only intended files are modified.

- [ ] **Step 4: Commit**

```bash
git add backend/core/location_service.py backend/tests/test_location_nominatim_outbound.py docs/plans/2026-03-10-location-nominatim-outbound.md
git commit -m "fix(location): route nominatim through outbound policy"
git push origin main
```
