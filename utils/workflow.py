"""
utils/workflow.py
-----------------
邮件跟进工作流管理。
追踪"已发开发信"的客户，提醒跟进时间节点，形成完整外贸销售闭环。
"""

from __future__ import annotations

from datetime import datetime, timedelta

import streamlit as st

from utils.storage import load_json, save_json

_FILENAME = "workflows.json"


# ── 跟进节点配置 ──────────────────────────────────────
FOLLOWUP_RULES: list[dict] = [
    {"days": 3,  "label": "3天跟进",  "stage": "已报价",   "hint": "询问是否收到邮件，温和确认"},
    {"days": 7,  "label": "1周跟进",  "stage": "已报价",   "hint": "分享产品新资讯或案例"},
    {"days": 14, "label": "2周跟进",  "stage": "长期未回复", "hint": "提供新价值，重新激活"},
    {"days": 30, "label": "1月跟进",  "stage": "长期未回复", "hint": "调整策略，考虑换话题切入"},
]


def _get_workflows() -> list[dict]:
    if "email_workflows" not in st.session_state:
        st.session_state["email_workflows"] = load_json(_FILENAME, default=[])
        st.session_state["_workflows_loaded_from_disk"] = True
    elif not st.session_state.get("_workflows_loaded_from_disk"):
        disk_data = load_json(_FILENAME, default=[])
        if disk_data and not st.session_state["email_workflows"]:
            st.session_state["email_workflows"] = disk_data
        st.session_state["_workflows_loaded_from_disk"] = True
    return st.session_state["email_workflows"]


def _persist_workflows() -> None:
    """Save current workflows to disk."""
    save_json(_FILENAME, st.session_state.get("email_workflows", []))


def add_workflow(
    customer: str,
    product: str,
    company: str = "",
    email: str = "",
    notes: str = "",
) -> None:
    """记录一封已发出的开发信，启动跟进工作流。"""
    workflows = _get_workflows()
    now = datetime.now()
    workflows.insert(0, {
        "id": f"wf_{len(workflows)+1}_{int(now.timestamp())}",
        "customer": customer,
        "product": product,
        "company": company,
        "email": email,
        "notes": notes,
        "sent_at": now.strftime("%Y-%m-%d"),
        "sent_ts": now.timestamp(),
        "status": "进行中",   # 进行中 / 已回复 / 已关闭
        "followups": [],      # 记录已完成的跟进
    })
    _persist_workflows()


def get_all_workflows() -> list[dict]:
    return _get_workflows()


def get_due_workflows() -> list[dict]:
    """返回今天需要跟进的工作流。"""
    now = datetime.now()
    due = []
    for wf in _get_workflows():
        if wf["status"] != "进行中":
            continue
        sent_ts = wf.get("sent_ts", 0)
        sent_dt = datetime.fromtimestamp(sent_ts)
        days_elapsed = (now - sent_dt).days
        done_stages = {f["stage_label"] for f in wf.get("followups", [])}

        for rule in FOLLOWUP_RULES:
            label = rule["label"]
            if label in done_stages:
                continue
            if days_elapsed >= rule["days"]:
                due.append({**wf, "_rule": rule, "_days_elapsed": days_elapsed})
                break   # 每个 workflow 只提一个最紧迫的
    return due


def mark_followup_done(wf_id: str, stage_label: str) -> None:
    """标记某个跟进节点已完成。"""
    for wf in _get_workflows():
        if wf["id"] == wf_id:
            wf["followups"].append({
                "stage_label": stage_label,
                "done_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
            })
            _persist_workflows()
            return


def update_workflow_status(wf_id: str, status: str) -> None:
    """更新工作流状态（已回复/已关闭）。"""
    for wf in _get_workflows():
        if wf["id"] == wf_id:
            wf["status"] = status
            _persist_workflows()
            return


def get_workflow_stats() -> dict:
    wfs = _get_workflows()
    total   = len(wfs)
    active  = sum(1 for w in wfs if w["status"] == "进行中")
    replied = sum(1 for w in wfs if w["status"] == "已回复")
    due_cnt = len(get_due_workflows())
    return {"total": total, "active": active, "replied": replied, "due": due_cnt}


def find_workflow_by_customer(customer_name: str, company: str) -> dict | None:
    """Find the first active workflow matching customer name and company."""
    customer_lower = customer_name.lower()
    company_lower = company.lower()
    for wf in _get_workflows():
        if wf["status"] != "进行中":
            continue
        if (wf.get("customer", "").lower() == customer_lower
                and wf.get("company", "").lower() == company_lower):
            return wf
    return None


def create_workflow_from_customer(customer_data: dict) -> bool:
    """Create a workflow from a customer dict. Returns False if duplicate exists."""
    contact = customer_data.get("contact", "")
    product = customer_data.get("product", "")
    company = customer_data.get("company", "")
    email = customer_data.get("email", "")

    # Check for duplicate: same customer + company + product with active status
    workflows = _get_workflows()
    contact_lower = contact.lower()
    company_lower = company.lower()
    product_lower = product.lower()
    for wf in workflows:
        if wf["status"] != "进行中":
            continue
        if (wf.get("customer", "").lower() == contact_lower
                and wf.get("company", "").lower() == company_lower
                and wf.get("product", "").lower() == product_lower):
            return False

    add_workflow(contact, product, company, email)
    return True
