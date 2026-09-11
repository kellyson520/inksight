import asyncio
import json
from pathlib import Path

import pytest

from core.mode_catalog import builtin_catalog_map


EXPECTED = {"QIDIAN_NOVEL", "PIXIV_DAILY", "IWARA_VIDEO", "PORN_VIDEO"}


def test_recommendation_modes_are_in_catalog_with_layout_setting():
    ids = set(builtin_catalog_map())
    assert EXPECTED <= ids
    for mode_id in EXPECTED:
        mode_path = Path("backend/core/modes/builtin") / f"{mode_id.lower()}.json"
        data = json.loads(mode_path.read_text(encoding="utf-8"))
        assert data["content"]["provider"]
        en_path = Path("backend/core/modes/builtin/en") / f"{mode_id.lower()}.json"
        assert json.loads(en_path.read_text(encoding="utf-8"))["mode_id"] == mode_id
        setting = next(x for x in data["settings_schema"] if x["key"] == "layout_style")
        assert {x["value"] for x in setting["options"]} == {"ranking", "cover_card"}


@pytest.mark.asyncio
async def test_recommendation_modes_render_both_layouts():
    from core.json_content import generate_json_mode_content
    from core.mode_registry import get_registry
    registry = get_registry()
    for mode_id in EXPECTED:
        mode = registry.get_json_mode(mode_id)
        assert mode is not None
        for style in ("ranking", "cover_card"):
            content = await generate_json_mode_content(mode.definition, config={"mode_overrides": {mode_id: {"layout_style": style}}})
            assert content.get("layout_style") == style


def test_recommendation_layout_style_survives_effective_mode_settings():
    from core.json_content import generate_json_mode_content
    from core.mode_registry import get_registry
    mode = get_registry().get_json_mode("QIDIAN_NOVEL")
    content = asyncio.run(generate_json_mode_content(mode.definition, config={"mode_settings": {"layout_style": "ranking"}}))
    assert content.get("layout_style") == "ranking"


def test_recommendation_cover_card_does_not_overlap_footer():
    """验证 recommendation 块在 cover_card 样式下，图片与标题文字严格位于 Footer 上方，杜绝与底栏重叠。"""
    import json
    from PIL import ImageDraw
    from core.json_renderer import render_json_mode

    with open("backend/core/modes/builtin/pixiv_daily.json", "r", encoding="utf-8") as f:
        mode_def = json.load(f)

    content = {
        "title": "测试插画",
        "subtitle": "艺术家",
        "source": "Pixiv",
        "rank_label": "NO.1",
        "layout_style": "cover_card",
        "items": [{
            "title": "测试插画标题",
            "subtitle": "作者",
            "rank_label": "NO.1",
            "thumbnail_url": "https://example.com/test.jpg",
        }],
    }

    text_y_coords = []
    orig_text = ImageDraw.ImageDraw.text

    def spy_text(self, xy, text, *args, **kwargs):
        text_y_coords.append((xy[1], text))
        return orig_text(self, xy, text, *args, **kwargs)

    try:
        ImageDraw.ImageDraw.text = spy_text
        render_json_mode(
            mode_def,
            content,
            date_str="2026-09-11",
            weather_str="晴",
            battery_pct=100.0,
            screen_w=400,
            screen_h=300,
        )
    finally:
        ImageDraw.ImageDraw.text = orig_text

    rec_texts = [y for y, t in text_y_coords if "测试插画标题" in str(t)]
    assert rec_texts, "未找到推荐项标题文字渲染记录"
    assert rec_texts[0] < 265, f"推荐标题文字 y={rec_texts[0]} 过于靠下，与 Footer 发生重叠！"

