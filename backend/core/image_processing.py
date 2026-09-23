"""Reusable image fitting and e-ink quantization helpers."""
from __future__ import annotations

from functools import lru_cache
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageOps, ImageStat

from . import native_dither


def _aligned_offset(container: int, content: int, align: str) -> int:
    if align in ("left", "top", "start"):
        return 0
    if align in ("right", "bottom", "end"):
        return container - content
    return (container - content) // 2


def fit_image_to_box(
    src: Image.Image,
    width: int,
    height: int,
    *,
    fit: str = "fill",
    align_x: str = "center",
    align_y: str = "center",
) -> Image.Image:
    """Fit an image into an RGB box using JSON image-block semantics."""
    src_rgba = ImageOps.exif_transpose(src).convert("RGBA")
    fit_mode = str(fit or "fill").lower()
    if fit_mode in ("fill", "stretch"):
        base = Image.new("RGBA", (width, height), (255, 255, 255, 255))
        base.alpha_composite(src_rgba.resize((width, height), Image.LANCZOS))
        return base.convert("RGB")

    src_w = max(1, src_rgba.size[0])
    src_h = max(1, src_rgba.size[1])
    scale_x = width / src_w
    scale_y = height / src_h

    if fit_mode in ("backdrop_blur", "contain_blur", "iwara_blur", "blur"):
        # 1. 扩大的毛玻璃/放大镜模糊背景（仿照 iwara/视频播放器卡片高质感呈现）
        scale_bg = max(scale_x, scale_y) * 1.3
        bg_w = max(width, int(round(src_w * scale_bg)))
        bg_h = max(height, int(round(src_h * scale_bg)))
        bg_img = src_rgba.resize((bg_w, bg_h), Image.LANCZOS)
        crop_x = max(0, (bg_w - width) // 2)
        crop_y = max(0, (bg_h - height) // 2)
        bg_cropped = bg_img.crop((crop_x, crop_y, crop_x + width, crop_y + height))

        blur_radius = max(6, int(min(width, height) * 0.05))
        bg_blurred = bg_cropped.filter(ImageFilter.GaussianBlur(radius=blur_radius))
        bg_soft = ImageEnhance.Brightness(bg_blurred).enhance(0.88)
        bg_soft = ImageEnhance.Contrast(bg_soft).enhance(0.80)

        # 2. 前置主体清晰封面（居中保持原生纵横比，不拉伸变形）
        scale_fg = min(scale_x, scale_y)
        fg_w = max(1, int(round(src_w * scale_fg)))
        fg_h = max(1, int(round(src_h * scale_fg)))
        fg_resized = src_rgba.resize((fg_w, fg_h), Image.LANCZOS)

        base = bg_soft.convert("RGBA")
        paste_x = _aligned_offset(width, fg_w, align_x)
        paste_y = _aligned_offset(height, fg_h, align_y)

        # 3. 增加微立体阴影与白色描边，使主体封面与模糊背景分层鲜明
        if fg_w < width or fg_h < height:
            shadow_offset = max(2, int(2 * (width / 400)))
            shadow = Image.new("RGBA", (fg_w + shadow_offset * 2, fg_h + shadow_offset * 2), (0, 0, 0, 110))
            base.alpha_composite(shadow, (paste_x - shadow_offset, paste_y - shadow_offset))

            draw = ImageDraw.Draw(fg_resized)
            draw.rectangle([0, 0, fg_w - 1, fg_h - 1], outline=(255, 255, 255, 200), width=1)

        base.alpha_composite(fg_resized, (paste_x, paste_y))
        return base.convert("RGB")

    scale = min(scale_x, scale_y) if fit_mode == "contain" else max(scale_x, scale_y)
    resized_w = max(1, int(round(src_w * scale)))
    resized_h = max(1, int(round(src_h * scale)))
    resized = src_rgba.resize((resized_w, resized_h), Image.LANCZOS)
    base = Image.new("RGBA", (width, height), (255, 255, 255, 255))
    paste_x = _aligned_offset(width, resized_w, align_x)
    paste_y = _aligned_offset(height, resized_h, align_y)
    base.alpha_composite(resized, (paste_x, paste_y))
    return base.convert("RGB")


def _flatten_alpha_to_white(im: Image.Image) -> Image.Image:
    """Flatten any transparent channels (RGBA, LA, P with transparency) onto a white background."""
    if im.mode in ("RGBA", "LA") or (im.mode == "P" and "transparency" in im.info):
        rgba = im.convert("RGBA")
        base = Image.new("RGBA", rgba.size, (255, 255, 255, 255))
        base.alpha_composite(rgba)
        return base.convert("RGB")
    if im.mode != "RGB":
        return im.convert("RGB")
    return im


@lru_cache(maxsize=128)
def _get_apple_eink_lut(mean_bucket: int) -> tuple[int, ...]:
    """生成并缓存苹果级 256 色阶调色曲线映射表 (自适应曝光 LUT)。"""
    mean_lum = float(mean_bucket)
    lut: list[int] = []
    for i in range(256):
        x = i / 255.0

        # 暗部平滑提亮 (伽马微扩张)
        if x < 0.35:
            val = x ** 0.82 * 1.12
        elif x > 0.80:
            val = 0.80 + (x - 0.80) * 0.90
        else:
            # 中间调自然过渡
            val = x

        # 针对欠曝画面进行智能光感补偿
        if mean_lum < 95.0:
            val = min(1.0, val * 1.10)
        elif mean_lum > 185.0:
            val = max(0.0, val * 0.95)

        mapped_byte = int(max(0.0, min(1.0, val)) * 255.0 + 0.5)
        lut.append(mapped_byte)
    return tuple(lut)


def apply_apple_eink_tone_curve(im: Image.Image) -> Image.Image:
    """苹果级墨水屏光影雕琢曲线 (Apple-Grade E-Ink Tonal Curve)。

    针对电子纸微胶囊物理双稳态特性精益设计：
    1. 动态自适应暗部增益 (Shadow Boost)：在 0~85 亮度区间执行微伽马曲线平滑扩展，
       避免人像头发、深色西装及暗景在二值化后塌陷为死黑块（唤醒暗部细节）；
    2. 局部高光平滑滚降 (Highlight Roll-off)：在 200~255 亮度区间执行非线性平滑过渡，
       保护天空云层、浅色面部与雪景不被过曝切断为纯白；
    3. 中间调局部微反差 (Midtone Clarity)：微调 UnsharpMask 半径与阈值，
       消除传统全局锐化的虚影白边 (Halo)，使照片呈现纸质书籍般的真实印刷层次。
    """
    flat = _flatten_alpha_to_white(im)
    rgb = flat.convert("RGB")

    # 1. 测算整体亮度均值，进行全局动态自适应曝光补偿
    gray = rgb.convert("L")
    stat = ImageStat.Stat(gray)
    mean_lum = stat.mean[0] if stat.mean else 128.0

    # 查表获取高性能量化 LUT 映射
    mean_bucket = int(round(mean_lum / 2.0)) * 2
    lut = list(_get_apple_eink_lut(mean_bucket))

    adjusted = rgb.point(lut * 3)

    # 2. 局部微反差与清晰度雕琢 (无光晕非锐化掩模)
    enhanced = ImageEnhance.Contrast(adjusted).enhance(1.08)
    enhanced = ImageEnhance.Sharpness(enhanced).enhance(1.20)
    return enhanced.filter(ImageFilter.UnsharpMask(radius=0.9, percent=95, threshold=2))


def enhance_photo_for_eink(rgb: Image.Image) -> Image.Image:
    """Conservative photo preparation before e-ink quantization with Apple-grade tonal curve."""
    return apply_apple_eink_tone_curve(rgb)


def hybrid_dither_for_eink(
    im: Image.Image,
    *,
    colors: int = 2,
    edge_preserve: bool = True,
    dark_threshold: int = 40,
    bright_threshold: int = 225,
) -> Image.Image:
    """自适应混合墨水屏抖动算法 (Hybrid E-ink Dithering)。

    - 对高反差笔画、文字与几何边缘保持绝对二值化（零噪点、坚挺黑线）；
    - 对中间连续灰度调与渐变区执行高质量 Atkinson 误差扩散；
    - 在 1-bit 黑白点阵上兼顾文本极度锐利与摄影灰度过渡。
    """
    flat = _flatten_alpha_to_white(im)
    gray = flat.convert("L")

    # 1. 生成高质量抖动全图
    dithered = native_dither.atkinson_bw(gray) if colors < 3 else native_dither.atkinson_palette(flat, colors)

    if not edge_preserve or colors >= 3:
        return dithered

    # 2. 提取极端高对比度固实像素遮罩（深黑与亮白）
    # 极黑像素（如文字、纯黑细线）直接固定为黑 (0)
    solid_black = gray.point(lambda p: 255 if p <= dark_threshold else 0, mode="1")
    # 极亮背景直接固定为白 (255)
    solid_white = gray.point(lambda p: 255 if p >= bright_threshold else 0, mode="1")

    # 3. 将固实黑/白覆盖回抖动结果上，消除边缘噪点
    res = dithered.copy()
    # 贴纯黑
    black_mask = Image.new("1", res.size, 0)
    res.paste(black_mask, (0, 0), mask=solid_black)
    # 贴纯白
    white_mask = Image.new("1", res.size, 1)
    res.paste(white_mask, (0, 0), mask=solid_white)

    return res


def quantize_image_for_eink(
    rgb: Image.Image,
    *,
    colors: int,
    photo_enhance: bool = False,
    hybrid: bool = False,
) -> Image.Image:
    """Quantize RGB image data for 2-, 3-, or 4-color e-ink output with Atkinson/Hybrid dithering."""
    rgb_flattened = _flatten_alpha_to_white(rgb)
    prepared = enhance_photo_for_eink(rgb_flattened) if photo_enhance else rgb_flattened

    if hybrid:
        return hybrid_dither_for_eink(prepared, colors=colors)

    if colors < 3:
        gray = ImageOps.autocontrast(prepared.convert("L"), cutoff=1)
        return native_dither.atkinson_bw(gray)

    return native_dither.atkinson_palette(prepared, 3 if colors == 3 else 4)


def convert_image_block(
    src: Image.Image,
    width: int,
    height: int,
    colors: int,
    *,
    fit: str = "fill",
    align_x: str = "center",
    align_y: str = "center",
    photo_enhance: bool = False,
) -> Image.Image:
    """Fit and quantize an image for a JSON image block."""
    fitted = fit_image_to_box(src, width, height, fit=fit, align_x=align_x, align_y=align_y)
    return quantize_image_for_eink(
        fitted,
        colors=colors,
        photo_enhance=photo_enhance,
    )
