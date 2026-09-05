# Platform Foundation Phase 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 建立统一出站 HTTP 与可观测性核心接口，并迁移媒体、RSS、新闻和热榜读取链路。

**Architecture:** `OutboundHttp` 负责所有公共网络访问策略；`Observability` 负责 request/dependency/render/cache 事件。业务模块只声明 URL、解析器和业务 fallback，不再复制 client、retry、timeout 和日志格式。

**Tech Stack:** Python 3.10+, FastAPI, httpx, asyncio, contextvars, pytest, Docker。

**Spec:** `docs/design/2026-09-05-platform-foundation-roadmap.md`

## Global Constraints

- 默认 `verify=True`，禁止新增或保留无理由的 `verify=False`。
- URL 默认阻断 loopback、私有、link-local、metadata 地址；不安全重定向不得自动跟随。
- 响应体限制为可配置上限；重试次数有上限，状态分类明确。
- 观测输出不得包含 API key、Cookie、token、完整 prompt、transcript 或完整用户内容。
- 观测失败不得影响业务。
- 每项变更先写失败测试、运行确认失败，再实现并验证。

---

### Task 1: Unified Observability facade

**Files:**
- Create: `backend/core/observability.py`
- Create: `backend/tests/test_observability.py`

**Interfaces:**
- `obs.emit(event: str, attributes: Mapping[str, Any]) -> None`
- `obs.start_request(request_id: str | None = None) -> RequestContext`
- `obs.observe(operation: str, **attributes) -> ContextManager`
- `obs.snapshot() -> dict[str, Any]`
- `get_request_id() -> str | None`

- [ ] **Step 1: Write failing tests**

```python
from core.observability import Observability, get_request_id


def test_emit_records_structured_event_and_snapshot():
    obs = Observability()
    obs.emit("dependency.completed", {"operation": "rss", "status": 200, "api_key": "secret"})
    event = obs.snapshot()["events"][-1]
    assert event["event"] == "dependency.completed"
    assert event["api_key"] == "[REDACTED]"


def test_request_context_propagates_and_restores_request_id():
    obs = Observability()
    assert get_request_id() is None
    with obs.start_request("req-123"):
        assert get_request_id() == "req-123"
    assert get_request_id() is None


def test_observation_failure_does_not_raise():
    obs = Observability(max_events=1)
    obs.emit("one", {})
    obs.emit("two", {"token": "secret"})
    assert len(obs.snapshot()["events"]) == 1
```

- [ ] **Step 2: Run tests to verify failure**

Run: `PYTHONPATH=backend pytest backend/tests/test_observability.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'core.observability'`.

- [ ] **Step 3: Implement minimal facade**

Use `contextvars.ContextVar` for request ID, monotonic duration in `observe`, bounded deque for events, JSON-safe low-cardinality attributes, redaction keys (`api_key`, `authorization`, `cookie`, `token`, `secret`, `prompt`, `transcript`), and standard logger output. Add `request.completed`, `dependency.completed`, `render.completed`, `cache.result`, and `exception` helper methods through `emit` only; do not persist to a new database in this phase.

- [ ] **Step 4: Run tests**

Run: `PYTHONPATH=backend pytest backend/tests/test_observability.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/core/observability.py backend/tests/test_observability.py
git commit -m "feat(core): add structured observability facade"
```

---

### Task 2: Unified OutboundHttp

**Files:**
- Create: `backend/core/outbound_http.py`
- Create: `backend/tests/test_outbound_http.py`
- Modify: `backend/core/media_fetcher.py`

**Interfaces:**
- `OutboundHttp.get_bytes(url, *, headers=None, policy=None) -> HttpResponse`
- `OutboundHttp.get_text(url, *, headers=None, policy=None) -> HttpResponse`
- `OutboundHttp.get_json(url, *, headers=None, policy=None) -> HttpResponse`
- `HttpResponse(status_code, headers, content, url, attempts, elapsed_ms)`
- `RequestPolicy(timeout, max_attempts, max_response_bytes, verify, follow_redirects, allowed_hosts)`

- [ ] **Step 1: Write failing tests**

