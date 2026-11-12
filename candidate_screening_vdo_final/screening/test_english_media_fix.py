"""Tests verifying the English-only media resolution and DMCore playlist fix."""
import json
from pathlib import Path
from django.test import TestCase, Client, RequestFactory
from django.conf import settings
from screening.media import resolve_question_media, get_interview_media_root
from screening.questions import (
    QUESTION_LOOKUP,
    FRESHER_ANSWER,
    build_dmcore_playlist,
    get_dmcore_active_questions,
)
from screening.views import get_question


class MockSession(dict):
    session_key = 'test-session-key'
    modified = False

    def cycle_key(self):
        pass

    def create(self):
        pass


class EnglishMediaFixTests(TestCase):
    def test_all_24_questions_resolve_own_unique_file(self):
        """Every question 1 to 24 resolves to its own file in interview_media/english,
        not to a legacy static file, and no two IDs share a file."""
        media_root = get_interview_media_root()
        legacy_dir = settings.BASE_DIR / 'screening' / 'static' / 'screening' / 'videos'
        resolved_files = set()

        for qid in range(1, 25):
            res = resolve_question_media('en', qid)
            self.assertIsNotNone(res['url'], f"Question {qid} should resolve to a video URL")
            self.assertFalse(res['is_fallback'], f"Question {qid} should not be fallback")
            self.assertEqual(res['lang_folder'], 'english')
            self.assertIn(f"?v=", res['url'], "URL must include ?v= cachebuster")

            file_path = res['file_path']
            self.assertIsNotNone(file_path)
            self.assertTrue(file_path.exists(), f"File {file_path} must exist on disk")

            # Must be located in interview_media/english
            self.assertTrue(
                str(file_path).startswith(str(media_root / 'english')),
                f"File {file_path} must be inside interview_media/english",
            )
            # Must NOT be in legacy static directory
            self.assertFalse(
                str(file_path).startswith(str(legacy_dir)),
                f"File {file_path} must not be in legacy static directory",
            )

            # Uniqueness check: no two questions share a file
            self.assertNotIn(file_path, resolved_files, f"File {file_path} is shared by multiple questions")
            resolved_files.add(file_path)

        self.assertEqual(len(resolved_files), 24, "All 24 questions must resolve to 24 unique files")

    def test_dmcore_session_order(self):
        """A DMCore session with questions [1, 2, 6, 15] requests only those four videos in exact order."""
        playlist = build_dmcore_playlist([
            {'question_id': 1},
            {'question_id': 2},
            {'question_id': 6},
            {'question_id': 15},
        ])
        rf = RequestFactory()
        session_data = MockSession({
            'token_interview': True,
            'dmcore_token': 'token-12615',
            'dmcore_play_list': playlist,
            'interview_language': 'en',
            'answers': {},
            'q_index': 0,
        })

        requested_qids = []
        requested_videos = []

        for idx in range(4):
            session_data['q_index'] = idx
            req = rf.post('/api/question/', data={'lang': 'en'}, content_type='application/json')
            req.session = session_data
            resp = get_question(req)
            self.assertEqual(resp.status_code, 200)
            data = json.loads(resp.content)
            q = data['question']
            requested_qids.append(q['id'])
            requested_videos.append(q['question_video'].split('?')[0])

        self.assertEqual(requested_qids, [1, 2, 6, 15])
        self.assertEqual(requested_videos, [
            '/media/interview/english/q1.mp4',
            '/media/interview/english/q2.mp4',
            '/media/interview/english/q6.mp4',
            '/media/interview/english/q15.mp4',
        ])

    def test_fresher_skipping_no_videos_for_11_12_13(self):
        """Fresher answering 'No, I am a fresher' for question 10 skips questions 11, 12, 13."""
        playlist = build_dmcore_playlist([
            {'question_id': 10},
            {'question_id': 11},
            {'question_id': 12},
            {'question_id': 13},
            {'question_id': 14},
        ])
        answers = {'has_experience': FRESHER_ANSWER}
        active_qs = get_dmcore_active_questions(playlist, answers)
        active_ids = [q['id'] for q in active_qs]
        self.assertEqual(active_ids, [10, 14])

        # Verify get_question does not serve 11, 12, 13
        rf = RequestFactory()
        session_data = MockSession({
            'token_interview': True,
            'dmcore_token': 'test-fresher',
            'dmcore_play_list': playlist,
            'interview_language': 'en',
            'answers': answers,
            'q_index': 1,  # Second active question is index 1
        })
        req = rf.post('/api/question/', data={'lang': 'en'}, content_type='application/json')
        req.session = session_data
        resp = get_question(req)
        data = json.loads(resp.content)
        # Next question served must be 14 (skills), not 11, 12, or 13
        self.assertEqual(data['question']['id'], 14)
        self.assertIn('q14.mp4', data['question']['question_video'])

    def test_internship_skipping_no_videos_for_22_23_24(self):
        """Candidate answering 'No' for question 21 skips questions 22, 23, 24."""
        playlist = build_dmcore_playlist([
            {'question_id': 21},
            {'question_id': 22},
            {'question_id': 23},
            {'question_id': 24},
        ])
        answers = {'internship_done': 'No'}
        active_qs = get_dmcore_active_questions(playlist, answers)
        active_ids = [q['id'] for q in active_qs]
        self.assertEqual(active_ids, [21])

        # Verify index 1 marks interview as done
        rf = RequestFactory()
        session_data = MockSession({
            'token_interview': True,
            'dmcore_token': 'test-internship',
            'dmcore_play_list': playlist,
            'interview_language': 'en',
            'answers': answers,
            'q_index': 1,
        })
        req = rf.post('/api/question/', data={'lang': 'en'}, content_type='application/json')
        req.session = session_data
        resp = get_question(req)
        data = json.loads(resp.content)
        self.assertTrue(data.get('done'))

    def test_disabled_language_rejected(self):
        """Attempting to select a disabled regional language is rejected with 400 Bad Request."""
        client = Client()
        s = client.session
        s['token_interview'] = True
        s['dmcore_token'] = 'token-lang'
        s['dmcore_play_list'] = build_dmcore_playlist([{'question_id': 1}])
        s.save()

        for disabled_lang in ('ml', 'hi', 'ta', 'te'):
            resp = client.post('/select-language/', {'lang': disabled_lang})
            self.assertEqual(
                resp.status_code, 400,
                f"Selecting disabled language '{disabled_lang}' must return 400",
            )
            self.assertIn(b'not enabled', resp.content.lower())

        # English is enabled and must be accepted
        resp_en = client.post('/select-language/', {'lang': 'en'})
        self.assertEqual(resp_en.status_code, 302)
        self.assertEqual(resp_en.get('Location'), '/interview/')

    def test_media_endpoint_200_and_content_type_all_24_videos(self):
        """The media endpoint returns 200 with video/mp4 and valid cache headers for all 24 videos."""
        client = Client()
        for qid in range(1, 25):
            res = resolve_question_media('en', qid)
            url = res['url']
            resp = client.get(url)
            self.assertEqual(resp.status_code, 200, f"GET {url} must return 200")
            self.assertEqual(resp.get('Content-Type'), 'video/mp4')
            self.assertEqual(
                resp.get('Cache-Control'),
                'public, max-age=31536000, immutable',
                f"Verified ?v= request must return immutable cache header for {url}",
            )

        # Unversioned request returns no-cache
        unversioned_resp = client.get('/media/interview/english/q1.mp4')
        self.assertEqual(unversioned_resp.status_code, 200)
        self.assertEqual(unversioned_resp.get('Cache-Control'), 'no-cache, must-revalidate')
