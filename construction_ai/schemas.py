"""Pydantic schemas used to validate every structured AI response (Python 3.9+ safe)."""
from __future__ import annotations

from typing import Annotated, List, Literal, Optional

from pydantic import BaseModel, BeforeValidator, Field, model_validator

from . import scheduler


def _norm(v):
    """Lower-case / trim strings so 'High ' and 'HIGH' validate as 'high'."""
    if isinstance(v, str):
        return v.strip().lower().replace(" ", "_").replace("-", "_")
    return v


Level = Annotated[Literal["low", "medium", "high", "critical"], BeforeValidator(_norm)]
Confidence = Annotated[Literal["low", "medium", "high"], BeforeValidator(_norm)]
CrackSeverity = Annotated[
    Literal["none", "hairline", "minor", "moderate", "severe", "critical"], BeforeValidator(_norm)
]
PPEStatus = Annotated[Literal["present", "missing", "unclear"], BeforeValidator(_norm)]
Impact = Annotated[Literal["positive", "negative", "neutral"], BeforeValidator(_norm)]


class _Base(BaseModel):
    model_config = {"extra": "ignore"}


# ---- 1. Safety / PPE -------------------------------------------------------
class PPEItem(_Base):
    item: str = Field(description="PPE item, e.g. hard hat, hi-vis vest, safety boots, gloves, eye protection, harness")
    status: PPEStatus = Field(description="present, missing or unclear (use unclear if not determinable from the image)")
    note: str = ""


class Hazard(_Base):
    description: str
    severity: Level
    recommendation: str


class SafetyReport(_Base):
    summary: str
    people_visible: Optional[int] = Field(default=None, ge=0, description="Number of workers visible, null if unsure")
    overall_risk: Level
    ppe: List[PPEItem] = Field(default_factory=list)
    hazards: List[Hazard] = Field(default_factory=list)
    immediate_actions: List[str] = Field(default_factory=list)
    limitations: str = ""


# ---- 2. Cracks ---------------------------------------------------------------
class CrackReport(_Base):
    crack_visible: bool
    crack_type: str = Field(description="e.g. hairline, vertical, horizontal, diagonal/stair-step, map/pattern, shrinkage, settlement, none")
    location_description: str = ""
    estimated_width_mm: Optional[float] = Field(
        default=None, ge=0, description="Only if a scale reference is visible; otherwise null"
    )
    severity: CrackSeverity
    severity_rationale: str
    probable_causes: List[str] = Field(default_factory=list)
    corrective_actions: List[str] = Field(default_factory=list)
    monitoring_advice: str = ""
    needs_structural_engineer: bool
    confidence: Confidence
    limitations: str = ""


# ---- 3. Valuation ------------------------------------------------------------
class ValueFactor(_Base):
    name: str
    impact: Impact
    note: str = ""


class ValuationReport(_Base):
    currency: str
    estimated_value_low: float = Field(gt=0)
    estimated_value_mid: float = Field(gt=0)
    estimated_value_high: float = Field(gt=0)
    price_per_sqft_built_up: Optional[float] = Field(default=None, ge=0)
    method: str
    key_factors: List[ValueFactor] = Field(default_factory=list)
    assumptions: List[str] = Field(default_factory=list)
    confidence: Confidence
    disclaimer: str = ""

    @model_validator(mode="after")
    def _ordered(self):
        if not (self.estimated_value_low <= self.estimated_value_mid <= self.estimated_value_high):
            raise ValueError("estimated_value_low <= estimated_value_mid <= estimated_value_high must hold")
        return self


# ---- 5. Planning -------------------------------------------------------------
class TaskSpec(_Base):
    id: str
    name: str
    phase: str = ""
    duration_days: int = Field(ge=1, le=365, description="Working days")
    depends_on: List[str] = Field(default_factory=list)
    notes: str = ""


class ProjectPlan(_Base):
    summary: str = ""
    tasks: List[TaskSpec] = Field(min_length=1)
    assumptions: List[str] = Field(default_factory=list)
    risks: List[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _graph_ok(self):
        scheduler.validate_tasks(self.tasks)  # raises ValueError -> triggers a repair retry
        return self


# ---- 6. Daily site assistant -------------------------------------------------
class ActionItem(_Base):
    action: str
    owner: str = ""
    priority: Level = "medium"


class DailyReport(_Base):
    summary: str
    work_completed: List[str] = Field(default_factory=list)
    issues: List[str] = Field(default_factory=list)
    safety_observations: List[str] = Field(default_factory=list)
    plan_for_tomorrow: List[str] = Field(default_factory=list)
    resource_needs: List[str] = Field(default_factory=list)
    action_items: List[ActionItem] = Field(default_factory=list)


# ---- 7. Weather narrative ----------------------------------------------------
class DayAdvice(_Base):
    date: str
    recommended: List[str] = Field(default_factory=list)
    avoid: List[str] = Field(default_factory=list)


class WeatherNarrative(_Base):
    summary: str
    daily: List[DayAdvice] = Field(default_factory=list)
    precautions: List[str] = Field(default_factory=list)


# ---- 8. Knowledge assistant --------------------------------------------------
class KnowledgeAnswer(_Base):
    answer: str
    key_points: List[str] = Field(default_factory=list)
    standards_to_check: List[str] = Field(
        default_factory=list, description="Only standards/codes the model is confident exist; user must verify edition"
    )
    follow_up_questions: List[str] = Field(default_factory=list)
    confidence: Confidence = "medium"


# ---- 9. General multimodal analysis ------------------------------------------
class Observation(_Base):
    item: str
    detail: str
    confidence: Confidence = "medium"


class GeneralAnalysis(_Base):
    summary: str
    observations: List[Observation] = Field(default_factory=list)
    risks: List[str] = Field(default_factory=list)
    recommended_actions: List[str] = Field(default_factory=list)
    follow_up_questions: List[str] = Field(default_factory=list)
    limitations: str = ""
