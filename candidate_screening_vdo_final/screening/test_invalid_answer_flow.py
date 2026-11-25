"""Unit tests for the shared invalid video flow, month-year date validation, hint texts, and optimistic rollback."""
import json
import tempfile
from pathlib import Path
from unittest.mock import patch
from django.test import TestCase, override_settings
from django.urls import reverse

from screening.questions import (
    QUESTION_LOOKUP,
    parse_month_year,
    validate_internship_start_date,
    validate_internship_end_date,
    validate_answer,
    DATE_MIN_YEAR,
    DATE_MAX_YEAR,
)
from screening.media import (
    MEDIA_MANIFEST,
    resolve_media,
    resolve_invalid_input_media,
    FILENAME_PATTERN,
)
from screening.translations import (
    QUESTION_HINTS,
    get_question_hint,
)


class DateValidatorTests(TestCase):
    """Test date parsing and validation across accepted and rejected formats."""

    def test_valid_month_year_formats(self):
        valid_inputs = [
            ("June 2025", 6, 2025),
            ("Jun 2025", 6, 2025),
            ("jun 2025", 6, 2025),
            ("june, 2025", 6, 2025),
            ("06/2025", 6, 2025),
            ("6/2025", 6, 2025),
            ("06-2025", 6, 2025),
            ("2025-06", 6, 2025),
            ("2025/06", 6, 2025),
            ("01/2024", 1, 2024),
            ("12/2023", 12, 2023),
        ]
        for inp, expected_m, expected_y in valid_inputs:
            with self.subTest(inp=inp):
                m, y = parse_month_year(inp)
                self.assertEqual(m, expected_m, f"Failed month for input: {inp}")
                self.assertEqual(y, expected_y, f"Failed year for input: {inp}")

    def test_valid_date_normalisation_to_dmcore_format(self):
        """All valid formats normalise to 'Month YYYY' (e.g. 'June 2025')."""
        valid_inputs = [
            "June 2025",
            "Jun 2025",
            "jun 2025",
            "june, 2025",
            "06/2025",
            "6/2025",
            "06-2025",
            "2025-06",
            "2025/06",
        ]
        for inp in valid_inputs:
            with self.subTest(inp=inp):
                is_valid, normalized = validate_internship_start_date(inp)
                self.assertTrue(is_valid, f"Expected valid for: {inp}")
                self.assertEqual(normalized, "June 2025")

    def test_invalid_month_year_formats(self):
        invalid_inputs = [
            "june 202",    # 3-digit year
            "2025",        # missing month
            "june",        # missing year
            "13/2025",     # invalid month 13
            "0/2025",      # invalid month 0
            "00/2025",     # invalid month 00
            "",            # empty
            "abc",         # non-numeric/gibberish
            "xyz 123",     # invalid tokens
            "June 1998",   # before DATE_MIN_YEAR (2000)
            "June 2045",   # beyond DATE_MAX_YEAR
            "June 2025 extra",  # too many tokens
        ]
        for inp in invalid_inputs:
            with self.subTest(inp=inp):
                m, y = parse_month_year(inp)
                self.assertIsNone(m, f"Expected None month for invalid input: {inp}")
                self.assertIsNone(y, f"Expected None year for invalid input: {inp}")

    def test_internship_start_date_invalid_reason(self):
        res = validate_internship_start_date("june 202")
        self.assertFalse(res[0])
        self.assertEqual(res.reason, "invalid")


