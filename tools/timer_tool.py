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
PomodoroPhase = Literal["work", "break"]


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
    phase: PomodoroPhase = "work"
    break_started_at: Optional[datetime] = None
    total_break_seconds: int = 0

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        # Convert datetimes to ISO strings for JSON responses
        for key in ["started_at", "updated_at", "completed_at", "break_started_at"]:
            value = data.get(key)
            if isinstance(value, datetime):
                data[key] = value.isoformat()
        return data
    
    def calculate_remaining_work_seconds(self) -> int:
        """Calculate remaining work seconds based on current state."""
        if self.status != "running" or self.phase != "work":
            # If paused or not in work phase, use stored elapsed time
            total_work_seconds = self.work_duration_minutes * 60
            return max(0, total_work_seconds - self.total_work_seconds)
        
        # Running in work phase - calculate elapsed since last update
        now = _utc_now()
        elapsed = (now - self.updated_at).total_seconds()
        total_elapsed = self.total_work_seconds + int(elapsed)
        total_work_seconds = self.work_duration_minutes * 60
        return max(0, int(total_work_seconds - total_elapsed))
    
    def calculate_remaining_break_seconds(self) -> int:
        """Calculate remaining break seconds based on current state."""
        if self.status != "running" or self.phase != "break" or self.break_started_at is None:
            # If paused or not in break phase, return full break duration
            return self.break_duration_minutes * 60
        
        # Running in break phase - calculate elapsed since break started
        now = _utc_now()
        elapsed = (now - self.break_started_at).total_seconds()
        total_break_seconds = self.break_duration_minutes * 60
        return max(0, int(total_break_seconds - elapsed))


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
    
    def _check_and_handle_transitions(self, session: PomodoroSession) -> None:
        """Check if timer transitions are needed and handle them."""
        if session.status != "running":
            return
        
        now = _utc_now()
        
        if session.phase == "work":
            remaining = session.calculate_remaining_work_seconds()
            if remaining <= 0:
                # Work timer finished - start break timer
                logger.info("Work timer completed, starting break timer for session %s", session.id)
                # Save any remaining elapsed work time
                elapsed = (now - session.updated_at).total_seconds()
                if elapsed > 0:
                    session.total_work_seconds += int(elapsed)
                
                # Transition to break phase
                session.phase = "break"
                session.break_started_at = now
                session.updated_at = now
                self._update_timer_state(session)
                self._screen.update_status("Break started")
        
        elif session.phase == "break":
            remaining = session.calculate_remaining_break_seconds()
            if remaining <= 0:
                # Break timer finished - start new work timer
                logger.info("Break timer completed, starting new work timer for session %s", session.id)
                
                # Reset for new work cycle
                session.phase = "work"
                session.total_work_seconds = 0
                session.total_break_seconds = 0
                session.started_at = now
                session.updated_at = now
                session.break_started_at = None
                self._update_timer_state(session)
                self._screen.update_status("New work cycle started")
    
    def _update_timer_state(self, session: PomodoroSession) -> None:
        """Update screen manager with current timer state including remaining times."""
        remaining_work = session.calculate_remaining_work_seconds()
        remaining_break = session.calculate_remaining_break_seconds()
        
        timer_state = {
            "session_id": session.id,
            "status": session.status,
            "phase": session.phase,
            "work_duration_minutes": session.work_duration_minutes,
            "break_duration_minutes": session.break_duration_minutes,
            "remaining_work_seconds": remaining_work,
            "remaining_break_seconds": remaining_break,
            "total_work_seconds": session.total_work_seconds,
            "started_at": session.started_at.isoformat(),
            "updated_at": session.updated_at.isoformat(),
        }
        
        if session.break_started_at:
            timer_state["break_started_at"] = session.break_started_at.isoformat()
        
        self._screen.update_timer(**timer_state)

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
                phase="work",
            )
            TimerTool._sessions[session_id] = session
            logger.info("Started Pomodoro session %s", session_id)

            self._update_timer_state(session)
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
            # Save elapsed time based on current phase
            elapsed = (now - session.updated_at).total_seconds()
            if elapsed > 0:
                if session.phase == "work":
                    session.total_work_seconds += int(elapsed)
                elif session.phase == "break":
                    session.total_break_seconds += int(elapsed)
            
            session.status = "paused"
            session.updated_at = now
            logger.info("Paused Pomodoro session %s", session_id)

            self._update_timer_state(session)
            self._screen.update_status("Pomodoro paused")
            return {"session": session.to_dict()}

        if action == "resume":
            session = self._get_session(session_id)
            if session.status != "paused":
                return {"session": session.to_dict()}

            now = _utc_now()
            session.status = "running"
            session.updated_at = now
            # If resuming break phase, update break_started_at if needed
            if session.phase == "break" and session.break_started_at is None:
                session.break_started_at = now
            logger.info("Resumed Pomodoro session %s", session_id)

            self._update_timer_state(session)
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
                    if session.phase == "work":
                        session.total_work_seconds += int(elapsed)
                    elif session.phase == "break":
                        session.total_break_seconds += int(elapsed)

            session.status = "completed"
            session.updated_at = now
            session.completed_at = now
            logger.info("Completed Pomodoro session %s", session_id)

            # Update timer state with completed status (triggers cleanup in screen manager)
            self._update_timer_state(session)
            self._screen.update_status("Pomodoro completed")
            # Clear timer state from screen
            self._screen.state.timer_state.clear()
            return {"session": session.to_dict()}
        
        if action == "stop":
            session = self._get_session(session_id)
            if session.status == "completed":
                return {"session": session.to_dict()}

            now = _utc_now()
            if session.status == "running":
                elapsed = (now - session.updated_at).total_seconds()
                if elapsed > 0:
                    if session.phase == "work":
                        session.total_work_seconds += int(elapsed)
                    elif session.phase == "break":
                        session.total_break_seconds += int(elapsed)

            session.status = "completed"
            session.updated_at = now
            session.completed_at = now
            logger.info("Stopped Pomodoro session %s", session_id)

            # Update timer state with completed status (triggers cleanup in screen manager)
            self._update_timer_state(session)
            self._screen.update_status("Focus session ended")
            # Clear timer state from screen
            self._screen.state.timer_state.clear()
            return {"session": session.to_dict()}

        if action == "status":
            session = self._get_session(session_id)
            # Check for transitions before returning status
            self._check_and_handle_transitions(session)
            return {"session": session.to_dict()}

        if action == "list":
            return {"sessions": [s.to_dict() for s in TimerTool._sessions.values()]}

        raise ValueError(f"Unknown timer action '{action}'")

    def get_session(self, session_id: str) -> PomodoroSession:
        """Get a session by ID (for API access)."""
        session = self._get_session(session_id)
        # Check for transitions when getting session
        self._check_and_handle_transitions(session)
        # Update timer state so UI gets current countdown
        self._update_timer_state(session)
        return session

    def list_sessions(self) -> List[PomodoroSession]:
        """List all sessions (for API access)."""
        sessions = list(TimerTool._sessions.values())
        # Check transitions and update state for all active sessions
        for session in sessions:
            if session.status == "running":
                self._check_and_handle_transitions(session)
                self._update_timer_state(session)
        return sessions


__all__ = ["TimerTool", "PomodoroSession"]
