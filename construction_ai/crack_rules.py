"""Deterministic cross-check for a USER-MEASURED crack width.

Categories follow the widely used BRE Digest 251 damage classification for
masonry/plaster cracking (indicative only; RC members have separate durability
limits and need an engineer's judgement).
"""
from __future__ import annotations

from typing import Tuple


def classify_width_mm(width_mm: float) -> Tuple[int, str, str]:
    """Return (category 0-5, label, typical significance) for a measured crack width."""
    if width_mm < 0:
        raise ValueError("Crack width cannot be negative.")
    if width_mm < 0.1:
        return 0, "Negligible (hairline)", "Cosmetic; monitor."
    if width_mm <= 1:
        return 1, "Very slight", "Cosmetic; fill during routine decoration."
    if width_mm <= 5:
        return 2, "Slight", "Repair and make weatherproof; check for recurrence."
    if width_mm <= 15:
        return 3, "Moderate", "Needs professional investigation and repair."
    if width_mm <= 25:
        return 4, "Severe", "Structural assessment required; consider temporary support."
    return 5, "Very severe", "Possible danger: restrict access and call a structural engineer now."
