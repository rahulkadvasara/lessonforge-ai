# LessonForge AI — Technical Decisions & Architecture Trade-offs

## 1. Architectural Decisions

### 1.1 Orchestration Framework: LangGraph vs. Alternatives
- **Decision**: Select **LangGraph** (StateGraph) for agent workflow orchestration.
- **Rationale**:
  - LangGraph provides first-class support for cyclic graphs, which is the foundational pattern of a generate-evaluate-regenerate feedback loop.
  - LangChain's standard LCEL chains or legacy `AgentExecutor` are strictly acyclic or difficult to control with hard state checkpoints.
  - Alternatives like CrewAI or Autogen carry heavier abstractions, conversational baggage, and opaque internal prompts. LangGraph allows explicit node definitions, fine-grained state schemas, deterministic conditional routing, and transparent error handling.
- **Trade-off**: Requires explicit state definitions and careful schema modeling, but delivers 100% deterministic workflow boundaries.

### 1.2 LLM Provider: Groq Cloud API with Multi-Provider Abstraction
- **Decision**: Integrate **Groq Cloud API** via an extensible provider abstraction (`BaseLLMClient`), defaulting to fast, capable open-weights models (`openai/gpt-oss-120b` or `openai/gpt-oss-20b`).
- **Rationale**:
  - Evaluator and generator loops require high token-throughput and minimal latency so users don't wait minutes per evaluation cycle. Groq provides ultra-fast inference (hundreds of tokens/second on LPU).
  - Encapsulating the client behind `BaseLLMClient` ensures zero lock-in: swapping to OpenAI, Anthropic, or an offline Ollama backend requires implementing only a single interface class.
  - Configurable strictly through environment variables (`GROQ_API_KEY`, `GROQ_MODEL`, `LLM_TEMPERATURE`). Zero hardcoding of credentials.

### 1.3 State Persistence: SQLite vs. NoSQL / Vector Stores
- **Decision**: Use **SQLite** via standard Python `sqlite3` for persistent application memory.
- **Rationale**:
  - The assessment mandates persistence across application restarts for generation runs, versioned lessons, evaluation logs, rejection histories, user feedback, and learned insights.
  - SQLite requires zero external services or daemon processes, runs everywhere without Docker, has ACID compliance, and supports relational queries across runs, versions, and checkpoints.
  - NoSQL or pure JSON files lack transaction safety, indexing, and structured analytics capabilities needed for the self-evolution engine.

### 1.4 Hard Gate Evaluator: Binary (PASS/FAIL) vs. Averaged Numeric Scores
- **Decision**: Enforce an uncompromising **18-checkpoint binary (PASS/FAIL) hard gate**. If any checkpoint fails, the overall status is strictly `FAIL`.
- **Rationale**:
  - In educational content generation, an average score of "85%" can easily hide a catastrophic factual hallucination or an incomprehensible section that leaves a beginner completely lost.
  - Averaged scores create vague, un-actionable feedback. Binary checkpoints with explicit `evidence`, `reason`, and `suggestion` provide pinpoint feedback for the regeneration engine.
- **Trade-off**: Increases the probability of initial generation failure, but ensures that an `APPROVED` status signifies genuine compliance with all pedagogical and technical benchmarks.

### 1.5 Grounding Mechanism: Curated Local References vs. Heavy Vector DB
- **Decision**: Curate an authoritative reference corpus in `data/references/` with a lightweight, transparent retrieval extraction service.
- **Rationale**:
  - The goal is grounding technical accuracy for the topic (RAG) against authoritative literature (Lewis et al. 2020 RAG paper, LangChain docs) without over-engineering an unnecessary external vector database infrastructure for the generator itself.
  - Keeps local installation instantaneous and 100% reliable on any laptop without spinning up Chroma/Qdrant servers.

### 1.6 Bounded Regeneration Strategy
- **Decision**: Enforce a strict bound: Attempt 1 (Initial Generation), Attempt 2 (First Retry), Attempt 3 (Second Retry). Hard maximum of 2 retries (3 generations total).
- **Rationale**:
  - Guarantees termination: the system cannot enter an infinite loop.
  - If a lesson fails all 3 attempts, it is finalized with status `NEEDS_HUMAN_REVIEW` rather than falsely stamped as approved.

### 1.7 UI Architecture: Streamlit
- **Decision**: Multi-page/tab modern Streamlit dashboard with real-time workflow telemetry.
- **Rationale**:
  - Allows rapid, rich, interactive inspection of complex JSON reports, side-by-side diffs of regenerated versions, and live agent step progress without complex frontend build toolchains.
