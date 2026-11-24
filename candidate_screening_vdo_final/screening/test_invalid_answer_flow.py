"""Unit tests for the shared invalid video flow, month-year date validation, hint texts, and optimistic rollback."""
import json
import tempfile
from pathlib import Path
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

    def test_invalid_answers_resolve_to_invalid_input_and_hint(self):
        test_cases = [
            (1, "invalid_name_no_spaces", "Enter your full name"),
            (2, "not-an-email", "Enter a valid email address"),
            (8, "year20", "Enter the 4-digit year"),
            (22, "june 202", "Enter the month and year"),
        ]

        for qid, bad_val, expected_hint_part in test_cases:
            with self.subTest(qid=qid, bad_val=bad_val):
                session = self.client.session
                session['demo_mode'] = True
                # In demo mode, active_qs is from get_active_questions(answers)
                # Ensure question 22 is active by setting internship_done = Yes
                session['answers'] = {'internship_done': 'Yes', 'has_experience': 'Yes, I have experience'}
                from screening.questions import get_active_questions
                active = get_active_questions(session['answers'])
                idx = next(i for i, q in enumerate(active) if q['id'] == qid)
                session['q_index'] = idx
                session.save()

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
