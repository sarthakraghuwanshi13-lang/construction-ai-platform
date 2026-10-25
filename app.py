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
from construction_ai.ui import cost_tabs, ops_tabs, vision_tabs  # noqa: E402
from construction_ai.llm import LLMClient, LLMError, LLMUnavailable  # noqa: E402

try:
    from construction_ai.llm import _generate_demo
except ImportError:
    _generate_demo = None


def _inline_demo(schema):
    """Fallback generator for demo mode if construction_ai is not yet updated on server."""
    name = schema.__name__
    if name == "SafetyReport":
        return schema.model_validate({
            "summary": "AI site safety inspection (Demo mode). 3 workers detected in active work zone. Hard hats and high-visibility vests observed; hand protection and perimeter guardrails require immediate attention.",
            "people_visible": 3,
            "overall_risk": "medium",
            "ppe": [
                {"item": "Hard Hat", "status": "present", "note": "Workers wearing approved hard hats"},
                {"item": "Hi-Vis Vest", "status": "present", "note": "Reflective class 2 high-visibility vests worn"},
                {"item": "Safety Boots", "status": "present", "note": "Steel-toe work boots visible"},
                {"item": "Safety Gloves", "status": "missing", "note": "Material handling observed without cut-resistant gloves"},
                {"item": "Eye Protection", "status": "missing", "note": "Safety glasses missing in dusty zone"},
                {"item": "Safety Harness", "status": "unclear", "note": "No elevated work above 2m requiring tie-off"}
            ],
            "hazards": [
                {"description": "Unprotected slab edge without standard perimeter guardrails", "severity": "high", "recommendation": "Install temporary dual-rail barrier with toe-boards immediately."},
                {"description": "Scattered timber and rebar offcuts obstructing access route", "severity": "medium", "recommendation": "Designate waste sorting area and clear main walkways."}
            ],
            "immediate_actions": [
                "Issue cut-resistant gloves and safety glasses to active workers.",
                "Erect temporary edge protection along open slab perimeter.",
                "Clear trip hazards from site access pathways."
            ],
            "limitations": "Demo Mode simulation for testing and demonstration."
        })
    elif name == "CrackReport":
        return schema.model_validate({
            "crack_visible": True,
            "crack_type": "Diagonal / stair-step crack",
            "location_description": "Masonry infill wall near RC column junction",
            "estimated_width_mm": 1.2,
            "severity": "moderate",
            "severity_rationale": "Diagonal cracking traversing mortar courses indicates differential foundation movement or frame deflection.",
            "probable_causes": [
                "Differential settlement of foundation subsoil",
                "Thermal expansion mismatch between concrete frame and masonry infill",
                "Moisture shrinkage during initial curing"
            ],
            "corrective_actions": [
                "Install optical crack monitor (tell-tale gauge) to verify if crack is active over 60 days.",
                "Inspect perimeter surface drainage to prevent water ingress near foundations.",
                "V-cut and inject non-shrink polymer repair mortar once movement has stabilized."
            ],
            "monitoring_advice": "Log width measurements bi-weekly with a crack comparator card.",
            "needs_structural_engineer": True,
            "confidence": "high",
            "limitations": "Demo Mode simulation for testing and demonstration."
        })
    elif name == "ValuationReport":
        return schema.model_validate({
            "currency": "INR",
            "estimated_value_low": 7200000.0,
            "estimated_value_mid": 8000000.0,
            "estimated_value_high": 8800000.0,
            "price_per_sqft_built_up": 5300.0,
            "method": "Comparative market estimate and local construction benchmark (Demo)",
            "key_factors": [
                {"name": "Location & Connectivity", "impact": "positive", "note": "Established neighbourhood with road frontage"},
                {"name": "Building Age & Maintenance", "impact": "neutral", "note": "Sound structure consistent with building age"},
                {"name": "Floor Layout & Natural Light", "impact": "positive", "note": "Functional layout and cross ventilation"}
            ],
            "assumptions": [
                "Clear legal title and municipal sanctions in place",
                "Normal market conditions with willing buyer and seller"
            ],
            "confidence": "medium",
            "disclaimer": "Demo Mode simulation only. Not a certified appraisal."
        })
    elif name == "ProjectPlan":
        tasks = [
            {"id": "T1", "name": "Site Clearing & Soil Survey", "phase": "Substructure", "duration_days": 4, "depends_on": []},
            {"id": "T2", "name": "Excavation & Footing Pits", "phase": "Substructure", "duration_days": 6, "depends_on": ["T1"]},
            {"id": "T3", "name": "PCC Bed & Footing Reinforcement", "phase": "Substructure", "duration_days": 5, "depends_on": ["T2"]},
            {"id": "T4", "name": "Column Starters & Plinth Beam", "phase": "Substructure", "duration_days": 7, "depends_on": ["T3"]},
            {"id": "T5", "name": "Ground Floor Columns Casting", "phase": "Superstructure", "duration_days": 6, "depends_on": ["T4"]},
            {"id": "T6", "name": "Slab Shuttering & Steel Fixing", "phase": "Superstructure", "duration_days": 8, "depends_on": ["T5"]},
            {"id": "T7", "name": "Slab Concrete Pour & Curing", "phase": "Superstructure", "duration_days": 10, "depends_on": ["T6"]},
            {"id": "T8", "name": "Brickwork & Masonry Partitions", "phase": "Finishing", "duration_days": 12, "depends_on": ["T7"]},
            {"id": "T9", "name": "Electrical & Plumbing Rough-in", "phase": "Services", "duration_days": 8, "depends_on": ["T8"]},
            {"id": "T10", "name": "Internal Plastering", "phase": "Finishing", "duration_days": 7, "depends_on": ["T9"]},
            {"id": "T11", "name": "Flooring & Tiling", "phase": "Finishing", "duration_days": 8, "depends_on": ["T10"]},
            {"id": "T12", "name": "Painting & Final Handover", "phase": "Finishing", "duration_days": 6, "depends_on": ["T11"]}
        ]
        return schema.model_validate({
            "summary": "Master construction schedule for residential building (Demo simulation).",
            "tasks": tasks,
            "assumptions": ["6-day working week with Sunday off", "Concrete curing duration observed per standard codes"],
            "risks": ["Monsoon rain delay during substructure excavation", "Material lead time for high-grade rebar"]
        })
    elif name == "DailyReport":
        return schema.model_validate({
            "summary": "Daily site log (Demo simulation). Foundation concreting completed for Grid A-C.",
            "work_completed": [
                "Completed concrete pour for 4 isolated footings (approx 18 m3 concrete)",
                "Continued rebar tying for plinth beam sections",
                "Delivered 2 truckloads of coarse aggregate and cement bags"
            ],
            "issues": [
                "Water tanker arrived 45 minutes late in the morning",
                "Slight aggregate segregation in batch 3; corrected with water-cement ratio adjustment"
            ],
            "safety_observations": [
                "Toolbox talk conducted on concrete handling and chemical burn prevention",
                "Worker footwear and gloves checked before pour"
            ],
            "plan_for_tomorrow": [
                "Begin de-shuttering footing sides and commence wet hessian curing",
                "Survey levels for stub columns"
            ],
            "resource_needs": ["12 mason/labour crew", "1 transit mixer standby", "Hessian bags for curing"],
            "action_items": [
                {"action": "Collect 7-day concrete cube test results from lab", "owner": "Site Engineer", "priority": "high"},
                {"action": "Confirm cement delivery schedule for Wednesday", "owner": "Procurement Officer", "priority": "medium"}
            ]
        })
    elif name == "WeatherNarrative":
        return schema.model_validate({
            "summary": "Weather advisory for site operations over the next 3 days (Demo simulation). Favourable weather with light afternoon breeze.",
            "daily": [
                {"date": "Day 1", "recommended": ["Concrete pouring early morning", "External masonry and rebar tying"], "avoid": ["Heavy crane lifting during peak afternoon gusts"]},
                {"date": "Day 2", "recommended": ["Internal plastering and plumbing work", "Curing of exposed slabs"], "avoid": ["Exposing fresh plaster to direct midday heat"]},
                {"date": "Day 3", "recommended": ["Substructure backfilling", "Formwork stripping"], "avoid": []}
            ],
            "precautions": [
                "Maintain continuous water curing on concrete elements due to low ambient humidity",
                "Provide shaded rest areas and drinking water for workforce"
            ]
        })
    elif name == "KnowledgeAnswer":
        return schema.model_validate({
            "answer": "Minimum curing period for OPC (Ordinary Portland Cement) concrete under standard conditions is 7 days, and at least 10 to 14 days when mineral admixtures (fly ash, slag) are blended or in hot/dry weather conditions (IS 456 / ACI 308).",
            "key_points": [
                "Proper hydration prevents plastic shrinkage cracks and ensures target compressive strength.",
                "Ponding, continuous water spray, or wet hessian wrapping are standard moist-curing methods.",
                "Membrane curing compounds can be used where continuous water supply is limited."
            ],
            "standards_to_check": ["IS 456:2000 (Plain and Reinforced Concrete)", "ACI 308R (Guide to Curing Concrete)"],
            "follow_up_questions": [
                "What specific grade of cement or concrete mix is being used?",
                "What is the average daytime ambient temperature and relative humidity at the site?"
            ],
            "confidence": "high"
        })
    elif name == "GeneralAnalysis":
        return schema.model_validate({
            "summary": "Multimodal site & documentation analysis (Demo simulation). Evaluated visual progress and project metrics.",
            "observations": [
                {"item": "Structural Framework", "detail": "Columns cast up to first floor beam bottom; alignment appears plumb.", "confidence": "high"},
                {"item": "Site Storage", "detail": "Rebar bundles stacked on wooden sleepers, preventing direct soil contact.", "confidence": "high"},
                {"item": "Scaffolding Setup", "detail": "Tubular scaffolding erected with base plates on compacted earth.", "confidence": "medium"}
            ],
            "risks": [
                "Open trench near scaffolding base could destabilize ground during rains.",
                "Access ladder to first floor deck needs secure top tie."
            ],
            "recommended_actions": [
                "Secure scaffolding top ties to structural columns before loading decking.",
                "Backfill and compact utility trench adjacent to scaffold."
            ],
            "follow_up_questions": [
                "Has the scaffolding structure been inspected and tagged by a competent person?",
                "What is the scheduled pour date for the first floor slab?"
            ],
            "limitations": "Demo Mode simulation."
        })
    raise LLMError("Unsupported schema for demo mode: %s" % name)


