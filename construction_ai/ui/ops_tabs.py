"""Operational tabs: project planning, daily site assistant, weather advisory, knowledge assistant."""
from __future__ import annotations

from datetime import date
from typing import List

import pandas as pd
import streamlit as st

from .. import prompts, scheduler, weather
from ..estimator import to_sqft
from ..llm import LLMClient
from ..schemas import DailyReport, KnowledgeAnswer, ProjectPlan, TaskSpec, WeatherNarrative
from .common import (RISK_ICON, STATUS_ICON, bullet_list, disclaimer, get_profile, image_inputs, need_ai,
                     project_context, run_ai, show_json)


# --------------------------------------------------------------------------- planning
def _gantt(df: pd.DataFrame) -> None:
    try:
        import altair as alt

        chart = (
            alt.Chart(df)
            .mark_bar()
            .encode(
                x=alt.X("Start:T", title=None),
                x2="End:T",
                y=alt.Y("Task:N", sort=list(df["Task"]), title=None),
                color=alt.Color("Phase:N", legend=alt.Legend(title="Phase")),
                tooltip=["Task", "Phase", "Start", "End", "Days", "Critical"],
            )
            .properties(height=max(200, 26 * len(df)))
        )
        st.altair_chart(chart)
    except Exception:
        st.caption("Gantt chart unavailable; see the table.")


def render_planning(client: LLMClient) -> None:
    st.subheader("📅 Project planning & task scheduling")
    st.caption("Tasks come from the AI (if configured) or a generic template. Dates, working-day calendar and the "
               "critical path are always computed by code, never by the AI.")
    prof = get_profile()
    desc = st.text_area("Project description", value=prof.project_type + (" in " + prof.location if prof.location else ""),
                        key="plan_desc", height=70)
    c1, c2, c3, c4 = st.columns(4)
    start = c1.date_input("Start date", value=date.today(), key="plan_start")
    floors = int(c2.number_input("Floors", min_value=1, max_value=100, value=int(prof.floors), key="plan_floors"))
    area = c3.number_input("Total built-up area (all floors)", min_value=1.0, value=float(prof.built_up_area or 1500.0), step=50.0,
                           key="plan_area")
    unit = c4.selectbox("Unit", ["sq ft", "sq m"], index=0 if prof.area_unit == "sq ft" else 1, key="plan_unit")
    sunday_off = st.checkbox("Sunday is a non-working day (Mon-Sat work week)", value=True, key="plan_sunday")
    work_week = (0, 1, 2, 3, 4, 5) if sunday_off else (0, 1, 2, 3, 4, 5, 6)

    ai_ok = client.available
    b1, b2 = st.columns(2)
    if b1.button("Generate plan with AI", type="primary", disabled=not ai_ok or not desc.strip(), key="plan_ai"):
        result = run_ai(lambda: client.generate_structured(
            ProjectPlan, prompts.plan(desc, start.isoformat(), floors, "%s %s" % (area, unit), project_context()),
            max_tokens=3000), "Planning with AI...")
        if result:
            st.session_state["plan"] = {"data": result, "source": "AI-generated"}
    if b2.button("Use generic template (no AI)", key="plan_tpl"):
        tasks = [TaskSpec(**d) for d in scheduler.default_template(floors, to_sqft(area, unit))]
        st.session_state["plan"] = {
            "data": ProjectPlan(summary="Generic residential RCC-frame template (not AI generated).", tasks=tasks,
                                assumptions=["Durations are placeholders scaled by project size; review with your planner."]),
            "source": "Template (not AI)"}
    if not ai_ok:
        st.caption("AI planning needs an API key; the template works without one.")

    saved = st.session_state.get("plan")
    if not saved:
        return
    plan: ProjectPlan = saved["data"]
    try:
        sched = scheduler.schedule(plan.tasks, start, work_week)
    except ValueError as exc:
        st.error("Could not schedule this plan: %s" % exc)
        return
    end = scheduler.project_end(sched)
    m1, m2, m3 = st.columns(3)
    m1.metric("Source", saved["source"])
    m2.metric("Finish date", end.strftime("%d %b %Y"))
    m3.metric("Critical tasks", sum(1 for s in sched if s.critical))
    if plan.summary:
        st.write(plan.summary)
    df = pd.DataFrame([{"ID": s.id, "Task": s.name, "Phase": s.phase or "-", "Start": pd.Timestamp(s.start),
                        "End": pd.Timestamp(s.end), "Days": s.duration_days, "Depends on": ", ".join(s.depends_on) or "-",
                        "Slack": s.slack_days, "Critical": "Yes" if s.critical else ""} for s in sched])
    _gantt(df)
    show_df = df.copy()
    show_df["Start"] = show_df["Start"].dt.strftime("%d %b %Y")
    show_df["End"] = show_df["End"].dt.strftime("%d %b %Y")
    st.dataframe(show_df, hide_index=True)
    st.download_button("Download schedule (CSV)", show_df.to_csv(index=False), file_name="schedule.csv",
                       mime="text/csv", key="plan_dl")
    bullet_list("Assumptions", plan.assumptions)
    bullet_list("Risks", plan.risks)
    disclaimer("Planning aid only. Durations are estimates; validate with your site team and local conditions.")
    show_json(plan, "project_plan.json", "plan")


