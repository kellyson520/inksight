# Recommendation Modules Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Qidian novel, Pixiv daily image, iwara video, and Pornhub video recommendation modes with two layouts each, global proxy configuration, and categorized paginated device configuration.

**Architecture:** Providers normalize source data into one recommendation schema. JSON modes select `ranking` or `cover_card` through `mode_overrides`. All external requests use the existing outbound HTTP layer with a validated user proxy URL. The configuration page paginates catalog categories without changing the submitted modes array.

**Tech Stack:** Python 3.10, FastAPI, httpx, Pillow, pytest, Next.js/React/TypeScript, existing JSON mode renderer.

**Spec:** `docs/design/2026-09-09-recommendation-modules.md`

## Global Constraints

- Do not delegate to subagents.
- Preserve existing mode IDs, config payload compatibility, and fallback behavior.
- Use `backend/core/outbound_http.py` for new external HTTP requests.
- Never log complete proxy URLs or credentials.
- Every bug/feature change follows RED → GREEN → REFACTOR.
- Public-source failures must render fallback content; never bypass authentication, CAPTCHA, or access controls.

---

### Task 1: Establish shared recommendation schema and proxy-aware outbound requests

**Files:**
- Create: `backend/core/recommendation_provider.py`
- Modify: `backend/core/outbound_http.py`
- Test: `backend/tests/test_recommendation_provider.py`
- Test: `backend/tests/test_outbound_http_proxy.py`

**Interfaces:**
- Produces `RecommendationItem`, `normalize_recommendation_item`, `resolve_proxy_url`.
- `outbound_http.get_json/get_text` accept optional `proxy_url` without changing existing callers.

- [ ] Step 1: Write failing tests for normalization and proxy propagation.
- [ ] Step 2: Run `PYTHONPATH=backend pytest backend/tests/test_recommendation_provider.py backend/tests/test_outbound_http_proxy.py -q` and confirm failure.
- [ ] Step 3: Implement the dataclass, URL validation, URL redaction, and httpx client proxy wiring.
- [ ] Step 4: Re-run the two test files and confirm pass.
- [ ] Step 5: Run existing outbound HTTP tests.
- [ ] Step 6: Commit `feat: add recommendation schema and proxy-aware outbound requests`.

### Task 2: Persist and expose global proxy preference

**Files:**
- Modify: `backend/core/config_store.py`
- Modify: relevant user preference API route under `backend/api/`
- Modify: `webapp/app/profile/page.tsx` or the existing profile settings component discovered during implementation
- Test: `backend/tests/test_global_proxy_preference.py`

**Interfaces:**
- Preference key: `global_proxy_url`.
- API read/write preserves existing preference fields and redacts proxy URL in logs/errors.

- [ ] Step 1: Write failing persistence/API tests for save, read, clear, and invalid scheme rejection.
- [ ] Step 2: Run the focused test and confirm failure.
- [ ] Step 3: Add the preference field and validation to the existing store/API.
- [ ] Step 4: Add the profile form input with supported scheme hint.
- [ ] Step 5: Run backend tests and web typecheck/build.
- [ ] Step 6: Commit `feat: add global external proxy preference`.

### Task 3: Add provider implementations with deterministic parsers

**Files:**
- Create: `backend/core/providers/qidian_novel_provider.py`
- Create: `backend/core/providers/pixiv_daily_provider.py`
- Create: `backend/core/providers/iwara_video_provider.py`
- Create: `backend/core/providers/porn_video_provider.py`
- Modify: `backend/core/providers/__init__.py`
- Test: `backend/tests/test_recommendation_providers.py`

**Interfaces:**
- Each registered provider returns `dict[str, Any]` containing `items`, `title`, `source`, and `layout_style`.
- Each provider supports mocked payload parsing and fallback without network access.

- [ ] Step 1: Write parser tests with representative JSON/HTML fixtures for all four sources.
- [ ] Step 2: Run focused tests and confirm failure.
- [ ] Step 3: Implement source parsers using `outbound_http` and `proxy_url` from config.
- [ ] Step 4: Add source-specific fallback items and safe title/URL cleanup.
- [ ] Step 5: Run focused tests and existing provider tests.
- [ ] Step 6: Commit `feat: add four recommendation providers`.

### Task 4: Add two layouts and four built-in JSON modes

**Files:**
- Create: `backend/core/modes/builtin/qidian_novel.json`
- Create: `backend/core/modes/builtin/pixiv_daily.json`
- Create: `backend/core/modes/builtin/iwara_video.json`
- Create: `backend/core/modes/builtin/porn_video.json`
- Create: matching files under `backend/core/modes/builtin/en/`
- Modify: `backend/core/mode_catalog.py`
- Modify: renderer block or shared layout helper if existing JSON blocks cannot express cover-card rendering
- Test: `backend/tests/test_recommendation_modes.py`

**Interfaces:**
- Mode IDs: `QIDIAN_NOVEL`, `PIXIV_DAILY`, `IWARA_VIDEO`, `PORN_VIDEO`.
- Setting key: `layout_style`, values `ranking` and `cover_card`.
- All modes expose a fallback and render at `400x300` and `296x128`.

- [ ] Step 1: Write failing catalog/layout/render tests.
- [ ] Step 2: Run focused tests and confirm failure.
- [ ] Step 3: Add JSON modes and catalog entries.
- [ ] Step 4: Implement the smallest shared card/list rendering needed for both layouts.
- [ ] Step 5: Run focused mode tests and render previews.
- [ ] Step 6: Commit `feat: add recommendation modes and layouts`.

### Task 5: Wire mode overrides, proxy preference, and configuration pagination

**Files:**
- Modify: `backend/core/json_content.py` or provider dispatch path
- Modify: `webapp/app/config/page.tsx`
- Modify: `webapp/components/config/mode-selector.tsx` and related config components
- Test: `backend/tests/test_recommendation_config_integration.py`
- Test: `webapp` component/unit test location used by the project, or TypeScript compile assertions if no UI test harness exists

**Interfaces:**
- `mode_overrides[MODE_ID].layout_style` is passed to provider/layout.
- Catalog category values: `core`, `news`, `media`, `tools`, `custom`.
- Pagination state does not alter selected mode IDs.

- [ ] Step 1: Write failing integration/UI tests for layout override propagation and cross-page mode selection.
- [ ] Step 2: Run tests and confirm failure.
- [ ] Step 3: Wire proxy and layout override into content generation.
- [ ] Step 4: Add categorized tabs/pages with stable selected-mode state and page controls.
- [ ] Step 5: Run backend integration tests and `npm run build` in `webapp`.
- [ ] Step 6: Commit `feat: paginate categorized mode configuration`.

### Task 6: End-to-end verification and production rollout

**Files:**
- Modify only files required by verification findings.
- Test: existing focused suites plus selected full backend suite.

- [ ] Step 1: Run all new focused backend tests.
- [ ] Step 2: Run existing mode/provider/outbound/config regression tests.
- [ ] Step 3: Run `npm run build` and any configured lint/typecheck command.
- [ ] Step 4: Restart the managed InkSight runtime, clear preview cache, and render all four modes in both layouts.
- [ ] Step 5: Verify proxy setting read/write through the real API without printing secrets.
- [ ] Step 6: Review `git diff`, `git diff --check`, and runtime-generated files.
- [ ] Step 7: Commit final fixes and update the goal only after all acceptance criteria have fresh evidence.
