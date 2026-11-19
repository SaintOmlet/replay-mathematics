import re
import unittest
from decimal import Decimal
from fractions import Fraction
from math import gcd, isclose

from backend.grade7 import FAMILIES, LEGACY_LESSONS, TOPICS


def only(values):
    (answer,) = tuple(values)
    return answer


def linear_coefficient(polynomial):
    """Exact coefficient of x for degree ≤2, from two evaluations."""
    return Fraction(polynomial(1) - polynomial(-1), 2)


def cubic_linear_coefficient(polynomial):
    """Isolate the x term by cancelling x³ from the two odd parts."""
    return Fraction(8 * (polynomial(1) - polynomial(-1))
                    - (polynomial(2) - polynomial(-2)), 12)


def triangle_sides(a, b, c):
    assert min(a, b, c) > 0
    ordered = sorted((a, b, c))
    return ordered[0] + ordered[1] > ordered[2]


def angle_set(*angles):
    assert sum(angles) == 180
    assert all(0 < angle < 180 for angle in angles)
    return angles


def solution_candidates(line):
    clean = line.replace("−", "-").replace(",", ".")
    tokens = re.findall(r"-?[0-9]+(?:\.[0-9]+)?(?:/[0-9]+)?", clean)
    return [Fraction(token) for token in tokens if not token.endswith("/0")]


