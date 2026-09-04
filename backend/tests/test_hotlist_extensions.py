import pytest
from core.hotlist_service import HotlistService, PLATFORM_NAMES


@pytest.mark.asyncio
async def test_hotlist_new_platforms_support():
    """验证 HotlistService 支持网易云音乐、豆瓣电影、微信与抖音热榜。"""
    service = HotlistService(ttl=300)

    # 1. 验证解析
    parsed = service.parse_platforms(["netease", "douban", "douyin", "wechat"])
    assert "netease" in parsed
    assert "douban" in parsed
    assert "douyin" in parsed
    assert "wechat" in parsed

    # 2. 验证各新增单平台拉取与兜底保护
    for plat in ["netease", "douban", "douyin", "wechat"]:
        res = await service.get_hotlist(plat, limit=6)
        assert res is not None
        assert "items" in res
        assert len(res["items"]) >= 4
        # 验证特定平台字段指示符
        if plat == "netease":
            assert any("♪" in (item.get("hot_value") or item.get("hot", "")) for item in res["items"])
        elif plat == "douban":
            assert any("★" in (item.get("hot_value") or item.get("hot", "")) for item in res["items"])

    # 3. 验证多平台跨平台聚合与动态标题
    multi_res = await service.get_multi_hotlist(["netease", "douban", "douyin"], limit=6)
    assert multi_res is not None
    assert "网易云" in multi_res["platform_title"] or "豆瓣" in multi_res["platform_title"]
    assert len(multi_res["items"]) == 6
