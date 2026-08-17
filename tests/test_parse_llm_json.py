"""Tests for the shared parse_llm_json helper."""
from __future__ import annotations

from utils.sanitize import parse_llm_json


def test_parse_plain_json():
    assert parse_llm_json('{"a": 1}') == {"a": 1}


def test_parse_markdown_fenced_json():
    text = '```json\n{"a": 1, "b": [2]}\n```'
    assert parse_llm_json(text) == {"a": 1, "b": [2]}


def test_parse_fenced_with_language_specifics():
    # Our prompt asks for JSON without a language tag; also handle the plain ``` case.
    assert parse_llm_json('```\n{"ok": true}\n```') == {"ok": True}


def test_parse_invalid_returns_none():
    assert parse_llm_json("not json {{{") is None
    assert parse_llm_json("") is None
    assert parse_llm_json("[]") is None  # list, not dict


def test_parse_plain_json_with_ying_prefix_returns_none():
    # A ⚠️ error string from call_llm is not valid plan JSON.
    assert parse_llm_json("⚠️ 调用频率超限，请稍后再试") is None
