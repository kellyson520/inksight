# Pixiv Rendering Chain Fix Plan

**Goal:** Make Pixiv daily recommendations reliably acquire public image bytes and render them in the final preview/device image, with proxy support and deterministic fallback.

**Architecture:** Trace provider response normalization, JSON content dispatch, image-field prefetch/rendering, and outbound proxy propagation. Keep public-only behavior and use a local PIL fallback when upstream acquisition fails.

**Tech Stack:** Python 3.10, FastAPI, httpx, Pillow, pytest.

## Tasks

- [ ] Add failing tests for real JSON fallback, image bytes reaching renderer, and proxy propagation.
- [ ] Verify RED failures reproduce missing items/image bytes.
- [ ] Fix Pixiv provider response shape and public endpoint parsing.
- [ ] Fix renderer/media-fetcher proxy and PIL image handling.
- [ ] Verify GREEN with focused and regression suites.
- [ ] Restart managed runtime, generate Pixiv PNG, inspect image statistics/OCR and logs.
- [ ] Run web/backend checks, review diff, and commit.
