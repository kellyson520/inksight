# Creative Community Modes & Primitives Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans or superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build 3 creative, high-engagement community desktop modes (GitHub Contributions Heatmap, Periodic Table Element of the Day, Daily XKCD Geek Comic) backed by the new `contrib_matrix` rendering primitive and resilient services.

**Architecture:**
1. `contrib_matrix` block in `backend/core/blocks/geek_widgets.py`: 7-row × N-week e-ink dithered heatmap grid.
2. `core/github_service.py`: GitHub user activity and contributions fetcher with offline sample fallback.
3. `core/periodic_table.py`: Curated 118-element periodic table catalog with daily rotation and trivia.
4. `core/xkcd_service.py`: Daily XKCD comic metadata and 1-bit Floyd-Steinberg dithered image processing.
5. Standard JSON mode definitions in `backend/core/modes/builtin/` and registration in `core/mode_catalog.py`.

**Tech Stack:** Python 3.10, FastAPI, PIL/Pillow (1-bit dithering), Next.js 16, Pytest.

**Spec:** `docs/design/2026-09-07-creative-community-modes-and-primitives.md`

## Global Constraints
- Strict e-ink contrast compliance: No emojis; crisp pixel alignment; support 1-bit monochrome screens (400x300 and 296x128).
- Resilient network calls: Any external API must use `outbound_http` and have instant fallback when offline or rate-limited.
- TDD Red-Green-Refactor on every step.

---

### Task 1: The `contrib_matrix` Heatmap Grid Block
**Files:**
- Create: `backend/tests/test_contrib_matrix.py`
- Modify: `backend/core/blocks/geek_widgets.py`
- Modify: `backend/core/blocks/registry.py`
- Modify: `backend/core/blocks/__init__.py`

- [ ] **Step 1: Write the failing test**
- [ ] **Step 2: Run test to verify it fails (RED)**
- [ ] **Step 3: Implement `render_contrib_matrix` in `geek_widgets.py`**
- [ ] **Step 4: Run test to verify it passes (GREEN)**
- [ ] **Step 5: Commit**

### Task 2: GitHub Data Provider & Service (`github_service.py`)
**Files:**
- Create: `backend/tests/test_github_service.py`
- Create: `backend/core/github_service.py`

- [ ] **Step 1: Write the failing test**
- [ ] **Step 2: Run test to verify it fails (RED)**
- [ ] **Step 3: Implement `github_service.py` with fallback and cache**
- [ ] **Step 4: Run test to verify it passes (GREEN)**
- [ ] **Step 5: Commit**

### Task 3: Periodic Table Element Provider (`periodic_table.py`)
**Files:**
- Create: `backend/tests/test_periodic_table.py`
- Create: `backend/core/periodic_table.py`

- [ ] **Step 1: Write the failing test**
- [ ] **Step 2: Run test to verify it fails (RED)**
- [ ] **Step 3: Implement `periodic_table.py`**
- [ ] **Step 4: Run test to verify it passes (GREEN)**
- [ ] **Step 5: Commit**

### Task 4: XKCD Daily Comic Provider (`xkcd_service.py`)
**Files:**
- Create: `backend/tests/test_xkcd_service.py`
- Create: `backend/core/xkcd_service.py`

- [ ] **Step 1: Write the failing test**
- [ ] **Step 2: Run test to verify it fails (RED)**
- [ ] **Step 3: Implement `xkcd_service.py`**
- [ ] **Step 4: Run test to verify it passes (GREEN)**
- [ ] **Step 5: Commit**

### Task 5: JSON Builtin Modes & Catalog Integration
**Files:**
- Create: `backend/core/modes/builtin/github_pulse.json`
- Create: `backend/core/modes/builtin/element_day.json`
- Create: `backend/core/modes/builtin/xkcd_comic.json`
- Modify: `backend/core/mode_catalog.py`
- Create: `backend/tests/test_creative_modes_pipeline.py`

- [ ] **Step 1: Write mode definitions and catalog entries**
- [ ] **Step 2: Write pipeline rendering tests**
- [ ] **Step 3: Verify all 3 modes render to valid 1-bit/PNG images without error**
- [ ] **Step 4: Commit**

### Task 6: Full System Verification, WebApp Build & Container Restart
- [ ] **Step 1: Run comprehensive backend test suite**
- [ ] **Step 2: Test live preview endpoint `/api/preview?persona=GITHUB_PULSE`**
- [ ] **Step 3: Rebuild webapp and restart Docker container**
