"""
utils/auto_outreach.py
----------------------
自动推送引擎：解析客户列表 → 按行业匹配 → AI生成个性化邮件 → 批量发送 → 自动回复 → 重点转发

核心功能:
  1. parse_prospect_file(): 解析上传的客户邮箱列表文件(CSV/Excel)
  2. generate_outreach_email(): 按客户行业信息AI生成个性化产品推介邮件
  3. run_campaign(): 执行推送任务，逐个生成并发送
  4. auto_reply(): 自动识别客户回复意图并生成回复
  5. forward_important_email(): 重点邮件转发到指定邮箱/渠道

Campaign状态管理使用JSON持久化，支持暂停/恢复。
"""
from __future__ import annotations

import csv
import io
import secrets
from datetime import datetime
from typing import Generator

from utils.logger import get_logger
from utils.storage import load_user_json, save_user_json

logger = get_logger("auto_outreach")

_CAMPAIGNS_FILE = "outreach_campaigns.json"
_OUTREACH_LOG_FILE = "outreach_log.json"

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


# ---------------------------------------------------------------------------
# 文件解析
# ---------------------------------------------------------------------------

def parse_prospect_file(file_content: bytes, filename: str) -> tuple[list[dict], str]:
    """
    解析上传的客户列表文件。

    支持格式: CSV, Excel (xlsx)
    必填列: email
    可选列: company, contact_name, industry, country, product_interest, notes

    Args:
        file_content: 文件二进制内容
        filename: 文件名（用于判断格式）

    Returns:
        (prospects_list, error_message)
        成功时 error_message 为空字符串
    """
    prospects = []
    error = ""

    try:
        if filename.lower().endswith(".csv"):
            prospects, error = _parse_csv(file_content)
        elif filename.lower().endswith((".xlsx", ".xls")):
            prospects, error = _parse_excel(file_content)
        else:
            return [], "不支持的文件格式，请上传 CSV 或 Excel 文件"
    except Exception as e:
        logger.error("File parse error: %s", e)
        return [], f"文件解析失败: {e}"

    # 验证必填字段
    valid_prospects = []
    for i, p in enumerate(prospects):
        email = p.get("email", "").strip()
        if not email or "@" not in email:
            continue
        # 标准化字段
        valid_prospects.append({
            "email": email,
            "company": p.get("company", "").strip(),
            "contact_name": p.get("contact_name", p.get("name", "")).strip(),
            "industry": _normalize_industry(p.get("industry", "").strip()),
            "country": p.get("country", "").strip(),
            "product_interest": p.get("product_interest", p.get("product", "")).strip(),
            "notes": p.get("notes", "").strip(),
        })

    if not valid_prospects:
        return [], "未找到有效的客户记录（需要至少包含 email 列）"

    return valid_prospects, error


def _parse_csv(file_content: bytes) -> tuple[list[dict], str]:
    """解析CSV文件。"""
    # 尝试多种编码
    for encoding in ("utf-8-sig", "utf-8", "gbk", "gb2312", "latin-1"):
        try:
            text = file_content.decode(encoding)
            break
        except (UnicodeDecodeError, LookupError):
            continue
    else:
        return [], "无法识别文件编码"

    reader = csv.DictReader(io.StringIO(text))
    rows = list(reader)
    return rows, ""


def _parse_excel(file_content: bytes) -> tuple[list[dict], str]:
    """解析Excel文件（需要openpyxl）。"""
    try:
        import openpyxl
    except ImportError:
        return [], "Excel解析需要安装 openpyxl 库，请使用 CSV 格式"

    wb = openpyxl.load_workbook(io.BytesIO(file_content), read_only=True)
    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        return [], "Excel 文件为空"

    headers = [str(h).strip().lower() if h else f"col_{i}" for i, h in enumerate(rows[0])]
    prospects = []
    for row in rows[1:]:
        if not any(row):
            continue
        record = {}
        for i, val in enumerate(row):
            if i < len(headers):
                record[headers[i]] = str(val).strip() if val else ""
        prospects.append(record)

    return prospects, ""


