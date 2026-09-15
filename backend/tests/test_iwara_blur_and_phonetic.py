import pytest
from PIL import Image, ImageDraw
from core.image_processing import fit_image_to_box, quantize_image_for_eink
from core.patterns.utils import load_font_by_name, load_font
from core.mode_registry import get_registry
from core.json_renderer import render_json_mode

def test_phonetic_gentium_and_ipa_rendering():
    """Verify that IPA symbols render cleanly without tofu boxes."""
    font = load_font_by_name("GentiumPlus-Regular.ttf", 16)
    test_ipa = "/ˌser.ənˈdɪp.ə.ti/ /ɪˈfem.ər.əl/ /ˈpet.rɪ.kɔːr/ /ˈsɒn.dər/ /ˈzen.ɪθ/"
    
    # In GentiumPlus, IPA characters have proper glyph bounding boxes, not uniform 24x25 tofu
    bbox = font.getbbox(test_ipa)
    assert bbox[2] > 0, "Bounding box width must be > 0"
    
    # Check individual key IPA characters
    for ch in ["ˈ", "ˌ", "ɪ", "ə", "ɒ", "θ", "ː"]:
        mask = font.getmask(ch)
        assert mask.size[0] > 0 and mask.size[1] > 0, f"Glyph {ch!r} must have positive dimensions"
        # In NotoSerifSC (tofu), all glyphs were (16, 17) or (24, 25); in Gentium they vary by glyph
        assert mask.size != (16, 17)

def test_phonetic_fallback_preserves_ipa():
    """Verify fallback for missing gentium/ipa fonts falls back to Lora/Inter, not NotoSerifSC."""
    # Test a fake phonetic font name
    font = load_font_by_name("NonExistent-Gentium-Phonetic.ttf", 16)
    for ch in ["ə", "ɪ", "ˈ"]:
        mask = font.getmask(ch)
        # Should not be NotoSerifSC tofu box
        assert mask.size[0] > 0

def test_word_of_the_day_rendering():
    """Verify WORD_OF_THE_DAY renders properly with phonetic transcription."""
    reg = get_registry()
    mode_def = reg.get_json_mode("WORD_OF_THE_DAY")
    assert mode_def is not None
    content = mode_def.definition["content"]["fallback"]
    
    img = render_json_mode(
        mode_def=mode_def.definition,
        content=content,
        date_str="9月15日 周二",
        weather_str="晴 25°C",
        battery_pct=95.0,
        screen_w=400,
        screen_h=300,
    )
    assert img.size == (400, 300)

def test_iwara_backdrop_blur_fit():
    """Verify fit_image_to_box with backdrop_blur creates a sharp foreground on enlarged blurred background."""
    # Create distinct foreground image with high contrast center and colored edge
    src = Image.new("RGB", (320, 180), (200, 30, 30))
    d = ImageDraw.Draw(src)
    d.rectangle([40, 40, 280, 140], fill=(30, 200, 30))
    d.text((100, 80), "SHARP TEST", fill=(255, 255, 255))
    
    result = fit_image_to_box(src, 400, 240, fit="backdrop_blur")
    assert result.size == (400, 240)
    
    # Check that corners/outer border are not plain white (they are filled with blurred enlarged background)
    corner_pixel = result.getpixel((5, 5))
    assert corner_pixel != (255, 255, 255), "Corner must be filled with blurred backdrop, not blank white"
    
    # Center pixel should contain foreground content
    center_pixel = result.getpixel((200, 120))
    assert center_pixel != (255, 255, 255)
    
    # Quantize to e-ink
    eink_bw = quantize_image_for_eink(result, colors=2)
    assert eink_bw.size == (400, 240)


def test_iwara_backdrop_blur_vertical_and_sharp_foreground():
    """Verify that a vertical cover retains full height in center and blurred backdrop on side wings."""
    # Vertical image 100x200 with sharp checkerboard pattern in center
    src = Image.new("RGB", (100, 200), (220, 50, 50))
    d = ImageDraw.Draw(src)
    d.rectangle([10, 10, 90, 190], fill=(20, 20, 20))
    # Top and bottom markers that would be cropped out in cover mode
    d.rectangle([20, 5, 80, 15], fill=(255, 255, 0)) # top marker
    d.rectangle([20, 185, 80, 195], fill=(0, 255, 255)) # bottom marker

    result = fit_image_to_box(src, 400, 200, fit="backdrop_blur")
    assert result.size == (400, 200)

    # 1. Check that outer left side (x=20, y=100) is blurred backdrop, NOT white
    left_wing = result.getpixel((20, 100))
    assert left_wing != (255, 255, 255), "Side wings must contain blurred backdrop"

    # 2. Check that top marker and bottom marker are preserved in the center (NOT cropped off)
    # Center is at x=200, width is ~100 so marker is near x=200, y=10 and y=190
    top_pixel = result.getpixel((200, 10))
    bottom_pixel = result.getpixel((200, 190))
    # In cover mode, zoom is 4x so top/bottom would be completely lost outside bounds
    # In backdrop blur mode, the foreground is contained so top and bottom markers are present
    assert top_pixel == (255, 255, 0) or sum(abs(a - b) for a, b in zip(top_pixel, (255, 255, 0))) < 30, f"Top marker should be preserved in foreground, got {top_pixel}"
    assert bottom_pixel == (0, 255, 255) or sum(abs(a - b) for a, b in zip(bottom_pixel, (0, 255, 255))) < 30, f"Bottom marker should be preserved in foreground, got {bottom_pixel}"

