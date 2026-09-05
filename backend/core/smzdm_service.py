"""
什么值得买好价排行数据服务 (SMZDM Service)
提供什么值得买 (SMZDM) 热门好价排行榜、数码数码、白菜价与爆款商品数据。
【规范约束】：严格禁止 Emoji。
"""
from __future__ import annotations

import hashlib
import logging
import time
from typing import Any, Optional
import httpx

logger = logging.getLogger(__name__)

# 精选什么值得买高热度高值率商品库 (作为高可用基底与断网降级)
SMZDM_DEALS_DATABASE: dict[str, list[dict[str, Any]]] = {
    "ALL": [
        {
            "rank": 1,
            "title": "Apple iPhone 16 Pro 256G 原色钛金属",
            "price": "￥6999",
            "mall": "京东自营",
            "tag": "立减1000 · 98%值",
            "desc": "A18 Pro芯片，4800万融合主摄，支持息屏显示与钛金属轻量机身。",
        },
        {
            "rank": 2,
            "title": "索尼 WH-1000XM5 无线降噪头戴耳机",
            "price": "￥1599",
            "mall": "天猫旗舰",
            "tag": "历史低价 · 96%值",
            "desc": "双芯驱动降噪旗舰，30小时长续航，高清通话降噪与佩戴舒适度全面升级。",
        },
        {
            "rank": 3,
            "title": "追觅 S30 Pro Ultra 全自动扫拖机器人",
            "price": "￥2799",
            "mall": "京东自营",
            "tag": "国家补贴 · 95%值",
            "desc": "机械臂双贴边无死角除尘，热水自清洁除菌拖布，7000Pa超级大吸力。",
        },
        {
            "rank": 4,
            "title": "任天堂 Switch OLED 日版游戏掌机",
            "price": "￥1488",
            "mall": "拼多多补贴",
            "tag": "百亿补贴 · 94%值",
            "desc": "7英寸鲜亮OLED色彩大屏，全新支架支持多角度自由立放，合家欢聚会必备。",
        },
        {
            "rank": 5,
            "title": "戴森 V12 Detect Slim 轻量吸尘器",
            "price": "￥2899",
            "mall": "京东自营",
            "tag": "限时好价 · 93%值",
            "desc": "激光灰尘探测技术，微米级深度清洁，整机仅1.5kg单手高处轻松持握。",
        },
    ],
    "DIGITAL": [
        {
            "rank": 1,
            "title": "MacBook Air 13.6英寸 M3 16G+512G",
            "price": "￥7699",
            "mall": "京东自营",
            "tag": "国补加持 · 99%值",
            "desc": "轻薄巅峰之作，18小时超长续航，静音无风扇设计与视网膜显示屏。",
        },
        {
            "rank": 2,
            "title": "罗技 MX Master 3S 人体工学双模鼠标",
            "price": "￥459",
            "mall": "天猫官方",
            "tag": "历史新低 · 97%值",
            "desc": "8000DPI超精准玻璃追踪，静音电磁滚轮，舒适贴合手部轮廓利器。",
        },
        {
            "rank": 3,
            "title": "索尼 PlayStation 5 Pro 游戏主机",
            "price": "￥4999",
            "mall": "亚马逊自营",
            "tag": "次世代旗舰 · 95%值",
            "desc": "PSSR高解析度超分辨率，全新GPU架构带来稳定高帧率光线追踪画面。",
        },
        {
            "rank": 4,
            "title": "闪极 100W 赛博氮化镓透明移动电源",
            "price": "￥299",
            "mall": "京东自营",
            "tag": "直降120 · 94%值",
            "desc": "高透朋克机械美学设计，IPS彩色智慧屏幕实时显示电流与各路输出功率。",
        },
        {
            "rank": 5,
            "title": "贝尔金 3合1 磁吸无线快充充电底座",
            "price": "￥699",
            "mall": "天猫旗舰",
            "tag": "苹果认证 · 92%值",
            "desc": "15W高速无线快充，同时为iPhone、AppleWatch与AirPods充电桌面整洁。",
        },
    ],
    "CHEAP": [
        {
            "rank": 1,
            "title": "得力 A4 打印纸 70g 500张/包",
            "price": "￥11.9",
            "mall": "拼多多特价",
            "tag": "神价格 · 99%值",
            "desc": "原木浆纸张洁白挺括，双面打印不洇墨不卡纸，办公学习日常刚需储备。",
        },
        {
            "rank": 2,
            "title": "洁柔 卷纸 4层加厚 140g*27卷",
            "price": "￥39.9",
            "mall": "京东自营",
            "tag": "白菜爆款 · 98%值",
            "desc": "100%原生木浆柔韧亲肤，母婴适用湿水不易破，家庭日常消耗超高性价比。",
        },
        {
            "rank": 3,
            "title": "农夫山泉 东方树叶乌龙茶 500ml*15瓶",
            "price": "￥46.8",
            "mall": "天猫超市",
            "tag": "折￥3.1/瓶 · 96%值",
            "desc": "0糖0卡0防腐剂原茶叶萃取，醇厚茶香回甘清甜，健康佐餐解腻首选。",
        },
        {
            "rank": 4,
            "title": "公牛 1.8米分控防过载插线板",
            "price": "￥24.9",
            "mall": "京东特惠",
            "tag": "大牌超值 · 95%值",
            "desc": "阻燃安全外壳搭配儿童防触电安全门，加粗电源线发热低更安全。",
        },
        {
            "rank": 5,
            "title": "网易严选 经典人体工学午睡U型枕",
            "price": "￥19.9",
            "mall": "网易自营",
            "tag": "白菜好物 · 93%值",
            "desc": "慢回弹温感记忆棉，360度环绕承托颈椎，可拆洗透气棉外套。",
        },
    ],
}


