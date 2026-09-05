# Media Fetch Infrastructure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将超时、重试、候选链接、Referer、内存/磁盘缓存和失败冷却统一下沉为 `MediaFetcher` 基础设施，并迁移图片渲染链路使用它。

**Architecture:** `core/media_fetcher.py` 提供同步 `MediaFetcher.fetch()` 与结构化结果。图片组件仅负责布局和调用服务；上游服务通过 URL 候选列表表达备用源。网络策略、缓存与错误分类集中在单一模块。

**Tech Stack:** Python 3.10+, httpx, Pillow, pytest, FastAPI/Uvicorn Docker 热挂载。

**Spec:** `docs/design/2026-09-05-media-fetch-infrastructure.md`

## Global Constraints

- 网络请求必须使用连接、读取、写入、连接池分阶段超时。
- 只对传输异常和 408、425、429、5xx 有限重试；404、410、418 等失败转入候选切换。
- 缓存写入必须原子化；运行时二进制缓存不得提交到 Git。
- `render_image` 不得直接创建 `httpx.Client`。
- TDD：每项实现先写失败测试并运行确认失败，再写最小实现。
- 微信读书与豆瓣电影图片渲染必须保持现有 1-bit/4-color 调色板兼容。

---

### Task 1: MediaFetcher contract and failure policy

**Files:**
- Create: `backend/core/media_fetcher.py`
- Create: `backend/tests/test_media_fetcher.py`

**Interfaces:**
- Produces `MediaFetchResult(data: bytes, url: str, cache_hit: bool)`.
- Produces `MediaFetcher.fetch(urls: str | Sequence[str], *, referer: str | None = None) -> MediaFetchResult`.
- Accepts constructor options `cache_dir`, `client_factory`, `max_attempts`, `backoff_base`, `failure_cooldown` for deterministic tests.

- [ ] **Step 1: Write failing tests**

```python
from unittest.mock import Mock
import httpx
import pytest
from core.media_fetcher import MediaFetcher


def test_fetch_retries_transient_timeout_then_succeeds(tmp_path):
    responses = [httpx.ReadTimeout("slow"), httpx.Response(503), httpx.Response(200, content=b"ok")]
    client = Mock()
    client.get.side_effect = responses
    fetcher = MediaFetcher(cache_dir=tmp_path, client_factory=lambda **_: client, backoff_base=0)

    result = fetcher.fetch("https://cdn.example.test/a.jpg")

    assert result.data == b"ok"
    assert result.cache_hit is False
    assert client.get.call_count == 3


def test_fetch_switches_permanently_failed_url_to_candidate(tmp_path):
    client = Mock()
    client.get.side_effect = [httpx.Response(404), httpx.Response(200, content=b"fallback")]
    fetcher = MediaFetcher(cache_dir=tmp_path, client_factory=lambda **_: client, backoff_base=0)

    result = fetcher.fetch(["https://bad.example.test/a.jpg", "https://good.example.test/a.jpg"])

    assert result.url == "https://good.example.test/a.jpg"
    assert result.data == b"fallback"
    assert client.get.call_count == 2


def test_fetch_uses_disk_cache_without_network(tmp_path):
    client = Mock()
    client.get.return_value = httpx.Response(200, content=b"cached")
    fetcher = MediaFetcher(cache_dir=tmp_path, client_factory=lambda **_: client, backoff_base=0)
    first = fetcher.fetch("https://cdn.example.test/a.jpg")
    client.get.reset_mock()

    second = fetcher.fetch("https://cdn.example.test/a.jpg")

    assert first.data == second.data == b"cached"
    assert second.cache_hit is True
    client.get.assert_not_called()


def test_fetch_sends_domain_referer(tmp_path):
    client = Mock()
    client.get.return_value = httpx.Response(200, content=b"ok")
    fetcher = MediaFetcher(cache_dir=tmp_path, client_factory=lambda **_: client, backoff_base=0)

    fetcher.fetch("https://img.example.test/a.jpg")

    headers = client.get.call_args.kwargs["headers"]
    assert headers["Referer"] == "https://img.example.test/"
    assert "User-Agent" in headers
```

- [ ] **Step 2: Run tests to verify failure**

Run: `PYTHONPATH=backend pytest backend/tests/test_media_fetcher.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'core.media_fetcher'`.

- [ ] **Step 3: Implement minimal infrastructure**

Implement `MediaFetchResult`, URL normalization, status classification, bounded retry loop, exponential backoff with injectable zero base, SHA256 cache key, disk cache read/write, atomic temporary file replacement, default domain Referer, and one shared module-level `media_fetcher`. Reject empty URL lists and raise a final `MediaFetchError` containing attempted URLs/statuses.

