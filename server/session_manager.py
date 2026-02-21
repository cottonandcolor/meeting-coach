"""Meeting session lifecycle management."""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class MeetingSession:
    """Tracks a single meeting coaching session."""

    meeting_id: str
    user_id: str
    session_id: str
    start_time: float = field(default_factory=time.time)
    duration_minutes: int = 30
    user_name: str = "User"
    agenda_items: list[str] = field(default_factory=list)
    is_active: bool = True


class SessionManager:
    """Manages active meeting sessions."""

    def __init__(self) -> None:
        self._sessions: dict[str, MeetingSession] = {}

    def create_session(
        self,
        meeting_id: Optional[str] = None,
        user_name: str = "User",
        duration_minutes: int = 30,
        agenda_items: Optional[list[str]] = None,
    ) -> MeetingSession:
        """Create a new meeting session."""
        if meeting_id is None:
            meeting_id = uuid.uuid4().hex[:12]

        user_id = f"user_{uuid.uuid4().hex[:8]}"
        session_id = f"session_{meeting_id}"

        session = MeetingSession(
            meeting_id=meeting_id,
            user_id=user_id,
            session_id=session_id,
            user_name=user_name,
            duration_minutes=duration_minutes,
            agenda_items=agenda_items or [],
        )
        self._sessions[meeting_id] = session
        return session

    def get_session(self, meeting_id: str) -> Optional[MeetingSession]:
        """Get a session by meeting ID."""
        return self._sessions.get(meeting_id)

    def end_session(self, meeting_id: str) -> Optional[MeetingSession]:
        """Mark a session as ended."""
        session = self._sessions.get(meeting_id)
        if session:
            session.is_active = False
        return session

    def remove_session(self, meeting_id: str) -> None:
        """Remove a session entirely."""
        self._sessions.pop(meeting_id, None)

    @property
    def active_count(self) -> int:
        """Number of currently active sessions."""
        return sum(1 for s in self._sessions.values() if s.is_active)
