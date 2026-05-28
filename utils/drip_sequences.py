"""
utils/drip_sequences.py
-----------------------
Drip campaign engine: multi-step email sequences.

A drip sequence sends a series of pre-planned emails to each prospect at
defined day-offsets (D0, D3, D7, D14, D30, ...). When the prospect replies,
the sequence automatically pauses for that prospect.

Key concepts:
  - SequenceTemplate: a named preset of steps (e.g. "b2b_standard")
  - Step: {day_offset, step_type, label} — what & when to send
  - ProspectState: per-prospect cursor: which step is next, when due, status

State lives inside the existing Campaign dict (in outreach_campaigns.json):
    campaign["sequence_enabled"] = True
    campaign["sequence_template"] = "b2b_standard"
    campaign["sequence_steps"]    = [...]   # snapshot of template at create-time
    campaign["prospects_state"]   = { email: {...} }

Per-prospect status values:
    active        - sequence in progress, next send pending
    replied       - prospect replied; sequence stopped
    completed     - all steps sent
    unsubscribed  - prospect opted out
    paused        - manually paused
    bounced       - hard bounce

Public API:
    SEQUENCE_TEMPLATES     - dict of preset templates
    get_template(name)     - fetch a template by name
    init_prospects_state(prospects, steps, start_at) -> dict
    advance_state(state, email, step_idx, sent_at) -> updated state
    mark_replied(state, email)
    mark_unsubscribed(state, email)
    get_due_prospects(campaign, now) -> list of (email, prospect, step_idx)
    summarize_state(state) -> {active, replied, completed, ...}
"""
from __future__ import annotations

from datetime import datetime, timedelta

from utils.logger import get_logger

logger = get_logger("drip_sequences")


# ---------------------------------------------------------------------------
# Step types — each maps to a different prompt strategy
# ---------------------------------------------------------------------------
# step_type values used throughout the system:
#   initial      = first outreach (uses build_auto_outreach_prompt)
#   value_add    = share useful content / case study / market insight
#   followup     = gentle nudge after no reply
#   social_proof = mention similar industry clients / recent wins
#   case_study   = detailed example of how product solved a specific problem
#   breakup      = "should I close your file?" — psychologically nudges replies
#   reengage     = months later, fresh angle


# ---------------------------------------------------------------------------
# Built-in sequence templates
# ---------------------------------------------------------------------------
SEQUENCE_TEMPLATES: dict[str, dict] = {
    "b2b_standard": {
        "label": "B2B 标准 (5步)",
        "description": "外贸标准节奏，60%场景适用：D0→D3→D7→D14→D30",
        "steps": [
            {"day_offset": 0,  "step_type": "initial",      "label": "首次开发信"},
            {"day_offset": 3,  "step_type": "value_add",    "label": "提供价值"},
            {"day_offset": 7,  "step_type": "followup",     "label": "温和跟进"},
            {"day_offset": 14, "step_type": "social_proof", "label": "案例佐证"},
            {"day_offset": 30, "step_type": "breakup",      "label": "Break-up邮件"},
        ],
    },
    "b2b_aggressive": {
        "label": "B2B 激进 (7步)",
        "description": "高峰期/促销季：D0→D2→D5→D9→D14→D21→D30",
        "steps": [
            {"day_offset": 0,  "step_type": "initial",      "label": "首次开发信"},
            {"day_offset": 2,  "step_type": "followup",     "label": "快速跟进"},
            {"day_offset": 5,  "step_type": "value_add",    "label": "产品价值"},
            {"day_offset": 9,  "step_type": "social_proof", "label": "行业案例"},
            {"day_offset": 14, "step_type": "case_study",   "label": "深度案例"},
            {"day_offset": 21, "step_type": "followup",     "label": "再次跟进"},
            {"day_offset": 30, "step_type": "breakup",      "label": "Break-up邮件"},
        ],
    },
    "b2b_gentle": {
        "label": "B2B 温和 (4步)",
        "description": "适合大客户/严肃行业：D0→D7→D14→D30",
        "steps": [
            {"day_offset": 0,  "step_type": "initial",     "label": "首次开发信"},
            {"day_offset": 7,  "step_type": "value_add",   "label": "深度价值分享"},
            {"day_offset": 14, "step_type": "case_study",  "label": "成功案例"},
            {"day_offset": 30, "step_type": "breakup",     "label": "礼貌收尾"},
        ],
    },
    "reengagement": {
        "label": "重新激活 (3步)",
        "description": "针对沉默客户：D0→D5→D14",
        "steps": [
            {"day_offset": 0,  "step_type": "reengage",  "label": "重新触达"},
            {"day_offset": 5,  "step_type": "value_add", "label": "新价值点"},
            {"day_offset": 14, "step_type": "breakup",   "label": "最后机会"},
        ],
    },
    "single_shot": {
        "label": "单封模式 (1步)",
        "description": "传统一次性发送，等价于不开启序列",
        "steps": [
            {"day_offset": 0, "step_type": "initial", "label": "开发信"},
        ],
    },
}


