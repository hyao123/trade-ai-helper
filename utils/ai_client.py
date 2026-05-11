import os
import time
import requests
from collections import defaultdict
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("KIMI_API_KEY", "")
API_BASE = "https://api.moonshot.cn/v1"

EMAIL_STYLES = {
    "简洁专业": "简洁有力，50-80词，直接说明产品优势和合作邀请",
    "正式商务": "正式专业，100-150词，详细介绍产品资质和公司实力",
    "亲切友好": "友好亲切，80-100词，建立个人关系， softer tone"
}

# ---------------------------------------------------------------------------
# Rate Limiting
# ---------------------------------------------------------------------------
_call_times: dict = defaultdict(list)

RATE_LIMIT_MAX_CALLS = int(os.getenv("RATE_LIMIT_MAX_CALLS", "20"))   # 每个窗口最大调用次数
RATE_LIMIT_WINDOW    = int(os.getenv("RATE_LIMIT_WINDOW", "3600"))    # 窗口时长（秒），默认1小时


def _rate_limit_check(user_id: str = "default") -> tuple[bool, int]:
    """
    检查是否超出调用限制。
    返回 (allowed: bool, remaining: int)
    """
    now = time.time()
    # 只保留窗口内的调用记录
    _call_times[user_id] = [t for t in _call_times[user_id] if now - t < RATE_LIMIT_WINDOW]
    remaining = RATE_LIMIT_MAX_CALLS - len(_call_times[user_id])
    if remaining <= 0:
        return False, 0
    _call_times[user_id].append(now)
    return True, remaining - 1


# ---------------------------------------------------------------------------
# Core API caller
# ---------------------------------------------------------------------------

def call_kimi(prompt: str, system_prompt: str | None = None, user_id: str = "default") -> str:
    """调用 Kimi API，内置 Rate Limiting 与错误处理"""

    # 1. Rate limit 检查
    allowed, remaining = _rate_limit_check(user_id)
    if not allowed:
        wait_min = RATE_LIMIT_WINDOW // 60
        return f"⚠️ 调用频率超限，每 {wait_min} 分钟最多 {RATE_LIMIT_MAX_CALLS} 次，请稍后再试。"

    # 2. API Key 检查
    if not API_KEY:
        return "⚠️ 请先在 .env 文件中设置 KIMI_API_KEY 环境变量"

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
        elif response.status_code == 401:
            return "⚠️ API Key 无效，请检查 KIMI_API_KEY 是否正确。"
        elif response.status_code == 429:
            return "⚠️ API 调用超出 Kimi 平台限额，请稍后重试或升级套餐。"
        elif response.status_code >= 500:
            return f"⚠️ Kimi 服务器错误 ({response.status_code})，请稍后重试。"
        else:
            return f"⚠️ API 错误: {response.status_code} - {response.text[:200]}"
    except requests.exceptions.Timeout:
        return "⚠️ 请求超时（30s），请检查网络连接后重试。"
    except Exception as e:
        return f"⚠️ 调用失败: {str(e)}"


# ---------------------------------------------------------------------------
# Feature functions
# ---------------------------------------------------------------------------

def generate_email(product: str, customer: str, features: str, tone: str = "简洁专业") -> str:
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


def reply_inquiry(inquiry: str, customer_name: str = "", your_name: str = "") -> str:
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


def generate_product_intro(product: str, features: str, target: str, languages: list) -> str:
    """生成多语种产品介绍"""
    lang_map = {
        "英语": "English",
        "西班牙语": "Spanish",
        "法语": "French",
        "德语": "German",
        "日语": "Japanese"
    }

    langs = [lang_map.get(l, l) for l in languages]
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
