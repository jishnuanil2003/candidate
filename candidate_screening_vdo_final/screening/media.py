"""Interview video resolution and HTTP Range streaming helper."""
import os
import re
import logging
from pathlib import Path
from django.conf import settings
from django.http import HttpResponse, Http404, HttpResponseBadRequest, FileResponse

logger = logging.getLogger(__name__)

LANGUAGE_FOLDER_MAP = {
    'en': 'english',
    'ml': 'malayalam',
    'hi': 'hindi',
    'ta': 'tamil',
    'te': 'telugu',
    'english': 'english',
    'malayalam': 'malayalam',
    'hindi': 'hindi',
    'tamil': 'tamil',
    'telugu': 'telugu',
}

ALLOWED_LANGUAGES = {'english', 'malayalam', 'hindi', 'tamil', 'telugu'}

FILENAME_PATTERN = re.compile(r'^(q([1-9]|1[0-9]|2[0-4])|idle_waiting|q_complete|error_[a-z0-9_]+|[a-z0-9_]+_(error|empty|invalid|before_start))\.(mp4|webm)$')


def get_interview_media_root():
    return Path(getattr(settings, 'INTERVIEW_MEDIA_ROOT', settings.BASE_DIR / 'interview_media'))


def resolve_question_media(lang_code, question_id):
    """
    Resolve a question's media file given language code and question_id (1-18).
    Returns dict:
      {
         'url': '/media/interview/<lang_folder>/q<id>.mp4',
         'is_fallback': bool,
         'lang_folder': str,
         'filename': 'q<id>.mp4',
         'file_path': Path
      }
    """
    media_root = get_interview_media_root()
    folder = LANGUAGE_FOLDER_MAP.get(lang_code, 'english')
    filename = f'q{question_id}.mp4'

    lang_dir = media_root / folder
    target_path = lang_dir / filename

    if not target_path.exists():
        # Check webm alternative
        webm_path = lang_dir / f'q{question_id}.webm'
        if webm_path.exists():
            target_path = webm_path
            filename = f'q{question_id}.webm'

    is_fallback = False
    if not target_path.exists():
        logger.warning('Missing video for language=%s, question_id=%s. Falling back to english.', folder, question_id)
        fallback_dir = media_root / 'english'
        target_path = fallback_dir / f'q{question_id}.mp4'
        if not target_path.exists():
            target_path = fallback_dir / f'q{question_id}.webm'
            filename = f'q{question_id}.webm'
        else:
            filename = f'q{question_id}.mp4'
        folder = 'english'
        is_fallback = True

    if not target_path.exists() or not target_path.is_file():
        logger.warning('Missing video for question_id=%s in all languages.', question_id)
        return {
            'url': None,
            'is_fallback': False,
            'lang_folder': folder,
            'filename': filename,
            'file_path': None,
        }

    return {
        'url': f'/media/interview/{folder}/{filename}',
        'is_fallback': is_fallback,
        'lang_folder': folder,
        'filename': filename,
        'file_path': target_path,
    }