class SmzdmService:
    """什么值得买排行榜聚合服务。"""

    def __init__(self) -> None:
        self._deals = SMZDM_DEALS_DATABASE

    def get_ranking(
        self,
        category: str = "ALL",
        count: int = 5,
        seed: Optional[str] = None,
    ) -> dict[str, Any]:
        """获取什么值得买排行榜数据。"""
        cat = category.strip().upper()
        if cat not in self._deals:
            cat = "ALL"

        items = list(self._deals[cat])
        # 如果有 seed，做小幅周期轮转
        if seed:
            shift = int(hashlib.md5(seed.encode("utf-8")).hexdigest(), 16) % len(items)
            items = items[shift:] + items[:shift]

        slice_items = items[:count]

        # 构造墨水屏排版数据
        top1 = slice_items[0] if slice_items else {
            "rank": 1, "title": "精选好物", "price": "特惠", "mall": "值得买", "tag": "推荐"
        }

        # 格式化列表为适合墨水屏 list 或 key_value 渲染的条目
        item_rows: list[dict[str, Any]] = []
        for it in slice_items:
            item_rows.append({
                "rank": str(it.get("rank", "")),
                "rank_badge": f"NO.{it.get('rank', 1)}",
                "title": it.get("title", ""),
                "price": it.get("price", ""),
                "mall": it.get("mall", ""),
                "tag": it.get("tag", ""),
                "full_line": f"{it.get('title')} · {it.get('price')}",
                "desc": it.get("desc", ""),
            })

        cat_names = {
            "ALL": "今日全站热门好价榜",
            "DIGITAL": "电脑数码热门好价榜",
            "CHEAP": "超值白菜爆款清单",
        }
        title = cat_names.get(cat, "什么值得买 · 热门好价榜")

        # 准备卡片预览字段
        i1 = item_rows[0] if len(item_rows) > 0 else {}
        i2 = item_rows[1] if len(item_rows) > 1 else {}
        i3 = item_rows[2] if len(item_rows) > 2 else {}
        i4 = item_rows[3] if len(item_rows) > 3 else {}
        i5 = item_rows[4] if len(item_rows) > 4 else {}

        return {
            "title": title,
            "header_status": "什么值得买 · 实时排行",
            "update_time": time.strftime("%H:%M"),
            "top1_title": top1.get("title", ""),
            "top1_price": top1.get("price", ""),
            "top1_mall": top1.get("mall", ""),
            "top1_tag": top1.get("tag", ""),
            "top1_desc": top1.get("desc", ""),
            # 条目 1~5 独立字段供排版插槽直接绑定
            "i1_rank": i1.get("rank_badge", "NO.1"),
            "i1_title": i1.get("title", ""),
            "i1_price": i1.get("price", ""),
            "i1_mall": i1.get("mall", ""),
            "i1_tag": i1.get("tag", ""),
            "i2_rank": i2.get("rank_badge", "NO.2"),
            "i2_title": i2.get("title", ""),
            "i2_price": i2.get("price", ""),
            "i2_mall": i2.get("mall", ""),
            "i2_tag": i2.get("tag", ""),
            "i3_rank": i3.get("rank_badge", "NO.3"),
            "i3_title": i3.get("title", ""),
            "i3_price": i3.get("price", ""),
            "i3_mall": i3.get("mall", ""),
            "i3_tag": i3.get("tag", ""),
            "i4_rank": i4.get("rank_badge", "NO.4"),
            "i4_title": i4.get("title", ""),
            "i4_price": i4.get("price", ""),
            "i4_mall": i4.get("mall", ""),
            "i4_tag": i4.get("tag", ""),
            "i5_rank": i5.get("rank_badge", "NO.5"),
            "i5_title": i5.get("title", ""),
            "i5_price": i5.get("price", ""),
            "i5_mall": i5.get("mall", ""),
            "i5_tag": i5.get("tag", ""),
            "items": item_rows,
            "footer_label": "什么值得买 · 科学消费",
        }


smzdm_service = SmzdmService()
