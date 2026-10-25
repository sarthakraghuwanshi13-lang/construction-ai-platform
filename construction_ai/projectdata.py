"""Project profile + structured project-data (CSV/JSON) handling."""
from __future__ import annotations

import csv
import io
import json
from typing import List, Literal, Optional

from pydantic import BaseModel, Field, ValidationError

from .config import MAX_CONTEXT_CHARS, MAX_UPLOAD_MB


class ProjectDataError(ValueError):
    """Uploaded project data could not be read."""


class ProjectProfile(BaseModel):
    name: str = ""
    location: str = ""
    project_type: str = "Residential building"
    built_up_area: Optional[float] = Field(default=None, gt=0)
    area_unit: Literal["sq ft", "sq m"] = "sq ft"
    floors: int = Field(default=1, ge=1, le=100)
    currency: str = "INR"
    notes: str = ""

    def to_context(self) -> str:
        parts: List[str] = []
        if self.name:
            parts.append("Name: " + self.name)
        if self.location:
            parts.append("Location: " + self.location)
        parts.append("Type: " + self.project_type)
        if self.built_up_area:
            parts.append("Built-up area: %s %s" % (self.built_up_area, self.area_unit))
        parts.append("Floors: %d" % self.floors)
        parts.append("Currency: " + self.currency)
        if self.notes:
            parts.append("Notes: " + self.notes[:500])
        return "; ".join(parts)


def profile_from_json(data: bytes) -> ProjectProfile:
    try:
        return ProjectProfile.model_validate(json.loads(data.decode("utf-8-sig")))
    except (UnicodeDecodeError, ValueError, ValidationError) as exc:
        raise ProjectDataError("Not a valid project profile JSON: " + str(exc)[:200]) from exc


def profile_to_json(profile: ProjectProfile) -> str:
    return profile.model_dump_json(indent=2)


def _decode(data: bytes) -> str:
    for enc in ("utf-8-sig", "latin-1"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    raise ProjectDataError("Could not decode file.")  # pragma: no cover


def table_summary(data: bytes, filename: str, max_rows: int = 25) -> str:
    """Compact text summary of an uploaded CSV or JSON file for use as model context."""
    if not data:
        raise ProjectDataError("%s is empty." % filename)
    if len(data) > MAX_UPLOAD_MB * 1024 * 1024:
        raise ProjectDataError("%s is larger than %d MB." % (filename, MAX_UPLOAD_MB))
    text = _decode(data)
    lower = filename.lower()
    if lower.endswith(".json"):
        try:
            obj = json.loads(text)
        except ValueError as exc:
            raise ProjectDataError("%s is not valid JSON." % filename) from exc
        return json.dumps(obj, separators=(",", ":"))[:MAX_CONTEXT_CHARS]
    if lower.endswith(".csv"):
        try:
            rows = list(csv.reader(io.StringIO(text)))
        except csv.Error as exc:
            raise ProjectDataError("%s is not valid CSV." % filename) from exc
        rows = [r for r in rows if any(c.strip() for c in r)]
        if len(rows) < 1:
            raise ProjectDataError("%s has no rows." % filename)
        body = "\n".join(",".join(c.strip() for c in r) for r in rows[: max_rows + 1])
        return ("CSV %s (%d data rows; first %d shown):\n%s" % (filename, len(rows) - 1, min(len(rows) - 1, max_rows), body))[
            :MAX_CONTEXT_CHARS
        ]
    raise ProjectDataError("Unsupported file type for %s (use .csv or .json)." % filename)
