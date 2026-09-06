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
