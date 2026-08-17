"""
utils/sourcing_ai.py
--------------------
外贸智能寻源、货源开发与化工类深度定制支持模块。

核心功能：
1. 全国 50+ 重点外贸产业带与化工园区集群知识库（包含山东、江苏、浙江、广东等化工园区主营及CAS/品类）。
2. 出口采购成本、退税率与外贸综合利润测算模型（支持化工危包费、内陆运杂费、包装折算）。
3. 全网多渠道精准寻源与海外买家拓展搜索语法生成（1688 / 阿里国际 / Google X-Ray / LinkedIn / 化工CAS拓客）。
4. 化工外贸资质与危险品合规检查（CAS号、危险品Class 1-9判定、危包要求、MSDS/COA关键项）。
5. 供应商询价 (RFQ)、验厂打样与化工定制合成/采购协议 AI 生成。
"""
from __future__ import annotations

import re
from typing import Any

from utils.logger import get_logger

logger = get_logger("sourcing_ai")

# ---------------------------------------------------------------------------
# 1. 全国核心外贸产业带与化工集聚区数据库
# ---------------------------------------------------------------------------

INDUSTRIAL_CLUSTERS: list[dict[str, Any]] = [
    # ── 化工与新材料专区 ──
    {
        "category": "化工原料与精细化学品",
        "region": "山东 (东营 / 淄博 / 潍坊 / 烟台)",
        "hub_name": "鲁中北石化与精细化工产业带",
        "keywords": ["化工", "石化", "基础化工", "溶剂", "橡胶助剂", "塑料添加剂", "氯碱", "溴化物", "石油树脂"],
        "advantages": "国内最大石化与基础化工基地之一，产业链配套极全，大宗原料价格极具竞争力，沿海港口（青岛港/烟台港）发货便利。",
        "famous_markets": "齐鲁化工城、潍坊滨海化工园区、东营港经济开发区",
        "is_chemical": True,
        "export_tips": "大宗化工注意危包证与UN桶检验；重点关注原油价格联动与海关监管条件。",
    },
    {
        "category": "医药中间体与精细化工定制",
        "region": "江苏 (泰兴 / 张家港 / 南通 / 连云港)",
        "hub_name": "沿江沿海精细化工与医药中间体基地",
        "keywords": ["医药中间体", "定制合成", "表面活性剂", "农药原药", "染料颜料", "阻燃剂", "精细化工", "日化原料"],
        "advantages": "国内研发与定制合成能力最强区域之一，园区环保与安全规范完善，拥有大量高纯度合成定制实验室与合规工厂。",
        "famous_markets": "泰兴经济开发区精细化工园、连云港石化产业基地、张家港保税区化工品交易市场",
        "is_chemical": True,
        "export_tips": "涉及定制合成务必锁定 COA 纯度公差、水分/重金属指标及 SGS/第三方封样检测条款。",
    },
    {
        "category": "氟化工与特种染料助剂",
        "region": "浙江 (绍兴上虞 / 衢州 / 宁波)",
        "hub_name": "浙北染料涂料与浙西氟化工基地",
        "keywords": ["氟化工", "制冷剂", "染料", "印染助剂", "涂料树脂", "聚氨酯", "含氟聚合物"],
        "advantages": "全球重要的染料助剂与氟制冷剂供应源头，技术积累深厚，品牌出海成熟，宁波舟山港直通全球航线。",
        "famous_markets": "中国轻纺城染化市场、衢州绿色化学产业园、宁波大榭石化园区",
        "is_chemical": True,
        "export_tips": "制冷剂出口需特别注意配额与目标国含氟气体合规限制（如欧盟 F-Gas 法规）。",
    },
    {
        "category": "日化洗护原料与高分子改性",
        "region": "广东 (广州 / 佛山 / 惠州 / 茂名)",
        "hub_name": "珠三角日化原料与改性塑料集群",
        "keywords": ["日化原料", "表面活性剂", "香精香料", "改性塑料", "涂料油墨", "化妆品原料", "胶粘剂"],
        "advantages": "靠近全国最大的日化美妆与消费电子制造中心，响应快、支持小批量定制与特种复配配方服务。",
        "famous_markets": "广州兴发广场/怡发广场日化原料区、惠州大亚湾石化区、顺德涂料商城",
        "is_chemical": True,
        "export_tips": "化妆品与日化原料需符合目标国 INCI 命名、COA 及微生物重金属检测限量要求。",
    },
    {
        "category": "煤化工与基础化工单体",
        "region": "宁夏 / 内蒙古 / 陕西 (宁东 / 乌海 / 榆林)",
        "hub_name": "西北能源与现代煤化工产业集群",
        "keywords": ["煤化工", "甲醇", "聚乙烯", "聚丙烯", "电石", "PVC", "BDO", "草酸", "氰胺"],
        "advantages": "能源和矿产原料成本优势明显，大规模产能集中，适合大吨位基础化工与高分子材料集采。",
        "famous_markets": "宁东国家现代煤化工基地、乌海化工新材料产业园",
        "is_chemical": True,
        "export_tips": "内陆多采用铁路集装箱联运至天津/青岛港出海，需预留内陆运输与转运时间。",
    },
    # ── 通用外贸五金/电子/轻工 ──
    {
        "category": "消费电子与智能硬件",
        "region": "广东深圳 / 东莞",
        "hub_name": "全球消费电子与智能制造之都",
        "keywords": ["电子", "耳机", "智能手表", "手机配件", "LED", "数码", "PCB", "储能电源", "智能家居"],
        "advantages": "全球最完备的电子产业链，从打样开模到量产仅需数天，供应链响应极致。",
        "famous_markets": "华强北电子市场、东莞长安五金电子集聚区",
        "is_chemical": False,
        "export_tips": "重点关注 CE、FCC、RoHS、UN38.3 锂电池海运安全测试报告。",
    },
    {
        "category": "五金工具与园林机械",
        "region": "浙江永康 / 缙云 / 武义",
        "hub_name": "中国五金之都",
        "keywords": ["电动工具", "五金", "园林机械", "保温杯", "割草机", "门业", "铝梯", "户外炊具"],
        "advantages": "五金制造集群规模全球领先，模具与表面处理成本极低，OEM/ODM经验极其成熟。",
        "famous_markets": "永康中国科技五金城",
        "is_chemical": False,
        "export_tips": "机械类出口欧盟需通过 CE-MD 机械指令，电动类需关注电机能效认证。",
    },
    {
        "category": "小商品与饰品文具",
        "region": "浙江义乌",
        "hub_name": "世界小商品之都",
        "keywords": ["小商品", "饰品", "文具", "节庆用品", "日用百货", "派对用品", "发饰", "收纳"],
        "advantages": "品类繁多、支持小单快反、拼箱出口极其便利，现货库存充足。",
        "famous_markets": "义乌国际商贸城 (一区至五区)",
        "is_chemical": False,
        "export_tips": "多品类拼箱可利用义乌市场采购贸易方式 (1039) 简化申报流程。",
    },
    {
        "category": "玩具与动漫周边",
        "region": "广东汕头澄海",
        "hub_name": "中国玩具礼品之都",
        "keywords": ["玩具", "积木", "无人机玩具", "遥控车", "早教玩具", "婴童用品", "毛绒玩具"],
        "advantages": "全国最大的塑料玩具与遥控玩具研发制造基地，模具开发快，自动化注塑程度高。",
        "famous_markets": "澄海宝奥国际玩具城",
        "is_chemical": False,
        "export_tips": "儿童玩具对环保和安全性要求严苛，务必提供 EN71、ASTM F963、CPC 认证报告。",
    },
    {
        "category": "小家电与照明电气",
        "region": "浙江宁波 (慈溪/余姚) & 广东顺德/中山",
        "hub_name": "中国家电制造黄金走廊",
        "keywords": ["小家电", "空气炸锅", "电风扇", "吸尘器", "净水器", "灯具", "LED照明", "插座"],
        "advantages": "国内小家电出口主要基地，电机、电热元件与注塑高度垂直整合，性价比极高。",
        "famous_markets": "慈溪家电城、顺德容桂家电集聚区、中山古镇灯饰广场",
        "is_chemical": False,
        "export_tips": "出口欧美需注意 CB、CE-LVD/EMC、UL/ETL 认证，不同国家插头标准需精准核实。",
    },
]

