import json
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

from django.test import RequestFactory, SimpleTestCase
from django.conf import settings

from .questions import (
    QUESTION_LOOKUP,
    QUESTIONS,
    build_dmcore_playlist,
    get_dmcore_active_questions,
    validate_answer,
    validate_lead_source,
    validate_location,
    validate_internship_done,
    validate_internship_start_date,
    validate_internship_end_date,
    validate_internship_topic,
    parse_month_year,
)
from .media import resolve_question_media, resolve_error_media, serve_interview_media
from .views import submit_answer, get_question
from .translations import map_option_to_canonical_english


class TestSession(dict):
    session_key = 'test-session-key'
    modified = False

    def cycle_key(self):
        pass

    def create(self):
        pass


class NewQuestionsValidatorTests(SimpleTestCase):
    """Test validation rules for questions 19 to 24."""

    def test_q19_lead_source_valid_and_invalid(self):
        # Canonical keyword categories
        self.assertEqual(validate_lead_source("A friend referred me")[1], "Friend/Referral")
        self.assertEqual(validate_lead_source("My colleague at work")[1], "Friend/Referral")
        self.assertEqual(validate_lead_source("Saw a post on LinkedIn")[1], "Social Media")
        self.assertEqual(validate_lead_source("Instagram reels")[1], "Social Media")
        self.assertEqual(validate_lead_source("College campus placement cell")[1], "College/Campus")
        self.assertEqual(validate_lead_source("University job board")[1], "College/Campus")
        # Canonical Job Portal category
        self.assertEqual(validate_lead_source("Naukri.com job portal")[1], "Job Portal")
        self.assertEqual(validate_lead_source("Found it on Indeed")[1], "Job Portal")
        self.assertEqual(validate_lead_source("Applied via LinkedIn Jobs")[1], "Job Portal")
        self.assertEqual(validate_lead_source("Internshala listing")[1], "Job Portal")
        # Meaningful other
        self.assertEqual(validate_lead_source("Billboard ad on the highway")[1], "Other: Billboard ad on the highway")
        self.assertEqual(validate_lead_source("Other: Newspaper ad")[1], "Other: Newspaper ad")

        # Invalid and empty reasons
        res_empty = validate_lead_source("")
        self.assertFalse(res_empty[0])
        self.assertEqual(getattr(res_empty, 'reason'), 'empty')
        res_filler = validate_lead_source("um uh hmm")
        self.assertFalse(res_filler[0])
        self.assertEqual(getattr(res_filler, 'reason'), 'empty')

        res_num = validate_lead_source("123456")
        self.assertFalse(res_num[0])
        self.assertEqual(getattr(res_num, 'reason'), 'invalid')
        res_short = validate_lead_source("a")
        self.assertFalse(res_short[0])
        self.assertEqual(getattr(res_short, 'reason'), 'invalid')

    def test_q20_location_valid_and_invalid(self):
        # Valid locations: 2-60 chars, mostly letters
        self.assertTrue(validate_location("Bengaluru")[0])
        self.assertTrue(validate_location("New Delhi")[0])
        self.assertTrue(validate_location("Kochi, Kerala")[0])
        self.assertEqual(validate_location("Bengaluru")[1], "Bengaluru")

        # Invalid cases: numbers, phone number, too short, too long, symbols only
        self.assertFalse(validate_location("")[0])
        self.assertFalse(validate_location("A")[0])
        self.assertFalse(validate_location("9876543210")[0])
        self.assertFalse(validate_location("+91 9876543210")[0])
        self.assertFalse(validate_location("12345")[0])
        self.assertFalse(validate_location("A" * 65)[0])
        self.assertFalse(validate_location("---...###")[0])

    def test_q21_internship_done_synonyms_all_languages(self):
        # English
        self.assertEqual(validate_internship_done("Yes")[1], "Yes")
        self.assertEqual(validate_internship_done("yes, I have")[1], "Yes")
        self.assertEqual(validate_internship_done("yeah")[1], "Yes")
        self.assertEqual(validate_internship_done("No")[1], "No")
        self.assertEqual(validate_internship_done("nope")[1], "No")
        self.assertEqual(validate_internship_done("fresher")[1], "No")

        # Regional language synonyms
        self.assertEqual(validate_internship_done("हाँ")[1], "Yes")
        self.assertEqual(validate_internship_done("नहीं")[1], "No")
        self.assertEqual(validate_internship_done("അതെ")[1], "Yes")
        self.assertEqual(validate_internship_done("ഇല്ല")[1], "No")
        self.assertEqual(validate_internship_done("ஆம்")[1], "Yes")
        self.assertEqual(validate_internship_done("இல்லை")[1], "No")
        self.assertEqual(validate_internship_done("అవును")[1], "Yes")
        self.assertEqual(validate_internship_done("లేదు")[1], "No")

        # Invalid answers
        self.assertFalse(validate_internship_done("maybe")[0])
        self.assertFalse(validate_internship_done("")[0])
        self.assertFalse(validate_internship_done("random text")[0])

    def test_q22_internship_start_date_multilingual_and_limits(self):
        # Standard English dates
        valid, val = validate_internship_start_date("June 2025")
        self.assertTrue(valid)
        self.assertEqual(val, "June 2025")

        valid, val = validate_internship_start_date("06/2025")
        self.assertTrue(valid)
        self.assertEqual(val, "June 2025")

        valid, val = validate_internship_start_date("6 2025")
        self.assertTrue(valid)
        self.assertEqual(val, "June 2025")

        # Regional month names (post-transcription / translation)
        self.assertTrue(validate_internship_start_date("जून 2025")[0])
        self.assertEqual(validate_internship_start_date("जून 2025")[1], "June 2025")
        self.assertTrue(validate_internship_start_date("ജൂൺ 2024")[0])
        self.assertEqual(validate_internship_start_date("ജൂൺ 2024")[1], "June 2024")
        self.assertTrue(validate_internship_start_date("ஜூன் 2023")[0])
        self.assertEqual(validate_internship_start_date("ஜூன் 2023")[1], "June 2023")
        self.assertTrue(validate_internship_start_date("జూన్ 2022")[0])
        self.assertEqual(validate_internship_start_date("జూన్ 2022")[1], "June 2022")

        # Invalid cases: year < 2000, future dates, invalid month
        self.assertFalse(validate_internship_start_date("June 1998")[0])  # < 2000
        self.assertFalse(validate_internship_start_date("December 2026")[0])  # Future (current month 11/2026)
        self.assertFalse(validate_internship_start_date("June 2035")[0])  # Far future
        self.assertFalse(validate_internship_start_date("invalid date")[0])

    def test_q23_internship_end_date_ongoing_and_comparison(self):
        # Ongoing in various forms
        self.assertEqual(validate_internship_end_date("Ongoing")[1], "Ongoing")
        self.assertEqual(validate_internship_end_date("still going on")[1], "Ongoing")
        self.assertEqual(validate_internship_end_date("currently")[1], "Ongoing")
        self.assertEqual(validate_internship_end_date("present")[1], "Ongoing")
        self.assertEqual(validate_internship_end_date("चल रहा है")[1], "Ongoing")
        self.assertEqual(validate_internship_end_date("തുടരുന്നു")[1], "Ongoing")

        # Valid date not earlier than start date
        answers = {'internship_start_date': 'June 2025'}
        valid, val = validate_internship_end_date("August 2025", answers=answers)
        self.assertTrue(valid)
        self.assertEqual(val, "August 2025")

        # End date earlier than start date returns reason='before_start'
        invalid_res = validate_internship_end_date("May 2025", answers=answers)
        self.assertFalse(invalid_res[0])
        self.assertEqual(getattr(invalid_res, 'reason'), 'before_start')
        self.assertIn("start date", invalid_res[1].lower())

        # Unreadable end date returns reason='invalid'
        unreadable_res = validate_internship_end_date("xyz 123", answers=answers)
        self.assertFalse(unreadable_res[0])
        self.assertEqual(getattr(unreadable_res, 'reason'), 'invalid')

        # Empty end date returns reason='empty'
        empty_res = validate_internship_end_date("", answers=answers)
        self.assertFalse(empty_res[0])
        self.assertEqual(getattr(empty_res, 'reason'), 'empty')

        # Same month/year is valid
        self.assertTrue(validate_internship_end_date("June 2025", answers=answers)[0])

    def test_q24_internship_topic_valid_and_invalid(self):
        # Valid topic (at least 8 chars with letters)
        self.assertTrue(validate_internship_topic("Backend API development in Django")[0])
        self.assertTrue(validate_internship_topic("Machine Learning for Healthcare")[0])
        self.assertTrue(validate_internship_topic("Robotics")[0])

        # Invalid: < 8 chars
        self.assertFalse(validate_internship_topic("Python")[0])
        self.assertFalse(validate_internship_topic("Django")[0])

        # Invalid: no letters (digits/symbols only)
        self.assertFalse(validate_internship_topic("1234567890")[0])

        # Invalid: repeated words (e.g. "python python python")
        self.assertFalse(validate_internship_topic("python python python")[0])
        self.assertFalse(validate_internship_topic("test test test test")[0])
        self.assertFalse(validate_internship_topic("work work work")[0])
        self.assertFalse(validate_internship_topic("asdasdasd")[0])


