"""
pages/7_📇_客户管理.py
轻量级客户 CRM：管理客户信息，追踪沟通历史，支持评分和标签。
"""
from datetime import datetime

import streamlit as st

from utils.customers import (
    PREDEFINED_TAGS,
    add_customer,
    add_tag,
    compute_customer_score,
    delete_customer,
    get_customers,
    remove_tag,
)
from utils.ui_helpers import check_auth, inject_css
from utils.workflow import create_workflow_from_customer

st.set_page_config(page_title="客户管理 | 外贸AI助手", page_icon="📇", layout="wide")
inject_css()
check_auth()

# ── 初始化客户数据 ────────────────────────────────────
customers = get_customers()

# ── 页头 ──────────────────────────────────────────────
st.markdown("""
<div class="hero-section">
    <h1 class="hero-title">📇 客户管理</h1>
    <p class="hero-subtitle">轻量 CRM · 记录客户信息 · 追踪沟通状态</p>
</div>
""", unsafe_allow_html=True)

# ── 新增客户 ──────────────────────────────────────────
st.markdown('<div class="main-form">', unsafe_allow_html=True)
st.markdown("#### ➕ 新增客户")

col1, col2, col3 = st.columns(3)
with col1:
    new_company = st.text_input("公司名称 *", placeholder="ABC Trading Co.", key="crm_new_company")
    new_contact = st.text_input("联系人", placeholder="John Smith", key="crm_new_contact")
with col2:
    new_email = st.text_input("邮箱", placeholder="john@abctrading.com", key="crm_new_email")
    new_country = st.selectbox("国家/地区", [
        "美国", "英国", "德国", "法国", "西班牙", "巴西", "墨西哥",
        "印度", "日本", "韩国", "澳大利亚", "加拿大", "沙特", "阿联酋",
        "俄罗斯", "南非", "尼日利亚", "其他",
    ], key="crm_new_country")
with col3:
    new_product = st.text_input("关注产品", placeholder="LED Desk Lamp", key="crm_new_product")
    new_stage = st.selectbox("客户阶段", [
        "待开发", "已发信", "已询盘", "已报价", "已发样", "谈判中", "已下单", "长期客户",
    ], key="crm_new_stage")

new_notes = st.text_input("备注", placeholder="通过 LinkedIn 找到的客户", key="crm_new_notes")

if st.button("💾 添加客户", type="primary", use_container_width=True):
    if not new_company.strip():
        st.warning("⚠️ 请填写公司名称")
    else:
        customer_data = {
            "company": new_company.strip(),
            "contact": new_contact.strip(),
            "email": new_email.strip(),
            "country": new_country,
            "product": new_product.strip(),
            "stage": new_stage,
            "notes": new_notes.strip(),
            "created_at": datetime.now().strftime("%Y-%m-%d"),
            "last_contact": datetime.now().strftime("%Y-%m-%d"),
        }
        add_customer(customer_data)
        st.success(f"✅ 已添加客户：{new_company}")
        if new_stage in ["已发信", "已询盘", "已报价", "已发样", "谈判中"]:
            if create_workflow_from_customer(customer_data):
                st.info("📅 已自动创建跟进提醒")
        st.rerun()

st.markdown("</div>", unsafe_allow_html=True)

# ── 客户列表 ──────────────────────────────────────────
st.markdown("---")
st.markdown(f"### 📋 客户列表（{len(customers)} 位）")

if not customers:
    st.info("暂无客户记录，请在上方添加。")