# ---------------------------------------------------------------------------
# 2. 化工外贸危险品与合规知识库
# ---------------------------------------------------------------------------

DANGEROUS_GOODS_CLASSES: dict[str, dict[str, str]] = {
    "Non-DG": {"name_zh": "普货 (非危险品)", "desc": "无需危包证，普通集装箱或快运，需提供非危鉴定书/MSDS"},
    "Class 1": {"name_zh": "第1类：爆炸品", "desc": "烟花爆竹、火药等，出口需特种审批"},
    "Class 2": {"name_zh": "第2类：气体 (易燃/非易燃/有毒气体)", "desc": "压缩气体、液化气、制冷剂等，需高压钢瓶或ISO Tank"},
    "Class 3": {"name_zh": "第3类：易燃液体", "desc": "溶剂、醇类、酯类、油漆涂料等，注意闭杯闪点与防爆包装"},
    "Class 4": {"name_zh": "第4类：易燃固体/自燃物品/遇水放出易燃气体", "desc": "金属粉末、硫磺、电石等，要求密封防潮"},
    "Class 5": {"name_zh": "第5类：氧化剂和有机过氧化物", "desc": "过氧化氢、硝酸盐等，强氧化性，严禁混装"},
    "Class 6": {"name_zh": "第6类：毒性物质和感染性物质", "desc": "农药原药、剧毒品等，需剧毒品进出口许可证"},
    "Class 7": {"name_zh": "第7类：放射性物质", "desc": "特种放射源材料"},
    "Class 8": {"name_zh": "第8类：腐蚀性物质", "desc": "酸类、碱类、腐蚀性盐类，需耐腐蚀UN塑料桶/衬胶罐"},
    "Class 9": {"name_zh": "第9类：杂项危险物质和物品", "desc": "锂电池、危害环境物质等，需UN包装标志"},
}

