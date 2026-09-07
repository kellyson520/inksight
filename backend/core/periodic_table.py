"""
InkSight 元素周期表·每日一素核心服务 (Periodic Table Element of the Day)
提供 118 种化学元素的标准原子结构、中英文名、物理分类、历史发现与硬核科学趣闻。
支持基于日期的每日轮播与指定原子序数查询。
"""
from __future__ import annotations

import datetime
from typing import Any

# 精选标准元素数据集 (原子序数 1 ~ 86 及超重典型元素)
_RAW_ELEMENTS: list[dict[str, Any]] = [
    {
        "num": 1, "sym": "H", "zh": "氢", "en": "Hydrogen", "mass": "1.008",
        "cat": "反应性非金属", "period": 1, "group": 1, "config": "1s¹",
        "phase": "气态", "discoverer": "亨利·卡文迪许 (1766)",
        "summary": "宇宙中丰度最高、质量最轻的基础元素，恒星核聚变的主要燃料，孕育水与有机生命的源泉。",
        "fun_fact": "木星质量的 75% 都是氢。在极高压下，氢甚至能呈现出具有超导特性的金属形态。"
    },
    {
        "num": 2, "sym": "He", "zh": "氦", "en": "Helium", "mass": "4.0026",
        "cat": "稀有气体", "period": 1, "group": 18, "config": "1s²",
        "phase": "气态", "discoverer": "皮埃尔·让森 (1868)",
        "summary": "宇宙中第二丰富的元素，化学性质极其钝化，沸点仅有 4.22K，是超导磁体冷却的核心介质。",
        "fun_fact": "氦是唯一在太阳光谱中被人类首次发现、随后才在地球矿物中寻得踪迹的元素。"
    },
    {
        "num": 3, "sym": "Li", "zh": "锂", "en": "Lithium", "mass": "6.94",
        "cat": "碱金属", "period": 2, "group": 1, "config": "[He] 2s¹",
        "phase": "固态", "discoverer": "约翰·奥古斯特·阿尔费德森 (1817)",
        "summary": "密度最小的金属元素，现代二次电池与移动计算时代的能量核心，被誉为白色石油。",
        "fun_fact": "金属锂极轻，甚至可以浮在煤油上。它不仅驱动着电动车，也曾作为经典情绪稳定剂被用于医药。"
    },
    {
        "num": 4, "sym": "Be", "zh": "铍", "en": "Beryllium", "mass": "9.0122",
        "cat": "碱土金属", "period": 2, "group": 2, "config": "[He] 2s²",
        "phase": "固态", "discoverer": "路易·沃克兰 (1798)",
        "summary": "极轻且具备极高声速与刚度的金属，X 射线几乎完全穿透，航天与高能物理的首选透镜材料。",
        "fun_fact": "詹姆斯·韦伯太空望远镜的 18 面镀金主镜全部由铍制成，以确保在深空接近绝对零度下依然不形变。"
    },
    {
        "num": 5, "sym": "B", "zh": "硼", "en": "Boron", "mass": "10.81",
        "cat": "类金属", "period": 2, "group": 13, "config": "[He] 2s² 2p¹",
        "phase": "固态", "discoverer": "约瑟夫·路易·盖-吕萨克 (1808)",
        "summary": "自然界硬度仅次于金刚石的超硬材料基石，耐热硼硅玻璃与核反应堆中子吸收棒的核心组分。",
        "fun_fact": "燃烧的硼化合物会产生纯净翠绿色的火焰，烟花中亮丽的绿光正是硼的焰色反应。"
    },
    {
        "num": 6, "sym": "C", "zh": "碳", "en": "Carbon", "mass": "12.011",
        "cat": "反应性非金属", "period": 2, "group": 14, "config": "[He] 2s² 2p²",
        "phase": "固态", "discoverer": "古代已知",
        "summary": "有机化学与已知生命的绝对基石。既能构成柔软导电的石墨，也能形成自然界最硬的金刚石。",
        "fun_fact": "碳原子拥有无与伦比的自成键能力，已知含碳化合物超过数千万种，构成了地球整个生命世界的物质基础。"
    },
    {
        "num": 7, "sym": "N", "zh": "氮", "en": "Nitrogen", "mass": "14.007",
        "cat": "反应性非金属", "period": 2, "group": 15, "config": "[He] 2s² 2p³",
        "phase": "气态", "discoverer": "丹尼尔·卢瑟福 (1772)",
        "summary": "占地球大气体积 78% 的主导气体，蛋白质与核酸的必备元素。常温下极稳定，高温下可成剧毒或强爆炸物。",
        "fun_fact": "工业合成氨（哈伯法）将大气中的氮气转化为肥料，直接养活了如今地球上半数以上的人口。"
    },
    {
        "num": 8, "sym": "O", "zh": "氧", "en": "Oxygen", "mass": "15.999",
        "cat": "反应性非金属", "period": 2, "group": 16, "config": "[He] 2s² 2p⁴",
        "phase": "气态", "discoverer": "卡尔·威廉·舍勒 / 约瑟夫·普利斯特里 (1774)",
        "summary": "地壳中质量占比最高的元素，好氧生物呼吸与有氧代谢的必需氧化剂，臭氧层阻挡致命紫外线。",
        "fun_fact": "液态氧和固态氧其实具有淡淡的天蓝色，并且具有强顺磁性，能被磁铁的两极吸住悬空。"
    },
    {
        "num": 9, "sym": "F", "zh": "氟", "en": "Fluorine", "mass": "18.998",
        "cat": "卤素", "period": 2, "group": 17, "config": "[He] 2s² 2p⁵",
        "phase": "气态", "discoverer": "亨利·莫瓦桑 (1886)",
        "summary": "化学性质最活泼、电负性最强的元素。几乎能氧化除轻质稀有气体外的所有单质，连水也能在其中燃烧。",
        "fun_fact": "氟是化学史上最危险的恶魔元素，莫瓦桑因在经历数次中毒爆炸后成功制得单质氟而荣获诺贝尔奖。"
    },
    {
        "num": 10, "sym": "Ne", "zh": "氖", "en": "Neon", "mass": "20.180",
        "cat": "稀有气体", "period": 2, "group": 18, "config": "[He] 2s² 2p⁶",
        "phase": "气态", "discoverer": "威廉·拉姆齐 (1898)",
        "summary": "辉光放电时呈现标志性赤橙红光的稀有气体，霓虹灯的始祖，航天与深低温激光工程的关键气体。",
        "fun_fact": "真正的霓虹灯（Neon）只发出红橙色光，街道上其他蓝、绿等五彩缤纷的灯光其实是填充了氩气或荧光涂层。"
    },
    {
        "num": 11, "sym": "Na", "zh": "钠", "en": "Sodium", "mass": "22.990",
        "cat": "碱金属", "period": 3, "group": 1, "config": "[Ne] 3s¹",
        "phase": "固态", "discoverer": "汉弗里·戴维 (1807)",
        "summary": "柔软的银白金属，遇水剧烈反应并释放氢气。其离子形式是维持细胞外液渗透压与神经电信号传导的关键。",
        "fun_fact": "食盐中的氯化钠是生命不可或缺的矿物质，但单质钠和单质氯气各自都是极度危险的强腐蚀品。"
    },
    {
        "num": 12, "sym": "Mg", "zh": "镁", "en": "Magnesium", "mass": "24.305",
        "cat": "碱土金属", "period": 3, "group": 2, "config": "[Ne] 3s²",
        "phase": "固态", "discoverer": "汉弗里·戴维 (1808)",
        "summary": "结构最轻的工程金属材料之一，叶绿素分子的核心催化中心，支撑地球所有光合作用运转。",
        "fun_fact": "镁带在空气中燃烧能发出炫目的耀眼白光，早期照相馆使用的闪光粉就是细微镁粉与氧化剂的混合物。"
    },
    {
        "num": 13, "sym": "Al", "zh": "铝", "en": "Aluminium", "mass": "26.982",
        "cat": "后过渡金属", "period": 3, "group": 13, "config": "[Ne] 3s² 3p¹",
        "phase": "固态", "discoverer": "汉斯·奥斯特 (1825)",
        "summary": "地壳中丰度最高的金属元素。自发形成致密氧化铝保护膜，现代航空航天与轻量化工业的骨架。",
        "fun_fact": "19 世纪中叶电解法发明前，铝比黄金还要昂贵。拿破仑三世招待最尊贵的宾客时才使用铝制餐具。"
    },
    {
        "num": 14, "sym": "Si", "zh": "硅", "en": "Silicon", "mass": "28.085",
        "cat": "类金属", "period": 3, "group": 14, "config": "[Ne] 3s² 3p²",
        "phase": "固态", "discoverer": "永斯·雅各布·贝尔塞柳斯 (1824)",
        "summary": "半导体产业与整个现代微电子信息文明的物理地基，地壳中丰度仅次于氧的第二大元素。",
        "fun_fact": "高纯度单晶硅的纯度要求达到 99.9999999%（9个9以上），相当于几十个足球场沙滩上不能有第二粒异物。"
    },
    {
        "num": 15, "sym": "P", "zh": "磷", "en": "Phosphorus", "mass": "30.974",
        "cat": "反应性非金属", "period": 3, "group": 15, "config": "[Ne] 3s² 3p³",
        "phase": "固态", "discoverer": "亨尼格·布兰德 (1669)",
        "summary": "DNA/RNA 骨架与细胞能量货币 ATP 的不可或缺构成物，农业三要素（氮磷钾）核心养分。",
        "fun_fact": "炼金术士布兰德在试图通过蒸馏尿液寻找魔法石时偶然分离出了白磷，发现它在黑暗中居然自发发光。"
    },
    {
        "num": 16, "sym": "S", "zh": "硫", "en": "Sulfur", "mass": "32.06",
        "cat": "反应性非金属", "period": 3, "group": 16, "config": "[Ne] 3s² 3p⁴",
        "phase": "固态", "discoverer": "古代已知",
        "summary": "亮黄色晶体，火药与现代化工之母硫酸的核心来源，在蛋白质二硫键折叠中起决定性稳固作用。",
        "fun_fact": "纯硫黄本身没有任何气味。火山喷发与臭鸡蛋闻到的刺鼻恶臭其实是硫化氢或二氧化硫气体的气味。"
    },
    {
        "num": 17, "sym": "Cl", "zh": "氯", "en": "Chlorine", "mass": "35.45",
        "cat": "卤素", "period": 3, "group": 17, "config": "[Ne] 3s² 3p⁵",
        "phase": "气态", "discoverer": "卡尔·威廉·舍勒 (1774)",
        "summary": "黄绿色有毒窒息性气体，强氧化性广泛用于自来水消毒灭菌与塑料（PVC）合成。",
        "fun_fact": "自来水加氯消毒是现代公共卫生史上挽救生命最多的发明之一，使霍乱和伤寒在自来水普及区绝迹。"
    },
    {
        "num": 18, "sym": "Ar", "zh": "氩", "en": "Argon", "mass": "39.948",
        "cat": "稀有气体", "period": 3, "group": 18, "config": "[Ne] 3s² 3p⁶",
        "phase": "气态", "discoverer": "瑞利男爵 / 威廉·拉姆齐 (1894)",
        "summary": "地球大气中第三大成分（约占 0.93%），焊接高活性金属时最常用的工业保护气氛。",
        "fun_fact": "因为名字源自希腊语“懒惰（Argos）”，氩被用来灌充白炽灯泡防止钨丝升华，默默陪伴了人类一个世纪的黑夜。"
    },
    {
        "num": 19, "sym": "K", "zh": "钾", "en": "Potassium", "mass": "39.098",
        "cat": "碱金属", "period": 4, "group": 1, "config": "[Ar] 4s¹",
        "phase": "固态", "discoverer": "汉弗里·戴维 (1807)",
        "summary": "极活泼的金属单质，细胞内液关键阳离子，与细胞外的钠共同维持心肌收缩与动作电位兴奋。",
        "fun_fact": "一根普通的香蕉天然富含放射性同位素钾-40，因此在辐射物理学中甚至有“香蕉等效剂量（BED）”的比喻。"
    },
    {
        "num": 20, "sym": "Ca", "zh": "钙", "en": "Calcium", "mass": "40.078",
        "cat": "碱土金属", "period": 4, "group": 2, "config": "[Ar] 4s²",
        "phase": "固态", "discoverer": "汉弗里·戴维 (1808)",
        "summary": "人体内最丰富的矿物质，骨骼、牙齿与珊瑚贝壳的主要结构基石，也是细胞信号转导的核心第二信使。",
        "fun_fact": "心脏每一次强有力的跳动，本质上都是微量钙离子在心肌肌浆网内外高速穿梭释放的电化学产物。"
    },
    {
        "num": 22, "sym": "Ti", "zh": "钛", "en": "Titanium", "mass": "47.867",
        "cat": "过渡金属", "period": 4, "group": 4, "config": "[Ar] 3d² 4s²",
        "phase": "固态", "discoverer": "威廉·格雷戈尔 (1791)",
        "summary": "强度重量比极高且具有卓越耐海水腐蚀性与人体生物相容性的太空金属，人工关节与航天器理想材质。",
        "fun_fact": "钛能与人体骨骼细胞直接紧密生长并结合在一起（骨整合现象），使它成为最完美的医用种植牙牙根。"
    },
    {
        "num": 26, "sym": "Fe", "zh": "铁", "en": "Iron", "mass": "55.845",
        "cat": "过渡金属", "period": 4, "group": 8, "config": "[Ar] 3d⁶ 4s²",
        "phase": "固态", "discoverer": "古代已知",
        "summary": "地壳中最丰富的过渡金属元素，是血红蛋白的核心载体，也是人类工业与建筑文明的基石。",
        "fun_fact": "铁-56 是全宇宙核结合能最高、最稳定的核素之一。大质量恒星演化到了聚变产生铁阶段就走到了生命尽头。"
    },
    {
        "num": 29, "sym": "Cu", "zh": "铜", "en": "Copper", "mass": "63.546",
        "cat": "过渡金属", "period": 4, "group": 11, "config": "[Ar] 3d¹⁰ 4s¹",
        "phase": "固态", "discoverer": "古代已知 (约公元前 9000 年)",
        "summary": "人类最早开采利用的金属之一，导电性与导热性仅次于银，构建了全球电力网络与高保真音频线缆。",
        "fun_fact": "自由态铜离子具有极强的自杀式触杀抑菌特性（微动力效应），铜表面能在数小时内杀灭绝大多数附着细菌。"
    },
    {
        "num": 47, "sym": "Ag", "zh": "银", "en": "Silver", "mass": "107.87",
        "cat": "过渡金属", "period": 5, "group": 11, "config": "[Kr] 4d¹⁰ 5s¹",
        "phase": "固态", "discoverer": "古代已知",
        "summary": "所有单质中电导率、热导率与光学反射率最高的金属，既是历史货币载体，也是光伏导电银浆核心原料。",
        "fun_fact": "银镜反应是人类制作镜子的核心工艺，高纯度银反射所有可见光波长的反射率超过 99%。"
    },
    {
        "num": 79, "sym": "Au", "zh": "金", "en": "Gold", "mass": "196.97",
        "cat": "过渡金属", "period": 6, "group": 11, "config": "[Xe] 4f¹⁴ 5d¹⁰ 6s¹",
        "phase": "固态", "discoverer": "古代已知",
        "summary": "延展性最强、抗腐蚀性顶级的贵金属。1 克金即可拉成 2 公里长的细丝，千年来作为全球财富通用硬通货。",
        "fun_fact": "黄金的独特黄色并非传统吸收光谱所致，而是爱因斯坦相对论效应导致其内层电子运动速度接近光速的宏观显现。"
    },
    {
        "num": 92, "sym": "U", "zh": "铀", "en": "Uranium", "mass": "238.03",
        "cat": "锕系元素", "period": 7, "group": 3, "config": "[Rn] 5f³ 6d¹ 7s²",
        "phase": "固态", "discoverer": "马丁·克拉普罗特 (1789)",
        "summary": "自然界存在的最重原生核素，核裂变释放巨大能量，商用核电站与原子能时代的关键支柱。",
        "fun_fact": "一小颗指甲盖大小的微浓缩二氧化铀陶瓷燃料芯块，所蕴含的能量相当于整整一吨高品质煤炭。"
    },
    {
        "num": 21, "sym": "Sc", "zh": "钪", "en": "Scandium", "mass": "44.956",
        "cat": "过渡金属", "period": 4, "group": 3, "config": "[Ar] 3d¹ 4s²",
        "phase": "固态", "discoverer": "拉尔斯·尼尔森 (1879)",
        "summary": "稀土元素家族成员，微量钪加入铝合金即可显著细化晶粒并大幅提升焊接抗疲劳强度。",
        "fun_fact": "顶级棒球棒与航空航天特种铝钪合金骨架中，只需加入 0.1%~0.5% 的钪就能使强度翻倍。"
    },
    {
        "num": 23, "sym": "V", "zh": "钒", "en": "Vanadium", "mass": "50.942",
        "cat": "过渡金属", "period": 4, "group": 5, "config": "[Ar] 3d³ 4s²",
        "phase": "固态", "discoverer": "安德烈斯·德尔里奥 (1801)",
        "summary": "现代特种合金钢的“维生素”，不仅提高钢材耐磨耐冲击力，其多价态还是全钒液流长时储能电池的核心。",
        "fun_fact": "福特著名的 T 型车底盘采用了钒钢制造，使其在当年泥泞颠簸的美国土路上具备惊人的韧性与寿命。"
    },
    {
        "num": 24, "sym": "Cr", "zh": "铬", "en": "Chromium", "mass": "51.996",
        "cat": "过渡金属", "period": 4, "group": 6, "config": "[Ar] 3d⁵ 4s¹",
        "phase": "固态", "discoverer": "路易·沃克兰 (1797)",
        "summary": "自然界最硬的金属元素（莫氏硬度 8.5），不锈钢之所以“不锈”完全依赖其表面纳秒级自修复的氧化铬钝化膜。",
        "fun_fact": "铬的名字源于希腊语“颜色（Chroma）”，因为其化合物涵盖翠绿、明黄、赤红等极其艳丽丰富的色彩。"
    },
    {
        "num": 25, "sym": "Mn", "zh": "锰", "en": "Manganese", "mass": "54.938",
        "cat": "过渡金属", "period": 4, "group": 7, "config": "[Ar] 3d⁵ 4s²",
        "phase": "固态", "discoverer": "约翰·戈特利布·甘恩 (1774)",
        "summary": "冶金炼钢不可或缺的脱氧脱硫剂，也是植物光反应中心光解水产氧放氧复合物的核心金属催化簇。",
        "fun_fact": "深海数千米海底广泛分布着如土豆般大小的“富锰结核”，总储量高达万亿吨，是人类未来的重要矿产宝库。"
    },
    {
        "num": 27, "sym": "Co", "zh": "钴", "en": "Cobalt", "mass": "58.933",
        "cat": "过渡金属", "period": 4, "group": 9, "config": "[Ar] 3d⁷ 4s²",
        "phase": "固态", "discoverer": "乔治·布兰特 (1735)",
        "summary": "高能量密度三元锂电池（NCM）正极与耐高温航空涡轮叶片核心元素，维生素 B12 唯一的金属中心。",
        "fun_fact": "景德镇青花瓷流传千古的标志性幽蓝发色剂“苏麻离青”，化学本质就是天然富钴铁矿颜料。"
    },
    {
        "num": 28, "sym": "Ni", "zh": "镍", "en": "Nickel", "mass": "58.693",
        "cat": "过渡金属", "period": 4, "group": 10, "config": "[Ar] 3d⁸ 4s²",
        "phase": "固态", "discoverer": "阿克塞尔·克朗斯泰特 (1751)",
        "summary": "抗腐蚀与耐极温能力卓越，是动力电池高镍正极、不锈钢与耐热超级合金的核心骨架。",
        "fun_fact": "地球地核不仅有铁，第二大主要成分就是重达千亿亿吨的高温高压液态与固态金属镍。"
    },
    {
        "num": 30, "sym": "Zn", "zh": "锌", "en": "Zinc", "mass": "65.38",
        "cat": "过渡金属", "period": 4, "group": 12, "config": "[Ar] 3d¹⁰ 4s²",
        "phase": "固态", "discoverer": "古代已知 (印度与中国早期规模化蒸馏)",
        "summary": "钢铁镀锌防腐守护者，人体内百余种酶（如碳酸酐酶、DNA 聚合酶）的催化活性中枢，被誉为生命之花。",
        "fun_fact": "牺牲阳极保护法：在轮船钢铁船底贴上金属锌块，锌会主动代替钢铁被海水腐蚀氧化，默默保护船体完好。"
    },
    {
        "num": 31, "sym": "Ga", "zh": "镓", "en": "Gallium", "mass": "69.723",
        "cat": "后过渡金属", "period": 4, "group": 13, "config": "[Ar] 3d¹⁰ 4s² 4p¹",
        "phase": "固态", "discoverer": "保罗·埃米尔·勒科克·德布瓦博德兰 (1875)",
        "summary": "熔点仅为 29.76°C，放在手心里就能融化的奇特金属；其氮化物（GaN 氮化镓）彻底颠覆了现代高频快速充电器行业。",
        "fun_fact": "门捷列夫在发表第一版元素周期表时曾预言了“类铝”元素的存在与密度，几年后镓被发现，其性质与预言惊人吻合。"
    },
    {
        "num": 32, "sym": "Ge", "zh": "锗", "en": "Germanium", "mass": "72.630",
        "cat": "类金属", "period": 4, "group": 14, "config": "[Ar] 3d¹⁰ 4s² 4p²",
        "phase": "固态", "discoverer": "克莱门斯·温克勒 (1886)",
        "summary": "历史上第一个晶体管所使用的半导体材料，高折射率与红外透射性使其成为军工夜视仪红外光学透镜首选。",
        "fun_fact": "1947 年贝尔实验室发明世界上第一枚点接触晶体管时，用的基底不是硅，而是一小块高纯度单晶锗。"
    },
    {
        "num": 33, "sym": "As", "zh": "砷", "en": "Arsenic", "mass": "74.922",
        "cat": "类金属", "period": 4, "group": 15, "config": "[Ar] 3d¹⁰ 4s² 4p³",
        "phase": "固态", "discoverer": "阿尔伯图斯·麦格努斯 (约 1250)",
        "summary": "其三氧化二砷俗称砒霜，臭名昭著的毒药之王；而在微电子中，砷化镓（GaAs）是 5G 射频功率放大器的王牌芯片材料。",
        "fun_fact": "现代靶向药化学疗法中，超微量的高纯度砒霜（三氧化二砷注射液）被成功用于根治急性早幼粒细胞白血病。"
    },
    {
        "num": 34, "sym": "Se", "zh": "硒", "en": "Selenium", "mass": "78.971",
        "cat": "反应性非金属", "period": 4, "group": 16, "config": "[Ar] 3d¹⁰ 4s² 4p⁴",
        "phase": "固态", "discoverer": "永斯·雅各布·贝尔塞柳斯 (1817)",
        "summary": "具有光敏电导特性的抗氧化微量元素，早期的复印机感光鼓和光电池核心，谷胱甘肽过氧化物酶的核心活性位点。",
        "fun_fact": "名字源自希腊神话中的月亮女神塞勒涅（Selene），正好与同族前一周期代表大地的碲（Tellus）相互辉映。"
    },
    {
        "num": 35, "sym": "Br", "zh": "溴", "en": "Bromine", "mass": "79.904",
        "cat": "卤素", "period": 4, "group": 17, "config": "[Ar] 3d¹⁰ 4s² 4p⁵",
        "phase": "液态", "discoverer": "安托万·热罗姆·巴拉尔 (1826)",
        "summary": "常温常压下唯二呈液态的单质元素之一（另一种是汞），深红棕色强挥发性剧毒液体，溴化银开创了胶片摄影摄影时代。",
        "fun_fact": "古代地中海极其尊贵珍罕的“骨螺紫”染料，其核心显色发色团化学结构本质上就是一种二溴靛蓝天然分子。"
    },
    {
        "num": 36, "sym": "Kr", "zh": "氪", "en": "Krypton", "mass": "83.798",
        "cat": "稀有气体", "period": 4, "group": 18, "config": "[Ar] 3d¹⁰ 4s² 4p⁶",
        "phase": "气态", "discoverer": "威廉·拉姆齐 (1898)",
        "summary": "高密度发白光的稀有气体，机场跑道超高穿透力闪光信标灯填充气，曾被国际计量大会用于定义长度基准“1米”。",
        "fun_fact": "在 1960 至 1983 年间，国际标准“米”曾被极其精准地定义为氪-86 同位素在真空中辐射波长的 1650763.73 倍。"
    },
    {
        "num": 38, "sym": "Sr", "zh": "锶", "en": "Strontium", "mass": "87.62",
        "cat": "碱土金属", "period": 5, "group": 2, "config": "[Kr] 5s²",
        "phase": "固态", "discoverer": "阿黛尔·克劳福德 (1790)",
        "summary": "焰色反应呈现纯净极具辨识度的耀眼深红，现代最精准的光晶格光学原子钟的核心振荡基准。",
        "fun_fact": "世界上最精密的锶光晶格原子钟，精度高达每 150 亿年（甚至超过全宇宙现有年龄）才仅仅累积误差 1 秒。"
    },
    {
        "num": 42, "sym": "Mo", "zh": "钼", "en": "Molybdenum", "mass": "95.95",
        "cat": "过渡金属", "period": 5, "group": 6, "config": "[Kr] 4d⁵ 5s¹",
        "phase": "固态", "discoverer": "卡尔·威廉·舍勒 (1778)",
        "summary": "高熔点难熔金属，在极高温度下依然保持极佳机械强度与热导率，广泛用于特种装甲与半导体溅射靶材。",
        "fun_fact": "二硫化钼（MoS₂）具有类似于石墨的微观层状滑动结构，是真空与超高低温极端太空环境下无与伦比的固体润滑剂。"
    },
    {
        "num": 50, "sym": "Sn", "zh": "锡", "en": "Tin", "mass": "118.71",
        "cat": "后过渡金属", "period": 5, "group": 14, "config": "[Kr] 4d¹⁰ 5s² 5p²",
        "phase": "固态", "discoverer": "古代已知 (约公元前 3500 年)",
        "summary": "人类青铜器时代的合金融炼主角，无毒耐腐的马口铁镀层，电子电路印制板元器件焊接的生命线金属。",
        "fun_fact": "锡疫：在 -13.2°C 以下，延展性良好的白锡会逐渐转变为松散灰脆的同素异形体灰锡粉末，仿佛金属生病坍塌。"
    },
    {
        "num": 53, "sym": "I", "zh": "碘", "en": "Iodine", "mass": "126.90",
        "cat": "卤素", "period": 5, "group": 17, "config": "[Kr] 4d¹⁰ 5s² 5p⁵",
        "phase": "固态", "discoverer": "贝尔纳·库尔图瓦 (1811)",
        "summary": "蓝黑色带光泽的晶体，加热直接升华为绚丽紫色蒸汽。甲状腺素合成的核心原料，全民食盐加碘防治大脖子病。",
        "fun_fact": "碘遇淀粉会立即生成极深且极其灵敏的深蓝色络合物，是生物化学与法医检验中最经典的分子变色反应之一。"
    },
    {
        "num": 54, "sym": "Xe", "zh": "氙", "en": "Xenon", "mass": "131.29",
        "cat": "稀有气体", "period": 5, "group": 18, "config": "[Kr] 4d¹⁰ 5s² 5p⁶",
        "phase": "气态", "discoverer": "威廉·拉姆齐 (1898)",
        "summary": "质量极大的稀有气体，发光效率极高，现代深空探测器（如离子推力器、霍尔推进器）的首选工质推进推进剂。",
        "fun_fact": "氙是第一个被人类攻破化合神话的稀有气体：1962 年尼尔·巴特利特成功制得了六氟合铂酸氙，彻底改写了化学教科书。"
    },
    {
        "num": 74, "sym": "W", "zh": "钨", "en": "Tungsten", "mass": "183.84",
        "cat": "过渡金属", "period": 6, "group": 6, "config": "[Xe] 4f¹⁴ 5d⁴ 6s²",
        "phase": "固态", "discoverer": "胡安·何塞 / 福斯托·德卢亚尔 (1783)",
        "summary": "全宇宙所有金属中单质熔点最高（3422°C）与沸点最高（5930°C）的王者，硬质合金刀具与灯丝的无冕之王。",
        "fun_fact": "碳化钨（硬质合金）硬度堪比钻石，被称为“工业的牙齿”，数控机床切削最坚硬的钛合金和特种钢全靠钨钢铣刀。"
    },
    {
        "num": 78, "sym": "Pt", "zh": "铂", "en": "Platinum", "mass": "195.08",
        "cat": "过渡金属", "period": 6, "group": 10, "config": "[Xe] 4f¹⁴ 5d⁹ 6s¹",
        "phase": "固态", "discoverer": "安东尼奥·德乌略亚 (1735)",
        "summary": "化学性质极其稳定的贵金属“白金”，汽车尾气三元催化器与氢燃料电池质子交换膜（PEM）顶级电催化剂。",
        "fun_fact": "顺铂（Cisplatin）是现代抗肿瘤医学史上最伟大的广谱化疗药之一，彻底改变了睾丸癌与卵巢癌患者的临床治愈率。"
    },
    {
        "num": 80, "sym": "Hg", "zh": "汞", "en": "Mercury", "mass": "200.59",
        "cat": "过渡金属", "period": 6, "group": 12, "config": "[Xe] 4f¹⁴ 5d¹⁰ 6s²",
        "phase": "液态", "discoverer": "古代已知",
        "summary": "常温下唯一以液态存在的金属（俗称水银），高密度且能溶解多种金属形成汞齐，开创了托里拆利气压计时代。",
        "fun_fact": "汞在 -38.8°C 凝固为固态，而在 1911 年，卡末林·昂内斯正是用固态汞浸入液氦中首次发现了零电阻超导现象！"
    },
    {
        "num": 82, "sym": "Pb", "zh": "铅", "en": "Lead", "mass": "207.2",
        "cat": "后过渡金属", "period": 6, "group": 14, "config": "[Xe] 4f¹⁴ 5d¹⁰ 6s² 6p²",
        "phase": "固态", "discoverer": "古代已知",
        "summary": "质软易熔的重金属，所有放射性衰变链最终的稳定归宿，医院放射科与核反应堆阻挡 X 射线与伽马射线的坚固护盾。",
        "fun_fact": "从铀到针、从针到铅，全宇宙无论经历多少亿年的放射性衰变，绝大多数超重放射性元素最终都会稳定地化为一粒无害的铅。"
    },
    {
        "num": 44, "sym": "Ru", "zh": "钌", "en": "Ruthenium", "mass": "101.07",
        "cat": "过渡金属", "period": 5, "group": 8, "config": "[Kr] 4d⁷ 5s¹",
        "phase": "固态", "discoverer": "卡尔·恩斯特·克劳斯 (1844)",
        "summary": "极度耐磨耐腐的铂族金属，格拉布斯催化剂（烯烃复分解反应）核心，彻底革新现代有机全合成与药物研发。",
        "fun_fact": "钌络合物催化剂在室温空气中依然具备非凡的活性与稳定性，其发明者荣膺 2005 年诺贝尔化学奖。"
    },
    {
        "num": 46, "sym": "Pd", "zh": "钯", "en": "Palladium", "mass": "106.42",
        "cat": "过渡金属", "period": 5, "group": 10, "config": "[Kr] 4d¹⁰",
        "phase": "固态", "discoverer": "威廉·海德·沃拉斯顿 (1803)",
        "summary": "金属中的“吸氢海绵”，常温常压下能吞噬吸收自身体积 900 倍以上的氢气，有机偶联反应（铃木反应）王牌催化剂。",
        "fun_fact": "钯催化的碳-碳偶联反应几乎构成了现代抗癌药与高分子液晶材料合成的基础，被称为化学家的万能搭桥器。"
    },
    {
        "num": 56, "sym": "Ba", "zh": "钡", "en": "Barium", "mass": "137.33",
        "cat": "碱土金属", "period": 6, "group": 2, "config": "[Xe] 6s²",
        "phase": "固态", "discoverer": "汉弗里·戴维 (1808)",
        "summary": "焰色反应呈现苹果绿的碱土金属；其不溶性硫酸盐俗称“钡餐”，是消化道 X 射线透视的经典造影剂。",
        "fun_fact": "可溶性钡盐具有剧毒，但硫酸钡极难溶于水和胃酸（溶解度极低），因此能完全安全地穿过人体消化道而不被吸收。"
    },
    {
        "num": 83, "sym": "Bi", "zh": "铋", "en": "Bismuth", "mass": "208.98",
        "cat": "后过渡金属", "period": 6, "group": 15, "config": "[Xe] 4f¹⁴ 5d¹⁰ 6s² 6p³",
        "phase": "固态", "discoverer": "古代已知",
        "summary": "所有重金属中最温和无毒的“绿色重金属”，晶体熔融冷却时会生长出色彩斑斓、极具魔幻阶梯分形感的氧化彩虹晶体。",
        "fun_fact": "铋曾被认为是周期表上最重的绝对稳定元素。直到 2003 年物理学家才测出铋-209 其实有微弱放射性衰变，半衰期长达 1900 亿亿年（宇宙年龄的十亿倍以上）！"
    },
]

