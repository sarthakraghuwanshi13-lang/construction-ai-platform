"""Tabs driven by image analysis: safety/PPE, crack assessment, general multimodal analysis."""
from __future__ import annotations

import streamlit as st

from .. import prompts
from ..crack_rules import classify_width_mm
from ..llm import LLMClient
from ..projectdata import ProjectDataError, table_summary
from ..schemas import CrackReport, GeneralAnalysis, SafetyReport
from .common import (RISK_ICON, bullet_list, disclaimer, image_inputs, need_ai, project_context, run_ai, show_json)

ELEMENTS = ["Brick/block wall", "RC column", "RC beam", "RC slab / ceiling", "Foundation / plinth",
            "Plaster / finish", "Floor", "Other"]


def render_safety(client: LLMClient) -> None:
    st.subheader("🦺 Site safety & PPE analysis")
    st.caption("A vision-language model reviews site photos for PPE and visible hazards. "
               "It reports what it can see, not a certified inspection and not object-detection boxes.")
    ai_ok = need_ai(client)
    images = image_inputs("safety_imgs", "Site photo(s)", "Upload at least one site photo to analyze.")
    notes = st.text_area("Optional context (activity, area, number of workers)", key="safety_notes", height=70)
    if st.button("Analyze safety", type="primary", disabled=not (ai_ok and images), key="safety_go"):
        result = run_ai(lambda: client.generate_structured(
            SafetyReport, prompts.safety(notes, project_context()), images=images))
        if result:
            st.session_state["safety_result"] = result
    r = st.session_state.get("safety_result")
    if not r:
        return
    c1, c2 = st.columns(2)
    c1.metric("Overall risk", "%s %s" % (RISK_ICON.get(r.overall_risk, ""), r.overall_risk.title()))
    c2.metric("People visible", "unsure" if r.people_visible is None else r.people_visible)
    st.write(r.summary)
    if r.ppe:
        st.markdown("**PPE check**")
        st.dataframe([{"PPE item": p.item, "Status": p.status, "Note": p.note} for p in r.ppe], hide_index=True)
    if r.hazards:
        st.markdown("**Hazards**")
        for h in r.hazards:
            with st.expander("%s %s: %s" % (RISK_ICON.get(h.severity, ""), h.severity.title(), h.description)):
                st.write("Recommendation: " + h.recommendation)
    bullet_list("Immediate actions", r.immediate_actions)
    if r.limitations:
        st.caption("Limitations: " + r.limitations)
    disclaimer("AI visual assessment only. A competent safety officer must verify conditions on site.")
    show_json(r, "safety_report.json", "safety")


def render_crack(client: LLMClient) -> None:
    st.subheader("🧱 Crack detection, severity & corrective actions")
    st.caption("The model describes visible cracks and suggests causes/actions. It cannot measure width from a photo "
               "unless a scale reference is visible, so enter a measured width if you have one.")
    ai_ok = need_ai(client)
    images = image_inputs("crack_imgs", "Crack photo(s), ideally with a ruler/coin for scale",
                          "Upload at least one close-up photo of the crack.")
    c1, c2 = st.columns(2)
    element = c1.selectbox("Building element", ELEMENTS, key="crack_element")
    location = c2.text_input("Location (e.g. 2nd floor east wall, near window)", key="crack_loc")
    known = st.checkbox("I measured the maximum crack width", key="crack_known")
    width = st.number_input("Measured width (mm)", min_value=0.0, max_value=200.0, value=0.5, step=0.1,
                            disabled=not known, key="crack_width")
    age = st.text_input("Building age / recent events (new construction, nearby excavation, flooding...)", key="crack_age")
    notes = st.text_area("Other notes", key="crack_notes", height=60)
    measured = float(width) if known else None
    if st.button("Assess crack", type="primary", disabled=not (ai_ok and images), key="crack_go"):
        result = run_ai(lambda: client.generate_structured(
            CrackReport, prompts.crack(element, location, measured, age, notes, project_context()), images=images))
        if result:
            st.session_state["crack_result"] = (result, measured)
    saved = st.session_state.get("crack_result")
    if not saved:
        return
    r, measured_w = saved
    c1, c2, c3 = st.columns(3)
    c1.metric("Severity (AI)", "%s %s" % (RISK_ICON.get(r.severity, ""), r.severity.title()))
    c2.metric("Engineer needed", "Yes" if r.needs_structural_engineer else "Not indicated")
    c3.metric("AI confidence", r.confidence.title())
    if r.needs_structural_engineer:
        st.warning("The model recommends a structural engineer's inspection.")
    st.write("**Type:** %s  \n**Location:** %s" % (r.crack_type, r.location_description or "n/a"))
    if r.estimated_width_mm is not None:
        st.write("**Estimated width (from scale reference in photo):** %.2f mm" % r.estimated_width_mm)
    st.write("**Rationale:** " + r.severity_rationale)
    if measured_w is not None:
        cat, label, meaning = classify_width_mm(measured_w)
        st.info("Rule-based cross-check for your measured %.2f mm: **Category %d - %s**. %s "
                "(BRE Digest 251 style masonry classification; indicative only.)" % (measured_w, cat, label, meaning))
    bullet_list("Probable causes (most likely first)", r.probable_causes)
    bullet_list("Corrective actions", r.corrective_actions)
    if r.monitoring_advice:
        st.write("**Monitoring:** " + r.monitoring_advice)
    if r.limitations:
        st.caption("Limitations: " + r.limitations)
    disclaimer("Not a structural assessment. Wide, growing, diagonal or load-bearing cracks need a qualified engineer.")
    show_json(r, "crack_report.json", "crack")


def render_general(client: LLMClient) -> None:
    st.subheader("🔎 Multimodal analysis (images + project data → JSON)")
    st.caption("Free-form analysis of any construction images and/or a CSV/JSON project file. "
               "The reply is validated against a fixed schema.")
    ai_ok = need_ai(client)
    images = image_inputs("general_imgs", "Image(s) (optional)")
    data_file = st.file_uploader("Project data file (CSV or JSON, optional)", type=["csv", "json"], key="general_data")
    data_text = ""
    if data_file is not None:
        try:
            data_text = table_summary(data_file.getvalue(), data_file.name)
            with st.expander("Data sent to the model (truncated summary)"):
                st.code(data_text)
        except ProjectDataError as exc:
            st.error(str(exc))
    instructions = st.text_area("What should the AI analyze?", key="general_instr", height=90,
                                placeholder="e.g. Compare progress in these photos with the schedule and flag delays.")
    ready = ai_ok and bool(instructions.strip()) and (bool(images) or bool(data_text))
    if st.button("Run analysis", type="primary", disabled=not ready, key="general_go"):
        ctx = project_context() + (("\n" + data_text) if data_text else "")
        result = run_ai(lambda: client.generate_structured(
            GeneralAnalysis, prompts.general(instructions, ctx), images=images))
        if result:
            st.session_state["general_result"] = result
    if not ready:
        st.caption("Provide instructions plus at least one image or data file.")
    r = st.session_state.get("general_result")
    if not r:
        return
    st.write(r.summary)
    if r.observations:
        st.dataframe([{"Item": o.item, "Detail": o.detail, "Confidence": o.confidence} for o in r.observations],
                     hide_index=True)
    bullet_list("Risks", r.risks)
    bullet_list("Recommended actions", r.recommended_actions)
    bullet_list("Follow-up questions", r.follow_up_questions)
    if r.limitations:
        st.caption("Limitations: " + r.limitations)
    show_json(r, "analysis.json", "general")
