"""
utils/teams.py
--------------
Team/workspace multi-user system with role-based access control.

Concepts:
- Tenant (Team/Workspace): A group of users sharing customer data and settings
- Roles: owner, admin, manager, member
- Customer Pool: shared (public pool) vs assigned (private pool)
- Seat-based billing: team plan includes N seats, extras cost more

Role permissions:
  owner     — full control, billing, delete team
  admin     — manage members, settings, view all data
  manager   — assign customers, view team stats, manage own + team members' data
  member    — CRUD own customers, generate AI content, view own stats

Usage:
    from utils.teams import (
        create_team, invite_member, get_team, get_user_role,
        assign_customer, get_public_pool, reclaim_inactive_customers,
    )
"""
from __future__ import annotations

import secrets
from datetime import datetime

from utils.logger import get_logger
from utils.storage import load_json, save_json

logger = get_logger("teams")

_TEAMS_FILE = "teams.json"
_INVITES_FILE = "team_invites.json"

# ---------------------------------------------------------------------------
# Role definitions & permissions
# ---------------------------------------------------------------------------

ROLES = ["owner", "admin", "manager", "member"]

PERMISSIONS: dict[str, set[str]] = {
    "owner": {
        "manage_billing", "delete_team", "manage_members", "manage_settings",
        "view_all_customers", "assign_customers", "view_team_stats",
        "manage_own_data", "generate_ai",
    },
    "admin": {
        "manage_members", "manage_settings", "view_all_customers",
        "assign_customers", "view_team_stats", "manage_own_data", "generate_ai",
    },
    "manager": {
        "view_all_customers", "assign_customers", "view_team_stats",
        "manage_own_data", "generate_ai",
    },
    "member": {
        "manage_own_data", "generate_ai",
    },
}


def has_permission(role: str, permission: str) -> bool:
    """Check if a role has a specific permission."""
    return permission in PERMISSIONS.get(role, set())


# ---------------------------------------------------------------------------
# Team CRUD
# ---------------------------------------------------------------------------

def _load_teams() -> list[dict]:
    return load_json(_TEAMS_FILE, default=[])


def _save_teams(teams: list[dict]) -> None:
    save_json(_TEAMS_FILE, teams)


def create_team(name: str, owner_username: str) -> dict:
    """
    Create a new team with the given user as owner.

    Args:
        name: Team/workspace display name
        owner_username: Username of the team creator (becomes owner)

    Returns:
        The created team dict
    """
    teams = _load_teams()

    team = {
        "id": secrets.token_hex(8),
        "name": name.strip(),
        "owner": owner_username,
        "plan": "team",
        "max_seats": 5,
        "members": [
            {
                "username": owner_username,
                "role": "owner",
                "joined_at": datetime.now().isoformat(),
                "status": "active",
            }
        ],
        "settings": {
            "auto_reclaim_days": 30,  # Reclaim uncontacted customers after N days
            "public_pool_enabled": True,
        },
        "created_at": datetime.now().isoformat(),
    }

    teams.append(team)
    _save_teams(teams)
    logger.info("Team created: %s (owner=%s)", name, owner_username)
    return team


def get_team(team_id: str) -> dict | None:
    """Get a team by its ID."""
    teams = _load_teams()
    for team in teams:
        if team["id"] == team_id:
            return team
    return None


def get_user_team(username: str) -> dict | None:
    """Get the team a user belongs to (first match)."""
    teams = _load_teams()
    for team in teams:
        for member in team.get("members", []):
            if member["username"] == username and member.get("status") == "active":
                return team
    return None


def get_user_role(username: str, team_id: str = "") -> str | None:
    """
    Get the user's role in their team.

    Args:
        username: The user to look up
        team_id: Optional specific team ID (uses first team if empty)

    Returns:
        Role string or None if not in any team
    """
    if team_id:
        team = get_team(team_id)
    else:
        team = get_user_team(username)

    if not team:
        return None

    for member in team.get("members", []):
        if member["username"] == username and member.get("status") == "active":
            return member["role"]
    return None


def get_team_members(team_id: str) -> list[dict]:
    """Get all active members of a team."""
    team = get_team(team_id)
    if not team:
        return []
    return [m for m in team.get("members", []) if m.get("status") == "active"]


# ---------------------------------------------------------------------------
# Member management
# ---------------------------------------------------------------------------

def add_member(team_id: str, username: str, role: str = "member") -> tuple[bool, str]:
    """
    Add a user to a team.

    Args:
        team_id: Team to add to
        username: Username to add
        role: Role to assign (default: member)

    Returns:
        (success, message) tuple
    """
    if role not in ROLES:
        return False, f"Invalid role: {role}"

    teams = _load_teams()
    for team in teams:
        if team["id"] == team_id:
            # Check seat limit
            active_count = sum(1 for m in team["members"] if m.get("status") == "active")
            if active_count >= team.get("max_seats", 5):
                return False, f"Team is full ({active_count}/{team['max_seats']} seats)"

            # Check if already a member
            for member in team["members"]:
                if member["username"] == username:
                    if member["status"] == "active":
                        return False, "User is already a member"
                    else:
                        # Reactivate
                        member["status"] = "active"
                        member["role"] = role
                        member["joined_at"] = datetime.now().isoformat()
                        _save_teams(teams)
                        return True, "Member reactivated"

            team["members"].append({
                "username": username,
                "role": role,
                "joined_at": datetime.now().isoformat(),
                "status": "active",
            })
            _save_teams(teams)
            logger.info("Member added: %s -> team %s (role=%s)", username, team_id, role)
            return True, "Member added successfully"

    return False, "Team not found"


