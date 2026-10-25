import unittest

from construction_ai import estimator as E
from construction_ai.crack_rules import classify_width_mm


class EstimatorTests(unittest.TestCase):
    def test_to_sqft(self):
        self.assertAlmostEqual(E.to_sqft(100, "sq m"), 1076.39, places=2)
        self.assertEqual(E.to_sqft(1200, "sq ft"), 1200)
        for bad in (0, -5):
            with self.assertRaises(E.EstimateError):
                E.to_sqft(bad, "sq ft")
        with self.assertRaises(E.EstimateError):
            E.to_sqft(10, "acres")

    def test_quick_estimate_math(self):
        rules = {k: v[1] for k, v in E.THUMB_RULES.items()}
        lines = E.quick_estimate(1000, rules, E.DEFAULT_RATES, wastage_pct=0)
        by = {l.item: l for l in lines}
        self.assertEqual(by["Cement"].quantity, 400.0)
        self.assertEqual(by["Cement"].amount, 400.0 * 400.0)
        self.assertEqual(by["Steel (TMT)"].quantity, 4000.0)
        with_waste = E.quick_estimate(1000, rules, E.DEFAULT_RATES, wastage_pct=10)
        self.assertAlmostEqual({l.item: l for l in with_waste}["Cement"].quantity, 440.0)

    def test_quick_estimate_validation(self):
        with self.assertRaises(E.EstimateError):
            E.quick_estimate(0, {"Cement": 0.4}, {})
        with self.assertRaises(E.EstimateError):
            E.quick_estimate(100, {"Cement": 0.4}, {}, wastage_pct=80)
        with self.assertRaises(E.EstimateError):
            E.quick_estimate(100, {"Cement": -1}, {})
        with self.assertRaises(E.EstimateError):
            E.quick_estimate(100, {"Cement": 1}, {"Cement": -3})

    def test_concrete_m20_one_cubic_metre(self):
        r = E.concrete_materials(1.0)  # 1:1.5:3 -> dry 1.54 m3, cement 1.54/5.5 m3
        self.assertAlmostEqual(r["cement_bags"], 1.54 / 5.5 * 1440 / 50, delta=0.1)
        self.assertAlmostEqual(r["sand_m3"], 1.54 * 1.5 / 5.5, delta=0.01)
        self.assertAlmostEqual(r["aggregate_m3"], 1.54 * 3 / 5.5, delta=0.01)
        with self.assertRaises(E.EstimateError):
            E.concrete_materials(0)
        with self.assertRaises(E.EstimateError):
            E.concrete_materials(1, (1, 0, 3))

    def test_brickwork(self):
        r = E.brickwork_materials(10, 3, 230, opening_pct=0, wastage_pct=0)
        self.assertAlmostEqual(r["brickwork_m3"], 6.9, places=3)
        self.assertAlmostEqual(r["bricks"], 3450.0)
        self.assertGreater(r["cement_bags"], 0)
        with self.assertRaises(E.EstimateError):
            E.brickwork_materials(10, 3, 230, opening_pct=100)
        with self.assertRaises(E.EstimateError):
            E.brickwork_materials(0, 3, 230)

    def test_cost_summary(self):
        lines = [E.MaterialLine("a", "u", 1, 100, 100.0)]
        s = E.cost_summary(lines, labour_pct=50, contingency_pct=10)
        self.assertEqual(s["materials"], 100.0)
        self.assertEqual(s["labour_and_other"], 50.0)
        self.assertEqual(s["contingency"], 15.0)
        self.assertEqual(s["total"], 165.0)
        with self.assertRaises(E.EstimateError):
            E.cost_summary(lines, labour_pct=-1)

    def test_benchmark_and_baseline(self):
        self.assertEqual(E.benchmark_cost(1000, "Standard"), 1900000.0)
        with self.assertRaises(E.EstimateError):
            E.benchmark_cost(1000, "Luxury")
        b = E.cost_approach_baseline(1000, 5000, 1200, 2000, age_years=30)
        self.assertEqual(b["land_value"], 5_000_000.0)
        self.assertEqual(b["depreciation_pct"], 50.0)
        self.assertEqual(b["building_value"], 1200 * 2000 * 0.5)
        old = E.cost_approach_baseline(1000, 5000, 1200, 2000, age_years=500)
        self.assertEqual(old["depreciation_pct"], 70.0)
        with self.assertRaises(E.EstimateError):
            E.cost_approach_baseline(-1, 1, 1, 1, 1)


class CrackRuleTests(unittest.TestCase):
    def test_categories(self):
        cases = [(0.05, 0), (0.1, 1), (1.0, 1), (3, 2), (5, 2), (10, 3), (20, 4), (30, 5)]
        for width, cat in cases:
            self.assertEqual(classify_width_mm(width)[0], cat, width)
        with self.assertRaises(ValueError):
            classify_width_mm(-1)


if __name__ == "__main__":
    unittest.main()
