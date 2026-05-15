"""
pages/22_📈_数据导出.py
Pro 功能：全量数据导出（JSON / CSV）、导入恢复、数据统计摘要。
"""
from __future__ import annotations

import csv
import io
import json

import streamlit as st

from utils.customers import get_customers, import_customers
from utils.history import _get_history, get_history_count, import_history
from utils.pricing import check_feature_access
from utils.templates import _get_store, import_templates
from utils.ui_helpers import check_auth, inject_css
from utils.user_auth import get_current_user
from utils.workflow import get_all_workflows, import_workflows

st.set_page_config(page_title="数据导出 | 外贸AI助手", page_icon="📈", layout="wide")
inject_css()
check_auth()

# ── 页头 ──────────────────────────────────────────────
st.markdown("""
<div class="hero-section">
    <h1 class="hero-title">📈 数据导出 / 导入</h1>
    <p class="hero-subtitle">备份所有数据、迁移账户、导出 CSV 分析报表</p>
</div>
""", unsafe_allow_html=True)

# ── 功能门控 ──────────────────────────────────────────
current_user = get_current_user()
export_access = True
if current_user and current_user.get("username") not in (None, "admin"):
    export_access = check_feature_access(current_user["username"], "data_export")

if not export_access:
    st.warning("🔒 数据导出/导入功能需要 **Pro 套餐**，请升级以解锁。")
    if st.button("🚀 前往升级套餐", type="primary", use_container_width=True):
        st.switch_page("pages/11_👤_账户管理.py")
    st.stop()

# ── 数据统计摘要 ──────────────────────────────────────
st.markdown("### 📊 数据统计")

customers = get_customers()
history = _get_history()
templates = _get_store()
workflows = get_all_workflows()

c1, c2, c3, c4 = st.columns(4)
c1.metric("👥 客户记录", f"{len(customers)} 条")
c2.metric("📋 历史记录", f"{get_history_count()} 条")
c3.metric("📌 模板数量", f"{sum(len(v) for v in templates.values())} 个")
c4.metric("📅 跟进任务", f"{len(workflows)} 条")

st.markdown("---")

# ══════════════════════════════════════════════════════
# 导出区域
# ══════════════════════════════════════════════════════
st.markdown("### 📥 导出数据")

exp_tab1, exp_tab2, exp_tab3 = st.tabs(["🗄️ 完整备份 (JSON)", "👥 客户列表 (CSV)", "📋 生成历史 (CSV)"])

with exp_tab1:
    st.markdown("将所有数据打包为一个 JSON 文件，适合完整备份和账户迁移。")
    export_data = {
        "version": "1.0",
        "customers": customers,
        "history": history,
        "templates": templates,
        "workflows": workflows,
    }
    export_json = json.dumps(export_data, ensure_ascii=False, indent=2)
    st.metric("备份大小", f"{len(export_json.encode('utf-8')) / 1024:.1f} KB")
    st.download_button(
        "📥 下载完整备份 (JSON)",
        export_json,
        file_name="trade_ai_helper_backup.json",
        mime="application/json",
        use_container_width=True,
        type="primary",
    )

