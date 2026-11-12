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

FILENAME_PATTERN = re.compile(r'^(q_?([1-9]|1[0-9]|2[0-4])|idle_waiting|q_complete|error_[a-z0-9_]+|[a-z0-9_]+_(error|empty|invalid|before_start))\.(mp4|webm)$')


def get_interview_media_root():
    return Path(getattr(settings, 'INTERVIEW_MEDIA_ROOT', settings.BASE_DIR / 'interview_media'))


def _find_question_file(lang_dir, question_id):
    for prefix in (f'q{question_id}', f'q_{question_id}'):
        for ext in ('mp4', 'webm'):
            cand = lang_dir / f"{prefix}.{ext}"
            if cand.exists() and cand.is_file():
                return cand
    return None


def resolve_question_media(lang_code, question_id):
    """
    Resolve a question's media file given language code and question_id (1-24).
    Lookup order:
      1. chosen language file (e.g. interview_media/english/q<id>.mp4 or q_<id>.mp4)
      2. english fallback (if chosen language is not english)
      3. None (text on screen fallback) - no legacy pre-recorded fallback.
    Returns dict:
      {
         'url': '/media/interview/<lang_folder>/<filename>?v=<mtime>',
         'is_fallback': bool,
         'lang_folder': str,
         'filename': str,
         'file_path': Path,
         'absolute_path': str
      }
    """
    media_root = get_interview_media_root()
    folder = LANGUAGE_FOLDER_MAP.get(lang_code, 'english')

    lang_dir = media_root / folder
    target_path = _find_question_file(lang_dir, question_id)
    is_fallback = False

    if not target_path and folder != 'english':
        logger.warning('Missing video for language=%s, question_id=%s. Falling back to english.', folder, question_id)
        fallback_dir = media_root / 'english'
        target_path = _find_question_file(fallback_dir, question_id)
        if target_path:
            folder = 'english'
            is_fallback = True

    if not target_path or not target_path.is_file():
        logger.warning('Missing video for question_id=%s in all languages.', question_id)
        return {
            'url': None,
            'is_fallback': False,
            'lang_folder': folder,
            'filename': None,
            'file_path': None,
            'absolute_path': None,
        }

    mtime = int(target_path.stat().st_mtime)
    filename = target_path.name
    return {
        'url': f'/media/interview/{folder}/{filename}?v={mtime}',
        'is_fallback': is_fallback,
        'lang_folder': folder,
        'filename': filename,
        'file_path': target_path,
        'absolute_path': str(target_path.resolve()),
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
        is_question = bool(re.match(r'^q_?([1-9]|1[0-9]|2[0-4])\.', filename))
        if not is_question:
            static_candidate = settings.BASE_DIR / 'screening' / 'static' / 'screening' / 'videos' / filename
            if static_candidate.exists() and static_candidate.is_file():
                file_path = static_candidate

    if not file_path.exists() or not file_path.is_file():
        raise Http404('Video file not found')

    file_size = file_path.stat().st_size
    content_type = 'video/webm' if filename.endswith('.webm') else 'video/mp4'
    actual_mtime = int(file_path.stat().st_mtime)
    v_param = request.GET.get('v')
    if v_param and v_param == str(actual_mtime):
        cache_control = 'public, max-age=31536000, immutable'
    else:
        cache_control = 'no-cache, must-revalidate'

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
            response['Cache-Control'] = cache_control
            return response

    # Full content response
    response = FileResponse(open(file_path, 'rb'), content_type=content_type)
    response['Content-Length'] = str(file_size)
    response['Accept-Ranges'] = 'bytes'
    response['Cache-Control'] = cache_control
    return response
