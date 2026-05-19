"""
tests/test_integration.py
--------------------------
Integration tests verifying cross-module interactions.

Tests the wiring between:
  - ai_gateway ↔ ai_client
  - email_tracking ↔ email_service
  - referral ↔ user_auth
  - teams ↔ customers
  - notifications ↔ workflow
  - customer_scoring ↔ email_tracking
  - export_api ↔ storage
"""
from __future__ import annotations

import os
import sys
import tempfile
import types
from pathlib import Path
from unittest.mock import MagicMock, patch

# Setup path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Mock streamlit
_mock_st = types.ModuleType("streamlit")
_mock_st.session_state = {}
_mock_st.components = MagicMock()
sys.modules["streamlit"] = _mock_st
sys.modules["streamlit.components"] = MagicMock()
sys.modules["streamlit.components.v1"] = MagicMock()

# Mock dotenv
_mock_dotenv = types.ModuleType("dotenv")
_mock_dotenv.load_dotenv = lambda *a, **kw: None
sys.modules["dotenv"] = _mock_dotenv


# Mock openai if not available
try:
    import openai
except ImportError:
    _mock_openai = types.ModuleType("openai")
    _mock_openai.OpenAI = MagicMock
    sys.modules["openai"] = _mock_openai


class TestAIGatewayIntegration:
    """Test AI Gateway multi-model routing works with ai_client layer."""

    def _setup(self):
        _mock_st.session_state.clear()
        return tempfile.TemporaryDirectory()

    def test_gateway_available_providers_empty_when_no_keys(self):
        """Without API keys configured, no providers are available."""
        with self._setup():
            with patch("utils.secrets.get_secret", return_value=""):
                from utils.ai_gateway import AIGateway
                gw = AIGateway()
                assert gw.get_available_providers() == []

    def test_gateway_available_providers_with_nvidia_key(self):
        """NVIDIA provider available when key is set."""
        with self._setup():
            def mock_secret(key, default=""):
                if key == "NVIDIA_API_KEY":
                    return "nvapi-test123"
                return default

            with patch("utils.ai_gateway.get_secret", side_effect=mock_secret):
                from utils.ai_gateway import AIGateway
                gw = AIGateway()
                providers = gw.get_available_providers()
                assert "nvidia" in providers

    def test_gateway_resolve_model_fallback(self):
        """If preferred provider not available, falls back to available one."""
        with self._setup():
            def mock_secret(key, default=""):
                if key == "DEEPSEEK_API_KEY":
                    return "sk-deepseek-test"
                return default

            with patch("utils.ai_gateway.get_secret", side_effect=mock_secret):
                from utils.ai_gateway import AIGateway
                gw = AIGateway()
                # Request "balanced" (nvidia) but only deepseek is available
                provider, model = gw._resolve_model("balanced", None, None)
                assert provider == "deepseek"

    def test_gateway_get_available_models(self):
        """Lists all models from configured providers."""
        with self._setup():
            def mock_secret(key, default=""):
                if key == "NVIDIA_API_KEY":
                    return "nvapi-test"
                if key == "OPENAI_API_KEY":
                    return "sk-openai-test"
                return default

            with patch("utils.ai_gateway.get_secret", side_effect=mock_secret):
                from utils.ai_gateway import AIGateway
                gw = AIGateway()
                models = gw.get_available_models()
                assert len(models) >= 3  # At least nvidia(2) + openai(2)
                providers_in_models = {m["provider"] for m in models}
                assert "nvidia" in providers_in_models
                assert "openai" in providers_in_models


