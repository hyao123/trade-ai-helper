import os
import json
import requests

API_KEY = os.getenv("KIMI_API_KEY", "")
API_BASE = "https://api.moonshot.cn/v1"

EMAIL_STYLES = {
    "简洁专业": "简洁有力，50-80词，直接说明产品优势和合作邀请",
    "正式商务": "正式专业，100-150词，详细介绍产品资质和公司实力",
    "亲切友好": "友好亲切，80-100词，建立个人关系， softer tone"
}

def call_kimi(prompt, system_prompt=None):
    """调用Kimi API"""
    if not API_KEY:
        return "⚠️ 请先设置 KIMI_API_KEY 环境变量"
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}"
    }
    
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})
    
    data = {
        "model": "moonshot-v1-8k",
        "messages": messages,
        "temperature": 0.7
    }
    
    try:
        response = requests.post(
            f"{API_BASE}/chat/completions",
            headers=headers,
            json=data,
            timeout=30
        )
        if response.status_code == 200:
            result = response.json()
            return result["choices"][0]["message"]["content"]
        else:
            return f"⚠️ API错误: {response.status_code}"
    except Exception as e:
        return f"⚠️ 调用失败: {str(e)}"


def generate_email(product, customer, features, tone="简洁专业"):
    """生成开发信"""
    style = EMAIL_STYLES.get(tone, EMAIL_STYLES["简洁专业"])
    
    prompt = f"""请根据以下信息生成一封专业英文开发信：

- 产品: {product}
- 目标客户: {customer}
- 产品卖点: {features}
- 风格: {style}

要求：
1. 开头问候并说明如何得知客户
2. 简明介绍产品优势
3. 突出差异化卖点
4. 结尾Call to Action（邀请回复/视频会议）
5. 签名占位 [Your Name]
6. 公司信息占位 [Your Company]

输出纯文本开发信，不需要格式符号。"""
    
    return call_kimi(prompt)


def reply_inquiry(inquiry, customer_name="", your_name=""):
    """生成询盘回复"""
    customer_info = f"客户: {customer_name}" if customer_name else "某客户"
    
    prompt = f"""你是一位专业外贸业务员。请回复以下客户询盘：

{customer_info}的询盘内容：
{inquiry}

请生成专业回复，包含：
1. 感谢客户询盘
2. 回答客户问题
3. 提供合理报价区间（如不确定则给范围）
4. 询问其他需求
5. 邀请进一步沟通

{"签名: " + your_name if your_name else "签名: [Your Name]"}
"""
    
    return call_kimi(prompt)


def generate_product_intro(product, features, target, languages):
    """生成多语种产品介绍"""
    lang_map = {
        "英语": "English",
        "西班牙语": "Spanish",
        "法语": "French", 
        "德语": "German",
        "日语": "Japanese"
    }
    
    langs = [lang_map[l] for l in languages]
    lang_str = ", ".join(langs)
    
    prompt = f"""请为以下产品生成{lang_str}的产品介绍文案：

产品: {product}
特点: {features}
目标市场: {target}

要求：
1. 简洁专业
2. 突出产品优势
3. 适合B2B外贸场景
4. 每种语言单独输出，标注语言名称
5. 包含产品描述、优势、应用领域"""
    
    return call_kimi(prompt)


def generate_follow_up(customer, stage):
    """生成跟进邮件"""
    stages = {
        "已报价": "报价后跟进，确认客户意向",
        "已发样": "样品跟进，询问反馈",
        "已谈判": "价格谈判，促成订单",
        "已下单": "订单确认，感谢下单"
    }
    
    context = stages.get(stage, "常规跟进")
    
    prompt = f"""请生成一封跟进邮件：
- 客户: {customer}
- 阶段: {context}

要求：
1. 根据阶段选择合适内容
2. 专业但不过分催促
3. 包含明确的下一步行动邀请"""
    
    return call_kimi(prompt)


def generate_linkedin_message(profile_info, purpose="connect"):
    """生成领英消息"""
    purposes = {
        "connect": "建立联系",
        "introduce": "自我介绍",
        "followup": "跟进"
    }
    
    prompt = f"""请生成一条LinkedIn消息：
- 目的: {purposes.get(purpose, purpose)}
- 对方信息: {profile_info}

要求：
1. 简短（50词内）
2. 专业友好
3. 有明确的连接原因"""
    
    return call_kimi(prompt)