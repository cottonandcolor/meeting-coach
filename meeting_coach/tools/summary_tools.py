import time
from google.adk.tools.tool_context import ToolContext


def generate_meeting_summary(tool_context: ToolContext) -> dict:
    """Generate a post-meeting summary from all tracked state.

    Compiles action items, topics discussed, speaker turns, and nudge
    history into a structured summary. Call this when the meeting ends.

    Returns:
        A dict containing the complete meeting summary data.
    """
    action_items = tool_context.state.get("action_items", [])
    topics = tool_context.state.get("topics_discussed", [])
    speaker_turns = tool_context.state.get("speaker_turns", [])
    nudges = tool_context.state.get("nudges", [])
    start_time = tool_context.state.get("meeting_start_time", 0)
    duration_planned = tool_context.state.get("meeting_duration_minutes", 0)

    now = time.time()

    # Close the last open topic
    if topics and topics[-1].get("ended_at") is None:
        topics[-1]["ended_at"] = now
        tool_context.state["topics_discussed"] = topics

    # Calculate duration
    duration_actual = round((now - start_time) / 60, 1) if start_time else 0

    # Participation stats
    total_turns = len(speaker_turns)
    user_turns = sum(1 for t in speaker_turns if t.get("is_user"))
    other_turns = total_turns - user_turns
    user_pct = round((user_turns / total_turns * 100), 1) if total_turns > 0 else 0

    # Nudge breakdown by type
    nudge_breakdown = {}
    for n in nudges:
        ntype = n.get("type", "other")
        nudge_breakdown[ntype] = nudge_breakdown.get(ntype, 0) + 1

    # Topic durations
    topic_summaries = []
    for t in topics:
        started = t.get("started_at", 0)
        ended = t.get("ended_at", now)
        duration_min = round((ended - started) / 60, 1) if started else 0
        topic_summaries.append({
            "topic": t["topic"],
            "duration_minutes": duration_min,
        })

    summary = {
        "duration_planned_minutes": duration_planned,
        "duration_actual_minutes": duration_actual,
        "on_time": duration_actual <= duration_planned if duration_planned else True,
        "topics": topic_summaries,
        "action_items": action_items,
        "participation": {
            "total_speaker_turns": total_turns,
            "user_turns": user_turns,
            "other_turns": other_turns,
            "user_participation_pct": user_pct,
        },
        "coaching_stats": {
            "total_nudges": len(nudges),
            "breakdown": nudge_breakdown,
        },
    }

    tool_context.state["meeting_summary"] = summary
    return {"status": "success", "summary": summary}
