"""Firestore persistence layer for meeting state and summaries."""

from __future__ import annotations

import logging
import os
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Lazy initialization — Firestore client is created on first use
_db = None


def _get_db():
    """Get or create the Firestore async client."""
    global _db
    if _db is None:
        try:
            from google.cloud import firestore

            project = os.environ.get("GOOGLE_CLOUD_PROJECT")
            _db = firestore.AsyncClient(project=project)
            logger.info(f"Firestore client initialized for project: {project}")
        except Exception as e:
            logger.warning(f"Firestore not available: {e}. State will not persist.")
            return None
    return _db


async def save_meeting_state(meeting_id: str, state: dict[str, Any]) -> bool:
    """Persist meeting state to Firestore.

    Args:
        meeting_id: Unique meeting identifier.
        state: Meeting state dict to persist.

    Returns:
        True if saved successfully, False otherwise.
    """
    db = _get_db()
    if not db:
        return False

    try:
        doc_ref = db.collection("meetings").document(meeting_id)
        await doc_ref.set(state, merge=True)
        return True
    except Exception as e:
        logger.error(f"Failed to save meeting state: {e}")
        return False


async def save_meeting_summary(
    meeting_id: str,
    summary: dict[str, Any],
    user_id: Optional[str] = None,
) -> bool:
    """Save the final meeting summary.

    Args:
        meeting_id: Unique meeting identifier.
        summary: Summary data to persist.
        user_id: Optional user identifier for querying history.

    Returns:
        True if saved successfully, False otherwise.
    """
    db = _get_db()
    if not db:
        return False

    try:
        doc_ref = db.collection("meetings").document(meeting_id)
        update_data = {
            "summary": summary,
            "status": "completed",
        }
        if user_id:
            update_data["user_id"] = user_id
        await doc_ref.set(update_data, merge=True)
        return True
    except Exception as e:
        logger.error(f"Failed to save meeting summary: {e}")
        return False


async def get_meeting_history(
    user_id: str,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """Retrieve past meeting summaries for a user.

    Args:
        user_id: User identifier.
        limit: Max number of meetings to return.

    Returns:
        List of meeting summary dicts, most recent first.
    """
    db = _get_db()
    if not db:
        return []

    try:
        from google.cloud.firestore_v1.base_query import FieldFilter

        query = (
            db.collection("meetings")
            .where(filter=FieldFilter("user_id", "==", user_id))
            .where(filter=FieldFilter("status", "==", "completed"))
            .order_by("meeting_start_time", direction="DESCENDING")
            .limit(limit)
        )
        meetings = []
        async for doc in query.stream():
            meetings.append(doc.to_dict())
        return meetings
    except Exception as e:
        logger.error(f"Failed to retrieve meeting history: {e}")
        return []
