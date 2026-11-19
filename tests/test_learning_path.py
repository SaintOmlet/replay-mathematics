"""Behavioral checks for prerequisite-aware, evidence-based study guidance."""

import copy
import unittest

from backend.curriculum import TOPICS, TOPIC_BY_ID
from backend.learning_path import PREREQUISITES, plan, validate_prerequisites


def mastered(topic):
    return {"id":topic, "mastered":True, "lessonCompleted":True,
            "answered":8, "independentAttempted":8, "independentCorrect":8,
            "distinctFamilies":3, "mediumCorrect":2, "hardCorrect":1}


class LearningPathTests(unittest.TestCase):
    def test_every_registered_topic_has_authored_acyclic_dependencies(self):
        validate_prerequisites()
        self.assertLessEqual(set(TOPIC_BY_ID), set(PREREQUISITES))
        for topic in TOPICS:
            for prerequisite in PREREQUISITES[topic["id"]]:
                self.assertIn(prerequisite, TOPIC_BY_ID)
                self.assertLessEqual(TOPIC_BY_ID[prerequisite]["grade"], topic["grade"])

    def test_new_learner_gets_available_foundations_without_invented_score(self):
        result = plan({})
        self.assertEqual([row["topic"] for row in result], ["linear","percent","g7-integer-powers"])
        self.assertTrue(all(row["action"] == "lesson" for row in result))
        self.assertTrue(all(not PREREQUISITES[row["topic"]] for row in result))
        self.assertTrue(all("score" not in row for row in result))

    def test_advanced_weak_topic_leads_to_unconfirmed_foundation(self):
        report = {"topics":[{"id":"g9-dot-product","answered":5,"independentAttempted":5,
                             "independentCorrect":1,"lessonCompleted":True}],
                  "activeSessions":[{"topic":"g9-dot-product"}]}
        result = plan(report)
        self.assertEqual(result[0]["topic"], "linear")
        self.assertEqual(result[0]["prerequisite"], "g9-dot-product")
        self.assertIn(TOPIC_BY_ID["g9-dot-product"]["title"], result[0]["reason"])
        self.assertTrue(all(row["topic"] != "g9-dot-product" for row in result))

    def test_ready_advanced_learner_is_not_sent_back_to_mastered_topics(self):
        rows = [mastered(topic["id"]) for topic in TOPICS if topic["id"] != "g9-dot-product"]
        rows.append({"id":"g9-dot-product","answered":5,"independentAttempted":5,
                     "independentCorrect":1,"lessonCompleted":True})
        result = plan({"topics":rows})
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["topic"], "g9-dot-product")
        self.assertEqual(result[0]["action"], "practice")
        self.assertIn("1 из 5", result[0]["reason"])

    def test_old_or_assisted_attempts_are_not_claimed_as_independent(self):
        report = {"topics":[{"id":"linear","answered":12,"correct":12,
                             "lessonCompleted":True,"mastered":False}]}
        recommendation = plan(report)[0]
        self.assertEqual(recommendation["action"], "practice")
        self.assertIn("нет подтверждённых самостоятельных", recommendation["reason"])

    def test_unfinished_lesson_has_priority_over_adding_another_practice(self):
        report = {"topics":[{"id":"linear","answered":3}], "activeSessions":[{"topic":"linear"}]}
        recommendation = plan(report)[0]
        self.assertEqual(recommendation["topic"], "linear")
        self.assertEqual(recommendation["action"], "lesson")
        report["topics"][0]["lessonCompleted"] = True
        self.assertTrue(all(row["topic"] != "linear" for row in plan(report)))

    def test_fresh_work_follows_recently_selected_grade(self):
        rows = [mastered(topic["id"]) for topic in TOPICS if topic["grade"] < 9]
        result = plan({"topics":rows,"recent":[{"topics":["g9-counting"]}]})
        self.assertTrue(result)
        self.assertTrue(all(TOPIC_BY_ID[row["topic"]]["grade"] == 9 for row in result))

    def test_all_mastered_produces_no_manufactured_extra_work(self):
        self.assertEqual(plan({"topics":[mastered(topic["id"]) for topic in TOPICS]}), [])

    def test_sparse_invalid_legacy_fields_and_unknown_ids_are_ignored(self):
        report = {"topics":[None,{"id":"missing","mastered":True},{"id":[]},
                             {"id":"linear","answered":"old","independentAttempted":-3}],
                  "activeSessions":[None,{"topic":"deleted"},{"topic":{}}],
                  "recent":[{"topics":None},{"topics":[None,{},[]]}]}
        before = copy.deepcopy(report)
        result = plan(report)
        self.assertEqual(result, plan(report))
        self.assertEqual(report, before)
        self.assertEqual(len({row["topic"] for row in result}), len(result))
        self.assertTrue(all(row["topic"] in TOPIC_BY_ID for row in result))
        self.assertLessEqual(len(result), 3)
        self.assertEqual(plan(None), plan({}))

    def test_authoring_validator_rejects_missing_dependencies_and_cycles(self):
        with self.assertRaisesRegex(ValueError, "Unknown prerequisite"):
            validate_prerequisites({"linear":("unknown",)})
        with self.assertRaisesRegex(ValueError, "cycle"):
            validate_prerequisites({"linear":("lines",),"lines":("linear",)})


if __name__ == "__main__":
    unittest.main()