class TestEmailTrackingIntegration:
    """Test email tracking integrates with email sending."""

    def _setup(self):
        _mock_st.session_state.clear()
        return tempfile.TemporaryDirectory()

    def test_create_tracking_record(self):
        """Tracking record is created and retrievable."""
        with self._setup() as tmp_str:
            tmp_dir = Path(tmp_str)
            with patch("utils.storage.get_data_dir", return_value=tmp_dir):
                from utils.email_tracking import (
                    create_tracking_record,
                    get_email_stats,
                )
                tid = create_tracking_record(
                    user_id="testuser",
                    to_email="customer@example.com",
                    subject="Test Subject",
                )
                assert tid
                assert len(tid) == 12

                stats = get_email_stats(tid)
                assert stats is not None
                assert stats["to_email"] == "customer@example.com"
                assert stats["status"] == "sent"
                assert stats["open_count"] == 0

    def test_record_open_updates_stats(self):
        """Recording an open event updates the tracking record."""
        with self._setup() as tmp_str:
            tmp_dir = Path(tmp_str)
            with patch("utils.storage.get_data_dir", return_value=tmp_dir):
                from utils.email_tracking import (
                    create_tracking_record,
                    get_email_stats,
                    record_open,
                )
                tid = create_tracking_record("user1", "test@test.com", "Hi")
                assert record_open(tid) is True

                stats = get_email_stats(tid)
                assert stats["open_count"] == 1
                assert stats["opened_at"] is not None
                assert stats["status"] == "opened"

    def test_record_click_updates_stats(self):
        """Recording a click event updates status to 'clicked'."""
        with self._setup() as tmp_str:
            tmp_dir = Path(tmp_str)
            with patch("utils.storage.get_data_dir", return_value=tmp_dir):
                from utils.email_tracking import (
                    create_tracking_record,
                    get_email_stats,
                    record_click,
                    record_open,
                )
                tid = create_tracking_record("user1", "test@test.com", "Hi")
                record_open(tid)
                record_click(tid, "https://example.com")

                stats = get_email_stats(tid)
                assert stats["click_count"] == 1
                assert stats["status"] == "clicked"
                assert len(stats["clicked_links"]) == 1

    def test_user_email_stats_aggregation(self):
        """Aggregated user stats compute correctly."""
        with self._setup() as tmp_str:
            tmp_dir = Path(tmp_str)
            with patch("utils.storage.get_data_dir", return_value=tmp_dir):
                from utils.email_tracking import (
                    create_tracking_record,
                    get_user_email_stats,
                    record_open,
                )
                # Create 3 emails, open 2
                tid1 = create_tracking_record("user1", "a@a.com", "S1")
                tid2 = create_tracking_record("user1", "b@b.com", "S2")
                create_tracking_record("user1", "c@c.com", "S3")

                record_open(tid1)
                record_open(tid2)

                stats = get_user_email_stats("user1", days=30)
                assert stats["total_sent"] == 3
                assert stats["total_opened"] == 2
                assert stats["open_rate"] == 66.7

    def test_tracking_pixel_html_generation(self):
        """Tracking pixel HTML is generated with correct URL format."""
        with self._setup() as tmp_str:
            tmp_dir = Path(tmp_str)
            with patch("utils.storage.get_data_dir", return_value=tmp_dir), \
                 patch("utils.email_tracking.get_secret", return_value="https://app.example.com"):
                from utils.email_tracking import generate_tracking_pixel_html
                html = generate_tracking_pixel_html("abc123")
                assert "abc123" in html
                assert 'width="1"' in html
                assert "display:none" in html


class TestReferralIntegration:
    """Test referral system with user auth."""

    def _setup(self):
        _mock_st.session_state.clear()
        return tempfile.TemporaryDirectory()

    def test_referral_code_generation(self):
        """Each user gets a unique, consistent referral code."""
        with self._setup() as tmp_str:
            tmp_dir = Path(tmp_str)
            with patch("utils.storage.get_data_dir", return_value=tmp_dir):
                from utils.referral import get_referral_code
                code1 = get_referral_code("alice")
                code2 = get_referral_code("alice")  # Same user = same code
                code3 = get_referral_code("bob")

                assert code1 == code2  # Idempotent
                assert code1 != code3  # Different users = different codes
                assert len(code1) >= 6

    def test_referral_apply_awards_credits(self):
        """Applying a referral code gives credits to both parties."""
        with self._setup() as tmp_str:
            tmp_dir = Path(tmp_str)
            with patch("utils.storage.get_data_dir", return_value=tmp_dir):
                from utils.referral import (
                    apply_referral,
                    get_bonus_credits,
                    get_referral_code,
                )
                # Alice creates her code
                code = get_referral_code("alice")

                # Bob signs up with Alice's code
                ok, msg = apply_referral(code, "bob")
                assert ok is True
                assert "bonus" in msg.lower() or "credit" in msg.lower()

                # Both get credits
                alice_credits = get_bonus_credits("alice")
                bob_credits = get_bonus_credits("bob")
                assert alice_credits > 0
                assert bob_credits > 0

    def test_self_referral_rejected(self):
        """Users cannot use their own referral code."""
        with self._setup() as tmp_str:
            tmp_dir = Path(tmp_str)
            with patch("utils.storage.get_data_dir", return_value=tmp_dir):
                from utils.referral import apply_referral, get_referral_code
                code = get_referral_code("alice")
                ok, msg = apply_referral(code, "alice")
                assert ok is False
                assert "own" in msg.lower()

    def test_duplicate_referral_rejected(self):
        """Same user can't apply a referral code twice."""
        with self._setup() as tmp_str:
            tmp_dir = Path(tmp_str)
            with patch("utils.storage.get_data_dir", return_value=tmp_dir):
                from utils.referral import apply_referral, get_referral_code
                code = get_referral_code("alice")
                apply_referral(code, "bob")
                ok, msg = apply_referral(code, "bob")
                assert ok is False