CHEMICAL_MSDS_KEY_SECTIONS = [
    "1. 化学品及企业标识 (Chemical Product and Company Identification)",
    "2. 危险性概述 (Hazards Identification - GHS分类与警示词)",
    "3. 成分/组成信息 (Composition/Information on Ingredients - CAS号与纯度)",
    "4. 急救措施 (First-Aid Measures)",
    "5. 消防措施 (Fire-Fighting Measures)",
    "6. 泄漏应急处理 (Accidental Release Measures)",
    "7. 操作处置与储存 (Handling and Storage)",
    "8. 接触控制/个体防护 (Exposure Controls/Personal Protection)",
    "9. 理化特性 (Physical and Chemical Properties - 沸点/闪点/密度/pH)",
    "10. 稳定性和反应活性 (Stability and Reactivity)",
    "11. 毒理学信息 (Toxicological Information - LD50/LC50)",
    "12. 生态学信息 (Ecological Information)",
    "13. 废弃处置 (Disposal Considerations)",
    "14. 运输信息 (Transport Information - UN号/Class/包装类别PG)",
    "15. 法规信息 (Regulatory Information - REACH/TSCA等)",
    "16. 其他信息 (Other Information)",
]


# ---------------------------------------------------------------------------
# 3. 业务函数：产业带与货源地智能匹配
# ---------------------------------------------------------------------------

