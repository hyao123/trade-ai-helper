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
import time
from datetime import datetime
from typing import Generator

from utils.auto_outreach_config import (
    EMAIL_RE,
    IMPORTANT_KEYWORDS,
    INDUSTRY_TEMPLATES,
    MAX_PROSPECTS_PER_CAMPAIGN,
    PERSIST_BATCH_SIZE,
    SEND_INTERVAL_SECONDS,
)
from utils.logger import get_logger
from utils.repositories import (
    campaign_results_collection,
    load_campaign_results,
    load_campaigns,
    save_campaign_results,
    save_campaigns,
)

logger = get_logger("auto_outreach")

_CAMPAIGNS_FILE = "outreach_campaigns.json"
_OUTREACH_LOG_FILE = "outreach_log.json"
_CAMPAIGN_RESULTS_PREFIX = "campaign_results_"  # {campaign_id}.json

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
        if not email or not EMAIL_RE.match(email):
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
        return [], "未找到有效的客户记录（需要至少包含 email 列，且邮箱格式正确）"

    # 限制单次推送上限
    if len(valid_prospects) > MAX_PROSPECTS_PER_CAMPAIGN:
        error = (
            f"⚠️ 客户列表共 {len(valid_prospects)} 条有效记录，"
            f"超出单次推送上限 {MAX_PROSPECTS_PER_CAMPAIGN} 封。"
            f"已截取前 {MAX_PROSPECTS_PER_CAMPAIGN} 条，请分批推送。"
        )
        valid_prospects = valid_prospects[:MAX_PROSPECTS_PER_CAMPAIGN]
        return valid_prospects, error

    return valid_prospects, error


def _normalize_header(name: str, index: int) -> str:
    """Normalize a CSV/Excel header to the validator's expected key form.

    - strips surrounding whitespace / BOM
    - lowercases
    - replaces internal spaces with underscores so "Contact Name" -> "contact_name",
      matching the validated keys (email, company, contact_name, product, ...).
    """
    if not name:
        return f"col_{index}"
    normalized = name.strip().lower().replace(" ", "_")
    return normalized or f"col_{index}"


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
    raw_rows = list(reader)
    if not raw_rows:
        return [], ""

    # Normalize headers (lowercase + spaces->underscores) so that CSV files with
    # capitalized/multi-word headers ("Email", "Contact Name") validate correctly
    # instead of silently dropping every row in the required-field check below.
    fieldmap = {
        h: _normalize_header(h, i)
        for i, h in enumerate(reader.fieldnames or [])
    }
    prospects = []
    for row in raw_rows:
        record = {
            fieldmap.get(h, h): (str(v).strip() if v is not None else "")
            for h, v in row.items()
        }
        prospects.append(record)
    return prospects, ""


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

    headers = [_normalize_header(h, i) for i, h in enumerate(rows[0])]
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
    campaigns = load_campaigns(username)
    campaigns.append(campaign)
    save_campaigns(username, campaigns)

    logger.info("Campaign created: %s (%s) by %s", campaign_name, campaign_id, username)
    return campaign


def get_campaigns(username: str) -> list[dict]:
    """获取用户的所有推送任务。"""
    return load_campaigns(username)


def get_campaign(username: str, campaign_id: str) -> dict | None:
    """按ID获取某个推送任务。"""
    campaigns = get_campaigns(username)
    for c in campaigns:
        if c["id"] == campaign_id:
            return c
    return None


def update_campaign(username: str, campaign_id: str, updates: dict) -> bool:
    """更新推送任务。"""
    campaigns = load_campaigns(username)
    for c in campaigns:
        if c["id"] == campaign_id:
            c.update(updates)
            c["updated_at"] = datetime.now().isoformat()
            save_campaigns(username, campaigns)
            return True
    return False