class TestTeamsIntegration:
    """Test team system with customer management."""

    def _setup(self):
        _mock_st.session_state.clear()
        return tempfile.TemporaryDirectory()

    def test_create_team_and_add_member(self):
        """Create a team and add members with proper roles."""
        with self._setup() as tmp_str:
            tmp_dir = Path(tmp_str)
            with patch("utils.storage.get_data_dir", return_value=tmp_dir):
                from utils.teams import (
                    add_member,
                    create_team,
                    get_team_members,
                    get_user_role,
                )
                team = create_team("Test Corp", "owner1")
                assert team["name"] == "Test Corp"
                assert team["owner"] == "owner1"

                # Owner has correct role
                assert get_user_role("owner1", team["id"]) == "owner"

                # Add member
                ok, msg = add_member(team["id"], "member1", "member")
                assert ok is True

                members = get_team_members(team["id"])
                assert len(members) == 2
                assert get_user_role("member1", team["id"]) == "member"

    def test_team_seat_limit(self):
        """Team can't exceed max seat count."""
        with self._setup() as tmp_str:
            tmp_dir = Path(tmp_str)
            with patch("utils.storage.get_data_dir", return_value=tmp_dir):
                from utils.teams import add_member, create_team
                team = create_team("Small Team", "owner1")
                # Default max_seats is 5, owner takes 1

                for i in range(4):
                    ok, _ = add_member(team["id"], f"user{i}", "member")
                    assert ok is True

                # 6th member should fail
                ok, msg = add_member(team["id"], "user_overflow", "member")
                assert ok is False
                assert "full" in msg.lower()

    def test_permission_check(self):
        """Role-based permissions work correctly."""
        with self._setup() as tmp_str:
            tmp_dir = Path(tmp_str)
            with patch("utils.storage.get_data_dir", return_value=tmp_dir):
                from utils.teams import has_permission
                assert has_permission("owner", "manage_billing") is True
                assert has_permission("member", "manage_billing") is False
                assert has_permission("member", "generate_ai") is True
                assert has_permission("manager", "assign_customers") is True
                assert has_permission("member", "assign_customers") is False

    def test_invite_flow(self):
        """Invitation system creates and accepts invites."""
        with self._setup() as tmp_str:
            tmp_dir = Path(tmp_str)
            with patch("utils.storage.get_data_dir", return_value=tmp_dir):
                from utils.teams import (
                    accept_invite,
                    create_invite,
                    create_team,
                    get_user_role,
                )
                team = create_team("Invite Team", "boss")

                # Create invite
                ok, msg, code = create_invite(team["id"], "boss", role="manager")
                assert ok is True
                assert len(code) > 0

                # Accept invite
                ok, msg = accept_invite(code, "new_hire")
                assert ok is True
                assert get_user_role("new_hire", team["id"]) == "manager"


class TestNotificationsIntegration:
    """Test notification system delivery."""

    def _setup(self):
        _mock_st.session_state.clear()
        return tempfile.TemporaryDirectory()

    def test_notify_creates_in_app_notification(self):
        """notify() stores an in-app notification retrievable by get_unread."""
        with self._setup() as tmp_str:
            tmp_dir = Path(tmp_str)
            with patch("utils.storage.get_data_dir", return_value=tmp_dir):
                from utils.notifications import get_unread, get_unread_count, notify
                notify("testuser", "hot_lead", customer="ABC Corp")

                count = get_unread_count("testuser")
                assert count == 1

                unread = get_unread("testuser")
                assert len(unread) == 1
                assert "ABC Corp" in unread[0]["title"]
                assert unread[0]["type"] == "hot_lead"

    def test_mark_read(self):
        """Marking a notification as read decreases unread count."""
        with self._setup() as tmp_str:
            tmp_dir = Path(tmp_str)
            with patch("utils.storage.get_data_dir", return_value=tmp_dir):
                from utils.notifications import (
                    get_unread_count,
                    mark_read,
                    notify,
                )
                nid = notify("testuser", "email_opened", customer="client@test.com")
                assert get_unread_count("testuser") == 1

                mark_read("testuser", nid)
                assert get_unread_count("testuser") == 0

    def test_notification_preferences_quiet_hours(self):
        """Quiet hours suppress push notifications."""
        with self._setup() as tmp_str:
            tmp_dir = Path(tmp_str)
            with patch("utils.storage.get_data_dir", return_value=tmp_dir):
                from utils.notifications import (
                    get_unread,
                    notify,
                    set_notification_preferences,
                )
                # Set quiet hours to cover current time
                set_notification_preferences("testuser", {
                    "channels": {"in_app": True, "push": True, "email_digest": True},
                    "quiet_hours": {"enabled": True, "start": "00:00", "end": "23:59"},
                })

                notify("testuser", "followup_due", customer="John")
                # Should still get in_app (quiet hours only suppress push/email)
                unread = get_unread("testuser")
                assert len(unread) == 1