def remove_member(team_id: str, username: str, removed_by: str) -> tuple[bool, str]:
    """
    Remove a member from a team (soft delete).

    Args:
        team_id: Team ID
        username: Member to remove
        removed_by: Username of the person removing (must have manage_members permission)

    Returns:
        (success, message) tuple
    """
    teams = _load_teams()
    for team in teams:
        if team["id"] == team_id:
            # Check permissions
            remover_role = None
            for m in team["members"]:
                if m["username"] == removed_by and m["status"] == "active":
                    remover_role = m["role"]
            if not remover_role or not has_permission(remover_role, "manage_members"):
                return False, "Insufficient permissions"

            # Can't remove owner
            if username == team["owner"]:
                return False, "Cannot remove team owner"

            for member in team["members"]:
                if member["username"] == username:
                    member["status"] = "removed"
                    member["removed_at"] = datetime.now().isoformat()
                    member["removed_by"] = removed_by
                    _save_teams(teams)
                    logger.info("Member removed: %s from team %s (by %s)", username, team_id, removed_by)
                    return True, "Member removed"

            return False, "Member not found"

    return False, "Team not found"


def change_member_role(team_id: str, username: str, new_role: str, changed_by: str) -> tuple[bool, str]:
    """
    Change a member's role.

    Args:
        team_id: Team ID
        username: Member whose role to change
        new_role: New role to assign
        changed_by: Username of the person making the change

    Returns:
        (success, message) tuple
    """
    if new_role not in ROLES:
        return False, f"Invalid role: {new_role}"
    if new_role == "owner":
        return False, "Cannot assign owner role (use transfer_ownership)"

    teams = _load_teams()
    for team in teams:
        if team["id"] == team_id:
            changer_role = None
            for m in team["members"]:
                if m["username"] == changed_by and m["status"] == "active":
                    changer_role = m["role"]
            if not changer_role or not has_permission(changer_role, "manage_members"):
                return False, "Insufficient permissions"

            for member in team["members"]:
                if member["username"] == username and member["status"] == "active":
                    member["role"] = new_role
                    _save_teams(teams)
                    logger.info("Role changed: %s -> %s in team %s", username, new_role, team_id)
                    return True, f"Role changed to {new_role}"

            return False, "Member not found"

    return False, "Team not found"


# ---------------------------------------------------------------------------
# Invitation system
# ---------------------------------------------------------------------------

def _load_invites() -> list[dict]:
    return load_json(_INVITES_FILE, default=[])


def _save_invites(invites: list[dict]) -> None:
    save_json(_INVITES_FILE, invites)


def create_invite(team_id: str, invited_by: str, role: str = "member", email: str = "") -> tuple[bool, str, str]:
    """
    Create an invitation to join a team.

    Args:
        team_id: Team to invite to
        invited_by: Username creating the invite
        role: Role for the invitee
        email: Optional email to send invite to

    Returns:
        (success, message, invite_code) tuple
    """
    team = get_team(team_id)
    if not team:
        return False, "Team not found", ""

    # Check inviter's permission
    inviter_role = get_user_role(invited_by, team_id)
    if not inviter_role or not has_permission(inviter_role, "manage_members"):
        return False, "Insufficient permissions", ""

    invite_code = secrets.token_urlsafe(16)
    invites = _load_invites()
    invites.append({
        "code": invite_code,
        "team_id": team_id,
        "team_name": team["name"],
        "invited_by": invited_by,
        "role": role,
        "email": email,
        "created_at": datetime.now().isoformat(),
        "used": False,
        "used_by": None,
    })
    _save_invites(invites)

    logger.info("Invite created for team %s (by %s, code=%s)", team_id, invited_by, invite_code[:6])
    return True, "Invite created", invite_code


def accept_invite(invite_code: str, username: str) -> tuple[bool, str]:
    """
    Accept a team invitation.

    Args:
        invite_code: The invitation code
        username: The user accepting

    Returns:
        (success, message) tuple
    """
    invites = _load_invites()
    for invite in invites:
        if invite["code"] == invite_code and not invite["used"]:
            team_id = invite["team_id"]
            role = invite["role"]

            # Add member to team
            ok, msg = add_member(team_id, username, role)
            if ok:
                invite["used"] = True
                invite["used_by"] = username
                invite["used_at"] = datetime.now().isoformat()
                _save_invites(invites)
                logger.info("Invite accepted: %s joined team %s", username, team_id)
                return True, f"You've joined team '{invite['team_name']}' as {role}"
            return False, msg

    return False, "Invalid or expired invitation code"


