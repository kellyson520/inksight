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
            assert content.get("title")
