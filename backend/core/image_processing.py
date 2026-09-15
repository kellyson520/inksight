"""Reusable image fitting and e-ink quantization helpers."""
from __future__ import annotations

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageOps

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


def enhance_photo_for_eink(rgb: Image.Image) -> Image.Image:
    """Conservative photo preparation before e-ink quantization."""
    flattened = _flatten_alpha_to_white(rgb)
    img = ImageOps.autocontrast(flattened, cutoff=1)
    img = ImageEnhance.Contrast(img).enhance(1.12)
    img = ImageEnhance.Sharpness(img).enhance(1.25)
    return img.filter(ImageFilter.UnsharpMask(radius=0.8, percent=80, threshold=3))


def quantize_image_for_eink(
    rgb: Image.Image,
    *,
    colors: int,
    photo_enhance: bool = False,
) -> Image.Image:
    """Quantize RGB image data for 2-, 3-, or 4-color e-ink output with Atkinson dithering."""
    rgb_flattened = _flatten_alpha_to_white(rgb)
    prepared = enhance_photo_for_eink(rgb_flattened) if photo_enhance else rgb_flattened

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
