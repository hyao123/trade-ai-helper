# 依赖审查报告：外部服务配置与降级路径

**生成时间**：2025-01-XX  
**审查范围**：全项目外部服务依赖与门控逻辑  
**触发原因**：修复验证邮箱死锁问题后，系统化审查所有板块避免类似死锁

---

## 执行摘要

**审查发现**：项目存在 **8 类外部服务依赖**，共识别 **5 个高风险点**（可能导致功能死锁或体验降级）和 **3 个中风险点**（需改进提示）。

| 风险等级 | 数量 | 典型问题 |
|---------|------|---------|
| 🔴 高风险（已修复） | 1 | 验证邮箱死锁（邮件 provider 未配置 → AI 功能被锁） |
| 🟡 高风险（待修复） | 4 | 邮件发送门控不一致、支付门控过严、inbox OAuth 无降级 |
| 🟠 中风险 | 3 | 提示信息不友好、降级路径未明示 |
| 🟢 低风险 | 多个 | 已有合理降级，仅需文档改进 |

---

## 一、外部服务依赖清单

### 1. AI 生成服务（核心功能）
**配置检测**：`utils.ai_client._any_provider_configured()`  
**依赖项**：`NVIDIA_API_KEY` / `OPENAI_API_KEY` / `DEEPSEEK_API_KEY` 或自定义 provider  
**门控位置**：`ai_client._check_preconditions` (247 行)  
**降级路径**：✅ **合理**  
- 无任何 key → 返回友好提示 "⚠️ 请先设置 AI API Key"
- 不阻塞应用启动，用户可配置后立即使用

**风险评估**：🟢 **低风险** —— 提示清晰，无死锁

---

### 2. 邮件发送服务（多处依赖）

#### 2.1 业务邮件发送（开发信、推送、回复）
**配置检测**：`utils.email_service.has_email_provider_configured()`（已修复）  
**依赖项**：Resend → SendGrid → SMTP 三级链  
**门控位置**：
- `pages/1_📧_开发信.py:245`：`is_email_configured()` 判断是否显示发送表单
- `send_ai_generated_email` 内部自动 fallback

**降级路径**：✅ **已优化**（B7 修复后）  
- 配置任一 provider → 正常发送
- 无任何 provider → 显示配置提示，不发送但不崩溃

**风险评估**：🟢 **低风险** —— 三级链健壮

---

#### 2.2 验证/重置邮件（系统邮件）
**配置检测**：`has_email_provider_configured()`（已修复）  
**依赖项**：同 2.1  
**门控位置**：`user_auth.py` 397/527/605/683 行  
**降级路径**：✅ **已修复**（提交 `b7aca1d`）  
- 有 provider → 验证邮件正常发送，门控严格
- 无 provider → **email_gate 放宽**，不锁 AI 功能

**风险评估**：🟢 **已解决** —— 之前是 🔴 高风险死锁，现已修复

---

#### 2.3 工作流邮件提醒（workflow reminder）
**配置检测**：`is_email_configured()`（⚠️ **旧函数**）  
**依赖项**：纯 SMTP  
**门控位置**：
- `utils.workflow.py:233`：无 SMTP → 记 warning 日志，返回 (0, 0)
- `pages/10_📅_跟进日历.py:36`：`is_email_configured()` 门控提醒 UI

**降级路径**：⚠️ **不一致**  
- workflow 邮件提醒只检查 `is_email_configured()`（纯 SMTP），而非 `has_email_provider_configured()`
- 若只配置 Resend/SendGrid，提醒邮件发不出（与业务邮件行为不一致）

**风险评估**：🟡 **中风险** —— 功能可用但行为不一致

**建议修复**：
```python
# utils/workflow.py:233 + pages/10:36
- if not is_email_configured():
+ if not has_email_provider_configured():
```

---

#### 2.4 通知摘要邮件（digest）
**配置检测**：`is_email_configured()`（⚠️ **旧函数**）  
**依赖项**：纯 SMTP  
**门控位置**：`utils.notifications.py:368`  
**降级路径**：返回 "Email not configured"