# ---------------------------------------------------------------------------
# Customer pool management
# ---------------------------------------------------------------------------

def assign_customer(team_id: str, customer_id: str, assigned_to: str, assigned_by: str) -> tuple[bool, str]:
    """
    Assign a customer from the public pool to a team member.

    Args:
        team_id: Team ID
        customer_id: Customer record ID to assign
        assigned_to: Username to assign to
        assigned_by: Username making the assignment

    Returns:
        (success, message) tuple
    """
    # Verify permissions
    assigner_role = get_user_role(assigned_by, team_id)
    if not assigner_role or not has_permission(assigner_role, "assign_customers"):
        return False, "Insufficient permissions"

    # Store assignment in team's assignment ledger
    ledger_file = f"team_{team_id}_assignments.json"
    assignments = load_json(ledger_file, default=[])

    # Check if already assigned
    for a in assignments:
        if a["customer_id"] == customer_id and a["status"] == "active":
            if a["assigned_to"] == assigned_to:
                return False, "Already assigned to this member"
            # Reassign
            a["status"] = "reassigned"
            a["reassigned_at"] = datetime.now().isoformat()

    assignments.append({
        "customer_id": customer_id,
        "assigned_to": assigned_to,
        "assigned_by": assigned_by,
        "assigned_at": datetime.now().isoformat(),
        "status": "active",
    })
    save_json(ledger_file, assignments)
    logger.info("Customer %s assigned to %s (team=%s)", customer_id, assigned_to, team_id)
    return True, f"Customer assigned to {assigned_to}"


def get_member_assignments(team_id: str, username: str) -> list[dict]:
    """Get all active customer assignments for a team member."""
    ledger_file = f"team_{team_id}_assignments.json"
    assignments = load_json(ledger_file, default=[])
    return [a for a in assignments if a["assigned_to"] == username and a["status"] == "active"]


def get_public_pool(team_id: str) -> list[str]:
    """
    Get customer IDs that are in the public pool (unassigned).

    Returns list of customer_id strings that no one is actively assigned to.
    """
    ledger_file = f"team_{team_id}_assignments.json"
    assignments = load_json(ledger_file, default=[])
    assigned_ids = {a["customer_id"] for a in assignments if a["status"] == "active"}

    # Get all team customers (from team's shared customer list)
    team_customers_file = f"team_{team_id}_customers.json"
    all_customers = load_json(team_customers_file, default=[])
    all_ids = {c.get("id", str(i)) for i, c in enumerate(all_customers)}

    return list(all_ids - assigned_ids)


def reclaim_inactive_customers(team_id: str) -> int:
    """
    Reclaim customers that haven't been contacted within the team's auto_reclaim_days.

    Moves them back to the public pool.

    Returns:
        Number of customers reclaimed
    """
    team = get_team(team_id)
    if not team:
        return 0

    auto_reclaim_days = team.get("settings", {}).get("auto_reclaim_days", 30)
    from datetime import timedelta
    cutoff = (datetime.now() - timedelta(days=auto_reclaim_days)).isoformat()

    ledger_file = f"team_{team_id}_assignments.json"
    assignments = load_json(ledger_file, default=[])

    reclaimed = 0
    for a in assignments:
        if a["status"] == "active" and a.get("assigned_at", "") < cutoff:
            # Check if there's been recent activity (simplified: check assignment date)
            a["status"] = "reclaimed"
            a["reclaimed_at"] = datetime.now().isoformat()
            reclaimed += 1

    if reclaimed > 0:
        save_json(ledger_file, assignments)
        logger.info("Reclaimed %d customers in team %s", reclaimed, team_id)

    return reclaimed


# ---------------------------------------------------------------------------
# Team stats
# ---------------------------------------------------------------------------

def get_team_stats(team_id: str) -> dict:
    """
    Get team performance statistics.

    Returns:
        Dict with member count, assignment stats, etc.
    """
    team = get_team(team_id)
    if not team:
        return {}

    members = [m for m in team.get("members", []) if m.get("status") == "active"]
    ledger_file = f"team_{team_id}_assignments.json"
    assignments = load_json(ledger_file, default=[])
    active_assignments = [a for a in assignments if a["status"] == "active"]

    # Per-member stats
    member_stats = {}
    for m in members:
        username = m["username"]
        member_assignments = [a for a in active_assignments if a["assigned_to"] == username]
        member_stats[username] = {
            "role": m["role"],
            "assigned_customers": len(member_assignments),
            "joined_at": m.get("joined_at", ""),
        }

    return {
        "team_id": team_id,
        "team_name": team["name"],
        "total_members": len(members),
        "max_seats": team.get("max_seats", 5),
        "total_assignments": len(active_assignments),
        "public_pool_size": len(get_public_pool(team_id)),
        "member_stats": member_stats,
    }
