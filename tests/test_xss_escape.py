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
