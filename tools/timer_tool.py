"""Timer/Pomodoro tool implementation with built-in session management."""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional

from backend.services.screen_manager import ScreenManager
from tools.base import BaseTool, ToolContext

logger = logging.getLogger(__name__)

PomodoroStatus = Literal["running", "paused", "completed"]


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class PomodoroSession:
    """Represents a single Pomodoro session."""

    id: str
    work_duration_minutes: int
    break_duration_minutes: int
    status: PomodoroStatus
    started_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None
    total_work_seconds: int = 0

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        # Convert datetimes to ISO strings for JSON responses
        for key in ["started_at", "updated_at", "completed_at"]:
            value = data.get(key)
            if isinstance(value, datetime):
                data[key] = value.isoformat()
        return data


class TimerTool(BaseTool):
    """Pomodoro timer tool with built-in session management."""

    name = "timer"
    _sessions: Dict[str, PomodoroSession] = {}  # Class-level storage shared across instances

    def __init__(self, context: ToolContext) -> None:
        super().__init__(context)
        self._screen: ScreenManager = context.screen_manager

    def _get_session(self, session_id: str) -> PomodoroSession:
        if session_id not in TimerTool._sessions:
            raise KeyError(f"Pomodoro session '{session_id}' not found")
        return TimerTool._sessions[session_id]

    def execute(self, action: str, **kwargs: Any) -> Dict[str, Any]:
        action = action.lower()

        if action == "start":
            work = int(kwargs.get("work_duration_minutes", 25))
            brk = int(kwargs.get("break_duration_minutes", 5))
            session_id = str(uuid.uuid4())
            now = _utc_now()
            session = PomodoroSession(
                id=session_id,
                work_duration_minutes=work,
                break_duration_minutes=brk,
                status="running",
                started_at=now,
                updated_at=now,
            )
            TimerTool._sessions[session_id] = session
            logger.info("Started Pomodoro session %s", session_id)

            self._screen.update_timer(
                session_id=session.id,
                status=session.status,
                work_duration_minutes=session.work_duration_minutes,
                break_duration_minutes=session.break_duration_minutes,
            )
            self._screen.update_status("Pomodoro started")
            return {"session": session.to_dict()}

        session_id = kwargs.get("session_id")
        if not session_id:
            raise ValueError("session_id is required for this action")

        if action == "pause":
            session = self._get_session(session_id)
            if session.status != "running":
                return {"session": session.to_dict()}

            now = _utc_now()
            elapsed = (now - session.updated_at).total_seconds()
            if elapsed > 0:
                session.total_work_seconds += int(elapsed)
            session.status = "paused"
            session.updated_at = now
            logger.info("Paused Pomodoro session %s", session_id)

            self._screen.update_timer(session_id=session.id, status=session.status)
            self._screen.update_status("Pomodoro paused")
            return {"session": session.to_dict()}

        if action == "resume":
            session = self._get_session(session_id)
            if session.status != "paused":
                return {"session": session.to_dict()}

            now = _utc_now()
            session.status = "running"
            session.updated_at = now
            logger.info("Resumed Pomodoro session %s", session_id)

            self._screen.update_timer(session_id=session.id, status=session.status)
            self._screen.update_status("Pomodoro resumed")
            return {"session": session.to_dict()}

        if action == "complete":
            session = self._get_session(session_id)
            if session.status == "completed":
                return {"session": session.to_dict()}

            now = _utc_now()
            if session.status == "running":
                elapsed = (now - session.updated_at).total_seconds()
                if elapsed > 0:
                    session.total_work_seconds += int(elapsed)

            session.status = "completed"
            session.updated_at = now
            session.completed_at = now
            logger.info("Completed Pomodoro session %s", session_id)

            self._screen.update_timer(session_id=session.id, status=session.status)
            self._screen.update_status("Pomodoro completed")
            return {"session": session.to_dict()}

        if action == "status":
            session = self._get_session(session_id)
            return {"session": session.to_dict()}

        if action == "list":
            return {"sessions": [s.to_dict() for s in TimerTool._sessions.values()]}

        raise ValueError(f"Unknown timer action '{action}'")

    def get_session(self, session_id: str) -> PomodoroSession:
        """Get a session by ID (for API access)."""
        return self._get_session(session_id)

    def list_sessions(self) -> List[PomodoroSession]:
        """List all sessions (for API access)."""
        return list(TimerTool._sessions.values())


__all__ = ["TimerTool", "PomodoroSession"]
