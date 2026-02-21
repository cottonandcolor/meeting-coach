"""Meeting state data model."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ActionItem:
    assignee: str
    description: str
    deadline: str
    timestamp: float


@dataclass
class TopicEntry:
    topic: str
    started_at: float
    ended_at: Optional[float] = None


@dataclass
class SpeakerTurn:
    speaker: str
    is_user: bool
    timestamp: float


@dataclass
class Nudge:
    type: str
    message: str
    priority: str
    timestamp: float


@dataclass
class MeetingState:
    """Complete state for a single meeting coaching session."""

    meeting_id: str
    user_name: str = "User"
    meeting_start_time: float = 0.0
    meeting_duration_minutes: int = 30
    agenda_items: list[str] = field(default_factory=list)
    action_items: list[ActionItem] = field(default_factory=list)
    topics_discussed: list[TopicEntry] = field(default_factory=list)
    speaker_turns: list[SpeakerTurn] = field(default_factory=list)
    nudges: list[Nudge] = field(default_factory=list)
    current_topic: str = ""
    user_last_spoke_at: float = 0.0
    last_nudge_time: float = 0.0
    meeting_summary: Optional[dict] = None

    def to_dict(self) -> dict:
        """Convert to a flat dict suitable for ADK session state."""
        return {
            "meeting_start_time": self.meeting_start_time,
            "meeting_duration_minutes": self.meeting_duration_minutes,
            "agenda_items": self.agenda_items,
            "action_items": [
                {
                    "assignee": ai.assignee,
                    "description": ai.description,
                    "deadline": ai.deadline,
                    "timestamp": ai.timestamp,
                }
                for ai in self.action_items
            ],
            "topics_discussed": [
                {
                    "topic": t.topic,
                    "started_at": t.started_at,
                    "ended_at": t.ended_at,
                }
                for t in self.topics_discussed
            ],
            "speaker_turns": [
                {
                    "speaker": s.speaker,
                    "is_user": s.is_user,
                    "timestamp": s.timestamp,
                }
                for s in self.speaker_turns
            ],
            "nudges": [
                {
                    "type": n.type,
                    "message": n.message,
                    "priority": n.priority,
                    "timestamp": n.timestamp,
                }
                for n in self.nudges
            ],
            "current_topic": self.current_topic,
            "user_name": self.user_name,
            "user_last_spoke_at": self.user_last_spoke_at,
            "last_nudge_time": self.last_nudge_time,
        }
