"""
utils/product_catalog.py
------------------------
本地产品目录管理：用户可录入多个产品，每个产品带行业标签。
自动推送时根据客户行业匹配最相关的本企业产品，实现精准推介。

数据结构 (每个产品):
{
    "id": "hex_token",
    "name": "LED Street Light 200W",
    "description": "High-power outdoor LED street light...",
    "features": "IP67, 50000h lifespan, CE/RoHS...",
    "industries": ["electronics", "construction"],  # 适用行业列表
    "keywords": ["led", "street light", "outdoor"],
    "price_range": "$50-$120/unit",
    "moq": "100 units",
    "certifications": "CE, RoHS, FCC",
    "created_at": "...",
    "updated_at": "...",
}

存储路径: data/users/{username}/product_catalog.json
"""
from __future__ import annotations

import secrets
from datetime import datetime

from utils.logger import get_logger
from utils.storage import load_user_json, save_user_json

logger = get_logger("product_catalog")

_CATALOG_FILE = "product_catalog.json"


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------

def get_catalog(username: str) -> list[dict]:
    """获取用户的完整产品目录。"""
    return load_user_json(username, _CATALOG_FILE, default=[])


def get_product(username: str, product_id: str) -> dict | None:
    """按ID获取单个产品。"""
    catalog = get_catalog(username)
    for p in catalog:
        if p.get("id") == product_id:
            return p
    return None


def add_product(
    username: str,
    name: str,
    description: str = "",
    features: str = "",
    industries: list[str] | None = None,
    keywords: list[str] | None = None,
    price_range: str = "",
    moq: str = "",
    certifications: str = "",
) -> dict:
    """
    添加一个产品到目录。

    Args:
        username: 当前用户
        name: 产品名称
        description: 产品描述/简介
        features: 产品卖点/参数
        industries: 适用行业列表 (使用 INDUSTRY_TEMPLATES 中的key)
        keywords: 关键词列表 (用于模糊匹配)
        price_range: 参考价格区间
        moq: 最小起订量
        certifications: 认证信息

    Returns:
        新创建的产品 dict
    """
    product_id = secrets.token_hex(6)
    now = datetime.now().isoformat()

    product = {
        "id": product_id,
        "name": name.strip(),
        "description": description.strip(),
        "features": features.strip(),
        "industries": industries or [],
        "keywords": keywords or [],
        "price_range": price_range.strip(),
        "moq": moq.strip(),
        "certifications": certifications.strip(),
        "created_at": now,
        "updated_at": now,
    }

    catalog = get_catalog(username)
    catalog.append(product)
    save_user_json(username, _CATALOG_FILE, catalog)

    logger.info("Product added: %s (%s) by %s", name, product_id, username)
    return product


def update_product(username: str, product_id: str, updates: dict) -> bool:
    """更新产品信息（仅允许更新白名单内的字段）。"""
    _ALLOWED_UPDATE_KEYS = {
        "name", "description", "features", "industries", "keywords",
        "price_range", "moq", "certifications",
    }
    # 过滤非法字段
    safe_updates = {k: v for k, v in updates.items() if k in _ALLOWED_UPDATE_KEYS}
    if not safe_updates:
        return False

    catalog = load_user_json(username, _CATALOG_FILE, default=[])
    for p in catalog:
        if p.get("id") == product_id:
            p.update(safe_updates)
            p["updated_at"] = datetime.now().isoformat()
            save_user_json(username, _CATALOG_FILE, catalog)
            logger.info("Product updated: %s by %s", product_id, username)
            return True
    return False


def delete_product(username: str, product_id: str) -> bool:
    """删除一个产品。"""
    catalog = load_user_json(username, _CATALOG_FILE, default=[])
    original_len = len(catalog)
    catalog = [p for p in catalog if p.get("id") != product_id]
    if len(catalog) < original_len:
        save_user_json(username, _CATALOG_FILE, catalog)
        logger.info("Product deleted: %s by %s", product_id, username)
        return True
    return False


# ---------------------------------------------------------------------------
# 智能匹配：根据客户行业匹配最相关的本企业产品
# ---------------------------------------------------------------------------

