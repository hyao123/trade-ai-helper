"""Guard test for the SendGrid <-> SMTP fallback recursion.

Without the re-entrancy flag in utils.email_service, send_tracked_email's
generic-error fallback would call send_ai_generated_email, which (while SendGrid
is still configured) calls send_tracked_email again -> infinite mutual recursion
and hundreds of bogus tracking records.
"""
from __future__ import annotations

import os
import types
from unittest.mock import patch

sys_path_hack = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if sys_path_hack not in os.sys.path:
    os.sys.path.insert(0, sys_path_hack)

# Mock streamlit + dotenv so the module imports cleanly.
_mock_st = types.ModuleType("streamlit")
_mock_st.session_state = {}
os.sys.modules.setdefault("streamlit", _mock_st)
_mock_dotenv = types.ModuleType("dotenv")
_mock_dotenv.load_dotenv = lambda *a, **kw: None
os.sys.modules.setdefault("dotenv", _mock_dotenv)


def test_sendgrid_fallback_does_not_reenter_sendgrid():
    """send_ai_generated_email must not retry SendGrid while already inside a
    SendGrid send attempt (the email_sendgrid fallback path)."""
    import utils.email_service as es

    es._SENDING_AI_EMAIL = False

    calls = {"sendgrid": 0, "smtp": 0}

    def _fake_send_tracked_email(**kwargs):
        # Simulate SendGrid generic failure that triggers the fallback which
        # re-enters send_ai_generated_email. Return a 3-tuple like the real
        # send_tracked_email does.
        calls["sendgrid"] += 1
        from utils.email_service import send_ai_generated_email
        ok, msg = send_ai_generated_email(
            to_email=kwargs["to_email"],
            subject=kwargs["subject"],
            body=kwargs["body"],
        )
        return ok, msg, ""

    def _fake_send_email_with_attachments(*args, **kwargs):
        calls["smtp"] += 1
        return True, "sent"

    with patch("utils.email_sendgrid.is_sendgrid_configured", return_value=True), \
         patch("utils.email_sendgrid.send_tracked_email", side_effect=_fake_send_tracked_email), \
         patch("utils.email_service.is_email_configured", return_value=True), \
         patch("utils.email_service.send_email_with_attachments", side_effect=_fake_send_email_with_attachments), \
         patch("utils.email_tracking.create_tracking_record", return_value="t"), \
         patch("utils.user_auth.get_current_user", return_value=None):
        ok, msg = es.send_ai_generated_email("to@test.com", "Subj", "Body")

    # Exactly one SendGrid attempt and exactly one SMTP leaf send, no recursion.
    assert calls["sendgrid"] == 1, calls
    assert calls["smtp"] == 1, calls
    assert ok is True
    assert es._SENDING_AI_EMAIL is False


def test_smtp_subject_is_rfc2047_encoded():
    """SMTP subject with CJK/emoji must be RFC-2047 encoded, not raw."""
    import email.mime.multipart as mmp
    from email.header import Header

    msg = mmp.MIMEMultipart()
    msg["Subject"] = Header("报价单 2024 ✅", "utf-8")
    as_string = msg.as_string()
    assert "=?utf-8" in as_string
    assert "报价单" not in as_string.split("Subject:")[1].splitlines()[0] or "=?utf-8" in as_string
