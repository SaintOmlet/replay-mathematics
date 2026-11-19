"""Check the original 4,000 answers using values read from exercise statements."""

import math
import re
import unittest
from fractions import Fraction
from itertools import permutations, product
from statistics import mean, median

from backend.content import FAMILIES, TOPICS, generate


def numbers(statement):
    """Extract signed integers written in the original exercise prompts."""
    return tuple(int(token.replace("−", "-").replace(" ", ""))
                 for token in re.findall(r"(?:[−-] *)?[0-9]+", statement))


def linear_solution(a, b, c, d):
    """Solve ax + b = cx + d; evaluate the equation again at the root."""
    assert a != c
    root = Fraction(d - b, a - c)
    assert a * root + b == c * root + d
    return root


def solve_system(a, b, c, d, u, v):
    """Return the solution of ax + by = u, cx + dy = v."""
    determinant = a*d - b*c
    assert determinant
    x, y = Fraction(u*d - b*v, determinant), Fraction(a*v - c*u, determinant)
    assert a*x + b*y == u
    assert c*x + d*y == v
    return x, y


def solve_prices(two_pens_one_notebook, one_pen_two_notebooks):
    pen, notebook = solve_system(2, 1, 1, 2, two_pens_one_notebook, one_pen_two_notebooks)
    assert pen > 0 and notebook > 0
    return notebook


def solve_dependent(m, rhs, pm, p):
    """Evaluate the second row at two distinct solutions of the first row."""
    assert p
    y_intercept = rhs
    x_intercept = Fraction(rhs, m)
    assert pm * x_intercept == p * y_intercept
    return pm * x_intercept


def distance(a, b):
    assert min(a, b) > 0
    c = math.hypot(a, b)
    assert c > max(a, b)
    return c


def rectangle_long_side(perimeter, area):
    assert perimeter % 2 == 0 and area > 0
    semiperimeter = perimeter // 2
    choices = [x for x in range(1, semiperimeter) if x * (semiperimeter - x) == area]
    assert len(choices) == 2 and choices[0] != choices[1]
    return max(choices)


def exact_log(power, base):
    assert base >= 2 and power >= 1
    exponent = 0
    while power > 1:
        power, remainder = divmod(power, base)
        assert remainder == 0
        exponent += 1
    return exponent


def integer_power(base, exponent):
    assert exponent >= 0
    return math.prod([base] * exponent)


def perfect_root(square):
    root = math.isqrt(square)
    assert root * root == square
    return root


def find_larger_root(a, b, constant):
    assert constant == 0
    # The prompt parser reads signed constants in the two monic factors.
    roots = [x for x in range(-50, 51) if (x + a) * (x + b) == constant]
    assert len(roots) == 2
    return max(roots)


def parabola_minimum(linear_coefficient, constant):
    points = [(x*x + linear_coefficient*x + constant, x) for x in range(-50, 51)]
    simplest = sorted(points)
    assert simplest[0][0] < simplest[1][0]
    return simplest[0]


def tangent_height(shift, vertex_height):
    # Test the number of solutions on both sides of the minimum. These
    # sampled points are enough since the expression has positive square term.
    points = [(x + shift)**2 + vertex_height for x in range(-50, 51)]
    level = min(points)
    assert points.count(level) == 1 and points.count(level + 1) == 2
    return level


def weighted_mean(a, b):
    return mean([a, a, b, b, b])


def probability_by_counting(b, w, draw_count, *, replacement, favorable):
    assert b > 0 and w > 0
    balls = range(b + w)
    outcomes = (product(balls, repeat=draw_count) if replacement
                else permutations(balls, draw_count))
    count = matches = 0
    for outcome in outcomes:
        count += 1
        matches += favorable(tuple(ball < b for ball in outcome))
    return Fraction(matches, count)


def conditional_probability(attended, submitted):
    assert 0 <= submitted <= attended and attended > 0
    return Fraction(sum(k < submitted for k in range(attended)), attended)