def match_industrial_clusters(query: str, is_chemical_only: bool = False) -> list[dict[str, Any]]:
    """
    根据产品关键词/CAS号/行业名称，智能匹配全国对应产业带与货源集聚地。
    """
    cleaned_query = (query or "").strip().lower()
    if not cleaned_query:
        if is_chemical_only:
            return [c for c in INDUSTRIAL_CLUSTERS if c.get("is_chemical")]
        return INDUSTRIAL_CLUSTERS

    matched = []
    for cluster in INDUSTRIAL_CLUSTERS:
        if is_chemical_only and not cluster.get("is_chemical"):
            continue

        score = 0
        # 关键词匹配
        for kw in cluster.get("keywords", []):
            if kw.lower() in cleaned_query or cleaned_query in kw.lower():
                score += 10
        # 类目与地区匹配
        if cleaned_query in cluster.get("category", "").lower():
            score += 8
        if cleaned_query in cluster.get("region", "").lower():
            score += 5

        if score > 0 or not cleaned_query:
            matched.append({"cluster": cluster, "score": score})

    # 按匹配度从高到低排序
    matched.sort(key=lambda x: x["score"], reverse=True)
    return [m["cluster"] for m in matched] if matched else [c for c in INDUSTRIAL_CLUSTERS if (not is_chemical_only or c.get("is_chemical"))]


# ---------------------------------------------------------------------------
# 4. 业务函数：采购成本、退税与外贸综合利润测算
# ---------------------------------------------------------------------------

def calculate_export_profit(
    purchase_price_cny: float,
    vat_rate: float = 0.13,
    rebate_rate: float = 0.13,
    domestic_freight_cny: float = 0.0,
    packaging_cny: float = 0.0,
    dg_handling_cny: float = 0.0,
    fob_price_usd: float = 0.0,
    exchange_rate: float = 7.20,
    qty: float = 1.0,
    ocean_freight_usd: float = 0.0,
) -> dict[str, Any]:
    """
    外贸出口利润与采购核价测算器（支持化工及普货）：
    
    退税原理：
    含税采购成本 -> 实际无税采购成本 = 含税采购价 / (1 + 增值税率)
    退税金额 = (含税采购价 / (1 + 增值税率)) * 出口退税率
    实际净采购成本 = 含税采购价 - 退税金额
    国内综合成本 (CNY) = 实际净采购成本 + 内陆运费 + 包装打托费 + 危险品/杂费
    FOB保本单价 (USD) = 国内综合成本 / 汇率
    FOB收入 (CNY) = FOB售价(USD) * 汇率
    单件净利润 (CNY) = FOB收入 - 国内综合成本
    总净利润 (CNY) = 单件净利润 * 数量
    销售毛利率 (%) = (单件净利润 / FOB收入) * 100
    """
    if qty <= 0:
        qty = 1.0
    if exchange_rate <= 0:
        exchange_rate = 7.20

    vat_rate = max(0.0, vat_rate)
    rebate_rate = max(0.0, rebate_rate)
    purchase_price_cny = max(0.0, purchase_price_cny)

    # 1. 退税与净采购成本
    tax_free_base = purchase_price_cny / (1.0 + vat_rate) if vat_rate > 0 else purchase_price_cny
    tax_rebate_amount = tax_free_base * rebate_rate
    net_purchase_cost = purchase_price_cny - tax_rebate_amount

    # 2. 国内综合成本
    unit_domestic_cost = (
        net_purchase_cost + domestic_freight_cny + packaging_cny + dg_handling_cny
    )
    total_domestic_cost = unit_domestic_cost * qty

    # 3. FOB 保本价 (USD)
    breakeven_fob_usd = unit_domestic_cost / exchange_rate if exchange_rate > 0 else 0.0

    # 4. 收益与利润
    effective_fob_usd = fob_price_usd
    if effective_fob_usd <= 0:
        # 如果未指定售价，默认提供 15% 目标毛利率参考价
        effective_fob_usd = breakeven_fob_usd * 1.18

    fob_revenue_cny = effective_fob_usd * exchange_rate
    unit_profit_cny = fob_revenue_cny - unit_domestic_cost
    total_profit_cny = unit_profit_cny * qty
    total_profit_usd = total_profit_cny / exchange_rate if exchange_rate > 0 else 0.0

    margin_pct = (unit_profit_cny / fob_revenue_cny * 100.0) if fob_revenue_cny > 0 else 0.0

    # 5. CIF 参考价
    cif_price_usd = effective_fob_usd + ocean_freight_usd

    return {
        "purchase_price_cny": purchase_price_cny,
        "tax_free_base": round(tax_free_base, 2),
        "tax_rebate_amount": round(tax_rebate_amount, 2),
        "net_purchase_cost": round(net_purchase_cost, 2),
        "unit_domestic_cost": round(unit_domestic_cost, 2),
        "total_domestic_cost": round(total_domestic_cost, 2),
        "breakeven_fob_usd": round(breakeven_fob_usd, 2),
        "fob_price_usd": round(effective_fob_usd, 2),
        "cif_price_usd": round(cif_price_usd, 2),
        "fob_revenue_cny": round(fob_revenue_cny, 2),
        "unit_profit_cny": round(unit_profit_cny, 2),
        "total_profit_cny": round(total_profit_cny, 2),
        "total_profit_usd": round(total_profit_usd, 2),
        "margin_pct": round(margin_pct, 2),
        "qty": qty,
        "exchange_rate": exchange_rate,
    }


