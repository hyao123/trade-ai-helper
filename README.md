# 💼 外贸AI助手 — TradeAI Pro

> AI 赋能外贸 · 开发信 · 询盘回复 · 报价单 · 产品介绍 · 跟进邮件

---

## ✨ 功能一览

| 页面 | 功能 | 亮点 |
|------|------|------|
| 📧 开发信生成 | AI 撰写英文开发信 | 自动生成邮件主题行（Subject Line）⚡ 流式输出 |
| 📩 询盘回复 | 粘贴询盘，AI 生成回复草稿 | 逐条回答问题 + 报价区间建议 ⚡ 流式输出 |
| 📄 报价单 PDF | 多产品 SKU → 专业 PDF | 支持多行产品、自动合计、精美表格 |
| 📑 产品介绍 | 一键生成多语种文案 | 英/西/法/德/日 5 种语言 ⚡ 流式输出 |
| 📬 跟进邮件 | 按跟进阶段生成邮件 | 5 个阶段：已报价/已发样/已谈判/已下单/未回复 ⚡ 流式输出 |

---

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置 API Key

```bash
# 复制示例文件
cp .env.example .env

# 编辑 .env，填入你的 Kimi API Key
# 获取地址：https://platform.moonshot.cn/
KIMI_API_KEY=your_api_key_here

# 可选：设置访问密码（部署时防止他人滥用 API）
APP_PASSWORD=your_password
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
| **Render** | 支持 Web Service，已配置 Procfile | 免费额度 |

### Streamlit Cloud 部署步骤

1. 推送代码到 GitHub
2. 访问 [share.streamlit.io](https://share.streamlit.io)
3. 点击 "New app" → 选择仓库 → 主文件选 `app.py`
4. 在 "Secrets" 中填入 `KIMI_API_KEY` 和 `APP_PASSWORD`（可选）

---

## 📁 目录结构

```
trade-ai-helper/
├── app.py                    # 首页（功能导航）
├── pages/
│   ├── 1_📧_开发信.py         # 开发信生成
│   ├── 2_📩_询盘回复.py        # 询盘回复
│   ├── 3_📄_报价单.py          # 多产品 PDF 报价单
│   ├── 4_📑_产品介绍.py        # 多语种产品介绍
│   └── 5_📬_跟进邮件.py        # 跟进邮件生成
├── config/
│   ├── __init__.py
│   └── prompts.py            # 所有 AI Prompt 模板（统一管理）
├── utils/
│   ├── ai_client.py          # Kimi API 调用（流式 + 非流式）
│   ├── pdf_gen.py            # PDF 报价单生成（多 SKU）
│   └── ui_helpers.py         # 共享 UI 组件
├── fonts/                    # 可选：放置 NotoSansSC-Regular.ttf 支持完整中文
├── .env.example              # 环境变量示例
├── .streamlit/config.toml    # Streamlit 主题配置
├── Procfile                  # Railway / Render 部署配置
└── requirements.txt
```

---

## ⚙️ 环境变量

| 变量 | 必填 | 说明 |
|------|------|------|
| `KIMI_API_KEY` | ✅ | Kimi (Moonshot) API Key |
| `APP_PASSWORD` | 可选 | 访问密码，留空则不启用鉴权 |
| `KIMI_MODEL` | 可选 | 模型名，默认 `moonshot-v1-8k` |
| `RATE_LIMIT_MAX_CALLS` | 可选 | 每窗口最大调用次数，默认 `20` |
| `RATE_LIMIT_WINDOW` | 可选 | 限速窗口（秒），默认 `3600`（1小时）|

---

## 🛡️ 安全说明

- 设置 `APP_PASSWORD` 防止他人访问消耗 API 额度
- Rate Limiting 基于内存，单进程有效（多进程/重启后重置）
- 生产环境建议配合反向代理（Nginx）或平台级鉴权

---

## 📄 License

MIT
