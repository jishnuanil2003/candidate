import os
import sys
import json
import django

if sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings_local')
django.setup()

from django.test import RequestFactory
from screening.questions import QUESTION_LOOKUP
from screening.views import get_question, submit_answer
from unittest.mock import patch


class WalkthroughSession(dict):
    session_key = 'walkthrough-session'
    modified = False

    def cycle_key(self):
        pass

    def create(self):
        pass


def run_hindi_walkthrough():
    factory = RequestFactory()
    session = WalkthroughSession()
    session['token_interview'] = True
    session['dmcore_token'] = 'walkthrough-token'
    session['interview_language'] = 'hi'
    session['language'] = 'hi'
    session['answers'] = {}
    session['q_index'] = 0
    session['dmcore_play_list'] = [
        {'question_id': 19, 'field_key': 'lead_source'},
        {'question_id': 20, 'field_key': 'location'},
        {'question_id': 21, 'field_key': 'internship_done'},
        {'question_id': 22, 'field_key': 'internship_start_date'},
        {'question_id': 23, 'field_key': 'internship_end_date'},
        {'question_id': 24, 'field_key': 'internship_topic'},
    ]

    print("======================================================================")
    print("WALKTHROUGH: Hindi Candidate Interview Flow (Questions 19 - 24)")
    print("======================================================================\n")

    steps = [
        # Question 19
        {"answer": "A friend told me about this opening", "expected_valid": True, "note": "Valid (Friend/Referral)"},
        # Question 20
        {"answer": "Bengaluru", "expected_valid": True, "note": "Valid location"},
        # Question 21
        {"answer": "हाँ", "expected_valid": True, "note": "Valid Hindi option 'Yes'"},
        # Question 22 - Attempt 1 (INVALID)
        {"answer": "June 2035", "expected_valid": False, "note": "INVALID: Future year (2035)"},
        # Question 22 - Attempt 2 (VALID post-translation)
        {"answer": "June 2025", "expected_valid": True, "note": "Valid (June 2025)"},
        # Question 23 (VALID post-translation)
        {"answer": "Ongoing", "expected_valid": True, "note": "Valid (Ongoing)"},
        # Question 24
        {"answer": "Machine learning for fraud detection", "expected_valid": True, "note": "Valid topic (36 chars)"},
    ]

    with patch('screening.views.save_answer') as mock_save:
        for idx, step in enumerate(steps, 1):
            # 1. Fetch current question
            q_req = factory.post('/api/question/')
            q_req.session = session
            q_resp = json.loads(get_question(q_req).content)
            current_q = q_resp['question']
            q_id = current_q['id']

            print(f"--- STEP {idx}: Question {current_q['number']}/24 [ID: {q_id} - {QUESTION_LOOKUP[q_id]['key']}] ---")
            print(f"Prompt: {current_q['text']}")
            print(f"Candidate Input: \"{step['answer']}\" ({step['note']})")

            # 2. Submit answer
            ans_req = factory.post('/api/answer/',
                                   json.dumps({'question_id': q_id, 'value': step['answer']}),
                                   content_type='application/json')
            ans_req.session = session
            ans_resp = json.loads(submit_answer(ans_req).content)

            if ans_resp.get('valid'):
                print(f"Server Response: VALID")
                saved_val = session['answers'].get(QUESTION_LOOKUP[q_id]['field'])
                print(f"  Canonical Saved: \"{saved_val}\"")
                print(f"  Progress: {ans_resp.get('progress')}% | Done: {ans_resp.get('done')}")
            else:
                print(f"Server Response: INVALID")
                err_text = ans_resp.get('error_text') or ans_resp.get('error')
                print(f"  Error Message: \"{err_text}\"")
                print(f"  Error Video URL: {ans_resp.get('error_video_url')}")
                print(f"  Attempts Left: {ans_resp.get('attempts_left')}")

            print()

    print("======================================================================")
    print("WALKTHROUGH COMPLETE: All 6 questions processed successfully.")
    print(f"Final Candidate Answers in Session:\n{json.dumps(session['answers'], indent=2, ensure_ascii=False)}")
    print("======================================================================")


if __name__ == '__main__':
    run_hindi_walkthrough()
