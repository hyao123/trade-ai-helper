"""
utils/conversation.py
---------------------
Multi-turn conversation support for AI chat-like refinement.

Maintains a conversation history (list of {role, content} dicts) in
st.session_state under a given key. Allows users to continue editing
their AI-generated result through follow-up instructions.

Usage:
    conv = Conversation("email_conv")
    conv.add_user("Generate a cold email for LED lights")
    conv.add_assistant(ai_result)
    # User follows up:
    conv.add_user("Make it shorter and more casual")
    messages = conv.get_messages()  # → pass to stream_llm / call_llm
"""
from __future__ import annotations

import streamlit as st

from utils.logger import get_logger

logger = get_logger("conversation")

_MAX_TURNS = 10  # Max conversation turns to keep in memory


class Conversation:
    """
    Wraps a multi-turn conversation stored in st.session_state.

    Each instance is keyed by `conv_key` so multiple pages can maintain
    independent conversation threads.
    """

    def __init__(self, conv_key: str, system_prompt: str | None = None) -> None:
        self._key = f"_conv_{conv_key}"
        if self._key not in st.session_state:
            st.session_state[self._key] = []
            if system_prompt:
                st.session_state[self._key].append({
                    "role": "system",
                    "content": system_prompt,
                })

    def add_user(self, content: str) -> None:
        """Append a user message."""
        st.session_state[self._key].append({"role": "user", "content": content})
        self._trim()

    def add_assistant(self, content: str) -> None:
        """Append an assistant message."""
        st.session_state[self._key].append({"role": "assistant", "content": content})
        self._trim()

    def get_messages(self) -> list[dict]:
        """Return the full conversation history for the LLM."""
        return list(st.session_state[self._key])

    def get_last_assistant(self) -> str:
        """Return the last assistant message, or empty string."""
        for msg in reversed(st.session_state[self._key]):
            if msg["role"] == "assistant":
                return msg["content"]
        return ""

    def turn_count(self) -> int:
        """Number of user turns so far."""
        return sum(1 for m in st.session_state[self._key] if m["role"] == "user")

    def is_empty(self) -> bool:
        user_msgs = [m for m in st.session_state[self._key] if m["role"] == "user"]
        return len(user_msgs) == 0

    def clear(self, keep_system: bool = True) -> None:
        """Reset conversation. Optionally keep the system message."""
        msgs = st.session_state[self._key]
        if keep_system:
            system = [m for m in msgs if m["role"] == "system"]
            st.session_state[self._key] = system
        else:
            st.session_state[self._key] = []

    def _trim(self) -> None:
        """Keep conversation within _MAX_TURNS to avoid token overflow."""
        msgs = st.session_state[self._key]
        # Keep system message + last (MAX_TURNS * 2) messages
        system = [m for m in msgs if m["role"] == "system"]
        non_system = [m for m in msgs if m["role"] != "system"]
        max_non_system = _MAX_TURNS * 2
        if len(non_system) > max_non_system:
            non_system = non_system[-max_non_system:]
        st.session_state[self._key] = system + non_system

    def render_history(self, max_display: int = 6) -> None:
        """
        Render conversation history as a compact chat timeline.
        Shows last `max_display` messages.
        """
        msgs = [m for m in st.session_state[self._key] if m["role"] != "system"]
        if not msgs:
            return

        display_msgs = msgs[-max_display:]
        for msg in display_msgs:
            role = msg["role"]
            content = msg["content"]
            preview = content[:300] + ("…" if len(content) > 300 else "")
            if role == "user":
                st.markdown(
                    f'<div style="background:#eff6ff;border-left:3px solid #3b82f6;'
                    f'padding:0.6rem 0.9rem;border-radius:6px;margin:0.4rem 0;'
                    f'font-size:0.88rem;"><b>👤 你</b><br>{preview}</div>',
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    f'<div style="background:#f0fdf4;border-left:3px solid #22c55e;'
                    f'padding:0.6rem 0.9rem;border-radius:6px;margin:0.4rem 0;'
                    f'font-size:0.88rem;"><b>🤖 AI</b><br>{preview}</div>',
                    unsafe_allow_html=True,
                )


# ---------------------------------------------------------------------------
# Convenience: stream with conversation context
# ---------------------------------------------------------------------------
def stream_with_context(
    conv: Conversation,
    follow_up: str,
    system_prompt: str | None = None,
    user_id: str = "default",
) -> object:
    """
    Add the follow-up to the conversation and stream a response.

    Returns a generator (same as stream_llm).
    """
    from utils.ai_client import stream_llm  # local import to avoid circular
    from utils.user_prefs import get_ai_style_suffix

    suffix = get_ai_style_suffix()
    full_followup = follow_up + suffix if suffix else follow_up
    conv.add_user(full_followup)

    messages = conv.get_messages()
    # Build prompt from messages for the non-chat API
    # Combine into a single prompt string with context
    context_parts = []
    for msg in messages:
        if msg["role"] == "system":
            continue  # system already passed separately
        role_label = "User" if msg["role"] == "user" else "Assistant"
        context_parts.append(f"{role_label}: {msg['content']}")
    prompt = "\n\n".join(context_parts)

    # Extract system from messages
    sys_msgs = [m["content"] for m in messages if m["role"] == "system"]
    effective_system = sys_msgs[0] if sys_msgs else system_prompt

    logger.info("stream_with_context: turn=%d user_id=%s", conv.turn_count(), user_id)
    return stream_llm(prompt, effective_system, user_id)
