# Game Giveaway Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a 喜加一 game-giveaway mode using a game cover as the background, with source at top-left, deadline at top-right, and game-name badge at bottom-left.

**Architecture:** Add one registered computed provider and one pair of localized JSON mode definitions. The provider fetches public giveaway data through the existing outbound HTTP/media infrastructure when configured, merges safe fallback data when unavailable, and returns a cover URL plus normalized display fields. The existing image block handles cover rendering; the mode layout uses overlays/cards to keep labels readable over the cover.

**Tech Stack:** Python 3.10, FastAPI backend, async provider registry, existing outbound HTTP/media fetcher, JSON mode renderer, Pillow, pytest.

**Spec:** In-chat design for bounded feature; source/deadline/game title must be visible at 400x300 and narrow screens.

## Global Constraints

- Mode ID is `GAME_GIVEAWAY`.
- Source display is limited to `EPIC` or `STEAM` and may use text/letter marks, not external logo assets.
- Cover URL is public and optional; fallback must render without a network connection.
- Deadline display must be normalized to `截止 YYYY-MM-DD HH:MM` or `限时领取` when unavailable.
- Do not log API keys, private URLs, or full provider responses.
- Use existing `image` block and `image_url`/prefetch conventions; do not add a second image pipeline.
- Preserve all current mode IDs and existing tests.

---

### Task 1: Add failing provider and pipeline tests

**Files:**
- Modify: `backend/tests/test_creative_modes_pipeline.py`
- Create: `backend/tests/test_game_giveaway_mode.py`

**Interfaces:**
- Consumes: future `GAME_GIVEAWAY` JSON mode and `game_giveaway` provider.
- Produces: regression tests requiring `source_label`, `game_title`, `deadline_label`, `cover_url`, and successful 400x300/narrow rendering.

- [ ] **Step 1: Write the failing tests**

Add tests that call `generate_json_mode_content()` with a minimal `GAME_GIVEAWAY` definition and patch the provider fetch boundary to return deterministic public data. Assert:

```python
assert content["source_label"] in {"EPIC", "STEAM"}
assert content["game_title"] == "Test Game"
assert content["deadline_label"] == "截止 2026-09-30 23:59"
assert content["cover_url"].startswith("https://")
```

Add a mode pipeline test that calls `generate_and_render(persona="GAME_GIVEAWAY", screen_w=400, screen_h=300, colors=2)` and asserts image size, non-empty content, and a non-white pixel count above 500.

- [ ] **Step 2: Run tests to verify they fail**

Run: `PYTHONPATH=backend pytest backend/tests/test_game_giveaway_mode.py backend/tests/test_creative_modes_pipeline.py -k giveaway -v`

Expected: FAIL because `GAME_GIVEAWAY` is not registered and `game_giveaway` provider does not exist.

- [ ] **Step 3: Commit the red tests**

```bash
git add backend/tests/test_game_giveaway_mode.py backend/tests/test_creative_modes_pipeline.py
git commit -m "test: define game giveaway mode behavior"
```

---

### Task 2: Implement the game-giveaway provider

**Files:**
- Create: `backend/core/providers/game_giveaway_provider.py`
- Modify: `backend/core/providers/__init__.py`
- Test: `backend/tests/test_game_giveaway_mode.py`

**Interfaces:**
- Consumes: `config`, `mode_overrides.GAME_GIVEAWAY`, and optional `content_cfg` fields.
- Produces: `generate_game_giveaway(mode_def, content_cfg, fallback, **kwargs) -> dict[str, Any]` registered as `game_giveaway`.

- [ ] **Step 1: Implement deterministic normalization first**

Implement `generate_game_giveaway()` with these exact normalized fields:

```python
{
    "source": "EPIC" or "STEAM",
    "source_label": "EPIC" or "STEAM",
    "game_title": "...",
    "deadline_label": "截止 YYYY-MM-DD HH:MM" or "限时领取",
    "cover_url": "https://..." or "",
    "claim_url": "https://..." or "",
    "description": "...",
}
```

Read overrides from `config.get("mode_overrides", {}).get("GAME_GIVEAWAY", {})`; allow `source`, `game_title`, `deadline`, `cover_url`, `claim_url`, and `description`. Normalize source case to `EPIC`/`STEAM`, parse ISO timestamps with `datetime.fromisoformat`, and never expose arbitrary source strings in the source label.

- [ ] **Step 2: Run provider tests**

Run: `PYTHONPATH=backend pytest backend/tests/test_game_giveaway_mode.py -k provider -v`

Expected: PASS for source normalization, deadline formatting, and fallback behavior.

