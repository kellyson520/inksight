from __future__ import annotations

import pytest

from core.blocks import BlockSpec


def test_block_spec_normalizes_nested_blocks_and_collects_explicit_resources():
    spec = BlockSpec.from_dict(
        {
            "type": "section",
            "title": "News",
            "icon": "news",
            "children": [
                {"type": "image", "src": "https://example.com/a.png"},
                {"type": "text", "text": "plain text"},
            ],
        }
    )

    assert spec.type == "section"
    assert spec.children[0].type == "image"
    assert spec.to_dict()["children"][1]["type"] == "text"
    assert spec.collect_resources() == {"news", "https://example.com/a.png"}


def test_block_spec_validation_rejects_missing_or_unknown_types():
    with pytest.raises(ValueError, match="type"):
        BlockSpec.from_dict({"text": "missing type"})

    unknown = BlockSpec.from_dict({"type": "does_not_exist"})
    with pytest.raises(ValueError, match="unknown block type"):
        unknown.validate()


def test_json_renderer_uses_block_spec_for_measure_and_render(monkeypatch):
    from core.json_renderer import render_json_mode

    calls = []
    monkeypatch.setattr(BlockSpec, "measure", lambda self, ctx, width: calls.append("measure") or (width, 10))
    monkeypatch.setattr(BlockSpec, "render", lambda self, ctx: calls.append("render"))
    render_json_mode(
        {"mode_id": "TEST", "layout": {"body": [{"type": "text", "text": "hello"}]}},
        {}, date_str="", weather_str="", battery_pct=100,
    )
    assert calls == ["measure", "render"]


@pytest.mark.asyncio
async def test_block_spec_prefetch_returns_bytes_and_records_failures():
    spec = BlockSpec.from_dict({"type": "image", "src": "https://example.com/a.png"})

    async def fetch(resource):
        if resource.endswith("a.png"):
            return b"image-bytes"
        raise OSError("offline")

    result = await spec.prefetch(fetch)
    assert result == {"https://example.com/a.png": b"image-bytes"}
    assert spec.prefetch_errors == {}


@pytest.mark.asyncio
async def test_block_spec_prefetch_accepts_media_fetch_result():
    spec = BlockSpec.from_dict({"type": "image", "src": "image.png"})

    class Result:
        data = b"image-bytes"

    async def fetch(_resource):
        return Result()

    assert await spec.prefetch(fetch) == {"image.png": b"image-bytes"}


@pytest.mark.asyncio
async def test_block_spec_prefetch_does_not_drop_success_when_one_resource_fails():
    spec = BlockSpec.from_dict(
        {"type": "section", "children": [
            {"type": "image", "src": "ok.png"},
            {"type": "image", "src": "bad.png"},
        ]}
    )
    async def fetch(resource):
        if resource == "ok.png":
            return b"ok"
        raise OSError("offline")

    result = await spec.prefetch(fetch)
    assert result == {"ok.png": b"ok"}
    assert spec.prefetch_errors == {"bad.png": "offline"}


@pytest.mark.asyncio
async def test_block_spec_prefetch_with_sync_media_fetcher():
    spec = BlockSpec.from_dict({"type": "image", "src": "image.png"})

    class Result:
        data = b"image-bytes"

    def fetch(_resource):
        return Result()

    assert await spec.prefetch_with_media_fetcher(fetch) == {"image.png": b"image-bytes"}


def test_block_spec_validation_rejects_invalid_structural_props():
    invalid_specs = [
        {"type": "section", "children": {"type": "text"}},
        {"type": "image"},
        {"type": "progress_bar", "value": "bad", "max": 10},
        {"type": "two_column", "left": "bad", "right": []},
    ]
    for block in invalid_specs:
        with pytest.raises(ValueError, match="invalid"):
            BlockSpec.from_dict(block).validate()


def test_block_spec_validation_accepts_optional_legacy_props():
    BlockSpec.from_dict(
        {"type": "image", "url": "https://example.com/a.png", "custom_renderer_flag": True}
    ).validate()


def test_block_spec_render_and_measure_delegate_to_existing_dispatcher(monkeypatch):
    from core.blocks import spec as spec_module

    calls = []
    monkeypatch.setattr(spec_module, "render_block", lambda ctx, block: calls.append(("render", block)))
    monkeypatch.setattr(spec_module, "measure_block_size", lambda ctx, block, width: (width, 7))
    spec = BlockSpec.from_dict({"type": "text", "text": "hello"})

    ctx = type("Context", (), {"y": 10})()
    assert spec.measure(ctx, 123) == (123, 7)
    assert ctx.y == 17
    spec.render(object())
    assert calls == [("render", {"type": "text", "text": "hello"})]
