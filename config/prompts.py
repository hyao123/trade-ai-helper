"""
config/prompts.py
-----------------
所有 AI Prompt 模板统一管理。
每个函数返回 (prompt: str, system_prompt: str | None) 元组。
"""
from utils.sanitize import sanitize_input, sanitize_prompt_param

# ---------------------------------------------------------------------------
# 开发信
# ---------------------------------------------------------------------------
EMAIL_STYLES: dict[str, str] = {
    "简洁专业": "简洁有力，50-80词，直接说明产品优势和合作邀请",
    "正式商务": "正式专业，100-150词，详细介绍产品资质和公司实力",
    "亲切友好": "友好亲切，80-100词，建立个人关系，softer tone",
}

EMAIL_LANGUAGES: dict[str, str] = {
    "英语": "English",
    "西班牙语": "Spanish",
    "法语": "French",
    "德语": "German",
    "葡萄牙语": "Portuguese",
    "阿拉伯语": "Arabic",
    "俄语": "Russian",
}


def build_email_prompt(
    product: str,
    customer: str,
    features: str,
    tone: str = "简洁专业",
    language: str = "英语",
) -> tuple[str, str | None]:
    product = sanitize_prompt_param(product, "product")
    customer = sanitize_prompt_param(customer, "customer")
    features = sanitize_prompt_param(features, "features")
    style = EMAIL_STYLES.get(tone, EMAIL_STYLES["简洁专业"])
    lang_name = EMAIL_LANGUAGES.get(language, "English")
    system = f"你是一位有10年经验的外贸业务员，擅长撰写高转化率的{lang_name}开发信。"
    prompt = f"""请根据以下信息生成一封专业的{lang_name}开发信，同时生成一个吸引人的邮件主题行（Subject Line）：

- 产品: {product}
- 目标客户: {customer}
- 产品卖点: {features}
- 风格要求: {style}
- 输出语言: {lang_name}

输出格式（严格按此格式）：
Subject: [邮件主题行，不超过60字符，用{lang_name}写，突出核心价值]

[邮件正文开始，用{lang_name}写]
...邮件内容...
[Your Name]
[Your Company]

要求：
1. Subject Line 要简洁有力，能提高开信率
2. 邮件正文开头问候并说明如何得知客户
3. 简明介绍产品核心优势（2-3点）
4. 突出差异化卖点
5. 结尾包含明确的 Call to Action
6. 全文使用{lang_name}撰写

只输出纯文本，不要加 markdown 符号。"""
    return prompt, system


# ---------------------------------------------------------------------------
# 询盘回复
# ---------------------------------------------------------------------------
def build_inquiry_prompt(
    inquiry: str,
    customer_name: str = "",
    your_name: str = "",
    company_name: str = "",
) -> tuple[str, str | None]:
    inquiry = sanitize_input(inquiry, max_length=2000)
    customer_name = sanitize_prompt_param(customer_name, "customer_name")
    your_name = sanitize_prompt_param(your_name, "your_name")
    company_name = sanitize_prompt_param(company_name, "company_name")
    customer_info = f"客户姓名：{customer_name}" if customer_name else "（客户姓名未提供）"
    signature_name = your_name if your_name else "[Your Name]"
    signature_company = company_name if company_name else "[Your Company]"
    system = "你是一位专业外贸业务员，善于用英文回复客户询盘，语气专业友好。"
    prompt = f"""请回复以下客户询盘：

{customer_info}
询盘内容：
{inquiry}

回复要求：
1. 感谢客户询盘
2. 逐条回答客户问题
3. 给出合理报价区间（如无法确定则给范围并说明影响因素）
4. 主动询问客户其他需求（数量、规格、目标市场等）
5. 邀请进一步沟通（视频会议或邮件）
6. 签名：{signature_name} / {signature_company}

只输出英文邮件正文，不要加 markdown 符号。"""
    return prompt, system


# ---------------------------------------------------------------------------
# 产品介绍
# ---------------------------------------------------------------------------
LANG_MAP: dict[str, str] = {
    "英语": "English",
    "西班牙语": "Spanish",
    "法语": "French",
    "德语": "German",
    "日语": "Japanese",
}