# --------------------------------------------------------------------------- daily assistant
def render_daily(client: LLMClient) -> None:
    st.subheader("📝 Daily site assistant")
    st.caption("Turn rough site notes (and optional photos) into a structured daily report and next-day plan.")
    ai_ok = need_ai(client)
    c1, c2 = st.columns(2)
    day = c1.date_input("Report date", value=date.today(), key="daily_date")
    crew = c2.text_input("Crew on site (e.g. 12 masons, 8 helpers, 2 electricians)", key="daily_crew")
    done = st.text_area("Work done today", key="daily_done", height=100,
                        placeholder="e.g. Completed 2nd floor slab shuttering; started rebar on east side...")
    issues = st.text_area("Issues / delays / incidents", key="daily_issues", height=70)
    images = image_inputs("daily_imgs", "Site photo(s) (optional)")
    weather_text = st.session_state.get("weather_text", "")
    use_weather = st.checkbox("Include the latest weather forecast (fetch it in the Weather tab first)",
                              value=bool(weather_text), disabled=not weather_text, key="daily_use_weather")
    ready = ai_ok and bool(done.strip())
    if st.button("Generate daily report", type="primary", disabled=not ready, key="daily_go"):
        result = run_ai(lambda: client.generate_structured(
            DailyReport, prompts.daily(day.isoformat(), crew, done, issues, weather_text if use_weather else "",
                                       project_context()), images=images))
        if result:
            st.session_state["daily_result"] = result
    if not done.strip():
        st.caption("Describe today's work to enable the report.")
    r = st.session_state.get("daily_result")
    if not r:
        return
    st.write(r.summary)
    bullet_list("Work completed", r.work_completed)
    bullet_list("Issues", r.issues)
    bullet_list("Safety observations", r.safety_observations)
    bullet_list("Plan for tomorrow", r.plan_for_tomorrow)
    bullet_list("Resource needs", r.resource_needs)
    if r.action_items:
        st.markdown("**Action items**")
        st.dataframe([{"Priority": "%s %s" % (RISK_ICON.get(a.priority, ""), a.priority), "Action": a.action,
                       "Owner": a.owner or "-"} for a in r.action_items], hide_index=True)
    show_json(r, "daily_report.json", "daily")