- [ ] **Step 3: Add optional public endpoint fetch behind explicit configuration**

If `content_cfg["endpoint"]` or the mode override `endpoint` is an HTTPS URL, fetch JSON with the existing `outbound_http` and `RequestPolicy`; map common fields `source/platform`, `title/name`, `deadline/expires_at/end_time`, `cover_url/image/header_image`, `claim_url/url`. On any failure, return normalized fallback without logging response bodies or URLs containing query credentials.

- [ ] **Step 4: Run provider tests again**

Run: `PYTHONPATH=backend pytest backend/tests/test_game_giveaway_mode.py -k provider -v`

Expected: PASS.

- [ ] **Step 5: Commit provider implementation**

```bash
git add backend/core/providers/game_giveaway_provider.py backend/core/providers/__init__.py backend/tests/test_game_giveaway_mode.py
git commit -m "feat: add game giveaway data provider"
```

---

### Task 3: Add localized game-giveaway JSON layouts

**Files:**
- Create: `backend/core/modes/builtin/game_giveaway.json`
- Create: `backend/core/modes/builtin/en/game_giveaway.json`
- Modify: `backend/core/mode_catalog.py`
- Test: `backend/tests/test_game_giveaway_mode.py`

**Interfaces:**
- Consumes: `game_giveaway` provider output fields from Task 2.
- Produces: registry-visible `GAME_GIVEAWAY` mode with localized Chinese/English layouts.

- [ ] **Step 1: Add the Chinese mode definition**

Use `content.type = "computed"`, `content.provider = "game_giveaway"`, and a safe fallback with an HTTPS cover URL, title, `EPIC` source, deadline, claim URL, and description. Layout requirements:

```json
{
  "type": "image",
  "field": "cover_url",
  "width": 400,
  "height": 300,
  "fit": "cover"
}
```

Overlay the source badge at top-left, deadline badge at top-right, and game title badge at bottom-left using existing card/badge/text blocks. Use dark translucent/solid cards if supported by existing renderer; otherwise use solid black badges with white text. Add a fallback text block so title/source/deadline remain readable if the cover fails.

- [ ] **Step 2: Add the English mode definition**

Mirror the Chinese structure with `SOURCE`, `ENDS`, and `CLAIM` labels while keeping the same field names and provider.

- [ ] **Step 3: Register catalog metadata**

Add `GAME_GIVEAWAY` to the built-in catalog with category `more`, display name `喜加一`, and a concise description.

- [ ] **Step 4: Run registry and layout tests**

Run: `PYTHONPATH=backend pytest backend/tests/test_game_giveaway_mode.py -v`

Expected: PASS, including registry visibility and 400x300 render.

- [ ] **Step 5: Commit mode definitions**

```bash
git add backend/core/modes/builtin/game_giveaway.json backend/core/modes/builtin/en/game_giveaway.json backend/core/mode_catalog.py backend/tests/test_game_giveaway_mode.py
git commit -m "feat: add localized game giveaway display mode"
```

---

### Task 4: Verify rendering, narrow screens, and regressions

**Files:**
- Modify: `backend/tests/test_game_giveaway_mode.py` only if a concrete regression is found.

**Interfaces:**
- Consumes: completed provider and localized mode definitions.
- Produces: verified production-ready mode with no existing-mode regressions.

- [ ] **Step 1: Run focused tests**

Run: `PYTHONPATH=backend pytest backend/tests/test_game_giveaway_mode.py backend/tests/test_creative_modes_pipeline.py backend/tests/test_qr_code_mode.py -v`

Expected: all tests pass.

- [ ] **Step 2: Render production preview**

Restart the existing `inksight` container, then request:

```bash
curl -k -s "https://127.0.0.1:3001/api/preview?persona=GAME_GIVEAWAY&w=400&h=300" -H "Host: kellson.dpdns.org:3001" -o /tmp/game-giveaway.png
```

Verify the PNG dimensions are `(400, 300)` and inspect OCR/pixel output for source, deadline, and game title regions.

- [ ] **Step 3: Run the complete backend suite with a bounded timeout**

Run: `timeout 180s bash -c 'PYTHONPATH=backend pytest -q'`

Expected: exit code 0; if external-network tests exceed the timeout, report the exact timeout and retain the focused passing evidence rather than claiming the full suite passed.

- [ ] **Step 4: Check repository state and commit any test-only adjustment**

Run: `git status --short` and restore runtime-mutated files under `backend/data/` before any final commit.

- [ ] **Step 5: Final verification**

Run: `PYTHONPATH=backend pytest backend/tests/test_game_giveaway_mode.py -v` and confirm the final production preview after the last code change.
