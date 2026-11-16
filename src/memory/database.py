"""SQLite database initialization, connection management, and schema migrations."""
import sqlite3
import os
from pathlib import Path
from contextlib import contextmanager
from typing import Generator
from src.config.settings import get_settings

SCHEMA_SQL = """
-- 1. Generation Runs Table
CREATE TABLE IF NOT EXISTS generation_runs (
    run_id TEXT PRIMARY KEY,
    topic TEXT NOT NULL,
    learner_profile TEXT NOT NULL,
    max_retries INTEGER NOT NULL DEFAULT 2,
    attempts_used INTEGER NOT NULL DEFAULT 1,
    final_status TEXT NOT NULL, -- 'APPROVED', 'NEEDS_HUMAN_REVIEW', 'FAILED_INPUT'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Lesson Versions Table
CREATE TABLE IF NOT EXISTS lesson_versions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    attempt_number INTEGER NOT NULL,
    lesson_content TEXT NOT NULL,
    word_count INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(run_id) REFERENCES generation_runs(run_id) ON DELETE CASCADE
);

-- 3. Evaluation Results Table
CREATE TABLE IF NOT EXISTS evaluation_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    attempt_number INTEGER NOT NULL,
    overall_status TEXT NOT NULL, -- 'PASS', 'FAIL'
    passed_count INTEGER NOT NULL,
    failed_count INTEGER NOT NULL,
    evaluation_json TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(run_id) REFERENCES generation_runs(run_id) ON DELETE CASCADE
);

-- 4. Rejection Logs Table
CREATE TABLE IF NOT EXISTS rejection_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    attempt_number INTEGER NOT NULL,
    failed_checkpoint_ids TEXT NOT NULL, -- JSON array of strings
    reasons TEXT NOT NULL,               -- JSON array of strings
    suggestions TEXT NOT NULL,           -- JSON array of strings
    changes_made TEXT,                   -- Summary of diff / delta applied in subsequent version
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(run_id) REFERENCES generation_runs(run_id) ON DELETE CASCADE
);

-- 5. User Feedback Table
CREATE TABLE IF NOT EXISTS user_feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    feedback_type TEXT NOT NULL, -- 'POSITIVE' / 'NEGATIVE'
    comments TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(run_id) REFERENCES generation_runs(run_id) ON DELETE CASCADE
);

-- 6. Learning Insights Table (Self-evolution)
CREATE TABLE IF NOT EXISTS learning_insights (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    checkpoint_id TEXT NOT NULL,
    dimension TEXT NOT NULL,
    pattern_description TEXT NOT NULL,
    recommendation TEXT NOT NULL,
    occurrence_count INTEGER DEFAULT 1,
    is_active INTEGER DEFAULT 1,
    last_detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 7. Prompt Versions Table
CREATE TABLE IF NOT EXISTS prompt_versions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    prompt_name TEXT NOT NULL,
    version TEXT NOT NULL,
    prompt_template TEXT NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indices for performance
CREATE INDEX IF NOT EXISTS idx_runs_created_at ON generation_runs(created_at);
CREATE INDEX IF NOT EXISTS idx_versions_run_id ON lesson_versions(run_id);
CREATE INDEX IF NOT EXISTS idx_eval_run_id ON evaluation_results(run_id);
CREATE INDEX IF NOT EXISTS idx_rejection_run_id ON rejection_logs(run_id);
CREATE INDEX IF NOT EXISTS idx_insights_checkpoint ON learning_insights(checkpoint_id);
"""


class DatabaseManager:
    """Manages SQLite database connections and table lifecycle."""

    def __init__(self, db_path: str | None = None):
        self.db_path = db_path or get_settings().database_path
        # Ensure parent directory exists
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self.init_database()

    def init_database(self) -> None:
        """Initialize all schema tables and indices."""
        with self.get_connection() as conn:
            conn.executescript(SCHEMA_SQL)
            conn.commit()

    @contextmanager
    def get_connection(self) -> Generator[sqlite3.Connection, None, None]:
        """Context manager for SQLite connections with row factory."""
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
        finally:
            conn.close()


# Global database manager instance
_db_manager = None


def get_db_manager() -> DatabaseManager:
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
    return _db_manager
