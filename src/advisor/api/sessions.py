"""Process-local, thread-safe server-side session state.

The raw IncomeStatement lives ONLY here and is never handed to the LLM path.
"""

from __future__ import annotations

import threading
from collections import OrderedDict
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from advisor.narrative.advisor import Advisory
from advisor.schema import Facts, IncomeStatement


@dataclass
class Session:
    """Holds one uploaded statement and everything computed from it."""

    id: str
    statement: IncomeStatement
    thresholds: dict[str, Any]
    facts: Facts | None = None
    narrative: Advisory | None = None
    scenario_facts: Facts | None = None
    chat_history: list[tuple[str, str]] = field(default_factory=list)


class SessionStore:
    """Bounded, lock-guarded LRU store of sessions keyed by opaque id."""

    def __init__(
        self, *, max_sessions: int = 32, id_factory: Callable[[], str] = lambda: uuid4().hex
    ) -> None:
        self._max = max_sessions
        self._id_factory = id_factory
        self._lock = threading.RLock()
        self._sessions: OrderedDict[str, Session] = OrderedDict()

    def create(self, statement: IncomeStatement, thresholds: dict[str, Any]) -> Session:
        with self._lock:
            session = Session(id=self._id_factory(), statement=statement, thresholds=thresholds)
            self._sessions[session.id] = session
            self._sessions.move_to_end(session.id)
            while len(self._sessions) > self._max:
                self._sessions.popitem(last=False)
            return session

    def get(self, session_id: str) -> Session:
        with self._lock:
            session = self._sessions[session_id]  # raises KeyError if absent/evicted
            self._sessions.move_to_end(session_id)
            return session

    def delete(self, session_id: str) -> None:
        with self._lock:
            self._sessions.pop(session_id, None)

    def __contains__(self, session_id: str) -> bool:
        with self._lock:
            return session_id in self._sessions

    def __len__(self) -> int:
        with self._lock:
            return len(self._sessions)

    def clear(self) -> None:
        with self._lock:
            self._sessions.clear()
