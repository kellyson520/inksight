# Context Weather Outbound HTTP Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Migrate direct network clients in `backend/core/context.py` and `backend/core/weather_service.py` to the shared synchronous `core.outbound_http.outbound_http`, preserving async public APIs and existing fallback behavior.

**Architecture:** Keep the existing async functions and retry/fallback boundaries. Replace each direct async client block with `await asyncio.to_thread(...)` invoking `outbound_http.get_json`, then consume the returned `HttpResponse.json()` value. Use request policies carrying the existing timeout and retry intent where practical; do not change `content.py` or `rss_parser.py`.

**Tech Stack:** Python, asyncio, httpx response/error types, pytest/pytest-asyncio, shared `OutboundHttp`.

**Spec:** User request in this session.

## Global Constraints

- Modify only the requested context/weather implementation and focused tests/plan files.
- Do not modify `backend/core/content.py` or `backend/core/rss_parser.py`.
- Preserve existing async public APIs and weather/holiday fallback return values.
- Adapt synchronous outbound calls with `asyncio.to_thread`.
- Do not commit git changes.

---

### Task 1: Add failing migration and fallback tests

**Files:**
- Modify: `backend/tests/test_source_http_migration.py`
- Modify: `backend/tests/test_unit_context.py` or create focused migration test module

**Interfaces:**
- Tests target `core.context._fetch_holiday_info`, `core.context._fetch_upcoming_holiday`, `core.weather_service._fetch_weather_data`, and weather fallback behavior.

- [ ] **Step 1: Write the failing tests**
  - Assert only `context.py` and `weather_service.py` contain neither `httpx.AsyncClient` nor `httpx.Client` construction.
  - Patch `core.weather_service.outbound_http.get_json` to return a response whose `.json()` raises `JSONDecodeError`, patch QWeather fallback to `None`, and assert `get_weather(...)` returns `{"temp": 0, "weather_code": -1, "weather_str": "--°C"}`.
  - Assert the synchronous outbound function is reached through the async wrapper and receives the expected URL/params.

- [ ] **Step 2: Run focused tests to verify RED**

Run from repository root:
`cd backend && pytest tests/test_source_http_migration.py tests/test_weather_outbound_migration.py -q`

Expected: failures because the source still constructs `httpx.AsyncClient` and the new outbound seam is not used.

### Task 2: Implement shared outbound migration

**Files:**
- Modify: `backend/core/context.py`
- Modify: `backend/core/weather_service.py`

**Interfaces:**
- Preserve all existing async function signatures and return shapes.
- Consume `outbound_http.get_json(url, headers=..., policy=...).json()` inside `asyncio.to_thread`.

- [ ] **Step 1: Replace context holiday HTTP blocks**
  - Import `asyncio`, `RequestPolicy`, and `outbound_http`.
  - Add a small synchronous-call lambda/helper per request and await it with `asyncio.to_thread`.
  - Preserve `raise_for_status`/JSON failure semantics through `get_json` and existing exception handling.

- [ ] **Step 2: Replace weather Open-Meteo and QWeather HTTP blocks**
  - Use `asyncio.to_thread` around `outbound_http.get_json`.
  - Preserve auth headers, URL/params, and all existing QWeather code validation and fallback paths.
  - Keep `httpx` only for exception classes if needed; remove direct client construction/import usage.

- [ ] **Step 3: Run focused tests to verify GREEN**

Run:
`cd backend && pytest tests/test_source_http_migration.py tests/test_weather_outbound_migration.py tests/test_unit_context.py -q`

Expected: all focused migration/context tests pass.

### Task 3: Review and regression verification

**Files:**
- Review only the migration diff; no additional source scope.

- [ ] **Step 1: Check diff and prohibited files**

Run:
`git diff -- backend/core/context.py backend/core/weather_service.py backend/tests/test_source_http_migration.py backend/tests/test_weather_outbound_migration.py`

Confirm `content.py` and `rss_parser.py` are unchanged.

- [ ] **Step 2: Run relevant backend tests**

Run:
`cd backend && pytest tests/test_source_http_migration.py tests/test_weather_outbound_migration.py tests/test_unit_context.py tests/test_outbound_http.py -q`

- [ ] **Step 3: Report exact changed files, red/green evidence, and test output; do not commit.**
