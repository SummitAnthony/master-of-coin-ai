"""Conversational advisor over a loaded Facts object.

Like ``advisor()``, the LLM sees ONLY the Facts-derived context (plus the prior
turns and the question) — never the raw statement.
"""

from __future__ import annotations

from collections.abc import Sequence

from advisor.config import Settings, load_settings
from advisor.schema import Facts

from .client import SupportsGenerate
from .context import build_context
from .errors import LLMResponseError, MissingAPIKeyError
from .factory import get_llm_client
from .templates import DEFAULT_TEMPLATES, render_system

_CHAT_SYSTEM_SUFFIX = (
    " Answer the user's question using only the provided facts; never invent or recompute "
    "numbers. If the facts do not contain the answer, say so."
)


def _fallback_reply(question: str) -> str:
    return (
        "AI chat is unavailable in this run (offline / no provider configured). "
        "Please review the KPI scorecard, status flags, and anomalies for your question: "
        f"{question!r}"
    )


def answer_question(
    facts: Facts,
    history: Sequence[tuple[str, str]],
    question: str,
    *,
    client: SupportsGenerate | None = None,
    settings: Settings | None = None,
    fail_soft: bool = True,
) -> str:
    """Answer ``question`` about ``facts`` given prior (role, content) turns."""
    context = build_context(facts)
    conversation = "\n".join(f"{role}: {content}" for role, content in history)
    prompt = (
        f"Conversation so far:\n{conversation or '(none)'}\n\n"
        f"User question: {question}\n\nFACTS:\n{context.as_prompt_block()}"
    )

    own_client = False
    if client is None:
        try:
            client = get_llm_client(settings or load_settings())
            own_client = True
        except MissingAPIKeyError:
            if fail_soft:
                return _fallback_reply(question)
            raise

    try:
        reply = client.generate(
            prompt, system=render_system(DEFAULT_TEMPLATES.system, context) + _CHAT_SYSTEM_SUFFIX
        )
        if not reply.strip():
            raise LLMResponseError(getattr(client, "provider", "?"), "empty completion")
        return reply.strip()
    except (NotImplementedError, LLMResponseError):
        if fail_soft:
            return _fallback_reply(question)
        raise
    finally:
        if own_client:
            close = getattr(client, "close", None)
            if callable(close):
                close()
