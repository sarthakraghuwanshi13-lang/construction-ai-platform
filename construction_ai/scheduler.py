"""Deterministic task scheduling: validation, working-day calendar, critical path.

Tasks are duck-typed: any object with ``id``, ``name``, ``phase``,
``duration_days`` and ``depends_on`` attributes works.
"""
from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Dict, Iterable, List, Sequence, Set


def validate_tasks(tasks: Sequence) -> None:
    """Raise ValueError for empty lists, duplicate ids, bad dependencies or cycles."""
    if not tasks:
        raise ValueError("Task list is empty.")
    ids = [t.id for t in tasks]
    if len(set(ids)) != len(ids):
        dupes = sorted({i for i in ids if ids.count(i) > 1})
        raise ValueError("Duplicate task ids: " + ", ".join(dupes))
    known = set(ids)
    for t in tasks:
        if t.duration_days < 1:
            raise ValueError("Task '%s' has duration < 1 day." % t.id)
        for d in t.depends_on:
            if d == t.id:
                raise ValueError("Task '%s' depends on itself." % t.id)
            if d not in known:
                raise ValueError("Task '%s' depends on unknown task '%s'." % (t.id, d))
    _topological_order(tasks)  # raises on cycles


def _topological_order(tasks: Sequence) -> List[str]:
    indeg: Dict[str, int] = {t.id: len(set(t.depends_on)) for t in tasks}
    children: Dict[str, List[str]] = {t.id: [] for t in tasks}
    for t in tasks:
        for d in set(t.depends_on):
            children[d].append(t.id)
    queue = deque(i for i, n in indeg.items() if n == 0)
    order: List[str] = []
    while queue:
        cur = queue.popleft()
        order.append(cur)
        for c in children[cur]:
            indeg[c] -= 1
            if indeg[c] == 0:
                queue.append(c)
    if len(order) != len(tasks):
        stuck = sorted(i for i, n in indeg.items() if n > 0)
        raise ValueError("Circular dependency among tasks: " + ", ".join(stuck))
    return order


@dataclass
class ScheduledTask:
    id: str
    name: str
    phase: str
    duration_days: int
    depends_on: List[str]
    start: date
    end: date
    slack_days: int
    critical: bool


def _working_days(start: date, count: int, work_week: Iterable[int], holidays: Set[date]) -> List[date]:
    """First ``count`` working days on/after ``start``."""
    wk = set(work_week)
    if not wk:
        raise ValueError("work_week must contain at least one weekday.")
    out: List[date] = []
    cur = start
    guard = 0
    while len(out) < count:
        if cur.weekday() in wk and cur not in holidays:
            out.append(cur)
        cur += timedelta(days=1)
        guard += 1
        if guard > 20000:
            raise ValueError("Calendar produced no working days (check holidays).")
    return out


def schedule(
    tasks: Sequence,
    start: date,
    work_week: Iterable[int] = (0, 1, 2, 3, 4, 5),
    holidays: Iterable[date] = (),
) -> List[ScheduledTask]:
    """Forward/backward pass. Durations are in working days. Returns tasks in input order."""
    validate_tasks(tasks)
    by_id = {t.id: t for t in tasks}
    order = _topological_order(tasks)

    es: Dict[str, int] = {}
    ef: Dict[str, int] = {}
    for tid in order:
        t = by_id[tid]
        es[tid] = max((ef[d] for d in t.depends_on), default=0)
        ef[tid] = es[tid] + t.duration_days
    project_len = max(ef.values())

    successors: Dict[str, List[str]] = {t.id: [] for t in tasks}
    for t in tasks:
        for d in set(t.depends_on):
            successors[d].append(t.id)
    ls: Dict[str, int] = {}
    for tid in reversed(order):
        lf = min((ls[s] for s in successors[tid]), default=project_len)
        ls[tid] = lf - by_id[tid].duration_days

    days = _working_days(start, project_len, work_week, set(holidays))
    result: List[ScheduledTask] = []
    for t in tasks:
        slack = ls[t.id] - es[t.id]
        result.append(
            ScheduledTask(
                id=t.id,
                name=t.name,
                phase=getattr(t, "phase", "") or "",
                duration_days=t.duration_days,
                depends_on=list(t.depends_on),
                start=days[es[t.id]],
                end=days[ef[t.id] - 1],
                slack_days=slack,
                critical=(slack == 0),
            )
        )
    return result


def project_end(scheduled: Sequence[ScheduledTask]) -> date:
    return max(s.end for s in scheduled)


def default_template(floors: int = 1, area_sqft: float = 1500.0) -> List[dict]:
    """Generic residential RCC-frame task template (NOT AI generated).

    ``area_sqft`` is the TOTAL built-up area across all floors. Durations are working
    days, scaled by sqrt(total area / 1500 sq ft); extra floors also add repeated
    structure tasks. They are placeholders to be reviewed by a planner, not benchmarks.
    """
    floors = max(1, int(floors))
    area = max(100.0, float(area_sqft))
    k = max(0.6, min(3.0, math.sqrt(area / 1500.0)))

    def d(base: int) -> int:
        return max(1, int(round(base * k)))

    tasks: List[dict] = [
        dict(id="T1", name="Site clearing, marking and setting out", phase="Site preparation", duration_days=d(3), depends_on=[]),
        dict(id="T2", name="Excavation for foundation", phase="Foundation", duration_days=d(5), depends_on=["T1"]),
        dict(id="T3", name="PCC, footing reinforcement and concreting", phase="Foundation", duration_days=d(12), depends_on=["T2"]),
        dict(id="T4", name="Plinth beam, backfilling and plinth filling", phase="Foundation", duration_days=d(7), depends_on=["T3"]),
    ]
    prev = "T4"
    n = 5
    brick_ids: List[str] = []
    for f in range(1, floors + 1):
        slab_id, brick_id = "T%d" % n, "T%d" % (n + 1)
        tasks.append(dict(id=slab_id, name="Floor %d columns, beams and slab (formwork, rebar, pour)" % f,
                          phase="Structure", duration_days=d(14), depends_on=[prev]))
        tasks.append(dict(id=brick_id, name="Floor %d brickwork / block masonry" % f,
                          phase="Structure", duration_days=d(12), depends_on=[slab_id]))
        brick_ids.append(brick_id)
        prev = slab_id  # next floor's frame can start after this slab has cured
        n += 2
    last_brick = brick_ids[-1]
    mep, plaster, floor, doors, fin_mep, paint, ext, handover = (
        "T%d" % (n + i) for i in range(8)
    )
    tasks += [
        dict(id=mep, name="Electrical conduits and plumbing rough-in", phase="MEP", duration_days=d(10), depends_on=[last_brick]),
        dict(id=plaster, name="Internal and external plastering", phase="Finishing", duration_days=d(15), depends_on=[mep]),
        dict(id=floor, name="Flooring and tiling", phase="Finishing", duration_days=d(12), depends_on=[plaster]),
        dict(id=doors, name="Doors, windows and railings", phase="Finishing", duration_days=d(8), depends_on=[plaster]),
        dict(id=fin_mep, name="Electrical fixtures and plumbing fittings", phase="MEP", duration_days=d(8), depends_on=[floor]),
        dict(id=paint, name="Painting and final finishes", phase="Finishing", duration_days=d(12), depends_on=[floor, doors]),
        dict(id=ext, name="External works and cleanup", phase="Handover", duration_days=d(7), depends_on=[plaster]),
        dict(id=handover, name="Final inspection, snag list and handover", phase="Handover", duration_days=d(3), depends_on=[fin_mep, paint, ext]),
    ]
    return tasks