ORACLES = {
    "linear_isolate": lambda a, b, c: linear_solution(a, b, 0, c),
    "linear_brackets": lambda a, b, c: linear_solution(a, a*b, 0, c),
    "linear_both_sides": linear_solution,
    "linear_cost": lambda fee, unit, total: linear_solution(unit, fee, 0, total),
    "percent_of": lambda p, n: Fraction(n, 100) * p,
    "percent_increase": lambda n, p: n + Fraction(n, 100) * p,
    "percent_reverse": lambda price, p: linear_solution(Fraction(100-p, 100), 0, 0, price),
    "percent_change": lambda old, new: 100 * (Fraction(new, old) - 1),
    "lines_slope": lambda x1, y1, x2, y2: Fraction(y2-y1, x2-x1),
    "lines_intercept": lambda slope, x, y: y - x*slope,
    "lines_table": lambda x1, y1, x2, y2, x: Fraction(y1*(x2-x)+y2*(x-x1), x2-x1),
    "lines_rate": lambda start, per_minute, minutes: sum([start]+[per_minute]*minutes),
    "systems_sum": lambda u, v: solve_system(1, 1, 1, -1, u, v)[0],
    "systems_prices": solve_prices,
    "systems_intersect": lambda m, b, c: linear_solution(m, b, 1, c),
    "systems_infinite": solve_dependent,
    "triangles_area": lambda base, height: Fraction(base*height, 2),
    "triangles_height": lambda area, base: linear_solution(Fraction(base,2), 0, 0, area),
    "triangles_pythagoras": distance,
    "triangles_similarity": lambda a, b, next_a: linear_solution(a, 0, 0, b*next_a),
    "powers_product": lambda _, a, b: exact_log(integer_power(2,a)*integer_power(2,b),2),
    "powers_nested": lambda _, a, b: exact_log(integer_power(integer_power(2,a),b),2),
    "powers_negative": lambda base, exponent, numerator: numerator / Fraction(1, integer_power(base,-exponent)),
    "powers_square_roots": lambda a, b: perfect_root(a)-perfect_root(b),
    "quadratic_roots": find_larger_root,
    "quadratic_vertex": lambda b, c: parabola_minimum(b,c)[1],
    "quadratic_tangent": tangent_height,
    "quadratic_rectangle": rectangle_long_side,
    "exponential_value": lambda initial, base, steps: math.prod([initial]+[base]*steps),
    "exponential_rate": lambda initial, next_value: linear_solution(initial,0,0,next_value),
    "exponential_time": lambda initial, final: exact_log(Fraction(final,initial),2),
    "exponential_decay": lambda initial, p: initial - Fraction(p,100)*initial*(2-Fraction(p,100)),
    "stats_mean": lambda *values: mean(values),
    "stats_missing": lambda expected_mean, a, b: linear_solution(Fraction(1,3), Fraction(a+b,3), 0, expected_mean),
    "stats_median": lambda *values: median(values),
    "stats_weighted": weighted_mean,
    "probability_single": lambda b,w: probability_by_counting(b,w,1,replacement=False,favorable=all),
    "probability_without_replacement": lambda b,w: probability_by_counting(b,w,2,replacement=False,favorable=all),
    "probability_conditional": conditional_probability,
    "probability_complement": lambda b,w: probability_by_counting(b,w,2,replacement=True,favorable=any),
}


def inputs_for(family, statement, lang):
    values = numbers(statement)
    if lang == "en":
        return values
    if family in {"percent_of", "percent_reverse"}:
        return values[::-1]
    if family == "lines_intercept":
        assert values[-1] == 0
        return values[:-1]
    if family in {"powers_product", "powers_nested"}:
        return values[-1:] + values[:-1]
    return values


class LegacyAnswerTests(unittest.TestCase):
    def test_all_legacy_variants_against_prompt_based_oracles(self):
        self.assertEqual(set(ORACLES), {f.__name__ for families in FAMILIES.values() for f in families})
        checked = 0
        for topic in TOPICS:
            for seed in range(topic["variants"]):
                for lang in ("ru", "en"):
                    exercise = generate(topic["id"], seed, lang)
                    family_name = exercise["family"]
                    with self.subTest(topic=topic["id"], family=family_name, seed=seed, lang=lang):
                        values = inputs_for(family_name, exercise["prompt"], lang)
                        expected = ORACLES[family_name](*values)
                        self.assertAlmostEqual(exercise["answer"], float(expected), places=10)
                        checked += 1
        self.assertEqual(checked, 8000)


if __name__ == "__main__":
    unittest.main()
