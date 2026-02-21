from google.adk.tools.tool_context import ToolContext

from meeting_coach.tools.nudge_tools import emit_nudge


def check_agenda_status(tool_context: ToolContext) -> dict:
    """Check if the meeting is on track with the agenda.

    Compares discussed topics against agenda items and identifies
    any drift or remaining items. If off-topic, emits a nudge.

    Returns:
        A dict with agenda status, coverage, and any drift warnings.
    """
    agenda = tool_context.state.get("agenda_items", [])
    current_topic = tool_context.state.get("current_topic", "")
    topics_discussed = tool_context.state.get("topics_discussed", [])

    if not agenda:
        return {
            "status": "no_agenda",
            "message": "No agenda was set for this meeting.",
        }

    # Check which agenda items have been covered
    discussed_lower = [t["topic"].lower() for t in topics_discussed]
    covered = []
    remaining = []

    for item in agenda:
        item_lower = item.lower()
        is_covered = any(
            item_lower in topic or topic in item_lower
            for topic in discussed_lower
        )
        if is_covered:
            covered.append(item)
        else:
            remaining.append(item)

    # Check if current topic matches any agenda item
    on_agenda = any(
        item.lower() in current_topic.lower()
        or current_topic.lower() in item.lower()
        for item in agenda
    ) if current_topic else True

    # Emit off-topic nudge if needed
    if not on_agenda and current_topic:
        emit_nudge(
            "topic",
            f"The discussion seems off-agenda. Remaining items: {', '.join(remaining[:3])}",
            "low",
            tool_context,
        )

    return {
        "status": "success",
        "on_agenda": on_agenda,
        "current_topic": current_topic,
        "covered_items": covered,
        "remaining_items": remaining,
        "coverage_pct": round(len(covered) / len(agenda) * 100, 1) if agenda else 100,
    }
