"""Independent set-parser regressions and prompt-derived content oracles."""

from fractions import Fraction
from math import isqrt
import json
import re
import unittest

from backend.grading import AnswerError
from backend import set_curriculum as content
from backend import solution_sets as sets


def prompt_numbers(task):
    return [Fraction(value) for value in re.findall(r"[+-]?[0-9]+(?:/[0-9]+)?", task["ru"].replace("−", "-"))]


def exact_sqrt(value):
    value = Fraction(value)
    numerator, denominator = isqrt(value.numerator), isqrt(value.denominator)
    if numerator*numerator != value.numerator or denominator*denominator != value.denominator:
        raise AssertionError(f"Unexpected nonrational square root {value}")
    return Fraction(numerator,denominator)


def quadratic_roots(b,c):
    discriminant = b*b-4*c
    if discriminant < 0:
        return ()
    radical = exact_sqrt(discriminant)
    return ((-b-radical)/2,(-b+radical)/2)


def compare(value, sign):
    return {"<":value<0, "≤":value<=0, ">":value>0, "≥":value>=0}[sign]


def reported_member(components, value):
    # Deliberately independent from solution_sets.contains.
    for left,right,include_left,include_right in components:
        if value < left or value > right:
            continue
        if value == left and not include_left or value == right and not include_right:
            continue
        return True
    return False


class SetParserTests(unittest.TestCase):
    def test_root_sets_are_exact_order_independent_and_complete(self):
        response = {"kind":"roots"}
        self.assertTrue(sets.match("2/3; -1; 0,5",response,"1/2;2/3;-1"))
        self.assertTrue(sets.match("{0;2;-2}",response,"-2;0;2"))
        self.assertFalse(sets.match("0;2",response,"-2;0;2"))
        self.assertFalse(sets.match(".3333333333",response,"1/3"))
        for value in ("∅","{}","empty","нет решений"):
            self.assertTrue(sets.match(value,response,"∅"))
        self.assertFalse(sets.match(None,response,"∅"))
        for value in ("1;1", "1;", ";1", "1/0", "1,2,3", "__import__('os')", "{1;2", "1;2}"):
            with self.subTest(value=value), self.assertRaises(AnswerError):
                sets.parse_roots(value)

    def test_interval_unions_normalize_overlap_order_and_closed_contacts(self):
        response = {"kind":"interval_set"}
        cases = (
            ("[0;3] U (2;5)","[0;5)"),
            ("(2;+inf) ∪ (-inf;2]","R"),
            ("[2;4] U [0;2)","[0;4]"),
            ("[2;4) U [2;4]","[2;4]"),
            ("(2;2) U [1;1]","{1}"),
            ("[-1/2;0,5]","[-0.5;1/2]"),
            ("[2;+∞)","[2;inf)"),
            ("{2} U (-inf;2) U (2;+inf)","ℝ"),
            ("∅ U [1;2]","[1;2]"),
            ("(0;1) U (1;2)","(1;2) U (0;1)"),
        )
        for raw,target in cases:
            with self.subTest(raw=raw): self.assertTrue(sets.match(raw,response,target))
        self.assertFalse(sets.match("(0;1) U (1;2)",response,"(0;2)"))
        self.assertFalse(sets.match("[0;1]",response,"(0;1]"))
        self.assertFalse(sets.match("(-inf;2) U (2;+inf)",response,"R"))
        self.assertTrue(sets.match("(1;1)",response,"∅"))

    def test_malformed_bounds_and_excess_input_are_rejected(self):
        for raw in ("[2;1]", "[-inf;2]", "[2;+inf]", "(+inf;+inf)", "(2;-inf)",
                    "(;2)", "[1;2;3]", "[1;2] U", "U [1;2]", "eval(2)", "R+1", "[2**3;9]", "[0;1/0]"):
            with self.subTest(raw=raw),self.assertRaises(AnswerError): sets.parse_intervals(raw)
        with self.assertRaises(AnswerError): sets.parse_roots("1"*513)
        with self.assertRaises(AnswerError): sets.parse_intervals(" U ".join("[0;1]" for _ in range(17)))

    def test_intersection_preserves_singletons_exclusions_and_unbounded_sets(self):
        cases = (("[0;2]","[2;4]","{2}"), ("[0;2]","(2;4)","∅"),
                 ("(-inf;0) U (2;+inf)","[-1;3]","[-1;0) U (2;3]"),
                 ("R","[1/3;2/3)","[1/3;2/3)"))
        for a,b,expected in cases:
            with self.subTest(a=a,b=b):
                actual=sets.intersect(sets.parse_intervals(a),sets.parse_intervals(b))
                self.assertEqual(actual,sets.parse_intervals(expected))
                self.assertEqual(sets.parse_intervals(sets.format_intervals(actual)),actual)


