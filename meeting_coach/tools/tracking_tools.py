import time
from google.adk.tools.tool_context import ToolContext

from meeting_coach.tools.nudge_tools import emit_nudge


def track_action_item(
    assignee: str,
    description: str,
    deadline: str,
    tool_context: ToolContext,
) -> dict:
    """Record a detected action item from the meeting conversation.

    Call this when someone explicitly commits to a task, deliverable,
    or follow-up item during the meeting.

    Args:
        assignee: The person responsible for the action item.
        description: What they committed to do.
        deadline: The deadline if mentioned, or 'unspecified'.

    Returns:
        A dict confirming the action item was recorded.
    """
    action_item = {
        "assignee": assignee,
        "description": description,
        "deadline": deadline,
        "timestamp": time.time(),
    }

    items = tool_context.state.get("action_items", [])
    items.append(action_item)
    tool_context.state["action_items"] = items

    emit_nudge(
        "action_item",
        f"Captured: {assignee} will {description} (deadline: {deadline})",
        "medium",
        tool_context,
    )

    return {"status": "success", "action_item": action_item}


def update_current_topic(
    topic: str,
    tool_context: ToolContext,
) -> dict:
    """Update the current discussion topic when the conversation shifts.

    Args:
        topic: Brief description of the new topic being discussed.

    Returns:
        A dict confirming the topic was updated.
    """
    topics = tool_context.state.get("topics_discussed", [])
    now = time.time()

    # Don't duplicate if same topic
    if topics and topics[-1]["topic"] == topic:
        return {"status": "no_change", "topic": topic}

    # Close previous topic
    if topics:
        topics[-1]["ended_at"] = now

    topics.append({
        "topic": topic,
        "started_at": now,
        "ended_at": None,
    })
    tool_context.state["topics_discussed"] = topics
    tool_context.state["current_topic"] = topic

    return {"status": "success", "topic": topic}


def log_speaker_turn(
    speaker_name: str,
    is_user: bool,
    tool_context: ToolContext,
) -> dict:
    """Log when someone speaks in the meeting.

    Args:
        speaker_name: Name or identifier of the speaker.
        is_user: True if this is the coaching client (the user being coached).

    Returns:
        A dict confirming the speaker turn was logged.
    """
    now = time.time()
    turns = tool_context.state.get("speaker_turns", [])
    turns.append({
        "speaker": speaker_name,
        "is_user": is_user,
        "timestamp": now,
    })
    tool_context.state["speaker_turns"] = turns

    if is_user:
        tool_context.state["user_last_spoke_at"] = now

    return {"status": "success", "speaker": speaker_name, "is_user": is_user}
