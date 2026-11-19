"""Regression cases for mathematical teaching defects found by the independent audit."""

import hashlib
import json
from math import acos, degrees, sqrt
import tempfile
import unittest
from unittest.mock import patch

from backend import content, grade7, grade8, grade9
from backend.grading import AnswerError, sat_matches, structured_matches
from backend.storage import ApiError, StudyStore


BANKS = (content, grade7, grade8, grade9)
ORIGINAL_ANSWER_DIGEST = "d05dd52aced6eac84db646b35cd5e488ce966cb2e8f0dae61964779f33c648ad"


def topic_lesson(bank, topic_id):
    return next(topic["lesson"] for topic in bank.TOPICS if topic["id"] == topic_id)


class MathRepairTests(unittest.TestCase):
    def test_exact_pairs_preserve_fraction_equality(self):
        response = {"kind": "pair"}
        self.assertTrue(structured_matches("2/6;4/6", response, "1/3;2/3"))
        self.assertTrue(structured_matches("(0,5; 2/1)", response, "1/2;2"))
        self.assertFalse(structured_matches("1.00000000001;2", response, "1;2"))
        self.assertFalse(structured_matches("0.3333333333;2/3", response, "1/3;2/3"))

    def test_intervals_normalize_equivalent_infinity_and_fraction_endpoints(self):
        response = {"kind": "interval"}
        self.assertTrue(structured_matches("(1;+inf)", response, "(1;∞)"))
        self.assertTrue(structured_matches("(1;∞)", response, "(1;+inf)"))
        self.assertTrue(structured_matches("[2/4;2.0)", response, "[0,5;2)"))
        self.assertFalse(structured_matches("(1/2;2)", response, "[1/2;2)"))

    def test_sat_padding_cannot_reduce_required_decimal_precision(self):
        for answer in ("2/3", ".6666", ".6667", "0.666", "0.667"):
            self.assertTrue(sat_matches(answer, 2/3), answer)
        for answer in ("00.67", "000.7", "-00.33", "-000.3"):
            with self.subTest(answer=answer):
                try:
                    accepted = sat_matches(answer, -1/3 if answer.startswith("-") else 2/3)
                except AnswerError:
                    accepted = False
                self.assertFalse(accepted)

    def test_sat_disallows_signs_inside_fraction_and_leading_plus(self):
        for answer, target in (("+2/3", 2/3), ("1/-2", -.5), ("1/+2", .5), ("2/.5", 4)):
            with self.subTest(answer=answer):
                try:
                    accepted = sat_matches(answer, target)
                except AnswerError:
                    accepted = False
                self.assertFalse(accepted)

    def test_sat_large_integer_uses_an_answerable_response(self):
        with tempfile.TemporaryDirectory() as directory:
            store = StudyStore(directory)
            with patch.object(store, "select_questions", return_value=[["powers", 0], ["powers", 256]]):
                state = store.start({"mode": "practice", "lang": "en", "topics": ["powers"], "count": 2})
            first = content.generate("powers", 0, "en")["answer"]
            store.access(state["id"], "answer", {"index": 0, "answer": str(first)})
            second = store.access(state["id"], "next", {"index": 0})
            self.assertEqual(second["question"]["id"], "powers:256")
            self.assertTrue(second["question"].get("options"), "Six-digit integer cannot fit a SAT SPR field")
            result = store.access(state["id"], "answer", {"index": 1, "answer": "823543"})
            self.assertTrue(result["feedback"]["correct"])

    def test_periodic_fraction_practice_rejects_an_approximation(self):
        with tempfile.TemporaryDirectory() as directory:
            store = StudyStore(directory)
            state = store.start({"mode": "practice", "count": 1, "problemId": "g9-periodic-fractions:33"})
            with self.assertRaises(ApiError) as error:
                store.access(state["id"], "answer", {"index": 0, "answer": "0.3333333333"})
            self.assertEqual(error.exception.status, 400)
            result = store.access(state["id"], "answer", {"index": 0, "answer": "1/3"})
            self.assertTrue(result["feedback"]["correct"])
            self.assertEqual(result["feedback"]["answer"], "1/3")

    def test_vector_angle_rule_covers_endpoints_and_zero_vector(self):
        lesson = topic_lesson(grade9, "g9-dot-product")
        theory = " ".join(lesson["theory"])
        self.assertIn("0°≤θ<90°", theory)
        self.assertIn("90°<θ≤180°", theory)
        self.assertIn("Угол с нулевым вектором не определён", theory)
        questions = {check["prompt"]: check["answer"] for check in lesson["checks"]}
        cases = (
            ((1, 0), (2, 0), 0, "Каков угол между (1; 0) и (2; 0)?"),
            ((1, 0), (-2, 0), 180, "Каков угол между (1; 0) и (−2; 0)?"),
            ((1, 0), (0, 2), 90, "Каков угол между (1; 0) и (0; 2)?"),
        )
        for u, v, expected, prompt in cases:
            actual = degrees(acos(sum(a*b for a, b in zip(u, v)) /
                                  (sqrt(sum(x*x for x in u))*sqrt(sum(x*x for x in v)))))
            self.assertAlmostEqual(actual, expected)
            self.assertTrue(questions[prompt].startswith(str(expected)+"°"))
        zero_answer = questions["Можно ли вычислить угол между (0; 0) и (2; 3)?"]
        self.assertIn("нет направления", zero_answer)

    def test_exponential_model_explains_initial_value_assumptions(self):
        lesson = grade9.LEGACY_LESSONS["exponential"]["lesson"]
        theory = " ".join(lesson["theory"])
        self.assertIn("При A₀>0", theory)
        self.assertIn("Если A₀=0", theory)
        self.assertIn("Если A₀<0", theory)
        checks = {check["prompt"]: check["answer"] for check in lesson["checks"]}
        self.assertIn("равна нулю", checks["Растёт ли A(t)=0·2ᵗ?"])
        self.assertIn("Убывает", checks["Как меняется A(t)=−2ᵗ при увеличении t?"])
        for initial, ratio, direction in ((1, 2, 1), (1, .5, -1), (-1, 2, -1), (-1, .5, 1)):
            values = [initial*ratio**time for time in range(4)]
            self.assertTrue(all(direction*(b-a) > 0 for a, b in zip(values, values[1:])))
        self.assertEqual([0*2**time for time in range(4)], [0, 0, 0, 0])

    def test_square_root_bounds_separate_radicand_from_root(self):
        lesson = topic_lesson(grade8, "g8-real-roots")
        theory = " ".join(lesson["theory"])
        self.assertIn("n²≤a<(n+1)²", theory)
        self.assertIn("n≤√a<n+1", theory)
        checks = {check["prompt"]: check["answer"] for check in lesson["checks"]}
        self.assertEqual(checks["Какова целая часть √0?"], "0")
        self.assertEqual(checks["Какова целая часть √81?"], "9")
        for radicand in (0, 1, 2, 48, 49, 78, 81):
            bound = int(sqrt(radicand))
            self.assertLessEqual(bound**2, radicand)
            self.assertLess(radicand, (bound+1)**2)
            self.assertLessEqual(bound, sqrt(radicand))
            self.assertLess(sqrt(radicand), bound+1)

    def test_mast_height_states_collinearity_and_observation_height(self):
        for i, j in ((0, 0), (5, 6), (9, 9)):
            task = grade8.mast_height(i, j)
            self.assertIn("на одном луче из основания мачты", task["ru"])
            self.assertIn("высота глаза равна нулю", task["ru"])
            answer = task["answer"]
            gap = j+3
            near_tangent = answer/gap
            far_tangent = answer/(gap+gap)
            self.assertAlmostEqual(near_tangent, 2*(i+2)/17)
            self.assertAlmostEqual(far_tangent, (i+2)/17)

    def test_congruence_asks_for_required_third_pair(self):
        for i, j in ((0, 0), (5, 6), (9, 9)):
            task = grade7.congruence_sss(i, j)
            self.assertNotIn("У равного ему", task["ru"])
            self.assertIn("можно доказать по трём сторонам", task["ru"])
            self.assertIn("Для третьего признака требуется BC=QR", task["solution"][1])
        material = topic_lesson(grade7, "g7-congruence")
        checks = " ".join(check["prompt"] for check in material["checks"])
        self.assertIn("Назовите признак", checks)
        self.assertIn("Обоснуйте", checks)

    def test_hints_are_authored_guidance_separate_from_solutions(self):
        checked = 0
        for bank in BANKS:
            for topic, families in bank.FAMILIES.items():
                for family in families:
                    for i in range(10):
                        for j in range(10):
                            exercise = family(i, j)
                            with self.subTest(topic=topic, family=family.__name__, i=i, j=j):
                                hints = exercise["hints"]
                                self.assertEqual(len(hints), 2)
                                self.assertNotEqual(hints[0], hints[1])
                                self.assertTrue(all(hint not in exercise["solution"] for hint in hints))
                                self.assertGreaterEqual(len(exercise["solution"]), 2)
                                self.assertNotIn("Ответ:", hints[1])
                            checked += 1
        self.assertEqual(checked, 19000)

    def test_original_numeric_keys_remain_compatible(self):
        # This digest was computed from the 19,000 answer keys in the audited Windows ZIP.
        records = []
        for bank in BANKS:
            stem = bank.__name__.split(".")[-1]
            for topic, families in sorted(bank.FAMILIES.items()):
                for family_index, family in enumerate(families):
                    for pair in range(100):
                        exercise = family(*divmod(pair, 10))
                        records.append([stem, topic, family_index*100+pair, exercise["answer"]])
        current = hashlib.sha256(json.dumps(records, separators=(",", ":"), ensure_ascii=True).encode()).hexdigest()
        self.assertEqual(current, ORIGINAL_ANSWER_DIGEST)


if __name__ == "__main__":
    unittest.main()
