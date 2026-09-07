import pytest
from core.mode_registry import get_registry
from core.pipeline import generate_and_render


def test_creative_modes_registered_in_registry():
    registry = get_registry()
    supported = registry.get_supported_ids()
    assert "GITHUB_PULSE" in supported
    assert "ELEMENT_DAY" in supported
    assert "XKCD_COMIC" in supported


@pytest.mark.asyncio
async def test_github_pulse_mode_pipeline():
    img, content = await generate_and_render(
        persona="GITHUB_PULSE",
        config={
            "modes": ["GITHUB_PULSE"],
            "mode_overrides": {
                "GITHUB_PULSE": {
                    "username": "octocat",
                }
            },
        },
        date_ctx={"date_str": "2026-09-07", "time_str": "12:00"},
        weather={"weather_str": "晴", "weather_code": 0},
        battery_pct=95,
        screen_w=400,
        screen_h=300,
        colors=2,
    )
    assert img.size == (400, 300)
    assert content["username"] == "octocat"
    assert "contributions" in content
    assert len(content["contributions"]) > 0


@pytest.mark.asyncio
async def test_element_day_mode_pipeline():
    img, content = await generate_and_render(
        persona="ELEMENT_DAY",
        config={"modes": ["ELEMENT_DAY"]},
        date_ctx={"date_str": "2026-09-07", "time_str": "12:00"},
        weather={"weather_str": "晴", "weather_code": 0},
        battery_pct=88,
        screen_w=400,
        screen_h=300,
        colors=2,
    )
    assert img.size == (400, 300)
    assert "symbol" in content
    assert "atomic_number" in content
    assert "summary" in content


@pytest.mark.asyncio
async def test_xkcd_comic_mode_pipeline():
    img, content = await generate_and_render(
        persona="XKCD_COMIC",
        config={"modes": ["XKCD_COMIC"]},
        date_ctx={"date_str": "2026-09-07", "time_str": "12:00"},
        weather={"weather_str": "晴", "weather_code": 0},
        battery_pct=72,
        screen_w=400,
        screen_h=300,
        colors=2,
    )
    assert img.size == (400, 300)
    assert "title" in content
    assert "alt" in content
    assert "num" in content


@pytest.mark.asyncio
async def test_creative_modes_narrow_screen_support():
    # Test rendering on 2.9 inch (296x128) e-ink display
    for persona in ["GITHUB_PULSE", "ELEMENT_DAY", "XKCD_COMIC"]:
        img, content = await generate_and_render(
            persona=persona,
            config={"modes": [persona]},
            date_ctx={"date_str": "2026-09-07", "time_str": "12:00"},
            weather={"weather_str": "晴", "weather_code": 0},
            battery_pct=80,
            screen_w=296,
            screen_h=128,
            colors=2,
        )
        assert img.size == (296, 128)
        assert content is not None