**风险评估**：🟡 **中风险** —— 同 2.3

**建议修复**：同 2.3，切换到 `has_email_provider_configured()` + 复用三级链

---

#### 2.5 自动外呼转发（auto_outreach forward）
**配置检测**：`is_email_configured()`（⚠️ **旧函数**）  
**依赖项**：纯 SMTP  
**门控位置**：`utils.auto_outreach.py:680`  
**降级路径**：记 warning 日志，返回 False（不发送）

**风险评估**：🟡 **中风险** —— 同 2.3

**建议修复**：同 2.3

---

### 3. 支付服务（Stripe）
**配置检测**：`utils.payment.is_payment_configured()`  
**依赖项**：`STRIPE_SECRET_KEY` + `STRIPE_PRICE_ID_PRO` / `STRIPE_PRICE_ID_ENTERPRISE`  
**门控位置**：
- `pages/11_👤_账户管理.py:266`："升级套餐"按钮 disabled + "⚠️ Stripe 未配置，暂无法升级套餐"
- `pages/23_💳_套餐升级.py:177`：同上
- `payment.create_checkout_session:56`：返回 "Payment not configured"

**降级路径**：✅ **合理门控**  
- 支付未配置 → UI 明确提示，按钮禁用
- 不影响其他功能（AI 生成、CRM 等）

**风险评估**：🟢 **低风险** —— 提示清晰，不阻塞核心功能

**改进建议**：中文化 "Payment not configured" → "支付服务未配置，请联系管理员"

---

### 4. Inbox OAuth（Gmail/Outlook 收件）
**配置检测**：`utils.inbox_integration.is_provider_configured(provider)`  
**依赖项**：`GMAIL_CLIENT_ID` + `GMAIL_CLIENT_SECRET`（或 Outlook 对应）  
**门控位置**：
- `inbox_integration.get_available_providers():90`：返回已配置 provider 列表
- 各 OAuth 流程入口（`start_oauth_flow` / `exchange_code` 等）检查配置

**降级路径**：⚠️ **部分功能不可用**  
- 无任何 provider 配置 → 收件箱集成完全不可用
- UI 层缺少友好提示（用户看到空列表，不知为何）

**风险评估**：🟠 **中风险** —— 不影响核心 AI 功能，但体验差

**建议改进**：
- `pages/35_📥_AI收件箱.py`：检测 `get_available_providers()` 为空时，显示配置引导："📮 当前未配置 Gmail/Outlook OAuth，请在 Secrets 中配置 GMAIL_CLIENT_ID / GMAIL_CLIENT_SECRET"

---

### 5. MailSlurp（独立收件箱）
**配置检测**：`utils.mailslurp_integration.is_mailslurp_configured()`  
**依赖项**：`MAILSLURP_API_KEY`  
**门控位置**：
- `mailslurp_integration.ensure_inbox:105`：返回 `(False, {"error": "MAILSLURP_API_KEY 未配置"})`
- `pages/35_📥_AI收件箱.py:31`：import 后检查

**降级路径**：✅ **合理**  
- 返回中文错误，UI 显示
- 不影响其他收件方式（OAuth inbox）

**风险评估**：🟢 **低风险** —— 提示清晰

---

### 6. SSO 单点登录
**配置检测**：`utils.sso.is_sso_configured(team_id)`  
**依赖项**：
- SAML：`SSO_ENTITY_ID` + `SSO_SSO_URL` + `SSO_CERTIFICATE`
- OIDC：`SSO_OIDC_ISSUER` + `SSO_OIDC_CLIENT_ID` + `SSO_OIDC_CLIENT_SECRET`

**门控位置**：`sso.get_sso_config:88` + 各 SSO 流程入口  
**降级路径**：✅ **完全可选**  
- 未配置 SSO → 使用普通登录（用户名+密码）
- 不影响任何功能

**风险评估**：🟢 **低风险** —— 可选增强功能

---