def get_template(name: str) -> dict | None:
    """Get a sequence template by name."""
    return SEQUENCE_TEMPLATES.get(name)


def list_templates() -> list[dict]:
    """List all available templates with metadata."""
    return [
        {
            "name": name,
            "label": tpl["label"],
            "description": tpl["description"],
            "step_count": len(tpl["steps"]),
            "duration_days": tpl["steps"][-1]["day_offset"] if tpl["steps"] else 0,
        }
        for name, tpl in SEQUENCE_TEMPLATES.items()
    ]


# ---------------------------------------------------------------------------
# Per-prospect state lifecycle
# ---------------------------------------------------------------------------

def init_prospects_state(
    prospects: list[dict],
    steps: list[dict],
    start_at: datetime | None = None,
) -> dict[str, dict]:
    """
    Initialize per-prospect drip state.

    Args:
        prospects: list of prospect dicts (must have 'email' key)
        steps: sequence steps from template
        start_at: when D0 should be (defaults to now)

    Returns:
        dict mapping email -> state dict
    """
    if start_at is None:
        start_at = datetime.now()

    state: dict[str, dict] = {}
    if not steps:
        return state

    first_offset = steps[0].get("day_offset", 0)
    first_send = start_at + timedelta(days=first_offset)

    for p in prospects:
        email = p.get("email", "").strip().lower()
        if not email:
            continue
        state[email] = {
            "current_step": 0,         # next step index to send
            "next_send_at": first_send.isoformat(),
            "status": "active",
            "history": [],
            "started_at": start_at.isoformat(),
        }

    return state


def advance_state(
    state: dict[str, dict],
    email: str,
    sent_step_idx: int,
    sent_at: datetime,
    steps: list[dict],
    subject: str = "",
) -> dict[str, dict]:
    """
    Advance a prospect's state after successfully sending step N.

    - Append the send to history
    - Increment current_step
    - Compute next_send_at (or mark completed if no more steps)

    Args:
        state: full prospects_state dict
        email: which prospect (lowercased)
        sent_step_idx: the step that was just sent
        sent_at: when it was sent (real send time)
        steps: full sequence steps list
        subject: optional subject for history

    Returns:
        updated state dict (mutated in place + returned)
    """
    email = email.strip().lower()
    if email not in state:
        logger.warning("advance_state: unknown prospect %s", email)
        return state

    ps = state[email]
    ps["history"].append({
        "step": sent_step_idx,
        "sent_at": sent_at.isoformat(),
        "subject": subject,
    })

    next_idx = sent_step_idx + 1
    if next_idx >= len(steps):
        ps["current_step"] = next_idx
        ps["status"] = "completed"
        ps["next_send_at"] = None
    else:
        # Compute next send relative to original D0 (started_at)
        try:
            started_at = datetime.fromisoformat(ps["started_at"])
        except (KeyError, ValueError):
            started_at = sent_at  # fallback

        next_offset = steps[next_idx].get("day_offset", 0)
        next_send = started_at + timedelta(days=next_offset)
        ps["current_step"] = next_idx
        ps["next_send_at"] = next_send.isoformat()
        ps["status"] = "active"

    return state


def mark_replied(state: dict[str, dict], email: str) -> bool:
    """
    Mark a prospect as having replied — pauses the sequence.

    Returns True if state was changed, False if email not found or already
    in a terminal state.
    """
    email = email.strip().lower()
    if email not in state:
        return False
    ps = state[email]
    if ps["status"] in ("active",):
        ps["status"] = "replied"
        ps["next_send_at"] = None
        ps["replied_at"] = datetime.now().isoformat()
        logger.info("Drip sequence stopped for %s (replied)", email)
        return True
    return False


def mark_unsubscribed(state: dict[str, dict], email: str) -> bool:
    """Mark a prospect as unsubscribed; permanently halts the sequence."""
    email = email.strip().lower()
    if email not in state:
        return False
    ps = state[email]
    ps["status"] = "unsubscribed"
    ps["next_send_at"] = None
    ps["unsubscribed_at"] = datetime.now().isoformat()
    logger.info("Drip sequence stopped for %s (unsubscribed)", email)
    return True