# --------------------------------------------------------------------------- weather
def render_weather(client: LLMClient) -> None:
    st.subheader("🌦️ Weather-aware construction advisory")
    st.caption("Live forecast from Open-Meteo (free, no key). The go / caution / no-go table is rule-based with "
               "generic thresholds; an optional AI narrative adds scheduling advice.")
    prof = get_profile()
    c1, c2 = st.columns([3, 1])
    place = c1.text_input("Site location (city or town)", value=prof.location, key="wx_place")
    days = int(c2.number_input("Days", min_value=1, max_value=14, value=7, key="wx_days"))
    if st.button("Fetch forecast", type="primary", disabled=not place.strip(), key="wx_go"):
        try:
            with st.spinner("Fetching forecast..."):
                geo = weather.geocode(place)
                fc = weather.fetch_forecast(geo["lat"], geo["lon"], days)
            ass = [weather.assess_day(d) for d in fc]
            st.session_state["wx"] = {"geo": geo, "forecast": fc, "assess": ass}
            st.session_state["weather_text"] = weather.forecast_to_text(fc, ass)
            st.session_state.pop("wx_narrative", None)
        except weather.WeatherError as exc:
            st.error(str(exc))
    wx = st.session_state.get("wx")
    if not wx:
        return
    st.markdown("**Forecast for %s**" % wx["geo"]["name"])
    fc: List[weather.DayForecast] = wx["forecast"]
    st.dataframe([{"Date": d.date, "Conditions": d.conditions, "Tmax °C": d.tmax, "Tmin °C": d.tmin,
                   "Rain mm": d.rain_mm, "Rain %": d.rain_prob, "Gust km/h": d.gust_kmh, "UV": d.uv} for d in fc],
                 hide_index=True)
    st.markdown("**Rule-based site assessment**")
    st.dataframe([dict({"Date": a.date}, **{k: STATUS_ICON[v] for k, v in a.statuses.items()}) for a in wx["assess"]],
                 hide_index=True)
    for a in wx["assess"]:
        if a.notes:
            with st.expander("Notes for " + a.date):
                st.markdown("\n".join("- " + n for n in a.notes))
    disclaimer("Generic rules of thumb. Apply project-specific limits and equipment manufacturer wind/temperature limits.")

    if client.available:
        if st.button("Add AI advisory narrative", key="wx_ai"):
            result = run_ai(lambda: client.generate_structured(
                WeatherNarrative, prompts.weather(st.session_state["weather_text"], wx["geo"]["name"], project_context())))
            if result:
                st.session_state["wx_narrative"] = result
    else:
        st.caption("AI narrative unavailable (no API key). The rule-based table above is still valid.")
    n = st.session_state.get("wx_narrative")
    if n:
        st.write(n.summary)
        for d in n.daily:
            st.markdown("**%s**: do %s; avoid %s" % (d.date, ", ".join(d.recommended) or "-", ", ".join(d.avoid) or "-"))
        bullet_list("Precautions", n.precautions)
        show_json(n, "weather_advisory.json", "wx")


# --------------------------------------------------------------------------- knowledge
def render_knowledge(client: LLMClient) -> None:
    st.subheader("📚 Construction knowledge assistant")
    st.caption("Ask about materials, methods, QA/QC, scheduling or site practice. Answers come from the model's general "
               "knowledge, not from a verified standards database.")
    ai_ok = need_ai(client)
    q = st.text_area("Your question", key="kb_q", height=90,
                     placeholder="e.g. What is the minimum curing period for OPC concrete and why does it matter?")
    use_ctx = st.checkbox("Use my project profile as context", value=False, key="kb_ctx")
    if st.button("Ask", type="primary", disabled=not (ai_ok and q.strip()), key="kb_go"):
        result = run_ai(lambda: client.generate_structured(
            KnowledgeAnswer, prompts.knowledge(q, project_context() if use_ctx else "")))
        if result:
            st.session_state["kb_result"] = result
    r = st.session_state.get("kb_result")
    if not r:
        return
    st.write(r.answer)
    bullet_list("Key points", r.key_points)
    bullet_list("Standards to check (verify edition and local applicability)", r.standards_to_check)
    bullet_list("Follow-up questions", r.follow_up_questions)
    st.caption("Model confidence: %s" % r.confidence)
    disclaimer("General guidance only. Follow the governing code, drawings and your engineer's instructions.")
    show_json(r, "knowledge_answer.json", "kb")