def _inline_gemini(api_key, model, system, messages, max_tokens, timeout=90.0):
    if not api_key:
        raise LLMUnavailable("No GEMINI_API_KEY configured. Get a free key at https://aistudio.google.com/apikey")
    import requests
    gemini_parts = []
    user_turn = messages[0]["content"] if messages else []
    for block in user_turn:
        if block.get("type") == "image":
            source = block.get("source", {})
            gemini_parts.append({
                "inline_data": {
                    "mime_type": source.get("media_type", "image/jpeg"),
                    "data": source.get("data", "")
                }
            })
        elif block.get("type") == "text":
            gemini_parts.append({"text": block.get("text", "")})
    payload = {
        "contents": [{"role": "user", "parts": gemini_parts}],
        "generationConfig": {"response_mime_type": "application/json", "max_output_tokens": max_tokens, "temperature": 0.2}
    }
    if system:
        payload["system_instruction"] = {"parts": [{"text": system}]}
    url = "https://generativelanguage.googleapis.com/v1beta/models/%s:generateContent?key=%s" % (model, api_key)
    try:
        resp = requests.post(url, json=payload, timeout=timeout)
    except Exception as exc:
        raise LLMError("Could not reach Google Gemini API (network/timeout): %s" % exc) from exc
    if resp.status_code != 200:
        err_msg = resp.text
        try:
            err_msg = resp.json().get("error", {}).get("message", err_msg)
        except Exception:
            pass
        raise LLMError("Google Gemini API error %d: %s" % (resp.status_code, err_msg))
    res_json = resp.json()
    candidates = res_json.get("candidates", [])
    if not candidates:
        raise LLMError("Google Gemini returned no candidates.")
    return "".join(p.get("text", "") for p in candidates[0].get("content", {}).get("parts", []))


