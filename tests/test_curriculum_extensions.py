"""Independent regression checks for the added goal-aligned exercises."""

from collections import Counter
from fractions import Fraction
from math import isclose
import json
import re
import unittest

from backend import curriculum_extensions as ext


def split_pair(task):
    return tuple(Fraction(part) for part in task["answer"].split(";"))


def ordered_labels(task):
    options = {item["value"]: item["label"] for item in task["response"]["options"]}
    return [options[value] for value in task["answer"].split(",")]


def choice_label(task):
    return next(option["label"] for option in task["response"]["options"] if option["value"] == task["answer"])


class ExtensionContentTests(unittest.TestCase):
    def test_each_topic_is_complete_and_every_family_has_100_distinct_seeds(self):
        self.assertEqual(len(ext.TOPICS), 12)
        count = 0
        for topic in ext.TOPICS:
            body = topic["lesson"]
            self.assertGreaterEqual(len(body["theory"]), 3)
            self.assertGreaterEqual(len(body["examples"]), 2)
            self.assertTrue(all(len(item["steps"]) >= 3 for item in body["examples"]))
            self.assertGreaterEqual(len(body["mistakes"]), 2)
            self.assertGreaterEqual(len(body["checks"]), 2)
            self.assertEqual(len(ext.FAMILIES[topic["id"]]), len(ext.LEVELS_BY_TOPIC[topic["id"]]))
            seen = set()
            for family in ext.FAMILIES[topic["id"]]:
                for i in range(10):
                    for j in range(10):
                        task = family(i, j)
                        json.dumps(task, allow_nan=False)
                        self.assertEqual(task, family(i, j), family.__name__)
                        self.assertNotIn(task["ru"], seen, (family.__name__, i, j))
                        seen.add(task["ru"])
                        self.assertGreaterEqual(len(task["solution"]), 2)
                        self.assertNotIn(task["hints"][1], task["solution"])
                        if "response" in task:
                            spec = task["response"]
                            self.assertIn(spec["kind"], {"pair", "choice", "sequence", "interval", "fraction"})
                            if "options" in spec:
                                labels = [option["label"] for option in spec["options"]]
                                self.assertEqual(len(set(labels)), len(labels))
                                if spec["kind"] == "choice":
                                    self.assertIn(task["answer"], {o["value"] for o in spec["options"]})
                                else:
                                    self.assertEqual(len(task["answer"].split(",")), len(labels))
                                    self.assertEqual(len(set(task["answer"].split(","))), len(labels))
                        count += 1
            self.assertEqual(len(seen), 300)
        self.assertEqual(count, 3600)

    def test_all_coordinate_pairs_satisfy_both_equations_and_context(self):
        for i in range(10):
            for j in range(10):
                task = ext.systems_pair_eliminate(i, j)
                x, y = split_pair(task)
                s, d = map(int, re.search(r"x\+y=(-?\d+), x−y=(-?\d+)", task["ru"]).groups())
                self.assertEqual(x + y, s)
                self.assertEqual(x - y, d)
                task = ext.systems_pair_intersection(i, j)
                x, y = split_pair(task)
                b, c = map(int, re.search(r"y=2x\+\((-?\d+)\) и y=−x\+\((-?\d+)\)", task["ru"]).groups())
                self.assertEqual(y, 2*x + b)
                self.assertEqual(y, -x + c)
                graph = task["graph"]
                self.assertEqual(graph["m1"]*x + graph["b1"], graph["m2"]*x + graph["b2"])
                task = ext.systems_pair_model(i, j)
                adult, child = split_pair(task)
                total, second = map(int, re.findall(r"стоят (\d+)", task["ru"]))
                self.assertGreater(adult, 0)
                self.assertGreater(child, 0)
                self.assertEqual(3*adult + 2*child, total)
                self.assertEqual(adult + child, second)

    def test_modulus_pair_contains_every_real_root(self):
        for family in (ext.modulus_factor, ext.modulus_square, ext.modulus_shifted):
            for i in range(10):
                for j in range(10):
                    task = family(i, j)
                    supplied = split_pair(task)
                    self.assertLess(supplied[0], supplied[1])
                    if family is ext.modulus_factor:
                        coefficient, constant = map(int, re.search(r"x²\+(\d+)·\|x\|−(\d+)=0", task["ru"]).groups())
                        actual = [x for x in range(-30, 31) if x*x+coefficient*abs(x)-constant == 0]
                    elif family is ext.modulus_square:
                        inside, outside = map(int, re.search(r"\|x²\+(\d+)\|=(\d+)", task["ru"]).groups())
                        actual = [x for x in range(-30, 31) if abs(x*x+inside) == outside]
                    else:
                        h, coefficient, constant = map(int, re.search(
                            r"\(x−\((-?\d+)\)\)²\+(\d+)·\|x−\(-?\d+\)\|−(\d+)=0", task["ru"]).groups())
                        actual = [x for x in range(-30, 31) if (x-h)**2+coefficient*abs(x-h)-constant == 0]
                    self.assertEqual(tuple(actual), supplied)
                    # Every t-polynomial is upward quadratic with one positive and one negative root.
                    # The positive t yields exactly the two supplied x and no nonintegral x.

    def test_full_intervals_match_signs_at_boundaries_and_interior(self):
        for family in (ext.quadratic_interval, ext.rational_interval, ext.intersection_interval):
            for i in range(10):
                for j in range(10):
                    task = family(i, j)
                    a, b = map(int, re.search(r"x−\((-?\d+)\).*?x−(\d+)", task["ru"]).groups())
                    answer = task["answer"]
                    lo, hi = map(Fraction, answer[1:-1].split(";"))
                    samples = {Fraction(a), Fraction(b), Fraction(a-1), Fraction(b+1),
                               Fraction(a+b, 2), lo, hi, lo-Fraction(1, 2), lo+Fraction(1, 2)}
                    for x in samples:
                        if family is ext.rational_interval:
                            true = x != b and (x-a)/(x-b) <= 0
                        elif family is ext.intersection_interval:
                            bound = int(re.search(r"и x>(-?\d+)", task["ru"])[1])
                            true = (x-a)*(x-b) <= 0 and x > bound
                        else:
                            true = (x-a)*(x-b) <= 0
                        reported = (x > lo or x == lo and answer[0] == "[") and (
                            x < hi or x == hi and answer[-1] == "]")
                        self.assertEqual(true, reported, (family.__name__, i, j, x))

    def test_measurement_units_precision_and_errors(self):
        for i in range(10):
            for j in range(10):
                task = ext.units_scientific(i, j)
                a, n = split_pair(task)
                lengths = list(map(int, re.findall(r"(\d+) мм", task["ru"])))
                exact_m2 = Fraction(lengths[0]*lengths[1], 1_000_000)
                self.assertEqual(a * Fraction(10)**n, exact_m2)
                self.assertTrue(1 <= a < 10)
                task = ext.errors_pair(i, j)
                delta, relative = split_pair(task)
                actual, approx = map(int, re.findall(r"(\d+) г", task["ru"]))
                self.assertEqual(delta, abs(approx-actual))
                self.assertEqual(relative, delta/actual)
                task = ext.round_scientific(i, j)
                a, n = split_pair(task)
                initial = int(re.search(r"число (\d+)", task["ru"])[1])
                candidates = [number for number in range(12000, 15001, 100)]
                rounded = min(candidates, key=lambda number: (abs(number-initial), -number))
                self.assertEqual(a * Fraction(10)**n, rounded)

    def test_raw_frequency_tables_include_boundary_and_multiplicity(self):
        for i in range(10):
            for j in range(10):
                for family in (ext.frequencies_pair, ext.relative_frequency_pair):
                    task = family(i, j)
                    raw = task["ru"].split(": ", 1)[1].split(". ", 1)[0]
                    data = [int(number) for number in raw.split(", ")]
                    first, second = split_pair(task)
                    counts = (sum(0 <= x < 10 for x in data), sum(10 <= x < 20 for x in data))
                    expected = counts if family is ext.frequencies_pair else tuple(Fraction(n, len(data)) for n in counts)
                    self.assertEqual((first, second), expected)
                task = ext.frequency_table_choice(i, j)
                data = [int(number) for number in task["ru"].split(": ", 1)[1].split(". ", 1)[0].split(", ")]
                table = choice_label(task)
                counts = [int(number) for number in re.findall(r"\): (\d+)", table)]
                self.assertEqual(counts, [sum(start <= x < start+5 for x in data) for start in (0, 5, 10)])

    def test_periods_match_exact_infinite_series(self):
        for i in range(10):
            for j in range(10):
                task = ext.pure_period(i, j)
                digits = re.search(r"0,\((\d+)\)", task["ru"])[1]
                self.assertEqual(len(digits), 2)
                exact = Fraction(int(digits), 10**len(digits)-1)
                self.assertTrue(isclose(task["answer"], float(exact), rel_tol=1e-14, abs_tol=1e-14))
                task = ext.mixed_period(i, j)
                prefix_text, cycle_text = re.search(r"0,(\d+)\((\d)\)", task["ru"]).groups()
                places=len(prefix_text)
                prefix, cycle = int(prefix_text), int(cycle_text)
                exact = Fraction(prefix, 10**places) + Fraction(cycle, 10**(places+1)) / (1-Fraction(1, 10))
                self.assertTrue(isclose(task["answer"], float(exact), rel_tol=1e-14, abs_tol=1e-14))
                task = ext.period_series(i, j)
                numerator = int(re.search(r"ряд (\d+)/1000", task["ru"])[1])
                # Cross multiply the geometric-sum identity independently.
                self.assertTrue(isclose(task["answer"] * 999, numerator, rel_tol=1e-14))

    def test_circle_theorems_and_geometric_feasibility(self):
        for i in range(10):
            for j in range(10):
                task = ext.inscribed_angle(i, j)
                arc1, arc2 = map(int, re.search(r"меры (\d+)° и (\d+)°", task["ru"]).groups())
                self.assertEqual(task["answer"]*2, arc1+arc2)
                self.assertTrue(0 < task["answer"] < 180)
                task = ext.chord_product(i, j)
                ap, pb, cp = map(int, re.search(r"AP=(\d+), PB=(\d+), CP=(\d+)", task["ru"]).groups())
                self.assertGreater(task["answer"], 0)
                self.assertTrue(isclose(cp*task["answer"], ap*pb))
                task = ext.secant_product(i, j)
                pa, pb, pc = map(int, re.search(r"PA=(\d+), PB=(\d+), PC=(\d+)", task["ru"]).groups())
                pd = task["answer"]+pc
                self.assertGreater(pd, pc)
                self.assertGreater(pb, pa)
                self.assertTrue(isclose(pa*pb, pc*pd))

    def test_thales_uses_parallelism_and_proportional_lengths(self):
        for i in range(10):
            for j in range(10):
                task = ext.thales_equal(i, j)
                n = int(re.search(r"получились (\d+) равных", task["ru"])[1])
                length = int(re.search(r"равен (\d+) см", task["ru"])[1])
                self.assertEqual(task["answer"], n*length)
                task = ext.thales_ratio(i, j)
                ad, db, ae = map(int, re.search(r"AD=(\d+), DB=(\d+), AE=(\d+)", task["ru"]).groups())
                self.assertTrue(isclose(ad*task["answer"], ae*db))

    def test_construction_chains_have_valid_dependencies_and_conditions(self):
        first_marker = {
            ext.midpoint_construction: "С центром A",
            ext.angle_bisector_construction: "Проводим окружность",
            ext.angle_copy_construction: "В исходном угле",
            ext.construct_sss: "Проверяем",
            ext.construct_sas: "Откладываем",
            ext.construct_asa: "Проверяем",
            ext.thales_construct: "Из A",
        }
        for family, marker in first_marker.items():
            for i in range(10):
                for j in range(10):
                    task = family(i, j)
                    steps = ordered_labels(task)
                    self.assertTrue(steps[0].startswith(marker), family.__name__)
                    self.assertEqual(len(steps), 4)
                    if family is ext.midpoint_construction:
                        length = int(re.search(r"длиной (\d+) см", task["ru"])[1])
                        radius = int(re.search(r"циркуля (\d+) см", task["ru"])[1])
                        self.assertGreater(2*radius, length)
                        self.assertIn("перпендикуляр", steps[-1])
                    elif family is ext.construct_sss:
                        ab, ac, bc = map(int, re.search(r"AB=(\d+), AC=(\d+), BC=(\d+)", task["ru"]).groups())
                        self.assertLess(max(ab, ac, bc), ab+ac+bc-max(ab, ac, bc))
                        self.assertIn("пересечение", steps[2])
                    elif family is ext.construct_asa:
                        alpha, beta = map(int, re.search(r"∠A=(\d+)°, ∠B=(\d+)°", task["ru"]).groups())
                        self.assertTrue(0 < alpha+beta < 180)
                        self.assertIn("пересечение", steps[-1].lower())

    def test_proof_and_induction_chains_and_conservative_evidence(self):
        for i in range(10):
            for j in range(10):
                task = ext.theorem_parts(i, j)
                correct = choice_label(task)
                self.assertTrue(correct.startswith("Углы A и B смежные"))
                base, addition = map(int, re.search(r"∠A=(\d+)\+(\d+)", task["ru"]).groups())
                conclusion = int(re.search(r"; ∠B=(\d+)", correct)[1])
                self.assertEqual(base+addition+conclusion, 180)
                self.assertIn("Получаем ∠AOC=∠BOD", ordered_labels(ext.direct_proof(i, j))[-1])
                self.assertIn("противоречие", ordered_labels(ext.contradiction(i, j))[-1])
                for family in (ext.induction_sum, ext.induction_odd):
                    steps = ordered_labels(family(i, j))
                    self.assertIn("n=1", steps[0])
                    self.assertIn("k+1", steps[-1])
                task = ext.induction_divisibility(i, j)
                a, divisor = map(int, re.search(r"что (\d+)\^n−1 делится на (\d+)", task["ru"]).groups())
                self.assertEqual((a-1) % divisor, 0)
                self.assertIn(f"{a}·({a}^k−1)", choice_label(task))
                for k in (1, 2, 5):
                    self.assertEqual(a**(k+1)-1, a*(a**k-1)+(a-1))
        constrained = {"7.1.1.4", "7.1.2.16", "7.1.2.17", "7.1.2.18", "8.1.1.9", "9.2.3.3"}
        for goal in ext.GOAL_EVIDENCE:
            if goal["code"] in constrained:
                self.assertEqual(goal["status"], "P")


if __name__ == "__main__":
    unittest.main()