# ---------------------------------------------------------------------------
# 5. 业务函数：全网精准寻源与买家拓展搜索语法生成器
# ---------------------------------------------------------------------------

def generate_sourcing_search_queries(
    product_name: str,
    cas_number: str = "",
    target_country: str = "",
    application_industry: str = "",
) -> dict[str, list[dict[str, str]]]:
    """
    生成适用于 1688 / 阿里国际 / Google 采购商 X-Ray / LinkedIn 企业拓展的高精度搜索语法。
    针对化工类（带 CAS 号）提供纯度与配方采购商精准搜索。
    """
    clean_p = product_name.strip()
    clean_cas = cas_number.strip()
    clean_cnt = target_country.strip()
    clean_app = application_industry.strip()

    # 1. 1688 源头工厂寻源语法
    p_1688 = [
        {"platform": "1688 / 阿里国内站", "type": "源头工厂与现货", "query": f"{clean_p} 实力商家 源头工厂 现货"},
        {"platform": "1688 / 阿里国内站", "type": "代工与定制", "query": f"{clean_p} OEM 定制 代加工 厂房认证"},
    ]
    if clean_cas:
        p_1688.append({
            "platform": "1688 / 盖德化工网",
            "type": "CAS精确寻源",
            "query": f"{clean_cas} {clean_p} 现货 原装 出口品质",
        })

    # 2. 阿里国际站 (Alibaba.com) 竞品与同行比价
    p_ali = [
        {"platform": "Alibaba.com", "type": "Verified Supplier", "query": f'"{clean_p}" "Verified Supplier" MOQ OEM'},
        {"platform": "Alibaba.com", "type": "Price & Spec Search", "query": f'"{clean_p}" {clean_cas} "Custom synthesis" OR "Bulk supply"'.strip()},
    ]

    # 3. Google X-Ray 国际买家挖掘指令
    country_filter = f'site:.{clean_cnt.lower()}' if (clean_cnt and len(clean_cnt) == 2) else (f'"{clean_cnt}"' if clean_cnt else '')
    app_filter = f'"{clean_app}"' if clean_app else ''
    
    # 进口商/分销商搜索
    q_distributor = f'intitle:"distributor" OR intitle:"importer" OR intitle:"wholesaler" "{clean_p}" {app_filter} {country_filter} -china -chinese -supplier -manufacturer'.strip()
    # 化工专属搜索（采购商、配方师、MSDS发布商）
    if clean_cas:
        q_chemical_buyer = f'"{clean_cas}" ("safety data sheet" OR "TDS" OR "specifications") ("procurement" OR "purchasing" OR "distributor") {country_filter} -alibaba -made-in-china'.strip()
    else:
        q_chemical_buyer = f'"{clean_p}" ("distributor" OR "stockist") ("contact us" OR "request a quote") {country_filter} -alibaba'.strip()

    p_google = [
        {"platform": "Google Search", "type": "海外进口商与分销商", "query": re.sub(r"\s+", " ", q_distributor)},
        {"platform": "Google Search", "type": "化工/行业采购商精准", "query": re.sub(r"\s+", " ", q_chemical_buyer)},
        {"platform": "Google Search", "type": "行业展会参展商名录", "query": f'"{clean_p}" "exhibitor list" OR "exhibitor directory" (2024 OR 2025 OR 2026)'},
    ]

    # 4. LinkedIn 采购决策人挖掘
    p_linkedin = [
        {"platform": "LinkedIn X-Ray", "type": "采购总监/经理", "query": f'site:linkedin.com/in/ ("Purchasing Manager" OR "Procurement Director" OR "Sourcing Specialist") "{clean_p}" {country_filter}'.strip()},
        {"platform": "LinkedIn X-Ray", "type": "化工/配方研发决策人", "query": f'site:linkedin.com/in/ ("Formulator" OR "R&D Chemist" OR "Technical Buyer") ("{clean_p}" OR "{clean_cas}") {country_filter}'.strip()},
    ]

    return {
        "domestic_sourcing": p_1688,
        "b2b_marketplaces": p_ali,
        "google_xray": p_google,
        "linkedin_buyers": p_linkedin,
    }


