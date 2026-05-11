"""
config/prompts.py
-----------------
所有 AI Prompt 模板统一管理。
每个函数返回 (prompt: str, system_prompt: str | None) 元组。
"""

# ---------------------------------------------------------------------------
# 开发信
# ---------------------------------------------------------------------------
EMAIL_STYLES: dict[str, str] = {
    "简洁专业": "简洁有力，50-80词，直接说明产品优势和合作邀请",
    "正式商务": "正式专业，100-150词，详细介绍产品资质和公司实力",
    "亲切友好": "友好亲切，80-100词，建立个人关系，softer tone",
}


def build_email_prompt(
    product: str,
    customer: str,
    features: str,
    tone: str = "简洁专业",
) -> tuple[str, str | None]:
    style = EMAIL_STYLES.get(tone, EMAIL_STYLES["简洁专业"])
    system = "你是一位有10年经验的外贸业务员，擅长撰写高转化率的英文开发信。"
    prompt = f"""请根据以下信息生成一封专业英文开发信，同时生成一个吸引人的邮件主题行（Subject Line）：

- 产品: {product}
- 目标客户: {customer}
- 产品卖点: {features}
- 风格要求: {style}

输出格式（严格按此格式）：
Subject: [邮件主题行，不超过60字符，突出核心价值]

[邮件正文开始]
...邮件内容...
[Your Name]
[Your Company]

要求：
1. Subject Line 要简洁有力，能提高开信率
2. 邮件正文开头问候并说明如何得知客户
3. 简明介绍产品核心优势（2-3点）
4. 突出差异化卖点
5. 结尾包含明确的 Call to Action

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
