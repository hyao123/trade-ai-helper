"""Build full account backup bundles from scoped persisted data."""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any


def build_backup_bundle(
    *,
    customers: Sequence[Mapping[str, Any]] | None = None,
    history: Sequence[Mapping[str, Any]] | None = None,
    templates: Mapping[str, Sequence[Mapping[str, Any]]] | None = None,
    workflows: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Return a full backup bundle, loading scoped data when omitted."""
    if customers is None:
        from utils.customers import get_customers

        customers = get_customers()
    if history is None:
        from utils.history import _get_history

        history = _get_history()
    if templates is None:
        from utils.templates import _get_store

        templates = _get_store()
    if workflows is None:
        from utils.workflow import get_all_workflows

        workflows = get_all_workflows()

    return {
        "version": "1.0",
        "customers": list(customers),
        "history": list(history),
        "templates": {key: list(value) for key, value in dict(templates).items()},
        "workflows": list(workflows),
    }