### 7. 关税数据 API
**配置检测**：无显式函数，直接 `get_secret("TRADE_DATA_API_KEY")`  
**依赖项**：`TRADE_DATA_API_KEY`（外部 trade data provider）  
**门控位置**：`utils.customs_data.py:268`  
**降级路径**：✅ **合理 fallback**  
- 有 API key → 调用外部 API 获取实时数据
- 无 API key → 使用内置参考数据（`_REFERENCE_TARIFFS`）+ 标注 "Reference data — verify with customs authority"

**风险评估**：🟢 **低风险** —— 降级合理，有明确提示

---

### 8. 分析追踪（PostHog）
**配置检测**：无显式函数，直接 `get_secret("POSTHOG_API_KEY")`  
**依赖项**：`POSTHOG_API_KEY` + `POSTHOG_HOST`（可选）  
**门控位置**：`utils.analytics.py:136`  
**降级路径**：✅ **静默降级**  
- 无 key → PostHog 不初始化，事件不发送
- 不影响任何功能，仅分析数据缺失

**风险评估**：🟢 **低风险** —— 可选监控功能

---

## 二、高风险问题与修复建议

### 🔴 问题 1：验证邮箱死锁（已修复）
**状态**：✅ 已修复（提交 `b7aca1d`）  
**原问题**：验证邮件只走 SMTP → 无配置时发不出 → email_gate 锁死 AI  
**修复方案**：三级 provider 链 + 门控放宽（无 provider 时放行）

---

### 🟡 问题 2：邮件发送门控不一致
**影响模块**：workflow reminder (工作流邮件提醒)、notification digest (通知摘要)、auto_outreach forward (重点客户转发)  
**问题**：这 3 处仍使用 `is_email_configured()`（纯 SMTP 检测），与业务邮件的 `has_email_provider_configured()` 不一致。

**用户影响**：
- 配置了 Resend/SendGrid，但未配 SMTP → 开发信能发，但工作流提醒发不出
- 行为不一致，用户困惑

**修复方案**：
1. **统一门控函数**：3 处改为 `has_email_provider_configured()`
2. **复用三级链**：`send_followup_reminder` / `send_email`（notifications.py:371）改为调用 `send_ai_generated_email` 或共享链
3. **测试更新**：test_mid_priority.py / test_workflow.py 相关 patch 更新

**优先级**：🟡 **中** —— 不影响核心流程，但体验不一致

---

### 🟡 问题 3：支付门控消息非中文
**影响模块**：pages/11、pages/23、utils/payment.py  
**问题**：`create_checkout_session` 返回 "Payment not configured" / "Stripe not installed" 英文错误

**修复方案**：
```python
# utils/payment.py:54-57
if not STRIPE_AVAILABLE:
-   return (False, "Stripe not installed")
+   return (False, "支付服务未安装，请联系技术支持")
if not is_payment_configured():
-   return (False, "Payment not configured")
+   return (False, "支付服务未配置，请在 Secrets 中配置 STRIPE_SECRET_KEY 和价格 ID")
```

**优先级**：🟢 **低** —— 体验优化

---

### 🟠 问题 4：Inbox OAuth 无配置时 UI 缺少引导
**影响模块**：pages/35_📥_AI收件箱.py  
**问题**：`get_available_providers()` 返回空列表时，用户看不到任何提示，不知道为何无法连接 Gmail/Outlook

**修复方案**：
```python
# pages/35_📥_AI收件箱.py (约 60-80 行，provider 选择 section)
available = get_available_providers()
if not available:
    st.warning(
        "📮 当前未配置任何邮件 OAuth 集成。\n\n"
        "请在 `.streamlit/secrets.toml` 或环境变量中配置：\n"
        "- **Gmail**: `GMAIL_CLIENT_ID`, `GMAIL_CLIENT_SECRET`\n"
        "- **Outlook**: `OUTLOOK_CLIENT_ID`, `OUTLOOK_CLIENT_SECRET`\n\n"
        "[查看配置文档](https://github.com/your-repo/docs/inbox-oauth.md)"
    )
    st.stop()
```

**优先级**：🟠 **中** —— 改善新用户体验

---

