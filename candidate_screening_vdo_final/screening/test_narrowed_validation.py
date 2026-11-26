import json
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.urls import reverse

from screening.questions import QUESTION_LOOKUP, validate_answer, build_dmcore_playlist, get_dmcore_active_questions
from screening.translations import QUESTION_HINTS


@override_settings(DEBUG=True)
class NarrowedValidationComprehensiveTests(TestCase):
    """
    Verification tests for narrowed validation:
    - Only 6 questions keep 'invalid input' handling (email, phone, graduation year, experience in months, internship start date, internship end date).
    - Every other question accepts any non-empty answer (odd input, single char, symbols, non-English text, long text).
    - Question 24 specifically accepts any non-empty text and leads to outro.mp4 and completes the interview.
    - Empty answers still trigger empty-answer flow.
    - Optional LinkedIn (Q17) allows blank.
    """

    def setUp(self):
        self.url = reverse('submit_answer')

    def test_all_18_non_validated_questions_accept_odd_inputs(self):
        non_validated_ids = [1, 4, 5, 6, 7, 9, 10, 11, 12, 14, 15, 16, 17, 18, 19, 20, 21, 24]
        odd_inputs = [
            "x",
            "!@#$%^&*()_+",
            "മലയാളം ടെക്സ്റ്റ്",
            "हिंदी उत्तर",
            "A" * 1500,
        ]

        for qid in non_validated_ids:
            q = QUESTION_LOOKUP[qid]
            for val in odd_inputs:
                with self.subTest(qid=qid, val=val[:15]):
                    res = validate_answer(q, val)
                    self.assertTrue(res[0], f"Question {qid} ({q['key']}) rejected non-empty input {val[:20]!r}")

    def test_six_validated_questions_still_reject_invalid_inputs(self):
        invalid_cases = [
            (2, "not-an-email"),
            (3, "12345"),               # < 10 digits
            (8, "year20"),              # not 4 digits
            (13, "invalid duration"),   # not a valid experience option
            (22, "june 202"),           # invalid month/year
            (23, "invalid-date"),       # invalid month/year
        ]

        for qid, bad_val in invalid_cases:
            q = QUESTION_LOOKUP[qid]
            with self.subTest(qid=qid, bad_val=bad_val):
                res = validate_answer(q, bad_val)
                self.assertFalse(res[0], f"Question {qid} ({q['key']}) should have rejected {bad_val!r}")
                self.assertEqual(res.reason, 'invalid')

    def test_six_validated_questions_accept_valid_inputs(self):
        valid_cases = [
            (2, "candidate@example.com"),
            (3, "9876543210"),
            (8, "2024"),
            (13, "1-2 years"),
            (22, "June 2024"),
            (23, "August 2024"),
            (23, "Ongoing"),
        ]

        for qid, good_val in valid_cases:
            q = QUESTION_LOOKUP[qid]
            with self.subTest(qid=qid, good_val=good_val):
                res = validate_answer(q, good_val)
                self.assertTrue(res[0], f"Question {qid} ({q['key']}) should have accepted {good_val!r}")

    def test_empty_answer_still_rejected_for_non_optional_questions(self):
        for qid in [1, 2, 3, 4, 8, 14, 18, 19, 20, 22, 23, 24]:
            q = QUESTION_LOOKUP[qid]
            res = validate_answer(q, "")
            self.assertFalse(res[0], f"Empty answer on Q{qid} should be rejected")
            self.assertEqual(res.reason, 'empty')

    def test_q17_linkedin_optional_allows_blank(self):
        q17 = QUESTION_LOOKUP[17]
        res = validate_answer(q17, "")
        self.assertTrue(res[0], "LinkedIn optional should allow blank")
        res_spaces = validate_answer(q17, "   ")
        self.assertTrue(res_spaces[0], "LinkedIn optional should allow spaces")

    @patch('screening.views.save_answer')
    def test_q24_leads_to_outro_and_completion_with_any_input(self, mock_save):
        mock_save.return_value = {'success': True}

        test_inputs = [
            "Web Development",
            "x",
            "Python",
            "AI/ML & Data Science",
            "വെബ് ഡെവലപ്പ്മെന്റ്",
            "---...###",
            "A" * 500
        ]

        for test_val in test_inputs:
            session = self.client.session
            session['token_interview'] = True
            session['dmcore_token'] = 'proof-token'
            session['lang'] = 'en'
            dmcore_questions = [{'question_id': i, 'field_key': QUESTION_LOOKUP[i]['key']} for i in range(1, 25)]
            session['dmcore_play_list'] = build_dmcore_playlist(dmcore_questions)
            session['answers'] = {'internship_done': 'Yes'}
            session['q_index'] = 23 # Q24 is at index 23
            session.save()

            resp = self.client.post(
                self.url,
                data=json.dumps({'question_id': 24, 'value': test_val}),
                content_type='application/json'
            )
            self.assertEqual(resp.status_code, 200)
            data = resp.json()
            self.assertTrue(data.get('valid'), f"Q24 should be valid for {test_val!r}")
            self.assertTrue(data.get('done'), f"Q24 should set done:True for {test_val!r}")
            self.assertEqual(data.get('progress'), 100)
            self.assertIn('outro.mp4', data.get('outro_video', ''))
            self.assertIn('outro.mp4', data.get('completion_video', ''))

    def test_canonical_24_question_table_mapping(self):
        """Verify that all 24 questions have consistent id, key, hint, and text."""
        self.assertEqual(len(QUESTION_LOOKUP), 24)
        for qid in range(1, 25):
            self.assertIn(qid, QUESTION_LOOKUP)
            q = QUESTION_LOOKUP[qid]
            self.assertEqual(q['id'], qid)
            self.assertTrue(bool(q['key']))
            self.assertTrue(bool(q['question']))
            self.assertIn(qid, QUESTION_HINTS)

        # Question 24 specifically
        q24 = QUESTION_LOOKUP[24]
        self.assertEqual(q24['key'], 'internship_topic')
        self.assertEqual(q24['field'], 'internship_topic')
        self.assertEqual(q24['question'], 'What was the topic or domain of your internship?')
        self.assertEqual(q24['hint'], 'Enter your internship domain or project topic, for example: Web Development with Django.')
        self.assertEqual(QUESTION_HINTS[24], 'Enter your internship domain or project topic, for example: Web Development with Django.')