class SharedInvalidVideoMediaTests(TestCase):
    """Test resolution of the shared invalid_input video key."""

    def test_manifest_and_filename_pattern(self):
        self.assertIn('invalid_input', MEDIA_MANIFEST)
        self.assertEqual(MEDIA_MANIFEST['invalid_input'], 'invalid_input.mp4')
        self.assertTrue(FILENAME_PATTERN.match('invalid_input.mp4'))
        self.assertTrue(FILENAME_PATTERN.match('invalid_input.webm'))

    def test_english_invalid_input_resolution(self):
        res = resolve_media('en', 'invalid_input')
        self.assertIsNotNone(res)
        self.assertIn('invalid_input.mp4', res['url'])
        self.assertIn('?v=', res['url'])
        self.assertFalse(res['is_fallback'])

    def test_multilingual_fallback_to_english_invalid_input(self):
        for lang in ['hi', 'ml', 'ta', 'te']:
            with self.subTest(lang=lang):
                res = resolve_media(lang, 'invalid_input')
                self.assertIsNotNone(res)
                self.assertIn('invalid_input.mp4', res['url'])
                self.assertTrue(res['is_fallback'])

    def test_missing_invalid_input_returns_none_without_fallback_to_per_field(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            (temp_root / 'english').mkdir()
            (temp_root / 'hindi').mkdir()
            with override_settings(INTERVIEW_MEDIA_ROOT=temp_root):
                res = resolve_media('hi', 'invalid_input')
                self.assertIsNone(res)


class QuestionHintsAndValidationMatchingTests(TestCase):
    """Verify that every hint accurately matches its question's validator."""

    def test_all_24_hints_exist(self):
        self.assertEqual(len(QUESTION_HINTS), 24)
        for qid in range(1, 25):
            hint = get_question_hint(qid)
            self.assertTrue(bool(hint), f"Missing hint for question {qid}")

    def test_hint_16_expected_salary_matches_options(self):
        q16 = QUESTION_LOOKUP[16]
        hint16 = get_question_hint(16)
        self.assertIn("3-5 LPA", hint16)
        self.assertTrue(validate_answer(q16, "3-5 LPA")[0])
        self.assertFalse(validate_answer(q16, "400000")[0])

    def test_hint_10_has_experience_matches_options(self):
        q10 = QUESTION_LOOKUP[10]
        hint10 = get_question_hint(10)
        self.assertIn("Yes, I have experience", hint10)
        self.assertTrue(validate_answer(q10, "Yes, I have experience")[0])
        self.assertFalse(validate_answer(q10, "2 years")[0])

    def test_hint_13_experience_duration_matches_options(self):
        q13 = QUESTION_LOOKUP[13]
        hint13 = get_question_hint(13)
        self.assertIn("1-2 years", hint13)
        self.assertTrue(validate_answer(q13, "1-2 years")[0])

    def test_hint_17_linkedin_optional_skip(self):
        q17 = QUESTION_LOOKUP[17]
        hint17 = get_question_hint(17)
        self.assertIn("leave blank to skip", hint17)
        self.assertTrue(validate_answer(q17, "")[0])
        self.assertFalse(validate_answer(q17, "skip")[0])

    def test_hint_21_internship_done_yes_no(self):
        q21 = QUESTION_LOOKUP[21]
        self.assertTrue(validate_answer(q21, "Yes")[0])
        self.assertTrue(validate_answer(q21, "No")[0])


@override_settings(DEBUG=True)
class SubmitAnswerInvalidFlowApiTests(TestCase):
    """Test that invalid answers across multiple questions resolve to invalid_input media and hints."""

    def setUp(self):
        self.url = reverse('submit_answer')

    def _prepare_session_for_qid(self, target_qid):
        from screening.questions import get_active_questions
        session = self.client.session
        session['demo_mode'] = True
        answers = {
            'has_experience': 'Yes, I have experience',
            'internship_done': 'Yes'
        }
        active = get_active_questions(answers)
        for q in active:
            if q['id'] == target_qid:
                break
            f = q.get('field') or q.get('key')
            if f not in answers:
                answers[f] = 'Sample Answer'
        session['answers'] = answers
        session['skipped_questions'] = []
        active = get_active_questions(answers)
        idx = next(i for i, q in enumerate(active) if q['id'] == target_qid)
        session['q_index'] = idx
        session.save()
        return session, active, idx

    def test_invalid_answers_resolve_to_invalid_input_and_hint(self):
        test_cases = [
            (1, "invalid_name_no_spaces", "Enter your full name"),
            (2, "not-an-email", "Enter a valid email address"),
            (8, "year20", "Enter the 4-digit year"),
            (22, "june 202", "Enter the month and year"),
        ]

        for qid, bad_val, expected_hint_part in test_cases:
            with self.subTest(qid=qid, bad_val=bad_val):
                self._prepare_session_for_qid(qid)

                resp = self.client.post(
                    self.url,
                    data=json.dumps({'question_id': qid, 'value': bad_val, 'lang': 'en'}),
                    content_type='application/json'
                )
                self.assertEqual(resp.status_code, 200)
                data = resp.json()
                self.assertFalse(data['valid'])
                self.assertEqual(data['reason'], 'invalid')
                self.assertIn('invalid_input.mp4', data.get('error_video_url', ''))
                self.assertIn(expected_hint_part, data.get('hint', ''))

    def test_invalid_then_valid_answer_on_q22_advances_to_q23(self):
        """Entering 'june 202' fails without advancing; following 'June 2025' advances to Q23."""
        session, active, q22_idx = self._prepare_session_for_qid(22)

        # Step 1: Submit invalid answer 'june 202'
        resp1 = self.client.post(
            self.url,
            data=json.dumps({'question_id': 22, 'value': 'june 202', 'lang': 'en'}),
            content_type='application/json'
        )
        self.assertEqual(resp1.status_code, 200)
        d1 = resp1.json()
        self.assertFalse(d1['valid'])
        self.assertEqual(d1['reason'], 'invalid')
        self.assertEqual(d1['attempts_left'], 2)

        # Session verification: not advanced, not saved
        s_after_1 = self.client.session
        self.assertEqual(s_after_1['q_index'], q22_idx)
        self.assertNotIn('internship_start_date', s_after_1.get('answers', {}))

        # Step 2: Submit valid answer 'June 2025'
        resp2 = self.client.post(
            self.url,
            data=json.dumps({'question_id': 22, 'value': 'June 2025', 'lang': 'en'}),
            content_type='application/json'
        )
        self.assertEqual(resp2.status_code, 200)
        d2 = resp2.json()
        self.assertTrue(d2['valid'])
        self.assertEqual(d2['question']['id'], 23)

        # Session verification: advanced to Q23, saved
        s_after_2 = self.client.session
        self.assertEqual(s_after_2['answers']['internship_start_date'], 'June 2025')
        self.assertEqual(s_after_2['q_index'], q22_idx + 1)

    def test_two_invalid_answers_then_valid_advances(self):
        """Two invalid attempts leave 1 attempt remaining on Q22; third valid attempt advances to Q23."""
        session, active, q22_idx = self._prepare_session_for_qid(22)

        # Attempt 1: Invalid
        resp1 = self.client.post(
            self.url,
            data=json.dumps({'question_id': 22, 'value': 'bad_date_1', 'lang': 'en'}),
            content_type='application/json'
        )
        self.assertEqual(resp1.status_code, 200)
        d1 = resp1.json()
        self.assertFalse(d1['valid'])
        self.assertEqual(d1['attempts_left'], 2)
        self.assertEqual(self.client.session['q_index'], q22_idx)

        # Attempt 2: Invalid
        resp2 = self.client.post(
            self.url,
            data=json.dumps({'question_id': 22, 'value': 'bad_date_2', 'lang': 'en'}),
            content_type='application/json'
        )
        self.assertEqual(resp2.status_code, 200)
        d2 = resp2.json()
        self.assertFalse(d2['valid'])
        self.assertEqual(d2['attempts_left'], 1)
        self.assertEqual(self.client.session['q_index'], q22_idx)

        # Attempt 3: Valid
        resp3 = self.client.post(
            self.url,
            data=json.dumps({'question_id': 22, 'value': 'June 2025', 'lang': 'en'}),
            content_type='application/json'
        )
        self.assertEqual(resp3.status_code, 200)
        d3 = resp3.json()
        self.assertTrue(d3['valid'])
        self.assertEqual(d3['question']['id'], 23)
        self.assertEqual(self.client.session['q_index'], q22_idx + 1)
        self.assertEqual(self.client.session['answers']['internship_start_date'], 'June 2025')

    def test_dmcore_receives_only_valid_answer_in_order(self):
        """DMCore receives exactly one value for question 22 and it is the valid one."""
        session = self.client.session
        session['token_interview'] = True
        session['dmcore_play_list'] = [
            {'question_id': 21},
            {'question_id': 22},
            {'question_id': 23}
        ]
        session['answers'] = {'internship_experience': 'Yes'}
        session['q_index'] = 1  # on question 22
        session['skipped_questions'] = []
        session['invalid_attempts'] = {}
        session.save()

        dmcore_calls = []
        def mock_save_answer(token, q_id, answer_text):
            dmcore_calls.append({'q_id': q_id, 'answer': answer_text})
            return {'status': 'success'}

        with patch('screening.views.save_answer', side_effect=mock_save_answer):
            # 1. Invalid attempt
            resp_inv = self.client.post(
                self.url,
                data=json.dumps({'question_id': 22, 'value': 'bad_date', 'lang': 'en'}),
                content_type='application/json'
            )
            self.assertFalse(resp_inv.json()['valid'])
            self.assertEqual(len(dmcore_calls), 0)

            # 2. Valid attempt
            resp_val = self.client.post(
                self.url,
                data=json.dumps({'question_id': 22, 'value': 'June 2025', 'lang': 'en'}),
                content_type='application/json'
            )
            self.assertTrue(resp_val.json()['valid'])
            self.assertEqual(len(dmcore_calls), 1)
            self.assertEqual(dmcore_calls[0], {'q_id': 22, 'answer': 'June 2025'})

    def test_refresh_after_invalid_answer_resumes_at_q22(self):
        """Page refresh after an invalid answer resumes at Q22, never jumps to end."""
        self._prepare_session_for_qid(22)

        # Submit invalid answer
        self.client.post(
            self.url,
            data=json.dumps({'question_id': 22, 'value': 'june 202', 'lang': 'en'}),
            content_type='application/json'
        )

        # Simulate page refresh (POST /api/question/)
        get_q_url = reverse('get_question')
        ref_resp = self.client.post(get_q_url, content_type='application/json')
        self.assertEqual(ref_resp.status_code, 200)
        data = ref_resp.json()
        self.assertFalse(data.get('done', False))
        self.assertEqual(data['question']['id'], 22)

    def test_refresh_after_legitimate_skip_does_not_repeat_it(self):
        """After 3 failed attempts, question is skipped; refresh resumes at next question."""
        self._prepare_session_for_qid(22)

        # Attempt 1
        self.client.post(self.url, data=json.dumps({'question_id': 22, 'value': 'bad1', 'lang': 'en'}), content_type='application/json')
        # Attempt 2
        self.client.post(self.url, data=json.dumps({'question_id': 22, 'value': 'bad2', 'lang': 'en'}), content_type='application/json')
        # Attempt 3 (triggers skip)
        resp3 = self.client.post(self.url, data=json.dumps({'question_id': 22, 'value': 'bad3', 'lang': 'en'}), content_type='application/json')
        d3 = resp3.json()
        self.assertTrue(d3.get('skipped'))
        self.assertEqual(d3.get('attempts_left'), 0)

        # Session has skipped_questions
        s = self.client.session
        self.assertIn(22, s.get('skipped_questions', []))

        # Refresh resumes at Question 23, not 22, and not done
        get_q_url = reverse('get_question')
        ref_resp = self.client.post(get_q_url, content_type='application/json')
        self.assertEqual(ref_resp.status_code, 200)
        ref_data = ref_resp.json()
        self.assertFalse(ref_data.get('done', False))
        self.assertEqual(ref_data['question']['id'], 23)

    def test_question_mismatch_returns_400_and_does_not_corrupt_state(self):
        """Submitting an answer for the wrong question returns HTTP 400 mismatch."""
        session, active, q22_idx = self._prepare_session_for_qid(22)

        # Submit answer for question 23 while at 22
        resp = self.client.post(
            self.url,
            data=json.dumps({'question_id': 23, 'value': 'June 2025', 'lang': 'en'}),
            content_type='application/json'
        )
        self.assertEqual(resp.status_code, 400)
        data = resp.json()
        self.assertFalse(data['valid'])
        self.assertEqual(data['error'], 'Question mismatch.')

        # Calling get_question recovers and returns Question 22 cleanly
        get_q_url = reverse('get_question')
        ref_resp = self.client.post(get_q_url, content_type='application/json')
        self.assertEqual(ref_resp.status_code, 200)
        ref_data = ref_resp.json()
        self.assertEqual(ref_data['question']['id'], 22)


@override_settings(DEBUG=True)
class ProgressIndicatorTests(TestCase):
    """Test progress indicator N/M computations across DMCore playlists, conditional skips, and refreshes."""

    def setUp(self):
        self.submit_url = reverse('submit_answer')
        self.get_q_url = reverse('get_question')
        self.interview_url = reverse('interview')

    def _prepare_session_for_qid(self, target_qid):
        from screening.questions import get_active_questions
        session = self.client.session
        session['demo_mode'] = True
        answers = {
            'has_experience': 'Yes, I have experience',
            'internship_done': 'Yes'
        }
        active = get_active_questions(answers)
        for q in active:
            if q['id'] == target_qid:
                break
            f = q.get('field') or q.get('key')
            if f not in answers:
                answers[f] = 'Sample Answer'
        session['answers'] = answers
        session['skipped_questions'] = []
        active = get_active_questions(answers)
        idx = next(i for i, q in enumerate(active) if q['id'] == target_qid)
        session['q_index'] = idx
        session.save()
        return session, active, idx

    def test_playlist_of_8_questions_advances_sequentially(self):
        """A candidate playlist of 8 questions shows 1/8 then 2/8 ... up to 8/8."""
        playlist = [
            {'question_id': 1},
            {'question_id': 2},
            {'question_id': 3},
            {'question_id': 4},
            {'question_id': 5},
            {'question_id': 6},
            {'question_id': 7},
            {'question_id': 8},
        ]
        session = self.client.session
        session['token_interview'] = True
        session['dmcore_token'] = 'fake-token'
        session['interview_language'] = 'en'
        session['dmcore_play_list'] = playlist
        session['answers'] = {}
        session['skipped_questions'] = []
        session['q_index'] = 0
        session.save()

        # Check initial question via get_question
        resp = self.client.post(self.get_q_url, content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data['question']['number'], 1)
        self.assertEqual(data['question']['total'], 8)
        self.assertEqual(data['next_question']['number'], 2)
        self.assertEqual(data['next_question']['total'], 8)

        # Check initial HTML template rendering
        html_resp = self.client.get(self.interview_url)
        self.assertEqual(html_resp.status_code, 200)
        self.assertContains(html_resp, '1/8')
        self.assertContains(html_resp, 'aria-label="Question 1 of 8"')

        # Answer questions 1 through 7 and verify sequential 2/8 ... 8/8
        valid_answers = {
            1: 'John Doe',
            2: 'john@example.com',
            3: '9876543210',
            4: 'Developer',
            5: "Bachelor's Degree",
            6: 'Computer Science',
            7: 'ABC College',
        }
        for qid, ans in valid_answers.items():
            ans_resp = self.client.post(
                self.submit_url,
                data=json.dumps({'question_id': qid, 'value': ans, 'lang': 'en'}),
                content_type='application/json'
            )
            self.assertEqual(ans_resp.status_code, 200)
            ans_data = ans_resp.json()
            self.assertTrue(ans_data['valid'])
            # Next question number should be qid + 1, total should remain 8
            self.assertEqual(ans_data['question']['number'], qid + 1)
            self.assertEqual(ans_data['question']['total'], 8)

    def test_fresher_rule_reduces_total_from_8_to_5_without_counter_jumping(self):
        """When candidate at Q10 answers 'No, I am a fresher', total drops from 8 to 5 and counter goes to 4/5."""
        # 8 questions: [1, 2, 10, 11, 12, 13, 14, 15]
        playlist = [
            {'question_id': 1},
            {'question_id': 2},
            {'question_id': 10},
            {'question_id': 11},
            {'question_id': 12},
            {'question_id': 13},
            {'question_id': 14},
            {'question_id': 15},
        ]
        session = self.client.session
        session['token_interview'] = True
        session['dmcore_token'] = 'fake-token'
        session['interview_language'] = 'en'
        session['dmcore_play_list'] = playlist
        session['answers'] = {
            'full_name': 'Anil Kumar',
            'email': 'anil@example.com',
        }
        session['skipped_questions'] = []
        session['q_index'] = 2  # At Question 10
        session.save()

        # Fetch Question 10: it should be 3/8
        resp10 = self.client.post(self.get_q_url, content_type='application/json')
        self.assertEqual(resp10.status_code, 200)
        d10 = resp10.json()
        self.assertEqual(d10['question']['id'], 10)
        self.assertEqual(d10['question']['number'], 3)
        self.assertEqual(d10['question']['total'], 8)

        # Check conditional_next for fresher
        cond_fresher = d10['conditional_next']['fresher']
        self.assertEqual(cond_fresher['id'], 14)
        self.assertEqual(cond_fresher['number'], 4)  # 4th question among [1, 2, 10, 14, 15]
        self.assertEqual(cond_fresher['total'], 5)   # Total drops to 5! Not 8, and number is NOT 14!

        # Submit Fresher answer on Question 10
        ans_resp = self.client.post(
            self.submit_url,
            data=json.dumps({'question_id': 10, 'value': 'No, I am a fresher', 'lang': 'en'}),
            content_type='application/json'
        )
        self.assertEqual(ans_resp.status_code, 200)
        ans_data = ans_resp.json()
        self.assertTrue(ans_data['valid'])
        # Server response now gives question 14 at number 4, total 5
        self.assertEqual(ans_data['question']['id'], 14)
        self.assertEqual(ans_data['question']['number'], 4)
        self.assertEqual(ans_data['question']['total'], 5)

    def test_invalid_answer_does_not_change_number(self):
        """Entering an invalid answer keeps the same question number and total."""
        session, active, q22_idx = self._prepare_session_for_qid(22)
        total = len(active)
        q22_num = q22_idx + 1

        # Submit invalid answer 'june 202'
        resp = self.client.post(
            self.submit_url,
            data=json.dumps({'question_id': 22, 'value': 'june 202', 'lang': 'en'}),
            content_type='application/json'
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertFalse(data['valid'])

        # Session state: q_index has NOT changed
        s = self.client.session
        self.assertEqual(s['q_index'], q22_idx)

        # Re-fetch question (e.g. rollback/sync): number and total are identical
        ref_resp = self.client.post(self.get_q_url, content_type='application/json')
        self.assertEqual(ref_resp.status_code, 200)
        ref_data = ref_resp.json()
        self.assertEqual(ref_data['question']['number'], q22_num)
        self.assertEqual(ref_data['question']['total'], total)

    def test_resume_after_refresh_shows_right_number_and_total(self):
        """After answering questions and applying skip rules, refresh loads the exact next question."""
        playlist = [
            {'question_id': 1},
            {'question_id': 2},
            {'question_id': 10},
            {'question_id': 11},
            {'question_id': 12},
            {'question_id': 13},
            {'question_id': 14},
            {'question_id': 15},
        ]
        session = self.client.session
        session['token_interview'] = True
        session['dmcore_token'] = 'fake-token'
        session['interview_language'] = 'en'
        session['dmcore_play_list'] = playlist
        # Candidate answered Q1, Q2, and answered Q10 as fresher
        session['answers'] = {
            'full_name': 'Anil Kumar',
            'email': 'anil@example.com',
            'has_experience': 'No, I am a fresher',
        }
        session['skipped_questions'] = []
        session.save()

        # Simulate browser GET /interview/
        html_resp = self.client.get(self.interview_url)
        self.assertEqual(html_resp.status_code, 200)
        # Should render 4/5 (Question 14 is 4th active question out of 5)
        self.assertContains(html_resp, '4/5')
        self.assertContains(html_resp, 'aria-label="Question 4 of 5"')

        # Simulate API POST /api/question/
        ref_resp = self.client.post(self.get_q_url, content_type='application/json')
        self.assertEqual(ref_resp.status_code, 200)
        ref_data = ref_resp.json()
        self.assertEqual(ref_data['question']['id'], 14)
        self.assertEqual(ref_data['question']['number'], 4)
        self.assertEqual(ref_data['question']['total'], 5)
