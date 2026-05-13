"""
config/i18n.py
--------------
Internationalization support for Chinese/English language switching.
Provides t(key) helper to look up translated strings.
"""
from __future__ import annotations

try:
    import streamlit as st
except ImportError:  # pragma: no cover – tests mock st
    st = None  # type: ignore[assignment]

LANGUAGES = {"中文": "zh", "English": "en"}

TRANSLATIONS: dict[str, dict[str, str]] = {
    "zh": {
        # Common
        "login": "登录",
        "register": "注册",
        "logout": "退出登录",
        "submit": "提交",
        "cancel": "取消",
        "confirm": "确认",
        "upgrade": "升级",
        "username": "用户名",
        "password": "密码",
        "email": "邮箱",
        "language": "语言",
        # Login / Register
        "login_title": "外贸AI助手",
        "login_subtitle": "请登录或注册账号继续使用",
        "login_tab": "🔐 Login",
        "register_tab": "📝 Register",
        "login_button": "🔐 登录",
        "register_button": "📝 注册",
        "username_placeholder": "请输入用户名",
        "password_placeholder": "请输入密码",
        "choose_username_placeholder": "选择用户名（字母和数字）",
        "choose_password_placeholder": "选择密码",
        "confirm_password_placeholder": "确认密码",
        "email_optional": "邮箱（可选）",
        "email_placeholder": "your@email.com",
        "passwords_not_match": "两次输入的密码不一致",
        "registration_successful": "注册成功！请登录。",
        "invalid_credentials": "用户名或密码错误",
        "please_login": "请先登录",
        # Sidebar
        "usage_status": "📊 使用状态",
        "used_today": "今日已用",
        "plan_label": "Plan",
        "times": "次",
        "unlimited": "无限制",
        "remaining": "剩余",
        "used": "已用",
        "per_minutes_reset": "每 {minutes} 分钟重置",
        "earliest_release": "🕐 最早释放: {minutes}分{seconds}秒后",
        # Account page
        "account_management": "👤 账户管理",
        "account_subtitle": "查看个人资料、使用统计、套餐信息和安全设置",
        "profile": "📋 个人资料",
        "usage_stats": "📊 使用统计",
        "plan_comparison": "💎 套餐对比",
        "change_password": "🔒 修改密码",
        "current_plan": "当前套餐",
        "daily_used": "今日已用",
        "daily_limit": "每日额度",
        "times_per_day": "次/天",
        "register_time": "🗓️ 注册时间",
        "email_not_set": "未设置邮箱",
        "upgrade_plan": "🚀 升级套餐",
        "payment_coming_soon": "🎉 支付系统即将上线，敬请期待！",
        "recent_7_days": "📈 近7天使用记录",
        "no_usage_record": "暂无使用记录",
        "current_password": "当前密码",
        "new_password": "新密码",
        "confirm_new_password": "确认新密码",
        "current_password_placeholder": "请输入当前密码",
        "new_password_placeholder": "请输入新密码（至少4位）",
        "confirm_new_password_placeholder": "请再次输入新密码",
        "confirm_change": "✅ 确认修改",
        "password_changed": "✅ 密码修改成功！",
        "enter_current_password": "请输入当前密码",
        "enter_new_password": "请输入新密码",
        "new_passwords_not_match": "两次输入的新密码不一致",
        # Homepage
        "hero_title": "💼 外贸AI助手",
        "hero_subtitle": "AI 赋能外贸 · 开发信 · 询盘回复 · 报价单 · 多语种产品介绍",
        "free_trial": "🆓 免费试用",
        "per_hour_20": "每小时20次",
        "select_function": "🚀 选择功能开始使用",
        "usage_tips": "💡 使用提示",
        "footer": "💼 外贸AI助手 | 让外贸更简单 · Powered by NVIDIA NIM",
        "footer_account": "💼 外贸AI助手 · 账户管理",
        "enter_feature": "进入",
        # Stats
        "core_features": "核心功能",
        "languages_support": "语种支持",
        "realtime_output": "实时输出",
        "multi_sku_quote": "多SKU报价单",
        # Plans
        "free": "Free",
        "pro": "Pro",
        "enterprise": "Enterprise",
        "per_day": "次/天",
        "unlimited_per_day": "无限次",
        # Plan features
        "basic_ai_generation": "基础AI生成",
        "cold_email": "开发信撰写",
        "product_description": "产品描述",
        "email_reply": "邮件回复",
        "logo_upload": "Logo上传",
        "data_export": "数据导出",
        "priority_support": "优先支持",
        # Email verification
        "email_verified": "已验证",
        "email_unverified": "未验证",
        "verify_email": "验证邮箱",
        "enter_verification_token": "请输入验证码",
        "resend_verification": "重新发送验证邮件",
        "verification_success": "邮箱验证成功！",
        "verification_failed": "验证失败",
        "token_invalid": "验证码无效",
        "email_not_configured": "邮件服务未配置",
        "verification_sent": "验证邮件已发送",
        # Password reset
        "forgot_password": "忘记密码?",
        "reset_password": "重置密码",
        "enter_email_or_username": "输入邮箱或用户名",
        "send_reset_email": "发送重置邮件",
        "reset_email_sent": "如果账户存在，重置邮件已发送",
        "enter_reset_token": "输入重置令牌",
        "password_reset_success": "密码重置成功！请登录",
        "token_expired": "令牌已过期，请重新申请",
        "back_to_login": "返回登录",
        # Payment / Stripe
        "upgrade_to_pro": "升级到 Pro",
        "upgrade_to_enterprise": "升级到 Enterprise",
        "payment_not_available": "支付功能仅在云端部署时可用",
        "payment_not_configured": "支付系统未配置",
        "payment_checkout_link": "点击此链接完成支付",
        "verify_payment": "验证支付",
        "enter_session_id": "输入支付会话ID",
        "verify_and_upgrade": "验证并升级",
        "upgrade_success": "升级成功！",
        "upgrade_failed": "升级失败",
        "price_free": "$0/月",
        "price_pro": "$29/月",
        "price_enterprise": "$99/月",
        "current_plan_badge": "当前套餐",
    },
    "en": {
        # Common
        "login": "Login",
        "register": "Register",
        "logout": "Logout",
        "submit": "Submit",
        "cancel": "Cancel",
        "confirm": "Confirm",
        "upgrade": "Upgrade",
        "username": "Username",
        "password": "Password",
        "email": "Email",
        "language": "Language",
        # Login / Register
        "login_title": "Trade AI Assistant",
        "login_subtitle": "Please login or register to continue",
        "login_tab": "🔐 Login",
        "register_tab": "📝 Register",
        "login_button": "🔐 Login",
        "register_button": "📝 Register",
        "username_placeholder": "Enter username",
        "password_placeholder": "Enter password",
        "choose_username_placeholder": "Choose a username (letters and numbers)",
        "choose_password_placeholder": "Choose a password",
        "confirm_password_placeholder": "Confirm your password",
        "email_optional": "Email (optional)",
        "email_placeholder": "your@email.com",
        "passwords_not_match": "Passwords do not match",
        "registration_successful": "Registration successful! Please login.",
        "invalid_credentials": "Invalid username or password",
        "please_login": "Please login first",
        # Sidebar
        "usage_status": "📊 Usage Status",
        "used_today": "Used today",
        "plan_label": "Plan",
        "times": "times",
        "unlimited": "Unlimited",
        "remaining": "remaining",
        "used": "Used",
        "per_minutes_reset": "resets every {minutes} min",
        "earliest_release": "🕐 Next reset: {minutes}m {seconds}s",
        # Account page
        "account_management": "👤 Account Management",
        "account_subtitle": "View profile, usage stats, plan info, and security settings",
        "profile": "📋 Profile",
        "usage_stats": "📊 Usage Statistics",
        "plan_comparison": "💎 Plan Comparison",
        "change_password": "🔒 Change Password",
        "current_plan": "Current Plan",
        "daily_used": "Used Today",
        "daily_limit": "Daily Limit",
        "times_per_day": "times/day",
        "register_time": "🗓️ Registered",
        "email_not_set": "Email not set",
        "upgrade_plan": "🚀 Upgrade Plan",
        "payment_coming_soon": "🎉 Payment system coming soon!",
        "recent_7_days": "📈 Last 7 Days Usage",
        "no_usage_record": "No usage records yet",
        "current_password": "Current Password",
        "new_password": "New Password",
        "confirm_new_password": "Confirm New Password",
        "current_password_placeholder": "Enter current password",
        "new_password_placeholder": "Enter new password (min 4 chars)",
        "confirm_new_password_placeholder": "Enter new password again",
        "confirm_change": "✅ Confirm Change",
        "password_changed": "✅ Password changed successfully!",
        "enter_current_password": "Please enter current password",
        "enter_new_password": "Please enter new password",
        "new_passwords_not_match": "New passwords do not match",
        # Homepage
        "hero_title": "💼 Trade AI Assistant",
        "hero_subtitle": "AI-Powered Foreign Trade: Cold Emails, Inquiry Replies, Quotations, Multilingual Product Descriptions",
        "free_trial": "🆓 Free Trial",
        "per_hour_20": "20 uses/hour",
        "select_function": "🚀 Select a Feature to Start",
        "usage_tips": "💡 Usage Tips",
        "footer": "💼 Trade AI Assistant | Making Foreign Trade Easier · Powered by NVIDIA NIM",
        "footer_account": "💼 Trade AI Assistant · Account Management",
        "enter_feature": "Go to",
        # Stats
        "core_features": "Core Features",
        "languages_support": "Languages",
        "realtime_output": "Real-time",
        "multi_sku_quote": "Multi-SKU PDF",
        # Plans
        "free": "Free",
        "pro": "Pro",
        "enterprise": "Enterprise",
        "per_day": "times/day",
        "unlimited_per_day": "Unlimited",
        # Plan features
        "basic_ai_generation": "Basic AI Generation",
        "cold_email": "Cold Email Writing",
        "product_description": "Product Description",
        "email_reply": "Email Reply",
        "logo_upload": "Logo Upload",
        "data_export": "Data Export",
        "priority_support": "Priority Support",
        # Email verification
        "email_verified": "Verified",
        "email_unverified": "Unverified",
        "verify_email": "Verify Email",
        "enter_verification_token": "Enter verification token",
        "resend_verification": "Resend verification email",
        "verification_success": "Email verified successfully!",
        "verification_failed": "Verification failed",
        "token_invalid": "Invalid verification token",
        "email_not_configured": "Email service is not configured",
        "verification_sent": "Verification email sent",
        # Password reset
        "forgot_password": "Forgot password?",
        "reset_password": "Reset Password",
        "enter_email_or_username": "Enter email or username",
        "send_reset_email": "Send Reset Email",
        "reset_email_sent": "If an account exists with that email, a reset link has been sent",
        "enter_reset_token": "Enter reset token",
        "password_reset_success": "Password reset successful! Please login",
        "token_expired": "Token expired, please request a new one",
        "back_to_login": "Back to Login",
        # Payment / Stripe
        "upgrade_to_pro": "Upgrade to Pro",
        "upgrade_to_enterprise": "Upgrade to Enterprise",
        "payment_not_available": "Payment available on cloud deployment",
        "payment_not_configured": "Payment system not configured",
        "payment_checkout_link": "Click this link to complete payment",
        "verify_payment": "Verify Payment",
        "enter_session_id": "Enter Checkout Session ID",
        "verify_and_upgrade": "Verify & Upgrade",
        "upgrade_success": "Upgrade successful!",
        "upgrade_failed": "Upgrade failed",
        "price_free": "$0/mo",
        "price_pro": "$29/mo",
        "price_enterprise": "$99/mo",
        "current_plan_badge": "Current Plan",
    },
}


def get_lang() -> str:
    """Return current language code ('zh' or 'en') from session state."""
    if st is None:
        return "zh"
    try:
        return st.session_state.get("language", "zh")
    except Exception:
        return "zh"


def t(key: str) -> str:
    """
    Translate a key to the current language string.
    Falls back to the key itself if not found.
    """
    lang = get_lang()
    lang_dict = TRANSLATIONS.get(lang, TRANSLATIONS["zh"])
    return lang_dict.get(key, key)
