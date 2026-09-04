"""
多维数据网格、日历与课表组件模块 (Grids, Calendar & Timetable Blocks)
包含：grid, calendar_grid, timetable_grid 及日历切片算法。
"""
from __future__ import annotations

import logging
from typing import Any

from core.patterns.utils import (
    EINK_BG,
    EINK_FG,
    draw_dashed_line,
    has_cjk,
    load_font,
)
from .context import RenderContext, resolve_named_color
from .registry import register_block
from .text import pick_cjk_font

logger = logging.getLogger(__name__)


def render_grid(ctx: RenderContext, block: dict) -> None:
    """渲染多列键值指标网格，带可选虚线分隔线。"""
    items = block.get("items", [])
    if not items or not isinstance(items, list):
        return

    scale = ctx.scale
    cols = max(1, int(block.get("columns", 2)))
    gap_x = int(block.get("gap_x", block.get("gap", 8)) * scale)
    gap_y = int(block.get("gap_y", block.get("gap", 6)) * scale)
    margin_x = int(block.get("margin_x", 12) * scale)
    margin_bottom = int(block.get("margin_bottom", 8) * scale)
    show_divider = bool(block.get("show_divider", True))

    total_avail_w = ctx.available_width - margin_x * 2
    col_w = (total_avail_w - (cols - 1) * gap_x) // cols
    font_size = int(block.get("font_size", 11) * scale)
    val_size = int(block.get("value_size", 13) * scale)
    font_lbl = load_font("noto_serif_light", font_size)
    font_val = load_font("noto_serif_bold", val_size)

    rows = [items[i:i + cols] for i in range(0, len(items), cols)]
    cur_y = ctx.y

    for r_idx, row in enumerate(rows):
        row_h = font_size + val_size + 8
        for c_idx, cell in enumerate(row):
            cx = ctx.x_offset + margin_x + c_idx * (col_w + gap_x)
            lbl = ctx.resolve(cell.get("label", ""))
            val_f = cell.get("field")
            val = str(ctx.get_field(val_f)) if val_f else str(cell.get("value", ""))
            val = ctx.resolve(val)
            align = cell.get("align", "center")

            lbl_bbox = font_lbl.getbbox(lbl) if lbl else (0, 0, 0, 0)
            lbl_w = lbl_bbox[2] - lbl_bbox[0]
            val_bbox = font_val.getbbox(val) if val else (0, 0, 0, 0)
            val_w = val_bbox[2] - val_bbox[0]

            if align == "center":
                lx = cx + (col_w - lbl_w) // 2
                vx = cx + (col_w - val_w) // 2
            elif align == "right":
                lx = cx + col_w - lbl_w
                vx = cx + col_w - val_w
            else:
                lx = cx
                vx = cx

            ctx.draw.text((lx, cur_y), lbl, fill=EINK_FG, font=font_lbl)
            val_color = ctx.color_index(cell.get("color", "black"), default=EINK_FG)
            ctx.draw.text((vx, cur_y + font_size + 4), val, fill=val_color, font=font_val)

            if show_divider and c_idx < len(row) - 1:
                div_x = cx + col_w + gap_x // 2
                draw_dashed_line(ctx.draw, (div_x, cur_y + 2), (div_x, cur_y + row_h - 2), fill=EINK_FG, width=1)

        cur_y += row_h + gap_y

    ctx.y = cur_y + margin_bottom


def _calendar_cell_day_str(cell: Any) -> str:
    if cell is None:
        return ""
    return str(cell).strip()


def _calendar_row_contains_day(row: Any, day: str) -> bool:
    if not isinstance(row, list):
        return False
    t = str(day).strip()
    if not t:
        return False
    return any(_calendar_cell_day_str(c) == t for c in row)


def _calendar_has_leading_carry_row(norm: list[Any]) -> bool:
    if len(norm) < 2:
        return False
    return not _calendar_row_contains_day(norm[0], "1") and _calendar_row_contains_day(norm[1], "1")