def _normalize_industry(industry: str) -> str:
    """将行业名称标准化到预定义类别。"""
    if not industry:
        return "other"

    industry_lower = industry.lower()

    # 直接匹配
    if industry_lower in INDUSTRY_TEMPLATES:
        return industry_lower

    # 关键词匹配（顺序重要：更具体的类别放前面）
    keyword_map = {
        "medical": ["医疗", "健康", "medical", "health", "pharma", "hospital", "clinic"],
        "electronics": ["电子", "电器", "electronic", "consumer", "digital", "iot", "semiconductor", "led", "lighting", "solar"],
        "automotive": ["汽车", "汽配", "auto", "car", "vehicle", "motor"],
        "textiles": ["纺织", "服装", "textile", "garment", "apparel", "fabric", "clothing"],
        "food": ["食品", "农产", "food", "beverage", "agriculture", "organic"],
        "machinery": ["机械", "设备", "machine", "equipment", "industrial", "manufacturing"],
        "construction": ["建材", "家居", "construction", "building", "furniture", "home"],
        "chemical": ["化工", "原材料", "chemical", "material", "plastic", "polymer"],
    }

    for category, keywords in keyword_map.items():
        if any(kw in industry_lower for kw in keywords):
            return category

    return "other"


# ---------------------------------------------------------------------------
# 推送任务（Campaign）管理
# ---------------------------------------------------------------------------

def create_campaign(
    username: str,
    campaign_name: str,
    prospects: list[dict],
    product_info: str,
    company_intro: str = "",
    sender_name: str = "",
    forward_email: str = "",
    forward_channel: str = "email",
    auto_reply_enabled: bool = True,
) -> dict:
    """
    创建一个推送任务。

    Args:
        username: 当前用户
        campaign_name: 任务名称
        prospects: 解析后的客户列表
        product_info: 产品信息描述
        company_intro: 公司简介（可选）
        sender_name: 发件人显示名
        forward_email: 重点邮件转发目标邮箱
        forward_channel: 转发渠道 (email/webhook)
        auto_reply_enabled: 是否开启自动回复

    Returns:
        campaign dict
    """
    campaign_id = secrets.token_hex(8)

    campaign = {
        "id": campaign_id,
        "name": campaign_name,
        "status": "created",  # created / running / paused / completed
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "product_info": product_info,
        "company_intro": company_intro,
        "sender_name": sender_name,
        "forward_email": forward_email,
        "forward_channel": forward_channel,
        "auto_reply_enabled": auto_reply_enabled,
        "prospects": prospects,
        "stats": {
            "total": len(prospects),
            "sent": 0,
            "failed": 0,
            "opened": 0,
            "replied": 0,
            "important": 0,
        },
        "results": [],  # 每封邮件的发送结果
    }

    # 持久化
    campaigns = load_user_json(username, _CAMPAIGNS_FILE, default=[])
    campaigns.append(campaign)
    save_user_json(username, _CAMPAIGNS_FILE, campaigns)

    logger.info("Campaign created: %s (%s) by %s", campaign_name, campaign_id, username)
    return campaign


def get_campaigns(username: str) -> list[dict]:
    """获取用户的所有推送任务。"""
    return load_user_json(username, _CAMPAIGNS_FILE, default=[])


def get_campaign(username: str, campaign_id: str) -> dict | None:
    """按ID获取某个推送任务。"""
    campaigns = get_campaigns(username)
    for c in campaigns:
        if c["id"] == campaign_id:
            return c
    return None


def update_campaign(username: str, campaign_id: str, updates: dict) -> bool:
    """更新推送任务。"""
    campaigns = load_user_json(username, _CAMPAIGNS_FILE, default=[])
    for c in campaigns:
        if c["id"] == campaign_id:
            c.update(updates)
            c["updated_at"] = datetime.now().isoformat()
            save_user_json(username, _CAMPAIGNS_FILE, campaigns)
            return True
    return False


def delete_campaign(username: str, campaign_id: str) -> bool:
    """删除推送任务。"""
    campaigns = load_user_json(username, _CAMPAIGNS_FILE, default=[])
    original_len = len(campaigns)
    campaigns = [c for c in campaigns if c["id"] != campaign_id]
    if len(campaigns) < original_len:
        save_user_json(username, _CAMPAIGNS_FILE, campaigns)
        return True
    return False


# ---------------------------------------------------------------------------
# 核心推送逻辑
# ---------------------------------------------------------------------------

