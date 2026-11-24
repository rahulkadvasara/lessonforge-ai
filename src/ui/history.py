"""Run History and Rejection Log UI components."""
import streamlit as st
import json
from src.memory.repository import MemoryRepository
from src.services.export_service import ExportService


def render_rejection_logs_view(repo: MemoryRepository, active_run_id: str | None = None):
    """Render audit logs for all failed attempts and regeneration feedback."""
    st.subheader("Rejection Logs & Iteration Audit Trail")

    all_runs = repo.list_runs(limit=30)
    if not all_runs:
        st.info("No runs found in database. Run a generation first.")
        return

    run_options = {f"{r['created_at']} | {r['topic']} ({r['final_status']})": r["run_id"] for r in all_runs}
    
    default_idx = 0
    if active_run_id:
        for idx, (label, rid) in enumerate(run_options.items()):
            if rid == active_run_id:
                default_idx = idx
                break

    selected_label = st.selectbox("Select Run to Inspect Rejections:", list(run_options.keys()), index=default_idx)
    target_run_id = run_options[selected_label]

    logs = repo.get_rejection_logs(run_id=target_run_id)
    run_meta = repo.get_run(target_run_id)

    if not logs:
        status_text = run_meta.get("final_status") if run_meta else "APPROVED"
        if status_text == "APPROVED":
            st.success(f"🎉 **Zero Rejections for Run `{target_run_id[:12]}...`!** The lesson passed all 18 mandatory quality checkpoints on Attempt #1 without requiring any regeneration.")
        else:
            st.info(f"No rejection records logged for run `{target_run_id[:12]}...`.")
        return

    st.markdown(f"**Found {len(logs)} Rejection Event(s) for Run `{target_run_id[:12]}...`**")

    for i, r in enumerate(logs):
        attempt = r.get("attempt_number", 1)
        st.markdown(f"### 🛑 Rejection Record: Attempt #{attempt}")
        
        cids = r.get("failed_checkpoint_ids", [])
        st.error(f"Failed Checkpoint IDs: `{', '.join(cids)}`")

        reasons = r.get("reasons", [])
        suggestions = r.get("suggestions", [])

        col_r, col_s = st.columns(2)
        with col_r:
            st.markdown("**Root Causes Identified:**")
            for reason in reasons:
                st.markdown(f"- {reason}")
        
        with col_s:
            st.markdown("**Remediation Feedback Sent to Generator:**")
            for sugg in suggestions:
                st.markdown(f"- 💡 {sugg}")

        changes = r.get("changes_made")
        if changes:
            st.info(f"**Changes targeted in next iteration:** {changes}")

        st.markdown("---")


def render_run_history_view(repo: MemoryRepository, export_service: ExportService):
    """Render searchable run history, version comparison, and artifact downloads."""
    st.subheader("Historical Generation Runs")

    runs = repo.list_runs(limit=50)
    if not runs:
        st.info("No historical runs found in database.")
        return

    # Select run to inspect
    run_options = {f"{r['created_at']} | {r['topic']} ({r['final_status']})": r["run_id"] for r in runs}
    selected_label = st.selectbox("Select a Generation Run to Inspect:", list(run_options.keys()))
    selected_run_id = run_options[selected_label]

    run_meta = repo.get_run(selected_run_id)
    versions = repo.get_lesson_versions(selected_run_id)
    evaluations = repo.get_evaluations_for_run(selected_run_id)
    rejections = repo.get_rejection_logs(selected_run_id)

    if not run_meta:
        st.error("Could not load run metadata.")
        return

    # Header metadata
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.write(f"**Topic:** {run_meta['topic']}")
    with c2:
        st.write(f"**Status:** `{run_meta['final_status']}`")
    with c3:
        st.write(f"**Attempts Used:** {run_meta['attempts_used']} / {run_meta['max_retries'] + 1}")
    with c4:
        st.write(f"**Date:** {run_meta['created_at']}")

    st.markdown("---")

    # Version comparison tabs
    st.markdown("### Version History & Iteration Comparison")
    if versions:
        version_tabs = st.tabs([f"Attempt #{v['attempt_number']} ({v['word_count']} words)" for v in versions])
        for idx, v in enumerate(versions):
            with version_tabs[idx]:
                st.markdown(f"**Version Generated at:** `{v['created_at']}` | **Length:** `{v['word_count']}` words")
                
                # Check evaluation result for this version
                matching_eval = next((e for e in evaluations if e["attempt_number"] == v["attempt_number"]), None)
                if matching_eval:
                    eval_badge = "✅ PASSED (18/18)" if matching_eval["overall_status"] == "PASS" else f"❌ FAILED ({matching_eval['failed_count']} Checkpoints)"
                    st.markdown(f"**Evaluation Result:** `{eval_badge}`")
                
                st.text_area(f"Lesson Text (Attempt #{v['attempt_number']})", value=v["lesson_content"], height=350, key=f"ver_view_{v['id']}")

    st.markdown("---")

    # Exports
    st.markdown("### Export Artifacts")
    latest_lesson = versions[-1]["lesson_content"] if versions else ""
    
    col_dl1, col_dl2 = st.columns(2)
    with col_dl1:
        st.download_button(
            label="📥 Download Approved Lesson (Markdown)",
            data=latest_lesson,
            file_name=f"lesson_{selected_run_id[:8]}.md",
            mime="text/markdown",
            use_container_width=True
        )

    with col_dl2:
        audit_payload = {
            "run": run_meta,
            "versions": versions,
            "evaluations": evaluations,
            "rejections": rejections
        }
        st.download_button(
            label="📥 Download Complete Audit Report (JSON)",
            data=json.dumps(audit_payload, indent=2, default=str),
            file_name=f"audit_{selected_run_id[:8]}.json",
            mime="application/json",
            use_container_width=True
        )
