import unittest
from math import isfinite

from backend.content import TOPICS, generate


class ContentTests(unittest.TestCase):
    def test_catalog_has_distinct_variants_in_each_language(self):
        prompts = {"ru": set(), "en": set()}
        families = set()
        for topic in TOPICS:
            for variant in range(topic["variants"]):
                russian = generate(topic["id"], variant)
                english = generate(topic["id"], variant, "en")
                self.assertEqual(russian["answer"], english["answer"])
                self.assertTrue(isfinite(russian["answer"]))
                self.assertEqual(russian, generate(topic["id"], variant))
                self.assertTrue(russian["hints"])
                self.assertTrue(russian["solution"])
                families.add(russian["family"])
                for lang, exercise in (("ru", russian), ("en", english)):
                    self.assertNotIn(exercise["prompt"], prompts[lang])
                    prompts[lang].add(exercise["prompt"])
        self.assertGreaterEqual(len(families), 30)
        self.assertGreaterEqual(len(prompts["ru"]), 3000)

    def test_graphs_agree_with_answers(self):
        for topic in ("quadratics", "systems", "triangles"):
            entry = next(item for item in TOPICS if item["id"] == topic)
            for variant in range(entry["variants"]):
                exercise = generate(topic, variant)
                answer = exercise["answer"]
                family = exercise["family"]
                graph = exercise.get("graph")
                if family == "quadratic_roots":
                    self.assertEqual(graph["a"] * answer ** 2 + graph["b"] * answer + graph["c"], 0)
                    self.assertGreater(answer, -graph["b"] / (2 * graph["a"]))
                elif family == "quadratic_vertex":
                    self.assertEqual(2 * graph["a"] * answer + graph["b"], 0)
                elif family == "quadratic_tangent":
                    self.assertEqual(graph["b"] ** 2 - 4 * graph["a"] * (graph["c"] - answer), 0)
                elif graph and graph["type"] == "lines":
                    self.assertEqual(graph["m1"] * answer + graph["b1"], graph["m2"] * answer + graph["b2"])
                elif family == "triangles_area":
                    self.assertEqual(graph["base"] * graph["height"], 2 * answer)
                elif family == "triangles_pythagoras":
                    self.assertEqual(graph["base"] ** 2 + graph["height"] ** 2, answer ** 2)

    def test_rejects_unknown_catalog_entries(self):
        for arguments in (("unknown", 0), ("linear", True), ("linear", -1), ("linear", 400), ("linear", 0, "xx")):
            with self.subTest(arguments=arguments), self.assertRaises(ValueError):
                generate(*arguments)