class ConditionalInternshipSkipTests(SimpleTestCase):
    """Test conditional skip rule for questions 22, 23, 24."""

    def test_skip_22_24_when_21_is_no(self):
        playlist = build_dmcore_playlist([
            {'question_id': 21, 'field_key': 'internship_done'},
            {'question_id': 22, 'field_key': 'internship_start_date'},
            {'question_id': 23, 'field_key': 'internship_end_date'},
            {'question_id': 24, 'field_key': 'internship_topic'},
        ])
        active = get_dmcore_active_questions(playlist, {'internship_done': 'No'})
        self.assertEqual([q['id'] for q in active], [21])

    def test_include_22_24_when_21_is_yes(self):
        playlist = build_dmcore_playlist([
            {'question_id': 21, 'field_key': 'internship_done'},
            {'question_id': 22, 'field_key': 'internship_start_date'},
            {'question_id': 23, 'field_key': 'internship_end_date'},
            {'question_id': 24, 'field_key': 'internship_topic'},
        ])
        active = get_dmcore_active_questions(playlist, {'internship_done': 'Yes'})
        self.assertEqual([q['id'] for q in active], [21, 22, 23, 24])

    def test_skip_22_24_from_regional_answer_mapped_to_canonical(self):
        canonical_no = map_option_to_canonical_english(21, 'नहीं', lang='hi')
        self.assertEqual(canonical_no, 'No')
        playlist = build_dmcore_playlist([
            {'question_id': 21, 'field_key': 'internship_done'},
            {'question_id': 22, 'field_key': 'internship_start_date'},
        ])
        active = get_dmcore_active_questions(playlist, {'internship_done': canonical_no})
        self.assertEqual([q['id'] for q in active], [21])

    def test_play_22_24_as_sent_when_21_not_in_playlist(self):
        playlist = build_dmcore_playlist([
            {'question_id': 22, 'field_key': 'internship_start_date'},
            {'question_id': 23, 'field_key': 'internship_end_date'},
            {'question_id': 24, 'field_key': 'internship_topic'},
        ])
        active = get_dmcore_active_questions(playlist, {'internship_done': 'No'})
        # Since 21 wasn't in playlist, 22-24 play as sent
        self.assertEqual([q['id'] for q in active], [22, 23, 24])

    def test_playlist_is_identical_for_all_languages(self):
        dmcore_raw = [
            {'question_id': 19, 'field_key': 'lead_source'},
            {'question_id': 20, 'field_key': 'location'},
            {'question_id': 21, 'field_key': 'internship_done'},
            {'question_id': 22, 'field_key': 'internship_start_date'},
        ]
        pl_en = build_dmcore_playlist(dmcore_raw)
        pl_hi = build_dmcore_playlist(dmcore_raw)
        pl_ml = build_dmcore_playlist(dmcore_raw)
        pl_ta = build_dmcore_playlist(dmcore_raw)
        pl_te = build_dmcore_playlist(dmcore_raw)
        self.assertEqual(pl_en, pl_hi)
        self.assertEqual(pl_en, pl_ml)
        self.assertEqual(pl_en, pl_ta)
        self.assertEqual(pl_en, pl_te)


