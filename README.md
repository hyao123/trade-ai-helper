# AI-Trade Pro · 外贸 AI 助手

一站式外贸业务 AI 工具箱：开发信、询盘回复、报价单、产品文案、CRM、跟进、支付升级等。

## 🌐 Public URL

正式公网访问地址：

```text
https://trade-ai-helper.streamlit.app
```

## 🚀 本地启动

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置密钥

本地开发可创建 `.env` 或使用 Streamlit Secrets：

```toml
NVIDIA_API_KEY = "nvapi-xxx"
NVIDIA_MODEL = "meta/llama-3.3-70b-instruct"  # 可选，默认值
APP_PASSWORD = "your-admin-password"           # 可选：admin fallback
```

### 3. 启动应用

```bash
streamlit run app.py
```

浏览器访问：

```text
http://localhost:8501
```

---

## ☁️ 部署：Streamlit Cloud

本项目直接使用 **Streamlit Cloud** 作为主部署平台。

> Streamlit 使用 WebSocket 长连接，不建议部署在 Vercel / Netlify 等 Serverless 平台。仓库不再维护 Vercel 运行配置。

### Streamlit Cloud 配置

| 配置项 | 值 |
|---|---|
| Repository | `hyao123/trade-ai-helper` |
| Branch | `master` |
| Main file path | `app.py` |
| Public URL | `https://trade-ai-helper.streamlit.app` |

### Streamlit Cloud Secrets

在 Streamlit Cloud → App → Settings → Secrets 中配置：

```toml
NVIDIA_API_KEY = "nvapi-xxx"
NVIDIA_MODEL = "meta/llama-3.3-70b-instruct"

# 生产建议开启登录；APP_PASSWORD 仅作为 admin fallback。
APP_PASSWORD = "your-admin-password"

# 单实例 demo 可使用 SQLite 持久化。
SQLITE_DB_PATH = "trade_ai_helper.sqlite3"

# 可选：多模型 Provider
OPENAI_API_KEY = "sk-xxx"
DEEPSEEK_API_KEY = "sk-xxx"

# 可选：Stripe 支付
STRIPE_SECRET_KEY = "sk_live_xxx"
STRIPE_PRICE_ID_PRO = "price_xxx"
STRIPE_PRICE_ID_ENTERPRISE = "price_xxx"
APP_BASE_URL = "https://trade-ai-helper.streamlit.app"
```

### 部署检查清单

部署后验证：

1. 打开 `https://trade-ai-helper.streamlit.app`。
2. 注册新用户后自动进入首页。
3. AI 生成功能可调用配置的 Provider。
4. 历史记录在同一账号下可持久化。
5. 页面导航、PDF/CSV 下载、Stripe 升级流程正常。

---

## 📁 目录结构

```text
trade-ai-helper/
├── app.py                          # Streamlit 首页入口
├── pages/                          # 功能页面
├── config/                         # i18n 与 Prompt 模板
├── utils/                          # AI、存储、认证、支付、CRM 等业务模块
├── tests/                          # pytest 测试
├── .streamlit/config.toml          # Streamlit Cloud/runtime 配置
├── requirements.txt                # Python 依赖
└── README.md
```

## 🔒 安全说明

- 不要把真实 API Key、SMTP 密码、Stripe 密钥提交到 Git。
- 生产环境建议设置 `APP_PASSWORD` 或启用用户注册登录。
- 单实例 demo 可用 SQLite；多实例/商业化部署建议使用 PostgreSQL。
- Stripe 支付生产化建议改为 webhook 驱动升级。
