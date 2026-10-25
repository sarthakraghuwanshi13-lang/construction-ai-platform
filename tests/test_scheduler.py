import unittest
from datetime import date
from types import SimpleNamespace as NS

from construction_ai import scheduler as sch
from construction_ai.schemas import TaskSpec


def T(i, dur, deps=()):
    return NS(id=i, name=i, phase="", duration_days=dur, depends_on=list(deps))


class SchedulerTests(unittest.TestCase):
    def test_critical_path_and_slack(self):
        tasks = [T("A", 3), T("B", 5, ["A"]), T("C", 2, ["A"]), T("D", 1, ["B", "C"])]
        res = {s.id: s for s in sch.schedule(tasks, date(2026, 11, 2))}  # Monday
        self.assertTrue(res["A"].critical and res["B"].critical and res["D"].critical)
        self.assertFalse(res["C"].critical)
        self.assertEqual(res["C"].slack_days, 3)
        self.assertEqual(res["A"].start, date(2026, 11, 2))
        self.assertEqual(res["A"].end, date(2026, 11, 4))
        self.assertEqual(res["B"].start, date(2026, 11, 5))

    def test_sunday_skipped(self):
        # Mon 2 Nov 2026, 7 working days with Mon-Sat week -> ends Mon 9 Nov (Sunday 8th skipped)
        res = sch.schedule([T("A", 7)], date(2026, 11, 2))
        self.assertEqual(res[0].end, date(2026, 11, 9))
        res5 = sch.schedule([T("A", 6)], date(2026, 11, 2), work_week=(0, 1, 2, 3, 4))
        self.assertEqual(res5[0].end, date(2026, 11, 9))

    def test_start_on_weekend_rolls_forward(self):
        res = sch.schedule([T("A", 1)], date(2026, 11, 1))  # Sunday
        self.assertEqual(res[0].start, date(2026, 11, 2))

    def test_holiday(self):
        res = sch.schedule([T("A", 2)], date(2026, 11, 2), holidays=[date(2026, 11, 3)])
        self.assertEqual(res[0].end, date(2026, 11, 4))

    def test_validation_errors(self):
        with self.assertRaises(ValueError):
            sch.validate_tasks([])
        with self.assertRaises(ValueError):
            sch.validate_tasks([T("A", 1), T("A", 1)])
        with self.assertRaises(ValueError):
            sch.validate_tasks([T("A", 1, ["Q"])])
        with self.assertRaises(ValueError):
            sch.validate_tasks([T("A", 1, ["A"])])
        with self.assertRaises(ValueError):
            sch.validate_tasks([T("A", 1, ["B"]), T("B", 1, ["A"])])
        with self.assertRaises(ValueError):
            sch.validate_tasks([T("A", 0)])
        with self.assertRaises(ValueError):
            sch.schedule([T("A", 1)], date(2026, 11, 2), work_week=())

    def test_template_is_valid_and_scales(self):
        small = [TaskSpec(**d) for d in sch.default_template(1, 800)]
        big = [TaskSpec(**d) for d in sch.default_template(3, 3000)]
        sch.validate_tasks(small)
        sch.validate_tasks(big)
        s_end = sch.project_end(sch.schedule(small, date(2026, 11, 2)))
        b_end = sch.project_end(sch.schedule(big, date(2026, 11, 2)))
        self.assertGreater(b_end, s_end)
        self.assertGreater(len(big), len(small))
        self.assertTrue(any(s.critical for s in sch.schedule(big, date(2026, 11, 2))))


if __name__ == "__main__":
    unittest.main()
