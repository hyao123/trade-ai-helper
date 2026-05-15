# 💼 外贸AI助手 — TradeAI Pro

> **AI 赋能外贸 · 让每一位外贸人都拥有一个 24 小时在线的英文业务员**

[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/streamlit-1.45-red.svg)](https://streamlit.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![CI](https://github.com/hyao123/trade-ai-helper/actions/workflows/ci.yml/badge.svg)](https://github.com/hyao123/trade-ai-helper/actions)

---

## ✨ 功能一览（23 个页面）

### 📧 邮件 & 沟通自动化

| 页面 | 功能 | 亮点 |
|------|------|------|
| 📧 开发信生成 | AI 撰写高转化英文开发信 | Subject Line 自动生成 · 3种风格 ⚡ 流式 |
| 📩 询盘回复 | 粘贴询盘，AI 逐条回答 | 报价区间建议 · 不漏问题 ⚡ 流式 |
| 📬 跟进邮件 | 按阶段生成跟进邮件 | 5阶段覆盖完整销售周期 ⚡ 流式 |
| 📨 批量开发信 | CSV 上传，批量个性化生成 | 支持 Excel BOM · 批量下载 |
| 🗣️ 谈判话术 | 场景化谈判应对脚本 | 6种场景 · 开场/还价/备案/话术 |
| 🎄 节日问候 | 文化适配的节日祝福邮件 | 8个节日 · 3种关系级别 |
| 🌐 邮件润色 | 翻译 + 润色 + 双语对比 | 多语种互译 · 商务级润色 |
| 😟 投诉处理 | 专业客诉回复邮件生成 | 5类投诉 · 3级严重度 · 4种解决方案 |

### 📄 文案 & 内容创作

| 页面 | 功能 | 亮点 |
|------|------|------|
| 📑 多语种产品介绍 | 一次输入，5语言输出 | 英/西/法/德/日 ⚡ 流式 |
| 🛒 产品上架 | Amazon/Shopify Listing 文案 | SEO优化 · 标题+卖点+描述+搜索词 ⚡ 流式 |
| 💬 社媒文案 | LinkedIn/Instagram/Facebook | 含 hashtag · 多平台同时生成 ⚡ 流式 |

### 📊 业务工具 & 分析

| 页面 | 功能 | 亮点 |
|------|------|------|
| 📄 报价单 PDF | 多SKU专业PDF报价单 | Logo上传 · 自动合计 · 一键下载 |
| 📇 客户管理 | 轻量级外贸 CRM | 阶段追踪 · 一键触发邮件 |
| 📅 跟进日历 | 邮件跟进自动化提醒 | 3天/1周/2周/1月 · 不漏商机 |
| 📋 历史记录 | AI 生成结果归档 | 搜索/筛选 · 复用 · 最多50条 |
| 💰 智能报价 | AI 定价策略建议 | 市场分析 · 成本拆解 · 阶梯报价 ⚡ 流式 |
| 📦 装箱计算器 | 集装箱装载优化 | 20GP/40GP/40HQ · 体积+重量利用率 |
| 📋 装箱发票 | Packing List + 商业发票 PDF | 双文档一键生成 · 多产品 |
| 📊 客户分析 | 客户数据可视化仪表盘 | 转化漏斗 · 地区分布 · 月度趋势 |
| 🧪 A/B 测试 | 邮件变体科学优化 | AI生成变体 · 模拟数据 · 统计置信度 |

### ⚙️ 账户 & 平台

| 页面 | 功能 | 亮点 |
|------|------|------|
| 👤 账户管理 | 个人资料 · 用量 · 密码修改 | 套餐对比 · Stripe 支付验证 |
| 📈 数据导出 | 全量数据备份/恢复 | JSON + CSV · Pro 功能 |
| 💳 套餐升级 | Free / Pro / Enterprise 对比 | Stripe 支付 · 即时生效 |

---

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置 API Key

```bash
cp .env.example .env
# 编辑 .env，填入你的 NVIDIA NIM API Key
# 获取地址：https://build.nvidia.com → 选任意模型 → Get API Key
```

`.env` 示例：

```env
NVIDIA_API_KEY=nvapi-xxxxxxxxxxxxxxxxxxxxxxxx
APP_PASSWORD=your_password          # 可选，留空则不启用鉴权
NVIDIA_MODEL=meta/llama-3.3-70b-instruct  # 可选，默认值
```

### 3. 启动应用

```bash
streamlit run app.py
```

浏览器访问 `http://localhost:8501`

---

## ☁️ 部署

> ⚠️ **Streamlit 使用 WebSocket 长连接，不支持 Vercel / Netlify 等 Serverless 平台。**

### 推荐方案

| 平台 | 说明 | 费用 |
|------|------|------|
| **Streamlit Cloud** | 官方托管，推送 GitHub 即部署 | 免费 |
| **Railway** | 支持长连接，已配置 Procfile | 免费额度 |
| **Render** | 支持 Web Service | 免费额度 |

### Streamlit Cloud 部署步骤

1. Fork 此仓库到你的 GitHub
2. 访问 [share.streamlit.io](https://share.streamlit.io) → New app
3. 选择仓库，主文件填 `app.py`
4. 在 **Secrets** 中填入：
   ```toml
   NVIDIA_API_KEY = "nvapi-xxx"
   APP_PASSWORD = "your_password"
   ```
5. 点击 Deploy，等待 1-2 分钟即可访问

### 可选：Stripe 支付配置

```toml
# Streamlit Cloud Secrets 中追加：
STRIPE_SECRET_KEY = "sk_live_xxx"
STRIPE_PRICE_ID_PRO = "price_xxx"
STRIPE_PRICE_ID_ENTERPRISE = "price_xxx"
APP_BASE_URL = "https://your-app.streamlit.app"
```

---

## 📁 目录结构

```
trade-ai-helper/
├── app.py                          # 首页（功能导航，3行卡片）
├── pages/                          # 23 个功能页面
│   ├── 1_📧_开发信.py
│   ├── 2_📩_询盘回复.py
│   ├── 3_📄_报价单.py              # 多SKU PDF
│   ├── 4_📑_产品介绍.py            # 多语种
│   ├── 5_📬_跟进邮件.py
│   ├── 6_🛒_产品上架.py            # Amazon/Shopify
│   ├── 7_📇_客户管理.py            # CRM
│   ├── 8_💬_社媒文案.py
│   ├── 9_📋_历史记录.py
│   ├── 10_📅_跟进日历.py
│   ├── 11_👤_账户管理.py
│   ├── 12_📨_批量开发信.py
│   ├── 13_🗣️_谈判话术.py
│   ├── 14_🎄_节日问候.py
│   ├── 15_🌐_邮件润色.py
│   ├── 16_😟_投诉处理.py
│   ├── 17_💰_智能报价.py           # Tier 2
│   ├── 18_📦_装箱计算器.py         # Tier 2
│   ├── 19_📋_装箱发票.py           # Tier 2
│   ├── 20_📊_客户分析.py           # Tier 2
│   ├── 21_🧪_AB测试.py            # Tier 2
│   ├── 22_📈_数据导出.py           # Pro 功能
│   └── 23_💳_套餐升级.py           # 支付页
├── config/
│   ├── i18n.py                     # 中英双语支持
│   └── prompts.py                  # 所有 AI Prompt 模板（统一管理）
├── utils/
│   ├── ai_client.py                # NVIDIA NIM API（流式 + 非流式）
│   ├── analytics.py                # 客户分析引擎
│   ├── ab_testing.py               # A/B 测试框架
│   ├── container_calc.py           # 集装箱装载计算
│   ├── customers.py                # CRM 客户数据
│   ├── history.py                  # 历史记录管理
│   ├── packing_invoice_pdf.py      # 装箱单/商业发票 PDF
│   ├── payment.py                  # Stripe 支付集成
│   ├── pdf_gen.py                  # 报价单 PDF 生成
│   ├── pricing.py                  # 套餐管理 + 用量追踪
│   ├── sanitize.py                 # Prompt 注入防护
│   ├── secrets.py                  # 环境变量管理
│   ├── storage.py                  # JSON 持久化（原子写入）
│   ├── templates.py                # 邮件模板管理
│   ├── ui_helpers.py               # 共享 UI 组件
│   ├── user_auth.py                # 用户认证（PBKDF2）
│   └── workflow.py                 # 跟进工作流
├── tests/                          # 231+ 单元测试
│   ├── test_tier2.py               # Tier 2 功能测试（36个）
│   ├── test_new_prompts.py         # Prompt 测试（含CSV）
│   ├── test_payment.py             # Stripe 支付测试
│   └── ...
├── data/                           # 数据持久化目录（per-user 隔离）
├── fonts/                          # 可选：NotoSansSC-Regular.ttf（中文 PDF 支持）
├── .env.example
├── .streamlit/config.toml          # 主题配置
├── Procfile                        # Railway/Render 部署
├── requirements.txt
└── ruff.toml                       # Lint 配置
```

---

## ⚙️ 环境变量

| 变量 | 必填 | 说明 |
|------|------|------|
| `NVIDIA_API_KEY` | ✅ | NVIDIA NIM API Key |
| `APP_PASSWORD` | 可选 | 访问密码（留空不启用鉴权） |
| `NVIDIA_MODEL` | 可选 | 模型名，默认 `meta/llama-3.3-70b-instruct` |
| `RATE_LIMIT_MAX_CALLS` | 可选 | 每窗口最大调用次数，默认 `20` |
| `RATE_LIMIT_WINDOW` | 可选 | 限速窗口（秒），默认 `3600` |
| `STRIPE_SECRET_KEY` | 可选 | Stripe 密钥（启用支付功能） |
| `STRIPE_PRICE_ID_PRO` | 可选 | Pro 套餐 Stripe Price ID |
| `STRIPE_PRICE_ID_ENTERPRISE` | 可选 | Enterprise 套餐 Stripe Price ID |
| `APP_BASE_URL` | 可选 | 应用 URL（用于 Stripe 回调） |
| `SMTP_HOST` | 可选 | SMTP 服务器（启用邮件验证） |
| `SMTP_PORT` | 可选 | SMTP 端口 |
| `SMTP_USERNAME` | 可选 | SMTP 用户名 |
| `SMTP_PASSWORD` | 可选 | SMTP 密码 |

---

## 💎 定价方案

| | Free | Pro | Enterprise |
|--|------|-----|-----------|
| **价格** | 免费 | ¥99/月 ($29) | ¥299/月 ($99) |
| **AI 生成次数** | 20 次/天 | 100 次/天 | 无限 |
| 所有核心功能 | ✅ | ✅ | ✅ |
| **Logo 上传**（PDF） | ❌ | ✅ | ✅ |
| **数据导出/导入** | ❌ | ✅ | ✅ |
| **优先技术支持** | ❌ | ✅ | ✅ |
| **企业级 SLA** | ❌ | ❌ | ✅ |

---

## 🛡️ 安全说明

- **认证**：PBKDF2-HMAC-SHA256（10万次迭代）密码哈希
- **Prompt 安全**：25+ 注入模式过滤，sanitize 所有用户输入
- **数据隔离**：per-user 目录隔离，用户间完全独立
- **支付安全**：Stripe Checkout Sessions + 消费会话防重放
- **速率限制**：双层限速（Tier 日限 + 全局滑动窗口）

---

## 🧪 测试

```bash
# 运行所有测试
pytest tests/ -v

# 仅运行 Tier 2 测试
pytest tests/test_tier2.py -v

# 代码规范检查
ruff check . --select E,F,I --ignore E501
```

测试覆盖：231+ 单元测试，涵盖：
- 所有 AI Prompt 构建函数
- 集装箱计算器（9个用例）
- 客户分析引擎（9个用例）
- A/B 测试框架（11个用例）
- 支付集成（8个用例）
- 用户认证（20+ 用例）
- 历史/模板/工作流管理

---

## 📄 License

MIT © 2026 TradeAI Pro
