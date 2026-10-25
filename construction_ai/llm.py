"""Thin multimodal LLM client (Anthropic Messages API) with schema-validated JSON output.

The network call lives in ``_send`` so tests can replace it with a fake transport.
Nothing here fabricates output: if no API key is configured, ``LLMUnavailable`` is raised.
"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Sequence, Type, TypeVar

from pydantic import BaseModel

from .config import DEFAULT_GEMINI_MODEL, DEFAULT_MAX_TOKENS, DEFAULT_MODEL
from .imaging import PreparedImage
from .prompts import SYSTEM

T = TypeVar("T", bound=BaseModel)


class LLMError(Exception):
    """The model call failed or returned unusable output."""


class LLMUnavailable(LLMError):
    """No API key / SDK configured, so AI features are disabled."""


def extract_json(text: str) -> Any:
    """Return the first JSON object found in ``text`` (tolerates ```json fences and prose)."""
    decoder = json.JSONDecoder()
    start = text.find("{")
    while start != -1:
        try:
            obj, _ = decoder.raw_decode(text, start)
            if isinstance(obj, dict):
                return obj
        except ValueError:
            pass
        start = text.find("{", start + 1)
    raise ValueError("No JSON object found in model output.")


def _strip_titles(node: Any) -> Any:
    if isinstance(node, dict):
        return {k: _strip_titles(v) for k, v in node.items() if not (k == "title" and isinstance(v, str))}
    if isinstance(node, list):
        return [_strip_titles(v) for v in node]
    return node


def schema_hint(model: Type[BaseModel]) -> str:
    """Compact JSON Schema text for the prompt (keeps token use low)."""
    return json.dumps(_strip_titles(model.model_json_schema()), separators=(",", ":"))


def _generate_demo(schema: Type[T], user_text: str) -> T:
    """Return realistic, schema-valid mock output for demonstration and offline testing."""
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
    else:
        raise LLMError("Unsupported schema for demo mode: %s" % name)


class LLMClient:
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        timeout: float = 90.0,
        provider: str = "anthropic",
    ) -> None:
        self.provider = (provider or "anthropic").strip().lower()
        self.api_key = (api_key or "").strip() or None
        if self.provider == "gemini":
            self.model = model or DEFAULT_GEMINI_MODEL
        else:
            self.model = model or DEFAULT_MODEL
        self.max_tokens = max_tokens
        self.timeout = timeout

    @property
    def available(self) -> bool:
        if self.provider == "demo":
            return True
        return bool(self.api_key)

    # -- transport ---------------------------------------------------------
    def _send_anthropic(self, system: str, messages: List[Dict[str, Any]], max_tokens: int) -> str:
        if not self.available:
            raise LLMUnavailable("No ANTHROPIC_API_KEY configured, so AI analysis is unavailable.")
        try:
            import anthropic
        except ImportError as exc:  # pragma: no cover - depends on environment
            raise LLMUnavailable("The 'anthropic' package is not installed.") from exc
        client = anthropic.Anthropic(api_key=self.api_key, timeout=self.timeout, max_retries=2)
        try:
            resp = client.messages.create(
                model=self.model, max_tokens=max_tokens, system=system, messages=messages
            )
        except anthropic.AuthenticationError as exc:
            raise LLMError("Authentication failed: Check your ANTHROPIC_API_KEY (it may be expired or invalid).") from exc
        except anthropic.RateLimitError as exc:
            raise LLMError("Rate limit reached. Wait a moment and try again.") from exc
        except anthropic.APIConnectionError as exc:
            raise LLMError("Could not reach the Anthropic API (network/timeout). Try again.") from exc
        except anthropic.APIStatusError as exc:
            msg = getattr(exc, "message", str(exc))
            body_str = str(getattr(exc, "body", "")) + " " + str(msg)
            if "credit balance is too low" in body_str.lower() or "billing" in body_str.lower() or "credit_balance_too_low" in body_str.lower():
                raise LLMError(
                    "Anthropic API credits depleted: Your Anthropic account balance is $0.00. "
                    "Please visit https://console.anthropic.com/settings/plans to purchase credits, "
                    "or switch to Google Gemini (free) / Demo Mode in the sidebar."
                ) from exc
            raise LLMError("Anthropic API error %s: %s" % (exc.status_code, msg)) from exc
        text = "".join(getattr(b, "text", "") for b in resp.content if getattr(b, "type", "") == "text")
        if not text.strip():
            raise LLMError("The model returned an empty response.")
        return text

    def _send_gemini(self, system: str, messages: List[Dict[str, Any]], max_tokens: int) -> str:
        if not self.available:
            raise LLMUnavailable("No GEMINI_API_KEY configured. Get a free key at https://aistudio.google.com/apikey")
        import requests

        gemini_parts: List[Dict[str, Any]] = []
        user_turn = messages[0]["content"] if messages else []
        for block in user_turn:
            if block.get("type") == "image":
                source = block.get("source", {})
                media_type = source.get("media_type", "image/jpeg")
                data_b64 = source.get("data", "")
                gemini_parts.append({
                    "inline_data": {
                        "mime_type": media_type,
                        "data": data_b64
                    }
                })
            elif block.get("type") == "text":
                gemini_parts.append({"text": block.get("text", "")})

        payload: Dict[str, Any] = {
            "contents": [{"role": "user", "parts": gemini_parts}],
            "generationConfig": {
                "response_mime_type": "application/json",
                "max_output_tokens": max_tokens,
                "temperature": 0.2
            }
        }
        if system:
            payload["system_instruction"] = {"parts": [{"text": system}]}

        url = "https://generativelanguage.googleapis.com/v1beta/models/%s:generateContent?key=%s" % (
            self.model, self.api_key
        )
        try:
            resp = requests.post(url, json=payload, timeout=self.timeout)
        except Exception as exc:
            raise LLMError("Could not reach Google Gemini API (network/timeout): %s" % exc) from exc

        if resp.status_code != 200:
            err_data = resp.text
            try:
                err_json = resp.json()
                err_data = err_json.get("error", {}).get("message", err_data)
            except Exception:
                pass
            raise LLMError("Google Gemini API error %d: %s" % (resp.status_code, err_data))

        try:
            res_json = resp.json()
            candidates = res_json.get("candidates", [])
            if not candidates:
                raise LLMError("Google Gemini returned no candidates (possibly blocked by safety filters).")
            parts = candidates[0].get("content", {}).get("parts", [])
            text = "".join(p.get("text", "") for p in parts)
            if not text.strip():
                raise LLMError("Google Gemini returned an empty response.")
            return text
        except Exception as exc:
            if isinstance(exc, LLMError):
                raise
            raise LLMError("Failed to parse Google Gemini response: %s" % exc) from exc

    def _send(self, system: str, messages: List[Dict[str, Any]], max_tokens: int) -> str:
        if self.provider == "gemini":
            return self._send_gemini(system, messages, max_tokens)
        return self._send_anthropic(system, messages, max_tokens)

    # -- public API --------------------------------------------------------
    def generate_structured(
        self,
        schema: Type[T],
        user_text: str,
        images: Sequence[PreparedImage] = (),
        system: str = SYSTEM,
        max_tokens: Optional[int] = None,
        retries: int = 1,
    ) -> T:
        """Call the model and return a validated ``schema`` instance (one repair retry)."""
        if self.provider == "demo":
            return _generate_demo(schema, user_text)

        blocks: List[Dict[str, Any]] = [im.to_block() for im in images]
        blocks.append(
            {
                "type": "text",
                "text": user_text + "\n\nReturn ONLY one JSON object matching this JSON Schema:\n" + schema_hint(schema),
            }
        )
        messages: List[Dict[str, Any]] = [{"role": "user", "content": blocks}]
        limit = max_tokens or self.max_tokens
        reply = self._send(system, messages, limit)
        for attempt in range(retries + 1):
            try:
                return schema.model_validate(extract_json(reply))
            except ValueError as exc:  # includes pydantic.ValidationError and JSON errors
                if attempt >= retries:
                    raise LLMError("The model's reply did not match the expected format: " + str(exc)[:400]) from exc
                messages = messages + [
                    {"role": "assistant", "content": reply[:6000]},
                    {
                        "role": "user",
                        "content": "That reply was invalid: %s\nReturn corrected JSON only, as concise as possible."
                        % str(exc)[:600],
                    },
                ]
                reply = self._send(system, messages, limit)
        raise LLMError("Unreachable")  # pragma: no cover