# ---------------------------------------------------------------------------
# 6. 业务函数：化工与通用外贸定制询价单 (RFQ) Prompt 构造
# ---------------------------------------------------------------------------

def build_sourcing_rfq_prompt(
    product_name: str,
    cas_number: str = "",
    purity_spec: str = "99% Tech Grade",
    quantity_target: str = "1 FCL / 1000 Units",
    packaging_requirement: str = "Standard Export Drum / Pallet",
    target_price_cny: str = "",
    special_requirements: str = "",
    is_chemical: bool = False,
) -> str:
    """构建发给源头工厂/定制供应商的专业外贸询价与打样要求（中文版）。"""
    lines = [
        "尊敬的供应商朋友：",
        "",
        "您好！我们是一家专业进出口贸易公司，目前正在为海外重点客户采购及定制以下产品，特向贵司发起询价 (RFQ)：",
        "",
        f"【采购产品】：{product_name}",
    ]
    if cas_number:
        lines.append(f"【CAS 编号】：{cas_number}")
    if purity_spec:
        lines.append(f"【规格/纯度】：{purity_spec}")
    lines.extend([
        f"【首批采购量】：{quantity_target}",
        f"【包装要求】：{packaging_requirement}",
    ])
    if target_price_cny:
        lines.append(f"【目标含税出厂价】：{target_price_cny}（需开具13%增值税专用发票）")
    if special_requirements:
        lines.append(f"【特殊工艺/定制要求】：{special_requirements}")

    lines.append("")
    lines.append("【请贵司提供以下报价信息】：")
    lines.extend([
        "1. 含税出厂价 (EXW) 及开票税点；",
        "2. 供货交期 (Lead Time) 及打样周期与打样费用；",
        "3. 最小起订量 (MOQ) 及不同阶梯数量的优惠阶梯；",
        "4. 包装规格（毛净重、尺寸、托盘尺寸、每托装箱数）；",
    ])
    if is_chemical or cas_number:
        lines.extend([
            "5. 最新检测报告 COA (包含主含量、水分、重金属、色度、杂质限度)；",
            "6. 16项安全技术说明书 (SDS/MSDS) 及危包证/海运鉴定书（如属于危险品）；",
            "7. 是否支持第三方机构（如 SGS / Intertek）验厂封样复检。",
        ])
    else:
        lines.extend([
            "5. 相关的出口认证证书（如 CE / RoHS / FCC / FDA 等）；",
            "6. 是否支持 OEM 定制打标、彩盒包装与验厂审核。",
        ])

    lines.extend([
        "",
        "期待贵司尽快回复报价！",
    ])
    return "\n".join(lines)