- [ ] **Step 4: Run tests to verify pass**

Run: `PYTHONPATH=backend pytest backend/tests/test_media_fetcher.py -q`
Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/core/media_fetcher.py backend/tests/test_media_fetcher.py
git commit -m "feat(infra): add resilient shared media fetcher"
```

---

### Task 2: Migrate image rendering to MediaFetcher

**Files:**
- Modify: `backend/core/blocks/components.py:7-31, 361-459`
- Modify: `backend/tests/test_media_fetcher.py`

**Interfaces:**
- Consumes `media_fetcher.fetch()` from Task 1.
- `render_image(ctx, block)` retains its existing public behavior and uses `_paste_converted_image()` for both `P` and `1` canvases.

- [ ] **Step 1: Write failing regression test**

Add a test that monkeypatches `core.blocks.components.media_fetcher.fetch` to return `MediaFetchResult(data=<valid image bytes>, url=..., cache_hit=False)`, renders an image block into a `P` canvas, and asserts the downloaded image is visible in the target crop. Add a source inspection assertion that `components.render_image` no longer constructs an `httpx.Client`.

- [ ] **Step 2: Run test to verify failure**

Run: `PYTHONPATH=backend pytest backend/tests/test_media_fetcher.py::test_render_image_uses_shared_fetcher -q`
Expected: FAIL because `components` has no shared fetcher call.

- [ ] **Step 3: Implement migration**

Remove `_fetch_image_bytes`, `_IMAGE_MEMORY_CACHE`, and direct HTTP retry code from `components.py`. Import the shared fetcher and replace remote fetch with `result = media_fetcher.fetch(image_url)`, then decode `result.data`, convert, and call `_paste_converted_image`. Preserve local asset and upload handling.

- [ ] **Step 4: Run tests to verify pass**

Run: `PYTHONPATH=backend pytest backend/tests/test_media_fetcher.py backend/tests/test_wechat_read_mode.py -q`
Expected: all tests PASS and no direct HTTP client remains in `render_image`.

- [ ] **Step 5: Commit**

```bash
git add backend/core/blocks/components.py backend/tests/test_media_fetcher.py
 git commit -m "refactor(renderer): route remote images through media infrastructure"
```

---

### Task 3: Add reusable candidate URL support to upstream book data

**Files:**
- Modify: `backend/core/wechat_read_service.py`
- Modify: `backend/core/douban_movie_service.py`
- Modify: `backend/tests/test_wechat_read_mode.py`
- Modify: `backend/tests/test_smzdm_and_douban_movie.py`

**Interfaces:**
- Each media record may expose `cover_urls: list[str]`; `cover_url` remains the selected primary URL for backward compatibility.
- `MediaFetcher.fetch()` receives `cover_urls` when available.

- [ ] **Step 1: Write failing tests**

Add assertions that each built-in book has a non-empty `cover_urls` list containing `cover_url`, and that a known unstable WeChat cover has at least one alternate source. Add a service test asserting formatted recommendation exposes the candidate list.

- [ ] **Step 2: Run tests to verify failure**

Run: `PYTHONPATH=backend pytest backend/tests/test_wechat_read_mode.py backend/tests/test_smzdm_and_douban_movie.py -q`
Expected: FAIL because records do not expose `cover_urls`.

- [ ] **Step 3: Implement candidate normalization**

Add a small helper in each service to populate `cover_urls` from the primary URL plus stable mirror URL where known, without duplicating fetch/retry code. Keep `cover_url` as first candidate and preserve existing response schema.

- [ ] **Step 4: Run tests to verify pass**

Run: `PYTHONPATH=backend pytest backend/tests/test_wechat_read_mode.py backend/tests/test_smzdm_and_douban_movie.py -q`
Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/core/wechat_read_service.py backend/core/douban_movie_service.py backend/tests/test_wechat_read_mode.py backend/tests/test_smzdm_and_douban_movie.py
git commit -m "feat(media): expose upstream cover candidates"
```

---

### Task 4: Wire candidate lists through JSON image rendering

**Files:**
- Modify: `backend/core/blocks/components.py`
- Modify: `backend/core/modes/builtin/wechat_read.json`
- Modify: `backend/core/modes/builtin/douban_movie.json`
- Modify: `backend/tests/test_wechat_read_mode.py`

**Interfaces:**
- Image block supports optional `urls_field`; when present it reads a sequence from content and passes it to `MediaFetcher.fetch()`.
- Existing `field` behavior remains valid for all modes.

