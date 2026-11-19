"""Regression tests for the timed and repeat-practice flows."""

import http.client
import json
import os
import tempfile
import threading
import unittest
from fractions import Fraction
from unittest.mock import patch

from backend import coach
from backend.server import AppServer
from backend.storage import ApiError, StudyStore, TOPIC_BY_ID, TEST_SECONDS, parse_answer


class StudyStoreTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.now = 1000.0
        self.store = StudyStore(self.folder.name, clock=lambda: self.now)
        self.topic = next(iter(TOPIC_BY_ID))

    def start(self, mode, count=2, lang="ru"):
        return self.store.start(
            {"mode": mode, "topics": [self.topic], "count": count, "lang": lang}
        )

    def test_practice_persists_hints_and_picks_new_variant_for_review(self):
        practice = self.start("practice", 1)
        question_id = practice["question"]["id"]
        with_hint = self.store.access(practice["id"], "hint", {"index": 0})
        self.assertEqual(len(with_hint["hints"]), 1)
        feedback = self.store.access(practice["id"], "answer", {"index": 0, "answer": None})
        self.assertFalse(feedback["feedback"]["correct"])
        self.assertTrue(feedback["feedback"]["solution"])
        restored = StudyStore(self.folder.name, clock=lambda: self.now)
        self.assertEqual(restored.access(practice["id"]), feedback)
        self.assertTrue(restored.access(practice["id"], "next", {"index": 0})["finished"])
        review = self.start("review", 1)
        self.assertNotEqual(review["question"]["id"], question_id)
        self.assertEqual(review["question"]["topic"], self.topic)
        self.assertEqual(restored.progress()["answered"], 1)

    def test_test_hides_solutions_and_rejects_a_late_answer_for_next_question(self):
        test = self.start("test")
        self.assertEqual(test["remainingSeconds"], TEST_SECONDS)
        self.assertNotIn("graph", test["question"])
        self.assertNotIn("answer", test["question"])
        with self.assertRaises(ApiError) as denied:
            self.store.coach_context(test["id"], 0)
        self.assertEqual(denied.exception.status, 403)
        self.assertEqual(self.store.access(test["id"], "hint", {"index": 0})["hints"], [])
        self.now += TEST_SECONDS
        current = self.store.access(test["id"], "answer", {"index": 0, "answer": "1"})
        self.assertEqual(current["index"], 1)
        self.assertEqual(current["remainingSeconds"], TEST_SECONDS)
        self.assertEqual(current["answered"], 1)
        self.assertIsNone(current["feedback"])
        self.assertEqual(current["results"], [])
        self.assertNotEqual(current["question"]["id"], test["question"]["id"])
        done = self.store.access(test["id"], "answer", {"index": 1, "answer": "1"})
        self.assertTrue(done["finished"])
        self.assertTrue(done["results"][0]["timedOut"])
        self.assertIsNone(done["results"][0]["submitted"])
        self.assertTrue(done["results"][0]["solution"])
        self.assertFalse(done["results"][1]["timedOut"])

    def test_answer_parser_accepts_signed_decimals_and_fractions(self):
        self.assertEqual(parse_answer("−0,25"), Fraction(-1, 4))
        self.assertEqual(parse_answer(" -2 / 8 "), Fraction(-1, 4))
        self.assertIsNone(parse_answer(""))
        for invalid in ["1/0", "1+2", "NaN"]:
            with self.subTest(invalid=invalid), self.assertRaises(ApiError):
                parse_answer(invalid)

    def test_english_test_has_stable_options_with_exactly_one_correct_choice(self):
        state = self.start("test", lang="en")
        self.assertEqual(state["lang"], "en")
        options = state["question"]["options"]
        self.assertEqual(len(set(options)), 4)
        self.assertEqual(options, self.store.access(state["id"])["question"]["options"])
        done = self.store.access(state["id"], "finish", {})
        answer = done["results"][0]["answer"]
        self.assertEqual(sum(self.store.matches(parse_answer(str(option)), answer) for option in options), 1)

    def test_optional_coach_without_key_keeps_local_hints_available(self):
        practice = self.start("practice")
        context = self.store.coach_context(practice["id"], 0)
        self.assertEqual(context["problem"], practice["question"]["prompt"])
        with patch.dict(os.environ, {"GROQ_API_KEY": ""}), self.assertRaises(ApiError) as error:
            coach.reply(context, "Как начать?")
        self.assertEqual(error.exception.status, 503)
        self.assertTrue(self.store.access(practice["id"], "hint", {"index": 0})["hints"])

    def test_http_session_persists_an_answer_and_completes(self):
        with AppServer(("127.0.0.1", 0), self.store) as server:
            worker = threading.Thread(target=server.serve_forever, daemon=True)
            worker.start()
            try:
                connection = http.client.HTTPConnection(*server.server_address, timeout=3)
                self.addCleanup(connection.close)

                def call(method, path, data=None):
                    connection.request(method, path, json.dumps(data) if data else None,
                                       {"Content-Type": "application/json"} if data else {})
                    response = connection.getresponse()
                    return response.status, json.loads(response.read())

                status, state = call("POST", "/api/sessions", {
                    "mode": "practice", "topics": [self.topic], "count": 1, "lang": "en"
                })
                self.assertEqual(status, 200)
                session_url = f"/api/sessions/{state['id']}"
                status, attempt = call("POST", session_url + "/answer", {"index": 0, "answer": "1"})
                self.assertEqual(status, 200)
                self.assertIsNotNone(attempt["feedback"])
                self.assertEqual(call("GET", session_url), (200, attempt))
                self.assertTrue(call("POST", session_url + "/next", {"index": 0})[1]["finished"])
                self.assertEqual(call("GET", "/api/progress")[1]["sessions"], 1)
            finally:
                server.shutdown()
                worker.join(timeout=3)


if __name__ == "__main__":
    unittest.main()
