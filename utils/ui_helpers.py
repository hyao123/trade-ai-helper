"""
utils/ui_helpers.py
-------------------
所有页面共享的 UI 组件：
- inject_css()   注入全局样式（幂等，用 session_state 控制）
- check_auth()   访问密码鉴权
- copy_button()  真实可用的"复制到剪贴板"按钮
- show_result()  统一渲染生成结果区域（流式/非流式均正确处理）
"""

from __future__ import annotations

import hmac
import html
import json
import re
import time
import types

import streamlit as st
from utils.secrets import get_secret

# ---------------------------------------------------------------------------
# 全局 CSS
# ---------------------------------------------------------------------------
_CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@300;400;500;600;700&display=swap');
    * { font-family: 'Noto Sans SC', 'Microsoft YaHei', sans-serif !important; }

    .block-container { padding: 2rem 3rem !important; max-width: 1400px !important; }
    h1, h2, h3 { font-weight: 600 !important; }

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

    .stat-card {
        background: white; border-radius: 14px; padding: 1.25rem;
        text-align: center; box-shadow: 0 2px 12px rgba(0,0,0,0.06);
        border: 1px solid #e5e7eb;
    }
    .stat-value { font-size: 1.6rem; font-weight: 700; color: #1e3a5f; }
    .stat-label { font-size: 0.8rem; color: #666; margin-top: 0.25rem; }

    .main-form {
        background: white; border-radius: 16px; padding: 2rem;
        box-shadow: 0 2px 16px rgba(0,0,0,0.06); border: 1px solid #e5e7eb;
        margin-bottom: 1.5rem;
    }
    .form-title { color: #1e3a5f; font-size: 1.15rem; font-weight: 600; margin-bottom: 1.25rem; }

    .stTextInput > div > div > input,
    .stTextArea  > div > div > textarea {
        border-radius: 8px; border: 1.5px solid #e5e7eb; padding: 0.6rem 0.85rem;
    }
    .stTextInput > div > div > input:focus,
    .stTextArea  > div > div > textarea:focus {
        border-color: #3b82f6; box-shadow: 0 0 0 3px rgba(59,130,246,0.1);
    }
    .stButton > button { border-radius: 8px; font-weight: 600; padding: 0.6rem 1.25rem; }

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

    /* 流式输出区域 */
    .stream-container {
        background: #f8fafc; border-radius: 10px; padding: 1.25rem;
        border: 1.5px dashed #bfdbfe; margin: 0.75rem 0;
        min-height: 60px; line-height: 1.7; white-space: pre-wrap;
        font-size: 0.95rem; color: #1e3a5f;
    }

    .login-box {
        max-width: 400px; margin: 6rem auto; background: white;
        border-radius: 20px; padding: 2.5rem;
        box-shadow: 0 8px 40px rgba(0,0,0,0.12); border: 1px solid #e5e7eb; text-align: center;
    }
    .login-title { font-size: 1.4rem; font-weight: 700; color: #1e3a5f; margin-bottom: 0.5rem; }
    .login-sub   { color: #6b7280; font-size: 0.9rem; margin-bottom: 1.5rem; }

    [data-testid="stSidebar"] { background: linear-gradient(180deg, #1e3a5f 0%, #0f172a 100%); }
    .footer { text-align: center; padding: 1.5rem; color: #9ca3af; font-size: 0.8rem; }

    @media (max-width: 768px) { .block-container { padding: 0.75rem !important; } }
</style>
"""


def inject_css() -> None:
    """注入全局 CSS（幂等：用 session_state 控制，每次 session 只注入一次）。"""
    if not st.session_state.get("_css_injected"):
        st.markdown(_CSS, unsafe_allow_html=True)
        st.session_state["_css_injected"] = True
    # 每次页面渲染时刷新侧栏信息
    show_sidebar_info()


# ---------------------------------------------------------------------------
# 侧栏信息（Rate Limit 剩余次数）
# ---------------------------------------------------------------------------
def show_sidebar_info() -> None:
    """在侧栏显示剩余 API 调用次数和重置倒计时。"""
    from utils.ai_client import get_rate_limit_remaining, RATE_LIMIT_MAX_CALLS, RATE_LIMIT_WINDOW, _call_times

    remaining = get_rate_limit_remaining()
    used = RATE_LIMIT_MAX_CALLS - remaining

    with st.sidebar:
        st.markdown("---")
        st.markdown("### 📊 使用状态")
        st.progress(used / RATE_LIMIT_MAX_CALLS if RATE_LIMIT_MAX_CALLS > 0 else 0)
        st.caption(f"已用 **{used}** / {RATE_LIMIT_MAX_CALLS} 次（每 {RATE_LIMIT_WINDOW // 60} 分钟重置）")

        # 计算最早 slot 何时过期
        if _call_times.get("default"):
            now = time.time()
            earliest = min(_call_times["default"])
            reset_in = max(0, int(RATE_LIMIT_WINDOW - (now - earliest)))
            minutes, seconds = divmod(reset_in, 60)
            st.caption(f"🕐 最早释放: {minutes}分{seconds}秒后")
        st.markdown("---")


# ---------------------------------------------------------------------------
# 鉴权
# ---------------------------------------------------------------------------
def check_auth() -> None:
    """
    密码验证。
    - APP_PASSWORD 未设置 → 直接通过
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
            if hmac.compare_digest(pwd, app_password):
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("❌ 密码错误，请重试")
    st.stop()


# ---------------------------------------------------------------------------
# 复制按钮（用 json.dumps 安全转义，防止 JS 注入）
# ---------------------------------------------------------------------------
def copy_button(text: str, key: str) -> None:
    """使用 navigator.clipboard JS API 实现真实复制，2s 后恢复。"""
    safe_js = json.dumps(text)   # 自动处理所有转义：\n \\ " 等
    btn_id = f"copy_btn_{key}"
    st.components.v1.html(
        f"""
        <button id="{btn_id}"
            onclick="navigator.clipboard.writeText({safe_js}).then(()=>{{
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
# Subject Line 提取
# ---------------------------------------------------------------------------
def extract_subject(text: str) -> tuple[str, str]:
    """
    从 AI 输出中提取邮件主题行，支持多种变体格式：
    - Subject: xxx
    - **Subject:** xxx
    - Subject Line: xxx
    - 主题行：xxx
    返回 (subject, body)；提取失败则返回 ('', text)。
    """
    lines = text.strip().splitlines()
    if not lines:
        return "", text

    first = lines[0].strip()
    # 正则匹配多种 Subject 变体（含 markdown bold、中文冒号等）
    pattern = r'^\s*(?:\*\*)?(?:subject(?:\s*line)?|邮件主题行?)\s*[:：]\s*(?:\*\*)?\s*(.+?)(?:\*\*)?\s*$'
    match = re.match(pattern, first, re.IGNORECASE)
    if match:
        subject = match.group(1).strip()
        # 跳过 subject 行之后的空行
        rest_lines = lines[1:]
        while rest_lines and not rest_lines[0].strip():
            rest_lines = rest_lines[1:]
        body = "\n".join(rest_lines).strip()
        return subject, body
    return "", text


def show_subject(subject: str, key: str) -> None:
    """渲染主题行高亮卡片 + 复制按钮（XSS 安全）。"""
    if not subject:
        return
    safe_subject = html.escape(subject)
    st.markdown(
        f'<div class="subject-box">'
        f'<div class="subject-label">📌 邮件主题行（Subject Line）</div>'
        f'<div class="subject-text">{safe_subject}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )
    copy_button(subject, f"subject_{key}")


# ---------------------------------------------------------------------------
# 结果展示区（静态：非流式 or 流式完成后）
# ---------------------------------------------------------------------------
def _render_result_area(
    text: str,
    result_key: str,
    label: str,
    file_name: str,
    height: int,
    show_subject_line: bool,
) -> None:
    """渲染成功提示 + 可选 Subject Line + 文本区 + 下载/复制按钮。"""
    st.markdown(
        '<div class="success-box">'
        '<div style="font-size:1.5rem;">✅</div>'
        '<div class="success-title">生成完成！</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    display_text = text
    if show_subject_line:
        subject, display_text = extract_subject(text)
        if subject:
            show_subject(subject, result_key)

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


# ---------------------------------------------------------------------------
# 流式渲染（核心修复：让 st.write_stream 在干净容器里运行）
# ---------------------------------------------------------------------------
def _stream_into_container(generator: types.GeneratorType) -> str:
    """
    在一个干净的 st.container() 内运行 st.write_stream()。
    避免周围 HTML/markdown 块干扰 Streamlit 的增量更新机制。
    返回完整文本。
    """
    with st.container():
        full_text: str = st.write_stream(generator)  # type: ignore[arg-type]
    return full_text


# ---------------------------------------------------------------------------
# 统一入口：show_result
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

    流式模式（result 是 GeneratorType）：
      1. 显示"⚡ 正在生成中..."提示
      2. 在干净容器内调用 st.write_stream()，token 实时滚动显示
      3. 流式完成后：保存到 session_state，渲染 Subject Line + 下载/复制按钮

    非流式模式（result 是 str）：
      直接调用 _render_result_area() 展示。
    """
    if not result:
        return

    if "results" not in st.session_state:
        st.session_state.results = {}

    # ── 流式模式 ──────────────────────────────────────
    if isinstance(result, types.GeneratorType):
        # 1. 状态提示（放在流式区域之前，不影响 write_stream）
        status_placeholder = st.empty()
        status_placeholder.markdown(
            '<div class="success-box">'
            '<div style="font-size:1.2rem;">⚡ 正在生成中，请稍候...</div>'
            '</div>',
            unsafe_allow_html=True,
        )

        # 2. 流式输出（独立容器，避免 HTML 块干扰）
        full_text = _stream_into_container(result)

        # 3. 清除"正在生成"提示
        status_placeholder.empty()

        # 4. 保存结果
        st.session_state.results[result_key] = full_text

        if balloons:
            st.balloons()

        # 5. 渲染静态结果区（Subject Line + 下载 + 复制）
        _render_result_area(full_text, result_key, label, file_name, height, show_subject_line)
        return

    # ── 非流式模式 ────────────────────────────────────
    _render_result_area(result, result_key, label, file_name, height, show_subject_line)
