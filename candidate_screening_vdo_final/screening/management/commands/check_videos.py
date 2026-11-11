import os
import sys
from pathlib import Path
from django.core.management.base import BaseCommand
from django.conf import settings

LANGUAGES = ['english', 'malayalam', 'hindi', 'tamil', 'telugu']
QUESTION_IDS = list(range(1, 25))  # 1 to 24

ERROR_VIDEOS = [
    ('lead_source_invalid', []),
    ('lead_source_empty', []),
    ('location_invalid', []),
    ('location_empty', []),
    ('internship_done_invalid', []),
    ('internship_done_empty', []),
    ('internship_start_date_invalid', []),
    ('internship_start_date_empty', []),
    ('internship_end_date_invalid', []),
    ('internship_end_date_empty', []),
    ('internship_end_date_before_start', []),
    ('internship_topic_invalid', []),
    ('internship_topic_empty', []),
    ('lead_source_error', ['error_lead_source']),
    ('location_error', ['error_location']),
    ('internship_done_error', ['error_internship_done']),
    ('internship_start_date_error', ['error_internship_start_date']),
    ('internship_end_date_error', ['error_internship_end_date']),
    ('internship_topic_error', ['error_internship_topic']),
    ('full_name_error', ['error_name']),
    ('email_error', ['error_email']),
    ('phone_error', ['error_phone']),
    ('graduation_year_error', ['error_year']),
    ('skills_error', ['error_skills']),
    ('why_good_fit_error', ['cover_note_error', 'error_cover']),
    ('empty_error', ['error_empty']),
]


class Command(BaseCommand):
    help = 'Check interview video status across all 5 languages (ids 1-24) and optional error videos.'

    def handle(self, *args, **options):
        media_root = Path(getattr(settings, 'INTERVIEW_MEDIA_ROOT', settings.BASE_DIR / 'interview_media'))
        self.stdout.write(f'Checking interview media root: {media_root}\n')

        overall_status = {}

        for lang in LANGUAGES:
            lang_dir = media_root / lang
            self.stdout.write(self.style.MIGRATE_HEADING(f'[{lang.upper()}] - {lang_dir}'))
            if not lang_dir.exists():
                self.stdout.write(self.style.ERROR(f'  Directory does NOT exist: {lang_dir}'))
                overall_status[lang] = 'MISSING (0/24)'
                continue

            # Check question videos (q1 to q24)
            present_count = 0
            missing_count = 0

            self.stdout.write(self.style.NOTICE('  -- Question Videos (q1-q24) --'))
            for q_id in QUESTION_IDS:
                found_path = None
                for ext in ('mp4', 'webm'):
                    candidate = lang_dir / f'q{q_id}.{ext}'
                    if candidate.exists() and candidate.is_file():
                        found_path = candidate
                        break

                if found_path:
                    size = found_path.stat().st_size
                    size_mb = size / (1024 * 1024)
                    self.stdout.write(f'  q{q_id:02d}: PRESENT ({found_path.name}) - {size_mb:.2f} MB')
                    present_count += 1
                else:
                    self.stdout.write(self.style.WARNING(f'  q{q_id:02d}: MISSING (expected q{q_id}.mp4)'))
                    missing_count += 1

            if present_count == 24:
                status_label = 'READY (24/24)'
            elif present_count > 0:
                status_label = f'PARTIAL ({present_count}/24)'
            else:
                status_label = 'MISSING (0/24)'
            overall_status[lang] = status_label

            self.stdout.write(f'  Question videos status for {lang}: {status_label} ({present_count}/24 present, {missing_count}/24 missing)')

            # Check optional error videos
            self.stdout.write(self.style.NOTICE('  -- Error Videos (OPTIONAL) --'))
            err_present = 0
            err_missing = 0
            for canonical_name, aliases in ERROR_VIDEOS:
                found_err = None
                candidates = [canonical_name] + aliases
                for c_name in candidates:
                    for ext in ('mp4', 'webm'):
                        cand_path = lang_dir / f'{c_name}.{ext}'
                        if cand_path.exists() and cand_path.is_file():
                            found_err = cand_path
                            break
                    if found_err:
                        break

                if found_err:
                    self.stdout.write(f'  [OPTIONAL] {canonical_name}.mp4: PRESENT ({found_err.name})')
                    err_present += 1
                else:
                    self.stdout.write(self.style.NOTICE(f'  [OPTIONAL] {canonical_name}.mp4: MISSING'))
                    err_missing += 1

            self.stdout.write(f'  Optional error videos for {lang}: {err_present} present, {err_missing} missing\n')

        self.stdout.write(self.style.MIGRATE_HEADING('=== OVERALL SUMMARY ==='))
        for lang, status in overall_status.items():
            color_fn = self.style.SUCCESS if 'READY' in status else self.style.WARNING
            self.stdout.write(f'  {lang:10s}: {color_fn(status)}')

        self.stdout.write(self.style.SUCCESS('\nVideo status check complete.'))
