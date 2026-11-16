"""Prompt templates for guided lesson regeneration after evaluation failure."""

REGENERATION_SYSTEM_PROMPT = """You are LessonForge AI's Master Pedagogical Content Generator in REVISION MODE.
Your previous generation was audited by our Independent Quality Evaluator and REJECTED due to specific quality and rubric failures.

YOUR MANDATE:
1. Carefully study every failed checkpoint, the quoted evidence, reasons, and actionable improvement recommendations.
2. Regenerate the ENTIRE lesson from start to finish.
3. DO NOT just append sentences to the end of the previous text. Produce a seamless, complete, cohesive, 17-section revised lesson.
4. PRESERVE sections that were praised or passed, but REVISE all weak or failed parts to strictly comply with the rubric.
5. Pay special attention to:
   - Explaining every technical term the moment it appears using plain analogies.
   - Ensuring language matches the 12th-grade Indian graduate persona (simple English, no unexplained jargon).
   - Ensuring complete coverage of all 17 mandatory sections.
"""

def build_regeneration_user_prompt(
    topic: str,
    learner_profile: dict,
    previous_lesson: str,
    failed_checkpoints: list[dict],
    attempt_number: int,
    max_retries: int
) -> str:
    issues_block = []
    for cp in failed_checkpoints:
        issues_block.append(
            f"❌ [{cp.get('id')}] {cp.get('name')} ({cp.get('dimension')}):\n"
            f"   - Issue Cited: {cp.get('reason')}\n"
            f"   - Remediation Suggestion: {cp.get('suggestion')}\n"
        )
    formatted_issues = "\n".join(issues_block)

    return f"""TOPIC: {topic}
REVISION ATTEMPT: {attempt_number} (Maximum allowed: {max_retries + 1})

TARGET LEARNER PROFILE:
- {learner_profile.get('target_audience')}
- {learner_profile.get('english_proficiency')}

PREVIOUS REJECTED LESSON:
----------------------------------------------------------------------
{previous_lesson}
----------------------------------------------------------------------

EVALUATOR REJECTION REPORT (You MUST fix all of these):
{formatted_issues}

INSTRUCTIONS FOR THIS REGENERATION:
1. Completely revise the lesson, thoroughly resolving every one of the cited failure points above.
2. Ensure all 17 mandatory sections are clearly present and fully developed.
3. Maintain accessible, simple English and intuitive analogies throughout.
Output the full, revised lesson now.
"""
