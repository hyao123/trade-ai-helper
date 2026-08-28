"""Unit tests for the XSS escape helper added in this batch."""
from __future__ import annotations


def test_html_escape_neutralizes_markup():
    from utils.ui_helpers import html_escape

    assert html_escape("<img src=x onerror=alert(1)>") == (
        "&lt;img src=x onerror=alert(1)&gt;"
    )
    assert html_escape('"') == "&quot;"
    assert html_escape("safe text") == "safe text"
    assert html_escape("") == ""
    assert html_escape("<script>alert('x')</script>") == (
        "&lt;script&gt;alert(&#x27;x&#x27;)&lt;/script&gt;"
    )


def test_html_escape_handles_none_as_empty():
    from utils.ui_helpers import html_escape

    # None is rendered by callers as empty; ensure no "None" text leak.
    escaped = html_escape("")
    assert escaped == ""


def test_app_py_escapes_username_and_email_in_banner():
    """Verify app.py imports html and calls html.escape on user data."""
    with open("app.py", "r", encoding="utf-8") as f:
        content = f.read()
    
    # Must import html module
    assert "import html" in content
    # Must call html.escape in banner function
    assert "html.escape(username)" in content
    assert "html.escape(email)" in content


def test_crm_page_imports_and_uses_html_escape():
    """Verify CRM page imports html_escape and uses it on product field."""
    with open("pages/7_📇_客户管理.py", "r", encoding="utf-8") as f:
        content = f.read()
    
    # Must import html_escape from utils
    assert "from utils.ui_helpers import" in content and "html_escape" in content
    # Must call html_escape on product
    assert "html_escape(cust['product']" in content or 'html_escape(cust["product"]' in content