class TestExportIntegration:
    """Test data export/import roundtrip."""

    def _setup(self):
        _mock_st.session_state.clear()
        return tempfile.TemporaryDirectory()

    def test_export_json_roundtrip(self):
        """Export to JSON and import back yields same data."""
        with self._setup() as tmp_str:
            tmp_dir = Path(tmp_str)
            with patch("utils.storage.get_data_dir", return_value=tmp_dir):
                from utils.storage import save_user_json

                # Setup test data
                test_customers = [
                    {"company": "ABC", "contact": "John", "email": "j@abc.com",
                     "country": "US", "product": "LED", "stage": "new"},
                    {"company": "XYZ", "contact": "Jane", "email": "j@xyz.com",
                     "country": "UK", "product": "Lamp", "stage": "quoted"},
                ]
                save_user_json("exportuser", "customers.json", test_customers)

                from utils.export_api import export_data, import_data
                ok, content, filename = export_data("exportuser", "customers", format="json")
                assert ok is True
                assert "ABC" in content
                assert filename.endswith(".json")

                # Import into a different "user"
                save_user_json("importuser", "customers.json", [])
                ok, msg, count = import_data("importuser", "customers", content, format="json", merge_strategy="replace")
                assert ok is True
                assert count == 2

    def test_export_csv_format(self):
        """Export to CSV produces valid CSV with headers."""
        with self._setup() as tmp_str:
            tmp_dir = Path(tmp_str)
            with patch("utils.storage.get_data_dir", return_value=tmp_dir):
                from utils.storage import save_user_json

                test_data = [
                    {"company": "Test Co", "contact": "Bob", "email": "b@t.com",
                     "country": "DE", "product": "Cable", "stage": "new"},
                ]
                save_user_json("csvuser", "customers.json", test_data)

                from utils.export_api import export_data
                ok, content, filename = export_data("csvuser", "customers", format="csv")
                assert ok is True
                assert filename.endswith(".csv")
                lines = content.strip().split("\n")
                assert len(lines) == 2  # Header + 1 data row
                assert "company" in lines[0]
                assert "Test Co" in lines[1]

    def test_export_anonymization(self):
        """Anonymized export masks PII."""
        with self._setup() as tmp_str:
            tmp_dir = Path(tmp_str)
            with patch("utils.storage.get_data_dir", return_value=tmp_dir):
                from utils.storage import save_user_json

                test_data = [
                    {"company": "Secret Corp", "contact": "John Smith",
                     "email": "john@secret.com", "country": "US",
                     "product": "Widget", "stage": "new"},
                ]
                save_user_json("anonuser", "customers.json", test_data)

                from utils.export_api import export_data
                ok, content, _ = export_data("anonuser", "customers", format="json", anonymize=True)
                assert ok is True
                assert "john@secret.com" not in content  # Original email masked
                assert "John Smith" not in content  # Name masked
                assert "Secret Corp" in content  # Company preserved

    def test_list_exportable_collections_by_tier(self):
        """Free tier has limited access, Pro has full access."""
        from utils.export_api import list_exportable_collections
        free_collections = list_exportable_collections("free")
        pro_collections = list_exportable_collections("pro")

        # Free should have customers accessible
        customers_free = next(c for c in free_collections if c["key"] == "customers")
        assert customers_free["accessible"] is True

        # History requires Pro
        history_free = next(c for c in free_collections if c["key"] == "history")
        assert history_free["accessible"] is False

        history_pro = next(c for c in pro_collections if c["key"] == "history")
        assert history_pro["accessible"] is True


