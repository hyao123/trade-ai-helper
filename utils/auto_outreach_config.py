"""Configuration constants for the auto outreach engine."""
from __future__ import annotations

import re

# ---------------------------------------------------------------------------
# 推送配置常量
# ---------------------------------------------------------------------------
MAX_PROSPECTS_PER_CAMPAIGN = 500   # 单次推送上限
SEND_INTERVAL_SECONDS = 2.0       # 每封邮件之间的间隔（防限流）
PERSIST_BATCH_SIZE = 10            # 每N封持久化一次结果（减少IO）

# 邮箱格式校验正则
EMAIL_RE = re.compile(r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$")

# ---------------------------------------------------------------------------
# 行业模板映射（AI会根据行业自动调整，这里提供默认参考）
# ---------------------------------------------------------------------------
INDUSTRY_TEMPLATES: dict[str, dict] = {
    "electronics": {
        "label": "电子/消费电子",
        "focus": "product quality, certifications (CE/FCC/RoHS), competitive pricing, fast delivery",
        "pain_points": "supply chain stability, quality consistency, MOQ flexibility",
    },
    "automotive": {
        "label": "汽车/汽配",
        "focus": "OEM/ODM capability, IATF16949 certification, durability testing, timely delivery",
        "pain_points": "quality standards compliance, long-term supply reliability",
    },
    "textiles": {
        "label": "纺织/服装",
        "focus": "fabric quality, customization, fast sampling, eco-friendly materials",
        "pain_points": "lead time, color consistency, minimum order flexibility",
    },
    "machinery": {
        "label": "机械/工业设备",
        "focus": "precision, durability, after-sale service, installation support",
        "pain_points": "technical support, spare parts availability, warranty terms",
    },
    "food": {
        "label": "食品/农产品",
        "focus": "food safety certifications (HACCP/ISO22000), shelf life, packaging",
        "pain_points": "import regulations, freshness, documentation",
    },
    "medical": {
        "label": "医疗器械/健康",
        "focus": "FDA/CE certification, clinical evidence, quality management system",
        "pain_points": "regulatory compliance, documentation, traceability",
    },
    "construction": {
        "label": "建材/家居",
        "focus": "material durability, competitive pricing, bulk supply capability",
        "pain_points": "shipping logistics for heavy goods, sample availability",
    },
    "chemical": {
        "label": "化工/原材料",
        "focus": "purity, MSDS documentation, stable supply, competitive pricing",
        "pain_points": "hazmat shipping compliance, batch consistency",
    },
    "other": {
        "label": "其他/通用",
        "focus": "product quality, competitive pricing, reliable delivery, professional service",
        "pain_points": "finding the right supplier, communication, quality assurance",
    },
}

# 重要邮件触发关键词（用于自动识别是否需要转发）
IMPORTANT_KEYWORDS = [
    "order", "purchase", "buy", "quote", "quotation", "price list",
    "sample", "urgent", "asap", "contract", "agreement", "payment",
    "bulk order", "large quantity", "exclusive", "distributor",
    "下单", "采购", "报价", "样品", "紧急", "合同", "付款",
]

