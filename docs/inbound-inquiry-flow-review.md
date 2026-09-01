# 客户咨询邮件后续流程梳理

**日期:** 2026-08-29
**范围:** 客户咨询（inquiry）邮件从「收件 → 分类 → 回复 → 发送 → 沉淀 CRM → 跟进」的全链路现状梳理
**依据:** 代码阅读（utils/ + pages/），不含主观臆断

---

## 一、现有入口与主线（4 入口 / 3 主存储 / 2 套意图体系）

### 入口 A：AI 收件箱（`pages/35_📥_AI收件箱.py`）——实时邮箱，最完整

```
Gmail/Outlook OAuth ─┐
 (utils/inbox_integration.fetch_inbox)   ┐
MailSlurp 收件 ──────┤                    ├→ utils/inbox_ai.process_inbox()
 (utils/mailslurp_integration.process_    │   AI 分类意图 + 优先级 + 缓存(processed_*.json)
  received_inbox → 同一管线)              ┘
        │
        ▼
process_inbox 输出: {email, classification{intent, priority_score, urgency}, email_id}
        │
        ▼
generate_reply_suggestion()  AI 生成回复（受信内容 sanitize_input 后进 prompt）
        │
        ▼
send_via_provider()  → Gmail/Outlook API 直发（utils/inbox_integration.py:332）
        │
        ⚠️ 断点：发送后不建 tracking_id、不写 outreach log（页内 TODO:446）、
          不回写 CRM；处理结果只存在 inbox_ai 的分类缓存里
```

### 入口 B：入站邮件（`pages/37_📥_入站邮件.py`）——手动导入

```
粘贴原文 / 上传 .eml / 填写关联客户ID
        │
        ▼
utils.inbound_email.create_inbound_record()
  → data/users/<user>/inbound_emails.json   （status=pending，fingerprint 幂等去重）
        │
        ▼
「生成回复草稿」→ update_inbound_status(drafted)
「标记已回复」  → update_inbound_status(replied)
「归档」        → update_inbound_status(archived)
        ⚠️ 断点：该入口无「发送」动作——草稿只能被标记，实际回信要走别的入口；
          与 inbox_ai（入口A）完全独立存储，互不感知
```

### 入口 C：自动推送 → 自动回复（`pages/36_🚀_自动推送.py`，`utils/auto_outreach.auto_reply_to_customer`）

```
唯一调用点：页面「🧪 模拟自动回复」（588-649 行，按钮手动触发）
  ① 识别意图（独立 prompt 的 INTENT: 明文解析：interested/need_info/bargain/order…）
  ② 生成回复
  ③ 重点邮件 → 转发到 campaign.forward_email
        ⚠️ 断点：仅测试工具；无收件抓取、无定时触发、无落库；
          意图体系与 inbox_ai 的 INTENT_CATEGORIES 是两套
```

### 入口 D：CRM 与跟进（`pages/7_📇_客户管理.py`、`pages/5_📬_跟进邮件.py`、`pages/10_📅_跟进日历.py`）

```
手动「添加客户」(pages/7) → utils.customers.add_customer
        │
        ▼  （阶段为 已发信/已询盘/已报价/已发样/谈判中 时）
utils.workflow.create_workflow_from_customer → 跟进工作流（5 阶段）
        │
        ▼
pages/5 跟进邮件 / pages/10 跟进日历 / send_due_reminders（到期提醒）
        ⚠️ 断点：邮件链路（A/B/C）不会自动沉淀客户或创建跟进；
          全链路依赖手动录入（客户画像/客户分析页同样以手动客户为数据源）
```

---

## 二、三套并行存储 vs 单一事实源