def mark_bounced(state: dict[str, dict], email: str) -> bool:
    """Mark a prospect as bounced; halts the sequence."""
    email = email.strip().lower()
    if email not in state:
        return False
    ps = state[email]
    ps["status"] = "bounced"
    ps["next_send_at"] = None
    return True


def pause_prospect(state: dict[str, dict], email: str) -> bool:
    """Manually pause a single prospect."""
    email = email.strip().lower()
    if email not in state:
        return False
    ps = state[email]
    if ps["status"] == "active":
        ps["status"] = "paused"
        return True
    return False


def resume_prospect(state: dict[str, dict], email: str) -> bool:
    """Resume a manually-paused prospect (does NOT recover replied/unsubscribed)."""
    email = email.strip().lower()
    if email not in state:
        return False
    ps = state[email]
    if ps["status"] == "paused":
        ps["status"] = "active"
        return True
    return False


# ---------------------------------------------------------------------------
# Scheduling: which prospects need an email RIGHT NOW
# ---------------------------------------------------------------------------

def get_due_prospects(
    campaign: dict,
    now: datetime | None = None,
) -> list[tuple[str, dict, int]]:
    """
    Find prospects whose next sequence step is due to be sent.

    Args:
        campaign: campaign dict (must have prospects, sequence_steps, prospects_state)
        now: current time (defaults to datetime.now())

    Returns:
        list of (email, prospect_dict, step_index) tuples ready for sending,
        ordered by next_send_at (earliest first).
    """
    if now is None:
        now = datetime.now()

    state = campaign.get("prospects_state", {})
    steps = campaign.get("sequence_steps", [])
    prospects_by_email = {
        p.get("email", "").strip().lower(): p
        for p in campaign.get("prospects", [])
    }

    if not state or not steps:
        return []

    due = []
    for email, ps in state.items():
        if ps.get("status") != "active":
            continue
        next_send_str = ps.get("next_send_at")
        if not next_send_str:
            continue
        try:
            next_send = datetime.fromisoformat(next_send_str)
        except ValueError:
            continue
        if next_send > now:
            continue

        step_idx = ps.get("current_step", 0)
        if step_idx >= len(steps):
            continue

        prospect = prospects_by_email.get(email)
        if not prospect:
            continue

        due.append((email, prospect, step_idx))

    # Earliest-due first
    due.sort(key=lambda x: state[x[0]].get("next_send_at", ""))
    return due


# ---------------------------------------------------------------------------
# Reporting / aggregates
# ---------------------------------------------------------------------------

def summarize_state(state: dict[str, dict]) -> dict[str, int]:
    """
    Count prospects by status for dashboard display.

    Returns dict with keys: active, replied, completed, unsubscribed,
                            bounced, paused, total
    """
    summary = {
        "total": len(state),
        "active": 0,
        "replied": 0,
        "completed": 0,
        "unsubscribed": 0,
        "bounced": 0,
        "paused": 0,
    }
    for ps in state.values():
        status = ps.get("status", "active")
        if status in summary:
            summary[status] += 1
    return summary


def count_step_completions(state: dict[str, dict], step_count: int) -> list[int]:
    """
    Per-step completion count: how many prospects have received step N.

    Returns list of length step_count.
    """
    counts = [0] * step_count
    for ps in state.values():
        for hist in ps.get("history", []):
            idx = hist.get("step", -1)
            if 0 <= idx < step_count:
                counts[idx] += 1
    return counts


def reply_rate_per_step(state: dict[str, dict], step_count: int) -> list[float]:
    """
    For each step N: of prospects who received step N, what % replied
    BEFORE receiving step N+1?

    Returns list of length step_count, each value 0.0 - 100.0.
    """
    if step_count <= 0:
        return []

    received_step = [0] * step_count
    replied_at_step = [0] * step_count

    for ps in state.values():
        history = ps.get("history", [])
        # Each prospect received steps 0..len(history)-1
        for hist in history:
            idx = hist.get("step", -1)
            if 0 <= idx < step_count:
                received_step[idx] += 1

        # If they replied, it happened after their last sent step
        if ps.get("status") == "replied" and history:
            last_step_idx = history[-1].get("step", -1)
            if 0 <= last_step_idx < step_count:
                replied_at_step[last_step_idx] += 1

    rates = []
    for i in range(step_count):
        if received_step[i] == 0:
            rates.append(0.0)
        else:
            rates.append(round(replied_at_step[i] / received_step[i] * 100, 1))
    return rates
