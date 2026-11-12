import json
import logging
from unittest.mock import patch

from django.test import RequestFactory, SimpleTestCase, override_settings
from django.http import HttpResponse

from .media import resolve_question_media, serve_interview_media
from .questions import QUESTION_LOOKUP, build_dmcore_playlist, get_dmcore_active_questions, FRESHER_ANSWER
from .translations import map_option_to_canonical_english, TRANSLATIONS
from .views import index, select_language, interview, get_question, submit_answer


class TestSession(dict):
    session_key = 'multilingual-test-session'
    modified = False

    def cycle_key(self):
        pass

    def create(self):
        pass


@override_settings(ENABLED_INTERVIEW_LANGUAGES=['en', 'ml', 'hi', 'ta', 'te'])
class MultilingualFlowTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()

    @patch('screening.views.load_session')
    def test_link_without_chosen_language_shows_landing_page(self, mock_load):
        mock_load.return_value = {
            'candidate': {'name': 'Jishnu'},
            'questions': [{'question_id': 1}, {'question_id': 2}]
        }
        session = TestSession()
        req = self.factory.get('/?token=sample-token')
        req.session = session

        response = index(req)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Choose Your Language')
        self.assertContains(response, 'Jishnu')
        self.assertContains(response, 'മലയാളം')
        self.assertContains(response, 'हिन्दी')
        self.assertContains(response, 'தமிழ்')
        self.assertContains(response, 'తెలుగు')
        self.assertEqual(session.get('candidate_name'), 'Jishnu')
        self.assertEqual([q['question_id'] for q in session.get('dmcore_play_list', [])], [1, 2])

    def test_select_language_saves_to_session_and_redirects(self):
        session = TestSession()
        session['token_interview'] = True
        session['answers'] = {}

        req = self.factory.post('/select-language/', {'lang': 'ml'})
        req.session = session

        response = select_language(req)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], '/interview/')
        self.assertEqual(session.get('interview_language'), 'ml')
        self.assertEqual(session.get('language'), 'ml')

    @patch('screening.views.load_session')
    def test_reopening_link_with_saved_language_skips_landing_page(self, mock_load):
        mock_load.return_value = {
            'candidate': {'name': 'Jishnu'},
            'questions': [{'question_id': 1}]
        }
        session = TestSession()
        session['token_interview'] = True
        session['dmcore_token'] = 'sample-token'
        session['dmcore_play_list'] = [{'question_id': 1, 'field_key': 'full_name'}]
        session['interview_language'] = 'hi'

        req = self.factory.get('/?token=sample-token')
        req.session = session

        response = index(req)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], '/interview/')

    def test_invalid_language_is_rejected_server_side(self):
        session = TestSession()
        session['token_interview'] = True
        session['answers'] = {}

        req = self.factory.post('/select-language/', {'lang': 'fr'})
        req.session = session

        response = select_language(req)
        self.assertEqual(response.status_code, 400)
        self.assertIn(b'Invalid language selected', response.content)

    def test_language_cannot_be_changed_after_first_answer(self):
        session = TestSession()
        session['token_interview'] = True
        session['interview_language'] = 'en'
        session['answers'] = {1: 'Priya Sharma'}  # Question 1 already answered

        req = self.factory.post('/select-language/', {'lang': 'ml'})
        req.session = session

        response = select_language(req)
        self.assertEqual(response.status_code, 400)
        self.assertIn(b'Language cannot be changed', response.content)
        self.assertEqual(session.get('interview_language'), 'en')

    def test_media_resolver_and_fallback_warning(self):
        # English video exists
        en_res = resolve_question_media('english', 1)
        self.assertEqual(en_res['url'].split('?')[0], '/media/interview/english/q1.mp4')
        self.assertFalse(en_res['is_fallback'])

        # Malayalam video does not exist yet -> falls back to english with warning
        with self.assertLogs('screening.media', level='WARNING') as cm:
            ml_res = resolve_question_media('malayalam', 1)
            self.assertEqual(ml_res['url'].split('?')[0], '/media/interview/english/q1.mp4')
            self.assertTrue(ml_res['is_fallback'])
            self.assertIn('Missing video for language=malayalam, question_id=1. Falling back to english.', cm.output[0])

    def test_serve_media_path_traversal_rejection(self):
        req = self.factory.get('/media/interview/english/../../settings.py')
        res = serve_interview_media(req, 'english', '../../settings.py')
        self.assertEqual(res.status_code, 400)

        res2 = serve_interview_media(req, 'unsupported_lang', 'q1.mp4')
        self.assertEqual(res2.status_code, 400)

    def test_serve_media_http_range_206_response(self):
        url = resolve_question_media('english', 1)['url']
        req = self.factory.get(url, HTTP_RANGE='bytes=0-100')
        res = serve_interview_media(req, 'english', 'q1.mp4')

        self.assertEqual(res.status_code, 206)
        self.assertTrue(res.has_header('Content-Range'))
        self.assertTrue(res['Content-Range'].startswith('bytes 0-100/'))
        self.assertEqual(res['Content-Length'], '101')
        self.assertEqual(res['Accept-Ranges'], 'bytes')
        self.assertIn('max-age=31536000', res['Cache-Control'])

    def test_serve_media_full_response_headers(self):
        url = resolve_question_media('english', 1)['url']
        req = self.factory.get(url)
        res = serve_interview_media(req, 'english', 'q1.mp4')

        self.assertEqual(res.status_code, 200)
        self.assertEqual(res['Accept-Ranges'], 'bytes')
        self.assertIn('max-age=31536000', res['Cache-Control'])

    def test_option_mapping_to_canonical_english_all_languages(self):
        # Question 10 (experience vs fresher)
        self.assertEqual(map_option_to_canonical_english(10, 'അതെ, എനിക്ക് പരിചയമുണ്ട്', 'ml'), 'Yes, I have experience')
        self.assertEqual(map_option_to_canonical_english(10, 'ഇല്ല, ഞാൻ ഒരു തുടക്കക്കാരനാണ്', 'ml'), 'No, I am a fresher')

        self.assertEqual(map_option_to_canonical_english(10, 'हाँ, मेरे पास अनुभव है', 'hi'), 'Yes, I have experience')
        self.assertEqual(map_option_to_canonical_english(10, 'नहीं, मैं एक फ्रेशर हूँ', 'hi'), 'No, I am a fresher')

        self.assertEqual(map_option_to_canonical_english(10, 'ஆம், எனக்கு அனுபவம் உள்ளது', 'ta'), 'Yes, I have experience')
        self.assertEqual(map_option_to_canonical_english(10, 'இல்லை, நான் புதியவர் (Fresher)', 'ta'), 'No, I am a fresher')

        self.assertEqual(map_option_to_canonical_english(10, 'అవును, నాకు అనుభవం ఉంది', 'te'), 'Yes, I have experience')
        self.assertEqual(map_option_to_canonical_english(10, 'లేదు, నేను ఫ్రెషర్‌ని', 'te'), 'No, I am a fresher')

        # Question 5 (qualification)
        self.assertEqual(map_option_to_canonical_english(5, 'ബാച്ചിലേഴ്സ് ബിരുദം', 'ml'), "Bachelor's Degree")
        self.assertEqual(map_option_to_canonical_english(5, "स्नातक डिग्री (Bachelor's)", 'hi'), "Bachelor's Degree")
        self.assertEqual(map_option_to_canonical_english(5, "பட்டப்படிப்பு (Bachelor's)", 'ta'), "Bachelor's Degree")
        self.assertEqual(map_option_to_canonical_english(5, 'బ్యాచిలర్ డిగ్రీ', 'te'), "Bachelor's Degree")

        # Question 15 (notice period)
        self.assertEqual(map_option_to_canonical_english(15, 'ഉടൻ തന്നെ ചേരാം', 'ml'), 'Immediate joiner')
        self.assertEqual(map_option_to_canonical_english(15, 'तुरंत शामिल हो सकते हैं', 'hi'), 'Immediate joiner')
        self.assertEqual(map_option_to_canonical_english(15, 'உடனடியாக சேரக்கூடியவர்', 'ta'), 'Immediate joiner')
        self.assertEqual(map_option_to_canonical_english(15, 'వెంటనే చేరగలరు', 'te'), 'Immediate joiner')

        # Question 16 (salary)
        self.assertEqual(map_option_to_canonical_english(16, '₹3-5 ലക്ഷം', 'ml'), '3-5 LPA')
        self.assertEqual(map_option_to_canonical_english(16, '₹3-5 लाख प्रति वर्ष', 'hi'), '3-5 LPA')

    def test_fresher_skip_rule_works_with_regional_language_answers(self):
        playlist = [
            {'question_id': 10, 'field_key': 'has_experience'},
            {'question_id': 11, 'field_key': 'last_company'},
            {'question_id': 12, 'field_key': 'last_role'},
            {'question_id': 13, 'field_key': 'experience_duration'},
            {'question_id': 14, 'field_key': 'skills'}
        ]

        # In Malayalam: candidate answered with Malayalam fresher option
        canonical_answer = map_option_to_canonical_english(10, 'ഇല്ല, ഞാൻ ഒരു തുടക്കക്കാരനാണ്', 'ml')
        answers = {'has_experience': canonical_answer}

        active = get_dmcore_active_questions(playlist, answers)
        active_ids = [q['id'] for q in active]
        # Questions 11, 12, 13 must be skipped!
        self.assertEqual(active_ids, [10, 14])

    def test_playlist_is_identical_in_order_and_ids_regardless_of_language(self):
        dmcore_input = [
            {'question_id': 4, 'field_key': 'role_applied'},
            {'question_id': 10, 'field_key': 'has_experience'},
            {'question_id': 16, 'field_key': 'expected_salary'},
        ]
        pl_en = build_dmcore_playlist(dmcore_input)
        pl_ml = build_dmcore_playlist(dmcore_input)
        pl_hi = build_dmcore_playlist(dmcore_input)
        pl_ta = build_dmcore_playlist(dmcore_input)
        pl_te = build_dmcore_playlist(dmcore_input)

        expected = [
            {'question_id': 4, 'field_key': 'role_applied'},
            {'question_id': 10, 'field_key': 'has_experience'},
            {'question_id': 16, 'field_key': 'expected_salary'},
        ]
        self.assertEqual(pl_en, expected)
        self.assertEqual(pl_ml, expected)
        self.assertEqual(pl_hi, expected)
        self.assertEqual(pl_ta, expected)
        self.assertEqual(pl_te, expected)
