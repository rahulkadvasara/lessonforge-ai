"""Grounding service providing factual context from authoritative technical references."""
import os
from pathlib import Path
from typing import List, Dict, Any
from src.config.settings import get_settings


class GroundingService:
    """Manages local reference documents and provides grounded excerpts for generation and evaluation."""

    def __init__(self, references_dir: str | None = None):
        settings = get_settings()
        self.references_dir = Path(references_dir or settings.references_dir)
        self.reference_documents: Dict[str, str] = {}
        self.load_reference_documents()

    def load_reference_documents(self) -> None:
        """Load all text files from the references directory."""
        if not self.references_dir.exists():
            self.references_dir.mkdir(parents=True, exist_ok=True)
            return

        for file_path in self.references_dir.glob("*.txt"):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    self.reference_documents[file_path.name] = f.read()
            except Exception as e:
                print(f"Warning: Failed to load reference {file_path}: {e}")

    def get_grounding_context(self, topic: str, max_chars: int = 2000) -> str:
        """
        Return relevant grounding excerpts based on the topic.
        Provides authoritative grounding notes for RAG and related AI topics.
        """
        if not self.reference_documents:
            self.load_reference_documents()

        excerpts = []
        for doc_name, content in self.reference_documents.items():
            excerpts.append(f"--- SOURCE: {doc_name} ---\n{content.strip()}")

        combined = "\n\n".join(excerpts)
        if len(combined) > max_chars:
            combined = combined[:max_chars] + "\n...[truncated for context budget]"
        return combined
