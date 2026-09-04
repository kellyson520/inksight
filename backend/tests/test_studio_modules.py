import pytest
from core.studio_modules import (
    STUDIO_CATEGORIES,
    MODE_TO_STUDIO_CATEGORY,
    get_studio_category_for_mode,
    enrich_mode_with_studio_meta,
)


def test_studio_categories_structure():
    """验证 Studio 四大标准分类定义完备。"""
    assert len(STUDIO_CATEGORIES) == 4
    cat_ids = [c["id"] for c in STUDIO_CATEGORIES]
    assert "life" in cat_ids
    assert "productivity" in cat_ids
    assert "news" in cat_ids
    assert "studio" in cat_ids


def test_mode_to_studio_mapping():
    """验证新旧模式均正确映射到规范分类。"""
    assert get_studio_category_for_mode("HOTLIST") == "news"
    assert get_studio_category_for_mode("DISASTER_ALERT") == "news"
    assert get_studio_category_for_mode("TODO") == "productivity"
    assert get_studio_category_for_mode("CLOCK") == "life"
    assert get_studio_category_for_mode("LETTER") == "studio"
    assert get_studio_category_for_mode("WORD_OF_THE_DAY") == "studio"


def test_enrich_mode_with_studio_meta():
    """验证模式定义正确丰富元数据。"""
    mode_def = {"mode_id": "HOTLIST", "display_name": "全网热点"}
    enriched = enrich_mode_with_studio_meta(mode_def)
    assert enriched["studio_category"] == "news"
    assert enriched["studio_spec_version"] == "1.0.0"