```python
import httpx
from unittest.mock import Mock
from core.outbound_http import OutboundHttp, RequestPolicy


def test_outbound_retries_503_and_emits_dependency_event(tmp_path):
    client = Mock()
    client.get.side_effect = [httpx.Response(503), httpx.Response(200, content=b"ok")]
    http = OutboundHttp(client_factory=lambda **_: client, policy=RequestPolicy(max_attempts=2, backoff_base=0))
    response = http.get_bytes("https://example.test/a", policy=RequestPolicy(max_attempts=2, backoff_base=0))
    assert response.content == b"ok"
    assert response.attempts == 2


def test_outbound_rejects_private_url_before_network():
    client = Mock()
    http = OutboundHttp(client_factory=lambda **_: client)
    import pytest
    with pytest.raises(ValueError, match="private"):
        http.get_text("http://127.0.0.1/admin")
    client.get.assert_not_called()


def test_outbound_enforces_response_limit():
    client = Mock()
    client.get.return_value = httpx.Response(200, content=b"12345")
    http = OutboundHttp(client_factory=lambda **_: client)
    import pytest
    with pytest.raises(ValueError, match="too large"):
        http.get_bytes("https://example.test/a", policy=RequestPolicy(max_response_bytes=4))
```

- [ ] **Step 2: Run tests to verify failure**

Run: `PYTHONPATH=backend pytest backend/tests/test_outbound_http.py -q`
Expected: FAIL with missing module.

- [ ] **Step 3: Implement minimal HTTP kernel**

Centralize timeout, retryable status codes, bounded exponential backoff, URL validation, explicit TLS verification, no automatic redirects, response size checks, JSON/text decoding, client lifecycle, and `obs.emit("dependency.completed", ...)`. Make the module-level client share connections but close through application shutdown. Preserve `MediaFetcher` image validation and candidate behavior by delegating low-level HTTP requests to `OutboundHttp`.

- [ ] **Step 4: Run tests**

Run: `PYTHONPATH=backend pytest backend/tests/test_outbound_http.py backend/tests/test_media_fetcher.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/core/outbound_http.py backend/core/media_fetcher.py backend/tests/test_outbound_http.py
git commit -m "feat(core): centralize outbound HTTP policy"
```

---

### Task 3: Request middleware and health observability

**Files:**
- Modify: `backend/api/index.py`
- Create: `backend/tests/test_request_observability.py`
- Modify: `backend/Dockerfile`

**Interfaces:**
- Every HTTP response includes `X-Request-ID`.
- Every request emits `request.completed` with route, method, status, duration_ms.
- `/health` is a liveness endpoint; `/api/health` or existing readiness endpoint is tested explicitly.

- [ ] **Step 1: Write failing tests**

Add FastAPI TestClient tests asserting generated/preserved request IDs, response header, completed event on 200 and 500, and health path used by Docker.

- [ ] **Step 2: Run tests to verify failure**

Run: `PYTHONPATH=backend pytest backend/tests/test_request_observability.py -q`
Expected: FAIL because middleware and exact health contract are absent.

- [ ] **Step 3: Implement middleware**

Add a pure ASGI/HTTP middleware using `time.perf_counter`, `X-Request-ID` input validation and generated UUID fallback. Store request ID in `contextvars`; emit redacted low-cardinality event; attach header even on handled errors. Add a lightweight `/health` route if Docker expects it, without converting it into a dependency probe.

- [ ] **Step 4: Run tests**

Run: `PYTHONPATH=backend pytest backend/tests/test_request_observability.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/api/index.py backend/Dockerfile backend/tests/test_request_observability.py
git commit -m "feat(api): add request ids and completion telemetry"
```

---

### Task 4: Migrate RSS, news, and hotlist reads

**Files:**
- Modify: `backend/core/rss_parser.py`
- Modify: `backend/core/content.py`
- Modify: `backend/core/context.py`
- Modify: `backend/core/weather_service.py`
- Modify: `backend/core/hotlist_service.py`
- Create: `backend/tests/test_source_http_migration.py`

**Interfaces:**
- Existing public service functions remain compatible.
- All migrated dependencies call `outbound_http` and emit dependency events.
- Existing fallback values remain unchanged.