| 存储 | 负责人 | 内容 | 生命周期 |
|---|---|---|---|
| `inbound_emails.json`（用户级） | inbound_email.py | 手动导入邮件 + status | pending→drafted→replied→archived |
| `processed_*.json`（用户级） | inbox_ai.py | AI 分类缓存（intent/priority） | 200 条滑动窗口，与发送无关 |
| `email_tracking.json`（全局） | email_tracking.py | 外发邮件追踪记录 | email_service / inbox 直发均可创建 |
| `outreach_log.json`（用户级） | outreach_log.py | 统一对外发送日志 | inbox/inbound/campaign 共用，最多500条 |

**剩余问题：** 入站、分类缓存、追踪和统一发送日志仍是不同集合；P4 计划引入 customer_timeline 归一化事件流。

---

## 三、断点清单（按数据流顺序）

| # | 断点 | 位置 | 影响 |
|---|---|---|---|
| B1 | 入口A发送后不建 tracking、不落 outreach log | `pages/35:446` TODO | ✅ P1：`send_via_provider` 自动记录 |
| B2 | 入口B无「发送」动作，草稿无法真正回信 | `pages/37` | ✅ P1：新增直接回复按钮 |
| B3 | 邮件链路不自动沉淀 CRM / 跟进工作流 | inbox/inbound 均无 add_customer 联动 | ✅ P2：高意图自动建客户+工作流 |
| B4 | 高优先级意图无通知提醒 | inbox_ai 分类后无人触发 notify(hot_lead/…) | ✅ P2：触发 hot_lead |
| B5 | 两套意图体系不一致 | inbox_ai.INTENT_CATEGORIES vs auto_reply 的 INTENT: | ✅ P3：统一 canonical key + legacy 映射 |
| B6 | 三套存储并行、无统一事件流 | inbound / processed / tracking | ✅ P4a：customer_timeline 统一事件流 + 核心写入点 |
| B7 | 入站邮件回复不关联 campaign/产品上下文 | inbound_email 无 campaign_id 字段 | ✅ B7：关联推送任务 + 回复生成时带产品/公司上下文 |

---

## 四、建议优化路线（按 ROI 排序，均可 TDD）

**P1 — 打通「发送 → 记录」闭环（治 B1+B2）——✅ 已完成（`eeb167e`）**
- `send_via_provider` 成功后创建 tracking + 写 unified `outreach_log.json`
- 入口B增加「发送回复」按钮：`email_service.send_ai_generated_email`（Resend/SendGrid/SMTP 链）→ 状态 replied + 写 log

**P2 — 意图 → CRM/跟进联动（治 B3+B4）——✅ 已完成（`021d5ac`）**
- 分类后，对高意图邮件自动按 email 去重创建 CRM 客户、跟进工作流和 `hot_lead` 通知

**P3 — 统一意图体系（治 B5）——✅ 已完成（`3e2d642`）**
- `auto_reply_to_customer` 输出 `inbox_ai.INTENT_CATEGORIES` canonical key
- 旧英文文案通过 `normalize_reply_intent` 兼容映射；页面显示中文 label

**P4a — 统一事件流基础（治 B6）——✅ 已完成（`5bd47f9`）**
- 新建 `customer_timeline.json`（用户级，最多 1000 条事件）
- 核心写入点：lead_capture 成功、inbox send_via_provider、inbound send_reply
- 事件类型：lead_captured / email_sent / email_replied（timestamp + data + source）

**P4b — 客户画像时间线展示——✅ 已完成（待提交）**
- pages/7 客户管理：每个客户 expander 内展示最近 10 条互动事件
- 时间 + 事件类型 + 简要信息（主题/意图/工作流状态）

**P4c — 历史数据回填（可选后续）**

---

## 五、本次未覆盖（明确排除）

- 定时自动回复（需要定时任务 + Stripe/邮件 webhook 之外的新基础设施）
- Gmail/Outlook OAuth 之外的新邮箱接入
- 回复邮件语调/品牌化（已属生成质量优化）

---

*文档定位：现状梳理与优化候选，供决策；实施需另立计划并按 TDD 执行。*