def resolve_error_media(lang_code, field_key, reason='invalid', legacy_error_video=None):
    """
    Resolve an optional error video for a question.
    Lookup order for a case:
      1. chosen language specific file: <field_key>_<reason>.mp4
         (for internship_end_date and before_start: internship_end_date_before_start.mp4)
      2. english specific file
      3. chosen language generic file: <field_key>_error.mp4 (or legacy_error_video)
      4. english generic file: <field_key>_error.mp4 (or legacy_error_video)
      5. legacy static videos folder as fallback
      6. None (if no video exists)
    """
    if reason and (reason.endswith('.mp4') or reason.endswith('.webm') or reason.startswith('error_')):
        legacy_error_video = reason
        reason = 'invalid'

    if not field_key and not legacy_error_video:
        return None

    media_root = get_interview_media_root()
    folder = LANGUAGE_FOLDER_MAP.get(lang_code, 'english')

    # Specific file stem
    specific_stem = None
    if field_key:
        if field_key == 'internship_end_date' and reason == 'before_start':
            specific_stem = 'internship_end_date_before_start'
        elif reason:
            specific_stem = f"{field_key}_{reason}"

    # Generic file stems
    generic_stems = []
    if field_key:
        generic_stems.append(f"{field_key}_error")
    if legacy_error_video:
        legacy_stem = legacy_error_video.rsplit('.', 1)[0]
        if legacy_stem not in generic_stems:
            generic_stems.append(legacy_stem)

    def _find_in_folder(target_folder, stems):
        t_dir = media_root / target_folder
        for stem in stems:
            if not stem:
                continue
            for ext in ('mp4', 'webm'):
                cand = t_dir / f"{stem}.{ext}"
                if cand.exists() and cand.is_file():
                    mtime = int(cand.stat().st_mtime)
                    return {
                        'url': f"/media/interview/{target_folder}/{cand.name}?v={mtime}",
                        'filename': cand.name,
                        'file_path': cand,
                        'is_fallback': (target_folder == 'english' and folder != 'english'),
                    }
        return None

    # 1. Chosen language specific file
    if specific_stem:
        res = _find_in_folder(folder, [specific_stem])
        if res:
            return res

    # 2. English specific file
    if specific_stem and folder != 'english':
        res = _find_in_folder('english', [specific_stem])
        if res:
            return res

    # 3. Chosen language generic file
    res = _find_in_folder(folder, generic_stems)
    if res:
        return res

    # 4. English generic file
    if folder != 'english':
        res = _find_in_folder('english', generic_stems)
        if res:
            return res

    # 5. Legacy static videos folder as fallback
    for name in generic_stems:
        for ext in ('mp4', 'webm'):
            static_cand = settings.BASE_DIR / 'screening' / 'static' / 'screening' / 'videos' / f"{name}.{ext}"
            if static_cand.exists() and static_cand.is_file():
                mtime = int(static_cand.stat().st_mtime)
                return {
                    'url': f"/media/interview/english/{static_cand.name}?v={mtime}",
                    'filename': static_cand.name,
                    'file_path': static_cand,
                    'is_fallback': True,
                }

    return None


def serve_interview_media(request, lang, filename):
    """
    Serve interview video files with strict path validation and HTTP Range support.
    """
    # Strict validation: prevent directory traversal or unexpected filenames
    if not lang or not filename or '..' in lang or '..' in filename or '/' in filename or '\\' in filename:
        return HttpResponseBadRequest('Invalid path')

    folder = LANGUAGE_FOLDER_MAP.get(lang.lower())
    if not folder or folder not in ALLOWED_LANGUAGES:
        return HttpResponseBadRequest('Unsupported language')

    if not FILENAME_PATTERN.match(filename):
        return HttpResponseBadRequest('Invalid media filename')

    media_root = get_interview_media_root()
    file_path = media_root / folder / filename

    # Fallback to english if regional file does not exist
    if not file_path.exists() and folder != 'english':
        logger.warning('Requested file %s/%s not found, attempting fallback to english.', folder, filename)
        file_path = media_root / 'english' / filename

    if not file_path.exists():
        static_candidate = settings.BASE_DIR / 'screening' / 'static' / 'screening' / 'videos' / filename
        if static_candidate.exists() and static_candidate.is_file():
            file_path = static_candidate

    if not file_path.exists() or not file_path.is_file():
        raise Http404('Video file not found')

    file_size = file_path.stat().st_size
    content_type = 'video/webm' if filename.endswith('.webm') else 'video/mp4'

    range_header = request.META.get('HTTP_RANGE', '').strip()
    if range_header and range_header.startswith('bytes='):
        # Handle HTTP Range (206 Partial Content)
        range_match = re.match(r'bytes=(\d+)-(\d*)', range_header)
        if range_match:
            start = int(range_match.group(1))
            end_str = range_match.group(2)
            end = int(end_str) if end_str else file_size - 1

            if start >= file_size or end >= file_size or start > end:
                resp = HttpResponse(status=416)
                resp['Content-Range'] = f'bytes */{file_size}'
                return resp

            chunk_length = end - start + 1
            with open(file_path, 'rb') as f:
                f.seek(start)
                data = f.read(chunk_length)

            response = HttpResponse(data, status=206, content_type=content_type)
            response['Content-Range'] = f'bytes {start}-{end}/{file_size}'
            response['Content-Length'] = str(chunk_length)
            response['Accept-Ranges'] = 'bytes'
            response['Cache-Control'] = 'public, max-age=31536000, immutable'
            return response

    # Full content response
    response = FileResponse(open(file_path, 'rb'), content_type=content_type)
    response['Content-Length'] = str(file_size)
    response['Accept-Ranges'] = 'bytes'
    response['Cache-Control'] = 'public, max-age=31536000, immutable'
    return response
