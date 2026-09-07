import pytest
from PIL import Image, ImageDraw
from core.blocks.context import RenderContext
from core.blocks.geek_widgets import render_contrib_matrix


def test_contrib_matrix_renders_without_crashing():
    img = Image.new("1", (400, 300), 1)
    draw = ImageDraw.Draw(img)
    ctx = RenderContext(
        draw=draw,
        img=img,
        screen_w=400,
        screen_h=300,
        content={
            "contributions": [i % 4 for i in range(7 * 16)],
            "username": "octocat",
        },
    )

    block = {
        "type": "contrib_matrix",
        "field": "contributions",
        "weeks": 16,
        "show_weekday_labels": True,
        "margin_x": 16,
        "margin_bottom": 10,
    }

    initial_y = ctx.y
    render_contrib_matrix(ctx, block)

    # Verify ctx.y moved down
    assert ctx.y > initial_y

    # Verify pixels were drawn on the canvas (some black pixels exist in the matrix area)
    pixels = img.load()
    black_pixel_count = sum(
        1 for y in range(initial_y, ctx.y)
        for x in range(16, 380)
        if pixels[x, y] == 0
    )
    assert black_pixel_count > 50


def test_contrib_matrix_handles_empty_gracefully():
    img = Image.new("1", (400, 300), 1)
    draw = ImageDraw.Draw(img)
    ctx = RenderContext(
        draw=draw,
        img=img,
        screen_w=400,
        screen_h=300,
        content={},
    )

    block = {
        "type": "contrib_matrix",
        "field": "nonexistent",
        "weeks": 12,
    }

    initial_y = ctx.y
    render_contrib_matrix(ctx, block)
    assert ctx.y > initial_y
