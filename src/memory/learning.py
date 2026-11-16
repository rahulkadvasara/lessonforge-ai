"""Self-evolution engine: analyzes failure patterns and extracts persistent learning insights."""
import json
import logging
from typing import List, Dict, Any
from src.memory.database import DatabaseManager, get_db_manager
from src.evaluation.rubric import RUBRIC_MAP

logger = logging.getLogger(__name__)


class SelfEvolutionEngine:
    """Analyzes historical rejection patterns and produces actionable insights for future generations."""

    def __init__(self, db_manager: DatabaseManager | None = None):
        self.db = db_manager or get_db_manager()

    def analyze_and_update_insights(self) -> List[Dict[str, Any]]:
        """
        Scan rejection logs, cluster recurring checkpoint failures, and persist/update learning insights.
        Returns the list of active insights.
        """
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT failed_checkpoint_ids, reasons, suggestions FROM rejection_logs")
            rows = cursor.fetchall()

            # Count occurrences per checkpoint
            checkpoint_stats: Dict[str, Dict[str, Any]] = {}
            for row in rows:
                try:
                    cids = json.loads(row["failed_checkpoint_ids"])
                    reasons = json.loads(row["reasons"])
                    suggestions = json.loads(row["suggestions"])
                    for i, cid in enumerate(cids):
                        if cid not in checkpoint_stats:
                            checkpoint_stats[cid] = {
                                "count": 0,
                                "reasons": [],
                                "suggestions": []
                            }
                        checkpoint_stats[cid]["count"] += 1
                        if i < len(reasons):
                            checkpoint_stats[cid]["reasons"].append(reasons[i])
                        if i < len(suggestions):
                            checkpoint_stats[cid]["suggestions"].append(suggestions[i])
                except Exception as e:
                    logger.warning(f"Error parsing rejection log row: {e}")

            # Upsert into learning_insights table
            for cid, stats in checkpoint_stats.items():
                cp_def = RUBRIC_MAP.get(cid)
                dimension = cp_def.dimension if cp_def else "General"
                pattern_desc = f"Frequently failed checkpoint {cid} ({cp_def.name if cp_def else cid}): {stats['count']} occurrences."
                
                # Pick the most actionable suggestion or construct from rubric
                best_suggestion = stats["suggestions"][-1] if stats["suggestions"] else (cp_def.pass_criteria if cp_def else "Review guidelines.")
                rec_text = f"Proactively enforce: {best_suggestion}"

                cursor.execute(
                    """
                    SELECT id FROM learning_insights WHERE checkpoint_id = ?
                    """,
                    (cid,)
                )
                existing = cursor.fetchone()
                if existing:
                    cursor.execute(
                        """
                        UPDATE learning_insights
                        SET occurrence_count = ?, recommendation = ?, last_detected_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                        """,
                        (stats["count"], rec_text, existing["id"])
                    )
                else:
                    cursor.execute(
                        """
                        INSERT INTO learning_insights (checkpoint_id, dimension, pattern_description, recommendation, occurrence_count)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (cid, dimension, pattern_desc, rec_text, stats["count"])
                    )
            conn.commit()

        return self.get_active_insights()

    def get_active_insights(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Retrieve the top active learning insights ordered by occurrence frequency."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, checkpoint_id, dimension, pattern_description, recommendation, occurrence_count, last_detected_at
                FROM learning_insights
                WHERE is_active = 1
                ORDER BY occurrence_count DESC, last_detected_at DESC
                LIMIT ?
                """,
                (limit,)
            )
            return [dict(r) for r in cursor.fetchall()]

    def format_insights_for_prompt(self) -> str:
        """Format active insights as instructional guidance to inject into the generator prompt."""
        insights = self.get_active_insights(limit=5)
        if not insights:
            return "No historical quality failure insights recorded yet. Maintain general high standards."
        
        lines = [
            "CRITICAL LESSONS LEARNED FROM PAST QUALITY EVALUATIONS:",
            "Past lessons frequently failed due to the following specific issues. You MUST proactively avoid them:"
        ]
        for ins in insights:
            lines.append(f"- [{ins['checkpoint_id']} - {ins['dimension']}]: {ins['recommendation']} (Failed {ins['occurrence_count']} times previously)")
        return "\n".join(lines)
