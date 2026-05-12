"""
pages/10_📅_跟进日历.py
邮件自动化工作流：记录已发邮件，智能提醒跟进时间节点。
"""
import streamlit as st

from utils.ui_helpers import check_auth, inject_css
from utils.workflow import (
    FOLLOWUP_RULES,
    add_workflow,
    get_all_workflows,
    get_due_workflows,
    get_workflow_stats,
    mark_followup_done,
    update_workflow_status,
)

st.set_page_config(page_title="跟进日历 | 外贸AI助手", page_icon="📅", layout="wide")
inject_css()
check_auth()

# ── 页头 ──────────────────────────────────────────────
st.markdown("""
<div class="hero-section">
    <h1 class="hero-title">📅 跟进日历</h1>
    <p class="hero-subtitle">记录已发邮件，智能提醒跟进节点，不再漏掉任何商机</p>
</div>
""", unsafe_allow_html=True)

# ── 统计数据 ──────────────────────────────────────────
stats = get_workflow_stats()
c1, c2, c3, c4 = st.columns(4)
c1.metric("📬 跟踪中", stats["active"])
c2.metric("✅ 已回复", stats["replied"])
c3.metric("⏰ 今日待跟进", stats["due"], delta="需要行动" if stats["due"] > 0 else None,
          delta_color="inverse" if stats["due"] > 0 else "off")
c4.metric("📊 总计", stats["total"])

st.markdown("---")

# ── 今日待跟进提醒 ────────────────────────────────────
due_items = get_due_workflows()
if due_items:
    st.markdown(f"### ⏰ 今日待跟进（{len(due_items)} 位）")
    for item in due_items:
        rule = item["_rule"]
        days = item["_days_elapsed"]
        with st.container():
            st.markdown(
                f'<div class="tip-card">'
                f'🔔 <b>{item["customer"]}</b>'
                f'{"（" + item["company"] + "）" if item["company"] else ""} · '
                f'{item["product"]} · 已发送 <b>{days}</b> 天 · 建议：{rule["hint"]}'
                f'</div>',
                unsafe_allow_html=True,
            )
            col_a, col_b, col_c = st.columns(3)
            with col_a:
                if st.button("📬 去生成跟进邮件", key=f"gen_{item['id']}", use_container_width=True):
                    st.session_state["followup_customer_val"] = (
                        f"{item['customer']} / {item['company']}" if item["company"]
                        else item["customer"]
                    )
                    st.session_state["followup_product_val"] = item["product"]
                    st.switch_page("pages/5_📬_跟进邮件.py")
            with col_b:
                if st.button(f"✅ 标记「{rule['label']}」已完成", key=f"done_{item['id']}", use_container_width=True):
                    mark_followup_done(item["id"], rule["label"])
                    st.success(f"已标记完成：{rule['label']}")
                    st.rerun()
            with col_c:
                if st.button("🎉 客户已回复", key=f"replied_{item['id']}", use_container_width=True):
                    update_workflow_status(item["id"], "已回复")
                    st.success("已标记为：已回复")
                    st.rerun()
    st.markdown("---")

# ── 新增工作流 ────────────────────────────────────────
st.markdown("### ➕ 记录新发邮件")
st.markdown('<div class="main-form">', unsafe_allow_html=True)
st.markdown('<div class="tip-card">💡 发出开发信后记录到这里，系统会在 3天/1周/2周/1个月 自动提醒你跟进。</div>', unsafe_allow_html=True)

col1, col2 = st.columns(2)
with col1:
    new_customer = st.text_input("客户姓名 *", placeholder="John Smith", key="wf_customer")
    new_company  = st.text_input("客户公司", placeholder="ABC Trading Co.", key="wf_company")
with col2:
    new_product  = st.text_input("发送的产品 *", placeholder="LED Desk Lamp", key="wf_product")
    new_email    = st.text_input("客户邮箱", placeholder="john@abc.com", key="wf_email")

new_notes = st.text_input("备注（可选）", placeholder="LinkedIn 联系/展会认识", key="wf_notes")

if st.button("📬 记录已发邮件", type="primary", use_container_width=True):
    if not new_customer or not new_product:
        st.warning("⚠️ 请填写客户姓名和产品名称")
    else:
        add_workflow(new_customer, new_product, new_company, new_email, new_notes)
        st.success(f"✅ 已记录！将在 3天后提醒第一次跟进 → {new_customer} / {new_product}")
        st.rerun()

st.markdown("</div>", unsafe_allow_html=True)

# ── 所有工作流列表 ────────────────────────────────────
all_wfs = get_all_workflows()
if all_wfs:
    st.markdown("---")
    st.markdown(f"### 📋 所有跟进记录（{len(all_wfs)} 条）")

    # 状态筛选
    status_filter = st.selectbox("筛选状态", ["全部", "进行中", "已回复", "已关闭"], key="wf_filter")
    filtered = all_wfs if status_filter == "全部" else [w for w in all_wfs if w["status"] == status_filter]

    for wf in filtered:
        done_labels = [f["stage_label"] for f in wf.get("followups", [])]
        status_icon = {"进行中": "🔵", "已回复": "✅", "已关闭": "⚫"}.get(wf["status"], "•")

        with st.expander(
            f"{status_icon} **{wf['customer']}** · {wf['product']}"
            f'{"（" + wf["company"] + "）" if wf["company"] else ""}'
            f' — 发送于 {wf["sent_at"]}',
            expanded=False,
        ):
            # 跟进进度条
            st.markdown("**跟进节点进度：**")
            prog_cols = st.columns(len(FOLLOWUP_RULES))
            for i, rule in enumerate(FOLLOWUP_RULES):
                done = rule["label"] in done_labels
                color = "#22c55e" if done else "#e5e7eb"
                icon  = "✅" if done else "⭕"
                prog_cols[i].markdown(
                    f'<div style="text-align:center;padding:0.5rem;border-radius:8px;'
                    f'background:{color};font-size:0.8rem;">{icon}<br>{rule["label"]}</div>',
                    unsafe_allow_html=True,
                )

            if wf.get("notes"):
                st.caption(f"备注: {wf['notes']}")
            if wf.get("email"):
                st.caption(f"邮箱: {wf['email']}")

            # 操作
            col_x, col_y = st.columns(2)
            with col_x:
                if wf["status"] == "进行中":
                    if st.button("🎉 标记已回复", key=f"replied2_{wf['id']}", use_container_width=True):
                        update_workflow_status(wf["id"], "已回复")
                        st.rerun()
            with col_y:
                if wf["status"] != "已关闭":
                    if st.button("⚫ 关闭跟进", key=f"close_{wf['id']}", use_container_width=True):
                        update_workflow_status(wf["id"], "已关闭")
                        st.rerun()

st.markdown("---")
st.markdown('<div class="footer">💼 外贸AI助手 · 跟进日历</div>', unsafe_allow_html=True)
