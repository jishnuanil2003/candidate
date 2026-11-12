import json
from unittest.mock import patch

from django.test import RequestFactory, SimpleTestCase

from .questions import (
    FRESHER_ANSWER,
    NO_QUESTIONS_MESSAGE,
    QUESTION_LOOKUP,
    build_dmcore_playlist,
    get_dmcore_active_questions,
)
from .views import get_question, index


class TestSession(dict):
    session_key = 'question-flow-test'
    modified = False

    def cycle_key(self):
        pass

    def create(self):
        pass


class DmcoreQuestionFlowTests(SimpleTestCase):
    @patch('screening.views.load_session', return_value={
        'candidate': {'name': 'Test Candidate'},
        'questions': [
            {'question_id': 4, 'field_key': 'role_applied'},
            {'question_id': 15, 'field_key': 'notice_period'},
        ],
    })
    def test_only_requested_ids_play_in_dmcore_order(self, _load_session):
        session = TestSession()
        session['interview_language'] = 'en'
        entry = RequestFactory().get('/?token=test-token')
        entry.session = session
        self.assertEqual(index(entry).status_code, 302)

        first = RequestFactory().post('/api/question/')
        first.session = session
        first_question = json.loads(get_question(first).content)['question']
        self.assertEqual(first_question['id'], 4)
        self.assertTrue(first_question['question_video'].split('?')[0].endswith(('q4.mp4', 'q_role.mp4')))
        self.assertTrue(first_question['next_question_video'].split('?')[0].endswith(('q15.mp4', 'q_notice.mp4')))

        session['q_index'] = 1
        second = RequestFactory().post('/api/question/')
        second.session = session
        second_question = json.loads(get_question(second).content)['question']
        self.assertEqual(second_question['id'], 15)
        self.assertTrue(second_question['question_video'].split('?')[0].endswith(('q15.mp4', 'q_notice.mp4')))
        self.assertIsNone(second_question['next_question_video'])

    def test_empty_questions_keep_exact_fallback_message(self):
        playlist = build_dmcore_playlist([])
        self.assertEqual(playlist, [])
        self.assertEqual(NO_QUESTIONS_MESSAGE, 'No interview questions are available right now, please contact the recruiter')

    def test_fresher_answer_skips_company_role_and_duration(self):
        playlist = build_dmcore_playlist([
            {'question_id': 10, 'field_key': 'has_experience'},
            {'question_id': 11, 'field_key': 'last_company'},
        ])
        active = get_dmcore_active_questions(playlist, {'has_experience': FRESHER_ANSWER})
        self.assertEqual([question['id'] for question in active], [10])

    def test_experience_details_stay_when_question_10_was_not_sent(self):
        playlist = build_dmcore_playlist([
            {'question_id': 11, 'field_key': 'last_company'},
            {'question_id': 12, 'field_key': 'last_role'},
            {'question_id': 13, 'field_key': 'experience_duration'},
        ])
        active = get_dmcore_active_questions(playlist, {'has_experience': FRESHER_ANSWER})
        self.assertEqual([question['id'] for question in active], [11, 12, 13])
