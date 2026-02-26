"""FastAPI backend server for Meeting Coach.

Bridges the browser client (WebSocket) to the ADK agent (Gemini Live API).
Handles audio/video routing, nudge forwarding, and session lifecycle.
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import os
import time

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from google.adk.agents import LiveRequestQueue
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from meeting_coach.agent import root_agent
from meeting_coach.state.firestore_sync import save_meeting_state, save_meeting_summary
from server.models import MeetingConfig
from server.session_manager import SessionManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Meeting Coach", version="1.0.0")

# Serve frontend static files
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

# Services
session_service = InMemorySessionService()
session_manager = SessionManager()

APP_NAME = "meeting_coach"


@app.get("/")
async def root():
    """Serve the main frontend page."""
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))


@app.get("/health")
async def health():
    """Health check endpoint for Cloud Run."""
    return {
        "status": "healthy",
        "active_sessions": session_manager.active_count,
    }


@app.websocket("/ws/meeting/{meeting_id}")
async def meeting_websocket(websocket: WebSocket, meeting_id: str):
    """Main WebSocket endpoint for a meeting coaching session.

    Protocol:
    - Client sends binary frames: raw PCM audio (16-bit, 16kHz, mono)
    - Client sends JSON text frames: screen_frame, config, end_meeting, text_command
    - Server sends JSON text frames: nudge, audio_whisper, summary, state_update, error
    """
    await websocket.accept()
    logger.info(f"Client connected for meeting: {meeting_id}")

    # Create meeting session
    meeting_session = session_manager.create_session(meeting_id=meeting_id)

    # Default initial state
    initial_state = {
        "meeting_start_time": time.time(),
        "meeting_duration_minutes": 30,
        "agenda_items": [],
        "action_items": [],
        "topics_discussed": [],
        "speaker_turns": [],
        "nudges": [],
        "user_name": "User",
        "current_topic": "",
        "user_last_spoke_at": 0,
        "last_nudge_time": 0,
    }

    # Create ADK session
    adk_session = await session_service.create_session(
        app_name=APP_NAME,
        user_id=meeting_session.user_id,
        session_id=meeting_session.session_id,
        state=initial_state,
    )

    # Create Runner and LiveRequestQueue
    runner = Runner(
        agent=root_agent,
        app_name=APP_NAME,
        session_service=session_service,
    )
    live_queue = LiveRequestQueue()

    # Track nudge count for change detection
    last_nudge_count = 0
    is_running = True

    # Send ready confirmation
    await websocket.send_json({
        "type": "connection_ready",
        "meeting_id": meeting_id,
        "session_id": meeting_session.session_id,
    })

    async def receive_from_client():
        """Receive audio/screen/commands from client, forward to ADK."""
        nonlocal is_running
        try:
            while is_running:
                data = await websocket.receive()

                if "bytes" in data:
                    # Binary frame = raw PCM audio from microphone
                    pcm_data = data["bytes"]
                    if pcm_data:
                        live_request = types.LiveClientRealtimeInput(
                            media_chunks=[
                                types.Blob(
                                    data=pcm_data,
                                    mime_type="audio/pcm;rate=16000",
                                )
                            ]
                        )
                        await live_queue.send(live_request)

                elif "text" in data:
                    msg = json.loads(data["text"])
                    msg_type = msg.get("type", "")

                    if msg_type == "screen_frame":
                        # JPEG frame from screen share
                        frame_bytes = base64.b64decode(msg["data"])
                        live_request = types.LiveClientRealtimeInput(
                            media_chunks=[
                                types.Blob(
                                    data=frame_bytes,
                                    mime_type="image/jpeg",
                                )
                            ]
                        )
                        await live_queue.send(live_request)

                    elif msg_type == "config":
                        # Meeting configuration update (validated via Pydantic)
                        config = MeetingConfig(**msg.get("config", {}))
                        config_dict = config.model_dump()
                        current = await session_service.get_session(
                            app_name=APP_NAME,
                            user_id=meeting_session.user_id,
                            session_id=meeting_session.session_id,
                        )
                        if current:
                            for key, value in config_dict.items():
                                current.state[key] = value
                        meeting_session.user_name = config.user_name
                        meeting_session.duration_minutes = (
                            config.meeting_duration_minutes
                        )
                        meeting_session.agenda_items = config.agenda_items
                        logger.info(f"Meeting config updated: {config_dict}")

                    elif msg_type == "end_meeting":
                        # Tell agent to generate summary
                        live_request = types.LiveClientContent(
                            turns=[
                                types.Content(
                                    role="user",
                                    parts=[
                                        types.Part.from_text(
                                            "The meeting has ended. Please call "
                                            "generate_meeting_summary to compile "
                                            "the final summary."
                                        )
                                    ],
                                )
                            ]
                        )
                        await live_queue.send(live_request)

                    elif msg_type == "text_command":
                        # Free-form text command
                        text = msg.get("text", "")
                        if text:
                            live_request = types.LiveClientContent(
                                turns=[
                                    types.Content(
                                        role="user",
                                        parts=[types.Part.from_text(text)],
                                    )
                                ]
                            )
                            await live_queue.send(live_request)

        except WebSocketDisconnect:
            logger.info(f"Client disconnected: {meeting_id}")
            is_running = False
            live_queue.close()
        except Exception as e:
            logger.error(f"Error receiving from client: {e}")
            is_running = False
            live_queue.close()

    async def send_to_client():
        """Run the ADK live agent and forward responses to client."""
        nonlocal last_nudge_count, is_running
        try:
            async for event in runner.run_live(
                session=adk_session,
                live_request_queue=live_queue,
            ):
                if not is_running:
                    break

                # Check for audio response from agent (whisper)
                if hasattr(event, "content") and event.content:
                    for part in event.content.parts:
                        if hasattr(part, "inline_data") and part.inline_data:
                            audio_b64 = base64.b64encode(
                                part.inline_data.data
                            ).decode("utf-8")
                            await websocket.send_json({
                                "type": "audio_whisper",
                                "data": audio_b64,
                                "mime_type": (
                                    part.inline_data.mime_type
                                    or "audio/pcm;rate=24000"
                                ),
                            })

                # Check for new nudges in session state
                try:
                    current_session = await session_service.get_session(
                        app_name=APP_NAME,
                        user_id=meeting_session.user_id,
                        session_id=meeting_session.session_id,
                    )
                    if current_session:
                        nudges = current_session.state.get("nudges", [])
                        if len(nudges) > last_nudge_count:
                            for nudge in nudges[last_nudge_count:]:
                                await websocket.send_json({
                                    "type": "nudge",
                                    "nudge": nudge,
                                })
                            last_nudge_count = len(nudges)

                        # Send state updates periodically
                        elapsed = (
                            time.time()
                            - current_session.state.get("meeting_start_time", time.time())
                        ) / 60
                        await websocket.send_json({
                            "type": "state_update",
                            "current_topic": current_session.state.get(
                                "current_topic", ""
                            ),
                            "action_items_count": len(
                                current_session.state.get("action_items", [])
                            ),
                            "elapsed_minutes": round(elapsed, 1),
                        })

                        # Check for meeting summary
                        summary = current_session.state.get("meeting_summary")
                        if summary:
                            await websocket.send_json({
                                "type": "summary",
                                "summary": summary,
                            })
                            await save_meeting_summary(
                                meeting_id=meeting_id,
                                summary=summary,
                                user_id=meeting_session.user_id,
                            )

                except Exception as e:
                    logger.warning(f"Error checking session state: {e}")

        except Exception as e:
            logger.error(f"Error in agent stream: {e}")
            if is_running:
                try:
                    await websocket.send_json({
                        "type": "error",
                        "message": f"Agent error: {str(e)}",
                    })
                except Exception:
                    pass
        finally:
            is_running = False
            # Persist final meeting state to Firestore
            try:
                final_session = await session_service.get_session(
                    app_name=APP_NAME,
                    user_id=meeting_session.user_id,
                    session_id=meeting_session.session_id,
                )
                if final_session:
                    await save_meeting_state(meeting_id, dict(final_session.state))
            except Exception as e:
                logger.warning(f"Failed to persist final state: {e}")
            session_manager.end_session(meeting_id)
            logger.info(f"Meeting session ended: {meeting_id}")

    # Run both tasks concurrently
    try:
        await asyncio.gather(
            receive_from_client(),
            send_to_client(),
        )
    except Exception as e:
        logger.error(f"Session error: {e}")
    finally:
        session_manager.remove_session(meeting_id)