def slice_calendar_rows_around_day(rows: list[Any], today: str, *, max_rows: int) -> list[Any]:
    """返回最多 max_rows 个周行，以确保 today 居中显示。"""
    if max_rows < 1 or not rows:
        return rows
    norm: list[Any] = [r if isinstance(r, list) else [] for r in rows]
    n = len(norm)
    if n <= max_rows:
        return norm[:]
    t = str(today).strip()
    idx: int | None = None
    for i, row in enumerate(norm):
        if _calendar_row_contains_day(row, t):
            idx = i
            break
    if idx is None:
        return norm[:max_rows]
    if idx == 0:
        start = 0
    elif idx >= n - 1:
        start = max(0, n - max_rows)
    elif max_rows == 2 and 2 <= idx < n - 1 and _calendar_has_leading_carry_row(norm):
        start = idx - 1
    else:
        start = idx
    return norm[start : start + max_rows]


def render_calendar_grid(ctx: RenderContext, block: dict) -> None:
    rows_raw = ctx.get_field(block.get("rows_field", "calendar_rows"))
    rows = rows_raw if isinstance(rows_raw, list) else []
    headers = ctx.get_field(block.get("headers_field", "weekday_headers"))
    today = str(ctx.get_field(block.get("today_field", "today_day")))
    day_labels = ctx.get_field(block.get("labels_field", "day_labels")) or {}
    day_label_types = ctx.get_field(block.get("label_types_field", "day_label_types")) or {}
    if not isinstance(rows, list) or not isinstance(headers, list):
        return
    mr_raw = block.get("max_rows")
    if mr_raw is not None:
        try:
            rows = slice_calendar_rows_around_day(rows, today, max_rows=max(1, int(mr_raw)))
        except (TypeError, ValueError):
            pass

    if not isinstance(day_labels, dict):
        day_labels = {}
    if not isinstance(day_label_types, dict):
        day_label_types = {}

    font_size = int(block.get("font_size", 14) * ctx.scale)
    header_font_size = int(block.get("header_font_size", 10) * ctx.scale)
    sub_font_size = max(int(block.get("sub_font_size", 7) * ctx.scale), 6)
    reminder_font_size = max(int(block.get("reminder_font_size", sub_font_size) * ctx.scale), 6)
    font_key = pick_cjk_font(block.get("font", "noto_serif_regular"))
    reminder_font_key = pick_cjk_font(block.get("reminder_font", "noto_serif_light"))
    font = load_font(font_key, font_size)
    header_font = load_font(font_key, header_font_size)
    sub_font = load_font(font_key, sub_font_size)
    reminder_font = load_font(reminder_font_key, reminder_font_size)

    margin_x = int(block.get("margin_x", 12) * ctx.scale)
    cell_h = int(block.get("cell_height", 24) * ctx.scale)
    grid_w = ctx.available_width - margin_x * 2
    cell_w = grid_w // 7
    x0 = ctx.x_offset + margin_x
    weekend_start = int(block.get("weekend_start", 5))
    header_gap = int(block.get("header_gap", 3) * ctx.scale)
    date_line_gap = int(block.get("date_line_gap", 1) * ctx.scale)
    show_day_labels = bool(block.get("show_day_labels", True))
    today_style = str(block.get("today_style", "filled") or "filled")
    today_padding = int(block.get("today_padding", 1) * ctx.scale)

    weekend_color = resolve_named_color(ctx, block.get("weekend_color", "red"), EINK_FG)
    today_bg = resolve_named_color(ctx, block.get("today_fill_color", "red"), EINK_FG)
    today_text_color = resolve_named_color(ctx, block.get("today_text_color"), EINK_BG)
    reminder_color = resolve_named_color(ctx, block.get("reminder_color", "yellow"), EINK_FG)
    festival_color = resolve_named_color(ctx, block.get("festival_color", "red"), EINK_FG)

    for ci, hdr in enumerate(headers[:7]):
        cx = x0 + ci * cell_w + cell_w // 2
        bbox = header_font.getbbox(hdr)
        tw = bbox[2] - bbox[0]
        color = weekend_color if ci >= weekend_start else EINK_FG
        ctx.draw.text((cx - tw // 2, ctx.y), hdr, fill=color, font=header_font)
    ctx.y += header_font_size + header_gap

    date_line_h = font_size + date_line_gap

    for row in rows:
        if not isinstance(row, list):
            continue
        if ctx.y + cell_h > ctx.footer_top - 10:
            break
        for ci, day_str in enumerate(row[:7]):
            ds = _calendar_cell_day_str(day_str)
            if not ds:
                continue
            cx = x0 + ci * cell_w + cell_w // 2
            bbox = font.getbbox(ds)
            tw = bbox[2] - bbox[0]
            th = bbox[3] - bbox[1]
            tx = cx - tw // 2
            ty = ctx.y

            if ds == str(today).strip():
                r = max(tw, th) // 2 + today_padding
                cy = ty + th // 2 + int(2 * ctx.scale)
                ec = (cx - r, cy - r, cx + r, cy + r)
                if today_style == "outline":
                    ctx.draw.ellipse(ec, outline=today_bg, width=1)
                elif today_style == "none":
                    pass
                else:
                    ctx.draw.ellipse(ec, fill=today_bg)
                ctx.draw.text((tx, ty), ds, fill=today_text_color if today_style != "none" else EINK_FG, font=font)
            else:
                color = weekend_color if ci >= weekend_start else EINK_FG
                ctx.draw.text((tx, ty), ds, fill=color, font=font)

            sub = day_labels.get(ds, "")
            if show_day_labels and sub:
                lt = day_label_types.get(ds, "lunar")
                label_font = reminder_font if lt == "reminder" else sub_font
                sb = label_font.getbbox(sub)
                sw = sb[2] - sb[0]
                sx = cx - sw // 2
                sy = ty + date_line_h
                if lt == "reminder":
                    sub_color = reminder_color
                elif lt in ("festival", "solar_term"):
                    sub_color = festival_color
                else:
                    sub_color = EINK_FG
                ctx.draw.text((sx, sy), sub, fill=sub_color, font=label_font)
        ctx.y += cell_h


def _fit_text(text: str, font: Any, max_w: int) -> tuple[str, str]:
    if font.getlength(text) <= max_w:
        return text, ""
    for i in range(len(text), 0, -1):
        if font.getlength(text[:i]) <= max_w:
            return text[:i], text[i:]
    return "", text


def _draw_two_line_cell(
    ctx: RenderContext, cx: int, cy: int, col_w: int, row_h: int,
    name: str, loc: str, font_key: str, base_size: int,
    text_color: int, loc_color: int,
) -> None:
    max_w = col_w - 4
    f = load_font(font_key, base_size)
    sf = load_font(font_key, max(8, base_size - 2))
    sub_sz = max(8, base_size - 2)
    line_h = base_size + 1

    line1, remainder = _fit_text(name, f, max_w)
    if not remainder:
        loc_disp, _ = _fit_text(loc, sf, max_w)
        total_h = line_h + sub_sz
        ny = cy + (row_h - total_h) // 2
        nb = f.getbbox(line1); nw = nb[2] - nb[0]
        ctx.draw.text((cx + (col_w - nw) // 2, ny), line1, fill=text_color, font=f)
        lb = sf.getbbox(loc_disp); lw = lb[2] - lb[0]
        ctx.draw.text((cx + (col_w - lw) // 2, ny + line_h), loc_disp, fill=loc_color, font=sf)
        return

    line2, leftover = _fit_text(remainder, sf, max_w)
    if leftover:
        line2 = line2[: max(0, len(line2) - len(leftover))] + leftover if not line2 else line2
    loc_disp, _ = _fit_text(loc, sf, max_w)

    total_h = line_h + sub_sz + sub_sz
    ny = cy + (row_h - total_h) // 2

    nb = f.getbbox(line1); nw = nb[2] - nb[0]
    ctx.draw.text((cx + (col_w - nw) // 2, ny), line1, fill=text_color, font=f)

    l2b = sf.getbbox(line2); l2w = l2b[2] - l2b[0]
    ctx.draw.text((cx + (col_w - l2w) // 2, ny + line_h), line2, fill=text_color, font=sf)

    lb = sf.getbbox(loc_disp); lw = lb[2] - lb[0]
    ctx.draw.text((cx + (col_w - lw) // 2, ny + line_h + sub_sz), loc_disp, fill=loc_color, font=sf)


def _draw_single_line_cell(
    ctx: RenderContext, cx: int, cy: int, col_w: int, row_h: int,
    text: str, font_key: str, base_size: int, text_color: int,
) -> None:
    f = load_font(font_key, base_size)
    disp, _ = _fit_text(text, f, col_w - 4)
    tb = f.getbbox(disp)
    tw = tb[2] - tb[0]
    ctx.draw.text((cx + (col_w - tw) // 2, cy + (row_h - base_size) // 2), disp, fill=text_color, font=f)


def _render_timetable_daily(ctx: RenderContext, block: dict) -> None:
    slots = ctx.get_field(block.get("field", "slots"))
    if not isinstance(slots, list):
        return

    raw_font_size = float(block.get("font_size", 11))
    raw_loc_font_size = float(block.get("location_font_size", max(8, raw_font_size - 2)))
    font_size = int(raw_font_size * ctx.scale)
    loc_font_size = int(raw_loc_font_size * ctx.scale)
    font_key = pick_cjk_font(block.get("font", "noto_serif_regular"))
    font = load_font(font_key, font_size)
    small_font = load_font(font_key, max(8, loc_font_size))

    margin_x = int(block.get("margin_x", 12) * ctx.scale)
    row_h = int(block.get("row_height", 28) * ctx.scale)
    grid_w = ctx.available_width - margin_x * 2
    time_col_ratio = float(block.get("time_col_ratio", 0.22))
    time_col_w = int(grid_w * time_col_ratio)
    x0 = ctx.x_offset + margin_x

    highlight_color = resolve_named_color(ctx, block.get("highlight_color", "red"), EINK_FG)
    accent_color = resolve_named_color(ctx, block.get("accent_color", "yellow"), EINK_FG)
    current_text_color = resolve_named_color(ctx, block.get("current_text_color"), EINK_BG)
    show_location = bool(block.get("show_location", True))
    show_separator = bool(block.get("show_separator", True))
    time_field = str(block.get("time_field", "time"))
    name_field = str(block.get("name_field", "name"))
    location_field = str(block.get("location_field", "location"))
    current_field = str(block.get("current_field", "current"))

    for i, slot in enumerate(slots):
        if not isinstance(slot, dict):
            continue
        if ctx.y + row_h > ctx.footer_top - 10:
            break

        time_str = str(slot.get(time_field, ""))
        name = str(slot.get(name_field, ""))
        is_current = slot.get(current_field, False)
        loc = str(slot.get(location_field, ""))

        if is_current:
            ctx.draw.rectangle(
                [x0, ctx.y, x0 + grid_w, ctx.y + row_h - 1],
                fill=highlight_color if ctx.colors >= 3 else EINK_FG,
            )
            text_color = current_text_color
        else:
            text_color = EINK_FG

        ctx.draw.text((x0 + 2, ctx.y + 4), time_str, fill=text_color, font=small_font)
        ctx.draw.text((x0 + time_col_w, ctx.y + 2), name, fill=text_color, font=font)
        if show_location and loc:
            loc_color = current_text_color if is_current and ctx.colors >= 3 else accent_color
            ctx.draw.text((x0 + time_col_w, ctx.y + font_size + 3), loc, fill=loc_color, font=small_font)

        ctx.y += row_h

        if show_separator and i < len(slots) - 1:
            ctx.draw.line([(x0, ctx.y - 1), (x0 + grid_w, ctx.y - 1)], fill=EINK_FG, width=1)


def _render_timetable_weekly(ctx: RenderContext, block: dict) -> None:
    periods = ctx.get_field(block.get("periods_field", "periods"))
    grid = ctx.get_field(block.get("grid_field", "grid"))
    weekdays = ctx.get_field(block.get("weekdays_field", "weekdays")) or ["一", "二", "三", "四", "五"]
    current_day = ctx.get_field(block.get("current_day_field", "current_day"))
    current_period = ctx.get_field(block.get("current_period_field", "current_period"))
    if not isinstance(periods, list) or not isinstance(grid, list):
        return
    if not isinstance(current_day, int):
        current_day = -1
    if not isinstance(current_period, int):
        current_period = -1

    font_size = int(block.get("font_size", 11) * ctx.scale)
    header_font_size = int(block.get("header_font_size", font_size) * ctx.scale) if block.get("header_font_size") else font_size
    font_key = pick_cjk_font(block.get("font", "noto_serif_regular"))
    font = load_font(font_key, font_size)
    sub_font = load_font(font_key, max(8, font_size - 2))
    header_font = load_font(font_key, header_font_size)
    period_font = load_font(font_key, max(8, font_size - 2))

    margin_x = int(block.get("margin_x", 8) * ctx.scale)
    grid_w = ctx.available_width - margin_x * 2
    x0 = ctx.x_offset + margin_x

    has_time_range = any("-" in p and ":" in p for p in periods)
    time_col_ratio = float(block.get("time_col_ratio", 0.22 if has_time_range else 0.14))

    n_periods = len(periods)
    header_h = int(block.get("header_height", 16) * ctx.scale)
    avail_h = ctx.footer_top - ctx.y - header_h - int(4 * ctx.scale)
    requested_row_height = block.get("row_height")
    if requested_row_height is not None:
        row_h = int(requested_row_height * ctx.scale)
    else:
        row_h = max(int(16 * ctx.scale), avail_h // max(n_periods, 1))

    time_col_w = int(grid_w * time_col_ratio)
    day_count = max(1, len(weekdays))
    day_col_w = (grid_w - time_col_w) // day_count

    highlight_color = resolve_named_color(ctx, block.get("highlight_color", "red"), EINK_FG)
    accent_color = resolve_named_color(ctx, block.get("accent_color", "yellow"), EINK_FG)
    current_text_color = resolve_named_color(ctx, block.get("current_text_color"), EINK_BG)
    today_header_color = resolve_named_color(ctx, block.get("today_header_color", "red"), EINK_FG)
    show_location = bool(block.get("show_location", True))

    for d_idx, day_name in enumerate(weekdays):
        col_x = x0 + time_col_w + d_idx * day_col_w
        is_today = d_idx == current_day
        hdr_color = today_header_color if is_today else EINK_FG
        hdr_font = font if is_today else header_font
        tb = hdr_font.getbbox(str(day_name))
        tw = tb[2] - tb[0]
        ctx.draw.text((col_x + (day_col_w - tw) // 2, ctx.y), str(day_name), fill=hdr_color, font=hdr_font)

    ctx.y += header_h
    ctx.draw.line([(x0, ctx.y), (x0 + grid_w, ctx.y)], fill=EINK_FG, width=1)

    for p_idx, period_label in enumerate(periods):
        if ctx.y + row_h > ctx.footer_top:
            break
        p_str = str(period_label)
        if "-" in p_str and ":" in p_str:
            lines = p_str.split("-", 1)
            f_sz = max(7, font_size - 3)
            pf = load_font(font_key, f_sz)
            ctx.draw.text((x0 + 1, ctx.y + 1), lines[0].strip(), fill=EINK_FG, font=pf)
            ctx.draw.text((x0 + 1, ctx.y + f_sz + 2), lines[1].strip(), fill=EINK_FG, font=pf)
        else:
            pb = period_font.getbbox(p_str)
            pw = pb[2] - pb[0]
            ctx.draw.text((x0 + (time_col_w - pw) // 2, ctx.y + (row_h - font_size) // 2), p_str, fill=EINK_FG, font=period_font)

        ctx.draw.line([(x0 + time_col_w, ctx.y), (x0 + time_col_w, ctx.y + row_h)], fill=EINK_FG, width=1)
        grid_row = grid[p_idx] if p_idx < len(grid) and isinstance(grid[p_idx], list) else []

        for d_idx in range(day_count):
            cell_x = x0 + time_col_w + d_idx * day_col_w
            cell_text = str(grid_row[d_idx]) if d_idx < len(grid_row) and grid_row[d_idx] else ""
            is_cur = d_idx == current_day and p_idx == current_period

            if is_cur:
                ctx.draw.rectangle(
                    [cell_x + 1, ctx.y + 1, cell_x + day_col_w - 1, ctx.y + row_h - 1],
                    fill=highlight_color if ctx.colors >= 3 else EINK_FG,
                )
                text_color = current_text_color
            else:
                text_color = EINK_FG

            if cell_text:
                if show_location and "/" in cell_text:
                    full_name, loc_part = cell_text.split("/", 1)
                    _draw_two_line_cell(
                        ctx, cell_x, ctx.y, day_col_w, row_h,
                        full_name, loc_part, font_key, font_size,
                        text_color, current_text_color if text_color == current_text_color else accent_color,
                    )
                else:
                    _draw_single_line_cell(
                        ctx, cell_x, ctx.y, day_col_w, row_h,
                        cell_text, font_key, font_size, text_color,
                    )

        ctx.y += row_h


def render_timetable_grid(ctx: RenderContext, block: dict) -> None:
    style = str(ctx.get_field("style") or "daily")
    if style == "weekly":
        _render_timetable_weekly(ctx, block)
    else:
        _render_timetable_daily(ctx, block)


# 注册所有网格与时间表类组件
register_block("grid", render_grid)
register_block("calendar_grid", render_calendar_grid)
register_block("timetable_grid", render_timetable_grid)