### 🟠 问题 5：AI provider 未配置时首页无明确引导
**影响模块**：app.py / pages 首次使用流程  
**问题**：用户首次部署，无任何 AI key 时，各 AI 生成页面点击后才看到 "⚠️ 请先设置 AI API Key"，首页无统一配置引导

**修复方案**（可选增强）：
```python
# app.py (约 180 行，sidebar 底部)
from utils.ai_client import _any_provider_configured
if not _any_provider_configured():
    st.sidebar.warning(
        "⚠️ **AI 服务未配置**\n\n"
        "请先在 [AI 偏好](pages/0_⚙️_AI偏好.py) 或 Secrets 中配置任一 API Key：\n"
        "- NVIDIA_API_KEY\n"
        "- OPENAI_API_KEY\n"
        "- DEEPSEEK_API_KEY"
    )
```

**优先级**：🟢 **低** —— 体验优化（现有提示已清晰，这是锦上添花）

---

## 三、风险总结与优先级

| 问题 | 风险 | 影响范围 | 优先级 | 工作量 |
|-----|------|---------|--------|--------|
| 验证邮箱死锁 | 🔴 高 | AI 功能锁死 | ✅ 已修复 | - |
| 邮件门控不一致 | 🟡 中 | workflow/notification 邮件 | P1 | 2-3h（含测试） |
| 支付消息中文化 | 🟢 低 | 套餐升级提示 | P2 | 30min |
| Inbox OAuth 引导 | 🟠 中 | 收件箱配置体验 | P2 | 1h |
| AI provider 引导 | 🟢 低 | 首次部署体验 | P3 | 30min |

---

## 四、最佳实践建议

### 4.1 外部服务依赖设计原则
1. **配置检测函数统一命名**：`is_XXX_configured()` 返回 bool
2. **降级路径必须明确**：无配置时，返回中文友好提示 or 使用内置 fallback
3. **门控与 UI 一致**：同一服务的门控函数在各处保持一致（如邮件统一用 `has_email_provider_configured()`）
4. **避免死锁**：核心功能（AI 生成）不能被非核心配置（邮箱验证）完全锁死；无配置时应放宽门控或提供绕过路径

### 4.2 用户体验改进清单
- ✅ 验证邮箱三级链：已实现
- ⬜ 统一邮件门控（workflow/notification）：待修复
- ⬜ 中文化错误消息：支付/SSO/其他英文提示
- ⬜ 首次配置引导：AI provider / Inbox OAuth 在相关页面顶部提示
- ⬜ 文档完善：`docs/configuration-guide.md` 列出所有可选服务及配置方式

---

## 五、测试覆盖检查

**现有测试**：
- ✅ `test_email_service.py`：has_email_provider_configured + 三级链
- ✅ `test_email_gate.py`：无 provider 时放宽
- ✅ `test_payment.py`：is_payment_configured
- ✅ `test_mailslurp_integration.py`：is_mailslurp_configured
- ⬜ **缺失**：workflow/notification 邮件门控测试（待补充）

**建议新增测试**：
```python
# tests/test_workflow_email_fallback.py
def test_workflow_reminder_uses_provider_chain():
    # Mock has_email_provider_configured True (Resend)
    # Mock send_ai_generated_email success
    # Assert workflow reminder sent via Resend, not SMTP-only

def test_workflow_reminder_silent_fail_without_provider():
    # Mock has_email_provider_configured False
    # Assert send_due_reminders returns (0, 0), no crash
```

---

## 六、下一步行动

### 立即修复（P1）
1. ✅ **验证邮箱死锁**：已完成（提交 `b7aca1d`）
2. ⬜ **邮件门控统一**：workflow/notification/auto_outreach 改用 `has_email_provider_configured()` + 三级链（2-3h，含测试）

### 短期改进（P2）
3. ⬜ 支付/Inbox 中文提示（1h）
4. ⬜ 补充 workflow 邮件测试（1h）

### 长期优化（P3）
5. ⬜ 首页配置引导（可选）
6. ⬜ 配置文档完善

---

**审查结论**：项目外部依赖管理整体合理，核心死锁问题已修复。剩余 4 个中风险点建议按优先级逐步修复，提升体验一致性。
