"""Pydantic models for WebSocket message protocol between client and server."""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel


# --- Client -> Server Messages ---


class MeetingConfig(BaseModel):
    """Meeting configuration sent at session start."""

    user_name: str = "User"
    meeting_duration_minutes: int = 30
    agenda_items: list[str] = []


class ClientConfigMessage(BaseModel):
    """Configuration message from client."""

    type: str = "config"
    config: MeetingConfig


class ClientScreenFrame(BaseModel):
    """Screen capture frame from client (base64-encoded JPEG)."""

    type: str = "screen_frame"
    data: str  # base64


class ClientEndMeeting(BaseModel):
    """Signal that the meeting has ended."""

    type: str = "end_meeting"


class ClientTextCommand(BaseModel):
    """Free-form text command from client."""

    type: str = "text_command"
    text: str


# --- Server -> Client Messages ---


class NudgeData(BaseModel):
    """A coaching nudge."""

    type: str
    message: str
    priority: str
    timestamp: float


class ServerNudgeMessage(BaseModel):
    """Nudge message sent to client."""

    type: str = "nudge"
    nudge: NudgeData


class ServerAudioWhisper(BaseModel):
    """Audio whisper from the agent."""

    type: str = "audio_whisper"
    data: str  # base64-encoded PCM audio
    mime_type: str = "audio/pcm;rate=24000"


class ServerSummaryMessage(BaseModel):
    """Post-meeting summary."""

    type: str = "summary"
    summary: dict[str, Any]


class ServerStateUpdate(BaseModel):
    """Partial state update for UI."""

    type: str = "state_update"
    current_topic: str = ""
    action_items_count: int = 0
    elapsed_minutes: float = 0


class ServerErrorMessage(BaseModel):
    """Error message."""

    type: str = "error"
    message: str


class ServerConnectionReady(BaseModel):
    """Confirmation that the session is established."""

    type: str = "connection_ready"
    meeting_id: str
    session_id: Optional[str] = None
