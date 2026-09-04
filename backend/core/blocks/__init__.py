"""
InkSight 模块化墨水屏排版组件体系 (Block Components Package)
统一聚合与导出基础文本、容器布局、卡片徽章、图表与数据网格。
"""
from __future__ import annotations

from .context import (
    STATUS_BAR_BOTTOM_DEFAULT,
    RenderContext,
    resolve_named_color,
    resolve_template,
    section_icon_from_label,
    strip_emoji,
)
from .registry import BLOCK_RENDERERS, register_block, render_block
from .measure import measure_block_size, measure_column_blocks_height

# 导入所有组件模块以触发其自注册逻辑
from . import text as _text_module
from . import layout as _layout_module
from . import components as _components_module
from . import charts as _charts_module
from . import grids as _grids_module
from . import decorations as _decorations_module
from . import gauges as _gauges_module
from . import headers_footers as _headers_footers_module
from . import frames as _frames_module
from . import disaster as _disaster_module

from .grids import slice_calendar_rows_around_day

__all__ = [
    "RenderContext",
    "STATUS_BAR_BOTTOM_DEFAULT",
    "BLOCK_RENDERERS",
    "register_block",
    "render_block",
    "measure_block_size",
    "measure_column_blocks_height",
    "slice_calendar_rows_around_day",
    "resolve_template",
    "resolve_named_color",
    "section_icon_from_label",
    "strip_emoji",
]