class ErrorFlowAndAttemptsTests(SimpleTestCase):
    """Test 3-attempt failure mechanism, error payload, and canonical save."""

    def setUp(self):
        self.factory = RequestFactory()

    @patch('screening.views.save_answer')
    def test_invalid_answer_does_not_save_and_increments_attempts(self, mock_save):
        session = TestSession()
        session['token_interview'] = True
        session['dmcore_token'] = 'sample-token'
        session['dmcore_play_list'] = [{'question_id': 20, 'field_key': 'location'}]
        session['interview_language'] = 'en'
        session['answers'] = {}
        session['q_index'] = 0

        # Attempt 1: Invalid answer (digits only)
        req1 = self.factory.post('/api/answer/',
                                 json.dumps({'question_id': 20, 'value': '12345'}),
                                 content_type='application/json')
        req1.session = session
        resp1 = json.loads(submit_answer(req1).content)
        self.assertFalse(resp1['valid'])
        self.assertEqual(resp1['reason'], 'invalid')
        self.assertEqual(resp1['attempts_left'], 2)
        mock_save.assert_not_called()
        self.assertEqual(session['q_index'], 0)

        # Attempt 2: Another invalid answer
        req2 = self.factory.post('/api/answer/',
                                 json.dumps({'question_id': 20, 'value': '9876543210'}),
                                 content_type='application/json')
        req2.session = session
        resp2 = json.loads(submit_answer(req2).content)
        self.assertFalse(resp2['valid'])
        self.assertEqual(resp2['reason'], 'invalid')
        self.assertEqual(resp2['attempts_left'], 1)
        mock_save.assert_not_called()
        self.assertEqual(session['q_index'], 0)

        # Attempt 3: Third failure skips the question
        req3 = self.factory.post('/api/answer/',
                                 json.dumps({'question_id': 20, 'value': 'X'}),
                                 content_type='application/json')
        req3.session = session
        resp3 = json.loads(submit_answer(req3).content)
        self.assertFalse(resp3['valid'])
        self.assertEqual(resp3['reason'], 'invalid')
        self.assertTrue(resp3.get('skipped'))
        self.assertEqual(resp3['attempts_left'], 0)
        mock_save.assert_not_called()
        # Question was skipped, so q_index advanced to 1 and interview is done
        self.assertEqual(session['q_index'], 1)
        self.assertTrue(resp3['done'])

    @patch('screening.views.save_answer')
    def test_valid_answer_saves_canonical_value(self, mock_save):
        session = TestSession()
        session['token_interview'] = True
        session['dmcore_token'] = 'sample-token'
        session['dmcore_play_list'] = [{'question_id': 19, 'field_key': 'lead_source'}]
        session['interview_language'] = 'en'
        session['answers'] = {}
        session['q_index'] = 0

        req = self.factory.post('/api/answer/',
                                json.dumps({'question_id': 19, 'value': 'A friend recommended this'}),
                                content_type='application/json')
        req.session = session
        resp = json.loads(submit_answer(req).content)
        self.assertTrue(resp['valid'])
        # Canonical value Friend/Referral was saved to DMCore
        mock_save.assert_called_once_with('sample-token', 19, 'Friend/Referral')
        self.assertEqual(session['answers']['lead_source'], 'Friend/Referral')

    @patch('screening.views.save_answer')
    def test_empty_and_invalid_shared_counter(self, mock_save):
        session = TestSession()
        session['token_interview'] = True
        session['dmcore_token'] = 'sample-token'
        session['dmcore_play_list'] = [{'question_id': 20, 'field_key': 'location'}]
        session['interview_language'] = 'en'
        session['answers'] = {}
        session['q_index'] = 0

        # Attempt 1: Empty answer returns reason='empty'
        req1 = self.factory.post('/api/answer/',
                                 json.dumps({'question_id': 20, 'value': '   '}),
                                 content_type='application/json')
        req1.session = session
        resp1 = json.loads(submit_answer(req1).content)
        self.assertFalse(resp1['valid'])
        self.assertEqual(resp1['reason'], 'empty')
        self.assertEqual(resp1['attempts_left'], 2)
        self.assertEqual(resp1['error_text'], "I still need your current location. Which city or town do you live in?")

        # Attempt 2: Invalid answer returns reason='invalid'
        req2 = self.factory.post('/api/answer/',
                                 json.dumps({'question_id': 20, 'value': '12345'}),
                                 content_type='application/json')
        req2.session = session
        resp2 = json.loads(submit_answer(req2).content)
        self.assertFalse(resp2['valid'])
        self.assertEqual(resp2['reason'], 'invalid')
        self.assertEqual(resp2['attempts_left'], 1)
        self.assertEqual(resp2['error_text'], "I couldn't recognise that place. Could you tell me the name of your city or town again?")

        # Attempt 3: Filler word returns reason='empty' and triggers skip
        req3 = self.factory.post('/api/answer/',
                                 json.dumps({'question_id': 20, 'value': 'um uh'}),
                                 content_type='application/json')
        req3.session = session
        resp3 = json.loads(submit_answer(req3).content)
        self.assertFalse(resp3['valid'])
        self.assertEqual(resp3['reason'], 'empty')
        self.assertTrue(resp3.get('skipped'))
        self.assertEqual(resp3['attempts_left'], 0)
        mock_save.assert_not_called()
        self.assertEqual(session['q_index'], 1)

    @patch('screening.views.save_answer')
    def test_q23_before_start_reason(self, mock_save):
        session = TestSession()
        session['token_interview'] = True
        session['dmcore_token'] = 'sample-token'
        session['dmcore_play_list'] = [
            {'question_id': 22, 'field_key': 'internship_start_date'},
            {'question_id': 23, 'field_key': 'internship_end_date'}
        ]
        session['interview_language'] = 'en'
        session['answers'] = {'internship_start_date': 'June 2025'}
        session['q_index'] = 1

        # End date earlier than start date returns reason='before_start'
        req = self.factory.post('/api/answer/',
                                json.dumps({'question_id': 23, 'value': 'May 2025'}),
                                content_type='application/json')
        req.session = session
        resp = json.loads(submit_answer(req).content)
        self.assertFalse(resp['valid'])
        self.assertEqual(resp['reason'], 'before_start')
        self.assertEqual(resp['error_text'], "That end date seems to come before the start date. Could you check and tell me again? If it's still going on, just say so.")
        mock_save.assert_not_called()