def generate_outreach_email(
    prospect: dict,
    product_info: str,
    company_intro: str = "",
    user_id: str = "default",
    username: str = "",
    use_catalog: bool = True,
) -> dict:
    """
    为单个客户生成个性化推介邮件。

    基于客户的行业信息、公司背景，AI自动生成针对性的产品推介内容。
    当 use_catalog=True 且 username 非空时，自动从本地产品目录匹配对口产品，
    将匹配到的产品详情注入 prompt，实现精准推介。

    Returns:
        {
            "subject": str,
            "body": str,
            "error": str,
            "matched_products": list[dict],  # 匹配到的本地产品
        }
    """
    from config.prompts import build_auto_outreach_prompt
    from utils.ai_client import call_llm

    industry = prospect.get("industry", "other")
    industry_info = INDUSTRY_TEMPLATES.get(industry, INDUSTRY_TEMPLATES["other"])

    # ── 本地产品目录匹配 ──────────────────────────────────
    matched_products = []
    matched_product_text = ""
    if use_catalog and username:
        from utils.product_catalog import (
            format_matched_products_for_prompt,
            match_products_for_prospect,
        )

        matched_products = match_products_for_prospect(
            username=username,
            prospect_industry=industry,
            prospect_product_interest=prospect.get("product_interest", ""),
            limit=3,
        )
        if matched_products:
            matched_product_text = format_matched_products_for_prompt(matched_products)
            logger.debug(
                "Matched %d catalog products for %s (industry=%s)",
                len(matched_products),
                prospect.get("email", ""),
                industry,
            )

    # 合并产品信息：本地目录匹配优先，用户手动输入作为补充
    effective_product_info = _build_effective_product_info(
        product_info=product_info,
        matched_product_text=matched_product_text,
    )

    prompt, system = build_auto_outreach_prompt(
        email=prospect.get("email", ""),
        company=prospect.get("company", ""),
        contact_name=prospect.get("contact_name", ""),
        industry=industry_info["label"],
        industry_focus=industry_info["focus"],
        industry_pain_points=industry_info["pain_points"],
        country=prospect.get("country", ""),
        product_info=effective_product_info,
        company_intro=company_intro,
        product_interest=prospect.get("product_interest", ""),
        matched_products=matched_product_text,
    )

    result = call_llm(prompt, system, user_id=user_id)

    if result.startswith("⚠️"):
        return {"subject": "", "body": "", "error": result, "matched_products": []}

    # 解析 Subject 和 Body
    subject = ""
    body = result
    for line in result.splitlines():
        if line.strip().lower().startswith("subject:"):
            subject = line.strip()[len("subject:"):].strip()
            body = result[result.index("\n", result.index(line)) + 1:].strip()
            break

    if not subject:
        subject = f"Partnership Opportunity - {product_info[:30]}"

    return {
        "subject": subject,
        "body": body,
        "error": "",
        "matched_products": matched_products,
    }


def run_campaign_step(
    username: str,
    campaign_id: str,
    user_id: str = "default",
) -> Generator[dict, None, None]:
    """
    逐步执行推送任务（生成器模式，便于UI实时更新进度）。

    Yields:
        {"index": int, "email": str, "status": "sent"|"failed"|"skipped", "detail": str}
    """
    from utils.email_service import send_ai_generated_email

    campaign = get_campaign(username, campaign_id)
    if not campaign:
        yield {"index": -1, "email": "", "status": "failed", "detail": "任务不存在"}
        return

    # 更新状态为running
    update_campaign(username, campaign_id, {"status": "running"})

    prospects = campaign.get("prospects", [])
    product_info = campaign.get("product_info", "")
    company_intro = campaign.get("company_intro", "")
    sender_name = campaign.get("sender_name", "")
    results = campaign.get("results", [])
    sent_emails = {r["email"] for r in results if r.get("status") == "sent"}

    stats = campaign.get("stats", {})

    for i, prospect in enumerate(prospects):
        email = prospect.get("email", "")

        # 跳过已发送的
        if email in sent_emails:
            yield {"index": i, "email": email, "status": "skipped", "detail": "已发送"}
            continue

        # 生成邮件
        email_data = generate_outreach_email(
            prospect=prospect,
            product_info=product_info,
            company_intro=company_intro,
            user_id=user_id,
            username=username,
            use_catalog=True,
        )

        if email_data["error"]:
            result_entry = {
                "email": email,
                "company": prospect.get("company", ""),
                "contact_name": prospect.get("contact_name", ""),
                "status": "failed",
                "error": email_data["error"],
                "timestamp": datetime.now().isoformat(),
            }
            results.append(result_entry)
            stats["failed"] = stats.get("failed", 0) + 1
            yield {"index": i, "email": email, "status": "failed", "detail": email_data["error"]}
            continue

        # 发送邮件
        ok, msg = send_ai_generated_email(
            to_email=email,
            subject=email_data["subject"],
            body=email_data["body"],
            from_name=sender_name,
            campaign=campaign.get("name", ""),
        )

        if ok:
            result_entry = {
                "email": email,
                "company": prospect.get("company", ""),
                "contact_name": prospect.get("contact_name", ""),
                "status": "sent",
                "subject": email_data["subject"],
                "body": email_data["body"],
                "timestamp": datetime.now().isoformat(),
            }
            stats["sent"] = stats.get("sent", 0) + 1
            yield {"index": i, "email": email, "status": "sent", "detail": f"已发送: {email_data['subject'][:40]}"}
        else:
            result_entry = {
                "email": email,
                "company": prospect.get("company", ""),
                "contact_name": prospect.get("contact_name", ""),
                "status": "failed",
                "error": msg,
                "timestamp": datetime.now().isoformat(),
            }
            stats["failed"] = stats.get("failed", 0) + 1
            yield {"index": i, "email": email, "status": "failed", "detail": msg}

        results.append(result_entry)

        # 每发一封更新一次持久化
        update_campaign(username, campaign_id, {"results": results, "stats": stats})

    # 完成
    update_campaign(username, campaign_id, {"status": "completed", "results": results, "stats": stats})


