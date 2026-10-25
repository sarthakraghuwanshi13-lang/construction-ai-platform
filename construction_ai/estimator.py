"""Deterministic material estimation, cost calculation and valuation baseline.

All constants are INDICATIVE planning values and every rate is user-editable in the UI.
Final quantities must come from a BOQ prepared from structural/architectural drawings.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple

SQM_TO_SQFT = 10.7639

# Commonly quoted planning thumb rules per sq ft of built-up area (RCC framed residential).
THUMB_RULES: Dict[str, Tuple[str, float]] = {
    "Cement": ("bag (50 kg)", 0.4),
    "Steel (TMT)": ("kg", 4.0),
    "Sand": ("cft", 1.2),
    "Coarse aggregate": ("cft", 1.35),
}
# Placeholder market rates in INR. Replace with local supplier quotes.
DEFAULT_RATES: Dict[str, float] = {
    "Cement": 400.0,
    "Steel (TMT)": 65.0,
    "Sand": 55.0,
    "Coarse aggregate": 45.0,
    "Bricks": 9.0,
}
# Placeholder all-in construction cost per sq ft of built-up area (INR) by finish level.
BENCHMARK_RATE_PER_SQFT: Dict[str, float] = {"Basic": 1500.0, "Standard": 1900.0, "Premium": 2600.0}

CEMENT_DENSITY_KG_M3 = 1440.0
CEMENT_BAG_KG = 50.0
DRY_VOLUME_FACTOR = 1.54  # dry volume of materials per m3 of wet concrete
MORTAR_DRY_FACTOR = 1.33  # dry volume per m3 of wet mortar
BRICKS_PER_M3 = 500.0  # nominal 200x100x100 mm (190x90x90 actual + 10 mm mortar)
BRICK_ACTUAL_VOL_M3 = 0.19 * 0.09 * 0.09


class EstimateError(ValueError):
    """Invalid estimator input."""


def to_sqft(area: float, unit: str) -> float:
    if area is None or area <= 0:
        raise EstimateError("Area must be greater than zero.")
    if unit == "sq ft":
        return float(area)
    if unit == "sq m":
        return float(area) * SQM_TO_SQFT
    raise EstimateError("Unknown area unit: %s" % unit)


@dataclass
class MaterialLine:
    item: str
    unit: str
    quantity: float
    rate: float
    amount: float


def quick_estimate(
    area_sqft: float,
    rules: Dict[str, float],
    rates: Dict[str, float],
    wastage_pct: float = 5.0,
) -> List[MaterialLine]:
    """Quantity = area x rule x (1 + wastage). ``rules`` maps item -> quantity per sq ft."""
    if area_sqft <= 0:
        raise EstimateError("Area must be greater than zero.")
    if not 0 <= wastage_pct <= 50:
        raise EstimateError("Wastage must be between 0 and 50 %.")
    lines: List[MaterialLine] = []
    for item, per_sqft in rules.items():
        if per_sqft < 0:
            raise EstimateError("Rule for %s cannot be negative." % item)
        rate = float(rates.get(item, 0.0))
        if rate < 0:
            raise EstimateError("Rate for %s cannot be negative." % item)
        unit = THUMB_RULES.get(item, ("unit", 0))[0]
        qty = area_sqft * per_sqft * (1 + wastage_pct / 100.0)
        lines.append(MaterialLine(item, unit, round(qty, 2), rate, round(qty * rate, 2)))
    return lines


def concrete_materials(volume_m3: float, ratio: Tuple[float, float, float] = (1, 1.5, 3)) -> Dict[str, float]:
    """Cement/sand/aggregate for ``volume_m3`` of wet concrete at a nominal mix ratio (default M20)."""
    if volume_m3 <= 0:
        raise EstimateError("Concrete volume must be greater than zero.")
    if any(r <= 0 for r in ratio):
        raise EstimateError("Mix ratio parts must be positive.")
    total = float(sum(ratio))
    dry = volume_m3 * DRY_VOLUME_FACTOR
    cement_m3 = dry * ratio[0] / total
    return {
        "cement_bags": round(cement_m3 * CEMENT_DENSITY_KG_M3 / CEMENT_BAG_KG, 1),
        "sand_m3": round(dry * ratio[1] / total, 2),
        "aggregate_m3": round(dry * ratio[2] / total, 2),
    }


def brickwork_materials(
    length_m: float,
    height_m: float,
    thickness_mm: float,
    opening_pct: float = 10.0,
    wastage_pct: float = 5.0,
    mortar_ratio: Tuple[float, float] = (1, 6),
) -> Dict[str, float]:
    """Bricks, cement and sand for a wall (nominal-size brick, 10 mm joints)."""
    if min(length_m, height_m, thickness_mm) <= 0:
        raise EstimateError("Length, height and thickness must be greater than zero.")
    if not 0 <= opening_pct < 100:
        raise EstimateError("Openings must be between 0 and 100 %.")
    if not 0 <= wastage_pct <= 50:
        raise EstimateError("Wastage must be between 0 and 50 %.")
    vol = length_m * height_m * (thickness_mm / 1000.0) * (1 - opening_pct / 100.0)
    bricks = vol * BRICKS_PER_M3 * (1 + wastage_pct / 100.0)
    wet_mortar = vol * (1 - BRICKS_PER_M3 * BRICK_ACTUAL_VOL_M3)
    dry_mortar = wet_mortar * MORTAR_DRY_FACTOR
    parts = float(sum(mortar_ratio))
    return {
        "brickwork_m3": round(vol, 3),
        "bricks": float(round(bricks)),
        "cement_bags": round(dry_mortar * mortar_ratio[0] / parts * CEMENT_DENSITY_KG_M3 / CEMENT_BAG_KG, 1),
        "sand_m3": round(dry_mortar * mortar_ratio[1] / parts, 2),
    }


def cost_summary(lines: List[MaterialLine], labour_pct: float = 50.0, contingency_pct: float = 5.0) -> Dict[str, float]:
    if labour_pct < 0 or contingency_pct < 0:
        raise EstimateError("Percentages cannot be negative.")
    materials = sum(l.amount for l in lines)
    labour = materials * labour_pct / 100.0
    subtotal = materials + labour
    contingency = subtotal * contingency_pct / 100.0
    return {
        "materials": round(materials, 2),
        "labour_and_other": round(labour, 2),
        "subtotal": round(subtotal, 2),
        "contingency": round(contingency, 2),
        "total": round(subtotal + contingency, 2),
    }


def benchmark_cost(area_sqft: float, level: str, rates: Dict[str, float] = None) -> float:
    rates = rates or BENCHMARK_RATE_PER_SQFT
    if level not in rates:
        raise EstimateError("Unknown finish level: %s" % level)
    if area_sqft <= 0:
        raise EstimateError("Area must be greater than zero.")
    return round(area_sqft * rates[level], 2)


def cost_approach_baseline(
    land_area_sqft: float,
    land_rate_per_sqft: float,
    built_up_sqft: float,
    construction_rate_per_sqft: float,
    age_years: float,
    life_years: float = 60.0,
    max_depreciation: float = 0.7,
) -> Dict[str, float]:
    """Simple cost approach: land + depreciated replacement cost. Not a market valuation."""
    if min(land_area_sqft, land_rate_per_sqft, built_up_sqft, construction_rate_per_sqft) < 0 or age_years < 0:
        raise EstimateError("Areas, rates and age cannot be negative.")
    dep = min(max_depreciation, age_years / life_years) if life_years > 0 else max_depreciation
    land = land_area_sqft * land_rate_per_sqft
    building = built_up_sqft * construction_rate_per_sqft * (1 - dep)
    return {
        "land_value": round(land, 2),
        "depreciation_pct": round(dep * 100, 1),
        "building_value": round(building, 2),
        "total": round(land + building, 2),
    }