# Monkey-patch LLMClient to ensure compatibility even if server has older construction_ai files
def _patch_llm_if_needed():
    if getattr(LLMClient, "_compat_patched", False):
        return
    LLMClient._compat_patched = True

    orig_init = LLMClient.__init__
    def compat_init(self, api_key=None, model=None, max_tokens=1600, timeout=90.0, provider="anthropic"):
        self.provider = (provider or "anthropic").strip().lower()
        m = model or (DEFAULT_MODEL if self.provider == "anthropic" else "gemini-2.0-flash")
        try:
            orig_init(self, api_key=api_key, model=m, max_tokens=max_tokens, timeout=timeout, provider=self.provider)
        except TypeError:
            orig_init(self, api_key=api_key, model=m, max_tokens=max_tokens, timeout=timeout)
        if self.provider == "demo":
            self.api_key = self.api_key or "demo-key"
    LLMClient.__init__ = compat_init

    def compat_avail(self):
        if getattr(self, "provider", "anthropic") == "demo":
            return True
        return bool(self.api_key)
    LLMClient.available = property(compat_avail)

    orig_gen = LLMClient.generate_structured
    def compat_gen(self, schema, user_text, images=(), **kwargs):
        if getattr(self, "provider", "anthropic") == "demo":
            if _generate_demo:
                return _generate_demo(schema, user_text)
            return _inline_demo(schema)
        return orig_gen(self, schema, user_text, images=images, **kwargs)
    LLMClient.generate_structured = compat_gen

    orig_send = LLMClient._send
    def compat_send(self, system, messages, max_tokens):
        if getattr(self, "provider", "anthropic") == "gemini":
            if hasattr(self, "_send_gemini"):
                return self._send_gemini(system, messages, max_tokens)
            return _inline_gemini(self.api_key, self.model, system, messages, max_tokens, self.timeout)
        try:
            return orig_send(self, system, messages, max_tokens)
        except Exception as exc:
            msg = str(exc)
            if "credit balance is too low" in msg.lower() or "billing" in msg.lower():
                raise LLMError(
                    "Anthropic API credits depleted: Your account balance is $0.00. "
                    "Please visit https://console.anthropic.com/settings/plans to purchase credits, "
                    "or switch to Google Gemini (free) / Demo Mode in the sidebar."
                ) from exc
            raise
    LLMClient._send = compat_send


