"""
pages/38_🏭_智能寻源.py
----------------------
外贸智能寻源、货源地挖掘与化工类深度定制中心。

功能特性：
1. 全国 50+ 重点外贸产业带与化工园区智能匹配（支持化工 CAS 号检索）。
2. 出口退税、采购成本与净利润精准测算器（支持化工危包费、内陆运杂费、保本价测算）。
3. 全网多渠道精准寻源与海外买家拓展指令生成（1688 / Google X-Ray / LinkedIn / 盖德化工）。
4. 供应商询价 (RFQ)、验厂打样与化工定制采购品质协议生成。
5. AI 智能供应商评估与供应链策略深度诊断。
"""
from __future__ import annotations

import streamlit as st

from utils.ai_gateway import get_gateway
from utils.sourcing_ai import (
    CHEMICAL_MSDS_KEY_SECTIONS,
    DANGEROUS_GOODS_CLASSES,
    build_customization_agreement_text,
    build_sourcing_rfq_prompt,
    calculate_export_profit,
    generate_sourcing_search_queries,
    match_industrial_clusters,
)
from utils.ui_helpers import check_auth, inject_css
from utils.user_prefs import get_prefs

st.set_page_config(
    page_title="智能寻源与化工定制 | 外贸AI助手",
    page_icon="🏭",
    layout="wide",
)
inject_css()
check_auth()

prefs = get_prefs()
default_company = prefs.get("company_name", "")
default_product = prefs.get("default_product", "精细化工品 / 表面活性剂")

# ── 页头 ──────────────────────────────────────────────
st.markdown("""
<div class="hero-section" style="background: linear-gradient(135deg, #0f172a 0%, #1e293b 40%, #0369a1 100%);">
    <h1 class="hero-title">🏭 智能寻源与化工定制中心</h1>
    <p class="hero-subtitle">全国外贸产业带匹配 · 采购退税利润测算 · 化工CAS与危包合规 · 全网精准买家拓客</p>
    <div class="hero-tags">
        <span class="hero-tag">🧪 化工/精细化学品专区</span>
        <span class="hero-tag">🗺️ 50+ 产业带数据库</span>
        <span class="hero-tag">💰 实时退税与保本测算</span>
        <span class="hero-tag">🔍 Google/1688 X-Ray</span>
    </div>
</div>
""", unsafe_allow_html=True)

tab_clusters, tab_calculator, tab_search_engine, tab_rfq_contract, tab_ai_advisor = st.tabs([
    "🗺️ 产业带与货源地匹配",
    "💰 采购成本与退税利润测算",
    "🔍 全网寻源与买家拓展指令",
    "📝 供应商询价与定制协议",
    "🤖 AI 供应链策略深度诊断",
])