def reference(name, i, j):
    """By enumeration, substitution, exact arithmetic, or identities independent of grading."""
    if name == "integer_power_product":
        target = 3 ** (i + 1) * 3 ** (j + 2)
        return only(n for n in range(22) if 3**n == target)
    if name == "integer_power_quotient":
        target = Fraction((5 ** (i + 2)) ** 2, 5 ** (j + 4))
        return only(n for n in range(-20, 24) if Fraction(5)**n == target)
    if name == "integer_power_inverse":
        a, b = i + 2, 3 * (j - 5) - (i + 2)
        return only(n for n in range(-10, 11) if (Fraction(2)**n)**3 / 2**a == Fraction(2)**b)
    if name == "scientific_read":
        return Decimal((11 + i) * 10**(j + 1)).adjusted()
    if name == "scientific_product":
        a = Decimal(15 + i) / 10
        return ((a.scaleb(j + 1)) * Decimal(7000)).adjusted()
    if name == "scientific_quotient":
        a = (Decimal(13 + i) / 10).scaleb(j + 3)
        return (a / Decimal(29)).adjusted()
    if name == "monomial_degree":
        value = 7 * (2 ** (i + 1)) * (2 ** (j + 1))
        return only(n for n in range(25) if 7 * 2**n == value)
    if name == "monomial_coefficient":
        return (-i - 2) * (j + 2)  # Evaluate at x=y=1.
    if name == "monomial_unknown":
        target_degree = 2 * (i + 2) + 2 * (j + 3) + 3
        return only(n for n in range(15)
                    if (2**n * 2**(j + 3))**2 * 8 == 2**target_degree)
    if name == "polynomial_add":
        polynomial = lambda x: ((i + 2)*x*x - 2*x + 3) + ((j + 2)*x*x + 5*x - 7)
        return Fraction(polynomial(1) + polynomial(-1) - 2*polynomial(0), 2)
    if name == "polynomial_subtract":
        return linear_coefficient(lambda x: (x*x+(i+2)*x-1) - (3*x*x-(j+2)*x+4))
    if name == "polynomial_unknown":
        return only(k for k in range(-20, 20)
                    if linear_coefficient(lambda x: (x+i+2)*(x-j-2)+k*x) == 3)
    if name == "identity_square":
        return linear_coefficient(lambda x: ((i+2)*x-(j+2))**2)
    if name == "identity_difference":
        return (12+i+j)**2 - (10+i-j)**2
    if name == "identity_cube":
        return cubic_linear_coefficient(lambda x: ((i+2)*x+(j+1))**3 + ((i+2)*x-(j+1))**3)
    if name == "factor_gcd":
        return gcd((i+2)*(j+2), (i+2)*(j+3))
    if name == "factor_group":
        a, b = i+2, j+2
        roots = [x for x in range(-15, 0) if x*(x+a)+b*(x+a)==0]
        return 2*roots[0] if len(roots)==1 else sum(roots)
    if name == "factor_reveal":
        a, b = i+3, j+1
        polynomial = lambda x: x**3-a*x*x-b*x+a*b
        return Fraction(polynomial(0), -a)
    if name == "rational_hole":
        return only(x for x in range(15) if x-i-2==0)
    if name == "rational_cancel":
        x, a = i+j+3, i+2
        assert x != a
        return Fraction(x*x-a*a, x-a)
    if name == "rational_sum":
        a, x = i+2, j+2
        assert x not in (0, -1)
        return Fraction(a,x*(x+1)) + Fraction(a,x+1)
    if name == "basic_curve_square":
        return (i+1)*pow(-j-1, 2)
    if name == "basic_curve_cubic":
        x, y = -j-1, -(i+1)*(j+1)**3
        return Fraction(y,x*x*x)
    if name == "basic_curve_hyperbola":
        k = (i+2)*(j+2)
        return only(Fraction(n,2) for n in range(-125,0)
                    if Fraction(k,1)/Fraction(n,2)==-2)
    if name == "frequency_relative":
        labels = ["A"]*(i+1) + ["B"]*(j+11-i-1)
        return Fraction(labels.count("A"), len(labels))
    if name == "frequency_missing":
        a, b = i+2, j+2
        return len(set(range(4*a+b))-set(range(a+b)))
    if name == "frequency_merge":
        first = [True, False]*(i+1)
        second = [True, True, True, False]*(j+1)
        all_observations = first+second
        return Fraction(sum(all_observations),len(all_observations))
    if name == "inequality_boundary":
        return max(x for x in range(-50,50) if x+i+2 < i+j+5)
    if name == "inequality_negative":
        return min(x for x in range(-50,50) if (-i-2)*x < (-i-2)*(j+2))
    if name == "inequality_budget":
        price = i+4
        cash = price*(j+3)+(price-1)//2+12
        return max(n for n in range(30) if sum([price]*n)+12 <= cash)
    if name == "adjacent_angles":
        a, b = i+2, (i+2)*(j+1)+1
        alpha, beta = Fraction(180,1+Fraction(b,a)), Fraction(180,1+Fraction(a,b))
        angle_set(alpha,beta)
        assert gcd(a,b)==1
        return alpha
    if name == "vertical_equation":
        a, a2 = i+12, i+j+15
        answer = only(x for x in range(60) if 2*x+a==x+a2)
        assert 0 < 2*answer+a < 180
        return answer
    if name == "bisector_angle":
        a, total = i+2, 2*(i+j+4)
        assert 0 < a < total < 180
        midpoint = Fraction(total,2)
        return abs(midpoint-a)
    if name == "parallel_same_side":
        b, c = j+12, 180-2*(i+10)-(j+12)
        answer = only(x for x in range(60) if (x+b)+(x+c)==180)
        angle_set(answer+b,answer+c)
        return answer
    if name == "parallel_alternate":
        b, c = j+7, j+7+2*(i+9)
        actual = only(x+c for x in range(60) if 3*x+b==x+c)
        assert 0 < actual < 180
        return actual
    if name == "parallel_parameter":
        first, supplement_const = i+64, j+53
        answer = only(x for x in range(-60,180) if 180-(x+supplement_const)==first)
        angle_set(first,answer+supplement_const)
        return answer
    if name == "triangle_angle_missing":
        return angle_set(i+32,j+47,180-(i+32)-(j+47))[-1]
    if name == "triangle_angle_external":
        a, ext = i+32, i+j+70
        interior = 180-ext
        return only(b for b in range(1,180) if a+b+interior==180)
    if name == "triangle_angle_ratio":
        a, b = i+2,j+2
        c = 180 / Fraction(a+b+1)
        angles = angle_set(a*c,b*c,c)
        return sum(angles[:2])
    if name == "congruence_sas":
        length_a, length_b = i+4,i+j+7
        assert triangle_sides(length_b,length_b,length_b)
        return only(x for x in range(30) if x+length_a==length_b)
    if name == "congruence_asa":
        return only(c for c in range(1,180) if sum((i+35,j+40,c))==180)
    if name == "congruence_sss":
        b, perimeter = j+11, 20+(j+11)+(2*(i+5)+1)
        answer = only(x for x in range(30) if 20+b+2*x+1==perimeter)
        assert triangle_sides(20,b,2*answer+1)
        return answer
    if name == "isosceles_base_angle":
        a = 10*(i+1)+j
        return only(Fraction(k,2) for k in range(1,179) if a+k==180)
    if name == "isosceles_perimeter":
        base, p = j+4, 2*(i+9)+(j+4)
        return only(s for s in range(1,30) if 2*s+base==p and triangle_sides(s,s,base))
    if name == "isosceles_median":
        base, height = 2*(i+4),j+5
        return Fraction(abs(base*height-0*0),2)  # Determinant with vertices (0,0), (base,0), (base/2,height).
    if name in {"triangle_inequality_largest","triangle_inequality_count"}:
        a, b = i+3,i+j+4
        candidates = [x for x in range(1,a+b+1) if triangle_sides(a,b,x)]
        return max(candidates) if name.endswith("largest") else len(candidates)
    if name == "triangle_inequality_perimeter":
        a, b = i+4,j+7
        limit=2*(a+b)-2
        return max(x for x in range(1,a+b+2) if a+b+x<=limit and triangle_sides(a,b,x))
    if name == "circle_tangent_lengths":
        a, total = i+3,i+j+7
        return only(x for x in range(1,40) if x+a==total)
    if name == "circle_two_circles":
        a, b = i+3,j+4
        # Centers lie on opposite sides of the tangency point at coordinate zero.
        return abs(-a-b)
    if name == "circle_angle":
        central = 3*(i+6)+(j+6)
        assert 0 < central < 180
        return only(angle for angle in range(1,180) if sum((90,90,central,angle))==360)
    raise AssertionError(f"Missing oracle for {name}")


