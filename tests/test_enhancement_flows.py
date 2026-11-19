"""Integration through the public HTTP entry points for new learning formats."""
import http.client
import json
import tempfile
import threading
import unittest

from backend.curriculum import generate, graph_curriculum, set_curriculum
from backend.server import AppServer
from backend.storage import StudyStore


class EnhancementFlows(unittest.TestCase):
    def setUp(self):
        self.folder=tempfile.TemporaryDirectory()
        self.store=StudyStore(self.folder.name)
        self.server=AppServer(("127.0.0.1",0),self.store)
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.thread.join()
        self.server.server_close()
        self.folder.cleanup()

    def call(self,path,data=None):
        connection=http.client.HTTPConnection(*self.server.server_address,timeout=5)
        try:
            connection.request("POST" if data is not None else "GET",path,
                               json.dumps(data) if data is not None else None,
                               {"Content-Type":"application/json"} if data is not None else {})
            response=connection.getresponse()
            self.assertEqual(response.status,200)
            return json.loads(response.read())
        finally:
            connection.close()

    def test_every_new_family_can_be_started_answered_and_reviewed(self):
        for module in (graph_curriculum,set_curriculum):
            for topic,families in module.FAMILIES.items():
                for index in range(len(families)):
                    seed=index*100+56
                    question=generate(topic,seed)
                    state=self.call('/api/sessions',{"mode":"practice","count":1,"problemId":f"{topic}:{seed}"})
                    self.assertNotIn("answer",state["question"])
                    self.assertNotIn("diagnostics",state["question"])
                    result=self.call('/api/sessions/'+state["id"]+'/answer',{"index":0,"answer":question["answer"]})
                    self.assertTrue(result["feedback"]["correct"],(topic,seed))
                    if question["response"]["kind"]=="graph":
                        self.assertTrue(result["feedback"]["answerDisplay"].startswith('y ='))
                    final=self.call('/api/sessions/'+state["id"]+'/next',{"index":0})
                    self.assertTrue(final["finished"])
                    self.assertTrue(final["results"][0]["correct"])

    def test_graph_failure_has_diagnostic_and_original_response_stays_private(self):
        state=self.call('/api/sessions',{"mode":"practice","count":1,"problemId":"g7-line-graphs:56"})
        result=self.call('/api/sessions/'+state["id"]+'/answer',{"index":0,"answer":'{"m":0,"b":3}'})
        self.assertFalse(result["feedback"]["correct"])
        self.assertIn("Наклон совпадает",result["feedback"]["diagnostic"])
        self.assertEqual(result["feedback"]["answerDisplay"],"y = 2")
        self.assertEqual(result["feedback"]["submittedDisplay"],"y = 3")

    def test_recommendations_match_catalog_and_update_after_lesson(self):
        catalog=self.call('/api/catalog')
        identifiers={topic["id"] for topic in catalog["topics"]}
        report=self.call('/api/progress')
        step=report["recommendations"][0]
        self.assertIn(step["topic"],identifiers)
        self.assertEqual(step["action"],"lesson")
        self.call('/api/lessons/'+step["topic"]+'/complete',{})
        updated=self.call('/api/progress')
        self.assertTrue(any(s["topic"]==step["topic"] and s["action"]=="practice" for s in updated["recommendations"]))
