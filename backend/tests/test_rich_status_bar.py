import pytest
from core.context import get_date_context
from core.patterns.utils import draw_status_bar
from PIL import Image, ImageDraw

@pytest.mark.asyncio
async def test_date_context_contains_lunar_and_solar_term():
    ctx = await get_date_context()
    assert "date_str" in ctx
    assert "lunar_str" in ctx, "date_context 必须包含农历字符串 lunar_str"
    assert "solar_term" in ctx, "date_context 必须包含二十四节气 solar_term 字段"
    # 验证农历格式不为空且符合中文习惯，例如 '八月初四' 或 '正月初一'
    if ctx["lunar_str"]:
        assert any(m in ctx["lunar_str"] for m in ["正", "二", "三", "四", "五", "六", "七", "八", "九", "十", "冬", "腊"])

def test_draw_status_bar_renders_rich_info_without_overlapping():
    img = Image.new("1", (400, 300), 1)
    draw = ImageDraw.Draw(img)
    # 调用增强型状态栏绘制
    draw_status_bar(
        draw=draw,
        img=img,
        date_str="9月14日 周一",
        weather_str="晴 22°C",
        battery_pct=85,
        weather_code=0,
        time_str="14:30:00",
        screen_w=400,
        screen_h=300,
        colors=2,
        language="zh",
        lunar_str="八月初四",
        festival_str="中秋节",
    )
    # 验证状态栏区域（y: 0~35）存在充沛且分布合理的黑色像素
    pixels = [img.getpixel((x, y)) for y in range(5, 32) for x in range(10, 390)]
    black_count = pixels.count(0)
    assert black_count > 400, f"Status bar should render rich glyphs, got {black_count} black pixels"

def test_draw_status_bar_small_screen_adapts_cleanly():
    # 296x128 紧凑型墨水屏适配
    img = Image.new("1", (296, 128), 1)
    draw = ImageDraw.Draw(img)
    draw_status_bar(
        draw=draw,
        img=img,
        date_str="9月14日 周一",
        weather_str="22°C",
        battery_pct=45,
        weather_code=1,
        time_str="09:15:00",
        screen_w=296,
        screen_h=128,
        colors=2,
        language="zh",
        lunar_str="八月初四",
    )
    pixels = [img.getpixel((x, y)) for y in range(2, 14) for x in range(5, 290)]
    assert pixels.count(0) > 150