def build_product_intro_prompt(
    product: str,
    features: str,
    target: str,
    languages: list[str],
) -> tuple[str, str | None]:
    product = sanitize_prompt_param(product, "product")
    features = sanitize_prompt_param(features, "features")
    target = sanitize_prompt_param(target, "target")
    langs = [LANG_MAP.get(l, l) for l in languages]
    lang_str = ", ".join(langs)
    system = "你是一位专业的外贸文案撰写师，擅长为B2B产品撰写多语言推广文案。"
    prompt = f"""请为以下产品撰写 {lang_str} 的产品介绍文案：

产品名称: {product}
产品特点: {features}
目标市场: {target}

每种语言的文案要求：
1. 简洁专业，约 80-120 词
2. 突出产品核心优势和差异化
3. 适合 B2B 外贸场景（采购商视角）
4. 包含：产品描述 → 主要优势 → 适用领域

格式：每种语言前加标题，如「## English」，语言之间用分隔线「---」。"""
    return prompt, system


# ---------------------------------------------------------------------------
# 跟进邮件
# ---------------------------------------------------------------------------
FOLLOWUP_STAGES: dict[str, str] = {
    "已报价": "报价后跟进，确认客户对报价的看法，温和询问是否有疑问或需要调整",
    "已发样": "样品跟进，询问客户收到样品后的测试反馈，表示期待进一步合作",
    "已谈判": "谈判阶段跟进，在价格/条款上表示一定灵活性，推动签单",
    "已下单": "订单确认感谢信，表达感谢并告知生产/发货时间节点",
    "长期未回复": "客户长时间未回复，温和重新激活，提供新价值或新资讯",
}


def build_followup_prompt(
    customer: str,
    stage: str,
    product: str = "",
) -> tuple[str, str | None]:
    customer = sanitize_prompt_param(customer, "customer")
    product = sanitize_prompt_param(product, "product")
    context = FOLLOWUP_STAGES.get(stage, "常规跟进")
    product_info = f"\n产品: {product}" if product else ""
    system = "你是一位有丰富经验的外贸业务员，擅长撰写专业但不令人厌烦的跟进邮件。"
    prompt = f"""请生成一封外贸跟进邮件：

客户: {customer}{product_info}
跟进阶段: {context}

要求：
1. 根据阶段选择合适的内容和语气
2. 专业但不过分催促，保持友好
3. 包含明确的下一步行动建议
4. 长度适中（60-100词）
5. 签名使用 [Your Name] / [Your Company]

只输出英文邮件正文，不要加 markdown 符号。"""
    return prompt, system



# ---------------------------------------------------------------------------
# Amazon / Shopify Listing 生成
# ---------------------------------------------------------------------------
LISTING_PLATFORMS: dict[str, str] = {
    "Amazon": "Amazon product listing",
    "Shopify": "Shopify product page",
    "Amazon + Shopify": "both Amazon listing and Shopify product page",
}


def build_listing_prompt(
    product: str,
    keywords: str,
    features: str,
    platform: str = "Amazon",
    category: str = "",
) -> tuple[str, str | None]:
    """构建产品上架 Listing 文案的 Prompt。"""
    product = sanitize_prompt_param(product, "product")
    keywords = sanitize_prompt_param(keywords, "keywords")
    features = sanitize_prompt_param(features, "features")
    category = sanitize_prompt_param(category, "category")
    platform_desc = LISTING_PLATFORMS.get(platform, "Amazon product listing")
    category_info = f"\n产品类目: {category}" if category else ""
    system = (
        "你是一位有5年经验的跨境电商运营专家，"
        "精通 Amazon SEO 和 Shopify 产品页面优化，擅长撰写高转化率的产品 Listing。"
    )
    prompt = f"""请为以下产品生成 {platform_desc} 的完整文案：

产品名称: {product}
核心关键词: {keywords}
产品卖点/参数: {features}{category_info}

请严格按以下格式输出（每个部分用标题标注）：

## Title
[产品标题，200字符以内，自然嵌入3-5个核心关键词，格式：品牌+核心关键词+主要特点+适用场景]

## Bullet Points
[5条卖点，每条以大写字母开头，80-150字符，突出不同维度：功能/材质/场景/售后/差异化]
• [第1条]
• [第2条]
• [第3条]
• [第4条]
• [第5条]

## Product Description
[150-300词产品描述，分2-3段，自然融入关键词，讲产品故事+解决什么问题+为什么选我们]

## Search Terms
[后台搜索词，用逗号分隔，总计不超过249字符，不要重复标题中已有的词]

## SEO Meta Description
[Shopify SEO 描述，155字符以内，含CTA]

输出纯英文，不要加 markdown 以外的格式符号。"""
    return prompt, system