ELEMENTS_COUNT = len(_RAW_ELEMENTS)


def get_element_by_number(atomic_num: int) -> dict[str, Any]:
    """根据原子序数获取化学元素详情，若不存在则返回氢元素。"""
    for e in _RAW_ELEMENTS:
        if e["num"] == atomic_num:
            return _format_element(e)
    return _format_element(_RAW_ELEMENTS[0])


def get_element_of_the_day(date_str: str | None = None) -> dict[str, Any]:
    """根据日期（缺省今天）轮播获取当天专属元素。"""
    if date_str:
        try:
            dt = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            dt = datetime.date.today()
    else:
        dt = datetime.date.today()

    day_of_year = dt.timetuple().tm_yday
    idx = day_of_year % len(_RAW_ELEMENTS)
    elem = _RAW_ELEMENTS[idx]
    formatted = _format_element(elem)
    formatted["date"] = dt.strftime("%Y-%m-%d")
    return formatted


def _format_element(raw: dict[str, Any]) -> dict[str, Any]:
    return {
        "atomic_number": raw["num"],
        "symbol": raw["sym"],
        "name_zh": raw["zh"],
        "name_en": raw["en"],
        "atomic_mass": raw["mass"],
        "category": raw["cat"],
        "period": raw["period"],
        "group": raw["group"],
        "electron_config": raw["config"],
        "phase": raw["phase"],
        "discoverer": raw["discoverer"],
        "summary": raw["summary"],
        "fun_fact": raw["fun_fact"],
        "header_title": f"ELEMENT {raw['num']:02d} · {raw['sym']}",
    }
