"""HTTP contracts for every family added to the school course and SAT transfer."""
import http.client
import json
import tempfile
import threading
import unittest

from backend import (complete_grade7, complete_grade8, complete_grade9,
                     sat_curriculum, statistics_curriculum)
from backend.curriculum import generate
from backend.server import AppServer
from backend.storage import StudyStore


COURSE_MODULES = (complete_grade7, complete_grade8, complete_grade9,
                  sat_curriculum, statistics_curriculum)


def family_cases():
    """Stable representative inside each family's 100-variant parameter grid."""
    for module in COURSE_MODULES:
        for topic, families in module.FAMILIES.items():
            for index, family in enumerate(families):
                yield module, topic, family, index*100+56


class CourseFlows(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.store = StudyStore(self.folder.name, clock=lambda: 10000.0)
        self.server = AppServer(('127.0.0.1', 0), self.store)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.thread.join(timeout=5)
        self.server.server_close()
        self.folder.cleanup()

    def call(self, path, payload=None, *, method=None, status=200):
        method = method or ('POST' if payload is not None else 'GET')
        connection = http.client.HTTPConnection(*self.server.server_address, timeout=10)
        try:
            body = json.dumps(payload) if payload is not None else None
            headers = {'Content-Type': 'application/json'} if payload is not None else {}
            connection.request(method, path, body, headers)
            response = connection.getresponse()
            raw = response.read()
            self.assertEqual(response.status, status, (path, raw.decode('utf-8', errors='replace')))
            if method == 'HEAD':
                self.assertEqual(raw, b'')
                return None
            self.assertTrue(response.getheader('Content-Type').startswith('application/json'))
            return json.loads(raw)
        finally:
            connection.close()

    def stored_body(self, session_id):
        with self.store.transaction(write=False) as connection:
            row = connection.execute('SELECT body FROM sessions WHERE id=?', (session_id,)).fetchone()
        self.assertIsNotNone(row)
        return row[0]

    def assert_public_unanswered(self, state, problem_id):
        self.assertFalse(state['finished'])
        self.assertEqual(state['answered'], 0)
        self.assertEqual(state['correct'], 0)
        self.assertEqual(state['hints'], [])
        self.assertIsNone(state['feedback'])
        self.assertEqual(state['results'], [])
        self.assertEqual(state['question']['id'], problem_id)
        self.assertTrue(state['question']['prompt'])
        # Traverse response specifications as well: a leaked nested key is still a leak.
        private = {'answer', 'solution', 'hints', 'verify', 'diagnostics'}
        def visit(value):
            if isinstance(value, dict):
                self.assertFalse(private.intersection(value), value)
                for child in value.values():
                    visit(child)
            elif isinstance(value, list):
                for child in value:
                    visit(child)
        visit(state['question'])

    def test_every_new_family_public_resume_submit_and_results(self):
        checked = 0
        formats = set()
        for module, topic, family, seed in family_cases():
            with self.subTest(topic=topic, family=family.__name__, seed=seed):
                lang = 'en' if module is sat_curriculum else 'ru'
                question = generate(topic, seed, lang)
                problem_id = f'{topic}:{seed}'
                state = self.call('/api/sessions', {
                    'mode': 'practice', 'count': 1, 'problemId': problem_id, 'lang': lang,
                })
                self.assert_public_unanswered(state, problem_id)
                self.assertEqual(state['lang'], lang)
                self.assertEqual(state['question']['prompt'], question['prompt'])
                formats.add(question.get('response', {}).get('kind', 'number'))
                session_path = '/api/sessions/'+state['id']
                before = self.stored_body(state['id'])
                resumed = self.call(session_path)
                self.assert_public_unanswered(resumed, problem_id)
                self.assertEqual(resumed, state)
                self.assertEqual(self.stored_body(state['id']), before)

                answer = question['answer']
                raw = answer if isinstance(answer, str) else str(answer)
                result = self.call(session_path+'/answer', {'index': 0, 'answer': raw})
                self.assertEqual(result['answered'], 1)
                self.assertTrue(result['feedback']['correct'], (problem_id, raw, result['feedback']))
                self.assertEqual(result['feedback']['assistance'], 'independent')
                self.assertTrue(result['feedback']['solution'])
                self.assertEqual(result['feedback']['submitted'], raw)
                saved = json.loads(self.stored_body(state['id']))
                self.assertEqual(set(saved['outcomes']), {'0'})
                self.assertTrue(saved['outcomes']['0']['correct'])

                final = self.call(session_path+'/next', {'index': 0})
                self.assertTrue(final['finished'])
                self.assertIsNone(final['question'])
                self.assertEqual(final['correct'], 1)
                self.assertEqual(final['answered'], 1)
                self.assertEqual(len(final['results']), 1)
                self.assertEqual(final['results'][0]['id'], problem_id)
                self.assertTrue(final['results'][0]['correct'])
                self.assertFalse(final['results'][0]['unanswered'])
                checked += 1
        self.assertEqual(checked, sum(len(families) for module in COURSE_MODULES
                                      for families in module.FAMILIES.values()))
        self.assertGreaterEqual(checked, 150)
        self.assertLessEqual({'number', 'expression', 'choice', 'sequence', 'pair', 'data_plot'}, formats)

    def test_malformed_expression_http_400_does_not_record_an_attempt(self):
        checked = 0
        for module, topic, family, seed in family_cases():
            question = generate(topic, seed)
            response = question.get('response', {})
            if response.get('kind') != 'expression':
                continue
            with self.subTest(topic=topic, family=family.__name__):
                problem_id = f'{topic}:{seed}'
                state = self.call('/api/sessions', {'mode': 'practice', 'count': 1, 'problemId': problem_id})
                session_path = '/api/sessions/'+state['id']
                before = self.stored_body(state['id'])
                variable = response['variables'][0]
                for invalid in ('(', variable+'+', f'1/({variable}-{variable})', "__import__('os')"):
                    with self.subTest(invalid=invalid):
                        error = self.call(session_path+'/answer', {'index': 0, 'answer': invalid}, status=400)
                        self.assertTrue(error.get('error'))
                        self.assertEqual(self.stored_body(state['id']), before)
                        resumed = self.call(session_path)
                        self.assert_public_unanswered(resumed, problem_id)
                        self.assertEqual(json.loads(self.stored_body(state['id']))['outcomes'], {})
                # Parsing errors must not consume the question or prevent a later valid response.
                corrected = self.call(session_path+'/answer', {'index': 0, 'answer': question['answer']})
                self.assertTrue(corrected['feedback']['correct'])
                self.assertEqual(corrected['answered'], 1)
                checked += 1
        self.assertGreaterEqual(checked, 10)

    def test_head_and_get_are_read_only_for_an_unanswered_session(self):
        question = next((topic, seed) for _, topic, _, seed in family_cases()
                        if generate(topic, seed).get('response', {}).get('kind') == 'expression')
        topic, seed = question
        problem_id = f'{topic}:{seed}'
        state = self.call('/api/sessions', {'mode': 'practice', 'count': 1, 'problemId': problem_id})
        session_path = '/api/sessions/'+state['id']
        before = self.stored_body(state['id'])
        self.call(session_path, method='HEAD')
        self.assertEqual(self.stored_body(state['id']), before)
        self.assert_public_unanswered(self.call(session_path), problem_id)
        self.assertEqual(self.stored_body(state['id']), before)


if __name__ == '__main__':
    unittest.main()