def delete_campaign(username: str, campaign_id: str) -> bool:
    """删除推送任务。"""
    campaigns = load_campaigns(username)
    original_len = len(campaigns)
    campaigns = [c for c in campaigns if c["id"] != campaign_id]
    if len(campaigns) < original_len:
        save_campaigns(username, campaigns)
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

    # ── 自动读取注册企业介绍 ──────────────────────────────
    effective_company_intro = company_intro
    if not effective_company_intro and username:
        effective_company_intro = _get_company_profile_for_outreach(username)

    prompt, system = build_auto_outreach_prompt(
        email=prospect.get("email", ""),
        company=prospect.get("company", ""),
        contact_name=prospect.get("contact_name", ""),
        industry=industry_info["label"],
        industry_focus=industry_info["focus"],
        industry_pain_points=industry_info["pain_points"],
        country=prospect.get("country", ""),
        product_info=effective_product_info,
        company_intro=effective_company_intro,
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
    send_interval: float = SEND_INTERVAL_SECONDS,
) -> Generator[dict, None, None]:
    """
    逐步执行推送任务（生成器模式，便于UI实时更新进度）。

    Features:
    - 每封邮件之间自动间隔 send_interval 秒（防SMTP限流）
    - 每 PERSIST_BATCH_SIZE 封才持久化一次结果（减少IO）
    - 结果存储在独立文件中（减小主campaign文件体积）

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

    # 从独立结果文件加载已有结果
    results = _load_campaign_results(username, campaign_id)
    sent_emails = {r["email"] for r in results if r.get("status") == "sent"}

    stats = campaign.get("stats", {})
    unsaved_count = 0  # 追踪未持久化的结果数

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
            unsaved_count += 1
            yield {"index": i, "email": email, "status": "failed", "detail": email_data["error"]}
            # 失败不需要间隔
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
                "body": email_data["body"][:500],  # 只保留前500字符节省存储
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
        unsaved_count += 1

        # 批量持久化（每N封写一次，减少IO）
        if unsaved_count >= PERSIST_BATCH_SIZE:
            _save_campaign_results(username, campaign_id, results)
            update_campaign(username, campaign_id, {"stats": stats})
            unsaved_count = 0

        # 发送间隔（防SMTP限流）
        time.sleep(send_interval)

    # 最终持久化剩余结果
    _save_campaign_results(username, campaign_id, results)
    update_campaign(username, campaign_id, {"status": "completed", "stats": stats})


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
        reply_subject = "Re: Your inquiry"

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
    from utils.email_service import is_email_configured, send_email
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


def _get_company_profile_for_outreach(username: str) -> str:
    """
    从用户注册资料/偏好设置中读取企业介绍信息，用于自动推送。

    优先读取 company_description，如不存在则拼接 company_name + main_products。
    """
    from utils.storage import load_user_json

    prefs = load_user_json(username, "prefs.json", default={})
    parts = []

    company_name = prefs.get("company_name", "").strip()
    company_desc = prefs.get("company_description", "").strip()
    main_products = prefs.get("main_products", "").strip()
    company_industry = prefs.get("company_industry", "").strip()

    if company_desc:
        # 完整企业简介已配置
        parts.append(company_desc)
    elif company_name:
        parts.append(company_name)

    if main_products and main_products not in (company_desc or ""):
        parts.append(f"Main Products: {main_products}")

    if company_industry and company_industry != "other":
        industry_label = INDUSTRY_TEMPLATES.get(company_industry, {}).get("label", "")
        if industry_label and industry_label not in " ".join(parts):
            parts.append(f"Industry: {industry_label}")

    return " | ".join(parts) if parts else ""


# ---------------------------------------------------------------------------
# Campaign 结果独立存储（减少主文件IO压力）
# ---------------------------------------------------------------------------

def _get_results_filename(campaign_id: str) -> str:
    """获取campaign结果的独立存储文件名。"""
    return f"{_CAMPAIGN_RESULTS_PREFIX}{campaign_id}.json"


def _load_campaign_results(username: str, campaign_id: str) -> list[dict]:
    """从独立文件加载campaign发送结果。"""
    results = load_campaign_results(username, campaign_id)
    # 兼容：如果独立文件为空，尝试从主campaign文件迁移
    if not results:
        campaign = get_campaign(username, campaign_id)
        if campaign and campaign.get("results"):
            results = campaign["results"]
            # 迁移到独立文件
            _save_campaign_results(username, campaign_id, results)
            # 清理主文件中的results字段
            update_campaign(username, campaign_id, {"results": []})
    return results


def _save_campaign_results(username: str, campaign_id: str, results: list[dict]) -> None:
    """将campaign发送结果保存到独立文件。"""
    save_campaign_results(username, campaign_id, results)


def get_campaign_results(username: str, campaign_id: str) -> list[dict]:
    """公开接口：获取campaign的发送结果。"""
    return _load_campaign_results(username, campaign_id)


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



# ───────────────────────────────────────────────────────────────────────────
# Drip Campaign 多步序列：在现有 campaign 数据结构上扩展
# ───────────────────────────────────────────────────────────────────────────

def create_drip_campaign(
    username: str,
    campaign_name: str,
    prospects: list[dict],
    product_info: str,
    sequence_template: str = "b2b_standard",
    company_intro: str = "",
    sender_name: str = "",
    forward_email: str = "",
    forward_channel: str = "email",
    auto_reply_enabled: bool = True,
    start_at: datetime | None = None,
) -> dict:
    """
    创建一个开启序列模式的推送任务。

    比 create_campaign() 多做的事：
    - 解析 sequence_template 并把 steps 快照到 campaign
    - 为每个 prospect 初始化 prospects_state（D0送达时间）
    - sequence_enabled=True 让 tick 流程接管发送

    Args:
        sequence_template: 模板名（见 drip_sequences.SEQUENCE_TEMPLATES）
        start_at: 序列起始时间（D0），默认现在
    """
    from utils.drip_sequences import get_template, init_prospects_state

    tpl = get_template(sequence_template)
    if not tpl:
        raise ValueError(f"Unknown sequence template: {sequence_template}")

    steps = list(tpl["steps"])  # snapshot
    state = init_prospects_state(prospects, steps, start_at=start_at)

    # 复用基础 create_campaign，再写入序列字段
    campaign = create_campaign(
        username=username,
        campaign_name=campaign_name,
        prospects=prospects,
        product_info=product_info,
        company_intro=company_intro,
        sender_name=sender_name,
        forward_email=forward_email,
        forward_channel=forward_channel,
        auto_reply_enabled=auto_reply_enabled,
    )

    update_campaign(username, campaign["id"], {
        "sequence_enabled": True,
        "sequence_template": sequence_template,
        "sequence_template_label": tpl["label"],
        "sequence_steps": steps,
        "prospects_state": state,
    })

    logger.info(
        "Drip campaign created: %s (%s) template=%s, %d steps × %d prospects",
        campaign_name, campaign["id"], sequence_template, len(steps), len(state),
    )
    # Return refreshed campaign
    return get_campaign(username, campaign["id"]) or campaign


def tick_drip_campaign(
    username: str,
    campaign_id: str,
    user_id: str = "default",
    send_interval: float = SEND_INTERVAL_SECONDS,
    max_per_tick: int = 50,
) -> Generator[dict, None, None]:
    """
    Run one "tick" of a drip campaign: send all prospects whose next step is due.

    Designed to be called periodically (manually via UI button, or by a
    scheduler). Each call sends 0 or more emails — only those whose
    next_send_at has passed.

    Yields per-send progress dicts (same shape as run_campaign_step):
        {"index", "email", "status", "detail", "step", "step_label"}

    Args:
        max_per_tick: cap on emails sent in this tick (defaults to 50,
                      protecting against an unbounded burst if many prospects
                      come due simultaneously)
    """
    from config.prompts import build_drip_step_prompt
    from utils.ai_client import call_llm
    from utils.drip_sequences import advance_state, get_due_prospects
    from utils.email_service import send_ai_generated_email

    campaign = get_campaign(username, campaign_id)
    if not campaign:
        yield {"index": -1, "email": "", "status": "failed",
               "detail": "任务不存在", "step": -1, "step_label": ""}
        return

    if not campaign.get("sequence_enabled"):
        yield {"index": -1, "email": "", "status": "failed",
               "detail": "此 campaign 未开启序列模式", "step": -1, "step_label": ""}
        return

    steps = campaign.get("sequence_steps", [])
    state = campaign.get("prospects_state", {})
    if not steps or not state:
        yield {"index": -1, "email": "", "status": "failed",
               "detail": "序列配置缺失", "step": -1, "step_label": ""}
        return

    due = get_due_prospects(campaign)
    if not due:
        return  # nothing to do this tick

    due = due[:max_per_tick]
    logger.info("Drip tick: campaign=%s, due=%d (capped to %d)",
                campaign_id, len(due), max_per_tick)

    update_campaign(username, campaign_id, {"status": "running"})

    product_info = campaign.get("product_info", "")
    company_intro = campaign.get("company_intro", "")
    sender_name = campaign.get("sender_name", "")

    # Auto-pull seller profile if intro empty
    effective_company_intro = company_intro or _get_company_profile_for_outreach(username)

    results = _load_campaign_results(username, campaign_id)
    stats = campaign.get("stats", {})

    for i, (email, prospect, step_idx) in enumerate(due):
        step = steps[step_idx]
        step_type = step.get("step_type", "followup")
        step_label = step.get("label", f"Step {step_idx + 1}")
        industry = prospect.get("industry", "other")
        industry_info = INDUSTRY_TEMPLATES.get(industry, INDUSTRY_TEMPLATES["other"])

        # ── catalog matching (same as single-shot) ─────────────────────
        matched_product_text = ""
        try:
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
        except Exception as e:
            logger.debug("Catalog match skipped: %s", e)

        # ── collect prior subjects from history to avoid repetition ────
        prior_subjects = []
        ps = state.get(email, {})
        for h in ps.get("history", []):
            if h.get("subject"):
                prior_subjects.append(h["subject"])

        # ── build step-specific prompt ─────────────────────────────────
        prompt, system = build_drip_step_prompt(
            step_type=step_type,
            step_index=step_idx,
            total_steps=len(steps),
            prospect=prospect,
            industry=industry_info["label"],
            industry_focus=industry_info["focus"],
            industry_pain_points=industry_info["pain_points"],
            product_info=product_info,
            company_intro=effective_company_intro,
            matched_products=matched_product_text,
            previous_subjects=prior_subjects,
        )

        ai_result = call_llm(prompt, system, user_id=user_id)
        if ai_result.startswith("⚠️"):
            results.append({
                "email": email,
                "step": step_idx,
                "step_label": step_label,
                "status": "failed",
                "error": ai_result,
                "timestamp": datetime.now().isoformat(),
            })
            stats["failed"] = stats.get("failed", 0) + 1
            yield {"index": i, "email": email, "status": "failed",
                   "detail": ai_result, "step": step_idx, "step_label": step_label}
            continue

        # Parse subject + body
        subject = ""
        body = ai_result
        for line in ai_result.splitlines():
            if line.strip().lower().startswith("subject:"):
                subject = line.strip()[len("subject:"):].strip()
                body = ai_result[ai_result.index("\n", ai_result.index(line)) + 1:].strip()
                break
        if not subject:
            subject = f"[{step_label}] {product_info[:30]}"

        # ── send ────────────────────────────────────────────────────────
        ok, msg = send_ai_generated_email(
            to_email=email,
            subject=subject,
            body=body,
            from_name=sender_name,
            campaign=f"{campaign.get('name', '')}/step{step_idx}",
        )

        sent_at = datetime.now()
        if ok:
            results.append({
                "email": email,
                "company": prospect.get("company", ""),
                "contact_name": prospect.get("contact_name", ""),
                "step": step_idx,
                "step_label": step_label,
                "status": "sent",
                "subject": subject,
                "body": body[:500],
                "timestamp": sent_at.isoformat(),
            })
            stats["sent"] = stats.get("sent", 0) + 1
            # Advance prospect state
            advance_state(state, email, step_idx, sent_at, steps, subject=subject)
            yield {
                "index": i, "email": email, "status": "sent",
                "detail": f"[{step_label}] {subject[:40]}",
                "step": step_idx, "step_label": step_label,
            }
        else:
            results.append({
                "email": email,
                "step": step_idx,
                "step_label": step_label,
                "status": "failed",
                "error": msg,
                "timestamp": sent_at.isoformat(),
            })
            stats["failed"] = stats.get("failed", 0) + 1
            # Don't advance state on send failure — will retry next tick
            yield {
                "index": i, "email": email, "status": "failed",
                "detail": msg, "step": step_idx, "step_label": step_label,
            }

        # Persist state every step (low IO since drip ticks are small)
        update_campaign(username, campaign_id, {
            "prospects_state": state, "stats": stats,
        })
        _save_campaign_results(username, campaign_id, results)

        # Throttle between sends
        time.sleep(send_interval)

    # Final persist + check if all done
    summary = {
        ps.get("status", "active") for ps in state.values()
    }
    if "active" not in summary:
        update_campaign(username, campaign_id, {"status": "completed"})
    else:
        update_campaign(username, campaign_id, {"status": "running"})


def mark_campaign_reply(
    username: str,
    campaign_id: str,
    customer_email: str,
) -> bool:
    """
    Mark a prospect as having replied — pauses their drip sequence.

    Called by inbox integration / auto_reply flow when a customer reply is
    detected. Idempotent: re-calling has no effect.
    """
    from utils.drip_sequences import mark_replied

    campaign = get_campaign(username, campaign_id)
    if not campaign or not campaign.get("sequence_enabled"):
        return False

    state = campaign.get("prospects_state", {})
    if not mark_replied(state, customer_email):
        return False

    stats = campaign.get("stats", {})
    stats["replied"] = stats.get("replied", 0) + 1

    update_campaign(username, campaign_id, {
        "prospects_state": state, "stats": stats,
    })
    logger.info("Drip reply marked: %s in campaign %s", customer_email, campaign_id)
    return True


def get_drip_progress(username: str, campaign_id: str) -> dict:
    """
    Get drip campaign progress for UI display.

    Returns:
        {
            "enabled": bool,
            "template": str,
            "template_label": str,
            "step_count": int,
            "summary": {active, replied, completed, ...},
            "step_completions": list[int],   # how many got step N
            "reply_rate_per_step": list[float],
        }
    """
    from utils.drip_sequences import (
        count_step_completions,
        reply_rate_per_step,
        summarize_state,
    )

    campaign = get_campaign(username, campaign_id)
    if not campaign or not campaign.get("sequence_enabled"):
        return {"enabled": False}

    steps = campaign.get("sequence_steps", [])
    state = campaign.get("prospects_state", {})
    step_count = len(steps)

    return {
        "enabled": True,
        "template": campaign.get("sequence_template", ""),
        "template_label": campaign.get("sequence_template_label", ""),
        "steps": steps,
        "step_count": step_count,
        "summary": summarize_state(state),
        "step_completions": count_step_completions(state, step_count),
        "reply_rate_per_step": reply_rate_per_step(state, step_count),
    }
