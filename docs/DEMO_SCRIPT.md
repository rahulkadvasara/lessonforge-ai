# LessonForge AI — Video Demonstration Script (3–5 Minutes)

This script provides a structured walkthrough for demonstrating the **LessonForge AI** system in a screen recording or live presentation.

---

## Part 1: Project Overview & Problem Statement (0:00 – 0:45)
**Visual**: Show Streamlit Dashboard Overview with KPIs and system architecture diagram.
**Narration**:
> "Hello! Today I'm presenting **LessonForge AI**, an autonomous, self-evaluating GenAI content generator designed for beginners.
> 
> Most educational content generation today relies on a single LLM prompt, which frequently hallucinates, introduces unexplained technical jargon, or averages out low scores.
> 
> LessonForge AI solves this by implementing a genuine **agentic generate → evaluate → regenerate loop** orchestrated by LangGraph. It subjects every lesson to a strict, non-negotiable **18-checkpoint binary quality rubric**. If even one checkpoint fails, the lesson is rejected, actionable suggestions are extracted, and the lesson is automatically regenerated—bounded to a maximum of 2 retries."

---

## Part 2: Architecture & Persona Setup (0:45 – 1:30)
**Visual**: Navigate to **✍️ Generate Lesson** tab. Expand Learner Profile.
**Narration**:
> "Our default learner profile is tailored to a 12th-grade graduate from India with limited English vocabulary, a non-English-medium background, zero prior technical experience, and a desire to enter AI.
> 
> The topic is 'Introduction to RAG (Retrieval-Augmented Generation)'. 
> Notice in the sidebar we can configure the Groq Cloud model—defaulting to `openai/gpt-oss-120b`—or toggle Offline/Mock Mode for deterministic test demonstrations.
> We set the Max Regeneration Retries to 2."

---

## Part 3: Live Agentic Workflow Execution (1:30 – 2:30)
**Visual**: Click **'Start Agentic Generation & Evaluation Workflow'**. Show the live status box expanding with stage-by-stage events.
**Narration**:
> "Let's click Start. Notice the live LangGraph execution events:
> 1. **Input Validation**: Sanitizes topic and initializes the SQLite run record.
> 2. **Memory Retrieval**: Pulls historical rejection insights and authoritative reference context from Lewis et al. 2020.
> 3. **Lesson Generation**: Creates the initial complete 17-section lesson.
> 4. **Quality Gate Audit**: An independent evaluator agent audits the text against all 18 checkpoints.
> 5. When any checkpoint fails—such as unexplained embedding jargon—the workflow enters **Regeneration**, incorporating evaluator feedback to produce a revised lesson.
> 6. Once all 18 checkpoints pass, or the retry limit is reached, memory is updated and exports are generated."

---

## Part 4: Evaluation Dashboard & Rejection Logs (2:30 – 3:30)
**Visual**: Click on **⚖️ Evaluation Dashboard**, expand dimensions, then navigate to **🛑 Rejection Log**.
**Narration**:
> "Let's look at the Evaluation Dashboard. We see the clear PASS/FAIL banner, passed/failed checkpoint counts, and a breakdown across all 6 quality dimensions:
> - Technical Accuracy & Grounding
> - Beginner-Friendly Language
> - Teaching Through Examples
> - Clarity & Jargon Management
> - Coverage & Completeness
> - Coherent Teaching Flow
> 
> Under the Rejection Log tab, you see the exact audit trail: which checkpoint IDs failed, cited evidence from the lesson, evaluator reasoning, and the exact remediation feedback provided to the generator."

---

## Part 5: Final Lesson Viewer, Exports & Memory (3:30 – 4:45)
**Visual**: Navigate to **📖 Final Lesson Viewer**, show download buttons, then switch to **🧠 Memory & Learning**.
**Narration**:
> "Under the Final Lesson Viewer, an approved lesson is presented with Markdown and JSON report download options. Notice that every technical concept is explained immediately with simple analogies, such as a college student consulting a university handbook.
> 
> Finally, in the **🧠 Memory & Learning** section, all insights survive application restarts in SQLite. The Self-Evolution Engine analyzes repeated rejection patterns to proactively instruct future generation runs. We can also submit human-in-the-loop thumbs up/down feedback."

---

## Part 6: Closing Summary & Test Suite (4:45 – 5:00)
**Visual**: Quick terminal view showing `python -m pytest` with 19 passed tests.
**Narration**:
> "The entire test suite covers all 12 mandatory scenarios with 100% pass rate. 
> Thank you for reviewing LessonForge AI!"