# ---------------------------------------------------------------------------
# 社媒文案生成（LinkedIn / Instagram / Facebook）
# ---------------------------------------------------------------------------
SOCIAL_PLATFORMS: dict[str, str] = {
    "LinkedIn": "LinkedIn post for B2B professionals",
    "Instagram": "Instagram caption with hashtags",
    "Facebook Ad": "Facebook ad copy (short + long versions)",
    "All Platforms": "content for LinkedIn, Instagram, and Facebook",
}


def build_social_post_prompt(
    product: str,
    features: str,
    platform: str = "LinkedIn",
    audience: str = "",
    promo: str = "",
) -> tuple[str, str | None]:
    """构建社媒文案 Prompt。"""
    product = sanitize_prompt_param(product, "product")
    features = sanitize_prompt_param(features, "features")
    audience = sanitize_prompt_param(audience, "audience")
    promo = sanitize_prompt_param(promo, "promo")
    platform_desc = SOCIAL_PLATFORMS.get(platform, "social media post")
    audience_info = f"\n目标受众: {audience}" if audience else ""
    promo_info = f"\n促销/活动: {promo}" if promo else ""
    system = (
        "你是一位精通跨境电商社交媒体营销的文案专家，"
        "擅长为 B2B/B2C 产品撰写高互动率的社媒内容。"
    )
    prompt = f"""请为以下产品生成 {platform_desc} 文案：

产品: {product}
产品卖点: {features}{audience_info}{promo_info}

请按以下格式输出：

## LinkedIn Post
[100-150词，专业 B2B 风格，突出产品价值和行业洞察，含 CTA，适当使用换行提升可读性]

## Instagram Caption
[简短有力，含emoji，3-5个产品相关 hashtag + 3-5个行业通用 hashtag，含 CTA]

## Facebook Ad Copy
Short Version (25词以内):
[精炼广告标题，吸引点击]

Long Version (80-120词):
[详细广告正文，讲故事+痛点+解决方案+CTA]

输出纯英文，只输出文案内容。"""
    return prompt, system


# ---------------------------------------------------------------------------
# 批量开发信（Bulk Cold Email）
# ---------------------------------------------------------------------------
def build_bulk_email_prompt(
    company: str,
    contact_name: str,
    product: str,
    industry: str = "",
    country: str = "",
) -> tuple[str, str | None]:
    """构建批量开发信 Prompt，适合批量个性化发送场景。"""
    company = sanitize_prompt_param(company, "company")
    contact_name = sanitize_prompt_param(contact_name, "contact_name")
    product = sanitize_prompt_param(product, "product")
    industry = sanitize_prompt_param(industry, "industry")
    country = sanitize_prompt_param(country, "country")
    industry_info = f"\n行业: {industry}" if industry else ""
    country_info = f"\n国家/地区: {country}" if country else ""
    system = "你是一位有10年经验的外贸业务开发专家，擅长撰写高回复率的个性化批量开发信。"
    prompt = f"""Please generate a personalized cold email for bulk outreach with the following details:

Company: {company}
Contact Name: {contact_name}
Product: {product}{industry_info}{country_info}

Output format (strictly follow this format):
Subject: [Email subject line, under 60 characters, highlight core value proposition]

Dear {contact_name},

[Email body, 50-80 words, concise and professional]
- Open with a personalized reference to their company/industry
- Briefly introduce your product and 1-2 key advantages
- Include a clear Call to Action (schedule a call, request samples, etc.)

[Your Name]
[Your Company]

Requirements:
1. Subject line must be compelling and personalized
2. Opening must reference the recipient's company or industry specifically
3. Keep it short and scannable (suitable for bulk sending)
4. Professional but warm tone
5. Output in English, plain text only, no markdown symbols."""
    return prompt, system


