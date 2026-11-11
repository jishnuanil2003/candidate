import json
import logging
from unittest.mock import patch, call
from urllib.error import HTTPError, URLError

from django.test import RequestFactory, SimpleTestCase

from . import dmcore
from .questions import QUESTION_LOOKUP, NO_QUESTIONS_MESSAGE, build_dmcore_playlist, get_dmcore_active_questions
from .views import complete_application, get_question, index, interview, submit_answer


class SessionDict(dict):
    modified = False
    session_key = 'test-session'

    def cycle_key(self):
        self.session_key = 'cycled-session'


class JsonResponseStub:
    status = 200

    def __init__(self, payload, status=200):
        self.status = status
        self.body = json.dumps(payload).encode()

    def read(self):
        return self.body

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None


class DmcoreClientTests(SimpleTestCase):
    def test_session_success_and_headers(self):
        response = JsonResponseStub({'candidate': {'name': 'Test'}, 'questions': [{'question_id': 4}]})
        with patch.dict('os.environ', {'DMCORE_BASE_URL': 'http://dmcore.test', 'DMCORE_API_KEY': 'test-key'}), \
             patch('screening.dmcore.urlopen', return_value=response) as opened:
            result = dmcore.load_session('test-token')
            self.assertEqual(result, {'candidate': {'name': 'Test'}, 'questions': [{'question_id': 4}]})
            req = opened.call_args.args[0]
            self.assertEqual(req.get_header('X-api-key'), 'test-key')
            self.assertEqual(req.get_header('X-interview-token'), 'test-token')
            self.assertEqual(opened.call_args.kwargs['timeout'], 10)

    def test_save_answer_payload_and_truncation(self):
        response = JsonResponseStub({'success': True})
        with patch.dict('os.environ', {'DMCORE_BASE_URL': 'http://dmcore.test', 'DMCORE_API_KEY': 'test-key'}), \
             patch('screening.dmcore.urlopen', return_value=response) as opened:
            result = dmcore.save_answer('test-token', 4, 'Software Engineer' + 'x' * 900)
            self.assertTrue(result['success'])
            req = opened.call_args.args[0]
            self.assertEqual(req.get_header('X-api-key'), 'test-key')
            self.assertEqual(req.get_header('X-interview-token'), 'test-token')
            data = json.loads(req.data.decode('utf-8'))
            self.assertEqual(data['token'], 'test-token')
            self.assertEqual(len(data['answers']), 1)
            self.assertEqual(data['answers'][0]['question_id'], 4)
            self.assertEqual(len(data['answers'][0]['answer']), 855)

    def test_missing_config_raises_error(self):
        with patch.dict('os.environ', {'DMCORE_BASE_URL': '', 'DMCORE_API_KEY': ''}):
            self.assertFalse(dmcore.validate_configuration())
            with self.assertRaises(dmcore.DmcoreError) as ctx:
                dmcore.load_session('token')
            self.assertEqual(ctx.exception.kind, 'configuration')

    def test_401_403_logs_key_rejected(self):
        for code in (401, 403):
            with patch.dict('os.environ', {'DMCORE_BASE_URL': 'http://dmcore.test', 'DMCORE_API_KEY': 'bad-key'}), \
                 patch('screening.dmcore.urlopen', side_effect=HTTPError('http://dmcore.test', code, 'Forbidden', {}, None)), \
                 self.assertLogs('screening.dmcore', level='ERROR') as cm:
                with self.assertRaises(dmcore.DmcoreError) as ctx:
                    dmcore.load_session('token')
                self.assertEqual(ctx.exception.status, code)
                self.assertTrue(any('key rejected' in msg for msg in cm.output))
                # Ensure api key is not logged
                self.assertFalse(any('bad-key' in msg for msg in cm.output))

    def test_timeout_and_unreachable_errors(self):
        with patch.dict('os.environ', {'DMCORE_BASE_URL': 'http://dmcore.test', 'DMCORE_API_KEY': 'key'}), \
             patch('screening.dmcore.urlopen', side_effect=TimeoutError('timeout')), \
             self.assertLogs('screening.dmcore', level='ERROR') as cm:
            with self.assertRaises(dmcore.DmcoreError) as ctx:
                dmcore.load_session('token')
            self.assertEqual(ctx.exception.kind, 'timeout')
            self.assertTrue(any('timed out' in msg for msg in cm.output))

        with patch.dict('os.environ', {'DMCORE_BASE_URL': 'http://dmcore.test', 'DMCORE_API_KEY': 'key'}), \
             patch('screening.dmcore.urlopen', side_effect=URLError('unreachable')), \
             self.assertLogs('screening.dmcore', level='ERROR') as cm:
            with self.assertRaises(dmcore.DmcoreError) as ctx:
                dmcore.load_session('token')
            self.assertEqual(ctx.exception.kind, 'connection')
            self.assertTrue(any('unreachable' in msg for msg in cm.output))


class DmcoreFlowTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def request(self, view, path, data=None, session=None):
        request = self.factory.post(path, data=json.dumps(data or {}), content_type='application/json')
        session_store = SessionDict(session or {})
        request.session = session_store
        response = view(request)
        if session is not None:
            session.clear()
            session.update(session_store)
        return response

    @patch('screening.views.load_session')
    def test_session_response_with_ids_4_and_15_plays_only_those_two_in_order(self, mock_load):
        mock_load.return_value = {
            'candidate': {'name': 'Alex'},
            'questions': [{'question_id': 4}, {'question_id': 15}]
        }
        req = self.factory.get('/?token=test-token')
        req.session = SessionDict()
        resp = index(req)
        self.assertIn(resp.status_code, (200, 302))
        playlist = req.session.get('dmcore_play_list', [])
        self.assertEqual([item['question_id'] for item in playlist], [4, 15])

        session = req.session
        q1_resp = self.request(get_question, '/api/question/', {}, session)
        q1_data = json.loads(q1_resp.content)
        self.assertEqual(q1_data['question']['id'], 4)
        self.assertEqual(q1_data['question']['number'], 1)
        self.assertEqual(q1_data['question']['total'], 2)

        with patch('screening.views.save_answer', return_value={'success': True}):
            ans1_resp = self.request(submit_answer, '/api/answer/', {'question_id': 4, 'value': 'Software Engineer'}, session)
        self.assertTrue(json.loads(ans1_resp.content)['valid'])
        self.assertFalse(json.loads(ans1_resp.content)['done'])

        q2_resp = self.request(get_question, '/api/question/', {}, session)
        q2_data = json.loads(q2_resp.content)
        self.assertEqual(q2_data['question']['id'], 15)
        self.assertEqual(q2_data['question']['number'], 2)
        self.assertEqual(q2_data['question']['total'], 2)

        with patch('screening.views.save_answer', return_value={'success': True}):
            ans2_resp = self.request(submit_answer, '/api/answer/', {'question_id': 15, 'value': 'Immediate joiner'}, session)
        self.assertTrue(json.loads(ans2_resp.content)['valid'])
        self.assertTrue(json.loads(ans2_resp.content)['done'])

    @patch('screening.views.load_session')
    def test_empty_questions_shows_fallback_message(self, mock_load):
        mock_load.return_value = {'candidate': {'name': 'Alex'}, 'questions': []}
        req = self.factory.get('/?token=test-token')
        req.session = SessionDict()
        resp = index(req)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'No interview questions are available right now, please contact the recruiter')

    @patch('screening.views.load_session')
    def test_fresher_answer_skips_11(self, mock_load):
        mock_load.return_value = {
            'candidate': {'name': 'Alex'},
            'questions': [{'question_id': 10}, {'question_id': 11}]
        }
        req = self.factory.get('/?token=test-token')
        req.session = SessionDict()
        index(req)
        session = req.session

        with patch('screening.views.save_answer', return_value={'success': True}):
            ans_resp = self.request(submit_answer, '/api/answer/', {'question_id': 10, 'value': 'No, I am a fresher'}, session)
        ans_data = json.loads(ans_resp.content)
        self.assertTrue(ans_data['valid'])
        self.assertTrue(ans_data['done'])

        next_q = json.loads(self.request(get_question, '/api/question/', {}, session).content)
        self.assertTrue(next_q['done'])

    @patch('screening.views.load_session')
    def test_without_10_plays_11_to_13_as_sent(self, mock_load):
        mock_load.return_value = {
            'candidate': {'name': 'Alex'},
            'questions': [{'question_id': 11}, {'question_id': 12}, {'question_id': 13}]
        }
        req = self.factory.get('/?token=test-token')
        req.session = SessionDict()
        index(req)
        session = req.session

        active_qs = get_dmcore_active_questions(session['dmcore_play_list'], session['answers'])
        self.assertEqual([q['id'] for q in active_qs], [11, 12, 13])

    def test_each_answered_question_sends_one_request_with_single_item_answers_list(self):
        session = {
            'token_interview': True,
            'dmcore_token': 'my-token',
            'dmcore_play_list': [{'question_id': 4}, {'question_id': 15}],
            'unsaved_answers': [],
            'answers': {},
            'q_index': 0,
        }
        with patch('screening.views.save_answer', return_value={'success': True}) as mock_save:
            self.request(submit_answer, '/api/answer/', {'question_id': 4, 'value': 'Software Engineer'}, session)
            mock_save.assert_called_once_with('my-token', 4, 'Software Engineer')

            mock_save.reset_mock()
            self.request(submit_answer, '/api/answer/', {'question_id': 15, 'value': '2 weeks'}, session)
            mock_save.assert_called_once_with('my-token', 15, '2 weeks')

    def test_optional_question_skipped_sends_nothing(self):
        session = {
            'token_interview': True,
            'dmcore_token': 'my-token',
            'dmcore_play_list': [{'question_id': 17}],
            'unsaved_answers': [],
            'answers': {},
            'q_index': 0,
        }
        with patch('screening.views.save_answer') as mock_save:
            resp = self.request(submit_answer, '/api/answer/', {'question_id': 17, 'value': ''}, session)
            self.assertTrue(json.loads(resp.content)['valid'])
            mock_save.assert_not_called()

    def test_failed_save_retried_once_kept_in_memory_and_retried_at_end(self):
        session = {
            'token_interview': True,
            'dmcore_token': 'my-token',
            'dmcore_play_list': [{'question_id': 4}],
            'unsaved_answers': [],
            'answers': {},
            'q_index': 0,
        }
        with patch('screening.views.save_answer', side_effect=dmcore.DmcoreError('server error', 500)) as mock_save:
            resp = self.request(submit_answer, '/api/answer/', {'question_id': 4, 'value': 'Software Engineer'}, session)
            self.assertEqual(mock_save.call_count, 2)
            self.assertTrue(json.loads(resp.content)['valid'])
            self.assertEqual(len(session['unsaved_answers']), 1)
            self.assertEqual(session['unsaved_answers'][0], {'question_id': 4, 'answer': 'Software Engineer'})

        with patch('screening.views.save_answer', return_value={'success': True}) as mock_save, \
             patch('screening.views.dmcore_complete_interview', return_value={'success': True}) as mock_complete:
            comp_resp = self.request(complete_application, '/api/complete/', {}, session)
            self.assertEqual(comp_resp.status_code, 200)
            mock_save.assert_called_once_with('my-token', 4, 'Software Engineer')
            mock_complete.assert_called_once_with('my-token')
            self.assertEqual(session['unsaved_answers'], [])

    def test_400_for_unknown_question_continues(self):
        session = {
            'token_interview': True,
            'dmcore_token': 'my-token',
            'dmcore_play_list': [{'question_id': 4}],
            'unsaved_answers': [],
            'answers': {},
            'q_index': 0,
        }
        with patch('screening.views.save_answer', side_effect=dmcore.DmcoreError('bad request', 400)) as mock_save, \
             self.assertLogs('screening.views', level='WARNING') as cm:
            resp = self.request(submit_answer, '/api/answer/', {'question_id': 4, 'value': 'Software Engineer'}, session)
            self.assertEqual(mock_save.call_count, 1)
            self.assertTrue(json.loads(resp.content)['valid'])
            self.assertEqual(session['unsaved_answers'], [])
            self.assertTrue(any('DMCore returned 400' in msg for msg in cm.output))

    def test_unknown_question_id_logged_and_skipped(self):
        with self.assertLogs('screening.questions', level='WARNING') as cm:
            playlist = build_dmcore_playlist([{'question_id': 4}, {'question_id': 999}, {'question_id': 15}])
            self.assertEqual([item['question_id'] for item in playlist], [4, 15])
            self.assertTrue(any('unknown question_id=999' in msg for msg in cm.output))