class SetContentTests(unittest.TestCase):
    def test_registry_structure_uniqueness_and_json_serialization(self):
        self.assertEqual(len(content.TOPICS),3)
        total=0
        for topic in content.TOPICS:
            lesson=topic["lesson"]
            self.assertGreaterEqual(len(lesson["theory"]),3)
            self.assertGreaterEqual(len(lesson["examples"]),2)
            self.assertTrue(all(len(example["steps"])>=3 for example in lesson["examples"]))
            self.assertGreaterEqual(len(lesson["mistakes"]),2)
            self.assertGreaterEqual(len(lesson["checks"]),2)
            families=content.FAMILIES[topic["id"]]
            self.assertEqual(len(families),len(content.LEVELS_BY_TOPIC[topic["id"]]))
            seen=set()
            for family in families:
                for i in range(10):
                    for j in range(10):
                        task=family(i,j)
                        json.dumps(task,allow_nan=False)
                        self.assertEqual(task,family(i,j))
                        self.assertNotIn(task["ru"],seen,(family.__name__,i,j))
                        seen.add(task["ru"])
                        self.assertEqual(len(task["hints"]),2)
                        self.assertNotEqual(*task["hints"])
                        self.assertTrue(all(hint not in task["solution"] for hint in task["hints"]))
                        self.assertEqual(set(task["response"]),{"kind"},"Public spec cannot disclose the answer")
                        self.assertTrue(sets.match(task["answer"],task["response"],task["answer"]))
                        total+=1
        self.assertEqual(total,1100)

    def test_all_modulus_roots_from_independent_quadratic_formula(self):
        cardinalities=set()
        for family in (content.modulus_substitution,content.absolute_quadratic,content.two_moduli):
            for i in range(10):
                for j in range(10):
                    task=family(i,j)
                    values=prompt_numbers(task)
                    expected=set()
                    if family is content.modulus_substitution:
                        h,b,repeated_h,c=values[:-1]
                        self.assertEqual(h,repeated_h)
                        for t in quadratic_roots(b,c):
                            if t>=0: expected.update((h-t,h+t))
                        predicate=lambda x:(x-h)**2+b*abs(x-h)+c==0
                    elif family is content.absolute_quadratic:
                        h,inside,outside=values
                        if outside>=0:
                            for squared in (inside+outside,inside-outside):
                                if squared>=0:
                                    t=exact_sqrt(squared)
                                    expected.update((h-t,h+t))
                        predicate=lambda x:abs((x-h)**2-inside)==outside
                    else:
                        negative_square,b=values
                        square=-negative_square
                        for coefficient in (-b,b):
                            for t in quadratic_roots(coefficient,-square):
                                if t>=0: expected.update((-t,t))
                        predicate=lambda x:abs(x*x-square)==b*abs(x)
                    supplied=sets.parse_roots(task["answer"])
                    self.assertEqual(set(supplied),expected,(family.__name__,i,j))
                    self.assertTrue(all(predicate(root) for root in supplied))
                    cardinalities.add(len(supplied))
        self.assertEqual(cardinalities,{0,1,2,3,4})

    def test_all_inequality_sets_against_prompt_arithmetic(self):
        observed_shapes=set()
        families=(content.quadratic_distinct,content.quadratic_double,content.quadratic_no_roots,
                  content.rational_linear,content.rational_three_critical,content.mixed_system,
                  content.quadratic_system,content.quadratic_union)
        for family in families:
            for i in range(10):
                for j in range(10):
                    task=family(i,j)
                    values=prompt_numbers(task)
                    signs=re.findall(r"[<>≤≥]",task["ru"])
                    if family is content.quadratic_distinct:
                        coefficient,a,b=values[:-1]
                        predicate=lambda x:compare(coefficient*(x-a)*(x-b),signs[0])
                    elif family is content.quadratic_double:
                        coefficient,h=values[:-1]
                        predicate=lambda x:compare(coefficient*(x-h)**2,signs[0])
                    elif family is content.quadratic_no_roots:
                        coefficient,h,k=values[:-1]
                        predicate=lambda x:compare(coefficient*((x-h)**2+k),signs[0])
                    elif family is content.rational_linear:
                        coefficient,a,b=values[:-1]
                        predicate=lambda x:x!=b and compare(coefficient*(x-a)/(x-b),signs[0])
                    elif family is content.rational_three_critical:
                        coefficient,a,b,c=values[:-1]
                        predicate=lambda x:x!=c and compare(coefficient*(x-a)*(x-b)/(x-c),signs[0])
                    elif family is content.mixed_system:
                        a,b,zero,c=values
                        self.assertEqual(zero,0)
                        predicate=lambda x:compare((x-a)*(x-b),signs[0]) and compare(x-c,signs[1])
                    else:
                        a,b,zero,c,d,other_zero=values
                        self.assertEqual((zero,other_zero),(0,0))
                        if family is content.quadratic_system:
                            predicate=lambda x:compare((x-a)*(x-b),signs[0]) and compare((x-c)*(x-d),signs[1])
                        else:
                            predicate=lambda x:compare((x-a)*(x-b),signs[0]) or compare((x-c)*(x-d),signs[1])
                    actual=sets.parse_intervals(task["answer"])
                    observed_shapes.add(len(actual))
                    boundaries=sorted(set(values))
                    samples=set(boundaries)
                    samples.update((x+y)/2 for x,y in zip(boundaries,boundaries[1:]))
                    samples.update(x+delta for x in boundaries for delta in (Fraction(-1,2),Fraction(1,2)))
                    samples.update((boundaries[0]-2,boundaries[-1]+2))
                    for x in samples:
                        self.assertEqual(reported_member(actual,x),predicate(x),(family.__name__,i,j,x,task["answer"]))
        self.assertTrue({0,1,2,3}.issubset(observed_shapes))


if __name__=="__main__":
    unittest.main()