# ---------------------------------------------------------------------------
# 谈判话术（Negotiation Scripts）
# ---------------------------------------------------------------------------
NEGOTIATION_SCENARIOS: dict[str, str] = {
    "客户砍价": "Customer is asking for a lower price / price negotiation",
    "要求延长账期": "Customer requests extended payment terms",
    "要求降低MOQ": "Customer wants to reduce minimum order quantity",
    "催货": "Customer is pressing for faster delivery / urgent shipment",
    "要求免费样品": "Customer requests free samples",
    "竞争对手比价": "Customer comparing prices with competitors",
}


def build_negotiation_prompt(
    scenario: str,
    product: str,
    current_offer: str,
    bottom_line: str,
) -> tuple[str, str | None]:
    """构建谈判话术 Prompt。"""
    scenario = sanitize_prompt_param(scenario, "scenario")
    product = sanitize_prompt_param(product, "product")
    current_offer = sanitize_prompt_param(current_offer, "current_offer")
    bottom_line = sanitize_prompt_param(bottom_line, "bottom_line")
    scenario_desc = NEGOTIATION_SCENARIOS.get(scenario, scenario)
    system = "你是一位有15年经验的外贸谈判专家，精通国际贸易谈判策略和话术技巧。"
    prompt = f"""Please generate a negotiation response script for the following scenario:

Scenario: {scenario_desc}
Product: {product}
Current Offer: {current_offer}
Bottom Line: {bottom_line}

Please output in the following format:

## Opening Response
[Professional opening response to the customer's request, 2-3 sentences, acknowledge their concern while maintaining your position]

## Counter-Offer Suggestion
[Specific counter-offer with reasoning, show flexibility while protecting margins, include numbers/terms where applicable]

## Backup Plan
[Alternative solution if counter-offer is rejected, creative options like volume discounts, bundling, adjusted terms]

## Key Phrases
[5-8 useful English phrases for this negotiation scenario, each on a new line with brief context]

Requirements:
1. All content in English
2. Professional and diplomatic tone
3. Protect seller's interests while maintaining relationship
4. Include specific tactics relevant to the scenario
5. Output plain text only, no markdown symbols except section headers."""
    return prompt, system


# ---------------------------------------------------------------------------
# 节日祝福（Holiday Greetings）
# ---------------------------------------------------------------------------
HOLIDAYS: list[str] = [
    "Christmas",
    "New Year",
    "Eid",
    "Diwali",
    "Chinese New Year",
    "Thanksgiving",
    "Easter",
    "Ramadan",
]


def build_holiday_greeting_prompt(
    holiday: str,
    customer_name: str,
    company: str,
    relationship_level: str,
    product_mention: str = "",
) -> tuple[str, str | None]:
    """构建节日祝福 Prompt，支持不同节日和客户关系级别。"""
    holiday = sanitize_prompt_param(holiday, "holiday")
    customer_name = sanitize_prompt_param(customer_name, "customer_name")
    company = sanitize_prompt_param(company, "company")
    relationship_level = sanitize_prompt_param(relationship_level, "relationship_level")
    product_mention = sanitize_prompt_param(product_mention, "product_mention")
    product_info = f"\n产品提及: {product_mention}" if product_mention else ""
    system = "你是一位深谙国际商务礼仪的外贸业务专家，擅长撰写得体且有温度的节日祝福邮件。"
    prompt = f"""Please generate a culturally appropriate holiday greeting email:

Holiday: {holiday}
Customer Name: {customer_name}
Your Company: {company}
Relationship Level: {relationship_level}{product_info}

Relationship level guide:
- 新客户: Formal, professional, brief greeting with hope for future cooperation
- 老客户: Warm, appreciative, reference past cooperation and continued partnership
- VIP: Personal, heartfelt, emphasize special relationship and exclusive appreciation

Output format:
Subject: [Holiday greeting subject line, warm and professional]

Dear {customer_name},

[Greeting body, 60-100 words]
- Culturally appropriate holiday wishes
- Tone matching the relationship level
- Brief mention of business appreciation (subtle, not salesy)
- Well wishes for the coming period

Warm regards,
[Your Name]
[Your Company]

Requirements:
1. Be culturally sensitive and appropriate for the specific holiday
2. Match tone to relationship level
3. Keep it genuine, not overly promotional
4. Output in English, plain text only, no markdown symbols."""
    return prompt, system


