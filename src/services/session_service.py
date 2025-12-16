"""
Session metadata management service for tracking game sessions.

This service maintains a separate metadata database from LangGraph's checkpoint storage.
LangGraph handles full GameState persistence, while this tracks user-facing session info.
"""

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional


class SessionMetadata:
    """Data class for session metadata."""

    def __init__(
        self,
        session_id: str,
        title: str,
        created_at: str,
        last_played: str,
        turn_count: int,
        status: str,
    ):
        self.session_id = session_id
        self.title = title
        self.created_at = created_at
        self.last_played = last_played
        self.turn_count = turn_count
        self.status = status

    def __repr__(self):
        return (
            f"SessionMetadata(id={self.session_id}, title={self.title}, "
            f"turns={self.turn_count}, status={self.status})"
        )


class SessionService:
    """
    Manages session metadata storage and retrieval.

    Uses SQLite for simple, file-based session tracking.
    LangGraph's SqliteSaver handles the actual GameState checkpoints.
    """

    def __init__(self, db_path: str = "src/data/storage/sessions_metadata.db"):
        """
        Initialize the session service.

        Args:
            db_path: Path to the SQLite database file
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        """Create the sessions table if it doesn't exist."""
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                created_at TEXT NOT NULL,
                last_played TEXT NOT NULL,
                turn_count INTEGER NOT NULL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'active'
            )
        """)
        conn.commit()
        conn.close()

    def create_session(self, session_id: str, title: str) -> None:
        """
        Create a new session record.

        Args:
            session_id: Unique session identifier
            title: Campaign title
        """
        now = datetime.now().isoformat()
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            "INSERT INTO sessions (session_id, title, created_at, last_played, turn_count, status) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (session_id, title, now, now, 0, "active"),
        )
        conn.commit()
        conn.close()

    def update_session(self, session_id: str, turn_count: int) -> None:
        """
        Update session last_played timestamp and turn count.

        Args:
            session_id: Session to update
            turn_count: Current turn number
        """
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            "UPDATE sessions SET last_played = ?, turn_count = ? WHERE session_id = ?",
            (datetime.now().isoformat(), turn_count, session_id),
        )
        conn.commit()
        conn.close()

    def mark_completed(self, session_id: str) -> None:
        """
        Mark a session as completed.

        Args:
            session_id: Session to mark as completed
        """
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            "UPDATE sessions SET status = 'completed', last_played = ? WHERE session_id = ?",
            (datetime.now().isoformat(), session_id),
        )
        conn.commit()
        conn.close()

    def get_session(self, session_id: str) -> Optional[SessionMetadata]:
        """
        Get metadata for a specific session.

        Args:
            session_id: Session ID to retrieve

        Returns:
            SessionMetadata or None if not found
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute(
            "SELECT session_id, title, created_at, last_played, turn_count, status "
            "FROM sessions WHERE session_id = ?",
            (session_id,),
        )
        row = cursor.fetchone()
        conn.close()

        if row:
            return SessionMetadata(*row)
        return None

    def list_sessions(
        self, status_filter: Optional[str] = None, limit: int = 50
    ) -> list[SessionMetadata]:
        """
        List all sessions, optionally filtered by status.

        Args:
            status_filter: Filter by status ('active', 'completed', etc.)
            limit: Maximum number of sessions to return

        Returns:
            List of SessionMetadata objects, ordered by last_played (newest first)
        """
        conn = sqlite3.connect(self.db_path)

        if status_filter:
            cursor = conn.execute(
                "SELECT session_id, title, created_at, last_played, turn_count, status "
                "FROM sessions WHERE status = ? ORDER BY last_played DESC LIMIT ?",
                (status_filter, limit),
            )
        else:
            cursor = conn.execute(
                "SELECT session_id, title, created_at, last_played, turn_count, status "
                "FROM sessions ORDER BY last_played DESC LIMIT ?",
                (limit,),
            )

        rows = cursor.fetchall()
        conn.close()

        return [SessionMetadata(*row) for row in rows]

    def delete_session(self, session_id: str) -> bool:
        """
        Delete a session record.

        Note: This only deletes metadata. The LangGraph checkpoint must be deleted separately.

        Args:
            session_id: Session to delete

        Returns:
            True if deleted, False if not found
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
        deleted = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return deleted


# Global singleton instance
session_service = SessionService()
