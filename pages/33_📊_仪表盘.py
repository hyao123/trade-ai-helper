"""
pages/33_📊_仪表盘.py
商业化仪表盘：邮件追踪统计、客户评分概览、通知中心、邀请裂变。
整合 email_tracking, customer_scoring, notifications, referral 模块。
"""
from __future__ import annotations

import streamlit as st

from utils.ui_helpers import check_auth, get_user_id, inject_css

st.set_page_config(page_title="仪表盘 | 外贸AI助手", page_icon="📊", layout="wide")
inject_css()
check_auth()

# ── 页头 ──────────────────────────────────────────────
st.markdown("""
<div class="hero-section">
    <h1 class="hero-title">📊 智能仪表盘</h1>
    <p class="hero-subtitle">邮件追踪 · 客户评分 · 通知中心 · 邀请奖励 — 一站掌握全局</p>
</div>
""", unsafe_allow_html=True)

uid = get_user_id()

# ── Tab 布局 ──────────────────────────────────────────
tab_email, tab_score, tab_notify, tab_referral = st.tabs([
    "📧 邮件追踪", "🔥 客户评分", "🔔 通知中心", "🎁 邀请奖励"
])

# ══════════════════════════════════════════════════════
# Tab 1: 邮件追踪统计
# ══════════════════════════════════════════════════════
with tab_email:
    st.markdown("### 📧 邮件发送统计")

    try:
        from utils.email_tracking import get_recent_activity, get_user_email_stats

        stats = get_user_email_stats(uid, days=30)

        if stats["total_sent"] == 0:
            st.info("📭 暂无邮件发送记录。使用「开发信」页面发送邮件后，追踪数据将在此显示。")
        else:
            # ── KPI 指标卡 ──
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("📨 已发送", stats["total_sent"])
            c2.metric("👁️ 已打开", stats["total_opened"],
                      delta=f"{stats['open_rate']}%")
            c3.metric("🖱️ 已点击", stats["total_clicked"],
                      delta=f"{stats['click_rate']}%")
            c4.metric("💬 已回复", stats["total_replied"],
                      delta=f"{stats['reply_rate']}%")

            st.caption(f"统计周期：最近 {stats['period_days']} 天")

            # ── 转化漏斗 ──
            st.markdown("---")
            st.markdown("#### 📉 转化漏斗")
            funnel_data = {
                "发送": stats["total_sent"],
                "打开": stats["total_opened"],
                "点击": stats["total_clicked"],
                "回复": stats["total_replied"],
            }
            for stage, count in funnel_data.items():
                pct = (count / stats["total_sent"] * 100) if stats["total_sent"] > 0 else 0
                bar_width = max(pct, 2)
                st.markdown(
                    f'<div style="display:flex;align-items:center;margin-bottom:0.5rem;">'
                    f'<div style="width:60px;font-size:0.85rem;color:#4b5563;">{stage}</div>'
                    f'<div style="flex:1;background:#e5e7eb;border-radius:8px;height:24px;overflow:hidden;">'
                    f'<div style="width:{bar_width}%;background:#3b82f6;height:100%;border-radius:8px;'
                    f'display:flex;align-items:center;padding-left:8px;color:white;font-size:0.75rem;">'
                    f'{count} ({pct:.0f}%)</div></div></div>',
                    unsafe_allow_html=True,
                )

            # ── 最近活动 ──
            st.markdown("---")
            st.markdown("#### 📋 最近邮件活动")
            activities = get_recent_activity(uid, limit=10)
            if activities:
                for act in activities:
                    icon = {"open": "👁️", "click": "🖱️", "reply": "💬"}.get(act["type"], "•")
                    time_str = act.get("at", "")[:16].replace("T", " ")
                    st.markdown(
                        f"**{icon}** {act['to_email']} — _{act['subject'][:40]}_ · {time_str}"
                    )
            else:
                st.caption("暂无活动记录")

    except ImportError:
        st.warning("⚠️ 邮件追踪模块未安装")
    except Exception as e:
        st.error(f"加载邮件统计失败: {e}")

# ══════════════════════════════════════════════════════
# Tab 2: 客户评分
# ══════════════════════════════════════════════════════
with tab_score:
    st.markdown("### 🔥 客户行为评分")

    try:
        from utils.customer_scoring import batch_score_customers, get_score_summary
        from utils.customers import get_customers

        customers = get_customers()

        if not customers:
            st.info("📇 暂无客户数据。请先在「客户管理」页面添加客户。")
        else:
            # Score all customers
            with st.spinner("🧠 AI 正在分析客户行为..."):
                scored = batch_score_customers(uid, customers)

            # ── 总览指标 ──
            summary = get_score_summary(uid)
            c1, c2, c3 = st.columns(3)
            c1.metric("📊 平均分", f"{summary['avg_score']:.0f}/100")
            c2.metric("🔥 热门线索", summary["hot_leads_count"])
            c3.metric("📇 总客户", summary["total"])

            # ── 分层分布 ──
            st.markdown("---")
            st.markdown("#### 📊 客户分层分布")
            tier_dist = summary.get("tier_distribution", {})
            for tier_name, count in tier_dist.items():
                if count > 0:
                    pct = (count / summary["total"] * 100) if summary["total"] > 0 else 0
                    st.markdown(f"**{tier_name}**: {count} 位 ({pct:.0f}%)")

            # ── Top 10 热门客户 ──
            st.markdown("---")
            st.markdown("#### 🏆 Top 10 高分客户")
            for i, item in enumerate(scored[:10]):
                cust = item["customer"]
                score = item["score"]
                change = item.get("score_change", 0)
                change_str = f" (+{change})" if change > 0 else f" ({change})" if change < 0 else ""

                col1, col2, col3 = st.columns([3, 1, 1])
                with col1:
                    st.markdown(
                        f"**{i+1}. {cust.get('company', '—')}** — {cust.get('contact', '—')} "
                        f"({cust.get('stage', '')})"
                    )
                with col2:
                    st.markdown(
                        f"<span style='font-size:1.2rem;font-weight:700;color:{score['tier_color']};'>"
                        f"{score['tier_icon']} {score['total_score']}</span>",
                        unsafe_allow_html=True,
                    )
                with col3:
                    if change != 0:
                        st.caption(f"变化{change_str}")

    except ImportError:
        st.warning("⚠️ 客户评分模块未安装")
    except Exception as e:
        st.error(f"加载评分失败: {e}")

