"""
pages/9_📋_历史记录.py
查看所有 AI 生成的历史记录，支持筛选、搜索、复用。
"""
import streamlit as st
from utils.ui_helpers import inject_css, check_auth, copy_button
from utils.history import get_history, clear_history, get_history_count
from utils.pricing import check_feature_access
from utils.user_auth import get_current_user

st.set_page_config(page_title="历史记录 | 外贸AI助手", page_icon="📋", layout="wide")
inject_css()
check_auth()

# ── 页头 ──────────────────────────────────────────────
st.markdown("""
<div class="hero-section">
    <h1 class="hero-title">📋 生成历史记录</h1>
    <p class="hero-subtitle">所有 AI 生成结果自动保存，随时回看复用</p>
</div>
""", unsafe_allow_html=True)

# ── 筛选 + 统计 ──────────────────────────────────────
total = get_history_count()
st.markdown(f"共 **{total}** 条记录（本次会话）")

col_f1, col_f2, col_f3 = st.columns([2, 2, 1])
with col_f1:
    filter_feature = st.selectbox(
        "按功能筛选",
        ["全部", "开发信", "询盘回复", "产品介绍", "跟进邮件", "产品上架", "社媒文案"],
    )
with col_f2:
    search_q = st.text_input("搜索关键词", placeholder="搜索标题或内容...")
with col_f3:
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🗑️ 清空历史", use_container_width=True):
        clear_history()
        st.success("已清空所有历史记录")
        st.rerun()

# ── 获取并渲染历史 ────────────────────────────────────
feature_filter = None if filter_feature == "全部" else filter_feature
records = get_history(feature=feature_filter, limit=50)

# 搜索过滤
if search_q.strip():
    q = search_q.strip().lower()
    records = [
        r for r in records
        if q in r["title"].lower() or q in r["content"].lower()
    ]

if not records:
    st.info("暂无记录。使用任意 AI 功能后，结果会自动保存到这里。")
else:
    for i, record in enumerate(records):
        icon_map = {
            "开发信": "📧", "询盘回复": "📩", "产品介绍": "📑",
            "跟进邮件": "📬", "产品上架": "🛒", "社媒文案": "💬",
        }
        icon = icon_map.get(record["feature"], "📝")

        with st.expander(
            f"{icon} **{record['feature']}** · {record['title']} — {record['timestamp']}",
            expanded=(i == 0),
        ):
            # 内容预览
            st.text_area(
                "生成内容",
                record["content"],
                height=180,
                key=f"history_content_{i}",
                disabled=True,
            )

            # 操作按钮
            col1, col2, col3 = st.columns(3)
            with col1:
                copy_button(record["content"], f"history_copy_{i}")
            with col2:
                st.download_button(
                    "📥 下载",
                    record["content"],
                    file_name=f"{record['feature']}_{record['title'][:20]}.txt",
                    mime="text/plain",
                    use_container_width=True,
                    key=f"history_dl_{i}",
                )
            with col3:
                # 显示生成参数（如果有）
                if record.get("params"):
                    with st.popover("📌 参数详情"):
                        for k, v in record["params"].items():
                            if v:
                                st.caption(f"**{k}**: {v[:50]}")

# ── 数据导出/导入 ────────────────────────────────────
st.markdown("---")
st.markdown("### 💾 数据导出 / 导入")

# Feature gating: data export requires Pro tier
_current_user = get_current_user()
_export_access = True
if _current_user and _current_user.get("username") not in (None, "admin"):
    _export_access = check_feature_access(_current_user["username"], "data_export")

if not _export_access:
    st.info("🔒 数据导出功能需要 Pro 套餐，请升级以解锁")
else:
    st.caption("导出所有数据为 JSON 文件，可用于备份或迁移。导入会覆盖当前数据。")

    import json as _json
    from utils.history import _get_history
    from utils.templates import _get_store
    from utils.customers import import_customers
    from utils.workflow import import_workflows
    from utils.history import import_history
    from utils.templates import import_templates

    # 收集所有可导出数据
    export_data = {
        "history": _get_history(),
        "templates": _get_store(),
        "customers": st.session_state.get("customers", []),
        "workflows": st.session_state.get("email_workflows", []),
    }

    col_exp, col_imp = st.columns(2)
    with col_exp:
        export_json = _json.dumps(export_data, ensure_ascii=False, indent=2)
        st.download_button(
            "📥 导出全部数据 (JSON)",
            export_json,
            file_name="trade_ai_helper_backup.json",
            mime="application/json",
            use_container_width=True,
        )
    with col_imp:
        uploaded = st.file_uploader("📤 导入数据", type=["json"], key="import_json")
        if uploaded:
            try:
                imported = _json.loads(uploaded.read().decode("utf-8"))
                if st.button("确认导入（会覆盖当前数据）", type="primary", use_container_width=True):
                    if "history" in imported:
                        import_history(imported["history"])
                    if "templates" in imported:
                        import_templates(imported["templates"])
                    if "customers" in imported:
                        import_customers(imported["customers"])
                    if "workflows" in imported:
                        import_workflows(imported["workflows"])
                    st.success("✅ 数据导入成功！")
                    st.rerun()
            except Exception as e:
                st.error(f"❌ 导入失败：{e}")

st.markdown("---")
st.markdown('<div class="footer">💼 外贸AI助手 · 历史记录</div>', unsafe_allow_html=True)
