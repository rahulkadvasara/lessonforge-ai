"""Mandatory 18-checkpoint evaluation rubric definition."""
from typing import List, Dict
from src.evaluation.schemas import CheckpointDefinition

RUBRIC_CHECKPOINTS: List[CheckpointDefinition] = [
    # A. Technical Accuracy and Grounding
    CheckpointDefinition(
        id="ACC_01",
        dimension="Technical Accuracy and Grounding",
        name="Topic Definition Accuracy",
        description="The definition of the topic is technically correct and precise.",
        pass_criteria="Correctly defines RAG as retrieval, augmentation, and generation without conceptual errors.",
        fail_criteria="Confuses RAG with fine-tuning, training from scratch, or pure web scraping."
    ),
    CheckpointDefinition(
        id="ACC_02",
        dimension="Technical Accuracy and Grounding",
        name="Mechanism Explanation Accuracy",
        description="The explanation of how the concept works is mechanically accurate.",
        pass_criteria="Accurately describes chunking, vector embeddings, similarity search, prompt injection, and LLM inference.",
        fail_criteria="Claims incorrect mechanics (e.g. vector database rewrites model weights, vectors store plain text files directly)."
    ),
    CheckpointDefinition(
        id="ACC_03",
        dimension="Technical Accuracy and Grounding",
        name="Non-Misleading Technical Claims",
        description="The examples and claims do not contain misleading or false technical promises.",
        pass_criteria="Accurately reflects limitations, hallucination risks, and trade-offs.",
        fail_criteria="Claims RAG makes an LLM 100% bug-free or guarantees perfect accuracy without exception."
    ),
    CheckpointDefinition(
        id="ACC_04",
        dimension="Technical Accuracy and Grounding",
        name="Grounded Factual Claims",
        description="Important factual claims are supported by reference literature or clearly identified as analogies.",
        pass_criteria="All technical assertions align with authoritative RAG literature (Lewis et al. 2020) and standard vector search principles.",
        fail_criteria="Hallucinates non-existent technical standards or misattributes core architectural functions."
    ),

    # B. Beginner-Friendly Language
    CheckpointDefinition(
        id="BEG_01",
        dimension="Beginner-Friendly Language",
        name="Zero Prior Knowledge Baseline",
        description="The lesson assumes zero prior computer science, AI, or advanced programming knowledge.",
        pass_criteria="Explains fundamental concepts (like what an AI or prompt is) before diving into internal pipelines.",
        fail_criteria="Assumes the learner already knows Python coding, API requests, vector math, or neural architectures."
    ),
    CheckpointDefinition(
        id="BEG_02",
        dimension="Beginner-Friendly Language",
        name="Appropriate Vocabulary and Phrasing",
        description="Sentences and vocabulary are appropriate for a 12th-grade graduate with non-English-medium background.",
        pass_criteria="Uses short, clear sentences and simple conversational English with direct phrasing.",
        fail_criteria="Uses high-brow academic prose, overly complex grammar, or confusing idioms."
    ),
    CheckpointDefinition(
        id="BEG_03",
        dimension="Beginner-Friendly Language",
        name="Accessible Concept Translation",
        description="Technical concepts are translated using intuitive, accessible explanations.",
        pass_criteria="Explains embeddings as 'fingerprints of meaning' or 'number codes' and vector databases as 'smart digital libraries'.",
        fail_criteria="Uses raw mathematical definitions (e.g., 'dot product in 1536-dimensional hyper-space') without intuition."
    ),
    CheckpointDefinition(
        id="BEG_04",
        dimension="Beginner-Friendly Language",
        name="No Unnecessary Technical Prerequisites",
        description="The lesson does not force unnecessary prerequisites onto the learner.",
        pass_criteria="Teaches concepts cleanly without demanding terminal setup, package installation, or coding environments.",
        fail_criteria="Requires the student to clone git repositories or write Python code to understand the concept."
    ),

    # C. Teaching Through Examples
    CheckpointDefinition(
        id="EXA_01",
        dimension="Teaching Through Examples",
        name="Relatable Real-World Analogy",
        description="At least one relatable real-world example/analogy is included.",
        pass_criteria="Features a relatable everyday scenario (e.g., open-book exam, student checking college prospectus, librarian finding books).",
        fail_criteria="Lacks any real-world analogy or uses esoteric domain examples that alienate beginners."
    ),
    CheckpointDefinition(
        id="EXA_02",
        dimension="Teaching Through Examples",
        name="Step-by-Step Technical Walkthrough",
        description="The main technical workflow is demonstrated step by step with concrete examples.",
        pass_criteria="Walks through question -> document chunking -> vector search -> prompt injection -> final answer generation.",
        fail_criteria="Jumps from user question directly to final answer without explaining the intermediate retrieval flow."
    ),
    CheckpointDefinition(
        id="EXA_03",
        dimension="Teaching Through Examples",
        name="Reinforcing Educational Examples",
        description="Examples correctly reinforce the specific concepts being taught.",
        pass_criteria="The examples directly illuminate why chunking, embedding, and context injection are needed.",
        fail_criteria="Examples contradict the technical concepts or confuse the learner."
    ),

    # D. Clarity and Jargon Management
    CheckpointDefinition(
        id="CLR_01",
        dimension="Clarity and Jargon Management",
        name="Immediate Jargon Demystification",
        description="No important technical term is introduced without immediate explanation.",
        pass_criteria="Terms like 'chunking', 'embeddings', 'vector database', 'semantic search', 'context injection' are explained the exact moment they appear.",
        fail_criteria="Drops technical buzzwords into paragraphs without defining them first or immediately alongside."
    ),
    CheckpointDefinition(
        id="CLR_02",
        dimension="Clarity and Jargon Management",
        name="Self-Contained Comprehension",
        description="The explanations are understandable without consulting external resources.",
        pass_criteria="A beginner can read the entire lesson and understand the full mechanism without Googling terms.",
        fail_criteria="Tells the reader to 'search Wikipedia' or 'read external docs' to understand key parts."
    ),
    CheckpointDefinition(
        id="CLR_03",
        dimension="Clarity and Jargon Management",
        name="Avoidance of Unnecessary Complexity",
        description="The content avoids unnecessary complexity, circular definitions, and repetition.",
        pass_criteria="Clear, structured, progressive explanation without bloat or circular logic.",
        fail_criteria="Loops repetitively over the same definition or fills space with redundant phrasing."
    ),

    # E. Coverage and Completeness
    CheckpointDefinition(
        id="COV_01",
        dimension="Coverage and Completeness",
        name="Comprehensive Core Concept Coverage",
        description="All essential topic-specific concepts are covered.",
        pass_criteria="Covers RAG meaning, vanilla LLM limitations, chunking, embeddings, vector DB, semantic search, prompt injection, and answer generation.",
        fail_criteria="Omits essential pipeline pillars such as embeddings, vector databases, or prompt augmentation."
    ),
    CheckpointDefinition(
        id="COV_02",
        dimension="Coverage and Completeness",
        name="Triad of What, Why, and How",
        description="The lesson explains what the concept is, why it matters, and how it works.",
        pass_criteria="Distinct sections explicitly addressing what RAG is, why it is critical, and how the pipeline works.",
        fail_criteria="Explains how it works mechanically but fails to explain why anyone needs it or what problems it solves."
    ),
    CheckpointDefinition(
        id="COV_03",
        dimension="Coverage and Completeness",
        name="Practical Tradeoffs and Summary",
        description="The lesson includes practical applications, limitations, and a meaningful summary.",
        pass_criteria="Details practical applications, real-world limitations (speed, cost, chunk quality), a clear summary, and a quiz.",
        fail_criteria="Leaves out limitations, practical use cases, or knowledge check quiz."
    ),

    # F. Coherent Teaching Flow
    CheckpointDefinition(
        id="FLO_01",
        dimension="Coherent Teaching Flow",
        name="Logical Pedagogical Progression",
        description="Concepts are introduced in a logical order, progressing from basic understanding to technical depth.",
        pass_criteria="Progresses smoothly: Everyday Intuition -> High-Level Concept -> Mechanical Components -> Step-by-Step Flow -> Quiz.",
        fail_criteria="Jumbles ordering (e.g. explains vector similarity algorithms before explaining why we want to find similar text)."
    ),
]

RUBRIC_MAP: Dict[str, CheckpointDefinition] = {cp.id: cp for cp in RUBRIC_CHECKPOINTS}
TOTAL_CHECKPOINTS_COUNT = len(RUBRIC_CHECKPOINTS)  # exactly 18
