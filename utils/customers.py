"""
utils/customers.py
------------------
Customer data management with session_state cache and JSON persistence.
"""

from __future__ import annotations

import streamlit as st

from utils.storage import load_json, save_json

_FILENAME = "customers.json"


def _get_customers() -> list[dict]:
    """Get customer list from session_state, loading from disk on first access."""
    if "customers" not in st.session_state:
        st.session_state["customers"] = load_json(_FILENAME, default=[])
        st.session_state["_customers_loaded_from_disk"] = True
    elif not st.session_state.get("_customers_loaded_from_disk"):
        disk_data = load_json(_FILENAME, default=[])
        if disk_data and not st.session_state["customers"]:
            st.session_state["customers"] = disk_data
        st.session_state["_customers_loaded_from_disk"] = True
    return st.session_state["customers"]


def _persist_customers() -> None:
    """Save current customer list to disk."""
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
