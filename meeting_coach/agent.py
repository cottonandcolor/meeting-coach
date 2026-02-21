from google.adk.agents import Agent
from google.genai import types

from meeting_coach.prompts.coach_instructions import COACH_SYSTEM_INSTRUCTION
from meeting_coach.tools.nudge_tools import (
    emit_nudge,
    emit_participation_reminder,
    emit_time_warning,
)
from meeting_coach.tools.tracking_tools import (
    track_action_item,
    update_current_topic,
    log_speaker_turn,
)
from meeting_coach.tools.summary_tools import generate_meeting_summary
from meeting_coach.tools.agenda_tools import check_agenda_status

root_agent = Agent(
    model="gemini-live-2.5-flash-native-audio",
    name="meeting_coach",
    description=(
        "Real-time meeting coaching agent that listens to meetings "
        "and provides helpful nudges about participation, action items, "
        "time management, and topic tracking."
    ),
    instruction=COACH_SYSTEM_INSTRUCTION,
    tools=[
        emit_nudge,
        emit_participation_reminder,
        emit_time_warning,
        track_action_item,
        update_current_topic,
        log_speaker_turn,
        check_agenda_status,
        generate_meeting_summary,
    ],
    generate_content_config=types.GenerateContentConfig(
        temperature=0.7,
        response_modalities=["AUDIO"],
    ),
)