def build_customization_agreement_text(
    buyer_company: str,
    supplier_company: str,
    product_name: str,
    specs: str,
    tolerance_terms: str,
    is_chemical: bool = False,
) -> str:
    """生成标准化定制采购与质量把控协议框架。"""
    # Clause text kept OUTSIDE the f-string: the strings contain \n escape
    # sequences, which are not allowed inside f-string expressions before
    # Python 3.12 (PEP 701). Inlining them caused a SyntaxError on Python 3.11.
    chemical_clause = (
        "### 第四条 危险品与化学品特殊条款\n"
        "1. 乙方须保证提供符合 GHS 国际标准的 16 项中英文 SDS/MSDS，并与实际出货批次一致。\n"
        "2. 涉及危险货物运输的，乙方须提供合规的 UN 认证危险货物包装及危包证。\n"
        "3. 发生渗漏、包装破损引起港口滞留或罚款的，由乙方承担直接责任。"
    )
    packaging_clause = (
        "### 第四条 包装与知识产权保护\n"
        "1. 乙方须严格按照甲方提供的包装图稿及外箱唛头进行包装，确保海运/空运抗压防潮。\n"
        "2. 乙方不得向任何第三方泄露甲方的定制设计、配方及图纸，不得将定制模具或产品转售第三方。"
    )
    clause_four = chemical_clause if is_chemical else packaging_clause
    agreement = f"""# 产品外贸定制采购与品质保证协议

**甲方（采购方）**：{buyer_company or "________________________"}
**乙方（供货方）**：{supplier_company or "________________________"}

鉴于甲方委托乙方定制生产【{product_name}】，甲乙双方经友好协商，就产品技术指标、品质保证及验收标准达成如下协议：

### 第一条 定制技术规范与指标
1. 产品名称：{product_name}
2. 技术规格要求：{specs or "符合国际标准及双方确认之样品参数"}
3. 关键公差与限定条款：{tolerance_terms or "主指标公差不超过 ±0.5%，外观无瑕疵"}

### 第二条 样品确认与封样
1. 乙方须在量产前向甲方提供产前样（Pre-production Sample）至少两份，经甲方书面确认合格并封样后方可开始批量生产。
2. 批量生产之大货品质不得低于封样样品标准。

### 第三条 质量检验与第三方复检
1. 每批大货出厂前，乙方须提供每批次的自检质检报告（{"COA 分析报告" if is_chemical else "出厂检验合格证"}）。
2. 甲方有权在出厂前指定第三方检验机构（如 SGS、Intertek、BV）进行抽样检测，检测合格后方可放行发货。
3. 若第三方检测结果显示主要指标不合格，乙方应免费重做或退还已收货款，并承担相应检测及延误损失。

{clause_four}

### 第五条 违约责任与争议解决
1. 因乙方交期延误影响船期造成的海运亏舱费、集装箱滞期费由乙方承担。
2. 本协议未尽事宜由双方协商解决，协商不成可向甲方所在地有管辖权的人民法院提起诉讼。

**甲方（盖章）**：____________________      **乙方（盖章）**：____________________
**日期**：2026年___月___日                  **日期**：2026年___月___日
"""
    return agreement.strip()