else:
    # 筛选
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        filter_stage = st.selectbox(
            "按阶段筛选",
            ["全部"] + list(set(c["stage"] for c in customers)),
            key="crm_filter_stage",
        )
    with col_f2:
        filter_search = st.text_input("搜索（公司名/联系人/产品）", key="crm_filter_search")

    # 应用筛选
    filtered = customers
    if filter_stage != "全部":
        filtered = [c for c in filtered if c["stage"] == filter_stage]
    if filter_search.strip():
        q = filter_search.strip().lower()
        filtered = [
            c for c in filtered
            if q in c["company"].lower()
            or q in c["contact"].lower()
            or q in c.get("product", "").lower()
        ]

    # Sort options + tag filter
    col_f3, col_f4 = st.columns(2)
    with col_f3:
        sort_by = st.selectbox("排序方式", ["最新添加", "评分最高", "最近联系"], key="crm_sort")
    with col_f4:
        all_tags = sorted({t for c in filtered for t in c.get("tags", [])})
        filter_tag = st.selectbox("按标签筛选", ["全部"] + all_tags, key="crm_filter_tag")

    if filter_tag != "全部":
        filtered = [c for c in filtered if filter_tag in c.get("tags", [])]
    if sort_by == "评分最高":
        filtered = sorted(filtered, key=lambda c: compute_customer_score(c), reverse=True)
    elif sort_by == "最近联系":
        filtered = sorted(filtered, key=lambda c: c.get("last_contact", ""), reverse=True)

    # 渲染表格
    for i, cust in enumerate(filtered):
        score = compute_customer_score(cust)
        tags = cust.get("tags", [])
        tags_str = " ".join(f"#{t}" for t in tags) if tags else ""
        score_color = "#22c55e" if score >= 70 else "#f59e0b" if score >= 40 else "#6b7280"
        score_badge = (
            f'<span style="background:{score_color};color:white;padding:0.15rem 0.5rem;'
            f'border-radius:8px;font-size:0.75rem;font-weight:700;">{score}分</span>'
        )
        with st.expander(
            f"**{cust['company']}** — {cust['contact']} ({cust['stage']})  {tags_str}",
            expanded=False,
        ):
            c1, c2, c3 = st.columns(3)
            c1.write(f"📧 {cust['email'] or '—'}")
            c2.write(f"🌍 {cust['country']}")
            c3.markdown(f"📦 {cust['product'] or '—'}  {score_badge}", unsafe_allow_html=True)

            st.caption(f"添加日期: {cust['created_at']} | 最后联系: {cust['last_contact']}")
            if cust.get("notes"):
                st.write(f"📝 {cust['notes']}")

            # 标签管理
            st.markdown("**🏷️ 标签：**")
            tag_cols = st.columns(len(PREDEFINED_TAGS) + 1)
            real_idx = customers.index(cust)
            for ti, tag in enumerate(PREDEFINED_TAGS):
                has_tag = tag in tags
                with tag_cols[ti]:
                    if has_tag:
                        if st.button(f"✅ {tag}", key=f"tag_rm_{real_idx}_{tag}", use_container_width=True):
                            remove_tag(real_idx, tag)
                            st.rerun()
                    else:
                        if st.button(f"＋ {tag}", key=f"tag_add_{real_idx}_{tag}", use_container_width=True):
                            add_tag(real_idx, tag)
                            st.rerun()

            # 操作按钮
            col_a1, col_a2, col_a3 = st.columns(3)
            with col_a1:
                if st.button("📧 生成开发信", key=f"crm_email_{i}", use_container_width=True):
                    st.session_state["email_product_val"] = cust.get("product", "")
                    st.session_state["email_customer_val"] = f"{cust['contact']}, {cust['company']}"
                    st.switch_page("pages/1_📧_开发信.py")
            with col_a2:
                if st.button("📬 生成跟进", key=f"crm_followup_{i}", use_container_width=True):
                    st.session_state["followup_customer_val"] = f"{cust['contact']} / {cust['company']}"
                    st.session_state["followup_product_val"] = cust.get("product", "")
                    st.switch_page("pages/5_📬_跟进邮件.py")
            with col_a3:
                if st.button("🗑️ 删除", key=f"crm_del_{i}", use_container_width=True):
                    # 找到原始索引并删除
                    idx = customers.index(cust)
                    delete_customer(idx)
                    st.rerun()

st.markdown("---")
st.markdown('<div class="footer">💼 外贸AI助手 · 客户管理</div>', unsafe_allow_html=True)
