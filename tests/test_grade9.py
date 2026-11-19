import itertools
import math
import re
import unittest
from fractions import Fraction

from backend import grade9


PARAMETERS = tuple(itertools.product(range(10), repeat=2))
NUMBER = re.compile(r"[-−]?[0-9]+(?:/[0-9]+)?")


class GradeNineMathTests(unittest.TestCase):
    def test_written_conclusion_matches_numeric_answer(self):
        """Verify the student-facing answer in the last solution step, not only metadata."""
        for topic_id, families in grade9.FAMILIES.items():
            for difficulty, family in enumerate(families, start=1):
                for i, j in PARAMETERS:
                    task = family(i, j)
                    with self.subTest(topic=topic_id, difficulty=difficulty, parameters=(i, j)):
                        final_numbers = NUMBER.findall(task["solution"][-1])
                        self.assertTrue(final_numbers)
                        written = Fraction(final_numbers[-1].replace("−", "-"))
                        if isinstance(task["answer"], int):
                            self.assertEqual(written, task["answer"])
                        else:
                            self.assertTrue(math.isclose(float(written), task["answer"], rel_tol=1e-12, abs_tol=1e-12))

    def test_geometry_constraints_and_second_methods(self):
        for i, j in PARAMETERS:
            with self.subTest(i=i, j=j):
                # Rebuild the right triangle below a chord using its two legs.
                half, distance = i+2, j+3
                radius = math.hypot(half, distance)
                self.assertGreater(radius, half)
                self.assertGreater(radius, distance)
                self.assertAlmostEqual(grade9.sector_from_chord(i, j)["answer"], radius**2/4)

                # Independently embed the three-sided triangle in the coordinate plane.
                a, b = i+4, j+15
                c = a+b-3
                projection = (a*a+b*b-c*c)/(2*a)
                height_sq = b*b-projection**2
                self.assertGreater(height_sq, 0)
                self.assertAlmostEqual(grade9.triangle_area_squared(i, j)["answer"], a*a*height_sq/4)

                # Independent shoelace calculation for the four remaining vertices D,B,C,E.
                scale, divider = i+3, j+3
                width, height = 3*scale, 4*scale
                cut_base = Fraction(width,divider)
                cut_height = Fraction(height,divider)
                corners = ((cut_base, 0), (width, 0), (0, height), (0, cut_height))
                trapezoid = sum(
                    x1*y2-x2*y1 for (x1,y1),(x2,y2) in zip(corners, corners[1:]+corners[:1])
                )/2
                self.assertGreater(trapezoid, 0)
                self.assertAlmostEqual(grade9.cut_similar(i, j)["answer"], trapezoid)

    def test_rotation_center_inferred_from_both_coordinates(self):
        for i, j in PARAMETERS:
            task = grade9.recover_rotation(i, j)
            numbers = [int(value) for value in NUMBER.findall(task["ru"])]
            angle, px, py, qx, qy = numbers
            self.assertEqual(angle, 90)
            midpoint_x = Fraction(px+qx,2)
            midpoint_y = Fraction(py+qy,2)
            center_x = midpoint_x - Fraction(qy-py,2)
            center_y = midpoint_y + Fraction(qx-px,2)
            self.assertEqual(task["answer"],center_x * center_y)

    def test_diagrams_consistent_with_worked_examples(self):
        topics = {t["id"]: t["lesson"] for t in grade9.TOPICS}
        topics.update({key:item["lesson"] for key,item in grade9.LEGACY_LESSONS.items()})
        self.assertTrue(all(len(content["examples"])>=2 for content in topics.values()))

        for title, roots in (("g9-nonlinear-systems", (-2,2)), ("quadratics", (1,5))):
            parabola=topics[title]["graph"]
            level=parabola["level"]
            self.assertEqual(parabola["type"], "quadratic")
            for root in roots:
                self.assertEqual(parabola["a"]*root**2+parabola["b"]*root+parabola["c"],level)

        boundaries=topics["g9-plane-inequalities"]["graph"]
        self.assertEqual((boundaries["m1"],boundaries["b1"]),(-1,3))
        self.assertEqual((boundaries["m2"],boundaries["b2"]),(0,0))
        triangle=topics["g9-similarity-homothety"]["graph"]
        self.assertEqual(triangle["base"]*triangle["height"]/2,54)