# ---------------------------------------------------------------------------
# 邮件润色/翻译（Email Polish & Translation）
# ---------------------------------------------------------------------------
def build_email_polish_prompt(
    content: str,
    source_lang: str,
    target_lang: str,
    mode: str,
) -> tuple[str, str | None]:
    """构建邮件润色/翻译 Prompt。mode: 翻译/润色/翻译+润色。"""
    content = sanitize_input(content, max_length=3000)
    source_lang = sanitize_prompt_param(source_lang, "source_lang")
    target_lang = sanitize_prompt_param(target_lang, "target_lang")
    mode = sanitize_prompt_param(mode, "mode")
    system = "你是一位精通多语言商务写作的外贸邮件专家，擅长邮件翻译和润色优化。"

    if mode == "翻译":
        task_desc = f"Translate the following email from {source_lang} to {target_lang}. Keep the meaning and tone intact."
        requirements = f"""Requirements:
1. Accurate translation from {source_lang} to {target_lang}
2. Maintain the original tone and intent
3. Use natural, professional {target_lang} expressions
4. Keep formatting and structure consistent
5. Output the translated text only, plain text, no markdown symbols."""
    elif mode == "润色":
        task_desc = f"Polish and improve the following email in {source_lang}. Make it more professional, clear, and impactful."
        requirements = f"""Requirements:
1. Improve grammar, word choice, and sentence structure
2. Maintain the original meaning and intent
3. Make it sound more professional and polished
4. Keep the same language ({source_lang})
5. Output the polished text only, plain text, no markdown symbols."""
    else:  # 翻译+润色
        task_desc = f"Translate the following email from {source_lang} to {target_lang}, then polish it to be more professional and impactful."
        requirements = f"""Requirements:
1. First translate accurately from {source_lang} to {target_lang}
2. Then polish the translation for professional quality
3. Improve word choice and sentence flow in {target_lang}
4. Make it sound natural and compelling to native speakers
5. Output the final polished translation only, plain text, no markdown symbols."""

    prompt = f"""{task_desc}

Original email content:
---
{content}
---

{requirements}"""
    return prompt, system


# ---------------------------------------------------------------------------
# 客诉回复（Complaint Response）
# ---------------------------------------------------------------------------
COMPLAINT_TYPES: list[str] = [
    "质量问题",
    "交期延误",
    "数量短缺",
    "包装破损",
    "规格不符",
]

COMPLAINT_SEVERITIES: list[str] = ["轻微", "中等", "严重"]

COMPLAINT_RELATIONSHIPS: list[str] = ["新客户", "老客户", "大客户"]

COMPLAINT_SOLUTIONS: list[str] = ["换货", "补发", "折扣补偿", "退款"]


def build_complaint_response_prompt(
    complaint_type: str,
    severity: str,
    relationship: str,
    proposed_solution: str,
    customer_complaint: str = "",
) -> tuple[str, str | None]:
    """构建客诉回复 Prompt。"""
    complaint_type = sanitize_prompt_param(complaint_type, "complaint_type")
    severity = sanitize_prompt_param(severity, "severity")
    relationship = sanitize_prompt_param(relationship, "relationship")
    proposed_solution = sanitize_prompt_param(proposed_solution, "proposed_solution")
    customer_complaint = sanitize_input(customer_complaint, max_length=2000)
    complaint_detail = f"\n客户原文: {customer_complaint}" if customer_complaint else ""
    system = "你是一位有丰富经验的外贸客服经理，擅长处理国际贸易客诉并维护客户关系。"
    prompt = f"""Please generate a professional complaint response email:

Complaint Type: {complaint_type}
Severity: {severity}
Customer Relationship: {relationship}
Proposed Solution: {proposed_solution}{complaint_detail}

Please output in the following format:

Subject: [Professional subject line acknowledging the issue]

Dear [Customer],

[Response body, 100-150 words, structured as follows:]

1. Acknowledgment: Sincerely acknowledge the issue and apologize
2. Solution: Clearly state the proposed solution ({proposed_solution}) with timeline
3. Prevention: Briefly explain steps to prevent recurrence
4. Closing: Reaffirm commitment to quality and partnership

[Your Name]
[Your Company]

Requirements:
1. Tone should match severity (more apologetic for severe issues)
2. Adjust formality based on relationship level
3. Be specific about the solution and next steps
4. Show empathy without admitting excessive liability
5. Output in English, plain text only, no markdown symbols."""
    return prompt, system
