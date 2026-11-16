# LessonForge AI — Mandatory Quality Evaluation Rubric

## 1. Principles of Evaluation

The core philosophical differentiator of LessonForge AI is that **evaluation is an independent, non-negotiable hard gate**:
1. **Strict Binary Scoring**: Every checkpoint produces strictly either `PASS` or `FAIL`. No partial credit, numeric ratings (e.g. 7/10), or vague middle states.
2. **Zero Score-Averaging**: A lesson passes if and only if **18 out of 18 checkpoints** evaluate to `PASS`. If 17 pass and 1 fails, the entire generation is rejected (`FAIL`).
3. **Structured Evidentiary Rigor**: Every checkpoint result must cite verbatim or paraphrased evidence from the generated text, explain why it passed or failed, and provide an actionable, prescriptive suggestion whenever a failure occurs.
4. **Independent Critic Prompting**: The evaluator is executed under an adversarial critic persona, isolated from the generator prompt.

---

## 2. The 18 Checkpoints Across 6 Quality Dimensions

| Dimension | ID | Checkpoint Name | Description | Pass Criteria | Fail Criteria |
|---|---|---|---|---|---|
| **A. Technical Accuracy & Grounding** | `ACC_01` | Topic Definition Accuracy | Definition of topic is technically precise and correct according to authoritative references. | Accurately defines RAG (retrieval, augmentation, generation). | Inaccurate definition, conflating RAG with fine-tuning or web scraping. |
| | `ACC_02` | Mechanism Explanation Accuracy | Explanation of how the concept functions under the hood is mechanically valid. | Accurately describes chunking, vector embedding, similarity search, prompt augmentation. | Erroneous mechanical claims (e.g. "vectors store words directly"). |
| | `ACC_03` | Non-Misleading Technical Claims | Examples, comparisons, and claims do not mislead or overpromise. | Clearly identifies when LLM hallucination occurs and how context mitigates it. | Claims RAG makes an LLM 100% bug-free or modifies base weights permanently. |
| | `ACC_04` | Grounded Factual Claims | Factual claims match configured references or are explicitly flagged as analogies. | Technical mechanics align with standard RAG architecture literature. | Hallucinated technical protocols or inaccurate architectural claims. |
| **B. Beginner-Friendly Language** | `BEG_01` | Zero Prior Knowledge Baseline | Assumes zero prior computer science, AI, or advanced mathematics background. | Teaches from first principles; explains what an LLM or prompt is before deep mechanics. | Assumes familiarity with Python, APIs, matrices, or neural networks. |
| | `BEG_02` | Appropriate Vocabulary & Phrasing | Sentences and vocabulary are tailored to a non-native English 12th-grade graduate. | Short, active sentences; simple conversational English; clear definitions. | Hyper-academic syntax, dense collegiate prose, or esoteric idioms. |
| | `BEG_03` | Accessible Concept Translation | Complex technical concepts are translated into plain everyday terms. | Explains embeddings as "fingerprints of meaning" or "library numbers". | Uses raw mathematical jargon (dot product, high-dimensional space) without translation. |
| | `BEG_04` | No Unnecessary Pre-requisites | Does not require prerequisite coding, database setup, or terminal tools. | Teaches conceptual architecture clearly without requiring coding execution. | Instructs learner to clone git repos or configure SQL servers to understand concept. |
| **C. Teaching Through Examples** | `EXA_01` | Relatable Real-World Analogy | Contains at least one vivid, real-world everyday analogy. | Uses student consulting a college handbook, open-book exam, or librarian analogy. | Missing real-world analogy or uses highly esoteric domain examples. |
| | `EXA_02` | Step-by-Step Workflow Walkthrough | Walks through the end-to-end user query journey in logical order. | User asks question -> retrieval fetches chunks -> prompt augmented -> LLM answers. | Jumbled steps or omission of prompt augmentation step. |
| | `EXA_03` | Reinforcing Educational Examples | Examples directly reinforce and clarify the specific technical components. | Relates chunking to tearing a long manual into readable pages. | Disconnected examples that confuse rather than clarify the mechanism. |
| **D. Clarity & Jargon Management** | `CLR_01` | Immediate Jargon Demystification | Every technical term introduced is explained immediately upon first appearance. | Explains "chunking", "embeddings", "vector database" right when first mentioned. | Drops terms like "cosine similarity" or "tokenization" without inline explanation. |
| | `CLR_02` | Self-Contained Comprehension | Explanations can be completely understood without searching external sites. | Learner can read the lesson from start to finish with zero unanswered terms. | Directs reader to "look up how transformers work online". |
| | `CLR_03` | Avoidance of Unnecessary Complexity | Avoids redundant repetition, circular definitions, and filler text. | Concise, focused paragraphs that build progressively without circling back aimlessly. | Rambling text, repeated paragraphs, or bloated filler. |
| **E. Coverage & Completeness** | `COV_01` | Comprehensive Core Concept Coverage | Covers what RAG means, why needed, problems with vanilla LLMs, and all pipeline stages. | All 17 mandatory sections and all core RAG pipeline stages present. | Omits key concepts like vector database, chunking, or comparison with plain LLM. |
| | `COV_02` | Triad of What, Why, and How | Explicitly answers: What is it? Why do we need it? How does it work? | Dedicated sections addressing all three dimensions clearly. | Explains how it works without ever explaining why someone needs it. |
| | `COV_03` | Practical Tradeoffs & Summary | Includes practical applications, limitations, and a consolidated summary. | Explains when to use RAG, costs/delays, limitations, and key takeaway summary. | Completely ignores limitations or leaves out practical applications. |
| **F. Coherent Teaching Flow** | `FLO_01` | Logical Pedagogical Progression | Progresses logically from everyday intuition to technical breakdown to recap. | Intuition -> High-level concept -> Mechanical components -> End-to-end pipeline -> Quiz. | Jumps straight into vector database indexing before explaining what a query is. |

---

## 3. Evaluator Pydantic Schema Specification

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "EvaluationReport",
  "type": "object",
  "properties": {
    "overall_status": {
      "type": "string",
      "enum": ["PASS", "FAIL"]
    },
    "passed_count": { "type": "integer", "minimum": 0, "maximum": 18 },
    "failed_count": { "type": "integer", "minimum": 0, "maximum": 18 },
    "checkpoints": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "id": { "type": "string" },
          "dimension": { "type": "string" },
          "name": { "type": "string" },
          "status": { "type": "string", "enum": ["PASS", "FAIL"] },
          "evidence": { "type": "string" },
          "reason": { "type": "string" },
          "suggestion": { "type": ["string", "null"] }
        },
        "required": ["id", "dimension", "name", "status", "evidence", "reason"]
      }
    }
  },
  "required": ["overall_status", "passed_count", "failed_count", "checkpoints"]
}
```