class Grade7Tests(unittest.TestCase):
    def test_all_grade7_variants_have_valid_answers_and_explanations(self):
        prompts=set()
        for topic, families in FAMILIES.items():
            self.assertEqual(len(families),3)
            for family in families:
                for i in range(10):
                    for j in range(10):
                        with self.subTest(topic=topic,family=family.__name__,i=i,j=j):
                            item=family(i,j)
                            expected=reference(family.__name__,i,j)
                            self.assertTrue(isclose(item["answer"],expected,rel_tol=1e-12,abs_tol=1e-12))
                            self.assertIn(Fraction(expected),solution_candidates(item["solution"][-1]))
                            self.assertEqual(item,family(i,j))
                            self.assertNotIn(item["ru"],prompts)
                            self.assertGreaterEqual(len(item["solution"]),2)
                            self.assertEqual(len(item["hints"]),2)
                            if family.__name__=="basic_curve_square":
                                graph=item["graph"]
                                x=-j-1
                                self.assertEqual(graph["a"]*x*x+graph["b"]*x+graph["c"],item["answer"])
                            prompts.add(item["ru"])
        self.assertEqual(len(prompts),5100)

    def test_all_grade7_topics_have_structured_lessons(self):
        self.assertEqual(len(TOPICS)+len(LEGACY_LESSONS),20)
        self.assertEqual({topic["id"] for topic in TOPICS},set(FAMILIES))
        for entry in [*TOPICS,*LEGACY_LESSONS.values()]:
            with self.subTest(topic=entry.get("id"), section=entry["section"]):
                parts=entry["lesson"]
                self.assertTrue(parts["intro"])
                self.assertGreaterEqual(len(parts["theory"]),3)
                self.assertGreaterEqual(len(parts["mistakes"]),2)
                self.assertGreaterEqual(len(parts["examples"]),2)
                self.assertTrue(all(len(example["steps"])>=2 for example in parts["examples"]))
                self.assertGreaterEqual(len(parts["checks"]),2)