with exp_tab2:
    st.markdown("导出客户列表为 CSV，可在 Excel 中打开分析或批量处理。")
    if not customers:
        st.info("暂无客户数据。")
    else:
        csv_buf = io.StringIO()
        fieldnames = ["company", "contact", "email", "phone", "country", "industry",
                      "stage", "last_contact", "notes"]
        writer = csv.DictWriter(csv_buf, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for c in customers:
            writer.writerow({k: c.get(k, "") for k in fieldnames})
        st.metric("客户数量", f"{len(customers)} 条")
        st.download_button(
            "📥 下载客户列表 (CSV)",
            csv_buf.getvalue().encode("utf-8-sig"),  # BOM for Excel compatibility
            file_name="customers_export.csv",
            mime="text/csv",
            use_container_width=True,
            type="primary",
        )

with exp_tab3:
    st.markdown("导出 AI 生成历史为 CSV，可用于分析生产效率或内容存档。")
    if not history:
        st.info("暂无历史记录。")
    else:
        csv_buf = io.StringIO()
        fieldnames = ["timestamp", "feature", "title", "content"]
        writer = csv.DictWriter(csv_buf, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for h in history:
            writer.writerow({
                "timestamp": h.get("timestamp", ""),
                "feature":   h.get("feature", ""),
                "title":     h.get("title", ""),
                "content":   h.get("content", "")[:500],  # Truncate long content
            })
        st.metric("历史记录数", f"{len(history)} 条")
        st.download_button(
            "📥 下载历史记录 (CSV)",
            csv_buf.getvalue().encode("utf-8-sig"),
            file_name="history_export.csv",
            mime="text/csv",
            use_container_width=True,
            type="primary",
        )

st.markdown("---")

# ══════════════════════════════════════════════════════
# 导入区域
# ══════════════════════════════════════════════════════
st.markdown("### 📤 导入数据")
st.warning("⚠️ 导入操作将**覆盖**当前所有数据，请先导出备份后再执行。")

imp_tab1, imp_tab2 = st.tabs(["🗄️ 完整恢复 (JSON)", "👥 导入客户 (CSV)"])

with imp_tab1:
    uploaded_json = st.file_uploader("选择备份文件 (.json)", type=["json"], key="import_json_full")
    if uploaded_json:
        try:
            imported = json.loads(uploaded_json.read().decode("utf-8"))
            # Preview what will be imported
            st.markdown("**预览将导入的数据：**")
            prev_c1, prev_c2, prev_c3, prev_c4 = st.columns(4)
            prev_c1.metric("客户", len(imported.get("customers", [])))
            prev_c2.metric("历史", len(imported.get("history", [])))
            prev_c3.metric("模板", sum(len(v) for v in imported.get("templates", {}).values()))
            prev_c4.metric("跟进", len(imported.get("workflows", [])))

            confirm_key = f"confirm_import_{uploaded_json.name}"
            if confirm_key not in st.session_state:
                st.session_state[confirm_key] = False

            if st.button("⚠️ 确认导入（覆盖当前数据）", type="primary", use_container_width=True):
                if "customers" in imported:
                    import_customers(imported["customers"])
                if "history" in imported:
                    import_history(imported["history"])
                if "templates" in imported:
                    import_templates(imported["templates"])
                if "workflows" in imported:
                    import_workflows(imported["workflows"])
                st.success("✅ 数据导入成功！页面将自动刷新。")
                st.rerun()
        except Exception as e:
            st.error(f"❌ 文件解析失败：{e}")

with imp_tab2:
    st.markdown("从 CSV 文件批量导入客户。需要包含 `company`、`contact` 列。")
    st.markdown("**CSV 格式示例：**")
    sample_csv = "company,contact,email,phone,country,industry,stage,notes\nABC Trading,John Smith,john@abc.com,+1-555-0100,USA,Electronics,新客户,从展会获取"
    st.code(sample_csv, language="text")
    st.download_button(
        "📥 下载 CSV 模板",
        sample_csv.encode("utf-8-sig"),
        file_name="customers_import_template.csv",
        mime="text/csv",
        use_container_width=True,
    )

    uploaded_csv = st.file_uploader("选择客户 CSV 文件", type=["csv"], key="import_csv_customers")
    if uploaded_csv:
        try:
            decoded = uploaded_csv.read().decode("utf-8-sig")
            reader = csv.DictReader(io.StringIO(decoded))
            rows = list(reader)
            cols = set(reader.fieldnames or [])

            if "company" not in cols:
                st.error("❌ CSV 缺少必填列：`company`")
            else:
                st.success(f"✅ 检测到 {len(rows)} 行数据，列：{', '.join(sorted(cols))}")
                st.dataframe(
                    [{k: v for k, v in r.items()} for r in rows[:5]],
                    use_container_width=True,
                )
                if st.button("📤 导入客户数据", type="primary", use_container_width=True):
                    # Merge with existing customers (append, no overwrite)
                    existing = get_customers()
                    existing.extend(rows)
                    import_customers(existing)
                    st.success(f"✅ 成功导入 {len(rows)} 条客户记录！")
                    st.rerun()
        except Exception as e:
            st.error(f"❌ CSV 解析失败：{e}")

st.markdown("---")
st.markdown('<div class="footer">💼 外贸AI助手 · 数据导出</div>', unsafe_allow_html=True)