- [ ] **Step 1: Write failing test**

Add a regression test with content `{"cover_url": "bad", "cover_urls": ["bad", "good"]}` and an image block `{ "field": "cover_url", "urls_field": "cover_urls" }`; assert the shared fetcher receives both candidates in order.

- [ ] **Step 2: Run test to verify failure**

Run: `PYTHONPATH=backend pytest backend/tests/test_media_fetcher.py::test_image_block_passes_url_candidates -q`
Expected: FAIL because `urls_field` is unsupported.

- [ ] **Step 3: Implement minimal wiring**

In `render_image`, resolve `urls_field` to a list, prepend the primary URL if absent, and pass the list to `media_fetcher.fetch()`. Add `urls_field: "cover_urls"` to both WeChat Read and Douban Movie image blocks.

- [ ] **Step 4: Run tests to verify pass**

Run: `PYTHONPATH=backend pytest backend/tests/test_media_fetcher.py backend/tests/test_wechat_read_mode.py backend/tests/test_smzdm_and_douban_movie.py -q`
Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/core/blocks/components.py backend/core/modes/builtin/wechat_read.json backend/core/modes/builtin/douban_movie.json backend/tests/test_wechat_read_mode.py
 git commit -m "feat(renderer): support candidate media URLs in image blocks"
```

---

### Task 5: Runtime configuration, ignore rules, and end-to-end verification

**Files:**
- Modify: `backend/.gitignore`
- Modify: `backend/core/media_fetcher.py`
- Modify: `docs/changelog.md`

**Interfaces:**
- Environment variables: `INKSIGHT_MEDIA_CACHE_DIR`, `INKSIGHT_MEDIA_MAX_ATTEMPTS`, `INKSIGHT_MEDIA_TIMEOUT_CONNECT`, `INKSIGHT_MEDIA_TIMEOUT_READ`, `INKSIGHT_MEDIA_FAILURE_COOLDOWN`.
- Defaults remain safe for Docker and local execution.

- [ ] **Step 1: Write failing tests**

Add tests for environment-based timeout parsing, corrupt/empty cache file eviction, and failure cooldown preventing immediate duplicate network attempts.

- [ ] **Step 2: Run tests to verify failure**

Run: `PYTHONPATH=backend pytest backend/tests/test_media_fetcher.py -q`
Expected: FAIL because configuration and cooldown behavior are absent.

- [ ] **Step 3: Implement configuration and cooldown**

Read environment defaults at module construction, validate positive numeric values, delete invalid cache files, and remember failed URL timestamps for the configured cooldown. A later call after cooldown retries normally.

- [ ] **Step 4: Run full backend verification**

Run: `docker exec -w /app/backend inksight pytest tests/test_media_fetcher.py tests/test_wechat_read_mode.py tests/test_smzdm_and_douban_movie.py tests/test_unit_pipeline.py`
Expected: all tests PASS.

- [ ] **Step 5: Verify actual preview endpoint**

Run: `curl -k -s -I "https://127.0.0.1:3001/api/preview?persona=WECHAT_READ&w=400&h=300" -H "Host: kellson.dpdns.org:3001"`
Expected: `HTTP/1.1 200 OK` and container logs contain no image download failure for WeChat Read.

- [ ] **Step 6: Update changelog and commit**

```bash
git add backend/.gitignore backend/core/media_fetcher.py docs/changelog.md
git commit -m "chore(media): configure and document resilient media infrastructure"
```

---

### Task 6: Final review, build, and push

**Files:**
- Review all changed files from Tasks 1-5.

- [ ] **Step 1: Run code review against the design**

Check that all network policy lives in `media_fetcher.py`, no duplicate retry/cache implementation remains, candidate lists preserve backward compatibility, and cache binaries are ignored.

- [ ] **Step 2: Run final verification**

```bash
PYTHONPATH=backend pytest backend/tests/test_media_fetcher.py backend/tests/test_wechat_read_mode.py backend/tests/test_smzdm_and_douban_movie.py backend/tests/test_unit_pipeline.py
npm --prefix webapp run build
docker exec -w /app/backend inksight pytest tests/test_media_fetcher.py tests/test_wechat_read_mode.py tests/test_smzdm_and_douban_movie.py tests/test_unit_pipeline.py
```

Expected: all tests PASS and web build exits 0.

- [ ] **Step 3: Check working tree and push**

```bash
git status
git push origin main
```

Expected: only intentional tracked source/docs changes; remote `main` updated.
