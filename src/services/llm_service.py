"""LLM Provider abstraction and Groq client integration with resilience and mocking."""
import os
import time
import json
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from groq import Groq
from src.config.settings import get_settings

logger = logging.getLogger(__name__)


class BaseLLMClient(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    def generate(
        self,
        messages: List[Dict[str, str]],
        temperature: float | None = None,
        max_tokens: int = 4096,
        response_format: Optional[Dict[str, str]] = None
    ) -> str:
        """Generate response text from a list of chat messages."""
        pass

    @abstractmethod
    def get_model_name(self) -> str:
        """Return the active model name."""
        pass


class GroqLLMClient(BaseLLMClient):
    """Resilient Groq Cloud API client with exponential backoff and structured output support."""

    def __init__(
        self,
        api_key: str | None = None,
        model_name: str | None = None,
        temperature: float | None = None,
        timeout: int | None = None,
        max_retries: int | None = None
    ):
        settings = get_settings()
        self.api_key = api_key or settings.groq_api_key
        self.model_name = model_name or settings.groq_model
        self.temperature = temperature if temperature is not None else settings.llm_temperature
        self.timeout = timeout or settings.llm_timeout_seconds
        self.max_retries = max_retries or settings.llm_max_retries

        if not self.api_key:
            logger.warning("GROQ_API_KEY is not set. Real API calls will fail unless configured.")
            self.client = None
        else:
            self.client = Groq(api_key=self.api_key, timeout=self.timeout)

    def get_model_name(self) -> str:
        return self.model_name

    def generate(
        self,
        messages: List[Dict[str, str]],
        temperature: float | None = None,
        max_tokens: int = 2200,
        response_format: Optional[Dict[str, str]] = None
    ) -> str:
        if not self.client:
            raise ValueError(
                "Groq API Key is not configured. Please set GROQ_API_KEY in your .env file or Streamlit sidebar."
            )

        temp = temperature if temperature is not None else self.temperature
        delay = 3.0

        for attempt in range(1, self.max_retries + 1):
            try:
                kwargs: Dict[str, Any] = {
                    "model": self.model_name,
                    "messages": messages,
                    "temperature": temp,
                    "max_tokens": max_tokens,
                }
                # Groq server proxy often fails with 400 json_validate_failed for OSS models;
                # our prompts already enforce strict JSON output directly.

                response = self.client.chat.completions.create(**kwargs)
                content = response.choices[0].message.content
                if not content or not content.strip():
                    raise ValueError("Groq returned an empty response.")
                
                # Brief rate-limit buffer to prevent token-per-minute spikes on Groq free tier
                time.sleep(1.5)
                return content.strip()

            except Exception as e:
                err_str = str(e)
                logger.warning(f"Groq API call attempt {attempt}/{self.max_retries} failed: {err_str}")
                if attempt == self.max_retries:
                    raise RuntimeError(f"Groq API call permanently failed after {self.max_retries} attempts: {err_str}")
                time.sleep(delay)
                delay *= 2.0  # exponential backoff


class GeminiLLMClient(BaseLLMClient):
    """Google Gemini API client using the official google.genai SDK."""

    def __init__(
        self,
        api_key: str | None = None,
        model_name: str | None = None,
        temperature: float | None = None,
        max_retries: int | None = None
    ):
        settings = get_settings()
        self.api_key = api_key or settings.gemini_api_key
        self.model_name = model_name or settings.gemini_model
        self.temperature = temperature if temperature is not None else settings.llm_temperature
        self.max_retries = max_retries or settings.llm_max_retries

        if not self.api_key:
            logger.warning("GEMINI_API_KEY is not set.")
            self.client = None
        else:
            try:
                from google import genai
                self.client = genai.Client(api_key=self.api_key)
            except Exception as e:
                logger.error(f"Failed to initialize google.genai Client: {e}")
                self.client = None

    def get_model_name(self) -> str:
        return self.model_name

    def generate(
        self,
        messages: List[Dict[str, str]],
        temperature: float | None = None,
        max_tokens: int = 2200,
        response_format: Optional[Dict[str, str]] = None
    ) -> str:
        if not self.client:
            raise ValueError(
                "Gemini API Key is not configured. Please set GEMINI_API_KEY in .env or Streamlit sidebar."
            )

        temp = temperature if temperature is not None else self.temperature
        
        # Separate system instruction and user/conversation contents
        system_instruction = None
        contents_list = []
        for msg in messages:
            role = msg.get("role")
            content = msg.get("content", "")
            if role == "system":
                system_instruction = content
            else:
                contents_list.append(content)

        prompt_text = "\n\n".join(contents_list)

        config_dict: Dict[str, Any] = {
            "temperature": temp,
            "max_output_tokens": max_tokens,
        }
        if system_instruction:
            config_dict["system_instruction"] = system_instruction
        if response_format and response_format.get("type") == "json_object":
            config_dict["response_mime_type"] = "application/json"

        delay = 2.5
        for attempt in range(1, self.max_retries + 1):
            try:
                resp = self.client.models.generate_content(
                    model=self.model_name,
                    contents=prompt_text,
                    config=config_dict
                )
                text = resp.text
                if not text or not text.strip():
                    raise ValueError("Gemini returned an empty response.")
                return text.strip()

            except Exception as e:
                err_str = str(e)
                logger.warning(f"Gemini API call attempt {attempt}/{self.max_retries} failed: {err_str}")
                if attempt == self.max_retries:
                    raise RuntimeError(f"Gemini API permanently failed after {self.max_retries} attempts: {err_str}")
                time.sleep(delay)
                delay *= 2.0


class MockLLMClient(BaseLLMClient):
    """Deterministic Mock LLM Client for offline unit testing and development verification."""

    def __init__(self, model_name: str = "mock-groq-model"):
        self.model_name = model_name
        self.call_history: List[Dict[str, Any]] = []
        self.generator_responses: List[str] = []
        self.evaluator_responses: List[str] = []

    def get_model_name(self) -> str:
        return self.model_name

    def queue_generator_response(self, text: str) -> None:
        self.generator_responses.append(text)

    def queue_evaluator_response(self, text: str) -> None:
        self.evaluator_responses.append(text)

    def generate(
        self,
        messages: List[Dict[str, str]],
        temperature: float | None = None,
        max_tokens: int = 4096,
        response_format: Optional[Dict[str, str]] = None
    ) -> str:
        self.call_history.append({
            "messages": messages,
            "temperature": temperature,
            "response_format": response_format
        })

        # Detect role based on system prompt
        sys_msg = messages[0]["content"] if messages else ""
        if "Lead Quality Evaluation Auditor" in sys_msg or "THE 18 MANDATORY CHECKPOINTS TO EVALUATE" in sys_msg:
            if self.evaluator_responses:
                return self.evaluator_responses.pop(0)
            # Default passing evaluation json
            from src.evaluation.rubric import RUBRIC_CHECKPOINTS
            checkpoints = []
            for cp in RUBRIC_CHECKPOINTS:
                checkpoints.append({
                    "id": cp.id,
                    "dimension": cp.dimension,
                    "name": cp.name,
                    "status": "PASS",
                    "evidence": f"Mock evidence satisfying {cp.name}.",
                    "reason": "Meets criteria in mock test.",
                    "suggestion": None
                })
            return json.dumps({
                "overall_status": "PASS",
                "passed_count": 18,
                "failed_count": 0,
                "checkpoints": checkpoints
            })

        # Generator role default
        if self.generator_responses:
            return self.generator_responses.pop(0)

        # Standard compliant mock lesson
        return (
            "# Lesson Title: Introduction to RAG (Retrieval-Augmented Generation)\n\n"
            "## 1. Lesson Title\nIntroduction to RAG\n\n"
            "## 2. Learning Objectives\nLearn what RAG is, why it is needed, and how it works.\n\n"
            "## 3. Prerequisites\nNone. Zero prior knowledge needed.\n\n"
            "## 4. Introduction\nWelcome! Let us learn how computers find facts.\n\n"
            "## 5. What Is This Concept?\nRAG stands for Retrieval-Augmented Generation. Retrieval means fetching facts. Augmentation means adding facts to the prompt. Generation means the AI writing the answer.\n\n"
            "## 6. Why Is It Important?\nNormal AI models memorize things in the past. RAG allows them to read fresh documents today.\n\n"
            "## 7. How Does It Work?\nDocuments are broken into chunks, turned into vector embeddings, and stored in a vector database.\n\n"
            "## 8. Step-by-Step Explanation\n1. Question asked. 2. Chunks retrieved. 3. Context injected. 4. Answer generated.\n\n"
            "## 9. Real-World Example\nImagine an open-book exam where a college student consults a university handbook.\n\n"
            "## 10. Technical Example or Simple Analogy\nA librarian finding a specific chapter index card.\n\n"
            "## 11. Key Components\nChunking, Embeddings, Vector Database, Retriever, LLM.\n\n"
            "## 12. Practical Applications\nCustomer support bots, college prospectus helpers, legal research assistants.\n\n"
            "## 13. Common Misconceptions\nRAG does not train the model weights; it simply gives it open-book context.\n\n"
            "## 14. Summary\nRAG combines search with generation to prevent false answers.\n\n"
            "## 15. Key Terms Explained\nChunking: cutting text into bite-sized pieces. Embeddings: number codes representing meaning. Vector Database: digital storage for embeddings.\n\n"
            "## 16. Knowledge Check / Quiz\n1. What does R in RAG stand for? A) Running B) Retrieval C) Reading\n\n"
            "## 17. Answers to the Quiz\n1. B - Retrieval.\n"
        )


def get_llm_client(
    provider: str | None = None,
    api_key: str | None = None,
    model_name: str | None = None,
    force_mock: bool = False
) -> BaseLLMClient:
    """Factory function returning the active LLM client based on provider."""
    settings = get_settings()
    active_provider = (provider or settings.llm_provider).lower()

    if force_mock:
        return MockLLMClient()

    if active_provider == "gemini":
        key = api_key or settings.gemini_api_key
        if not key:
            logger.info("Using MockLLMClient (no Gemini API key)")
            return MockLLMClient()
        return GeminiLLMClient(api_key=key, model_name=model_name or settings.gemini_model)
    else:
        key = api_key or settings.groq_api_key
        if not key:
            logger.info("Using MockLLMClient (no Groq API key)")
            return MockLLMClient()
        return GroqLLMClient(api_key=key, model_name=model_name or settings.groq_model)
