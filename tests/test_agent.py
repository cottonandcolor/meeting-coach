"""Unit tests for Meeting Coach agent tools."""

import time
from unittest.mock import MagicMock

import pytest

from meeting_coach.tools.nudge_tools import (
    emit_nudge,
    emit_participation_reminder,
    emit_time_warning,
)
from meeting_coach.tools.tracking_tools import (
    log_speaker_turn,
    track_action_item,
    update_current_topic,
)
from meeting_coach.tools.summary_tools import generate_meeting_summary
from meeting_coach.tools.agenda_tools import check_agenda_status


def _make_context(state=None):
    """Create a mock ToolContext with the given state."""
    ctx = MagicMock()
    ctx.state = state or {
        "nudges": [],
        "action_items": [],
        "topics_discussed": [],
        "speaker_turns": [],
        "last_nudge_time": 0,
        "user_last_spoke_at": 0,
        "meeting_start_time": time.time(),
        "meeting_duration_minutes": 30,
        "agenda_items": [],
        "current_topic": "",
    }
    return ctx


class TestEmitNudge:
    def test_emits_nudge_successfully(self):
        ctx = _make_context()
        result = emit_nudge("participation", "Speak up!", "medium", ctx)

        assert result["status"] == "success"
        assert len(ctx.state["nudges"]) == 1
        assert ctx.state["nudges"][0]["type"] == "participation"
        assert ctx.state["nudges"][0]["message"] == "Speak up!"
        assert ctx.state["nudges"][0]["priority"] == "medium"

    def test_rate_limits_non_high_priority(self):
        ctx = _make_context()
        ctx.state["last_nudge_time"] = time.time()  # Just nudged

        result = emit_nudge("topic", "Off-topic", "low", ctx)

        assert result["status"] == "skipped"
        assert len(ctx.state["nudges"]) == 0

    def test_high_priority_bypasses_rate_limit(self):
        ctx = _make_context()
        ctx.state["last_nudge_time"] = time.time()  # Just nudged

        result = emit_nudge("time", "Overtime!", "high", ctx)

        assert result["status"] == "success"
        assert len(ctx.state["nudges"]) == 1


class TestParticipationReminder:
    def test_creates_participation_nudge(self):
        ctx = _make_context()
        result = emit_participation_reminder(5, ctx)

        assert result["status"] == "success"
        assert ctx.state["nudges"][0]["type"] == "participation"
        assert "5 minutes" in ctx.state["nudges"][0]["message"]


class TestTimeWarning:
    def test_remaining_time_warning(self):
        ctx = _make_context()
        result = emit_time_warning("remaining", 5, ctx)

        assert result["status"] == "success"
        assert "5 minutes remaining" in ctx.state["nudges"][0]["message"]
        assert ctx.state["nudges"][0]["priority"] == "high"

    def test_overtime_warning(self):
        ctx = _make_context()
        result = emit_time_warning("overtime", 10, ctx)

        assert result["status"] == "success"
        assert "10 minutes over" in ctx.state["nudges"][0]["message"]


class TestTrackActionItem:
    def test_tracks_action_item(self):
        ctx = _make_context()
        result = track_action_item("John", "Send the report", "Friday", ctx)

        assert result["status"] == "success"
        assert len(ctx.state["action_items"]) == 1
        assert ctx.state["action_items"][0]["assignee"] == "John"
        assert ctx.state["action_items"][0]["description"] == "Send the report"
        assert ctx.state["action_items"][0]["deadline"] == "Friday"

    def test_also_emits_nudge(self):
        ctx = _make_context()
        track_action_item("Alice", "Review PR", "EOD", ctx)

        assert len(ctx.state["nudges"]) == 1
        assert ctx.state["nudges"][0]["type"] == "action_item"


