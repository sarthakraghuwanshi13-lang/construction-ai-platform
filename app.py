"""AI-Powered Multimodal Construction Intelligence Platform: Streamlit entry point.

Run locally:  streamlit run app.py
"""
from __future__ import annotations

import streamlit as st
from pydantic import ValidationError

st.set_page_config(page_title="Construction Intelligence", page_icon="🏗️", layout="wide")

from construction_ai import __version__  # noqa: E402
from construction_ai.config import DEFAULT_MODEL, get_secret  # noqa: E402
from construction_ai.projectdata import (  # noqa: E402
    ProjectDataError, ProjectProfile, profile_from_json, profile_to_json, table_summary)
from construction_ai.ui import cost_tabs, ops_tabs, vision_tabs  # noqa: E402
from construction_ai.ui.common import get_client  # noqa: E402

PROFILE_DEFAULTS = {
    "p_name": "", "p_location": "", "p_type": "Residential building", "p_area": 0.0,
    "p_unit": "sq ft", "p_floors": 1, "p_currency": "INR", "p_notes": "",
}


def _import_profile() -> None:
    up = st.sidebar.file_uploader("Import profile (JSON)", type=["json"], key="profile_upload")
    if up is None:
        return
    sig = (up.name, up.size)
    if st.session_state.get("_profile_sig") == sig:
        return
    st.session_state["_profile_sig"] = sig
    try:
        p = profile_from_json(up.getvalue())
    except ProjectDataError as exc:
        st.sidebar.error(str(exc))
        return
    st.session_state.update(
        p_name=p.name, p_location=p.location, p_type=p.project_type, p_area=float(p.built_up_area or 0.0),
        p_unit=p.area_unit, p_floors=p.floors, p_currency=p.currency, p_notes=p.notes)
    st.sidebar.success("Profile imported.")


