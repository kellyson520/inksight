"""
Unit & Integration tests for Douban Movie and SMZDM modes:
- DOUBAN_MOVIE (豆瓣高分电影推荐，对标微信读书样式：右侧竖版海报，左侧电影名与影评推荐理由)
- SMZDM (什么值得买热门好价排行榜)
"""
from __future__ import annotations

import pytest
from core.douban_movie_service import douban_movie_service
from core.smzdm_service import smzdm_service
from core.pipeline import generate_and_render
from core.providers import list_registered_providers, dispatch_provider


def test_douban_movie_service():
    """验证豆瓣电影服务的基础数据与分类筛选。"""
    all_movies = douban_movie_service.get_movies_by_category("ALL")
    assert len(all_movies) >= 10
    top_movie = all_movies[0]
    assert "title" in top_movie
    assert "cover_url" in top_movie
    assert "recommend_reason" in top_movie

    sci_fi = douban_movie_service.get_movies_by_category("SCI_FI")
    assert any(m["title"] == "星际穿越" for m in sci_fi)

    rec = douban_movie_service.get_recommended_movie(category="TOP250", seed="device_test_123")
    assert "title_bracketed" in rec
    assert "director_line" in rec
    assert "rating_label" in rec
    assert "cover_url" in rec
    assert rec["cover_url"].startswith("http")


def test_smzdm_service():
    """验证什么值得买服务的数据结构与榜单排行。"""
    ranking_all = smzdm_service.get_ranking(category="ALL", count=5)
    assert "top1_title" in ranking_all
    assert "top1_price" in ranking_all
    assert len(ranking_all["items"]) == 5
    assert ranking_all["items"][0]["rank_badge"] == "NO.1"

    ranking_digital = smzdm_service.get_ranking(category="DIGITAL", count=5)
    assert any("MacBook" in it["title"] or "iPhone" in it["title"] or "罗技" in it["title"] for it in ranking_digital["items"])

    ranking_cheap = smzdm_service.get_ranking(category="CHEAP", count=5)
    assert len(ranking_cheap["items"]) == 5


def test_providers_registration():
    """验证 douban_movie 与 smzdm 正确注册到 provider 体系中。"""
    providers = list_registered_providers()
    assert "douban_movie" in providers
    assert "smzdm" in providers


@pytest.mark.asyncio
async def test_douban_movie_mode_render():
    """验证 DOUBAN_MOVIE 模式在中英文环境下完整排版与图片渲染。"""
    for lang, expected_rank in [("zh", "Top 250"), ("en", "Top 250")]:
        img, content = await generate_and_render(
            persona="DOUBAN_MOVIE",
            config={"mode_language": lang},
            date_ctx={"time_str": "16:30", "date_str": "09/05"},
            weather={"weather_str": "晴", "weather_code": 0},
            battery_pct=95.0,
            screen_w=400,
            screen_h=300,
            colors=4,
        )
        assert img.size == (400, 300)
        assert content is not None
        assert "cover_url" in content
        assert "recommend_reason" in content
        assert expected_rank in content.get("rank_tag", "")


@pytest.mark.asyncio
async def test_smzdm_mode_render():
    """验证 SMZDM 模式在中英文环境下完整排版与图片渲染。"""
    for lang in ["zh", "en"]:
        img, content = await generate_and_render(
            persona="SMZDM",
            config={"mode_language": lang},
            date_ctx={"time_str": "16:30", "date_str": "09/05"},
            weather={"weather_str": "晴", "weather_code": 0},
            battery_pct=88.0,
            screen_w=400,
            screen_h=300,
            colors=4,
        )
        assert img.size == (400, 300)
        assert content is not None
        assert "top1_title" in content
        assert "top1_price" in content
        assert "i2_title" in content
