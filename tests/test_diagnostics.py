"""Feedback is grounded in actual answer differences, never inferred thoughts."""

import copy
from fractions import Fraction
import json
import unittest

from backend.curriculum import EXTRA_FIRST_SEED, EXTRA_LAST_SEED, generate
from backend.diagnostics import explain, graph_description


def graph(model, target):
    return {"response":{"kind":"graph","model":model},"answer":json.dumps(target)}


def wrong(value):
    return {"correct":False,"submitted":value,"timedOut":False}


class DiagnosticTests(unittest.TestCase):
    def test_graph_descriptions_are_readable_formulas_and_keep_exact_fractions(self):
        line = {"kind":"graph","model":"line"}
        parabola = {"kind":"graph","model":"parabola"}
        self.assertEqual(graph_description('{"m":2,"b":-3}', line), "y = 2·x − 3")
        self.assertEqual(graph_description('{"m":-1,"b":0}', line), "y = −x")
        self.assertEqual(graph_description('{"m":0,"b":0.5}', line), "y = 1/2")
        self.assertEqual(graph_description('{"a":-2,"h":3,"k":4}', parabola), "y = −2·(x − 3)² + 4")
        self.assertEqual(graph_description('{"a":1,"h":-3,"k":0}', parabola), "y = (x + 3)²")
        self.assertEqual(graph_description('{"a":1,"h":0,"k":-4}', parabola), "y = x² − 4")
        self.assertEqual(graph_description('{"a":0,"h":3,"k":4}', parabola), "y = 4")

    def test_graph_line_feedback_distinguishes_slope_and_intercept(self):
        question = graph("line", {"m":2,"b":3})
        self.assertIn("знак наклона", explain(question, wrong('{"m":-2,"b":3}')))
        self.assertIn("изменение y", explain(question, wrong('{"m":4,"b":3}')))
        self.assertIn("при x=0", explain(question, wrong('{"m":2,"b":-3}')))
        self.assertIsNone(explain(question, wrong('{"m":-2,"b":-3}')))
        self.assertIsNone(explain(question, wrong('{"b":3,"m":2.0}')))

    def test_parabola_feedback_separates_shift_direction_and_stretch(self):
        question = graph("parabola", {"a":2,"h":3,"k":4})
        self.assertIn("противоположный знак", explain(question, wrong('{"a":2,"h":-3,"k":4}')))
        self.assertIn("ось симметрии", explain(question, wrong('{"a":2,"h":1,"k":4}')))
        self.assertIn("ординату вершины", explain(question, wrong('{"a":2,"h":3,"k":-4}')))
        self.assertIn("направление ветвей противоположное", explain(question, wrong('{"a":-2,"h":3,"k":4}')))
        self.assertIn("растяжение", explain(question, wrong('{"a":4,"h":3,"k":4}')))
        self.assertIn("постоянная функция", explain(question, wrong('{"a":0,"h":3,"k":4}')))
        self.assertIsNone(explain(question, wrong('{"a":-2,"h":-3,"k":4}')))

    def test_roots_are_compared_as_sets_and_incomplete_answers_are_identified(self):
        question = {"response":{"kind":"roots"},"answer":"{-2;2}"}
        self.assertIn("множество решений неполное", explain(question, wrong("-2")))
        self.assertIn("лишние значения", explain(question, wrong("-2;0;2")))
        self.assertIn("пропущены", explain(question, wrong("0;2")))
        self.assertIsNone(explain(question, wrong("2;-2")))
        self.assertIn("неполное", explain(question, wrong("∅")))
        empty = {"response":{"kind":"roots"},"answer":"∅"}
        self.assertIn("лишние значения", explain(empty, wrong("1")))
        self.assertIsNone(explain(empty, wrong("нет решений")))

    def test_intervals_distinguish_endpoint_inclusion_and_denominator_restrictions(self):
        question = {"response":{"kind":"interval_set"},"answer":"(0;2)","family":"quadratic_distinct"}
        feedback = explain(question, wrong("[0;2)"))
        self.assertIn("Границы промежутков найдены верно", feedback)
        self.assertIn("скобки", feedback)
        self.assertNotIn("знаменатель", feedback)
        question["family"] = "rational_linear"
        self.assertIn("знаменатель", explain(question, wrong("[0;2)")))
        self.assertIsNone(explain(question, wrong("(0;1] U (1;2)")))
        self.assertIn("на каждом промежутке", explain(question, wrong("(2;4)")))

    def test_linear_missing_division_and_opposite_operation_are_verified_patterns(self):
        question = generate("linear", 56)
        self.assertEqual(question["answer"], 1)
        self.assertIn("раздели обе части на 7", explain(question, wrong("7")))
        self.assertIn("при прибавлении 8", explain(question, wrong("23/7")))
        self.assertIsNone(explain(question, wrong("18")))
        self.assertIsNone(explain(question, wrong("1")))
        self.assertIn("осталось вычесть 8", explain(generate("linear",156), wrong("11")))

    def test_linear_patterns_work_on_full_standard_grid_and_extended_seed_range(self):
        for seed in range(100):
            question = generate("linear", seed)
            i,j = divmod(seed,10)
            a,b,x = i+2,i+3,j-5
            for raw in (str(a*x), str(Fraction(a*x+2*b,a))):
                result = explain(question, wrong(raw))
                self.assertEqual(result is None, Fraction(raw) == x)
        for seed in (EXTRA_FIRST_SEED,EXTRA_FIRST_SEED+1234,EXTRA_LAST_SEED):
            question = generate("linear", seed)
            offset,j = divmod(seed-EXTRA_FIRST_SEED,1000)
            a,x = offset+12,j-5
            self.assertIn("раздели обе части", explain(question, wrong(str(a*x))))
        question = generate("linear",56)
        question["seed"] = 99
        self.assertIsNone(explain(question, wrong("7")), "Stale metadata must not invent an explanation")

    def test_no_diagnostics_for_correct_unknown_unanswered_or_timed_out_attempts(self):
        question = graph("line", {"m":2,"b":3})
        submission = '{"m":-2,"b":3}'
        for outcome in ({"correct":True,"submitted":submission}, {"submitted":submission},
                        {"correct":False,"submitted":submission,"timedOut":True},
                        {"correct":False,"submitted":submission,"unanswered":True},
                        {"correct":False,"submitted":None}, {"correct":False,"submitted":""}):
            self.assertIsNone(explain(question,outcome))

    def test_malformed_legacy_inputs_are_ignored_and_never_executed(self):
        for model in ("line","parabola"):
            response = {"kind":"graph","model":model}
            for raw in (None, {}, "__import__('os').system('bad')", "[]", "{}", '{"m":NaN,"b":3}',
                        '{"m":true,"b":3}', '{"m":2,"b":3,"extra":4}'):
                self.assertIsNone(graph_description(raw,response))
                self.assertIsNone(explain({"response":response,"answer":"{}"},wrong(raw)))
        for kind,raw in (("roots","1;1"),("roots","oops"),("interval_set","[0;+inf]"),
                         ("interval_set","oops")):
            self.assertIsNone(explain({"response":{"kind":kind},"answer":"∅"},wrong(raw)))
        self.assertIsNone(graph_description('{"m":1,"b":2}', {"model":[]}))
        constant = graph("parabola", {"a":0,"h":0,"k":2})
        self.assertIsNone(explain(constant, wrong('{"a":1,"h":0,"k":2}')))

    def test_feedback_helpers_preserve_question_and_original_numeric_key(self):
        question = generate("linear",56)
        outcome = wrong("7")
        before = copy.deepcopy((question,outcome))
        self.assertTrue(explain(question,outcome))
        self.assertEqual((question,outcome),before)
        self.assertEqual(generate("linear",56)["answer"],1)


if __name__ == "__main__":
    unittest.main()
