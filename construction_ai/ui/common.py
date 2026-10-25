"""Shared Streamlit helpers: client creation, image inputs, AI-call wrapper, JSON display."""
from __future__ import annotations

from typing import Callable, List, Optional, TypeVar

import streamlit as st
from pydantic import BaseModel

from ..config import DEFAULT_MODEL, MAX_IMAGES, get_secret
from ..imaging import PreparedImage, prepare_many
from ..llm import LLMClient, LLMError
from ..projectdata import ProjectProfile

T = TypeVar("T", bound=BaseModel)

RISK_ICON = {"low": "🟢", "medium": "🟡", "high": "🟠", "critical": "🔴", "none": "🟢",
             "hairline": "🟢", "minor": "🟡", "moderate": "🟠", "severe": "🔴"}
STATUS_ICON = {"go": "🟢 go", "caution": "🟡 caution", "no-go": "🔴 no-go"}


def get_client() -> LLMClient:
    """Build the LLM client from session selection, session keys, env vars or Streamlit secrets."""
    provider_choice = st.session_state.get("provider_choice", "Anthropic Claude")
    if "Demo" in provider_choice:
        return LLMClient(provider="demo")
    elif "Gemini" in provider_choice:
        key = st.session_state.get("gemini_key_input") or get_secret("GEMINI_API_KEY")
        model = get_secret("GEMINI_MODEL", "gemini-2.0-flash")
        return LLMClient(api_key=key, model=model, provider="gemini")
    else:
        key = st.session_state.get("api_key_override") or get_secret("ANTHROPIC_API_KEY")
        model = get_secret("ANTHROPIC_MODEL", DEFAULT_MODEL)
        return LLMClient(api_key=key, model=model, provider="anthropic")


def get_profile() -> ProjectProfile:
    return st.session_state.get("profile") or ProjectProfile()


def project_context() -> str:
    parts = [get_profile().to_context()]
    extra = st.session_state.get("extra_context", "")
    if extra:
        parts.append(extra)
    return "\n".join(p for p in parts if p)


def need_ai(client: LLMClient) -> bool:
    """Show a clear notice when AI is not configured. Returns True if AI can be used."""
    if not client.available:
        if client.provider == "gemini":
            st.info(
                "Google Gemini is **not configured**: add `GEMINI_API_KEY` (free at [Google AI Studio](https://aistudio.google.com/apikey)) "
                "or paste a key in the sidebar.", icon="🔑"
            )
        else:
            st.info(
                "AI analysis is **not configured**: add `ANTHROPIC_API_KEY` (see README) or paste a key in the "
                "sidebar. Or select **Demo Mode** in the sidebar to test without a key.", icon="🔑"
            )
    return client.available


def image_inputs(key: str, label: str = "Upload image(s)", required_note: Optional[str] = None) -> List[PreparedImage]:
    files = st.file_uploader(
        "%s (JPG/PNG/WebP, up to %d)" % (label, MAX_IMAGES),
        type=["jpg", "jpeg", "png", "webp"],
        accept_multiple_files=True,
        key=key,
    )
    if not files:
        if required_note:
            st.caption(required_note)
        return []
    images, errors = prepare_many([(f.name, f.getvalue()) for f in files])
    for e in errors:
        st.warning(e)
    if images:
        cols = st.columns(min(len(images), MAX_IMAGES))
        for col, im in zip(cols, images):
            col.image(im.to_bytes(), caption="%s (%dx%d)" % (im.name, im.width, im.height), width=220)
    return images


def run_ai(fn: Callable[[], T], spinner: str = "Analyzing with AI...") -> Optional[T]:
    """Run an AI call, turning every failure into a readable message. Returns None on failure."""
    try:
        with st.spinner(spinner):
            return fn()
    except LLMError as exc:
        err_msg = str(exc)
        st.error(err_msg)
        if "credit balance is too low" in err_msg.lower() or "credits depleted" in err_msg.lower():
            st.info(
                "💡 **How to resolve this credit issue:**\n\n"
                "1. **Recharge Anthropic credits:** Visit [Anthropic Plans & Billing](https://console.anthropic.com/settings/plans) to purchase credits ($5 min).\n"
                "2. **Use Google Gemini (100% Free):** Get a free API key at [Google AI Studio](https://aistudio.google.com/apikey) and select **Google Gemini** in the sidebar.\n"
                "3. **Switch to Demo Mode:** Choose **Demo Mode (Simulated AI)** in the sidebar to test all 9 tabs with realistic results immediately."
            )
    except Exception as exc:  # last-resort guard so the app never shows a stack trace
        st.error("Unexpected error: %s" % type(exc).__name__)
    return None


def show_json(model: BaseModel, filename: str, key: str) -> None:
    """Expose the validated structured response and a download button."""
    text = model.model_dump_json(indent=2)
    with st.expander("Structured JSON response (schema-validated)"):
        st.code(text, language="json")
    st.download_button("Download JSON", text, file_name=filename, mime="application/json", key="dl_" + key)


def bullet_list(title: str, items: List[str]) -> None:
    if items:
        st.markdown("**%s**" % title)
        st.markdown("\n".join("- %s" % i for i in items))


def disclaimer(text: str) -> None:
    st.caption("⚠️ " + text)
