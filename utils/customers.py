"""
utils/customers.py
------------------
Customer data management with session_state cache and JSON persistence.
Supports per-user isolation when a user is logged in.
"""

from __future__ import annotations

import streamlit as st

from utils.storage import load_json, load_user_json, save_json, save_user_json

_FILENAME = "customers.json"


def _get_current_username() -> str | None:
    """Get current logged-in username, or None for shared/admin mode."""
    user = st.session_state.get("current_user")
    if user and user.get("username") and user["username"] != "admin":
        return user["username"]
    return None


def _get_customers() -> list[dict]:
    """Get customer list from session_state, loading from disk on first access."""
    username = _get_current_username()
    if username:
        flag_key = f"_customers_loaded_from_disk_{username}"
        state_key = f"customers_{username}"
        if state_key not in st.session_state or not st.session_state.get(flag_key):
            st.session_state[state_key] = load_user_json(username, _FILENAME, default=[])
            st.session_state[flag_key] = True
        return st.session_state[state_key]
    else:
        if "customers" not in st.session_state or not st.session_state.get("_customers_loaded_from_disk"):
            st.session_state["customers"] = load_json(_FILENAME, default=[])
            st.session_state["_customers_loaded_from_disk"] = True
        return st.session_state["customers"]


def _persist_customers() -> None:
    """Save current customer list to disk."""
    username = _get_current_username()
    if username:
        state_key = f"customers_{username}"
        save_user_json(username, _FILENAME, st.session_state.get(state_key, []))
    else:
        save_json(_FILENAME, st.session_state.get("customers", []))


def get_customers() -> list[dict]:
    """Return the list of customers."""
    return _get_customers()


def add_customer(data: dict) -> None:
    """Append a customer and persist to disk."""
    customers = _get_customers()
    customers.append(data)
    _persist_customers()


def delete_customer(index: int) -> None:
    """Remove a customer by index and persist to disk."""
    customers = _get_customers()
    if 0 <= index < len(customers):
        customers.pop(index)
        _persist_customers()


def update_customer(index: int, data: dict) -> None:
    """Update a customer by index and persist to disk."""
    customers = _get_customers()
    if 0 <= index < len(customers):
        customers[index] = data
        _persist_customers()


def import_customers(data: list) -> None:
    """Bulk-import customer data, replacing current state and persisting to disk."""
    username = _get_current_username()
    if username:
        state_key = f"customers_{username}"
        flag_key = f"_customers_loaded_from_disk_{username}"
        st.session_state[state_key] = data
        st.session_state[flag_key] = True
    else:
        st.session_state["customers"] = data
        st.session_state["_customers_loaded_from_disk"] = True
    _persist_customers()


def find_customer(company: str, contact: str) -> dict | None:
    """Find a customer by company AND contact name (case-insensitive)."""
    customers = _get_customers()
    company_lower = company.lower()
    contact_lower = contact.lower()
    for cust in customers:
        if (cust.get("company", "").lower() == company_lower
                and cust.get("contact", "").lower() == contact_lower):
            return cust
    return None


def update_customer_stage(company: str, contact: str, new_stage: str) -> bool:
    """Find the customer, update their stage and last_contact. Return True if updated."""
    from datetime import datetime

    customers = _get_customers()
    company_lower = company.lower()
    contact_lower = contact.lower()
    for cust in customers:
        if (cust.get("company", "").lower() == company_lower
                and cust.get("contact", "").lower() == contact_lower):
            cust["stage"] = new_stage
            cust["last_contact"] = datetime.now().strftime("%Y-%m-%d")
            _persist_customers()
            return True
    return False



# ---------------------------------------------------------------------------
# Customer scoring & tagging helpers
# ---------------------------------------------------------------------------

# Stage weights for automatic score calculation
_STAGE_SCORES: dict[str, int] = {
    "新客户": 10,
    "待开发": 10,
    "已发信": 20,
    "已联系": 25,
    "已询盘": 40,
    "已报价": 55,
    "已发样": 65,
    "谈判中": 75,
    "已下单": 90,
    "长期合作": 95,
    "长期客户": 95,
}

PREDEFINED_TAGS: list[str] = [
    "VIP", "高潜力", "价格敏感", "快速决策", "需要跟进",
    "样品请求", "大订单", "季节性", "竞争激烈", "推荐客户",
]


def compute_customer_score(customer: dict) -> int:
    """
    Compute a 0-100 engagement score for a customer.

    Based on:
    - Stage weight (primary, 0-60 pts)
    - Recency of last contact (0-25 pts)
    - Data completeness (0-15 pts)
    """
    import datetime

    stage = customer.get("stage", "新客户")
    stage_score = min(_STAGE_SCORES.get(stage, 10), 60)

    # Recency score (25 pts max)
    recency_score = 0
    last_contact = customer.get("last_contact", "")
    if last_contact:
        try:
            days = (datetime.date.today() - datetime.date.fromisoformat(last_contact)).days
            if days <= 7:
                recency_score = 25
            elif days <= 30:
                recency_score = 18
            elif days <= 90:
                recency_score = 10
            else:
                recency_score = 3
        except (ValueError, TypeError):
            pass

    # Completeness score (15 pts max)
    complete_score = 0
    if customer.get("email"):
        complete_score += 5
    if customer.get("phone") or customer.get("contact"):
        complete_score += 5
    if customer.get("product") or customer.get("notes"):
        complete_score += 5

    return min(stage_score + recency_score + complete_score, 100)


def get_customer_tags(index: int) -> list[str]:
    """Return the tags list for a customer by index."""
    customers = _get_customers()
    if 0 <= index < len(customers):
        return customers[index].get("tags", [])
    return []


def add_tag(index: int, tag: str) -> None:
    """Add a tag to a customer (no duplicates)."""
    customers = _get_customers()
    if 0 <= index < len(customers):
        tags = customers[index].get("tags", [])
        if tag not in tags:
            tags.append(tag)
            customers[index]["tags"] = tags
            _persist_customers()


def remove_tag(index: int, tag: str) -> None:
    """Remove a tag from a customer."""
    customers = _get_customers()
    if 0 <= index < len(customers):
        tags = customers[index].get("tags", [])
        if tag in tags:
            tags.remove(tag)
            customers[index]["tags"] = tags
            _persist_customers()


def get_customers_by_tag(tag: str) -> list[dict]:
    """Return all customers that have the given tag."""
    return [c for c in _get_customers() if tag in c.get("tags", [])]
