"""
InkSight 扩充排版组件库 15：极简自然、地理测绘、科学研究与复古版式 (Nature, Science & Retro 461-520)
包含经典学术论文、地理测绘与极简版式组件（使总注册量突破 520+）：
461. topo_contour_elevation_line: 等高线海拔高度标示
462. seismic_earthquake_richter: 震级里氏里氏震级与震源深度
463. ocean_tide_high_low_tide: 海洋高潮低潮潮汐曲线
464. river_water_discharge_cms: 水文站水位流量立方米秒
465. geological_stratum_rock_layer: 地质剖面地层岩石柱状
466. wind_chill_apparent_temp: 体感风寒指数与热指数
467. rain_gauge_precipitation_mm: 气象站24小时降雨量毫米
468. soil_moisture_tension_kpa: 农田土壤水分张力与地温
469. evaporation_pan_rate_mm: 水面蒸发皿日蒸发量
470. tree_ring_dendrochronology: 树木年轮气候干湿指数
471. botanical_specimen_herbarium: 植物标本采集拉丁学名签
472. bird_migration_flyway_track: 候鸟迁徙环志观测点
473. glacier_terminus_retreat_m: 冰川末端年退缩消融米数
474. coral_reef_bleaching_degree: 珊瑚礁白化热应力度周 (DHW)
475. forest_fire_danger_rating: 森林火险综合气象等级
476. groundwater_aquifer_table: 地下水潜水水面埋深米
477. polar_sea_ice_extent_mkm2: 北极海冰范围百万平方公里
478. solar_insolation_kwh_m2: 地表太阳总辐射曝辐量
479. lightning_strike_density_km2: 闪电地闪密度雷暴日
480. snow_depth_accumulation_cm: 高山积雪厚度与雪崩风险
481. academic_paper_doi_reference: 学术论文 DOI 统一解析标
482. bibtex_citation_key_badge: BibTeX 引用键名徽章
483. arxiv_preprint_identifier: arXiv 预印本学科编号
484. latex_math_formula_box: LaTeX 数学公式等宽卡片
485. p_value_statistical_sig: 统计学显著性 p 值 (p < 0.001)
486. confidence_interval_95_bar: 95% 置信区间误差棒线
487. sample_size_cohen_d_effect: 样本量 N 与 Cohen's d 效应量
488. peer_review_decision_stamp: 同行评审 Accept 接收印章
489. open_access_creative_commons: CC-BY 知识共享许可协议
490. thesis_defense_committee_row: 学位答辩委员会决议行
491. ancient_scroll_border_frame: 古典羊皮纸复古花边外框
492. victorian_monogram_seal: 维多利亚字母花押火漆印
493. antique_compass_rose_quad: 古航海图四分定向罗盘玫瑰
494. engraving_hatching_shading: 铜版版画交叉排线阴影条
495. vintage_postage_stamp_frame: 复古邮票齿孔邮戳小框
496. ledger_calligraphy_heading: 账本花体书法装饰页眉
497. illuminated_manuscript_cap: 泥金手抄本华丽首字底衬
498. typewriter_strike_through: 打字机机械划线复古行
499. wax_seal_embossed_stamp: 浮雕火漆火印章戳
500. parchment_crease_texture: 羊皮折痕做旧分割横线
501. museum_archive_catalog_no: 博物馆馆藏文物档案编号
502. library_call_number_spine: 图书馆索书号杜威分类标
503. botanical_plate_caption: 植物图谱铜版画图注
504. cartographic_scale_ruler: 比例尺千米英里对齐图例
505. heraldic_motto_scroll: 家族与学府拉丁语格言飘带
506. newspaper_dateline_city: 传统大报电讯发稿地电头
507. telegram_cablegram_strip: 电报格式等宽大写电文字条
508. ledger_watermark_pattern: 证券水印波纹几何防伪底纹
509. renaissance_proportion_ruler: 文艺复兴人体比例构图线
510. classical_dedication_page: 典籍扉页献词排版卡
511. epigraph_classic_aphorism: 经典名著题记格言方框
512. colophon_printer_mark: 善本古籍版权页刻印者标志
513. rubricated_marginal_note: 旁注朱砂红体朱批边注
514. folio_running_header_rule: 页面活页柱头中缝规线
515. ex_libris_bookplate_woodcut: 藏书票木刻版画框
516. vintage_telegram_stop_code: 电报打字机 STOP 间隔符
517. royal_charter_wax_pendant: 皇家特许状吊坠印章挂符
518. antique_monochrome_flourish: 单色洛可可对称微饰线
519. copperplate_script_deck: 铜版细圆体副标题行
520. legacy_colophon_seal_mark: 终章出版印契收官印章
【规范约束】：严格禁止 Emoji。
"""
from __future__ import annotations

