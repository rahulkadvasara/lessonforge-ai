"""LangGraph StateGraph construction and compilation for LessonForge AI."""
from langgraph.graph import StateGraph, START, END
from src.graph.state import WorkflowState
from src.graph.nodes import WorkflowNodes
from src.services.llm_service import BaseLLMClient


def decide_after_validation(state: WorkflowState) -> str:
    """Route after input validation."""
    if state.get("final_status") == "FAILED_INPUT":
        return "finalize"
    return "memory_retrieval"


def decide_after_evaluation(state: WorkflowState) -> str:
    """
    Decide whether to pass, regenerate, or mark as needing human review.
    Enforces the strict hard-gate and bounded retry limit.
    """
    eval_res = state.get("evaluation_result", {})
    status = eval_res.get("overall_status", "FAIL")

    if status == "PASS":
        return "memory_update"

    current_attempt = state.get("current_attempt", 1)
    max_retries = state.get("max_retries", 2)

    # If current attempt is <= max_retries, we still have retries available
    # e.g., attempt 1 with max_retries 2 -> retry (to reach attempt 2)
    # attempt 2 with max_retries 2 -> retry (to reach attempt 3)
    # attempt 3 with max_retries 2 -> exhausted!
    if current_attempt <= max_retries:
        return "regeneration"
    else:
        return "record_failure"


def create_workflow_graph(
    nodes: WorkflowNodes | None = None,
    llm_client: BaseLLMClient | None = None
):
    """Build and compile the complete LangGraph StateGraph."""
    workflow_nodes = nodes or WorkflowNodes(llm_client=llm_client)

    builder = StateGraph(WorkflowState)

    # Register Nodes
    builder.add_node("input_validation", workflow_nodes.input_validation_node)
    builder.add_node("memory_retrieval", workflow_nodes.memory_retrieval_node)
    builder.add_node("lesson_generator", workflow_nodes.lesson_generator_node)
    builder.add_node("content_evaluator", workflow_nodes.content_evaluator_node)
    builder.add_node("regeneration", workflow_nodes.regeneration_node)
    builder.add_node("record_failure", workflow_nodes.record_failure_node)
    builder.add_node("memory_update", workflow_nodes.memory_update_node)
    builder.add_node("finalize", workflow_nodes.finalize_node)

    # Define Edges
    builder.add_edge(START, "input_validation")

    builder.add_conditional_edges(
        "input_validation",
        decide_after_validation,
        {
            "memory_retrieval": "memory_retrieval",
            "finalize": "finalize"
        }
    )

    builder.add_edge("memory_retrieval", "lesson_generator")
    builder.add_edge("lesson_generator", "content_evaluator")

    # Conditional Routing based on Evaluation
    builder.add_conditional_edges(
        "content_evaluator",
        decide_after_evaluation,
        {
            "memory_update": "memory_update",
            "regeneration": "regeneration",
            "record_failure": "record_failure"
        }
    )

    # Regeneration cycles back to evaluator (Agentic Loop!)
    builder.add_edge("regeneration", "content_evaluator")

    builder.add_edge("record_failure", "memory_update")
    builder.add_edge("memory_update", "finalize")
    builder.add_edge("finalize", END)

    return builder.compile()
