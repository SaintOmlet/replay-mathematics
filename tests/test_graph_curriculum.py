"""Independent mathematical and input checks for graded graph exercises."""

from fractions import Fraction
import json
import math
import re
import unittest

from backend import graph_curriculum as bank
from backend.graph_answers import describe, matches, parameters
from backend.grading import AnswerError


def curve(model, values, x):
    if model == "line":
        return values["m"]*x+values["b"]
    return values["a"]*(x-values["h"])**2+values["k"]


def every(family):
    for i in range(10):
        for j in range(10):
            yield i, j, family(i,j)


class GraphCurriculumTests(unittest.TestCase):
    def test_all_900_variants_are_distinct_deterministic_and_answerable(self):
        total = 0
        for topic in bank.TOPICS:
            body = topic["lesson"]
            self.assertGreaterEqual(len(body["theory"]),4)
            self.assertGreaterEqual(len(body["examples"]),2)
            self.assertTrue(all(len(example["steps"]) >= 3 for example in body["examples"]))
            self.assertGreaterEqual(len(body["mistakes"]),2)
            self.assertGreaterEqual(len(body["checks"]),2)
            prompts = set()
            self.assertEqual(len(bank.FAMILIES[topic["id"]]),len(bank.LEVELS_BY_TOPIC[topic["id"]]))
            for family in bank.FAMILIES[topic["id"]]:
                for i,j,task in every(family):
                    self.assertEqual(task,family(i,j))
                    self.assertNotIn(task["ru"],prompts,(family.__name__,i,j))
                    prompts.add(task["ru"])
                    json.dumps(task,allow_nan=False)
                    self.assertTrue(matches(task["answer"],task["response"],task["answer"]))
                    initial=bank.key({p["key"]:p["initial"] for p in task["response"]["parameters"]})
                    self.assertFalse(matches(initial,task["response"],task["answer"]),family.__name__)
                    self.assertEqual(len(task["hints"]),2)
                    self.assertTrue(all(hint not in task["solution"] for hint in task["hints"]))
                    for diagnostic in task["diagnostics"]:
                        self.assertFalse(matches(diagnostic["answer"],task["response"],task["answer"]))
                    self.assertNotIn("answer",task["response"])
                    total += 1
            self.assertEqual(len(prompts),300)
        self.assertEqual(total,900)

    def test_line_formula_and_two_point_conditions(self):
        for _,_,task in every(bank.line_coefficients):
            m,b=map(int,re.search(r"y=\((-?\d+)\)x\+\((-?\d+)\)",task["ru"]).groups())
            values=parameters(task["answer"],task["response"])
            self.assertEqual((values["m"],values["b"]),(m,b))
            self.assertEqual(curve("line",values,0),b)
            self.assertEqual(curve("line",values,1)-curve("line",values,0),m)
        for _,_,task in every(bank.line_two_points):
            y1,y2=map(Fraction,re.search(r"A\(−2;(-?[\d.]+)\) и B\(2;(-?[\d.]+)\)",task["ru"]).groups())
            values=parameters(task["answer"],task["response"])
            self.assertEqual(curve("line",values,-2),y1)
            self.assertEqual(curve("line",values,2),y2)
            self.assertEqual(values["m"],(y2-y1)/4)

    def test_parallel_line_is_distinct_and_passes_given_point(self):
        for _,_,task in every(bank.parallel_through_point):
            y,m,reference_b=map(int,re.search(r"A\(2;(-?\d+)\).*y=\((-?\d+)\)x\+\((-?\d+)\)",task["ru"]).groups())
            values=parameters(task["answer"],task["response"])
            self.assertEqual(values["m"],m)
            self.assertNotEqual(values["b"],reference_b)
            self.assertEqual(curve("line",values,2),y)
            self.assertEqual(task["response"]["reference"]["parameters"],{"m":m,"b":reference_b})

    def test_parabola_vertex_and_point_both_hold(self):
        for family in (bank.parabola_vertex,bank.parabola_through_point):
            for _,_,task in every(family):
                h,k=map(int,re.search(r"V\((-?\d+);(-?\d+)\)",task["ru"]).groups())
                values=parameters(task["answer"],task["response"])
                self.assertEqual((values["h"],values["k"]),(h,k))
                self.assertEqual(curve("parabola",values,h),k)
                self.assertEqual(curve("parabola",values,h+1),curve("parabola",values,h-1))
                if family is bank.parabola_vertex:
                    self.assertEqual(abs(values["a"]),1)
                    self.assertEqual(values["a"]>0,"ветвями вверх" in task["ru"])
                else:
                    x,y=map(int,re.search(r"P\((-?\d+);(-?\d+)\)",task["ru"]).groups())
                    self.assertNotEqual(x,h)
                    self.assertEqual(curve("parabola",values,x),y)
                    self.assertEqual(values["a"],Fraction(y-k,(x-h)**2))

    def test_parabola_transformation_applies_signed_translations_last(self):
        for _,_,task in every(bank.parabola_transformation):
            direction_x,x,direction_y,y=re.search(r"(вправо|влево) на (\d+) и (вверх|вниз) на (\d+)",task["ru"]).groups()
            h=int(x)*(1 if direction_x=="вправо" else -1)
            k=int(y)*(1 if direction_y=="вверх" else -1)
            a=-2 if "отразили" in task["ru"] else 2
            values=parameters(task["answer"],task["response"])
            for source_x in (-2,-1,0,1,2):
                self.assertEqual(curve("parabola",values,source_x+h),a*source_x**2+k)

    def test_reference_recovery_matches_whole_function(self):
        for family in (bank.recover_line,bank.recover_parabola):
            for _,_,task in every(family):
                spec=task["response"]
                values=parameters(task["answer"],spec)
                reference=spec["reference"]
                for x in (Fraction(-7,2),-1,0,Fraction(3,2),5):
                    self.assertEqual(curve(spec["model"],values,x),curve(reference["model"],reference["parameters"],x))
                for point in spec["points"]:
                    self.assertEqual(curve(spec["model"],values,Fraction(str(point["x"]))),Fraction(str(point["y"])))

    def test_horizontal_line_has_one_intersection_and_neighbors_have_zero_or_two(self):
        for _,_,task in every(bank.line_single_intersection):
            spec=task["response"]
            values=parameters(task["answer"],spec)
            reference=spec["reference"]["parameters"]
            self.assertEqual(values["m"],0)
            self.assertEqual(values["b"],reference["k"])
            # a(x-h)^2 + k = b has one root iff b=k (a is nonzero).
            self.assertEqual((values["b"]-reference["k"])/reference["a"],0)
            for offset in (-1,1):
                square=Fraction(values["b"]+offset-reference["k"],reference["a"])
                self.assertNotEqual(square,0)
                self.assertEqual(2 if square>0 else 0,2 if offset*reference["a"]>0 else 0)

    def test_input_errors_are_bounded_and_cannot_receive_credit(self):
        task=bank.line_two_points(7,3)
        spec=task["response"]
        for raw in ("no", "[]", "null", '{"m":true,"b":0}', '{"m":"1","b":0}',
                    '{"m":NaN,"b":0}', '{"m":Infinity,"b":0}', '{"m":1e309,"b":0}',
                    '{"m":1,"b":0,"extra":1}', '{"m":1}', '{"m":1,"m":2,"b":0}',
                    '{"m":6.5,"b":0}', '{"m":0.1,"b":0}', '{"m":'+"9"*400+',"b":0}'):
            with self.subTest(raw=raw[:40]),self.assertRaises(AnswerError):
                matches(raw,spec,task["answer"])
        self.assertFalse(matches(None,spec,task["answer"]))
        self.assertFalse(matches('{"b":-1,"m":-1}',spec,task["answer"]))
        self.assertTrue(matches('{"b":-1.0,"m":1}',spec,task["answer"]))
        parabola=bank.parabola_vertex(2,2)
        with self.assertRaises(AnswerError):
            matches('{"a":0,"h":-3,"k":-2}',parabola["response"],parabola["answer"])

    def test_answer_description_is_a_formula(self):
        for family in (bank.line_two_points,bank.parabola_through_point):
            task=family(1,2)
            text=describe(task["answer"],task["response"])
            self.assertTrue(text.startswith("y = "))
            self.assertNotIn('"',text)
            self.assertNotIn("{",text)


if __name__=="__main__":
    unittest.main()
