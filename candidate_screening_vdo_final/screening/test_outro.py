"""
Tests for outro media resolution, safe serving, and finish flow.
Verifies:
  - Helper returns the chosen language's outro and never another language's or a legacy file.
  - Missing outro gives text only and logs a warning.
  - Safe serving with Range support, ?v=<mtime>, and strict language validation.
  - Finish flow returns outro video for chosen language and text for missing.
"""
import tempfile
from pathlib import Path
from unittest.mock import patch

from django.test import TestCase, RequestFactory
from django.conf import settings
from django.http import Http404, HttpResponseBadRequest

from screening.media import (
    resolve_outro_media,
    resolve_media,
    serve_interview_media,
    MEDIA_MANIFEST,
    get_interview_media_root,
)
from screening.views import get_question, submit_answer


class MockSession(dict):
    session_key = 'test-session-key'
    modified = False

    def cycle_key(self):
        pass

    def create(self):
        pass


class OutroMediaTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.media_root = get_interview_media_root()

    def test_manifest_entry(self):
        """Manifest maps outro -> outro.mp4."""
        self.assertIn('outro', MEDIA_MANIFEST)
        self.assertEqual(MEDIA_MANIFEST['outro'], 'outro.mp4')

    def test_helper_returns_chosen_language_outro(self):
        """The helper returns the chosen language's outro with ?v=<mtime> and is_fallback=False."""
        # English outro exists in interview_media/english/outro.mp4
        for lang_code in ('en', 'english'):
            res = resolve_outro_media(lang_code)
            self.assertIsNotNone(res['url'])
            self.assertTrue(res['url'].startswith('/media/interview/english/outro.mp4?v='))
            self.assertFalse(res['is_fallback'])
            self.assertEqual(res['filename'], 'outro.mp4')
            self.assertEqual(res['lang_folder'], 'english')
            self.assertTrue(Path(res['absolute_path']).exists())

        # Also via generic resolve_media manifest helper
        res_manifest = resolve_media('en', 'outro')
        self.assertEqual(res_manifest['url'], res['url'])

    def test_helper_never_returns_another_language_or_legacy_file(self):
        """If chosen language has no outro, never return english outro or a legacy file."""
        # Hindi currently has no outro.mp4
        with self.assertLogs('screening.media', level='WARNING') as cm:
            res_hi = resolve_outro_media('hi')
            self.assertIsNone(res_hi['url'])
            self.assertFalse(res_hi['is_fallback'])
            self.assertIsNone(res_hi['filename'])
            self.assertTrue(any('Missing outro video for language=hindi' in msg for msg in cm.output))

        # Test with mock legacy file in static videos folder: should NOT be used
        with tempfile.TemporaryDirectory() as tmpdir:
            legacy_dir = Path(tmpdir) / 'screening' / 'static' / 'screening' / 'videos'
            legacy_dir.mkdir(parents=True, exist_ok=True)
            legacy_file = legacy_dir / 'outro.mp4'
            legacy_file.write_bytes(b'fake-legacy-video')

            with patch.object(settings, 'BASE_DIR', Path(tmpdir)), \
                 self.assertLogs('screening.media', level='WARNING'):
                res = resolve_outro_media('hi')
                self.assertIsNone(res['url'])
                self.assertFalse(res['is_fallback'])

    def test_serve_interview_media_outro_safe_serving(self):
        """Safe serving: 200 with Range support, ?v= caching, and 404 for missing language."""
        req = self.factory.get('/media/interview/english/outro.mp4')
        resp = serve_interview_media(req, 'english', 'outro.mp4')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp['Content-Type'], 'video/mp4')
        self.assertEqual(resp['Accept-Ranges'], 'bytes')

        # Test HTTP Range (206)
        req_range = self.factory.get('/media/interview/english/outro.mp4', HTTP_RANGE='bytes=0-100')
        resp_range = serve_interview_media(req_range, 'english', 'outro.mp4')
        self.assertEqual(resp_range.status_code, 206)
        self.assertEqual(resp_range['Content-Range'], f'bytes 0-100/{resp["Content-Length"]}')
        self.assertEqual(resp_range['Content-Length'], '101')

        # Test immutable cache header with valid ?v=
        file_path = self.media_root / 'english' / 'outro.mp4'
        mtime = int(file_path.stat().st_mtime)
        req_v = self.factory.get(f'/media/interview/english/outro.mp4?v={mtime}')
        resp_v = serve_interview_media(req_v, 'english', 'outro.mp4')
        self.assertIn('immutable', resp_v['Cache-Control'])

        # Missing language outro: raises Http404 (does NOT serve english fallback)
        req_hi = self.factory.get('/media/interview/hindi/outro.mp4')
        with self.assertRaises(Http404):
            serve_interview_media(req_hi, 'hindi', 'outro.mp4')

        # Path traversal / invalid language validation
        req_bad = self.factory.get('/media/interview/english/../outro.mp4')
        resp_bad = serve_interview_media(req_bad, 'english', '../outro.mp4')
        self.assertEqual(resp_bad.status_code, 400)

        req_bad_lang = self.factory.get('/media/interview/french/outro.mp4')
        resp_bad_lang = serve_interview_media(req_bad_lang, 'french', 'outro.mp4')
        self.assertEqual(resp_bad_lang.status_code, 400)

    def test_finish_flow_returns_outro_for_chosen_language(self):
        """Finish flow returns chosen language outro when done."""
        req = self.factory.post('/api/question/', data={'lang': 'en'}, content_type='application/json')
        req.session = MockSession({
            'q_index': 100,  # done
            'answers': {},
            'interview_language': 'en',
            'token_interview': True,
            'dmcore_token': 'token-test',
            'dmcore_play_list': [{'question_id': 1}],
        })
        resp = get_question(req)
        self.assertEqual(resp.status_code, 200)
        import json
        data = json.loads(resp.content)
        self.assertTrue(data['done'])
        self.assertIsNotNone(data['outro_video'])
        self.assertIn('/media/interview/english/outro.mp4', data['outro_video'])
        self.assertIn('thank_you', data['ui'])

    def test_finish_flow_missing_outro_gives_text_only(self):
        """If chosen language has no outro, finish flow gives text only and logs a warning."""
        req = self.factory.post('/api/question/', data={'lang': 'hi'}, content_type='application/json')
        req.session = MockSession({
            'q_index': 100,
            'answers': {},
            'interview_language': 'hi',
            'token_interview': True,
            'dmcore_token': 'token-test',
            'dmcore_play_list': [{'question_id': 1}],
        })
        with self.assertLogs('screening.media', level='WARNING') as cm:
            resp = get_question(req)
            self.assertEqual(resp.status_code, 200)
            import json
            data = json.loads(resp.content)
            self.assertTrue(data['done'])
            self.assertIsNone(data['outro_video'])
            self.assertIn('thank_you', data['ui'])
            self.assertTrue(any('Missing outro video for language=hindi' in msg for msg in cm.output))

    def test_submit_answer_finish_flow_outro(self):
        """Submit answer on the final question returns outro_video for chosen language."""
        req = self.factory.post('/api/answer/', data={'question_id': 1, 'value': 'John Doe'}, content_type='application/json')
        req.session = MockSession({
            'q_index': 0,
            'answers': {},
            'interview_language': 'en',
            'token_interview': True,
            'dmcore_token': 'token-test',
            'dmcore_play_list': [{'question_id': 1, 'field_key': 'full_name'}],
            'invalid_attempts': {},
        })
        with patch('screening.views.save_answer', return_value={'success': True}), \
             patch('screening.views.translate_to_english_via_groq', return_value='John Doe'):
            resp = submit_answer(req)
            self.assertEqual(resp.status_code, 200)
            import json
            data = json.loads(resp.content)
            self.assertTrue(data['valid'])
            self.assertTrue(data['done'])
            self.assertIsNotNone(data['outro_video'])
            self.assertIn('/media/interview/english/outro.mp4', data['outro_video'])

    def test_submit_answer_finish_flow_missing_outro(self):
        """Submit answer on final question for language without outro returns None and warns."""
        req = self.factory.post('/api/answer/', data={'question_id': 1, 'value': 'John Doe'}, content_type='application/json')
        req.session = MockSession({
            'q_index': 0,
            'answers': {},
            'interview_language': 'hi',
            'token_interview': True,
            'dmcore_token': 'token-test',
            'dmcore_play_list': [{'question_id': 1, 'field_key': 'full_name'}],
            'invalid_attempts': {},
        })
        with patch('screening.views.save_answer', return_value={'success': True}), \
             patch('screening.views.translate_to_english_via_groq', return_value='John Doe'), \
             self.assertLogs('screening.media', level='WARNING') as cm:
            resp = submit_answer(req)
            self.assertEqual(resp.status_code, 200)
            import json
            data = json.loads(resp.content)
            self.assertTrue(data['valid'])
            self.assertTrue(data['done'])
            self.assertIsNone(data['outro_video'])
            self.assertIn('thank_you', data['ui'])
            self.assertTrue(any('Missing outro video for language=hindi' in msg for msg in cm.output))
            self.assertIn('thank_you', data['ui'])
            self.assertTrue(any('Missing outro video for language=hindi' in msg for msg in cm.output))
