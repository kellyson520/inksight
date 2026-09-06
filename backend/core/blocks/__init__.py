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
from .spec import BlockSpec

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
from . import hotlist as _hotlist_module
from . import monitoring as _monitoring_module
from . import geek_widgets as _geek_widgets_module
from . import pack_data_charts as _pack_charts_module
from . import pack_sysops as _pack_sysops_module
from . import pack_finance as _pack_finance_module
from . import pack_calendar as _pack_calendar_module
from . import pack_health as _pack_health_module
from . import pack_typography as _pack_typography_module
from . import pack_travel as _pack_travel_module
from . import pack_forms_tables as _pack_forms_module
from . import pack_frames as _pack_frames_module
from . import pack_advanced as _pack_advanced_module
from . import pack_icons_tech as _pack_icons_module
from . import pack_space as _pack_space_module
from . import pack_industry as _pack_industry_module
from . import pack_cyber as _pack_cyber_module
from . import pack_nature as _pack_nature_module
from . import qrcode as _qrcode_module

from .grids import slice_calendar_rows_around_day

__all__ = [
    "RenderContext",
    "STATUS_BAR_BOTTOM_DEFAULT",
    "BLOCK_RENDERERS",
    "register_block",
    "render_block",
    "measure_block_size",
    "measure_column_blocks_height",
    "BlockSpec",
    "slice_calendar_rows_around_day",
    "resolve_template",
    "resolve_named_color",
    "section_icon_from_label",
    "strip_emoji",
]
