"""Configuration: secrets lookup and shared limits."""
from __future__ import annotations

import os
from typing import Optional

DEFAULT_MODEL = "claude-sonnet-5-5"
DEFAULT_GEMINI_MODEL = "gemini-2.0-flash"
DEFAULT_MAX_TOKENS = 1600
MAX_IMAGES = 4
MAX_UPLOAD_MB = 8
IMAGE_MAX_SIDE = 1568  # longest side after downscaling (keeps image tokens low)
MAX_CONTEXT_CHARS = 2500  # cap for uploaded project-data text sent to the model


def get_secret(name: str, default: Optional[str] = None) -> Optional[str]:
    """Look up a secret: environment variable first, then Streamlit secrets.

    Never raises if no secrets file exists (e.g. local runs and tests).
    """
    value = os.environ.get(name)
    if value:
        return value
    try:
        import streamlit as st  # imported lazily so core modules work without it

        if name in st.secrets:
            return str(st.secrets[name])
    except Exception:
        pass
    return default
