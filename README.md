# 外贸AI助手

外贸从业者的AI工具箱 - 开发信、询盘回复、报价单、产品介绍

## 功能

- 📧 开发信生成
- 📩 询盘回复
- 📄 报价单生成
- 📑 产品介绍

## 快速开始

### 1. 安装依赖

```bash
cd trade-ai-helper
pip install -r requirements.txt
```

### 2. 设置API Key

```bash
# 方式1: 环境变量
export KIMI_API_KEY="your-api-key"

# 方式2: 创建 .env 文件
echo "KIMI_API_KEY=your-api-key" > .env
```

### 3. 运行

```bash
streamlit run app.py
```

## 部署

### Vercel部署

```bash
# 安装vercel
npm i -g vercel

# 部署
vercel deploy
```

### Streamlit Cloud

1. 推送到GitHub
2. 访问 [share.streamlit.io](https://share.streamlit.io)
3. 绑定仓库即可

## 价格

| 方案 | 价格 |
|------|------|
| 免费 | 3次/天 |
| 年卡 | ¥99/年 |

## 目录结构

```
trade-ai-helper/
├── app.py              # 主应用
├── requirements.txt   # 依赖
├── utils/
│   ├── __init__.py
│   ├── ai_client.py   # AI调用
│   └── pdf_gen.py     # PDF生成
└── README.md
```