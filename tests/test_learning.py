from collections import Counter
import math
import tempfile
import unittest

from backend.curriculum import TOPICS, LEVELS, generate, lesson
from backend.storage import ApiError, StudyStore, TOPIC_BY_ID, parse_answer


class CurriculumTests(unittest.TestCase):
    def test_curriculum_structure_and_variants(self):
        counts = Counter(entry["grade"] for entry in TOPICS)
        self.assertTrue(all(counts[grade] >= 20 for grade in (7, 8, 9)), counts)
        for entry in TOPICS:
            key = entry["id"]
            with self.subTest(topic=key):
                body = lesson(key)
                self.assertTrue(entry["section"])
                self.assertTrue(body["intro"])
                self.assertGreaterEqual(len(body["theory"]), 2)
                self.assertGreaterEqual(len(body["examples"]), 2)
                self.assertGreaterEqual(len(body["mistakes"]), 2)
                self.assertGreaterEqual(len(body["checks"]), 2)
                self.assertTrue(all(len(example["steps"]) >= 2 for example in body["examples"]))
                prompts = set()
                family_counts = Counter()
                for variant in range(entry["variants"]):
                    task = generate(key, variant)
                    if not task.get("response"):
                        self.assertTrue(math.isfinite(task["answer"]))
                    self.assertNotIn(task["prompt"], prompts)
                    self.assertEqual(task, generate(key, variant))
                    self.assertTrue(task["hints"] and task["solution"])
                    if "verify" in task:
                        self.assertTrue(math.isclose(float(task["verify"]), task["answer"], rel_tol=1e-10, abs_tol=1e-10))
                    graph = task.get("graph")
                    if graph:
                        self.assertIn(graph["type"], {"lines", "quadratic", "triangle"})
                        if graph["type"] == "triangle":
                            self.assertGreater(graph["base"] * graph["height"], 0)
                    prompts.add(task["prompt"])
                    family_counts[task["difficulty"]] += 1
                self.assertGreaterEqual(len(prompts), 100)
                self.assertEqual(sum(family_counts.values()), entry["variants"])
                self.assertTrue(set(family_counts).issubset(LEVELS))


class LearningTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.now = 500.0
        self.store = StudyStore(self.folder.name, clock=lambda: self.now)

    def answer(self, state, correct=True):
        q = state["question"]
        expected = generate(q["topic"], q["seed"], state["lang"])["answer"]
        return self.store.access(state["id"], "answer", {
            "index": state["index"], "answer": repr(expected) if correct else None,
        })

    def test_untimed_difficulty_record_and_exact_review(self):
        state = self.store.start({
            "mode": "test", "topics": ["systems"], "count": 2,
            "difficulty": "hard", "secondsPerQuestion": None,
        })
        self.assertIsNone(state["remainingSeconds"])
        self.assertEqual(state["question"]["difficulty"], "hard")
        first = state["question"]["id"]
        self.now += 301
        self.assertEqual(self.store.access(state["id"])["question"]["id"], first)
        second = self.answer(state, False)
        self.now += 5
        done = self.answer(second)
        self.assertTrue(done["finished"])
        self.assertEqual(done["topicErrors"], {"systems": 1})
        self.assertEqual(done["elapsedSeconds"], 306)
        self.assertEqual(done["results"][0]["seconds"], 301)
        replay = self.store.start({
            "mode": "review", "count": 5,
            "reviewStrategy": "exact", "sourceSessionId": done["id"],
        })
        self.assertEqual(replay["question"]["id"], first)
        self.assertEqual(replay["total"], 1)
        self.answer(replay)
        self.assertEqual(self.store.progress()["mistakeCount"], 0)

    def test_variable_deadline_and_resume(self):
        state = self.store.start({"mode": "test", "topics": ["linear"], "count": 2, "secondsPerQuestion": 60})
        self.now += 31
        self.assertEqual(self.store.access(state["id"])["remainingSeconds"], 29)
        self.now += 29
        advanced = self.store.access(state["id"], "expire", {"index": 0})
        self.assertEqual(advanced["index"], 1)
        self.assertEqual(advanced["remainingSeconds"], 60)
        self.now += 6
        done = self.answer(advanced)
        self.assertEqual(done["elapsedSeconds"], 66)

    def test_lesson_completion_and_mastery_use_distinct_answers(self):
        self.assertFalse(self.store.get_lesson("quadratics")["completed"])
        self.store.complete_lesson("quadratics")
        self.store.complete_lesson("quadratics")
        for level, count in (("easy", 3), ("medium", 2), ("hard", 1)):
            state = self.store.start({"mode": "test", "topics": ["quadratics"], "count": count, "difficulty": level})
            while not state["finished"]:
                state = self.answer(state)
        self.assertTrue(StudyStore(self.folder.name).get_lesson("quadratics")["completed"])
        progress = self.store.progress()
        entry = next(t for t in progress["topics"] if t["id"] == "quadratics")
        self.assertTrue(entry["mastered"])
        self.assertEqual(entry["distinctAttempted"], 6)
        self.assertEqual(progress["lessonsCompleted"], 1)
        self.assertEqual(progress["mastered"], 1)

    def test_reproduce_and_validate_settings(self):
        state = self.store.start({"mode": "practice", "count": 1, "problemId": "linear:130"})
        self.assertEqual(state["question"]["id"], "linear:130")
        self.assertEqual(state["question"]["prompt"], generate("linear", 130)["prompt"])
        for topic, verify in (
            ("linear", lambda i, j: j - 5),
            ("systems", lambda i, j: i + 5),
            ("quadratics", lambda i, j: j - 5),
        ):
            for seed in (1000, 1001, 1999, 2000, 125402, 1000999):
                i, j = divmod(seed - 1000, 1000)
                q = generate(topic, seed)
                self.assertEqual(q["answer"], verify(i + 10, j))
                self.assertEqual(q, generate(topic, seed))
        for data in ({"difficulty": "impossible"}, {"secondsPerQuestion": -4}):
            with self.assertRaises(ApiError):
                self.store.start({"mode": "test", "count": 1, "topics": ["linear"], **data})

    def test_sat_options_for_all_legacy_answers(self):
        for topic in TOPICS:
            if not topic["satReady"]:
                continue
            for seed in range(topic["variants"]):
                question = generate(topic["id"], seed, "en")
                if question.get("response"):
                    continue  # Authored, nonnumeric choices have their own exhaustive tests.
                target = question["answer"]
                options = self.store.options(topic["id"], seed, target)
                self.assertEqual(len(set(options)), 4)
                self.assertEqual(sum(self.store.matches(parse_answer(str(value)), target) for value in options), 1)

    def test_legacy_sqlite_session_is_preserved_by_migration(self):
        state = self.store.start({"mode": "test", "topics": ["linear"], "count": 1})
        finished = self.answer(state)
        with self.store.transaction() as conn:
            row = self.store.load_all(conn)[0]
            for key in ("secondsPerQuestion", "questionStartedAt", "difficulty", "elapsedSeconds"):
                row.pop(key, None)
            row["outcomes"]["0"].pop("seconds")
            row["outcomes"]["0"].pop("recordedAt")
            self.store.save(conn, row)
            conn.execute("DROP TABLE completed_lessons")
            conn.execute("PRAGMA user_version = 0")
        migrated = StudyStore(self.folder.name, clock=lambda: self.now)
        result = migrated.access(finished["id"])
        self.assertEqual(result["results"][0]["prompt"], finished["results"][0]["prompt"])
        self.assertEqual(result["correct"], 1)
        self.assertIsNone(result["elapsedSeconds"])
        self.assertEqual(migrated.progress()["answered"], 1)
        migrated.complete_lesson("linear")
        self.assertTrue(migrated.get_lesson("linear")["completed"])


if __name__ == "__main__":
    unittest.main()