# ══════════════════════════════════════════════════════
# Tab 3: 通知中心
# ══════════════════════════════════════════════════════
with tab_notify:
    st.markdown("### 🔔 通知中心")

    try:
        from utils.notifications import (
            delete_notification,
            get_all_notifications,
            get_unread_count,
            mark_all_read,
            mark_read,
        )

        unread_count = get_unread_count(uid)

        # ── 操作栏 ──
        col_a, col_b = st.columns([3, 1])
        with col_a:
            if unread_count > 0:
                st.markdown(f"**{unread_count} 条未读通知**")
            else:
                st.markdown("✅ 所有通知已读")
        with col_b:
            if unread_count > 0 and st.button("全部标为已读", use_container_width=True):
                mark_all_read(uid)
                st.rerun()

        # ── 通知列表 ──
        notifications = get_all_notifications(uid, limit=30)
        if not notifications:
            st.info("📭 暂无通知。当有跟进提醒、邮件打开等事件时，通知将显示在这里。")
        else:
            for notif in notifications:
                is_unread = not notif.get("read", False)
                bg = "#eff6ff" if is_unread else "#ffffff"
                border = "2px solid #3b82f6" if is_unread else "1px solid #e5e7eb"
                icon = notif.get("icon", "🔔")
                title = notif.get("title", "")
                time_str = notif.get("created_at", "")[:16].replace("T", " ")

                st.markdown(
                    f'<div style="background:{bg};border:{border};border-radius:10px;'
                    f'padding:0.8rem 1rem;margin-bottom:0.5rem;">'
                    f'<div style="display:flex;justify-content:space-between;align-items:center;">'
                    f'<span style="font-size:0.9rem;">{icon} {title}</span>'
                    f'<span style="font-size:0.75rem;color:#9ca3af;">{time_str}</span>'
                    f'</div></div>',
                    unsafe_allow_html=True,
                )

                # Mark read on expand
                if is_unread:
                    mark_read(uid, notif["id"])

    except ImportError:
        st.warning("⚠️ 通知模块未安装")
    except Exception as e:
        st.error(f"加载通知失败: {e}")

# ══════════════════════════════════════════════════════
# Tab 4: 邀请裂变
# ══════════════════════════════════════════════════════
with tab_referral:
    st.markdown("### 🎁 邀请好友，双方获益")

    try:
        from utils.referral import get_referral_link, get_referral_stats

        stats = get_referral_stats(uid)

        # ── 邀请链接 ──
        if stats.get("code"):
            st.markdown('<div class="main-form">', unsafe_allow_html=True)
            st.markdown("#### 🔗 你的专属邀请链接")
            link = stats.get("link", "")
            st.code(link, language=None)
            st.caption("分享此链接给好友，对方注册后双方各得 AI 额度奖励！")
            st.markdown("</div>", unsafe_allow_html=True)
        else:
            st.info("首次使用时将自动生成你的邀请链接。")

        # ── 奖励统计 ──
        st.markdown("---")
        c1, c2, c3 = st.columns(3)
        c1.metric("👥 已邀请", stats.get("total_referrals", 0))
        c2.metric("💰 获得积分", stats.get("total_credits_earned", 0))
        c3.metric("🎯 积分余额", stats.get("bonus_credits_balance", 0))

        # ── 下一个里程碑 ──
        next_ms = stats.get("next_milestone")
        if next_ms:
            st.markdown("---")
            st.markdown("#### 🏆 下一个里程碑")
            current = stats.get("total_referrals", 0)
            target = next_ms["target"]
            remaining = next_ms["remaining"]
            progress = current / target if target > 0 else 0
            st.progress(min(progress, 1.0))
            st.caption(
                f"再邀请 **{remaining}** 人即可获得：**{next_ms['reward_label']}** "
                f"(已完成 {current}/{target})"
            )

        # ── 奖励规则 ──
        st.markdown("---")
        with st.expander("📋 奖励规则"):
            st.markdown("""
            | 事件 | 奖励 |
            |------|------|
            | 好友注册 | 你 +30 积分，好友 +20 积分 |
            | 邀请满 5 人 | +100 额外积分 |
            | 邀请满 10 人 | 7 天 Pro 试用 |
            | 邀请满 25 人 | 1 个月 Pro 免费 |
            | 邀请满 50 人 | +500 额外积分 |

            *积分可在 AI 生成次数用尽后，作为额外额度使用。*
            """)

    except ImportError:
        st.warning("⚠️ 邀请模块未安装")
    except Exception as e:
        st.error(f"加载邀请数据失败: {e}")

# ── Footer ──────────────────────────────────────────────
st.markdown("---")
st.markdown('<div class="footer">💼 外贸AI助手 · 智能仪表盘</div>', unsafe_allow_html=True)
