"""Tests for immediate per-send outreach result persistence."""
from __future__ import annotations

from unittest.mock import Mock, patch


def test_run_campaign_step_persists_after_every_send():
    """Each send (success or failure) must persist immediately."""
    from utils.auto_outreach import run_campaign_step

    db_mock = Mock()
    
    def load_side_effect(username, collection, default):
        if "campaigns" in collection:
            return [{"id": "c1", "name": "Test", "prospects": [{"email": "a@test.com"}, {"email": "b@test.com"}], "status": "pending", "stats": {}}]
        return []
    
    db_mock.load_user_data.side_effect = load_side_effect
    campaign_results = []

    def capture_save(username, collection, data):
        if "campaign_results" in collection:
            campaign_results.append(len(data))

    db_mock.save_user_data.side_effect = capture_save

    with patch("utils.repositories.get_db", return_value=db_mock), \
         patch("utils.email_service.send_ai_generated_email", return_value=(True, "OK")), \
         patch("utils.auto_outreach.generate_outreach_email", return_value={"subject": "S", "body": "B", "error": "", "matched_products": []}), \
         patch("utils.auto_outreach.time.sleep"):
        steps = list(run_campaign_step("user1", "c1", user_id="test", send_interval=0.0))

    assert len(steps) == 2
    assert all(s["status"] == "sent" for s in steps)
    # Each send triggers immediate save
    assert len(campaign_results) == 2
    assert campaign_results == [1, 2]


def test_run_campaign_step_skips_already_sent_emails():
    """Resume must skip records with status 'sent'."""
    from utils.auto_outreach import run_campaign_step

    db_mock = Mock()
    db_mock.load_user_data.side_effect = lambda user, coll, default: (
        [{"id": "c1", "name": "Resume", "prospects": [{"email": "a@test.com"}, {"email": "b@test.com"}], "status": "pending", "stats": {}}]
        if "campaigns" in coll else
        [{"email": "a@test.com", "status": "sent", "timestamp": "2026-01-01T00:00:00"}]
    )

    with patch("utils.repositories.get_db", return_value=db_mock), \
         patch("utils.email_service.send_ai_generated_email", return_value=(True, "OK")), \
         patch("utils.auto_outreach.generate_outreach_email", return_value={"subject": "S", "body": "B", "error": "", "matched_products": []}), \
         patch("utils.auto_outreach.time.sleep"):
        steps = list(run_campaign_step("user1", "c1", user_id="test", send_interval=0.0))

    assert len(steps) == 2
    assert steps[0]["status"] == "skipped"
    assert steps[1]["status"] == "sent"