class MediaHelperAndErrorVideoOrderTests(SimpleTestCase):
    """Test media helper whitelist, path traversal, error video lookup order, and fallbacks."""

    def setUp(self):
        self.factory = RequestFactory()

    def test_media_helper_accepts_q1_to_q24(self):
        req = self.factory.get('/media/interview/english/q1.mp4')
        res = serve_interview_media(req, 'english', 'q1.mp4')
        self.assertEqual(res.status_code, 200)

        # q24 is accepted by filename pattern (returns 404 because file not yet on disk, but NOT 400 bad request)
        req24 = self.factory.get('/media/interview/english/q24.mp4')
        try:
            res24 = serve_interview_media(req24, 'english', 'q24.mp4')
            self.assertEqual(res24.status_code, 404)
        except Exception as e:
            from django.http import Http404
            self.assertIsInstance(e, Http404)

    def test_media_helper_rejects_q25_and_traversals(self):
        # q25 is outside q1-q24 whitelist
        req = self.factory.get('/media/interview/english/q25.mp4')
        res = serve_interview_media(req, 'english', 'q25.mp4')
        self.assertEqual(res.status_code, 400)

        # Path traversal rejected
        req_trav = self.factory.get('/media/interview/english/../views.py')
        res_trav = serve_interview_media(req_trav, 'english', '../views.py')
        self.assertEqual(res_trav.status_code, 400)

        # Slashes rejected
        req_slash = self.factory.get('/media/interview/english/sub/q1.mp4')
        res_slash = serve_interview_media(req_slash, 'english', 'sub/q1.mp4')
        self.assertEqual(res_slash.status_code, 400)

    def test_media_helper_accepts_addendum_error_video_names(self):
        from .media import FILENAME_PATTERN
        self.assertTrue(FILENAME_PATTERN.match('lead_source_invalid.mp4'))
        self.assertTrue(FILENAME_PATTERN.match('lead_source_empty.mp4'))
        self.assertTrue(FILENAME_PATTERN.match('location_invalid.mp4'))
        self.assertTrue(FILENAME_PATTERN.match('location_empty.mp4'))
        self.assertTrue(FILENAME_PATTERN.match('internship_done_invalid.mp4'))
        self.assertTrue(FILENAME_PATTERN.match('internship_done_empty.mp4'))
        self.assertTrue(FILENAME_PATTERN.match('internship_start_date_invalid.mp4'))
        self.assertTrue(FILENAME_PATTERN.match('internship_start_date_empty.mp4'))
        self.assertTrue(FILENAME_PATTERN.match('internship_end_date_invalid.mp4'))
        self.assertTrue(FILENAME_PATTERN.match('internship_end_date_empty.mp4'))
        self.assertTrue(FILENAME_PATTERN.match('internship_end_date_before_start.mp4'))
        self.assertTrue(FILENAME_PATTERN.match('internship_topic_invalid.mp4'))
        self.assertTrue(FILENAME_PATTERN.match('internship_topic_empty.mp4'))

    def test_error_video_lookup_fallback_order_stages(self):
        import tempfile
        from django.test import override_settings

        with tempfile.TemporaryDirectory() as temp_dir:
            media_root = Path(temp_dir)
            hindi_dir = media_root / 'hindi'
            english_dir = media_root / 'english'
            hindi_dir.mkdir(parents=True)
            english_dir.mkdir(parents=True)

            with override_settings(INTERVIEW_MEDIA_ROOT=media_root):
                # Initial: No video exists -> returns None
                res = resolve_error_media('hi', 'lead_source', reason='invalid')
                self.assertIsNone(res)

                # Stage 4: English generic exists
                en_generic = english_dir / 'lead_source_error.mp4'
                en_generic.write_bytes(b'fake')
                res = resolve_error_media('hi', 'lead_source', reason='invalid')
                self.assertIsNotNone(res)
                self.assertIn('/media/interview/english/lead_source_error.mp4', res['url'])
                self.assertTrue(res['is_fallback'])

                # Stage 3: Hindi generic exists (preferred over English generic)
                hi_generic = hindi_dir / 'lead_source_error.mp4'
                hi_generic.write_bytes(b'fake')
                res = resolve_error_media('hi', 'lead_source', reason='invalid')
                self.assertIsNotNone(res)
                self.assertIn('/media/interview/hindi/lead_source_error.mp4', res['url'])
                self.assertFalse(res['is_fallback'])

                # Stage 2: English specific exists (preferred over Hindi generic)
                en_specific = english_dir / 'lead_source_invalid.mp4'
                en_specific.write_bytes(b'fake')
                res = resolve_error_media('hi', 'lead_source', reason='invalid')
                self.assertIsNotNone(res)
                self.assertIn('/media/interview/english/lead_source_invalid.mp4', res['url'])
                self.assertTrue(res['is_fallback'])

                # Stage 1: Hindi specific exists (preferred over everything)
                hi_specific = hindi_dir / 'lead_source_invalid.mp4'
                hi_specific.write_bytes(b'fake')
                res = resolve_error_media('hi', 'lead_source', reason='invalid')
                self.assertIsNotNone(res)
                self.assertIn('/media/interview/hindi/lead_source_invalid.mp4', res['url'])
                self.assertFalse(res['is_fallback'])

    def test_error_video_lookup_order_and_none_fallback(self):
        # For a non-existent error video: returns None
        res = resolve_error_media('hindi', 'non_existent_field_key')
        self.assertIsNone(res)

        # For lead_source: since no file is uploaded yet, returns None
        res_lead = resolve_error_media('hindi', 'lead_source')
        self.assertIsNone(res_lead)

    def test_question_media_missing_returns_none_and_warns(self):
        with self.assertLogs('screening.media', level='WARNING') as cm:
            res = resolve_question_media('hindi', 99)
            self.assertIsNone(res['url'])
            self.assertFalse(res['is_fallback'])
            self.assertTrue(any('Missing video for question_id=99 in all languages.' in out for out in cm.output))
