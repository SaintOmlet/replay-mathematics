import unittest
from fractions import Fraction

from backend.expressions import Expression, matches
from backend.grading import AnswerError


class Expressions(unittest.TestCase):
    def test_exact_equivalence_and_implicit_products(self):
        spec={"variables":["x","y"]}
        for answer,target in (("2x+3x","5*x"),("(x+y)^2","x^2+2xy+y^2"),
                              ("(x^2-1)/(x+1)","x-1"),("x^-2","1/x^2"),
                              ("0,5x","x/2"),("-x^2","-(x*x)")):
            self.assertTrue(matches(answer,spec,target),(answer,target))
        self.assertFalse(matches("x^2+y^2",spec,"(x+y)^2"))
        self.assertFalse(matches("x+1",spec,"x-1"))

    def test_expanded_requires_collected_whole_polynomial(self):
        spec={"variables":["x"],"form":"expanded"}
        self.assertTrue(matches("x²+3x+2",spec,"(x+1)(x+2)"))
        self.assertTrue(matches("2+3x+x^2",spec,"x^2+3x+2"))
        for answer in ("(x+1)(x+2)","x^2+x+2x+2","x^2+3x+2*1"):
            self.assertFalse(matches(answer,spec,"x^2+3x+2"),answer)

    def test_factorisation_checks_factors_beyond_value(self):
        spec={"variables":["x"],"form":"factored"}
        self.assertTrue(matches("(x+1)(x-1)",spec,"(x-1)*(x+1)"))
        self.assertTrue(matches("-(1-x)*(x+1)",spec,"(x-1)*(x+1)"))
        self.assertTrue(matches("(2x+2)*x",spec,"2*x*(x+1)"))
        self.assertTrue(matches("(x+1)^2",spec,"(x+1)*(x+1)"))
        self.assertFalse(matches("x^2-1",spec,"(x-1)*(x+1)"))
        self.assertFalse(matches("1*(x^2-1)",spec,"(x-1)*(x+1)"))

    def test_monomial_requires_combining_powers_and_coefficients(self):
        spec={"variables":["x","y"],"form":"monomial"}
        self.assertTrue(matches("6x^3y",spec,"2x*x^2*3y"))
        for answer in ("2*3*x^3*y","6*x*x^2*y","3x^3y+3x^3y"):
            self.assertFalse(matches(answer,spec,"6*x^3*y"),answer)
        self.assertTrue(matches("x^-2",spec,"1/x^2"))

    def test_precedence_and_constant_oracle(self):
        for a in range(-4,5):
            for b in range(1,7):
                result=Expression(f"({a}+{b})^2-({a}-{b})^2",["x"]).value
                self.assertEqual(result[0],{} if not a else {(0,):Fraction(4*a*b)})
        self.assertTrue(matches("-2^2",{"variables":["x"]},"-4"))
        self.assertTrue(matches("(-2)^2",{"variables":["x"]},"4"))

    def test_invalid_or_excessive_input_is_rejected_without_running_code(self):
        for raw in ("__import__('os')","x+","1/(x-x)","0^0","x^y","x^1.5", "x^1000000",
                    "9"*100,"("*40+"x"+")"*40,"open(x)","sqrt(x)","x;1"):
            with self.subTest(raw=raw),self.assertRaises(AnswerError):
                Expression(raw,["x","y"])
