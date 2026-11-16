"""Unit tests for the redesigned language selection landing page."""
from django.test import TestCase, Client, override_settings
from screening.questions import build_dmcore_playlist


class LanguageLandingPageTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_landing_page_renders_all_five_languages_without_coming_soon(self):
        """All five languages must be present, active, and have no 'Coming soon' badges."""
        s = self.client.session
        s['token_interview'] = True
        s['dmcore_token'] = 'test-token-landing'
        s['dmcore_play_list'] = build_dmcore_playlist([{'question_id': 1}, {'question_id': 2}])
        s['candidate_name'] = 'Rahul Sharma'
        s.save()

        resp = self.client.get('/?token=test-token-landing')
        self.assertEqual(resp.status_code, 200)
        content = resp.content.decode('utf-8')

        # Check candidate greeting
        self.assertIn('Rahul Sharma', content)

        # Check native scripts and subtitles
        self.assertIn('English', content)
        self.assertIn('മലയാളം', content)
        self.assertIn('Malayalam', content)
        self.assertIn('हिन्दी', content)
        self.assertIn('Hindi', content)
        self.assertIn('தமிழ்', content)
        self.assertIn('Tamil', content)
        self.assertIn('తెలుగు', content)
        self.assertIn('Telugu', content)

        # Ensure no "Coming soon" or "disabled" language buttons exist
        self.assertNotIn('Coming soon', content)
        self.assertNotIn('lang-pill-soon', content)
        self.assertNotIn('lang-btn disabled', content)

    def test_expectations_strip_content(self):
        """Expectations strip must include microphone notice, voice or typing, and privacy line."""
        s = self.client.session
        s['token_interview'] = True
        s['dmcore_token'] = 'test-token-strip'
        s['dmcore_play_list'] = build_dmcore_playlist([{'question_id': 1}])
        s.save()

        resp = self.client.get('/?token=test-token-strip')
        self.assertEqual(resp.status_code, 200)
        content = resp.content.decode('utf-8')

        self.assertIn('Microphone needed · Answer by voice or typing', content)
        self.assertIn('Your responses are secure and confidential · TalentBot', content)

    def test_dynamic_question_count_without_conditionals(self):
        """When playlist has questions without branching, displays exact count 'N questions'."""
        s = self.client.session
        s['token_interview'] = True
        s['dmcore_token'] = 'test-token-exact'
        # Questions 1 and 2 (no conditionals)
        s['dmcore_play_list'] = build_dmcore_playlist([{'question_id': 1}, {'question_id': 2}])
        s.save()

        resp = self.client.get('/?token=test-token-exact')
        self.assertEqual(resp.status_code, 200)
        content = resp.content.decode('utf-8')

        self.assertIn('2 questions', content)
        self.assertNotIn('Up to 2 questions', content)

    def test_dynamic_question_count_with_conditionals(self):
        """When playlist includes fresher (q10) or internship (q21), displays 'Up to N questions'."""
        s = self.client.session
        s['token_interview'] = True
        s['dmcore_token'] = 'test-token-branch'
        # Questions 1, 10 (fresher branch), 11, 12, 13
        s['dmcore_play_list'] = build_dmcore_playlist([
            {'question_id': 1},
            {'question_id': 10},
            {'question_id': 11},
            {'question_id': 12},
        ])
        s.save()

        resp = self.client.get('/?token=test-token-branch')
        self.assertEqual(resp.status_code, 200)
        content = resp.content.decode('utf-8')

        self.assertIn('Up to 4 questions', content)

    def test_select_language_accepts_all_five_by_default(self):
        """Selecting any of the 5 languages must redirect to /interview/."""
        for lang in ('en', 'ml', 'hi', 'ta', 'te'):
            client = Client()
            s = client.session
            s['token_interview'] = True
            s['dmcore_token'] = f'token-{lang}'
            s['dmcore_play_list'] = build_dmcore_playlist([{'question_id': 1}])
            s.save()

            resp = client.post('/select-language/', {'lang': lang})
            self.assertEqual(resp.status_code, 302, f"Language {lang} should redirect to /interview/")
            self.assertEqual(resp.get('Location'), '/interview/')
            self.assertEqual(client.session.get('interview_language'), lang)