- [ ] **Step 1: Write failing source inspection tests**

```python
from pathlib import Path


def test_news_and_feed_services_do_not_construct_http_clients_directly():
    paths = ["backend/core/rss_parser.py", "backend/core/content.py", "backend/core/context.py", "backend/core/weather_service.py", "backend/core/hotlist_service.py"]
    for path in paths:
        source = Path(path).read_text()
        assert "httpx.AsyncClient" not in source
        assert "httpx.Client" not in source
```

- [ ] **Step 2: Run tests to verify failure**

Run: `PYTHONPATH=backend pytest backend/tests/test_source_http_migration.py -q`
Expected: FAIL listing existing direct clients.

- [ ] **Step 3: Migrate incrementally**

Replace direct clients with `outbound_http.get_json/get_text/get_bytes`; preserve parser-specific logic. For RSS add response size and safe XML parsing boundaries. For HN/Product Hunt/Dev.to use item-level exception isolation. For hotlist use a shared request-and-parse helper while preserving platform-specific parsers. Record `source`, `operation`, `status`, `attempts`, and `duration_ms`; do not log credentials or raw response bodies.

- [ ] **Step 4: Run source and behavior tests**

Run: `PYTHONPATH=backend pytest backend/tests/test_source_http_migration.py backend/tests/test_rss_parser.py backend/tests/test_hotlist_service.py backend/tests/test_briefing_mode.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/core/rss_parser.py backend/core/content.py backend/core/context.py backend/core/weather_service.py backend/core/hotlist_service.py backend/tests/test_source_http_migration.py
git commit -m "refactor(sources): migrate news rss weather and hotlist to outbound HTTP"
```

---

### Task 5: Render/cache event integration and final verification

**Files:**
- Modify: `backend/core/cache.py`
- Modify: `backend/core/pipeline.py`
- Modify: `backend/api/routes/render.py`
- Modify: `backend/api/routes/preview.py`
- Modify: `docs/changelog.md`

**Interfaces:**
- Cache emits `cache.result` with `result=memory|persistent|miss|expired|disabled|error`.
- Render emits `render.completed` with `mode`, `source`, `fallback`, `duration_ms`, `cache_result`.
- `obs.snapshot()` remains bounded and non-blocking.

- [ ] **Step 1: Write failing tests**

Add tests for cache hit/miss event classification and preview/render event emission with bounded attributes.

- [ ] **Step 2: Run tests to verify failure**

Run: `PYTHONPATH=backend pytest backend/tests/test_observability.py backend/tests/test_unit_cache.py -q`
Expected: FAIL because cache and render do not emit the event contract.

- [ ] **Step 3: Implement event hooks**

Wrap existing cache branches and render completion/error branches with `obs.emit`; do not alter cache contents or response semantics. Ensure event emission is exception-safe and avoids high-cardinality MAC labels.

- [ ] **Step 4: Run final verification**

```bash
PYTHONPATH=backend pytest backend/tests/test_observability.py backend/tests/test_outbound_http.py backend/tests/test_media_fetcher.py backend/tests/test_wechat_read_mode.py backend/tests/test_smzdm_and_douban_movie.py backend/tests/test_unit_pipeline.py
npm --prefix webapp run build
docker exec -w /app/backend inksight pytest tests/test_observability.py tests/test_outbound_http.py tests/test_media_fetcher.py tests/test_wechat_read_mode.py tests/test_smzdm_and_douban_movie.py tests/test_unit_pipeline.py
curl -k -s -I "https://127.0.0.1:3001/api/preview?persona=WECHAT_READ&w=400&h=300" -H "Host: kellson.dpdns.org:3001"
```

Expected: all tests pass, web build exits 0, preview returns HTTP 200, and logs contain dependency/request/render events without secrets.

- [ ] **Step 5: Commit and push**

```bash
git add backend/core/cache.py backend/core/pipeline.py backend/api/routes/render.py backend/api/routes/preview.py docs/changelog.md
git commit -m "feat(observability): instrument cache and render lifecycle"
git push origin main
```
