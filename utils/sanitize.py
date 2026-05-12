"""
utils/sanitize.py
-----------------
Basic prompt injection protection.
Sanitizes user inputs before they are interpolated into AI prompts.
"""
from __future__ import annotations

import re

# ---------------------------------------------------------------------------
# Compiled regex for prompt injection patterns (case-insensitive).
# Only specific multi-word injection phrases are matched.
# ---------------------------------------------------------------------------
_INJECTION_PATTERNS = re.compile(
    r"|".join([
        # Instruction override patterns
        r"ignore\s+previous\s+instructions",
        r"ignore\s+all\s+previous",
        r"ignore\s+above",
        r"ignore\s+the\s+above",
        r"disregard\s+previous",
        r"disregard\s+above",
        # Role switching
        r"you\s+are\s+now",
        r"you're\s+now",
        r"act\s+as",
        r"pretend\s+to\s+be",
        # System/role markers
        r"system:",
        r"###\s*System:",
        r"###\s*Human:",
        r"###\s*Assistant:",
        r"<\|system\|>",
        r"<\|user\|>",
        r"<\|assistant\|>",
        # Instruction tokens
        r"\[INST\]",
        r"\[/INST\]",
        r"<<SYS>>",
        r"<</SYS>>",
        # Override commands
        r"new\s+instructions:",
        r"override:",
        r"jailbreak",
        # Forget patterns
        r"forget\s+everything",
        r"forget\s+your\s+instructions",
        r"forget\s+all",
        # Other injection patterns
        r"do\s+not\s+follow",
        r"do\s+anything\s+now",
        r"DAN\s+mode",
    ]),
    re.IGNORECASE,
)


def sanitize_input(text: str, max_length: int = 2000) -> str:
    """Sanitize longer-form user input (e.g., inquiry text).

    - Strip leading/trailing whitespace
    - Remove null bytes and control characters (except newlines and tabs)
    - Detect and neutralize prompt injection patterns (replace with [FILTERED])
    - Truncate to max_length
    """
    if not text:
        return ""

    # Strip whitespace
    text = text.strip()

    # Remove null bytes and control characters (keep newlines \n, \r, tabs \t)
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)

    # Neutralize prompt injection patterns
    text = _INJECTION_PATTERNS.sub("[FILTERED]", text)

    # Truncate to max_length
    if len(text) > max_length:
        text = text[:max_length]

    return text


def sanitize_prompt_param(text: str, param_name: str = "", max_length: int = 500) -> str:
    """Sanitize shorter form parameters (product names, customer names, etc.).

    Same as sanitize_input but with stricter max_length default.
    """
    return sanitize_input(text, max_length=max_length)