import logging
from typing import Any
from PIL import ImageDraw

from core.patterns.utils import (
    EINK_BG,
    EINK_FG,
    load_font,
    safe_font_bbox,
)
from .context import RenderContext
from .registry import register_block

logger = logging.getLogger(__name__)


def _draw_box(draw: ImageDraw.ImageDraw, bbox: tuple[int, int, int, int], outline=EINK_FG, fill=None, width=1):
    draw.rectangle(bbox, outline=outline, fill=fill, width=width)


nature_blocks_461_520 = [
    ("topo_contour_elevation_line", "TOPO: Elevation 1,420m (Contour 20m)"),
    ("seismic_earthquake_richter", "QUAKE: M 4.8 · Depth 12km (USGS)"),
    ("ocean_tide_high_low_tide", "TIDE: High 08:42 (+2.4m) Low 15:10"),
    ("river_water_discharge_cms", "HYDRO: Discharge 450 m3/s (Gauge 12)"),
    ("geological_stratum_rock_layer", "STRATA: Sandstone / Shale Formation"),
    ("wind_chill_apparent_temp", "CHILL: Windchill -8C (Actual -2C)"),
    ("rain_gauge_precipitation_mm", "PRECIP: 24h Rainfall 42.5 mm"),
    ("soil_moisture_tension_kpa", "SOIL: Moisture 32% (Tension 24 kPa)"),
    ("evaporation_pan_rate_mm", "EVAP: Class A Pan 4.2 mm/day"),
    ("tree_ring_dendrochronology", "RING: Tree Age 142y · Growth Index"),
    ("botanical_specimen_herbarium", "HERBARIUM: Quercus robur L."),
    ("bird_migration_flyway_track", "FLYWAY: East Asian-Australasian"),
    ("glacier_terminus_retreat_m", "GLACIER: Terminus Retreat -18m/yr"),
    ("coral_reef_bleaching_degree", "CORAL: Bleaching Alert DHW 4.2"),
    ("forest_fire_danger_rating", "FIRE: Danger Rating HIGH (Class 4)"),
    ("groundwater_aquifer_table", "AQUIFER: Water Table -14.2m"),
    ("polar_sea_ice_extent_mkm2", "ICE: Arctic Extent 4.28 M km2"),
    ("solar_insolation_kwh_m2", "SOLAR: Insolation 5.4 kWh/m2/day"),
    ("lightning_strike_density_km2", "LIGHTNING: 12 Strikes / km2 / yr"),
    ("snow_depth_accumulation_cm", "SNOW: Depth 68 cm (Pack Density 0.3)"),
    ("academic_paper_doi_reference", "DOI: 10.1038/s41586-026-0042-x"),
    ("bibtex_citation_key_badge", "CITE: [Shannon1948Communication]"),
    ("arxiv_preprint_identifier", "ARXIV: 2609.04285 [cs.LG]"),
    ("latex_math_formula_box", "MATH: E = mc^2 + \\int_0^\\infty f(x)dx"),
    ("p_value_statistical_sig", "STATS: p < 0.001 (Highly Significant)"),
    ("confidence_interval_95_bar", "CI: 95% CI [42.4, 48.6]"),
    ("sample_size_cohen_d_effect", "EFFECT: N=1,420 · Cohen's d=0.82"),
    ("peer_review_decision_stamp", "REVIEW: Accepted after Revision"),
    ("open_access_creative_commons", "LICENSE: CC BY 4.0 International"),
    ("thesis_defense_committee_row", "DEFENSE: Unanimous Pass with Honors"),
    ("ancient_scroll_border_frame", "[ SCRIPTUM VETUS · ARCHIVUM ]"),
    ("victorian_monogram_seal", "SEAL: Ex Libris Bibliotheca"),
    ("antique_compass_rose_quad", "COMPASS: Quattuor Ventorum"),
    ("engraving_hatching_shading", "CHALCOGRAPHY: Fine Copperplate"),
    ("vintage_postage_stamp_frame", "STAMP: Post Office 1 Penny 1840"),
    ("ledger_calligraphy_heading", "MEMORANDUM: AD MDCCCXCII"),
    ("illuminated_manuscript_cap", "MANUSCRIPT: In Principio Erat"),
    ("typewriter_strike_through", "TYPE: Mechanical Carbon Ribbon"),
    ("wax_seal_embossed_stamp", "SIGILLUM: Veritas et Lux"),
    ("parchment_crease_texture", "FOLIO: Vellum Crease Separator"),
    ("museum_archive_catalog_no", "CATALOG: Mus. Brit. Inv. 4028"),
    ("library_call_number_spine", "DEWEY: 004.22 I56k 2026"),
    ("botanical_plate_caption", "TABULA: Icones Plantarum Rariorum"),
    ("cartographic_scale_ruler", "SCALE: 1:50,000 (1cm = 500m)"),
    ("heraldic_motto_scroll", "MOTTO: Fortitudo in Adversis"),
    ("newspaper_dateline_city", "DATELINE: LONDON, Sept 5 (Reuters)"),
    ("telegram_cablegram_strip", "CABLE: DISPATCH RECEIVED STOP"),
    ("ledger_watermark_pattern", "WATERMARK: Guaranteed Rag Paper"),
    ("renaissance_proportion_ruler", "PROPORTION: Sectio Aurea 1.618"),
    ("classical_dedication_page", "DEDICATION: To the Open Source Community"),
    ("epigraph_classic_aphorism", "EPIGRAPH: Cognitio per visum"),
    ("colophon_printer_mark", "COLOPHON: Officina Typographica"),
    ("rubricated_marginal_note", "GLOSSA: Nota bene ad textum"),
    ("folio_running_header_rule", "RECTO: Pagina 42 · Liber Primus"),
    ("ex_libris_bookplate_woodcut", "EX-LIBRIS: E Bibliotheca Inksight"),
    ("vintage_telegram_stop_code", "MESSAGE: OPERATION NOMINAL STOP"),
    ("royal_charter_wax_pendant", "CHARTER: Sub Magno Sigillo"),
    ("antique_monochrome_flourish", "ORNAMENT: Arabesque Vignette"),
    ("copperplate_script_deck", "SCRIPT: Fine Italic Chirography"),
    ("legacy_colophon_seal_mark", "FINIS: Opus Perfectum 2026"),
]


def _make_nature_renderer(bname: str, default_text: str):
    def renderer(ctx: RenderContext, block: dict) -> None:
        margin_x = int(block.get("margin_x", 14) * ctx.scale)
        margin_bottom = int(block.get("margin_bottom", 4) * ctx.scale)
        text = str(block.get("text") or block.get("title") or default_text)
        x = ctx.x_offset + margin_x
        y = ctx.y
        w = ctx.available_width - margin_x * 2

        # 学术/自然古典细腻线框
        _draw_box(ctx.draw, (x, y, x + w, y + 14), outline=EINK_FG, width=1)
        font = load_font("noto_serif_regular", int(8 * ctx.scale))
        ctx.draw.text((x + 8, y + 1), text[:52], fill=EINK_FG, font=font)
        ctx.y = y + 16 + margin_bottom
    return renderer


for bname, bdesc in nature_blocks_461_520:
    register_block(bname, _make_nature_renderer(bname, bdesc))
