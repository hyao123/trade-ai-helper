"""
pages/37_📥_入站邮件.py
----------------------
Inbound Email Intake 第一阶段：手动导入客户邮件，形成待回复队列，并一键进入询盘回复生成草稿。
"""
from __future__ import annotations

import streamlit as st

from utils.inbound_email import (
    create_inbound_record,
    list_inbound_emails,
    parse_eml_bytes,
    parse_raw_email_text,
    seed_inquiry_session_state,
    update_inbound_status,
)
from utils.ui_helpers import check_auth, inject_css
from utils.user_auth import get_current_user

st.set_page_config(page_title="入站邮件 | 外贸AI助手", page_icon="📥", layout="wide")
inject_css()
check_auth()

current_user = get_current_user()
if not current_user or not current_user.get("username"):
    st.warning("请先登录")
    st.stop()

username = current_user["username"]

st.markdown(
    """
    <div class="hero-section">
        <h1 class="hero-title">📥 入站邮件 Intake</h1>
        <p class="hero-subtitle">第一阶段：手动导入客户邮件，自动解析并进入待回复队列，再一键生成 AI 回复草稿。</p>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="tip-card">
    当前版本支持手动粘贴原始邮件或上传 <b>.eml</b> 文件。Gmail / Outlook / IMAP 自动同步将在下一阶段接入。
    </div>
    """,
    unsafe_allow_html=True,
)

import_tab, queue_tab = st.tabs(["导入邮件", "待回复队列"])

with import_tab:
    st.markdown("### 导入客户邮件")
    source = st.radio("导入方式", ["粘贴邮件内容", "上传 .eml 文件"], horizontal=True)
    customer_id = st.text_input("关联客户ID（可选）", placeholder="例如 CRM 客户ID，后续可用于客户时间线")

    parsed = None
    if source == "粘贴邮件内容":
        raw_text = st.text_area(
            "客户邮件内容 / 原始邮件",
            height=260,
            placeholder="可以粘贴完整邮件源码（含 From/Subject/Date），也可以只粘贴正文。",
        )
        if st.button("解析并保存到待回复队列", type="primary", use_container_width=True):
            if not raw_text.strip():
                st.warning("请先粘贴客户邮件内容")
            else:
                try:
                    parsed = parse_raw_email_text(raw_text)
                except Exception as exc:  # noqa: BLE001
                    st.error(f"⚠️ 邮件解析失败，请检查邮件格式。（{exc}）")
    else:
        uploaded = st.file_uploader("上传 .eml 文件", type=["eml"])
        if st.button("解析并保存 .eml", type="primary", use_container_width=True):
            if uploaded is None:
                st.warning("请先上传 .eml 文件")
            else:
                try:
                    parsed = parse_eml_bytes(uploaded.getvalue())
                except Exception as exc:  # noqa: BLE001
                    st.error(f"⚠️ .eml 文件解析失败，文件可能已损坏。（{exc}）")

    if parsed is not None:
        try:
            created, record = create_inbound_record(username, parsed, customer_id=customer_id.strip())
        except Exception as exc:  # noqa: BLE001
            st.error(f"⚠️ 保存失败：{exc}")
        else:
            if created:
                st.success("✅ 已保存到待回复队列")
            else:
                if record.get("error"):
                    st.error(f"保存失败：{record['error']}")
                else:
                    st.info("该邮件已存在，已显示已有记录")

            with st.expander("解析结果预览", expanded=True):
                c1, c2 = st.columns(2)
                with c1:
                    st.write("**发件人**", record.get("from_name") or "-")
                    st.write("**邮箱**", record.get("from_email") or "-")
                    st.write("**主题**", record.get("subject") or "-")
                with c2:
                    st.write("**状态**", record.get("status"))
                    st.write("**来源**", record.get("source"))
                    st.write("**ID**", record.get("id"))
                st.text_area("正文", value=record.get("body", ""), height=180, disabled=True)

with queue_tab:
    st.markdown("### 待回复队列")
    status_filter = st.selectbox("状态筛选", ["pending", "drafted", "replied", "archived", "全部"], index=0)
    status = None if status_filter == "全部" else status_filter
    try:
        inbound_emails = list_inbound_emails(username, status=status, limit=100)
    except Exception:  # noqa: BLE001 - a storage read failure must not crash the page
        inbound_emails = []
        st.warning("⚠️ 入站邮件读取失败，请稍后重试。")

    if not inbound_emails:
        st.info("暂无入站邮件。请先在“导入邮件”中添加客户邮件。")
    else:
        st.caption(f"共 {len(inbound_emails)} 封")
        for item in inbound_emails:
            title = item.get("subject") or "无主题邮件"
            sender = item.get("from_name") or item.get("from_email") or "未知发件人"
            with st.expander(f"{item.get('status', 'pending').upper()} · {sender} · {title}", expanded=False):
                meta1, meta2, meta3 = st.columns(3)
                with meta1:
                    st.write("**发件人**", sender)
                    st.write("**邮箱**", item.get("from_email") or "-")
                with meta2:
                    st.write("**主题**", title)
                    st.write("**接收时间**", item.get("received_at") or "-")
                with meta3:
                    st.write("**导入时间**", item.get("created_at") or "-")
                    st.write("**客户ID**", item.get("customer_id") or "-")

                st.text_area("邮件正文", value=item.get("body", ""), height=180, disabled=True, key=f"body_{item['id']}")

                col_a, col_b, col_c = st.columns(3)
                with col_a:
                    if st.button("生成回复草稿", key=f"draft_{item['id']}", type="primary", use_container_width=True):
                        try:
                            seed_inquiry_session_state(st, item)
                            update_inbound_status(username, item["id"], "drafted")
                        except Exception as exc:  # noqa: BLE001
                            st.error(f"⚠️ 操作失败：{exc}")
                        else:
                            st.switch_page("pages/2_📩_询盘回复.py")
                with col_b:
                    if st.button("标记已回复", key=f"replied_{item['id']}", use_container_width=True):
                        try:
                            update_inbound_status(username, item["id"], "replied")
                        except Exception as exc:  # noqa: BLE001
                            st.error(f"⚠️ 更新失败：{exc}")
                        else:
                            st.rerun()
                with col_c:
                    if st.button("归档", key=f"archive_{item['id']}", use_container_width=True):
                        try:
                            update_inbound_status(username, item["id"], "archived")
                        except Exception as exc:  # noqa: BLE001
                            st.error(f"⚠️ 归档失败：{exc}")
                        else:
                            st.rerun()

st.markdown("---")
st.markdown('<div class="footer">💼 外贸AI助手 · 入站邮件 Intake</div>', unsafe_allow_html=True)