def sidebar() -> None:
    sb = st.sidebar
    sb.title("🏗️ Construction Intelligence")
    sb.caption("v%s" % __version__)
    for k, v in PROFILE_DEFAULTS.items():
        st.session_state.setdefault(k, v)

    # --- AI status / key ----------------------------------------------------
    sb.subheader("AI connection")
    providers = ["Anthropic Claude", "Google Gemini (Free tier)", "Demo Mode (Simulated AI)"]
    default_p = 0
    if not (get_secret("ANTHROPIC_API_KEY") or st.session_state.get("api_key_override")):
        if get_secret("GEMINI_API_KEY"):
            default_p = 1
    selected_p = sb.selectbox("AI provider", providers, index=default_p, key="provider_choice")

    if selected_p == "Anthropic Claude":
        sb.text_input("Anthropic session API key (optional)", type="password", key="api_key_input",
                      help="Used only in this browser session. Prefer ANTHROPIC_API_KEY via env var or Streamlit Secrets.")
        st.session_state["api_key_override"] = st.session_state.get("api_key_input", "").strip()
        client = get_client()
        if client.available:
            sb.success("AI enabled · model: %s" % client.model)
        else:
            sb.warning("AI not configured. Calculators, scheduling and weather still work.")
    elif selected_p == "Google Gemini (Free tier)":
        sb.text_input("Gemini session API key (optional)", type="password", key="gemini_key_input",
                      help="Free key from https://aistudio.google.com/apikey. Or set GEMINI_API_KEY in Streamlit Secrets.")
        client = get_client()
        if client.available:
            sb.success("AI enabled · model: %s" % client.model)
        else:
            sb.warning("Gemini not configured. Paste a free key from Google AI Studio.")
    else:  # Demo Mode
        client = get_client()
        sb.info("ℹ️ Demo Mode: realistic simulated AI output. No API credits or keys needed.")

    # --- project profile ----------------------------------------------------
    sb.subheader("Project profile")
    _import_profile()
    sb.text_input("Project name", key="p_name")
    sb.text_input("Location", key="p_location")
    sb.text_input("Project type", key="p_type")
    c1, c2 = sb.columns(2)
    c1.number_input("Total built-up area (0 = unknown)", min_value=0.0, step=50.0, key="p_area")
    c2.selectbox("Unit", ["sq ft", "sq m"], key="p_unit")
    c1, c2 = sb.columns(2)
    c1.number_input("Floors", min_value=1, max_value=100, step=1, key="p_floors")
    c2.text_input("Currency", key="p_currency")
    sb.text_area("Notes", key="p_notes", height=70)
    try:
        profile = ProjectProfile(
            name=st.session_state["p_name"], location=st.session_state["p_location"],
            project_type=st.session_state["p_type"] or "Construction project",
            built_up_area=st.session_state["p_area"] or None, area_unit=st.session_state["p_unit"],
            floors=int(st.session_state["p_floors"]), currency=st.session_state["p_currency"] or "INR",
            notes=st.session_state["p_notes"])
        st.session_state["profile"] = profile
        sb.download_button("Export profile (JSON)", profile_to_json(profile), file_name="project_profile.json",
                           mime="application/json")
    except ValidationError:
        sb.error("Profile has invalid values; using the last valid profile.")

    # --- structured project data -------------------------------------------
    sb.subheader("Project data (optional)")
    data = sb.file_uploader("CSV / JSON (e.g. BOQ, schedule, log)", type=["csv", "json"], key="project_data")
    st.session_state["extra_context"] = ""
    if data is not None:
        try:
            st.session_state["extra_context"] = table_summary(data.getvalue(), data.name)
            sb.caption("Included as context in AI requests (truncated to keep token use low).")
        except ProjectDataError as exc:
            sb.error(str(exc))

    with sb.expander("About & limitations"):
        st.markdown(
            "- Streamlit app; the AI backend is the Anthropic API (multimodal). No separate React/FastAPI server.\n"
            "- Storage = this browser session plus JSON/CSV export (Streamlit Cloud disk is ephemeral).\n"
            "- AI output is validated against schemas but can still be wrong. It does **not** replace safety officers, "
            "structural engineers or licensed valuers.\n"
            "- No object-detection model is bundled: image findings are a vision-language model's description.\n"
            "- Valuation has no live market data. Cost rates are placeholders.\n"
            "- Default model: `%s` (override with `ANTHROPIC_MODEL`)." % get_secret("ANTHROPIC_MODEL", DEFAULT_MODEL))


def _safe(fn, *args) -> None:
    """Render a tab; a bug in one tab must never take down the whole app."""
    try:
        fn(*args)
    except Exception as exc:  # pragma: no cover - defensive UI guard
        st.error("This section hit an unexpected error (%s). Other sections are unaffected." % type(exc).__name__)


def main() -> None:
    sidebar()
    client = get_client()
    st.title("AI-Powered Multimodal Construction Intelligence Platform")
    st.caption("Site safety · crack assessment · valuation · estimation · planning · daily assistant · weather · knowledge")
    if client.provider == "demo":
        st.info("ℹ️ **Demo Mode active:** Displaying simulated AI results for review and demonstration. No API key or credits needed. Switch to live AI providers in the sidebar anytime.")

    names = ["🦺 Safety", "🧱 Cracks", "🏠 Valuation", "🧮 Estimator", "📅 Planning", "📝 Daily", "🌦️ Weather",
             "📚 Knowledge", "🔎 Analyzer"]
    tabs = st.tabs(names)
    with tabs[0]:
        _safe(vision_tabs.render_safety, client)
    with tabs[1]:
        _safe(vision_tabs.render_crack, client)
    with tabs[2]:
        _safe(cost_tabs.render_valuation, client)
    with tabs[3]:
        _safe(cost_tabs.render_estimator)
    with tabs[4]:
        _safe(ops_tabs.render_planning, client)
    with tabs[5]:
        _safe(ops_tabs.render_daily, client)
    with tabs[6]:
        _safe(ops_tabs.render_weather, client)
    with tabs[7]:
        _safe(ops_tabs.render_knowledge, client)
    with tabs[8]:
        _safe(vision_tabs.render_general, client)


main()
