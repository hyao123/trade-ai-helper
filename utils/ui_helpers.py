"""
utils/ui_helpers.py
-------------------
所有页面共享的 UI 组件：
- inject_css()   注入全局样式（幂等，多次调用安全）
- check_auth()   访问密码鉴权
- copy_button()  真实可用的"复制到剪贴板"按钮
- show_result()  统一渲染生成结果区域（支持流式 & 非流式）
"""

from __future__ import annotations

import os
import types
from typing import Generator

import streamlit as st
from utils.secrets import get_secret

APP_PASSWORD = get_secret("APP_PASSWORD")

# ---------------------------------------------------------------------------
# 全局 CSS
# ---------------------------------------------------------------------------
_CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@300;400;500;600;700&display=swap');
    * { font-family: 'Noto Sans SC', 'Microsoft YaHei', sans-serif !important; }

    .block-container { padding: 2rem 3rem !important; max-width: 1400px !important; }
    h1, h2, h3 { font-weight: 600 !important; }

    /* Hero */
    .hero-section {
        background: linear-gradient(135deg, #1e3a5f 0%, #3b82f6 50%, #8b5cf6 100%);
        padding: 2rem; border-radius: 16px; color: white; margin-bottom: 1.5rem;
    }
    .hero-title  { font-size: 1.8rem !important; font-weight: 700 !important; }
    .hero-subtitle { font-size: 1rem; opacity: 0.9; }
    .price-tag {
        background: rgba(255,255,255,0.2); padding: 0.4rem 1rem;
        border-radius: 20px; display: inline-flex; align-items: center;
        gap: 0.5rem; margin-top: 0.75rem; font-size: 0.9rem;
    }

    /* Stats */
    .stat-card {
        background: white; border-radius: 14px; padding: 1.25rem;
        text-align: center; box-shadow: 0 2px 12px rgba(0,0,0,0.06);
        border: 1px solid #e5e7eb;
    }
    .stat-value { font-size: 1.6rem; font-weight: 700; color: #1e3a5f; }
    .stat-label { font-size: 0.8rem; color: #666; margin-top: 0.25rem; }

    /* Form card */
    .main-form {
        background: white; border-radius: 16px; padding: 2rem;
        box-shadow: 0 2px 16px rgba(0,0,0,0.06); border: 1px solid #e5e7eb;
        margin-bottom: 1.5rem;
    }
    .form-title { color: #1e3a5f; font-size: 1.15rem; font-weight: 600; margin-bottom: 1.25rem; }

    /* Inputs */
    .stTextInput > div > div > input,
    .stTextArea  > div > div > textarea {
        border-radius: 8px; border: 1.5px solid #e5e7eb; padding: 0.6rem 0.85rem;
    }
    .stTextInput > div > div > input:focus,
    .stTextArea  > div > div > textarea:focus {
        border-color: #3b82f6; box-shadow: 0 0 0 3px rgba(59,130,246,0.1);
    }
    .stButton > button { border-radius: 8px; font-weight: 600; padding: 0.6rem 1.25rem; }

    /* Tip / Success */
    .tip-card {
        background: #fef9c3; border-radius: 8px; padding: 0.75rem 1rem;
        border-left: 3px solid #f59e0b; margin-bottom: 1rem; font-size: 0.85rem;
    }
    .success-box {
        background: linear-gradient(135deg, #dcfce7 0%, #bbf7d0 100%);
        border-radius: 12px; padding: 1.25rem; text-align: center;
        border: 2px solid #22c55e; margin: 1rem 0;
    }
    .success-title { font-size: 1.1rem; font-weight: 600; color: #166534; }
    .result-area {
        background: #f8fafc; border-radius: 10px; padding: 1.25rem;
        border: 1px solid #e2e8f0; margin-top: 1rem;
    }

    /* Subject line highlight */
    .subject-box {
        background: #eff6ff; border-radius: 10px; padding: 1rem 1.25rem;
        border: 1.5px solid #bfdbfe; margin-bottom: 0.75rem;
    }
    .subject-label { font-size: 0.75rem; font-weight: 700; color: #3b82f6;
                     text-transform: uppercase; letter-spacing: 0.05em; }
    .subject-text  { font-size: 1rem; font-weight: 600; color: #1e3a5f; margin-top: 0.25rem; }

    /* Login */
    .login-box {
        max-width: 400px; margin: 6rem auto; background: white;
        border-radius: 20px; padding: 2.5rem;
        box-shadow: 0 8px 40px rgba(0,0,0,0.12); border: 1px solid #e5e7eb; text-align: center;
    }
    .login-title { font-size: 1.4rem; font-weight: 700; color: #1e3a5f; margin-bottom: 0.5rem; }
    .login-sub   { color: #6b7280; font-size: 0.9rem; margin-bottom: 1.5rem; }

    /* Sidebar */
    [data-testid="stSidebar"] { background: linear-gradient(180deg, #1e3a5f 0%, #0f172a 100%); }

    /* Footer */
    .footer { text-align: center; padding: 1.5rem; color: #9ca3af; font-size: 0.8rem; }

    @media (max-width: 768px) { .block-container { padding: 0.75rem !important; } }
</style>
"""

_css_injected = False


def inject_css() -> None:
    """注入全局 CSS（幂等，同一 session 内多次调用只注入一次）。"""
    global _css_injected
    if not _css_injected:
        st.markdown(_CSS, unsafe_allow_html=True)
        _css_injected = True


# ---------------------------------------------------------------------------
# 鉴权
# ---------------------------------------------------------------------------
def check_auth() -> None:
    """
    密码验证。
    - APP_PASSWORD 未设置 → 直接通过（本地开发友好）
    - 已通过验证 → 直接通过
    - 未通过 → 渲染登录框并 st.stop()
    """
    app_password = get_secret("APP_PASSWORD")
    if not app_password:
        st.session_state.authenticated = True
        return
    if st.session_state.get("authenticated"):
        return

    st.markdown("""
    <div class="login-box">
        <div style="font-size:2.5rem;">💼</div>
        <div class="login-title">外贸AI助手</div>
        <div class="login-sub">请输入访问密码继续使用</div>
    </div>
    """, unsafe_allow_html=True)

    with st.form("login_form"):
        pwd = st.text_input("访问密码", type="password", placeholder="请输入密码")
        if st.form_submit_button("🔐 登录", use_container_width=True, type="primary"):
            if pwd == app_password:
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("❌ 密码错误，请重试")
    st.stop()


# ---------------------------------------------------------------------------
# 复制按钮
# ---------------------------------------------------------------------------
def copy_button(text: str, key: str) -> None:
    """使用 navigator.clipboard JS API 实现真实复制，2s 后按钮文字恢复。"""
    safe = text.replace("\\", "\\\\").replace("`", "\\`").replace("'", "\\'")
    btn_id = f"copy_btn_{key}"
    st.components.v1.html(
        f"""
        <button id="{btn_id}"
            onclick="navigator.clipboard.writeText(`{safe}`).then(()=>{{
                var b=document.getElementById('{btn_id}');
                b.innerText='✅ 已复制';
                b.style.background='#dcfce7';b.style.borderColor='#22c55e';b.style.color='#166534';
                setTimeout(()=>{{
                    b.innerText='📋 复制到剪贴板';
                    b.style.background='white';b.style.borderColor='#3b82f6';b.style.color='#3b82f6';
                }},2000);
            }})"
            style="width:100%;padding:0.55rem 1rem;border-radius:8px;
                   border:1.5px solid #3b82f6;background:white;color:#3b82f6;
                   font-weight:600;cursor:pointer;font-size:0.9rem;transition:all 0.2s;">
            📋 复制到剪贴板
        </button>
        """,
        height=48,
    )


# ---------------------------------------------------------------------------
# Subject Line 提取与展示
# ---------------------------------------------------------------------------
def extract_subject(text: str) -> tuple[str, str]:
    """
    若文本首行以 'Subject:' 开头，提取并返回 (subject, body)。
    否则返回 ('', text)。
    """
    lines = text.strip().splitlines()
    if lines and lines[0].lower().startswith("subject:"):
        subject = lines[0][len("subject:"):].strip()
        body = "\n".join(lines[1:]).strip()
        return subject, body
    return "", text


def show_subject(subject: str, key: str) -> None:
    """渲染主题行高亮卡片 + 复制按钮。"""
    if not subject:
        return
    st.markdown(
        f'<div class="subject-box">'
        f'<div class="subject-label">📌 邮件主题行（Subject Line）</div>'
        f'<div class="subject-text">{subject}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )
    copy_button(subject, f"subject_{key}")


# ---------------------------------------------------------------------------
# 生成结果区域（流式 + 非流式统一入口）
# ---------------------------------------------------------------------------
def show_result(
    result: str | types.GeneratorType,
    result_key: str,
    label: str = "📝 生成结果",
    file_name: str = "result.txt",
    height: int = 220,
    balloons: bool = True,
    show_subject_line: bool = False,
) -> None:
    """
    统一渲染生成结果区域。
    - result 是 GeneratorType → 流式渲染，完成后存入 session_state.results
    - result 是 str           → 直接展示
    - show_subject_line=True  → 自动提取并高亮显示 Subject Line
    """
    if not result:
        return

    if "results" not in st.session_state:
        st.session_state.results = {}

    # --- 流式模式 ---
    if isinstance(result, types.GeneratorType):
        st.markdown(
            '<div class="success-box">'
            '<div style="font-size:1.5rem;">⚡</div>'
            '<div class="success-title">正在生成中...</div>'
            '</div>',
            unsafe_allow_html=True,
        )
        full_text: str = st.write_stream(result)  # type: ignore[arg-type]
        st.session_state.results[result_key] = full_text
        result = full_text
        if balloons:
            st.balloons()

    # --- 成功提示 ---
    st.markdown(
        '<div class="success-box">'
        '<div style="font-size:1.5rem;">✅</div>'
        '<div class="success-title">生成完成！</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    # --- Subject Line 提取（开发信专用）---
    display_text = result
    subject = ""
    if show_subject_line:
        subject, display_text = extract_subject(result)
        if subject:
            show_subject(subject, result_key)

    # --- 正文展示 ---
    st.markdown('<div class="result-area">', unsafe_allow_html=True)
    st.text_area(label, display_text, height=height, key=f"display_{result_key}")
    col1, col2 = st.columns(2)
    with col1:
        st.download_button(
            "📥 下载", display_text,
            file_name=file_name, mime="text/plain",
            use_container_width=True,
        )
    with col2:
        copy_button(display_text, result_key)
    st.markdown("</div>", unsafe_allow_html=True)
