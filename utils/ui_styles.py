"""Shared Streamlit CSS for ui_helpers."""
from __future__ import annotations

# ---------------------------------------------------------------------------
# 全局 CSS
# ---------------------------------------------------------------------------
_CSS = """
<style>
    /* ── Google Fonts ── */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=Noto+Sans+SC:wght@300;400;500;600;700&display=swap');

    /* ── Base ── */
    * { font-family: 'Inter', 'Noto Sans SC', 'Microsoft YaHei', sans-serif !important; }
    :root {
        --primary:   #2563eb;
        --primary-light: #eff6ff;
        --primary-dark:  #1e40af;
        --accent:    #7c3aed;
        --success:   #059669;
        --warning:   #d97706;
        --surface:   #ffffff;
        --surface-2: #f8fafc;
        --border:    #e2e8f0;
        --text-1:    #0f172a;
        --text-2:    #475569;
        --text-3:    #94a3b8;
        --radius-lg: 16px;
        --radius-md: 10px;
        --radius-sm: 6px;
        --shadow-sm: 0 1px 3px rgba(0,0,0,0.07), 0 1px 2px rgba(0,0,0,0.05);
        --shadow-md: 0 4px 16px rgba(0,0,0,0.08), 0 2px 4px rgba(0,0,0,0.04);
        --shadow-lg: 0 10px 40px rgba(0,0,0,0.10), 0 4px 12px rgba(0,0,0,0.06);
    }

    .block-container { padding: 1.5rem 2.5rem !important; max-width: 1320px !important; }
    h1, h2, h3 { font-weight: 700 !important; color: var(--text-1) !important; }
    h3 { font-size: 1.05rem !important; }

    /* ── Hero ── */
    .hero-section {
        background: linear-gradient(135deg, #0f172a 0%, #1e3a8a 40%, #4f46e5 75%, #7c3aed 100%);
        padding: 2.8rem 2.5rem 2.4rem;
        border-radius: 20px;
        color: white;
        margin-bottom: 2rem;
        position: relative;
        overflow: hidden;
    }
    .hero-section::before {
        content: '';
        position: absolute; inset: 0;
        background: radial-gradient(ellipse at 80% 50%, rgba(124,58,237,0.35) 0%, transparent 60%),
                    radial-gradient(ellipse at 20% 80%, rgba(37,99,235,0.25) 0%, transparent 50%);
        pointer-events: none;
    }
    .hero-badge {
        display: inline-flex; align-items: center; gap: 6px;
        background: rgba(255,255,255,0.12); backdrop-filter: blur(8px);
        border: 1px solid rgba(255,255,255,0.2);
        border-radius: 20px; padding: 4px 14px; font-size: 0.78rem;
        font-weight: 600; letter-spacing: 0.04em; margin-bottom: 1rem;
        color: rgba(255,255,255,0.9);
    }
    .hero-title {
        font-size: 2.4rem !important; font-weight: 800 !important;
        line-height: 1.2 !important; margin-bottom: 0.6rem !important;
        letter-spacing: -0.02em;
    }
    .hero-title span { color: #93c5fd; }
    .hero-subtitle { font-size: 1rem; opacity: 0.82; line-height: 1.6; max-width: 560px; }
    .hero-tags {
        display: flex; flex-wrap: wrap; gap: 8px; margin-top: 1.4rem;
    }
    .hero-tag {
        background: rgba(255,255,255,0.12); backdrop-filter: blur(6px);
        border: 1px solid rgba(255,255,255,0.18); border-radius: 20px;
        padding: 4px 12px; font-size: 0.8rem; color: rgba(255,255,255,0.9);
        font-weight: 500;
    }
    .hero-stats {
        display: flex; gap: 2rem; margin-top: 1.6rem;
        padding-top: 1.4rem; border-top: 1px solid rgba(255,255,255,0.15);
    }
    .hero-stat-num { font-size: 1.55rem; font-weight: 800; color: #fff; }
    .hero-stat-lbl { font-size: 0.75rem; color: rgba(255,255,255,0.65); margin-top: 2px; }

    /* ── Stat cards (overview row) ── */
    .stat-card {
        background: var(--surface); border-radius: var(--radius-lg);
        padding: 1.2rem 1.4rem;
        box-shadow: var(--shadow-sm);
        border: 1px solid var(--border);
        display: flex; align-items: center; gap: 1rem;
        transition: box-shadow .2s, transform .2s;
    }
    .stat-card:hover { box-shadow: var(--shadow-md); transform: translateY(-2px); }
    .stat-icon {
        width: 44px; height: 44px; border-radius: 12px;
        display: flex; align-items: center; justify-content: center;
        font-size: 1.3rem; flex-shrink: 0;
    }
    .stat-value { font-size: 1.5rem; font-weight: 800; color: var(--text-1); line-height: 1; }
    .stat-label { font-size: 0.78rem; color: var(--text-2); margin-top: 3px; }

    /* ── Feature cards (quick access grid) ── */
    .feat-card {
        background: var(--surface); border-radius: var(--radius-lg);
        padding: 1.3rem 1.1rem 1.1rem;
        border: 1.5px solid var(--border);
        box-shadow: var(--shadow-sm);
        text-align: center; cursor: pointer;
        transition: all .2s ease;
        height: 100%;
    }
    .feat-card:hover {
        border-color: var(--primary);
        box-shadow: 0 0 0 3px rgba(37,99,235,0.08), var(--shadow-md);
        transform: translateY(-3px);
    }
    .feat-icon {
        font-size: 2rem; margin-bottom: 0.55rem;
        display: block;
    }
    .feat-title {
        font-size: 0.88rem; font-weight: 700; color: var(--text-1);
        line-height: 1.3; margin-bottom: 0.3rem;
    }
    .feat-desc {
        font-size: 0.73rem; color: var(--text-3); line-height: 1.4;
    }

    /* ── Category row items ── */
    .cat-row {
        display: flex; align-items: center; padding: 0.7rem 0.9rem;
        border-radius: var(--radius-md); border: 1px solid var(--border);
        background: var(--surface); margin-bottom: 0.5rem;
        transition: background .15s, border-color .15s;
    }
    .cat-row:hover { background: var(--primary-light); border-color: #bfdbfe; }
    .cat-row-icon { font-size: 1.1rem; margin-right: 0.65rem; flex-shrink: 0; }
    .cat-row-title { font-size: 0.88rem; font-weight: 600; color: var(--text-1); }
    .cat-row-desc  { font-size: 0.77rem; color: var(--text-2); margin-left: 0.5rem; }

    /* ── Tips cards ── */
    .tip-card-pro {
        background: var(--surface);
        border-radius: var(--radius-md);
        padding: 1rem 1.1rem;
        border: 1px solid var(--border);
        border-left: 3px solid var(--primary);
        box-shadow: var(--shadow-sm);
        font-size: 0.84rem; color: var(--text-2); line-height: 1.6;
    }
    .tip-card-pro strong { color: var(--text-1); }

    /* ── Section divider label ── */
    .section-label {
        font-size: 0.7rem; font-weight: 700; letter-spacing: 0.1em;
        text-transform: uppercase; color: var(--text-3);
        margin: 1.6rem 0 0.8rem; display: flex; align-items: center; gap: 8px;
    }
    .section-label::after {
        content: ''; flex: 1; height: 1px; background: var(--border);
    }

    /* ── main-form (existing pages) ── */
    .main-form {
        background: var(--surface); border-radius: var(--radius-lg); padding: 2rem;
        box-shadow: var(--shadow-sm); border: 1px solid var(--border);
        margin-bottom: 1.5rem;
    }
    .form-title { color: var(--text-1); font-size: 1.1rem; font-weight: 700; margin-bottom: 1.25rem; }

    /* ── Inputs ── */
    .stTextInput > div > div > input,
    .stTextArea  > div > div > textarea {
        border-radius: 8px !important; border: 1.5px solid var(--border) !important;
        padding: 0.6rem 0.85rem !important; font-size: 0.9rem !important;
        background: var(--surface-2) !important;
        transition: border-color .15s, box-shadow .15s;
    }
    .stTextInput > div > div > input:focus,
    .stTextArea  > div > div > textarea:focus {
        border-color: var(--primary) !important;
        box-shadow: 0 0 0 3px rgba(37,99,235,0.1) !important;
        background: var(--surface) !important;
    }

    /* ── Buttons ── */
    .stButton > button {
        border-radius: 8px !important; font-weight: 600 !important;
        padding: 0.55rem 1.25rem !important; font-size: 0.88rem !important;
        transition: all .2s !important; border: 1.5px solid transparent !important;
    }
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, var(--primary) 0%, var(--accent) 100%) !important;
        color: white !important;
        box-shadow: 0 2px 8px rgba(37,99,235,0.3) !important;
    }
    .stButton > button[kind="primary"]:hover {
        box-shadow: 0 4px 16px rgba(37,99,235,0.4) !important;
        transform: translateY(-1px) !important;
    }
    .stButton > button[kind="secondary"] {
        border-color: var(--border) !important; color: var(--text-1) !important;
        background: var(--surface) !important;
    }
    .stButton > button[kind="secondary"]:hover {
        border-color: var(--primary) !important; color: var(--primary) !important;
        background: var(--primary-light) !important;
    }

    /* ── Tip card (pages) ── */
    .tip-card {
        background: #fffbeb; border-radius: 8px; padding: 0.75rem 1rem;
        border-left: 3px solid #f59e0b; margin-bottom: 1rem; font-size: 0.85rem;
    }

    /* ── Success / result ── */
    .success-box {
        background: linear-gradient(135deg, #dcfce7 0%, #d1fae5 100%);
        border-radius: 12px; padding: 1.1rem; text-align: center;
        border: 1.5px solid #6ee7b7; margin: 1rem 0;
    }
    .success-title { font-size: 1rem; font-weight: 700; color: #065f46; }
    .result-area {
        background: var(--surface-2); border-radius: var(--radius-md); padding: 1.25rem;
        border: 1px solid var(--border); margin-top: 1rem;
    }
    .subject-box {
        background: var(--primary-light); border-radius: var(--radius-md);
        padding: 1rem 1.25rem; border: 1.5px solid #bfdbfe; margin-bottom: 0.75rem;
    }
    .subject-label {
        font-size: 0.72rem; font-weight: 700; color: var(--primary);
        text-transform: uppercase; letter-spacing: 0.06em;
    }
    .subject-text { font-size: 1rem; font-weight: 600; color: var(--text-1); margin-top: 0.25rem; }
    .stream-container {
        background: var(--surface-2); border-radius: var(--radius-md); padding: 1.25rem;
        border: 1.5px dashed #bfdbfe; margin: 0.75rem 0;
        min-height: 60px; line-height: 1.7; white-space: pre-wrap;
        font-size: 0.95rem; color: var(--text-1);
    }

    /* ── Login ── */
    .login-box {
        max-width: 420px; margin: 5rem auto; background: var(--surface);
        border-radius: 20px; padding: 2.5rem;
        box-shadow: var(--shadow-lg); border: 1px solid var(--border); text-align: center;
    }
    .login-title { font-size: 1.45rem; font-weight: 800; color: var(--text-1); margin-bottom: 0.4rem; }
    .login-sub   { color: var(--text-2); font-size: 0.9rem; margin-bottom: 1.5rem; }

    /* ── Sidebar ── */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #f8fafc 0%, #f1f5f9 100%) !important;
        border-right: 1px solid var(--border) !important;
    }
    [data-testid="stSidebar"] > div:first-child {
        padding-top: 0.5rem !important;
    }
    [data-testid="stSidebarNavItems"] {
        padding-top: 0.3rem !important;
    }

    /* ── Navigation link items (专业化) ── */
    [data-testid="stSidebarNavItems"] li {
        margin-bottom: 1px !important;
    }
    [data-testid="stSidebarNavItems"] a {
        padding: 0.5rem 0.75rem !important;
        border-radius: 8px !important;
        font-size: 0.82rem !important;
        font-weight: 500 !important;
        color: var(--text-2) !important;
        transition: all 0.15s ease !important;
        border-left: 3px solid transparent !important;
        margin: 0 0.4rem !important;
        display: flex !important;
        align-items: center !important;
    }
    [data-testid="stSidebarNavItems"] a:hover {
        background: rgba(37,99,235,0.06) !important;
        color: var(--text-1) !important;
        border-left-color: rgba(37,99,235,0.3) !important;
    }
    [data-testid="stSidebarNavItems"] a span {
        font-size: 0.82rem !important;
    }
    /* Active page: bold left indicator */
    [data-testid="stSidebarNavItems"] [aria-current="page"],
    [data-testid="stSidebarNavItems"] [aria-current="page"] span {
        color: var(--primary) !important;
        font-weight: 700 !important;
        background: linear-gradient(135deg, rgba(37,99,235,0.08) 0%, rgba(124,58,237,0.05) 100%) !important;
        border-left-color: var(--primary) !important;
        border-radius: 8px !important;
    }
    /* First nav item (app.py = 首页) — 隐藏"app"文字，用"🏠 首页"替代 */
    [data-testid="stSidebarNavItems"] li:first-child a span {
        font-size: 0 !important;
        line-height: 0 !important;
    }
    [data-testid="stSidebarNavItems"] li:first-child a span::after {
        content: "🏠 工作台";
        font-size: 0.82rem !important;
        line-height: normal !important;
        font-weight: 600 !important;
    }
    /* Navigation section separator — more subtle */
    [data-testid="stSidebarNavSeparator"] {
        margin: 0.6rem 0.75rem !important;
        border-color: rgba(226,232,240,0.6) !important;
    }

    /* ── Sidebar collapse/expand toggle button (更醒目) ── */
    [data-testid="collapsedControl"] {
        background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%) !important;
        border-radius: 0 12px 12px 0 !important;
        padding: 12px 10px 12px 8px !important;
        box-shadow: 0 4px 16px rgba(99,102,241,0.35), 0 2px 6px rgba(0,0,0,0.1) !important;
        transition: all 0.3s ease !important;
        border: none !important;
        top: 1rem !important;
    }
    [data-testid="collapsedControl"]:hover {
        background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%) !important;
        box-shadow: 0 6px 24px rgba(99,102,241,0.5), 0 3px 8px rgba(0,0,0,0.12) !important;
        transform: translateX(3px) !important;
    }
    [data-testid="collapsedControl"] svg {
        color: white !important;
        width: 20px !important;
        height: 20px !important;
    }
    /* Sidebar内的 collapse 按钮(收起按钮) */
    [data-testid="stSidebar"] button[kind="header"] {
        background: rgba(79, 70, 229, 0.08) !important;
        border-radius: 8px !important;
        border: 1.5px solid rgba(79, 70, 229, 0.2) !important;
        transition: all 0.2s ease !important;
    }
    [data-testid="stSidebar"] button[kind="header"]:hover {
        background: rgba(79, 70, 229, 0.15) !important;
        border-color: var(--primary) !important;
        transform: scale(1.05) !important;
    }
    [data-testid="stSidebar"] button[kind="header"] svg {
        color: var(--primary) !important;
    }
    [data-testid="stSidebar"] [aria-current="page"],
    [data-testid="stSidebar"] [aria-current="page"] span {
        color: var(--primary) !important; font-weight: 700 !important;
        background: rgba(37,99,235,0.08) !important; border-radius: 6px;
    }
    [data-testid="stSidebar"] .stProgress > div > div { background-color: #e2e8f0 !important; }
    [data-testid="stSidebar"] .stProgress > div > div > div { background-color: var(--primary) !important; }
    [data-testid="stSidebar"] hr { border-color: var(--border) !important; }
    [data-testid="stSidebar"] .stMarkdown a { color: var(--primary) !important; }

    /* ── Tabs ── */
    .stTabs [data-baseweb="tab-list"] {
        gap: 4px; background: var(--surface-2) !important;
        border-radius: 10px; padding: 4px !important;
        border: 1px solid var(--border);
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 7px !important; font-weight: 600 !important;
        font-size: 0.84rem !important; padding: 0.4rem 1rem !important;
        color: var(--text-2) !important;
    }
    .stTabs [aria-selected="true"] {
        background: var(--surface) !important; color: var(--primary) !important;
        box-shadow: var(--shadow-sm) !important;
    }

    /* ── Metrics ── */
    [data-testid="metric-container"] {
        background: var(--surface); border-radius: var(--radius-lg);
        border: 1px solid var(--border); padding: 1rem 1.2rem !important;
        box-shadow: var(--shadow-sm);
    }
    [data-testid="stMetricValue"] { font-size: 1.8rem !important; font-weight: 800 !important; color: var(--text-1) !important; }
    [data-testid="stMetricLabel"] { font-size: 0.8rem !important; color: var(--text-2) !important; }

    /* ── Footer ── */
    .footer { text-align: center; padding: 1.8rem; color: var(--text-3); font-size: 0.78rem; }
    .footer a { color: var(--primary) !important; text-decoration: none; }

    /* ── Hide Streamlit default chrome for cleaner look ── */
    #MainMenu { visibility: hidden; }
    header[data-testid="stHeader"] {
        background: transparent !important;
        backdrop-filter: none !important;
    }
    footer { visibility: hidden; }
    [data-testid="stDecoration"] { display: none !important; }

    /* ── Misc ── */
    .price-tag {
        background: rgba(255,255,255,0.18); padding: 0.4rem 1rem;
        border-radius: 20px; display: inline-flex; align-items: center;
        gap: 0.5rem; margin-top: 0.75rem; font-size: 0.88rem;
        border: 1px solid rgba(255,255,255,0.25);
    }

    /* ── Animations ── */
    @keyframes fadeUp {
        from { opacity: 0; transform: translateY(12px); }
        to   { opacity: 1; transform: translateY(0); }
    }
    .hero-section { animation: fadeUp .5s ease both; }
    .feat-card    { animation: fadeUp .4s ease both; }

    @media (max-width: 768px) {
        .block-container { padding: 0.75rem !important; }
        .hero-title { font-size: 1.6rem !important; }
        .hero-stats { flex-wrap: wrap; gap: 1rem; }
    }
</style>
"""
