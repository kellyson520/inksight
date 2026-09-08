"""Failing contract tests for the planned GAME_GIVEAWAY mode."""
from unittest.mock import AsyncMock, patch

import pytest

from core.json_content import generate_json_mode_content
from core.pipeline import generate_and_render
from core.mode_registry import get_registry


GAME_GIVEAWAY_MODE = {
    "mode_id": "GAME_GIVEAWAY",
    "display_name": "喜加一",
    "cacheable": True,
    "content": {
        "type": "computed",
        "provider": "game_giveaway",
        "fallback": {
            "source_label": "EPIC",
            "game_title": "Fallback Game",
            "deadline_label": "限时领取",
            "cover_url": "",
        },
    },
    "layout": {"body": [{"type": "text", "field": "game_title"}]},
}


@pytest.mark.asyncio
async def test_game_giveaway_provider_normalizes_deterministic_payload():
    """Provider output exposes safe, deterministic display fields."""
    provider_payload = {
        "platform": "epic",
        "title": "Test Game",
        "deadline": "2026-09-30T23:59:00",
        "cover_url": "https://cdn.example.test/test-game.jpg",
        "claim_url": "https://store.epicgames.com/test-game",
    }
    with patch(
        "core.providers.game_giveaway_provider._fetch_giveaway_payload",
        new=AsyncMock(return_value=provider_payload),
    ):
        content = await generate_json_mode_content(
            {**GAME_GIVEAWAY_MODE, "content": {**GAME_GIVEAWAY_MODE["content"], "endpoint": "https://example.test/giveaway.json"}},
            config={"mode_overrides": {"GAME_GIVEAWAY": {}}},
            date_str="2026-09-08",
            weather_str="晴",
        )

    assert content["source_label"] in {"EPIC", "STEAM"}
    assert content["game_title"] == "Test Game"
    assert content["deadline_label"] == "截止 2026-09-30 23:59"
    assert content["cover_url"].startswith("https://")


@pytest.mark.asyncio
async def test_game_giveaway_provider_falls_back_to_safe_cover_without_endpoint():
    from core.providers.game_giveaway_provider import generate_game_giveaway

    content = await generate_game_giveaway({}, {"fallback": {}}, {})
    assert content["source_label"] == "EPIC"
    assert content["cover_url"].startswith("https://")


def test_game_giveaway_layout_uses_cover_and_corner_fields():
    definition = get_registry().get_json_mode("GAME_GIVEAWAY").definition
    body = definition["layout"]["body"]
    serialized = str(body)
    assert "'type': 'game_giveaway'" in serialized
    assert "'fit': 'contain'" in serialized
    assert "'cover_field': 'cover_url'" in serialized
    assert "'source_field': 'source_label'" in serialized
    assert "'deadline_field': 'deadline_label'" in serialized
    assert "'title_field': 'game_title'" in serialized


@pytest.mark.asyncio
async def test_game_giveaway_mode_renders_at_400x300():
    img, content = await generate_and_render(
        persona="GAME_GIVEAWAY",
        config={"modes": ["GAME_GIVEAWAY"]},
        date_ctx={"date_str": "2026-09-08", "time_str": "12:00"},
        weather={"weather_str": "晴", "weather_code": 0},
        battery_pct=90,
        screen_w=400,
        screen_h=300,
        colors=2,
    )

    assert img.size == (400, 300)
    assert content is not None
    gray = img.convert("L")
    assert sum(1 for pixel in gray.getdata() if pixel < 250) > 500
    assert sum(1 for y in range(18, 55) for x in range(8, 392) if gray.getpixel((x, y)) < 80) > 50
    assert sum(1 for y in range(165, 245) for x in range(8, 250) if gray.getpixel((x, y)) < 80) > 50


@pytest.mark.asyncio
async def test_game_giveaway_mode_renders_on_narrow_screen():
    img, content = await generate_and_render(
        persona="GAME_GIVEAWAY",
        config={"modes": ["GAME_GIVEAWAY"]},
        date_ctx={"date_str": "2026-09-08", "time_str": "12:00"},
        weather={"weather_str": "晴", "weather_code": 0},
        battery_pct=90,
        screen_w=296,
        screen_h=128,
        colors=2,
    )

    assert img.size == (296, 128)
    assert content is not None