# ---------------------------------------------------------------------------
# 自动回复（识别意图 + 生成回复）
# ---------------------------------------------------------------------------

def auto_reply_to_customer(
    customer_email: str,
    customer_message: str,
    campaign_id: str,
    username: str,
    user_id: str = "default",
) -> dict:
    """
    自动识别客户回复意图并生成合适的回复。

    流程:
    1. 识别客户意图（感兴趣/需要信息/砍价/下单等）
    2. 根据意图生成针对性回复
    3. 如果是重点邮件（下单意向/大客户），触发转发

    Returns:
        {
            "intent": str,
            "is_important": bool,
            "reply_subject": str,
            "reply_body": str,
            "forwarded": bool,
            "error": str,
        }
    """
    from config.prompts import build_auto_reply_prompt
    from utils.ai_client import call_llm

    # 获取campaign上下文
    campaign = get_campaign(username, campaign_id)
    product_info = campaign.get("product_info", "") if campaign else ""
    company_intro = campaign.get("company_intro", "") if campaign else ""

    # 识别意图并生成回复
    prompt, system = build_auto_reply_prompt(
        customer_email=customer_email,
        customer_message=customer_message,
        product_info=product_info,
        company_intro=company_intro,
    )

    result = call_llm(prompt, system, user_id=user_id)

    if result.startswith("⚠️"):
        return {
            "intent": "unknown",
            "is_important": False,
            "reply_subject": "",
            "reply_body": "",
            "forwarded": False,
            "error": result,
        }

    # 解析AI回复结果
    intent = _extract_section(result, "INTENT:")
    is_important = _check_importance(customer_message, intent)
    reply_subject = _extract_section(result, "REPLY_SUBJECT:")
    reply_body = _extract_section(result, "REPLY_BODY:")

    if not reply_body:
        # fallback: 直接使用整个结果作为回复
        reply_body = result
        reply_subject = f"Re: Your inquiry"

    # 重点邮件转发
    forwarded = False
    if is_important and campaign:
        forward_email = campaign.get("forward_email", "")
        if forward_email:
            forwarded = _forward_important(
                username=username,
                forward_to=forward_email,
                original_from=customer_email,
                original_message=customer_message,
                intent=intent,
                campaign_name=campaign.get("name", ""),
            )

    # 记录日志
    _log_outreach_event(username, {
        "type": "auto_reply",
        "campaign_id": campaign_id,
        "customer_email": customer_email,
        "intent": intent,
        "is_important": is_important,
        "forwarded": forwarded,
        "timestamp": datetime.now().isoformat(),
    })

    return {
        "intent": intent,
        "is_important": is_important,
        "reply_subject": reply_subject,
        "reply_body": reply_body,
        "forwarded": forwarded,
        "error": "",
    }


def _check_importance(message: str, intent: str) -> bool:
    """判断邮件是否为重点邮件。"""
    message_lower = message.lower()

    # 意图关键词
    important_intents = ["下单", "purchase", "order", "buy", "sample", "样品", "采购"]
    if any(kw in intent.lower() for kw in important_intents):
        return True

    # 内容关键词
    if any(kw in message_lower for kw in IMPORTANT_KEYWORDS):
        return True

    return False


