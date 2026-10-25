"""Cost-related tabs: real-estate valuation and material estimation / cost calculation."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from .. import estimator as E
from .. import prompts
from ..llm import LLMClient
from ..schemas import ValuationReport
from .common import (bullet_list, disclaimer, get_profile, image_inputs, need_ai, project_context, run_ai, show_json)

PROPERTY_TYPES = ["Independent house", "Apartment / flat", "Villa", "Plot with building", "Commercial building"]
CONDITIONS = ["Excellent", "Good", "Average", "Needs repair"]


def _money(v: float, cur: str) -> str:
    return "%s %s" % (cur, format(v, ",.0f"))


def render_valuation(client: LLMClient) -> None:
    st.subheader("🏠 Real-estate valuation")
    st.caption("An AI estimate from your inputs and general market knowledge. It has **no live comparable-sales data** "
               "and is not a licensed valuation. A local cost-approach baseline is computed when you supply rates.")
    ai_ok = need_ai(client)
    prof = get_profile()
    c1, c2 = st.columns(2)
    ptype = c1.selectbox("Property type", PROPERTY_TYPES, key="val_type")
    location = c2.text_input("Location (city, locality)", value=prof.location, key="val_loc")
    c1, c2, c3 = st.columns(3)
    land = c1.number_input("Land area (sq ft)", min_value=0.0, value=1200.0, step=50.0, key="val_land")
    built = c2.number_input("Built-up area (sq ft)", min_value=0.0, value=float(prof.built_up_area or 1000.0)
                            if prof.area_unit == "sq ft" else 1000.0, step=50.0, key="val_built")
    age = c3.number_input("Age (years)", min_value=0.0, max_value=200.0, value=5.0, step=1.0, key="val_age")
    c1, c2, c3 = st.columns(3)
    beds = c1.number_input("Bedrooms", min_value=0, max_value=20, value=3, key="val_beds")
    cond = c2.selectbox("Condition", CONDITIONS, index=1, key="val_cond")
    cur = c3.text_input("Currency", value=prof.currency, key="val_cur")
    amen = st.text_input("Amenities / notes (parking, lift, road width, nearby metro...)", key="val_amen")
    with st.expander("Optional: local rates for a cost-approach baseline"):
        r1, r2 = st.columns(2)
        land_rate = r1.number_input("Land rate (per sq ft)", min_value=0.0, value=0.0, step=100.0, key="val_land_rate")
        con_rate = r2.number_input("Replacement construction rate (per sq ft)", min_value=0.0, value=0.0, step=100.0,
                                   key="val_con_rate")
    images = image_inputs("val_imgs", "Property photo(s) (optional)")

    baseline_text, baseline = "", None
    if land_rate > 0 and con_rate > 0 and built > 0:
        baseline = E.cost_approach_baseline(land, land_rate, built, con_rate, age)
        baseline_text = ("Land %s + building %s (after %.1f%% depreciation) = %s" % (
            _money(baseline["land_value"], cur), _money(baseline["building_value"], cur),
            baseline["depreciation_pct"], _money(baseline["total"], cur)))
        st.info("Cost-approach baseline (rule-based, computed locally): " + baseline_text)

    ready = ai_ok and bool(location.strip()) and built > 0
    if not location.strip():
        st.caption("Enter a location to enable the AI estimate.")
    if st.button("Estimate value with AI", type="primary", disabled=not ready, key="val_go"):
        inputs = ("Type: %s; Location: %s; Land: %.0f sq ft; Built-up: %.0f sq ft; Age: %.0f yrs; Bedrooms: %d; "
                  "Condition: %s; Currency: %s; Notes: %s" % (ptype, location, land, built, age, beds, cond, cur, amen))
        result = run_ai(lambda: client.generate_structured(
            ValuationReport, prompts.valuation(inputs, baseline_text, project_context()), images=images))
        if result:
            st.session_state["val_result"] = result
    r = st.session_state.get("val_result")
    if not r:
        return
    c1, c2, c3 = st.columns(3)
    c1.metric("Low", _money(r.estimated_value_low, r.currency))
    c2.metric("Mid", _money(r.estimated_value_mid, r.currency))
    c3.metric("High", _money(r.estimated_value_high, r.currency))
    if r.price_per_sqft_built_up:
        st.write("**Implied price per built-up sq ft:** " + _money(r.price_per_sqft_built_up, r.currency))
    st.write("**Method:** %s  \n**Confidence:** %s" % (r.method, r.confidence.title()))
    if r.key_factors:
        st.dataframe([{"Factor": f.name, "Impact": f.impact, "Note": f.note} for f in r.key_factors], hide_index=True)
    bullet_list("Assumptions", r.assumptions)
    disclaimer(r.disclaimer or "Indicative AI estimate without live market data. Not a certified valuation.")
    show_json(r, "valuation.json", "valuation")


def render_estimator() -> None:
    st.subheader("🧮 Material estimation & construction cost")
    st.caption("Fully rule-based (no AI). Defaults are **indicative thumb rules and placeholder rates in INR**: "
               "edit them to match your drawings and local quotes. A real BOQ must come from structural drawings.")
    prof = get_profile()
    c1, c2, c3 = st.columns(3)
    unit = c1.selectbox("Area unit", ["sq ft", "sq m"], index=0 if prof.area_unit == "sq ft" else 1, key="est_unit")
    area = c2.number_input("Total built-up area", min_value=0.0, value=float(prof.built_up_area or 1000.0), step=50.0,
                           key="est_area")
    wastage = c3.number_input("Wastage (%)", min_value=0.0, max_value=50.0, value=5.0, step=1.0, key="est_waste")
    if area <= 0:
        st.warning("Enter a built-up area greater than zero.")
        return
    area_sqft = E.to_sqft(area, unit)

    st.markdown("**Quantities & rates** (editable)")
    table = pd.DataFrame(
        [{"Item": k, "Unit": E.THUMB_RULES[k][0], "Qty per sq ft": E.THUMB_RULES[k][1], "Rate": E.DEFAULT_RATES.get(k, 0.0)}
         for k in E.THUMB_RULES])
    edited = st.data_editor(table, hide_index=True, disabled=["Item", "Unit"], key="est_table")
    try:
        rules = {r["Item"]: float(r["Qty per sq ft"]) for _, r in edited.iterrows()}
        rates = {r["Item"]: float(r["Rate"]) for _, r in edited.iterrows()}
        lines = E.quick_estimate(area_sqft, rules, rates, wastage)
    except (E.EstimateError, ValueError, TypeError) as exc:
        st.error("Check the table values: %s" % exc)
        return

    c1, c2 = st.columns(2)
    labour = c1.number_input("Labour & other costs (% of materials)", min_value=0.0, max_value=300.0, value=50.0, step=5.0,
                             key="est_labour")
    cont = c2.number_input("Contingency (%)", min_value=0.0, max_value=50.0, value=5.0, step=1.0, key="est_cont")
    summary = E.cost_summary(lines, labour, cont)
    out = pd.DataFrame([{"Item": l.item, "Unit": l.unit, "Quantity": l.quantity, "Rate": l.rate, "Amount": l.amount}
                        for l in lines])
    st.dataframe(out, hide_index=True)
    cur = prof.currency
    m1, m2, m3 = st.columns(3)
    m1.metric("Materials", _money(summary["materials"], cur))
    m2.metric("Labour & other", _money(summary["labour_and_other"], cur))
    m3.metric("Total incl. contingency", _money(summary["total"], cur))
    st.download_button("Download estimate (CSV)", out.to_csv(index=False), file_name="material_estimate.csv",
                       mime="text/csv", key="est_dl")
    st.caption("Excludes land, approvals, finishing, MEP fixtures and furniture unless you add them in the rates.")

    with st.expander("Benchmark cost by finish level (cost per sq ft x area)"):
        level = st.selectbox("Finish level", list(E.BENCHMARK_RATE_PER_SQFT), index=1, key="est_level")
        rate = st.number_input("Rate per sq ft", min_value=0.0, value=E.BENCHMARK_RATE_PER_SQFT[level], step=50.0,
                               key="est_level_rate_%s" % level)
        st.metric("Indicative total", _money(area_sqft * rate, cur))
        st.caption("Placeholder rates (Tier-2 India style). Replace with local contractor quotes.")

    with st.expander("Concrete element calculator (cement / sand / aggregate)"):
        c1, c2, c3 = st.columns(3)
        vol = c1.number_input("Wet concrete volume (m³)", min_value=0.0, value=10.0, step=0.5, key="cc_vol")
        mix = c2.selectbox("Nominal mix", ["M20 (1:1.5:3)", "M15 (1:2:4)", "M25 (1:1:2)"], key="cc_mix")
        ratio = {"M20 (1:1.5:3)": (1, 1.5, 3), "M15 (1:2:4)": (1, 2, 4), "M25 (1:1:2)": (1, 1, 2)}[mix]
        try:
            res = E.concrete_materials(vol, ratio)
            c3.metric("Cement bags (50 kg)", res["cement_bags"])
            st.write("Sand: **%.2f m³**, coarse aggregate: **%.2f m³** (dry-volume factor 1.54)." % (
                res["sand_m3"], res["aggregate_m3"]))
        except E.EstimateError as exc:
            st.warning(str(exc))

    with st.expander("Brickwork calculator (bricks, mortar cement & sand)"):
        c1, c2, c3, c4 = st.columns(4)
        length = c1.number_input("Wall length (m)", min_value=0.0, value=20.0, step=1.0, key="bw_len")
        height = c2.number_input("Height (m)", min_value=0.0, value=3.0, step=0.1, key="bw_h")
        thick = c3.selectbox("Thickness (mm)", [115, 230], index=1, key="bw_t")
        openings = c4.number_input("Openings (%)", min_value=0.0, max_value=99.0, value=10.0, key="bw_open")
        try:
            bw = E.brickwork_materials(length, height, thick, openings, wastage)
            st.write("Brickwork volume **%.2f m³** → **%d bricks**, mortar (1:6) cement **%.1f bags**, sand **%.2f m³**." % (
                bw["brickwork_m3"], bw["bricks"], bw["cement_bags"], bw["sand_m3"]))
        except E.EstimateError as exc:
            st.warning(str(exc))
