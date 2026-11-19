"""Regression tests derived from the independent audit findings."""
import json
import sqlite3
import tempfile
import unittest
from fractions import Fraction

from backend.curriculum import TOPICS, difficulty, generate
from backend.grading import AnswerError, sat_matches, sat_input_available, structured_matches
from backend.storage import StudyStore, ApiError, parse_answer
from backend.server import AppServer, CoachLimiter
import http.client
import threading


class Repairs(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.now = 1000.0
        self.store = StudyStore(self.folder.name, clock=lambda: self.now)

    def attempt(self, seed, help_count=0):
        state = self.store.start({"mode":"practice","count":1,"problemId":f"linear:{seed}"})
        for _ in range(help_count):
            self.store.access(state["id"], "hint", {"index":0})
        result = self.store.access(state["id"], "answer", {
            "index":0, "answer":str(generate("linear",seed)["answer"])
        })
        self.store.access(state["id"], "next", {"index":0})
        self.now += 1
        return result

    def test_help_and_unknown_attempts_cannot_master_topic(self):
        self.store.complete_lesson("linear")
        for seed in (0, 1, 100, 101, 200, 300):
            self.assertEqual(self.attempt(seed, 2)["feedback"]["assistance"], "assisted")
        entry = next(t for t in self.store.progress()["topics"] if t["id"]=="linear")
        self.assertFalse(entry["mastered"])
        self.assertEqual(entry["independentAttempted"], 0)
        self.assertEqual(entry["assisted"], 6)
        with self.store.transaction() as conn:
            for session in self.store.load_all(conn):
                for outcome in session["outcomes"].values():
                    outcome.pop("assistance")
                self.store.save(conn, session)
        revived = StudyStore(self.folder.name, clock=lambda:self.now)
        entry = next(t for t in revived.progress()["topics"] if t["id"]=="linear")
        self.assertFalse(entry["mastered"])
        self.assertEqual(entry["unknown"], 6)

    def test_mastery_requires_diverse_self_solved_types(self):
        self.store.complete_lesson("linear")
        for seed in range(100,106):
            self.attempt(seed)
        entry=next(t for t in self.store.progress()["topics"] if t["id"]=="linear")
        self.assertFalse(entry["mastered"])
        for seed in (1,201):
            self.attempt(seed)
        entry=next(t for t in self.store.progress()["topics"] if t["id"]=="linear")
        self.assertTrue(entry["mastered"])
        self.assertGreaterEqual(entry["distinctFamilies"],3)

    def test_direct_substitution_families_do_not_award_hard_credit(self):
        for topic, seed in (("linear",356),("lines",356),("triangles",356),("percent",356),
                            ("powers",256),("g8-complete-square",256),("g7-congruence",256),
                            ("g7-factorization",256),("g7-algebraic-fractions",256),
                            ("g7-circle-tangency",256),("g7-adjacent-vertical",256),
                            ("g8-radicals",256),("g8-discriminant",256),("g9-triangle-laws",256)):
            self.assertNotEqual(difficulty(topic,seed),"hard",topic)

    def test_read_only_expired_get_and_explicit_idempotent_expiry(self):
        state=self.store.start({"mode":"test","topics":["linear"],"count":2,"secondsPerQuestion":60})
        with self.store.transaction() as conn:
            initial=conn.execute("SELECT body FROM sessions WHERE id=?",(state["id"],)).fetchone()[0]
        self.now += 100
        snapshot=self.store.access(state["id"])
        self.assertTrue(snapshot["expired"])
        self.assertEqual(snapshot["index"],0)
        with self.store.transaction() as conn:
            self.assertEqual(initial,conn.execute("SELECT body FROM sessions WHERE id=?",(state["id"],)).fetchone()[0])
        next_state=self.store.access(state["id"],"expire",{"index":0})
        duplicate=self.store.access(state["id"],"expire",{"index":0})
        self.assertEqual(next_state,duplicate)
        self.assertEqual(next_state["index"],1)
        self.assertEqual(next_state["answered"],1)
        self.assertEqual(next_state["remainingSeconds"],60)

    def test_active_sessions_and_cache_invalidate_for_other_store(self):
        a=self.store.start({"mode":"practice","topics":["linear"],"count":1})
        b=self.store.start({"mode":"test","topics":["systems"],"count":1})
        self.assertEqual({s["id"] for s in self.store.progress()["activeSessions"]},{a["id"],b["id"]})
        before=self.store.progress()
        other=StudyStore(self.folder.name,clock=lambda:self.now)
        other.complete_lesson("linear")
        after=self.store.progress()
        self.assertEqual(after["lessonsCompleted"],before["lessonsCompleted"]+1)

    def test_sat_forms_and_domain(self):
        for value in ("2/3",".6666",".6667","0.666","0.667"):
            self.assertTrue(sat_matches(value,2/3),value)
        for value in (".66",".67","0.66","0.67","0.668","00.67","000.7","-00.33"):
            self.assertFalse(sat_matches(value,2/3),value)
        for value in ("-1/3","-.3333","-0.333"):
            self.assertTrue(sat_matches(value,-1/3),value)
        self.assertFalse(sat_matches("-00.33", -1/3))
        for value in ("+2/3", "1/-2", "0.5/0.75"):
            with self.assertRaises(AnswerError):
                sat_matches(value, 2/3)
        for topic in TOPICS:
            if not topic["satReady"]: continue
            for seed in range(topic["variants"]):
                question=generate(topic["id"],seed)
                if question.get("response"): continue
                target=question["answer"]
                options=self.store.options(topic["id"],seed,target)
                values=[parse_answer(v) for v in options]
                self.assertEqual(len(set(values)),4)
                self.assertEqual(sum(self.store.matches(v,target) for v in values),1)
                if "/" in options[0]:
                    self.assertTrue(all("/" in choice for choice in options))
                else:
                    self.assertTrue(all("/" not in choice for choice in options))
                if topic["id"]=="probability":
                    self.assertTrue(all(0<=value<=1 for value in values))
        self.assertEqual(parse_answer("3 047 466 240"),3047466240)
        with self.assertRaises(ApiError):parse_answer("3 1/2")

    def test_sat_oversized_keys_use_choices_for_display_and_grading(self):
        oversized = []
        for topic in TOPICS:
            if not topic["satReady"] or topic.get("satOnly"):
                continue
            for seed in range(topic["variants"]):
                target = generate(topic["id"], seed)["answer"]
                if not sat_input_available(target):
                    oversized.append((topic["id"], seed))
        self.assertEqual(len(oversized), 36)
        state = self.store.start({"mode":"practice", "topics":["powers"], "count":2, "lang":"en"})
        with self.store.transaction() as conn:
            session = next(s for s in self.store.load_all(conn) if s["id"] == state["id"])
            session["questions"] = [["powers",0],["powers",256]]
            session["index"] = 1
            session["recordedDifficulties"] = ["easy","easy"]
            self.store.save(conn, session)
        state = self.store.access(state["id"])
        self.assertIn("options", state["question"])
        result = self.store.access(state["id"], "answer", {"index":1,"answer":"823543"})
        self.assertTrue(result["feedback"]["correct"])

    def test_structured_exactness_and_equivalent_interval_forms(self):
        self.assertTrue(structured_matches("(1/3;2/3)", {"kind":"pair"}, "1/3;2/3"))
        self.assertFalse(structured_matches("0.3333333333;2/3", {"kind":"pair"}, "1/3;2/3"))
        self.assertFalse(structured_matches("1.00000000001;2", {"kind":"pair"}, "1;2"))
        with self.assertRaises(AnswerError):
            structured_matches("))1;2((", {"kind":"pair"}, "1;2")
        self.assertTrue(structured_matches("[2;+∞)", {"kind":"interval"}, "[2;inf)"))
        self.assertFalse(structured_matches("(2;5]", {"kind":"interval"}, "[2;5]"))
        with self.assertRaises(AnswerError):
            structured_matches("[2;+∞]", {"kind":"interval"}, "[2;inf)")
        with self.assertRaises(AnswerError):
            structured_matches("(;5]", {"kind":"interval"}, "[2;5]")

    def test_periodic_fraction_response_requires_exact_reduced_fraction(self):
        task = generate("g9-periodic-fractions",33)
        self.assertEqual(task["response"], {"kind":"fraction"})
        self.assertTrue(structured_matches("1/3", task["response"], task["answer"]))
        for raw in ("0.3333333333", "33/99"):
            with self.assertRaises(AnswerError):
                structured_matches(raw, task["response"], task["answer"])
        self.assertFalse(structured_matches("1/4", task["response"], task["answer"]))

    def test_limiter_boundaries_and_parallelism(self):
        clock=[10.]
        limiter=CoachLimiter(clock=lambda:clock[0])
        with limiter.reserve():
            with limiter.reserve():
                with self.assertRaises(ApiError):
                    with limiter.reserve(): pass
        self.assertEqual(limiter.running,0)
        for _ in range(4):
            with limiter.reserve():pass
        with self.assertRaises(ApiError):
            with limiter.reserve():pass
        clock[0] += 61
        with limiter.reserve():pass
        for _ in range(53):
            clock[0] += 61
            with limiter.reserve():pass
        with self.assertRaises(ApiError):
            with limiter.reserve():pass
        clock[0] += 86400
        with self.assertRaisesRegex(RuntimeError,"provider failed"):
            with limiter.reserve():
                raise RuntimeError("provider failed")
        self.assertEqual(limiter.running,0)

    def test_head_has_headers_and_does_not_expire(self):
        state=self.store.start({"mode":"test","topics":["linear"],"count":1,"secondsPerQuestion":60})
        self.now += 61
        with AppServer(("127.0.0.1",0),self.store) as server:
            thread=threading.Thread(target=server.serve_forever,daemon=True)
            thread.start()
            try:
                conn=http.client.HTTPConnection(*server.server_address,timeout=3)
                conn.request("HEAD","/api/sessions/"+state["id"])
                response=conn.getresponse()
                self.assertEqual(response.status,200)
                self.assertIn("frame-ancestors 'none'",response.getheader("Content-Security-Policy"))
                self.assertEqual(response.getheader("Referrer-Policy"),"no-referrer")
                self.assertNotIn("Python",response.getheader("Server"))
                self.assertEqual(response.read(),b"")
                conn.close()
                self.assertFalse(self.store.access(state["id"])["finished"])
            finally:
                server.shutdown()
                thread.join()


if __name__=="__main__":
    unittest.main()