def _forward_important(
    username: str,
    forward_to: str,
    original_from: str,
    original_message: str,
    intent: str,
    campaign_name: str,
) -> bool:
    """转发重点邮件到指定邮箱。"""
    from utils.email_service import send_email, is_email_configured
    from utils.notifications import notify

    if not is_email_configured():
        logger.warning("Cannot forward email - SMTP not configured")
        return False

    subject = f"🔥 [重点客户回复] {original_from} - {campaign_name}"
    body = (
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🔥 重点客户邮件提醒\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📧 客户邮箱: {original_from}\n"
        f"🎯 识别意图: {intent}\n"
        f"📋 推送任务: {campaign_name}\n"
        f"⏰ 时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
        f"━━ 客户原文 ━━━━━━━━━━━━━━━━\n\n"
        f"{original_message}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"请尽快跟进此客户！\n"
        f"登录外贸AI助手查看详情: https://trade-ai-helper.streamlit.app\n"
    )

    ok, msg = send_email(forward_to, subject, body)

    # 同时发送应用内通知
    try:
        notify(
            username,
            "hot_lead",
            message=f"🔥 重点客户回复: {original_from} ({intent})",
            data={"campaign": campaign_name, "customer": original_from},
            customer=original_from,
        )
    except Exception as e:
        logger.debug("Notification failed (non-critical): %s", e)

    if ok:
        logger.info("Important email forwarded to %s from %s", forward_to, original_from)
    else:
        logger.error("Forward failed: %s", msg)

    return ok


def _build_effective_product_info(product_info: str, matched_product_text: str) -> str:
    """
    合并用户手动输入的产品信息和本地目录匹配到的产品详情。

    策略：
    - 如果有匹配产品，以匹配产品为主体，用户输入作为补充背景
    - 如果没有匹配产品，直接使用用户输入
    """
    if not matched_product_text:
        return product_info

    if product_info:
        return (
            f"[From Product Catalog - Best Match for Customer's Industry]\n"
            f"{matched_product_text}\n\n"
            f"[Additional Product/Service Context]\n"
            f"{product_info}"
        )
    return matched_product_text


# ---------------------------------------------------------------------------
# 辅助函数
# ---------------------------------------------------------------------------

def _extract_section(text: str, marker: str) -> str:
    """从AI返回文本中提取标记后的内容。"""
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if marker.lower() in line.lower():
            # 返回标记后面的内容
            content = line.split(":", 1)[-1].strip() if ":" in line else ""
            if not content and i + 1 < len(lines):
                # 可能内容在下一行
                remaining = []
                for j in range(i + 1, len(lines)):
                    if lines[j].strip() and any(
                        lines[j].strip().upper().startswith(m)
                        for m in ["INTENT:", "REPLY_SUBJECT:", "REPLY_BODY:", "IMPORTANCE:"]
                    ):
                        break
                    remaining.append(lines[j])
                content = "\n".join(remaining).strip()
            return content
    return ""


def _log_outreach_event(username: str, event: dict) -> None:
    """记录推送事件日志。"""
    try:
        logs = load_user_json(username, _OUTREACH_LOG_FILE, default=[])
        logs.append(event)
        # 保留最近500条
        if len(logs) > 500:
            logs = logs[-500:]
        save_user_json(username, _OUTREACH_LOG_FILE, logs)
    except Exception as e:
        logger.debug("Log write failed: %s", e)


def get_outreach_logs(username: str, limit: int = 50) -> list[dict]:
    """获取推送日志。"""
    logs = load_user_json(username, _OUTREACH_LOG_FILE, default=[])
    logs.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    return logs[:limit]


def get_campaign_summary(username: str) -> dict:
    """获取所有推送任务的汇总统计。"""
    campaigns = get_campaigns(username)
    total_sent = sum(c.get("stats", {}).get("sent", 0) for c in campaigns)
    total_failed = sum(c.get("stats", {}).get("failed", 0) for c in campaigns)
    total_replied = sum(c.get("stats", {}).get("replied", 0) for c in campaigns)
    total_important = sum(c.get("stats", {}).get("important", 0) for c in campaigns)

    return {
        "total_campaigns": len(campaigns),
        "active_campaigns": sum(1 for c in campaigns if c.get("status") == "running"),
        "total_sent": total_sent,
        "total_failed": total_failed,
        "total_replied": total_replied,
        "total_important": total_important,
        "success_rate": round(total_sent / max(total_sent + total_failed, 1) * 100, 1),
    }