class TestUpdateCurrentTopic:
    def test_updates_topic(self):
        ctx = _make_context()
        result = update_current_topic("Q4 Budget Review", ctx)

        assert result["status"] == "success"
        assert ctx.state["current_topic"] == "Q4 Budget Review"
        assert len(ctx.state["topics_discussed"]) == 1

    def test_no_change_for_same_topic(self):
        ctx = _make_context()
        ctx.state["topics_discussed"] = [
            {"topic": "Q4 Budget Review", "started_at": time.time(), "ended_at": None}
        ]

        result = update_current_topic("Q4 Budget Review", ctx)
        assert result["status"] == "no_change"

    def test_closes_previous_topic(self):
        ctx = _make_context()
        ctx.state["topics_discussed"] = [
            {"topic": "Topic A", "started_at": time.time() - 300, "ended_at": None}
        ]

        update_current_topic("Topic B", ctx)

        assert ctx.state["topics_discussed"][0]["ended_at"] is not None
        assert len(ctx.state["topics_discussed"]) == 2


class TestLogSpeakerTurn:
    def test_logs_speaker(self):
        ctx = _make_context()
        result = log_speaker_turn("John", False, ctx)

        assert result["status"] == "success"
        assert len(ctx.state["speaker_turns"]) == 1
        assert ctx.state["speaker_turns"][0]["speaker"] == "John"

    def test_updates_user_last_spoke(self):
        ctx = _make_context()
        log_speaker_turn("Preeti", True, ctx)

        assert ctx.state["user_last_spoke_at"] > 0


class TestGenerateMeetingSummary:
    def test_generates_summary(self):
        ctx = _make_context()
        ctx.state["meeting_start_time"] = time.time() - 1800  # 30 min ago
        ctx.state["meeting_duration_minutes"] = 30
        ctx.state["action_items"] = [
            {"assignee": "John", "description": "Send report", "deadline": "Friday", "timestamp": time.time()},
        ]
        ctx.state["topics_discussed"] = [
            {"topic": "Budget", "started_at": time.time() - 1800, "ended_at": None},
        ]
        ctx.state["speaker_turns"] = [
            {"speaker": "John", "is_user": False, "timestamp": time.time() - 1000},
            {"speaker": "User", "is_user": True, "timestamp": time.time() - 500},
            {"speaker": "John", "is_user": False, "timestamp": time.time() - 200},
        ]
        ctx.state["nudges"] = [
            {"type": "participation", "message": "Speak up", "priority": "medium", "timestamp": time.time()},
        ]

        result = generate_meeting_summary(ctx)

        assert result["status"] == "success"
        summary = result["summary"]
        assert summary["duration_actual_minutes"] > 0
        assert len(summary["action_items"]) == 1
        assert summary["participation"]["total_speaker_turns"] == 3
        assert summary["participation"]["user_turns"] == 1
        assert summary["coaching_stats"]["total_nudges"] == 1


class TestCheckAgendaStatus:
    def test_no_agenda(self):
        ctx = _make_context()
        result = check_agenda_status(ctx)

        assert result["status"] == "no_agenda"

    def test_on_agenda(self):
        ctx = _make_context()
        ctx.state["agenda_items"] = ["Budget Review", "Team Updates"]
        ctx.state["current_topic"] = "Budget Review"
        ctx.state["topics_discussed"] = [
            {"topic": "Budget Review", "started_at": time.time(), "ended_at": None},
        ]

        result = check_agenda_status(ctx)

        assert result["status"] == "success"
        assert result["on_agenda"] is True
        assert "Budget Review" in result["covered_items"]

    def test_off_agenda_emits_nudge(self):
        ctx = _make_context()
        ctx.state["agenda_items"] = ["Budget Review", "Team Updates"]
        ctx.state["current_topic"] = "Lunch Plans"
        ctx.state["topics_discussed"] = [
            {"topic": "Lunch Plans", "started_at": time.time(), "ended_at": None},
        ]

        result = check_agenda_status(ctx)

        assert result["on_agenda"] is False
        # Should have emitted an off-topic nudge
        assert len(ctx.state["nudges"]) == 1
        assert ctx.state["nudges"][0]["type"] == "topic"