_patch_llm_if_needed()


def get_client() -> LLMClient:
    """Build the LLM client, respecting the sidebar provider choice."""
    provider_choice = st.session_state.get("provider_choice", "Anthropic Claude")
    if "Demo" in provider_choice:
        c = LLMClient(api_key="demo", provider="demo")
        c.provider = "demo"
        return c
    elif "Gemini" in provider_choice:
        key = (st.session_state.get("gemini_key_input") or get_secret("GEMINI_API_KEY") or "").strip() or None
        model = get_secret("GEMINI_MODEL", "gemini-2.0-flash")
        c = LLMClient(api_key=key, model=model, provider="gemini")
        c.provider = "gemini"
        return c
    else:
        key = (st.session_state.get("api_key_override") or get_secret("ANTHROPIC_API_KEY") or "").strip() or None
        model = get_secret("ANTHROPIC_MODEL", DEFAULT_MODEL)
        c = LLMClient(api_key=key, model=model, provider="anthropic")
        c.provider = "anthropic"
        return c


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
        if getattr(client, "available", False):
            sb.success("AI enabled · model: %s (Anthropic)" % getattr(client, "model", DEFAULT_MODEL))
        else:
            sb.warning("AI not configured. Calculators, scheduling and weather still work.")
    elif selected_p == "Google Gemini (Free tier)":
        sb.text_input("Gemini session API key (optional)", type="password", key="gemini_key_input",
                      help="Free key from https://aistudio.google.com/apikey. Or set GEMINI_API_KEY in Streamlit Secrets.")
        client = get_client()
        if getattr(client, "available", False):
            sb.success("AI enabled · model: %s (Gemini Free)" % getattr(client, "model", "gemini-2.0-flash"))
        else:
            sb.warning("Gemini not configured. Paste a free key from Google AI Studio.")
    else:  # Demo Mode
        client = get_client()
        sb.info("ℹ️ Demo Mode: realistic simulated AI output. No API credits or keys needed.")
        sb.success("Demo Mode active · simulated AI enabled")

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
            "- Streamlit app supporting Anthropic Claude, Google Gemini (free tier), and offline Demo Mode.\n"
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
    if getattr(client, "provider", "") == "demo":
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