# ══════════════════════════════════════════════════════
# Tab 1: 产业带与货源地匹配
# ══════════════════════════════════════════════════════
with tab_clusters:
    st.markdown("### 🗺️ 全国外贸产业带与化工基地智能检索")
    st.caption("输入产品名称、行业关键词或化工品名称，系统自动定位国内核心货源地与集聚优势。")

    # ── 快捷范例 ──────────────────────────────────────────
    sourcing_demo_cols = st.columns(3)
    with sourcing_demo_cols[0]:
        if st.button("🧪 范例1: 医药中间体与精细化工", use_container_width=True, key="demo_cluster_1"):
            st.session_state["cluster_search_kw"] = "医药中间体"
            st.rerun()
    with sourcing_demo_cols[1]:
        if st.button("💡 范例2: LED商业与工矿照明", use_container_width=True, key="demo_cluster_2"):
            st.session_state["cluster_search_kw"] = "LED照明"
            st.rerun()
    with sourcing_demo_cols[2]:
        if st.button("🔧 范例3: 五金工具与电动机械", use_container_width=True, key="demo_cluster_3"):
            st.session_state["cluster_search_kw"] = "电动工具"
            st.rerun()

    col_q1, col_q2 = st.columns([3, 1])
    with col_q1:
        search_kw = st.text_input(
            "搜索产品 / 产业带关键词 / 化工品类",
            value=st.session_state.get("cluster_search_kw", ""),
            placeholder="例如：医药中间体、环己酮、LED、五金工具、表面活性剂、山东...",
            key="cluster_search_input",
        )
    with col_q2:
        chem_filter = st.checkbox("仅显示化工与新材料产业带", value=False)

    clusters = match_industrial_clusters(search_kw, is_chemical_only=chem_filter)

    st.markdown(f"**共检索到 {len(clusters)} 个匹配产业带：**")
    for item in clusters:
        is_chem = item.get("is_chemical", False)
        badge_style = "background: #e0f2fe; color: #0369a1; border: 1px solid #bae6fd;" if is_chem else "background: #f1f5f9; color: #475569; border: 1px solid #e2e8f0;"
        chem_badge = f'<span style="padding: 2px 8px; border-radius: 6px; font-size: 0.75rem; font-weight: 600; {badge_style}">{"🧪 化工新材料" if is_chem else "📦 综合外贸"}</span>'

        with st.container():
            st.markdown(f"""
            <div style="background: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px; padding: 18px 20px; margin-bottom: 14px; box-shadow: 0 1px 3px rgba(0,0,0,0.05);">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                    <div style="font-size: 1.1rem; font-weight: 700; color: #0f172a;">
                        📍 {item['region']} · {item['hub_name']}
                    </div>
                    <div>{chem_badge}</div>
                </div>
                <div style="font-size: 0.9rem; color: #334155; margin-bottom: 6px;">
                    <strong>主营品类：</strong>{item['category']}
                </div>
                <div style="font-size: 0.88rem; color: #475569; margin-bottom: 6px;">
                    <strong>产业集聚优势：</strong>{item['advantages']}
                </div>
                <div style="font-size: 0.85rem; color: #64748b; margin-bottom: 6px;">
                    <strong>代表市场与园区：</strong>{item['famous_markets']}
                </div>
                <div style="font-size: 0.85rem; color: #0284c7; background: #f0f9ff; padding: 8px 12px; border-radius: 6px;">
                    💡 <strong>出口与寻源建议：</strong>{item['export_tips']}
                </div>
            </div>
            """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════
# Tab 2: 采购成本与退税利润测算
# ══════════════════════════════════════════════════════
with tab_calculator:
    st.markdown("### 💰 外贸出口利润、退税与保本底价核算")
    st.caption("综合考虑增值税专用发票抵扣、出口退税率、危险品/普货运杂费及海运成本。")

    col_calc_in, col_calc_res = st.columns([1, 1], gap="large")

    with col_calc_in:
        st.markdown("#### 1. 采购与国内成本输入")
        c1, c2 = st.columns(2)
        with c1:
            p_price = st.number_input("工厂含税采购单价 (CNY)", min_value=0.0, value=100.0, step=5.0)
            vat_pct = st.number_input("增值税率 (%)", min_value=0.0, max_value=30.0, value=13.0, step=1.0)
            rebate_pct = st.number_input("出口退税率 (%)", min_value=0.0, max_value=30.0, value=13.0, step=1.0)
            order_qty = st.number_input("采购/订货总数量", min_value=1.0, value=500.0, step=50.0)
        with c2:
            freight_dom = st.number_input("单件国内运杂费 (CNY)", min_value=0.0, value=2.5, step=0.5)
            packaging_fee = st.number_input("单件包装/打托费 (CNY)", min_value=0.0, value=1.5, step=0.5)
            dg_fee = st.number_input("单件危化品/商检检测费 (CNY)", min_value=0.0, value=0.0, step=0.5, help="化工危险品申报、危包证分摊及商检费用")
            fx_rate = st.number_input("美元汇率 (USD/CNY)", min_value=1.0, value=7.20, step=0.05)

        st.markdown("#### 2. 国际售价与运费")
        c3, c4 = st.columns(2)
        with c3:
            target_fob_usd = st.number_input("目标 FOB 售价 (USD/件)", min_value=0.0, value=18.5, step=0.5, help="填 0 时系统自动以 18% 预期毛利反算")
        with c4:
            ocean_freight = st.number_input("单件国际海运费 (USD)", min_value=0.0, value=1.2, step=0.2)

    # 计算结果
    calc_res = calculate_export_profit(
        purchase_price_cny=p_price,
        vat_rate=vat_pct / 100.0,
        rebate_rate=rebate_pct / 100.0,
        domestic_freight_cny=freight_dom,
        packaging_cny=packaging_fee,
        dg_handling_cny=dg_fee,
        fob_price_usd=target_fob_usd,
        exchange_rate=fx_rate,
        qty=order_qty,
        ocean_freight_usd=ocean_freight,
    )

    with col_calc_res:
        st.markdown("#### 📊 财务与利润测算看板")
        
        # 顶部三大关键指标卡片
        m1, m2, m3 = st.columns(3)
        with m1:
            st.metric("FOB 保本底价", f"${calc_res['breakeven_fob_usd']:.2f}")
        with m2:
            st.metric("单件实际净利润", f"¥{calc_res['unit_profit_cny']:.2f}", delta=f"{calc_res['margin_pct']:.1f}% 毛利率")
        with m3:
            st.metric("订单总净利润", f"¥{calc_res['total_profit_cny']:,.2f}", delta=f"${calc_res['total_profit_usd']:,.2f} USD")

        st.markdown(f"""
        <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 12px; padding: 16px; margin-top: 10px;">
            <table style="width: 100%; font-size: 0.9rem; line-height: 2;">
                <tr><td style="color: #64748b;">工厂含税采购总额：</td><td style="text-align: right; font-weight: 600;">¥{calc_res['purchase_price_cny'] * order_qty:,.2f}</td></tr>
                <tr><td style="color: #64748b;">无税计税基数 (单件)：</td><td style="text-align: right; font-weight: 600;">¥{calc_res['tax_free_base']:.2f}</td></tr>
                <tr><td style="color: #16a34a;">单件出口退税金额：</td><td style="text-align: right; font-weight: 600; color: #16a34a;">+¥{calc_res['tax_rebate_amount']:.2f}</td></tr>
                <tr><td style="color: #0284c7;">扣减退税后实际净采购成本：</td><td style="text-align: right; font-weight: 600; color: #0284c7;">¥{calc_res['net_purchase_cost']:.2f}</td></tr>
                <tr><td style="color: #64748b;">单件国内综合成本 (含运/包/杂)：</td><td style="text-align: right; font-weight: 600;">¥{calc_res['unit_domestic_cost']:.2f}</td></tr>
                <tr style="border-top: 1px solid #cbd5e1;"><td style="color: #0f172a; font-weight: 700;">建议 FOB 报价 (USD)：</td><td style="text-align: right; font-weight: 700; color: #0f172a;">${calc_res['fob_price_usd']:.2f}</td></tr>
                <tr><td style="color: #0f172a; font-weight: 700;">建议 CIF 报价 (USD)：</td><td style="text-align: right; font-weight: 700; color: #0f172a;">${calc_res['cif_price_usd']:.2f}</td></tr>
            </table>
        </div>
        """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════
# Tab 3: 全网寻源与买家拓展指令
# ══════════════════════════════════════════════════════
with tab_search_engine:
    st.markdown("### 🔍 全网高精度寻源与海外买家拓客引擎")
    st.caption("自动生成 1688 / 阿里国际 / Google X-Ray / LinkedIn 采购商精准布尔搜索指令。")

    c_s1, c_s2, c_s3 = st.columns(3)
    with c_s1:
        s_pname = st.text_input("产品名称 (中英文)", value="Cyclohexanone 环己酮", key="s_pname")
    with c_s2:
        s_cas = st.text_input("CAS 号 (化工品选填)", value="108-94-1", placeholder="如：108-94-1", key="s_cas")
    with c_s3:
        s_app = st.text_input("下游应用领域 / 行业", value="Solvent / Coating / Chemical", key="s_app")

    c_cnt, _ = st.columns([1, 2])
    with c_cnt:
        s_country = st.text_input("目标出口国家/地区代码", value="Germany", placeholder="例如：Germany, USA, Vietnam...", key="s_country")

    queries_dict = generate_sourcing_search_queries(
        product_name=s_pname,
        cas_number=s_cas,
        target_country=s_country,
        application_industry=s_app,
    )

    st.markdown("#### 1. 🌐 Google X-Ray 国际买家与分销商深度指令")
    for q_item in queries_dict.get("google_xray", []):
        st.markdown(f"**【{q_item['type']}】**")
        st.code(q_item["query"], language="text")

    st.markdown("#### 2. 👥 LinkedIn 采购决策人与配方研发工程师")
    for q_item in queries_dict.get("linkedin_buyers", []):
        st.markdown(f"**【{q_item['type']}】**")
        st.code(q_item["query"], language="text")

    st.markdown("#### 3. 🏭 1688 与国内产业带源头工厂寻源")
    for q_item in queries_dict.get("domestic_sourcing", []):
        st.markdown(f"**【{q_item['type']}】**")
        st.code(q_item["query"], language="text")


# ══════════════════════════════════════════════════════
# Tab 4: 供应商询价与定制协议
# ══════════════════════════════════════════════════════
with tab_rfq_contract:
    st.markdown("### 📝 供应商询价函 (RFQ) 与外贸定制采购协议")
    st.caption("快速生成向工厂发起的专业询价要求，或定制生产时的品质保证与违约责任协议。")

    sub_t1, sub_t2, sub_t3 = st.tabs(["📤 供应商 RFQ 询价单", "📜 定制采购与品质协议", "⚠️ 化工危化品包装与合规速查"])

    with sub_t1:
        col_rfq1, col_rfq2 = st.columns(2)
        with col_rfq1:
            rfq_pname = st.text_input("询价产品名称", value=s_pname)
            rfq_cas = st.text_input("CAS 编号 (化工品选填)", value=s_cas)
            rfq_spec = st.text_input("规格/纯度要求", value=">= 99.8% 优级品, 水分 <= 0.05%")
            rfq_qty = st.text_input("采购量", value="1*20GP (16.8 MT) / 80 桶")
        with col_rfq2:
            rfq_pkg = st.text_input("包装要求", value="200L 新镀锌铁桶，打托缠膜")
            rfq_target_price = st.text_input("目标含税出厂价", value="¥8,500/吨 (含13%专票及运费)")
            rfq_extra = st.text_input("特殊要求", value="每批需提供原厂 COA，支持 SGS 出厂封样复检")
            rfq_is_chem = st.checkbox("该产品属于化工品/需要检测报告", value=True)

        rfq_text = build_sourcing_rfq_prompt(
            product_name=rfq_pname,
            cas_number=rfq_cas,
            purity_spec=rfq_spec,
            quantity_target=rfq_qty,
            packaging_requirement=rfq_pkg,
            target_price_cny=rfq_target_price,
            special_requirements=rfq_extra,
            is_chemical=rfq_is_chem,
        )
        st.text_area("生成的专业 RFQ 询价函 (可直接微信/邮件发送工厂)", value=rfq_text, height=260)

    with sub_t2:
        col_c1, col_c2 = st.columns(2)
        with col_c1:
            c_buyer = st.text_input("甲方 (采购方)", value=default_company or "深圳市某某进出口贸易有限公司")
            c_supp = st.text_input("乙方 (供货工厂)", value="山东某某精细化工制造有限公司")
        with col_c2:
            c_spec = st.text_input("品质指标要求", value="主纯度 >= 99.8%, 水分 <= 0.05%, 色度 APHA <= 10")
            c_tol = st.text_input("公差与违约限定", value="水分超标 0.01% 按不合格处理，交期延误每超 1 天扣除货款 0.5%")

        agreement_txt = build_customization_agreement_text(
            buyer_company=c_buyer,
            supplier_company=c_supp,
            product_name=rfq_pname,
            specs=c_spec,
            tolerance_terms=c_tol,
            is_chemical=rfq_is_chem,
        )
        st.text_area("外贸定制采购与品质保证协议", value=agreement_txt, height=320)
        st.download_button(
            "📥 下载定制采购协议 (.txt)",
            data=agreement_txt.encode("utf-8"),
            file_name=f"custom_procurement_agreement_{rfq_pname.split()[0]}.txt",
            mime="text/plain",
        )

    with sub_t3:
        st.markdown("#### 🧪 国际危险货物分类 (Class 1-9) 与包装要求")
        for dg_code, dg_info in DANGEROUS_GOODS_CLASSES.items():
            st.markdown(f"**{dg_code} · {dg_info['name_zh']}**：{dg_info['desc']}")
        
        st.markdown("---")
        st.markdown("#### 📋 国际标准 MSDS/SDS 16 项必备检查清单")
        for sec in CHEMICAL_MSDS_KEY_SECTIONS:
            st.markdown(f"- {sec}")


# ══════════════════════════════════════════════════════
# Tab 5: AI 供应链策略深度诊断
# ══════════════════════════════════════════════════════
with tab_ai_advisor:
    st.markdown("### 🤖 AI 供应链寻源策略与供需格局深度诊断")
    st.caption("利用大模型分析目标产品在全球供应链中的供需关系、源头工厂分布、环保安监壁垒及谈判压价策略。")

    col_ai_p, col_ai_btn = st.columns([3, 1])
    with col_ai_p:
        ai_diag_product = st.text_input("输入要分析的产品/CAS号/行业", value=s_pname, key="ai_diag_product")
    with col_ai_btn:
        st.markdown("<div style='margin-top: 28px;'></div>", unsafe_allow_html=True)
        run_ai_diag = st.button("🚀 开始 AI 寻源诊断", use_container_width=True, type="primary")

    if run_ai_diag:
        gw = get_gateway()
        diag_prompt = f"""
请作为资深外贸供应链总监与资深化工寻源专家，为以下产品制定一份深度寻源与业务开拓策略：

【分析目标产品】：{ai_diag_product}
【CAS 编号】：{s_cas}
【下游目标应用】：{s_app}
【目标出口市场】：{s_country}

请从以下五个核心维度进行系统剖析：
1. 【国内源头产业带与工厂格局】：主要集中在哪些省市园区？大厂与中小厂的差异？
2. 【外贸出口关键合规与技术壁垒】：（如化工纯度、REACH/FDA认证、危包证、海运要求等）
3. 【采购议价与控本技巧】：原料成本结构是什么？如何与工厂压价/锁价？如何防范以次充好？
4. 【海外目标买家画像与拓客切入点】：海外主要买家是哪些类型？如何找到配方师或采购总监？
5. 【外贸风控与质量验收要点】：如何设计打样、封样、第三方检测（SGS）及账期风控？

输出要求：结构清晰、专业干练、包含实战案例和具体数据建议。
"""
        with st.spinner("AI 供应链专家正在分析产业格局与寻源策略..."):
            diag_result = gw.generate(
                prompt=diag_prompt,
                system_prompt="你是一位拥有 15 年外贸供应链、精细化工与跨国大宗集采经验的首席采购官 (CPO)。",
                tier="balanced",
            )
            st.markdown(diag_result)
