import time
from google.adk.tools.tool_context import ToolContext


def emit_nudge(
    nudge_type: str,
    message: str,
    priority: str,
    tool_context: ToolContext,
) -> dict:
    """Emit a coaching nudge to the user.

    Args:
        nudge_type: Category of nudge. One of: 'participation', 'time',
            'action_item', 'topic', 'decision', 'summary_suggestion'.
        message: The short nudge message to display to the user (1-2 sentences).
        priority: Priority level: 'low', 'medium', or 'high'.

    Returns:
        A dict confirming the nudge was emitted or skipped due to rate limiting.
    """
    # Rate limiting: no more than one nudge per 2 minutes
    last_nudge_time = tool_context.state.get("last_nudge_time", 0)
    now = time.time()
    if now - last_nudge_time < 120 and priority != "high":
        return {
            "status": "skipped",
            "reason": "Rate limited — last nudge was less than 2 minutes ago.",
        }

    nudge = {
        "type": nudge_type,
        "message": message,
        "priority": priority,
        "timestamp": now,
    }

    nudges = tool_context.state.get("nudges", [])
    nudges.append(nudge)
    tool_context.state["nudges"] = nudges
    tool_context.state["last_nudge_time"] = now
    tool_context.state["pending_nudge"] = nudge

    return {"status": "success", "nudge": nudge}


def emit_participation_reminder(
    minutes_silent: int,
    tool_context: ToolContext,
) -> dict:
    """Remind the user they haven't spoken recently in the meeting.

    Args:
        minutes_silent: Approximate number of minutes the user has been silent.

    Returns:
        A dict confirming the nudge was emitted.
    """
    message = (
        f"You haven't spoken in about {minutes_silent} minutes. "
        "Look for an opening to contribute."
    )
    return emit_nudge("participation", message, "medium", tool_context)


def emit_time_warning(
    warning_type: str,
    minutes_info: int,
    tool_context: ToolContext,
) -> dict:
    """Emit a time-related warning nudge.

    Args:
        warning_type: Either 'remaining' (minutes left before scheduled end)
            or 'overtime' (minutes past scheduled end).
        minutes_info: Number of minutes remaining or over schedule.

    Returns:
        A dict confirming the nudge was emitted.
    """
    if warning_type == "remaining":
        message = f"Heads up — only {minutes_info} minutes remaining in the meeting."
    elif warning_type == "overtime":
        message = f"The meeting is {minutes_info} minutes over the scheduled time."
    else:
        message = f"Time check: {minutes_info} minutes on the current topic."

    return emit_nudge("time", message, "high", tool_context)
