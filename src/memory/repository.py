"""Repository pattern for database operations across runs, versions, and feedback."""
import json
from typing import List, Dict, Any, Optional
from src.memory.database import get_db_manager, DatabaseManager


class MemoryRepository:
    """Provides structured persistence methods for all agent memory and audit artifacts."""

    def __init__(self, db_manager: DatabaseManager | None = None):
        self.db = db_manager or get_db_manager()

    # --- Runs ---
    def create_run(self, run_id: str, topic: str, learner_profile: dict, max_retries: int) -> None:
        with self.db.get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO generation_runs (run_id, topic, learner_profile, max_retries, attempts_used, final_status)
                VALUES (?, ?, ?, ?, 1, 'IN_PROGRESS')
                """,
                (run_id, topic, json.dumps(learner_profile), max_retries)
            )
            conn.commit()

    def update_run_status(self, run_id: str, final_status: str, attempts_used: int) -> None:
        with self.db.get_connection() as conn:
            conn.execute(
                """
                UPDATE generation_runs
                SET final_status = ?, attempts_used = ?, updated_at = CURRENT_TIMESTAMP
                WHERE run_id = ?
                """,
                (final_status, attempts_used, run_id)
            )
            conn.commit()

    def get_run(self, run_id: str) -> Optional[Dict[str, Any]]:
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM generation_runs WHERE run_id = ?", (run_id,))
            row = cursor.fetchone()
            if row:
                res = dict(row)
                res["learner_profile"] = json.loads(res["learner_profile"])
                return res
            return None

    def list_runs(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM generation_runs ORDER BY rowid DESC LIMIT ?", (limit,))
            rows = cursor.fetchall()
            runs = []
            for r in rows:
                item = dict(r)
                try:
                    item["learner_profile"] = json.loads(item["learner_profile"])
                except Exception:
                    pass
                runs.append(item)
            return runs

    # --- Lesson Versions ---
    def save_lesson_version(self, run_id: str, attempt_number: int, lesson_content: str) -> int:
        word_count = len(lesson_content.split())
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO lesson_versions (run_id, attempt_number, lesson_content, word_count)
                VALUES (?, ?, ?, ?)
                """,
                (run_id, attempt_number, lesson_content, word_count)
            )
            conn.commit()
            return cursor.lastrowid

    def get_lesson_versions(self, run_id: str) -> List[Dict[str, Any]]:
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM lesson_versions WHERE run_id = ? ORDER BY attempt_number ASC",
                (run_id,)
            )
            return [dict(r) for r in cursor.fetchall()]

    # --- Evaluation Results ---
    def save_evaluation_result(
        self,
        run_id: str,
        attempt_number: int,
        overall_status: str,
        passed_count: int,
        failed_count: int,
        evaluation_json: str
    ) -> int:
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO evaluation_results (run_id, attempt_number, overall_status, passed_count, failed_count, evaluation_json)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (run_id, attempt_number, overall_status, passed_count, failed_count, evaluation_json)
            )
            conn.commit()
            return cursor.lastrowid

    def get_evaluations_for_run(self, run_id: str) -> List[Dict[str, Any]]:
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM evaluation_results WHERE run_id = ? ORDER BY attempt_number ASC",
                (run_id,)
            )
            results = []
            for r in cursor.fetchall():
                item = dict(r)
                item["evaluation_report"] = json.loads(item["evaluation_json"])
                results.append(item)
            return results

    # --- Rejection Logs ---
    def save_rejection_log(
        self,
        run_id: str,
        attempt_number: int,
        failed_checkpoint_ids: List[str],
        reasons: List[str],
        suggestions: List[str],
        changes_made: str | None = None
    ) -> int:
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO rejection_logs (run_id, attempt_number, failed_checkpoint_ids, reasons, suggestions, changes_made)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    attempt_number,
                    json.dumps(failed_checkpoint_ids),
                    json.dumps(reasons),
                    json.dumps(suggestions),
                    changes_made or ""
                )
            )
            conn.commit()
            return cursor.lastrowid

    def get_rejection_logs(self, run_id: str | None = None) -> List[Dict[str, Any]]:
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            if run_id:
                cursor.execute(
                    "SELECT * FROM rejection_logs WHERE run_id = ? ORDER BY attempt_number ASC",
                    (run_id,)
                )
            else:
                cursor.execute("SELECT * FROM rejection_logs ORDER BY created_at DESC LIMIT 100")
            
            logs = []
            for r in cursor.fetchall():
                item = dict(r)
                item["failed_checkpoint_ids"] = json.loads(item["failed_checkpoint_ids"])
                item["reasons"] = json.loads(item["reasons"])
                item["suggestions"] = json.loads(item["suggestions"])
                logs.append(item)
            return logs

    # --- User Feedback ---
    def save_user_feedback(self, run_id: str, feedback_type: str, comments: str | None = None) -> int:
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO user_feedback (run_id, feedback_type, comments)
                VALUES (?, ?, ?)
                """,
                (run_id, feedback_type, comments or "")
            )
            conn.commit()
            return cursor.lastrowid

    def get_user_feedback(self, run_id: str | None = None) -> List[Dict[str, Any]]:
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            if run_id:
                cursor.execute("SELECT * FROM user_feedback WHERE run_id = ?", (run_id,))
            else:
                cursor.execute("SELECT * FROM user_feedback ORDER BY created_at DESC")
            return [dict(r) for r in cursor.fetchall()]

    # --- Metrics & Dashboard Aggregates ---
    def get_system_metrics(self) -> Dict[str, Any]:
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            
            # Total runs
            cursor.execute("SELECT COUNT(*) FROM generation_runs")
            total_runs = cursor.fetchone()[0]

            # Approved runs
            cursor.execute("SELECT COUNT(*) FROM generation_runs WHERE final_status = 'APPROVED'")
            approved_runs = cursor.fetchone()[0]

            # Rejected / Needs Review runs
            cursor.execute("SELECT COUNT(*) FROM generation_runs WHERE final_status = 'NEEDS_HUMAN_REVIEW'")
            review_runs = cursor.fetchone()[0]

            # Average attempts
            cursor.execute("SELECT AVG(attempts_used) FROM generation_runs WHERE final_status IN ('APPROVED', 'NEEDS_HUMAN_REVIEW')")
            avg_attempts_row = cursor.fetchone()[0]
            avg_attempts = round(avg_attempts_row, 2) if avg_attempts_row else 1.0

            # Checkpoint failure frequencies
            cursor.execute("SELECT failed_checkpoint_ids FROM rejection_logs")
            freq_map: Dict[str, int] = {}
            for row in cursor.fetchall():
                try:
                    cp_ids = json.loads(row[0])
                    for cid in cp_ids:
                        freq_map[cid] = freq_map.get(cid, 0) + 1
                except Exception:
                    pass

            return {
                "total_runs": total_runs,
                "approved_runs": approved_runs,
                "review_runs": review_runs,
                "average_attempts": avg_attempts,
                "checkpoint_failure_frequencies": freq_map
            }
