import unittest

from pydantic import ValidationError

from construction_ai import schemas as S


class SchemaTests(unittest.TestCase):
    def test_safety_normalizes_case_and_ignores_extra(self):
        r = S.SafetyReport.model_validate(
            {"summary": "ok", "overall_risk": " HIGH ", "ppe": [{"item": "hard hat", "status": "Missing"}], "bogus": 1}
        )
        self.assertEqual(r.overall_risk, "high")
        self.assertEqual(r.ppe[0].status, "missing")

    def test_safety_rejects_bad_risk(self):
        with self.assertRaises(ValidationError):
            S.SafetyReport.model_validate({"summary": "x", "overall_risk": "extreme"})

    def test_crack_requires_core_fields(self):
        with self.assertRaises(ValidationError):
            S.CrackReport.model_validate({"crack_visible": True})

    def test_crack_negative_width_rejected(self):
        with self.assertRaises(ValidationError):
            S.CrackReport.model_validate(
                dict(crack_visible=True, crack_type="x", estimated_width_mm=-1, severity="minor",
                     severity_rationale="r", needs_structural_engineer=False, confidence="low"))

    def test_valuation_ordering_enforced(self):
        base = dict(currency="INR", method="m", confidence="low")
        S.ValuationReport(estimated_value_low=1, estimated_value_mid=2, estimated_value_high=3, **base)
        with self.assertRaises(ValidationError):
            S.ValuationReport(estimated_value_low=5, estimated_value_mid=2, estimated_value_high=3, **base)

    def test_plan_rejects_cycle_unknown_dep_and_duplicates(self):
        def t(i, deps):
            return {"id": i, "name": i, "duration_days": 2, "depends_on": deps}
        S.ProjectPlan.model_validate({"tasks": [t("A", []), t("B", ["A"])]})
        with self.assertRaises(ValidationError):
            S.ProjectPlan.model_validate({"tasks": [t("A", ["B"]), t("B", ["A"])]})
        with self.assertRaises(ValidationError):
            S.ProjectPlan.model_validate({"tasks": [t("A", ["Z"])]})
        with self.assertRaises(ValidationError):
            S.ProjectPlan.model_validate({"tasks": [t("A", []), t("A", [])]})
        with self.assertRaises(ValidationError):
            S.ProjectPlan.model_validate({"tasks": []})

    def test_plan_duration_bounds(self):
        with self.assertRaises(ValidationError):
            S.ProjectPlan.model_validate({"tasks": [{"id": "A", "name": "a", "duration_days": 0}]})


if __name__ == "__main__":
    unittest.main()