def match_products_for_prospect(
    username: str,
    prospect_industry: str,
    prospect_product_interest: str = "",
    limit: int = 3,
) -> list[dict]:
    """
    根据客户行业和产品兴趣，从本地产品目录中匹配最相关的产品。

    匹配算法（按优先级评分）:
    1. 行业完全匹配 (industries字段包含客户行业) → +10分
    2. 产品兴趣关键词匹配 (keywords/name/features中包含客户感兴趣的词) → +5分/词
    3. 通用产品（industries为空，适用所有行业） → +2分

    Args:
        username: 当前用户
        prospect_industry: 客户行业 (标准化后的key，如 "electronics")
        prospect_product_interest: 客户感兴趣的产品关键词
        limit: 最多返回几个匹配产品

    Returns:
        按相关度排序的产品列表 (最多limit个)
    """
    catalog = get_catalog(username)
    if not catalog:
        return []

    # 准备客户兴趣关键词
    interest_words = set()
    if prospect_product_interest:
        # 分词：按空格、逗号、斜杠分割
        for word in prospect_product_interest.lower().replace(",", " ").replace("/", " ").split():
            word = word.strip()
            if len(word) >= 2:  # 忽略太短的词
                interest_words.add(word)

    scored_products = []

    for product in catalog:
        score = 0
        match_reasons = []

        # 1. 行业匹配
        product_industries = [ind.lower() for ind in product.get("industries", [])]
        if prospect_industry and prospect_industry.lower() in product_industries:
            score += 10
            match_reasons.append("行业匹配")

        # 2. 关键词匹配
        if interest_words:
            # 搜索范围：产品名称 + 关键词 + 特点 + 描述
            searchable_text = " ".join([
                product.get("name", "").lower(),
                " ".join(product.get("keywords", [])).lower(),
                product.get("features", "").lower(),
                product.get("description", "").lower(),
            ])

            matched_words = []
            for word in interest_words:
                if word in searchable_text:
                    score += 5
                    matched_words.append(word)

            if matched_words:
                match_reasons.append(f"关键词匹配: {', '.join(matched_words)}")

        # 3. 通用产品（未指定行业的产品适用于所有客户）
        if not product_industries:
            score += 2
            match_reasons.append("通用产品")

        # 4. 额外加分：有详细描述/卖点的产品优先
        if product.get("features"):
            score += 1
        if product.get("certifications"):
            score += 1

        if score > 0:
            scored_products.append({
                **product,
                "_score": score,
                "_match_reasons": match_reasons,
            })

    # 按评分排序，取前N个
    scored_products.sort(key=lambda x: x["_score"], reverse=True)
    return scored_products[:limit]


def format_matched_products_for_prompt(matched_products: list[dict]) -> str:
    """
    将匹配到的产品格式化为AI prompt可用的文本描述。

    Args:
        matched_products: match_products_for_prospect 返回的产品列表

    Returns:
        格式化后的产品信息文本（给AI看的）
    """
    if not matched_products:
        return ""

    parts = []
    for i, product in enumerate(matched_products, 1):
        lines = [f"Product {i}: {product.get('name', 'Unknown')}"]

        if product.get("description"):
            lines.append(f"  Description: {product['description']}")
        if product.get("features"):
            lines.append(f"  Key Features: {product['features']}")
        if product.get("price_range"):
            lines.append(f"  Price Range: {product['price_range']}")
        if product.get("moq"):
            lines.append(f"  MOQ: {product['moq']}")
        if product.get("certifications"):
            lines.append(f"  Certifications: {product['certifications']}")

        match_reasons = product.get("_match_reasons", [])
        if match_reasons:
            lines.append(f"  Match Reason: {'; '.join(match_reasons)}")

        parts.append("\n".join(lines))

    return "\n\n".join(parts)


def get_catalog_industries(username: str) -> dict[str, int]:
    """
    统计产品目录中各行业的产品数量。

    Returns:
        {"electronics": 3, "automotive": 1, ...}
    """
    catalog = get_catalog(username)
    industry_counts: dict[str, int] = {}
    for product in catalog:
        for ind in product.get("industries", []):
            industry_counts[ind] = industry_counts.get(ind, 0) + 1
    return industry_counts