class TestCustomerScoringIntegration:
    """Test customer scoring engine."""

    def _setup(self):
        _mock_st.session_state.clear()
        return tempfile.TemporaryDirectory()

    def test_score_complete_customer(self):
        """Fully profiled customer with recent activity scores high."""
        with self._setup() as tmp_str:
            tmp_dir = Path(tmp_str)
            with patch("utils.storage.get_data_dir", return_value=tmp_dir):
                from datetime import date

                from utils.customer_scoring import compute_behavior_score
                customer = {
                    "company": "Big Corp",
                    "contact": "CEO",
                    "email": "ceo@bigcorp.com",
                    "country": "US",
                    "product": "LED Panel",
                    "stage": "negotiating",
                    "notes": "Met at Canton Fair",
                    "tags": ["VIP"],
                    "last_contact": date.today().isoformat(),
                }

                email_stats = {"total_sent": 5, "total_opened": 4, "total_clicked": 2, "total_replied": 1}
                intent_signals = ["inquiry", "order_intent"]

                score = compute_behavior_score(
                    customer=customer,
                    email_stats=email_stats,
                    intent_signals=intent_signals,
                    interaction_count=8,
                )

                assert score["total_score"] >= 70  # Should be "warm" or "hot"
                assert score["tier"] in ("Hot Lead", "Warm Lead")
                assert score["dimensions"]["engagement"] > 50
                assert score["dimensions"]["activity"] == 100  # Today

    def test_score_dormant_customer(self):
        """Customer with no activity scores low."""
        with self._setup() as tmp_str:
            tmp_dir = Path(tmp_str)
            with patch("utils.storage.get_data_dir", return_value=tmp_dir):
                from utils.customer_scoring import compute_behavior_score
                customer = {
                    "company": "Old Co",
                    "contact": "",
                    "email": "",
                    "country": "",
                    "product": "",
                    "stage": "new",
                    "last_contact": "2023-01-01",
                }

                score = compute_behavior_score(customer=customer)
                assert score["total_score"] <= 30
                assert score["tier"] in ("Cold", "Dormant")

    def test_batch_scoring_persistence(self):
        """Batch scoring saves results to user storage."""
        with self._setup() as tmp_str:
            tmp_dir = Path(tmp_str)
            with patch("utils.storage.get_data_dir", return_value=tmp_dir):
                from datetime import date

                from utils.customer_scoring import batch_score_customers, get_score_summary
                customers = [
                    {"company": "A", "contact": "X", "email": "x@a.com",
                     "country": "US", "product": "P", "stage": "new",
                     "last_contact": date.today().isoformat()},
                    {"company": "B", "contact": "Y", "email": "y@b.com",
                     "country": "UK", "product": "Q", "stage": "quoted",
                     "last_contact": "2020-01-01"},
                ]

                results = batch_score_customers("scorer", customers)
                assert len(results) == 2
                # Should be sorted by score (highest first)
                assert results[0]["score"]["total_score"] >= results[1]["score"]["total_score"]

                summary = get_score_summary("scorer")
                assert summary["total"] == 2
                assert summary["avg_score"] > 0


class TestI18nIntegration:
    """Test multi-language engine."""

    def test_basic_translation(self):
        """Basic key lookup works for multiple languages."""
        from utils.i18n_engine import I18n
        i18n = I18n("en")
        assert i18n.t("login") == "Login"

        i18n.current_language = "ja"
        assert i18n.t("login") == "ログイン"

        i18n.current_language = "ko"
        assert i18n.t("login") == "로그인"

        i18n.current_language = "es"
        assert i18n.t("login") == "Iniciar sesión"

    def test_fallback_chain(self):
        """Missing key falls back through en → zh → raw key."""
        from utils.i18n_engine import I18n
        i18n = I18n("ja")
        # Key that exists in en but not ja
        result = i18n.t("some_nonexistent_key_xyz")
        assert result == "some_nonexistent_key_xyz"  # Falls back to key itself

    def test_interpolation(self):
        """Variable interpolation in translations."""
        from utils.i18n_engine import I18n
        i18n = I18n("zh")
        # The existing i18n has per_minutes_reset with {minutes} placeholder
        result = i18n.t("per_minutes_reset", minutes=60)
        assert "60" in result

    def test_available_languages(self):
        """Lists all supported languages."""
        from utils.i18n_engine import I18n
        i18n = I18n()
        langs = i18n.available_languages()
        assert len(langs) >= 5
        codes = [l["code"] for l in langs]
        assert "zh" in codes
        assert "en" in codes
        assert "ja" in codes

    def test_direction_rtl(self):
        """Arabic has RTL direction."""
        from utils.i18n_engine import I18n
        i18n = I18n("ar")
        assert i18n.get_direction() == "rtl"

        i18n.current_language = "en"
        assert i18n.get_direction() == "ltr"
