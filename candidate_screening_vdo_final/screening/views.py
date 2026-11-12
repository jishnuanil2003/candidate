import json
import logging
import time
from django.conf import settings
from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.cache import never_cache
from django.templatetags.static import static
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import CandidateApplication, HRProfile
from .questions import (QUESTION_LOOKUP, QUESTIONS, NO_QUESTIONS_MESSAGE, build_dmcore_playlist,
                        get_dmcore_active_questions, validate_answer, get_active_questions,
                        is_empty_or_filler, ValidationResult)
from .forms import HRSignupForm, HRLoginForm
from .translations import TRANSLATIONS, map_option_to_canonical_english, get_error_text, ADDENDUM_ERROR_TEXTS
from .media import resolve_question_media, resolve_error_media, serve_interview_media

SUPPORTED_LANGUAGES = {'en', 'ml', 'hi', 'ta', 'te'}
ENABLED_INTERVIEW_LANGUAGES = set(getattr(settings, 'ENABLED_INTERVIEW_LANGUAGES', ['en']))
from .dmcore import DmcoreError, load_session, save_answer, complete_interview as dmcore_complete_interview

logger = logging.getLogger(__name__)


def _dmcore_public_error(error):
    """Return a clear, safe message without exposing credentials or tokens."""
    if error.kind == 'configuration':
        return 'Interview service configuration is missing. Please contact the recruiter.'
    if error.kind == 'authentication':
        return 'Something went wrong. Please try again shortly or contact the recruiter.'
    if error.kind == 'timeout':
        return 'Interview service timed out. Please try again shortly.'
    if error.kind == 'connection_refused':
        return 'Interview service refused the connection. Please try again shortly.'
    if error.kind == 'connection':
        return 'Interview service is unreachable. Please try again shortly.'
    if error.status is not None:
        return f'Interview service returned HTTP {error.status}. Please try again shortly.'
    return 'Interview service failed. Please contact the recruiter.'


VIDEO_BASE = 'screening/videos/'

# ─── Translation & Mapping Helpers ─────────────────────────────────────

import re
import unicodedata


REGIONAL_NUMBER_WORDS = {
    # Hindi
    'शून्य': '0', 'एक': '1', 'दो': '2', 'तीन': '3', 'चार': '4',
    'पाँच': '5', 'पांच': '5', 'छह': '6', 'सात': '7', 'आठ': '8', 'नौ': '9',
    # Malayalam
    'പൂജ്യം': '0', 'ഒന്ന്': '1', 'രണ്ട്': '2', 'മൂന്ന്': '3', 'നാല്': '4',
    'അഞ്ച്': '5', 'ആറ്': '6', 'ഏഴ്': '7', 'എട്ട്': '8', 'ഒമ്പത്': '9',
    # Tamil
    'பூஜ்யம்': '0', 'ஒன்று': '1', 'இரண்டு': '2', 'மூன்று': '3', 'நான்கு': '4',
    'ஐந்து': '5', 'ஆறு': '6', 'ஏழு': '7', 'எட்டு': '8', 'ஒன்பது': '9',
    # Telugu
    'సున్నా': '0', 'ఒకటి': '1', 'రెండు': '2', 'మూడు': '3', 'నాలుగు': '4',
    'ఐదు': '5', 'ఆరు': '6', 'ఏడు': '7', 'ఎనిమిది': '8', 'తొమ్మిది': '9',
}

def convert_to_ascii_digits(text):
    if not text:
        return text
    result = []
    for char in text:
        if char.isdigit():
            try:
                result.append(str(unicodedata.digit(char)))
            except ValueError:
                result.append(char)
        else:
            result.append(char)
    return "".join(result)

def normalize_number_input(text, field_type):
    if not text:
        return text
    cleaned = convert_to_ascii_digits(text)
    if field_type == 'phone':
        return re.sub(r'[^\d\+]', '', cleaned)
    elif field_type == 'cgpa':
        match = re.search(r'\d+(\.\d+)?', cleaned)
        return match.group(0) if match else cleaned
    elif field_type == 'year':
        match = re.search(r'\d{4}', cleaned)
        return match.group(0) if match else cleaned
    return cleaned

def translate_number_via_groq(text, lang, field_type):
    from django.conf import settings
    if not hasattr(settings, 'GROQ_API_KEY') or not settings.GROQ_API_KEY:
        return text
    try:
        from groq import Groq
        client = Groq(api_key=settings.GROQ_API_KEY)
        
        system_instructions = {
            'phone': "You are a data cleaning assistant. Extract the phone number from the text. Provide ONLY the standard digits (and leading + if applicable), with no spaces, symbols, text, or explanations.",
            'cgpa': "You are a data cleaning assistant. Extract the numeric CGPA or percentage score from the text. Provide ONLY the float or integer number, with no text, percentage symbols, or explanation.",
            'year': "You are a data cleaning assistant. Extract the 4-digit graduation year from the text. Provide ONLY the 4-digit year as a number, with no text or explanation."
        }
        instruction = system_instructions.get(field_type, "Extract the number from the text. Provide ONLY the digits.")
        
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": instruction},
                {"role": "user", "content": text}
            ],
            temperature=0.0
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Groq number translation error: {e}")
        return text

def clean_and_normalize_number(text, lang, field_type):
    if not text:
        return text
    
    replaced = text
    for word, digit in REGIONAL_NUMBER_WORDS.items():
        replaced = replaced.replace(word, digit)
    text_ascii_digits = convert_to_ascii_digits(replaced)
    indic_pattern = re.compile(r'[\u0900-\u097F\u0B80-\u0BFF\u0C00-\u0C7F\u0D00-\u0D7F]')
    
    if indic_pattern.search(text_ascii_digits):
        translated = translate_number_via_groq(text_ascii_digits, lang, field_type)
        return normalize_number_input(translated, field_type)
    else:
        return normalize_number_input(text_ascii_digits, field_type)

def translate_email_via_groq(text):
    from django.conf import settings
    if not hasattr(settings, 'GROQ_API_KEY') or not settings.GROQ_API_KEY:
        return None
    try:
        from groq import Groq
        # 1. Pre-process common spoken substitutions
        replacements = {
            r'\bat the rate of\b': '@',
            r'\bat the rate\b': '@',
            r'attherateof': '@',
            r'attherate': '@',
            r'\bat\b': '@',
            r'theright': '',
            r'the right': '',
            r'\bthe rate of\b': '@',
            r'\bthe rate\b': '@',
            r'\bdot\b': '.',
            r'\bunderscore\b': '_',
            r'\bdash\b': '-',
            r'\bhyphen\b': '-',
        }
        cleaned = text
        for pattern, repl in replacements.items():
            cleaned = re.sub(pattern, repl, cleaned, flags=re.IGNORECASE)
            
        cleaned = re.sub(r'\s*@\s*', '@', cleaned)
        cleaned = re.sub(r'\s*\.\s*', '.', cleaned)
        cleaned = re.sub(r'@+', '@', cleaned)
        
        # 2. Collapse the email-ish part (removing spaces within it)
        if '@' in cleaned:
            parts = cleaned.split('@', 1)
            prefix = parts[0]
            suffix = '@' + parts[1]
            
            words = prefix.split()
            email_username_words = []
            stop_words = {'is', 'email', 'my', 'me', 'address', 'the', 'a', 'an', 'to', 'for', 'here', 'am', 'was', 'are', 'i', 'have', 'hello', 'hi', 'dear'}
            
            for word in reversed(words):
                if word.lower() in stop_words:
                    break
                email_username_words.insert(0, word)
                
            username = "".join(email_username_words)
            suffix_clean = suffix.replace(' ', '')
            
            non_email_len = len(prefix) - len(" ".join(email_username_words))
            non_email_prefix = prefix[:non_email_len]
            
            pre_collapsed = (non_email_prefix + username + suffix_clean).strip()
        else:
            pre_collapsed = cleaned
            
        client = Groq(api_key=settings.GROQ_API_KEY)
        
        system_instruction = (
            "You are a strict data cleaning assistant. Your task is to extract and correct the email address from a transcribed text.\n"
            "Identify phonetic name spelling errors and convert spoken words like 'at the rate of' or 'dot' to symbols.\n\n"
            "Here are reference examples of how to clean the text:\n"
            "- 'My email is rahul at gmail dot com' -> 'rahul@gmail.com'\n"
            "- 'rahul dash work at gmail.com' -> 'rahul-work@gmail.com'\n"
            "- 'rahul underscore 123 at yahoo . com' -> 'rahul_123@yahoo.com'\n"
            "- 'Just know any zero seven at the gmail.com' -> 'jishnuanil07@gmail.com'\n"
            "- 'jishnu kanil07 at gmail.com' -> 'jishnukanil07@gmail.com'\n\n"
            "Strictly clean and return the email from the user's input text below. Do NOT output any of the reference example emails above under any circumstances.\n"
            "Provide ONLY the clean email address in lowercase. Do NOT include any explanations, introduction, quotes, punctuation, or extra words."
        )
        
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": pre_collapsed}
            ],
            temperature=0.0
        )
        result = response.choices[0].message.content.strip()
        result = result.replace('"', '').replace("'", "").replace(" ", "")
        return result
    except Exception as e:
        print(f"Groq email translation error: {e}")
        return None

def clean_transcribed_phone(text):
    if not text:
        return text
    cleaned = convert_to_ascii_digits(text)
    for word, digit in REGIONAL_NUMBER_WORDS.items():
        cleaned = cleaned.replace(word, digit)
    cleaned = re.sub(r'[^\d\+]', '', cleaned)
    return cleaned

def clean_transcribed_email(text):
    if not text:
        return text
    
    # Try using Groq LLM first
    llm_result = translate_email_via_groq(text)
    if llm_result and '@' in llm_result and '.' in llm_result and ' ' not in llm_result:
        # Check that '@' appears before the last '.'
        if llm_result.find('@') < llm_result.rfind('.'):
            return llm_result.lower()
            
    # Fallback to regex-based cleaning
    cleaned = text.strip().strip('"').strip("'")
    
    # Normalize common spoken substitutions
    replacements = {
        r'\bat the rate of\b': '@',
        r'\bat the rate\b': '@',
        r'attherateof': '@',
        r'attherate': '@',
        r'\bat\b': '@',
        r'theright': '',
        r'the right': '',
        r'\bthe rate of\b': '@',
        r'\bthe rate\b': '@',
        r'\bdot\b': '.',
        r'\bunderscore\b': '_',
        r'\bdash\b': '-',
        r'\bhyphen\b': '-',
        r'അറ്റ് ദി റേറ്റ് ഓഫ്': '@',
        r'അറ്റ് ദി റേറ്റ്': '@',
        r'അറ്റ്': '@',
        r'ഡോട്ട് കോം': '.com',
        r'ഡോട്ട്': '.',
        r'एट द रेट ऑफ': '@',
        r'एट द रेट': '@',
        r'एट': '@',
        r'डॉट कॉम': '.com',
        r'डॉट': '.',
        r'அட்': '@',
        r'டாட் காம்': '.com',
        r'டாட்': '.',
        r'ఎట్': '@',
        r'డాట్ కామ్': '.com',
        r'డాట్': '.',
    }
    for pattern, repl in replacements.items():
        cleaned = re.sub(pattern, repl, cleaned, flags=re.IGNORECASE)

    # Clean up spaces around @ and . first
    cleaned = re.sub(r'\s*@\s*', '@', cleaned)
    cleaned = re.sub(r'\s*\.\s*', '.', cleaned)
    cleaned = re.sub(r'@+', '@', cleaned)

    if '@' in cleaned:
        parts = cleaned.split('@', 1)
        prefix = parts[0]
        suffix = '@' + parts[1]
        
        # Split prefix into words
        words = prefix.split()
        email_username_words = []
        stop_words = {'is', 'email', 'my', 'me', 'address', 'the', 'a', 'an', 'to', 'for', 'here', 'am', 'was', 'are', 'i', 'have', 'hello', 'hi', 'dear'}
        
        for word in reversed(words):
            # If we hit a stop word, we stop building the email username
            if word.lower() in stop_words:
                break
            email_username_words.insert(0, word)
            
        username = "".join(email_username_words).lower()
        suffix_clean = suffix.replace(' ', '').lower()
        
        non_email_len = len(prefix) - len(" ".join(email_username_words))
        non_email_prefix = prefix[:non_email_len]
        
        return (non_email_prefix + username + suffix_clean).strip()
        
    return cleaned.lower()

def translate_to_english_via_groq(text, source_lang, field_id=None):
    if not text or not text.strip():
        return text
    if source_lang in ['en', 'en-US', 'en-GB']:
        return text
        
    import re
    # Check if there are any regional Indian script characters (Devanagari, Tamil, Telugu, Malayalam).
    # If not, the text is already in English/Latin script or gibberish, so return it as-is.
    indic_pattern = re.compile(r'[\u0900-\u097F\u0B80-\u0BFF\u0C00-\u0C7F\u0D00-\u0D7F]')
    if not indic_pattern.search(text):
        return text
    
    lang_names = {
        'ml': 'Malayalam',
        'hi': 'Hindi',
        'ta': 'Tamil',
        'te': 'Telugu',
    }
    lang_name = lang_names.get(source_lang, source_lang)
    
    from django.conf import settings
    if not hasattr(settings, 'GROQ_API_KEY') or not settings.GROQ_API_KEY:
        return text
        
    try:
        from groq import Groq
        client = Groq(api_key=settings.GROQ_API_KEY)
        
        system_instruction = f"You are a professional translator. Translate the following text from {lang_name} to English. Preserve any original names, emails, dates, or numbers. If the text is already in English, is gibberish, or cannot be translated, return it exactly as it is without any changes. Provide ONLY the direct English translation without any preamble, explanation, quotes, or conversation."
        
        if field_id == 'full_name':
            system_instruction += " Crucial: The text being translated is a person's name. Do NOT translate the literal meaning of the name. Instead, transliterate/romanize the name to its standard English pronunciation/spelling (e.g., 'പ്രിയ' -> 'Priya', 'സൂര്യ' -> 'Surya')."
        elif field_id == 'institution':
            system_instruction += " Crucial: The text being translated is a college/university name. Transliterate proper names (e.g. college or place names) rather than translating their literal meanings."
        elif field_id == 'company':
            system_instruction += " Crucial: The text being translated is a company name. Transliterate proper names rather than translating literal meanings."
            
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": text}
            ],
            temperature=0.0
        )
        translated_text = response.choices[0].message.content.strip()
        if translated_text.startswith('"') and translated_text.endswith('"'):
            translated_text = translated_text[1:-1]
        elif translated_text.startswith("'") and translated_text.endswith("'"):
            translated_text = translated_text[1:-1]
        return translated_text
    except Exception as e:
        print(f"Groq translation error: {e}")
        return text

def translate_to_lang_via_groq(text, target_lang):
    if not text or not text.strip() or target_lang == 'en':
        return text
        
    lang_names = {
        'ml': 'Malayalam',
        'hi': 'Hindi',
        'ta': 'Tamil',
        'te': 'Telugu',
    }
    lang_name = lang_names.get(target_lang, target_lang)
    
    from django.conf import settings
    if not hasattr(settings, 'GROQ_API_KEY') or not settings.GROQ_API_KEY:
        return text
        
    try:
        from groq import Groq
        client = Groq(api_key=settings.GROQ_API_KEY)
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": f"You are a professional translator. Translate the following validation error message from English to {lang_name}. Provide ONLY the translation, without any explanations or extra text."},
                {"role": "user", "content": text}
            ],
            temperature=0.0
        )
        return response.choices[0].message.content.strip()
    except Exception:
        return text

def map_option_to_english(question, selected_value, lang):
    if lang == 'en' or not selected_value:
        return selected_value
        
    q_id = question['id']
    lang_translations = TRANSLATIONS.get(lang, {}).get('questions', {}).get(question.get('translation_key', q_id), {})
    if not lang_translations:
        return selected_value
        
    options = lang_translations.get('options', [])
    options_translated = lang_translations.get('options_translated', [])
    
    for i, opt_trans in enumerate(options_translated):
        if opt_trans.strip().lower() == selected_value.strip().lower():
            return options[i]
            
    for opt in options:
        if opt.strip().lower() == selected_value.strip().lower():
            return opt
            
    return selected_value

def get_translation_cache(request):
    if 'translation_cache' not in request.session:
        request.session['translation_cache'] = {}
    return request.session['translation_cache']

def save_translation_cache(request, cache):
    request.session['translation_cache'] = cache
    request.session.modified = True

def get_translated_question(q, lang):
    q_translated = q.copy()
    if not lang:
        lang = 'en'
    lang_data = TRANSLATIONS.get(lang, {})
    q_dict = lang_data.get('questions', {})
    q_trans = q_dict.get(q['id']) or q_dict.get(q.get('key')) or q_dict.get(q.get('translation_key')) or {}
    
    if q_trans:
        if 'question' in q_trans:
            q_translated['question'] = q_trans['question']
        if 'options_translated' in q_trans:
            q_translated['options'] = q_trans['options_translated']
        elif 'options' in q_trans:
            q_translated['options'] = q_trans['options']
        if 'other_label' in q_trans:
            q_translated['other_label'] = q_trans['other_label']
        if 'placeholder' in q_trans:
            q_translated['placeholder'] = q_trans['placeholder']
        if 'hint' in q_trans:
            q_translated['hint'] = q_trans['hint']
            
    return q_translated

# ─── Public: Candidate pages ───────────────────────────────────────────

def index(request):
    token = request.GET.get('token', '').strip()
    if not token:
        return render(request, 'screening/entry_message.html', {
            'message': 'Please use the interview link sent to you'
        }, status=400)
    if request.session.get('token_interview') and request.session.get('dmcore_token') == token and request.session.get('dmcore_play_list'):
        if request.session.get('interview_language') and request.session.get('interview_language') in SUPPORTED_LANGUAGES:
            return redirect('interview')
        return render(request, 'screening/select_language.html', {
            'candidate_name': request.session.get('candidate_name', '')
        })
    try:
        session_data = load_session(token)
    except DmcoreError as error:
        if error.status in (401, 403):
            logger.error('key rejected (HTTP %s)', error.status)
            message = 'Something went wrong. Please try again shortly or contact the recruiter.'
            response_status = 403
        elif error.kind == 'timeout':
            logger.error('DMCore request timed out')
            message = 'Interview service timed out. Please try again shortly.'
            response_status = 504
        elif error.kind in ('connection', 'connection_refused'):
            logger.error('DMCore is unreachable')
            message = 'Interview service is unreachable. Please try again shortly.'
            response_status = 503
        elif error.kind == 'configuration':
            logger.error('DMCore configuration error: %s', error)
            message = 'Interview service configuration is missing. Please contact the recruiter.'
            response_status = 500
        elif error.status in (400, 404):
            message = 'This link is not valid'
            response_status = 400
        elif error.status == 410:
            message = 'This link has expired, please contact the recruiter'
            response_status = 410
        elif error.status == 409:
            message = 'This interview has already been completed'
            response_status = 409
        else:
            logger.error('DMCore session error (status=%s, kind=%s)', error.status, error.kind)
            message = _dmcore_public_error(error)
            response_status = 503
        return render(request, 'screening/entry_message.html', {'message': message}, status=response_status)

    dmcore_questions = session_data.get('questions') or []
    if not dmcore_questions:
        logger.info('DMCore session returned no interview questions')
        return render(request, 'screening/entry_message.html', {'message': NO_QUESTIONS_MESSAGE})
    playlist = build_dmcore_playlist(dmcore_questions)
    if not playlist:
        logger.info('No known DMCore question IDs remain after filtering')
        return render(request, 'screening/entry_message.html', {'message': NO_QUESTIONS_MESSAGE})

    request.session.cycle_key()
    request.session['token_interview'] = True
    request.session['dmcore_token'] = token
    candidate_data = session_data.get('candidate', {})
    candidate_name = str(candidate_data.get('name', '')) if isinstance(candidate_data, dict) else ''
    request.session['candidate_name'] = candidate_name
    request.session['dmcore_play_list'] = playlist
    request.session['unsaved_answers'] = []
    request.session['answers'] = {}
    request.session['q_index'] = 0
    request.session['interview_finished'] = False
    request.session.modified = True

    saved_lang = request.session.get('interview_language')
    if saved_lang and saved_lang in SUPPORTED_LANGUAGES and saved_lang in ENABLED_INTERVIEW_LANGUAGES:
        return redirect('interview')

    return render(request, 'screening/select_language.html', {
        'candidate_name': candidate_name,
        'enabled_languages': ENABLED_INTERVIEW_LANGUAGES,
    })


def select_language(request):
    token_mode = request.session.get('token_interview', False)
    demo_mode = settings.DEBUG and request.session.get('demo_mode', False)
    if not token_mode and not demo_mode:
        return redirect('index')

    if request.method in ('POST', 'GET'):
        lang = request.POST.get('lang') or request.GET.get('lang')
        if not lang or lang not in SUPPORTED_LANGUAGES:
            return HttpResponseBadRequest('Invalid language selected')



        answers = request.session.get('answers', {})
        addendum_text = None
        if len(answers) > 0:
            return HttpResponseBadRequest('Language cannot be changed once the interview has started')

        enabled_langs = set(getattr(settings, 'ENABLED_INTERVIEW_LANGUAGES', ['en']))
        if lang not in enabled_langs:
            return HttpResponseBadRequest('Selected language is not enabled. Only English is currently supported.')

        request.session['interview_language'] = lang
        request.session['language'] = lang
        request.session.modified = True
        return redirect('interview')

    return redirect('interview')


def demo_interview(request):
    if not settings.DEBUG:
        return HttpResponse('Not found', status=404)
    if not request.session.session_key:
        request.session.create()
    request.session['demo_mode'] = True
    request.session['token_interview'] = False
    request.session['answers'] = {}
    request.session['q_index'] = 0
    request.session['language'] = request.GET.get('lang', 'en')
    request.session['interview_language'] = request.session['language']
    request.session.modified = True
    return render(request, 'screening/index.html')


def interview(request):
    token_mode = request.session.get('token_interview', False)
    demo_mode = settings.DEBUG and request.session.get('demo_mode', False)
    if not token_mode and not demo_mode:
        return redirect('index')
    if token_mode and not request.session.get('dmcore_play_list'):
        return redirect('index')
    if token_mode and not request.session.get('interview_language'):
        return redirect('index')
    if not request.session.session_key:
        request.session.create()
    if 'answers' not in request.session:
        request.session['answers'] = {}
        request.session['q_index'] = 0
    if 'language' not in request.session:
        request.session['language'] = request.session.get('interview_language', 'en')

    active_qs = (get_dmcore_active_questions(request.session.get('dmcore_play_list', []), request.session.get('answers', {}))
                 if token_mode else get_active_questions(request.session.get('answers', {})))
    current_lang = request.session.get('interview_language') or request.session.get('language', 'en')
    answers = request.session.get('answers', {})
    return render(request, 'screening/interview.html', {
        'total_questions': len(active_qs),
        'current_language': current_lang,
        'candidate_name': request.session.get('candidate_name', ''),
        'token_interview': token_mode,
        'can_change_language': len(answers) == 0,
    })


@require_http_methods(['POST'])
def get_question(request):
    try:
        answers = request.session.get('answers', {})
        addendum_text = None
        q_index = request.session.get('q_index', 0)
        token_mode = request.session.get('token_interview', False)
        demo_mode = settings.DEBUG and request.session.get('demo_mode', False)
        if not token_mode and not demo_mode:
            return JsonResponse({'error': 'Interview link required'}, status=403)
        active_qs = (get_dmcore_active_questions(request.session.get('dmcore_play_list', []), answers)
                     if token_mode else get_active_questions(answers))

        lang = request.session.get('interview_language') or request.session.get('language', 'en')
        if request.body:
            try:
                data = json.loads(request.body)
                if 'lang' in data and data['lang'] in SUPPORTED_LANGUAGES and data['lang'] in ENABLED_INTERVIEW_LANGUAGES:
                    if len(answers) == 0:
                        lang = data['lang']
                        request.session['interview_language'] = lang
                        request.session['language'] = lang
                        request.session.modified = True
            except json.JSONDecodeError:
                pass

        ui_trans = TRANSLATIONS.get(lang, {}).get('ui', {}).copy()
        lang_data = TRANSLATIONS.get(lang, {})
        ui_trans['english_only'] = lang_data.get('errors', {}).get('english_only', 'Please enter your response in English only.')
        if q_index >= len(active_qs):
            return JsonResponse({'done': True, 'completion_video': '/media/interview/english/q_complete.mp4', 'ui': ui_trans})

        question = active_qs[q_index]
        translated = get_translated_question(question, lang)
        next_question = active_qs[q_index + 1] if q_index + 1 < len(active_qs) else None
        total = len(active_qs)

        media_info = resolve_question_media(lang, question['id'])
        next_media_info = resolve_question_media(lang, next_question['id']) if next_question else None
        error_media = resolve_error_media(lang, question.get('key', ''), question.get('error_video', ''))
        error_video_url = error_media['url'] if error_media else None
        debug_info = None
        if settings.DEBUG:
            debug_info = {
                'question_id': question['id'],
                'language': lang,
                'resolved_file': media_info.get('filename') or 'None (text only)',
                'absolute_path': media_info.get('absolute_path') or 'None (text on screen)',
            }

        return JsonResponse({
            'done': False,
            'question': {
                'id': translated['id'],
                'text': translated['question'],
                'type': translated['type'],
                'options': translated.get('options', []),
                'other_label': translated.get('other_label', ''),
                'placeholder': translated.get('placeholder', ''),
                'hint': translated.get('hint', ''),
                'optional': translated.get('optional', False),
                'number': q_index + 1,
                'total': total,
                'question_video': media_info['url'],
                'video_is_fallback': media_info['is_fallback'],
                'next_question_video': next_media_info['url'] if next_media_info else None,
                'error_video_url': error_video_url,
                'error_video': error_video_url or f"/media/interview/english/{translated['error_video']}",
                'idle_video': '/media/interview/english/idle_waiting.mp4',
            },
            'progress': int((q_index / total) * 100) if total else 100,
            'ui': ui_trans,
            'debug': debug_info,
        })
    except Exception:
        logger.exception('Could not resolve the next interview question')
        return JsonResponse({'error': 'Could not load the next question.'}, status=400)


@require_http_methods(['POST'])
def submit_answer(request):
    try:
        data = json.loads(request.body)
        raw_value = data.get('value', '')
        if not isinstance(raw_value, str):
            return JsonResponse({'valid': False, 'error': 'Please enter a text answer.'}, status=400)
        value = raw_value.strip()
        raw_question_id = data.get('question_id', '')
        answers = request.session.get('answers', {})
        addendum_text = None
        lang = request.session.get('interview_language') or request.session.get('language', 'en')
        if 'lang' in data and data['lang'] in SUPPORTED_LANGUAGES and len(answers) == 0:
            lang = data['lang']
            request.session['interview_language'] = lang
            request.session['language'] = lang
            request.session.modified = True
        q_index = request.session.get('q_index', 0)
        token_mode = request.session.get('token_interview', False)
        demo_mode = settings.DEBUG and request.session.get('demo_mode', False)
        if not token_mode and not demo_mode:
            return JsonResponse({'valid': False, 'error': 'Interview link required'}, status=403)
        if token_mode:
            try:
                q_id = int(raw_question_id)
            except (TypeError, ValueError):
                return JsonResponse({'valid': False, 'error': 'Question mismatch.'}, status=400)
            active_qs = get_dmcore_active_questions(request.session.get('dmcore_play_list', []), answers)
        else:
            q_id = raw_question_id
            active_qs = get_active_questions(answers)
        if q_index >= len(active_qs):
            return JsonResponse({'done': True})
            
        q = active_qs[q_index]
        if q['id'] != q_id and q.get('field') != q_id and q.get('key') != q_id and str(q['id']) != str(q_id):
            return JsonResponse({'valid': False, 'error': 'Question mismatch.'}, status=400)
        if len(raw_value) > 10000:
            return JsonResponse({'valid': False, 'error': 'Please enter an answer of up to 10,000 characters.'}, status=400)

        # Check if typed input is English-only
        if value:
            is_option_q = q['type'] in ['options', 'options_or_text']
            is_valid_translated_option = False
            if is_option_q:
                options_english = q.get('options', [])
                options_translated = []
                if not addendum_text and lang != 'en':
                    lang_translations = TRANSLATIONS.get(lang, {}).get('questions', {}).get(q.get('translation_key', q['id']), {})
                    options_translated = lang_translations.get('options_translated', [])
                
                normalized_value = value.strip().lower()
                if any(opt.strip().lower() == normalized_value for opt in options_translated) or \
                   any(opt.strip().lower() == normalized_value for opt in options_english) or \
                   (map_option_to_canonical_english(q['id'], value, lang) in options_english):
                    is_valid_translated_option = True
                    
            if not is_valid_translated_option:
                # Bypass English-only check for cover_note if Hindi is selected
                is_cover_note_hindi = (q['id'] == 18 and lang == 'hi')
                if not is_cover_note_hindi:
                    english_pattern = re.compile(r'^[\sA-Za-z0-9!"#$%&\'()*+,\-./:;<=>?@\[\\\]^_`{|}~\u2010-\u201f\u2026\u2022\u20B9\u20A8\xA3\u20AC]*$')
                    if not english_pattern.match(value):
                        error_msg = "Please enter your response in English only."
                        if not addendum_text and lang != 'en':
                            lang_data = TRANSLATIONS.get(lang, {})
                            error_msg = lang_data.get('errors', {}).get('english_only', error_msg)
                        error_media = resolve_error_media(lang, q.get('key', ''), reason='invalid', legacy_error_video=q.get('error_video', ''))
                        error_video_url = error_media['url'] if error_media else None

                        return JsonResponse({  # first
                            'valid': False,
                            'reason': 'invalid',
                            'error': error_msg,
                            'error_text': error_msg,
                            'error_video_url': error_video_url,
                            'error_video': error_video_url,
                            'idle_video': '/media/interview/english/idle_waiting.mp4'
                        })


                        return JsonResponse({  # first
                            'valid': False,
                            'error': error_msg,
                            'error_video': error_video_url,
                            'idle_video': '/media/interview/english/idle_waiting.mp4'
                        })
            
        # Option mapping & numeric/email normalization
        is_option_q = q['type'] in ['options', 'options_or_text']
        if is_option_q and value:
            value_english = map_option_to_canonical_english(q['id'], value, lang)
        elif q['id'] in (3, 'phone') or q.get('key') == 'phone':
            value_english = clean_and_normalize_number(value, lang, 'phone')
        elif q['id'] in (8, 'graduation_year') or q.get('key') == 'graduation_year':
            value_english = clean_and_normalize_number(value, lang, 'year')
        elif q['id'] in (9, 'academic_performance') or q.get('key') == 'academic_performance':
            value_english = clean_and_normalize_number(value, lang, 'cgpa')
        elif q['id'] in (2, 'email') or q.get('key') == 'email':
            value_english = clean_transcribed_email(value)
        elif lang != 'en' and value:
            indic_pattern = re.compile(r'[ऀ-ॿ஀-௿ఀ-౿ഀ-ൿ]')
            if indic_pattern.search(value):
                if q['id'] not in [1, 2, 6, 7, 17]:
                    cache_key = f"trans_{lang}_{value}"
                    cache = get_translation_cache(request)
                    if cache_key in cache:
                        value_english = cache[cache_key]
                    else:
                        value_english = translate_to_english_via_groq(value, lang, q.get('key', ''))
                        cache[cache_key] = value_english
                        save_translation_cache(request, cache)
                else:
                    value_english = value
            else:
                value_english = value
        else:
            value_english = value

        validation_res = validate_answer(q, value_english, answers=answers)
        is_valid, error_msg = validation_res[0], validation_res[1]
        reason = getattr(validation_res, 'reason', None)
        if not is_valid and not reason:
            if is_empty_or_filler(value_english) or is_empty_or_filler(value):
                reason = 'empty'
            else:
                reason = 'invalid'
        if is_valid:
            value_english = error_msg if error_msg else value_english
            invalid_attempts = request.session.get('invalid_attempts', {})
            if str(q['id']) in invalid_attempts:
                invalid_attempts.pop(str(q['id']), None)
                request.session['invalid_attempts'] = invalid_attempts
                request.session.modified = True
        if not is_valid:
            invalid_attempts = request.session.get('invalid_attempts', {})
            q_id_str = str(q['id'])
            current_attempts = invalid_attempts.get(q_id_str, 0) + 1
            MAX_INVALID_ATTEMPTS = 3
            attempts_left = MAX_INVALID_ATTEMPTS - current_attempts
            addendum_text = get_error_text(q.get('key', ''), reason, lang=lang)
            if addendum_text:
                error_msg_translated = addendum_text
            else:
                error_msg_translated = error_msg
            if not addendum_text and lang != 'en':
                lang_data = TRANSLATIONS.get(lang, {})
                errors_map = lang_data.get('errors', {})
                error_video_fn = q.get('error_video', '')
                if error_video_fn in errors_map:
                    error_msg_translated = errors_map[error_video_fn]
                else:
                    cache_key = f"err_{lang}_{error_msg}"
                    cache = get_translation_cache(request)
                    if cache_key in cache:
                        error_msg_translated = cache[cache_key]
                    else:
                        error_msg_translated = translate_to_lang_via_groq(error_msg, lang)
                        cache[cache_key] = error_msg_translated
                        save_translation_cache(request, cache)
                    
            error_media = resolve_error_media(lang, q.get('key', ''), reason=reason, legacy_error_video=q.get('error_video', ''))
            error_video_url = error_media['url'] if error_media else None

            if attempts_left <= 0:
                logger.warning('Question %s failed %s validation attempts; skipping question without saving.', q['id'], MAX_INVALID_ATTEMPTS)
                invalid_attempts.pop(q_id_str, None)
                request.session['invalid_attempts'] = invalid_attempts
                request.session['q_index'] = q_index + 1
                request.session.modified = True

                if token_mode:
                    active_qs = get_dmcore_active_questions(request.session.get('dmcore_play_list', []), answers)
                else:
                    active_qs = get_active_questions(answers)
                new_index = request.session['q_index']
                total = len(active_qs)
                done = new_index >= total
                return JsonResponse({
                    'valid': False,
                    'reason': reason,
                    'skipped': True,
                    'done': done,
                    'attempts_left': 0,
                    'error_video_url': error_video_url,
                    'error_video': error_video_url,
                    'error_text': error_msg_translated,
                    'error': error_msg_translated,
                    'progress': int((new_index / total) * 100) if total else 100,
                    'completion_video': static(VIDEO_BASE + 'q_complete.mp4') if done else None,
                    'ui': TRANSLATIONS.get(lang, {}).get('ui', {})
                })

            invalid_attempts[q_id_str] = current_attempts
            request.session['invalid_attempts'] = invalid_attempts
            request.session.modified = True

            return JsonResponse({'valid': False, 'reason': reason, 'error': error_msg_translated, 'error_text': error_msg_translated, 'error_video_url': error_video_url, 'attempts_left': attempts_left,
                'error_video': error_video_url,
                'idle_video': '/media/interview/english/idle_waiting.mp4'})
                
        if token_mode:
            is_skipped_optional = q.get('optional', False) and not value_english.strip()
            if not is_skipped_optional and value_english:
                token = request.session.get('dmcore_token', '')
                answer_text = value_english[:855]
                saved = False
                is_400 = False

                for attempt in range(2):
                    try:
                        save_answer(token, q['id'], answer_text)
                        saved = True
                        break
                    except DmcoreError as error:
                        if error.status == 400:
                            logger.warning('DMCore returned 400 for unknown question_id=%s; continuing without saving', q['id'])
                            is_400 = True
                            break
                        if attempt == 0:
                            logger.warning('DMCore answer save failed for question_id=%s (HTTP %s); retrying once', q['id'], error.status)
                        else:
                            logger.error('DMCore answer save failed after retry for question_id=%s (HTTP %s)', q['id'], error.status)

                if not saved and not is_400:
                    unsaved = request.session.get('unsaved_answers', [])
                    unsaved.append({'question_id': q['id'], 'answer': answer_text})
                    request.session['unsaved_answers'] = unsaved
                    request.session.modified = True

        answers[q['field']] = value_english
        request.session['answers'] = answers
        request.session['q_index'] = q_index + 1
        request.session.modified = True
        if token_mode:
            active_qs = get_dmcore_active_questions(request.session.get('dmcore_play_list', []), answers)
        else:
            active_qs = get_active_questions(answers)
        new_index = request.session['q_index']
        total = len(active_qs)
        done = new_index >= total
        return JsonResponse({'valid': True, 'done': done,
            'progress': int((new_index / total) * 100) if total else 100,
            'completion_video': static(VIDEO_BASE + 'q_complete.mp4') if done else None,
            'ui': TRANSLATIONS.get(lang, {}).get('ui', {})})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'error': str(e)}, status=400)


@require_http_methods(['POST'])
def transcribe_audio(request):
    import os
    import tempfile
    from django.conf import settings
    
    try:
        audio_file = request.FILES.get('audio')
        lang_code = request.POST.get('language', 'en')
        question_id = request.POST.get('question_id', '')
        
        if not audio_file:
            return JsonResponse({'error': 'No audio file provided'}, status=400)
            
        # Route Hindi cover_note (tell about yourself) question to Sarvam AI Speech-to-Text API
        if lang_code == 'hi' and str(question_id) in ('18', 'cover_note'):
            if not hasattr(settings, 'SARVAM_API_KEY') or not settings.SARVAM_API_KEY:
                return JsonResponse({'error': 'Sarvam AI API key not configured on server.'}, status=500)
            
            import requests
            url = "https://api.sarvam.ai/speech-to-text"
            headers = {
                "api-subscription-key": settings.SARVAM_API_KEY
            }
            
            ext = audio_file.name.split('.')[-1] if '.' in audio_file.name else 'webm'
            with tempfile.NamedTemporaryFile(suffix=f'.{ext}', delete=False) as tmp:
                for chunk in audio_file.chunks():
                    tmp.write(chunk)
                tmp_path = tmp.name
                
            try:
                with open(tmp_path, 'rb') as f:
                    files = {
                        'file': (audio_file.name or f'audio.{ext}', f, f'audio/{ext}')
                    }
                    payload = {
                        'model': 'saaras:v3',
                        'language_code': 'hi-IN'
                    }
                    response = requests.post(url, headers=headers, files=files, data=payload)
                
                if response.status_code == 200:
                    res_data = response.json()
                    transcript_text = res_data.get('transcript', '')
                else:
                    try:
                        print(f"DEBUG STT (Sarvam AI) Error: {response.status_code} - {response.text}")
                    except UnicodeEncodeError:
                        print(f"DEBUG STT (Sarvam AI) Error: {response.status_code} - {response.text.encode('ascii', 'backslashreplace').decode('ascii')}")
                    return JsonResponse({'error': f"Sarvam AI STT failed: {response.text}"}, status=response.status_code)
            finally:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
                    
            return JsonResponse({'text': transcript_text})
            
        # For all other cases, use Groq Whisper
        if not hasattr(settings, 'GROQ_API_KEY') or not settings.GROQ_API_KEY:
            return JsonResponse({'error': 'Groq API key not configured on server.'}, status=500)
            
        from groq import Groq
        client = Groq(api_key=settings.GROQ_API_KEY)
        
        ext = audio_file.name.split('.')[-1] if '.' in audio_file.name else 'webm'
        with tempfile.NamedTemporaryFile(suffix=f'.{ext}', delete=False) as tmp:
            for chunk in audio_file.chunks():
                tmp.write(chunk)
            tmp_path = tmp.name
            
        # Always transcribe as English since only English is needed for STT
        print(f"DEBUG STT: Transcribing English audio using Whisper transcriptions")
        
        try:
            with open(tmp_path, 'rb') as f:
                transcription = client.audio.transcriptions.create(
                    file=(audio_file.name or f'audio.{ext}', f),
                    model="whisper-large-v3",
                    language="en",
                    prompt="English conversation.",
                )
            transcript_text = transcription.text
            if question_id == '2':
                transcript_text = clean_transcribed_email(transcript_text)
            elif question_id == '3':
                transcript_text = clean_transcribed_phone(transcript_text)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            
        return JsonResponse({'text': transcript_text})
    except ImportError:
        return JsonResponse({'error': 'Groq package is not installed on the server.'}, status=500)
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return JsonResponse({'error': str(e)}, status=400)



@require_http_methods(['POST'])
def complete_application(request):
    try:
        if request.session.get('token_interview', False):
            play_list = get_dmcore_active_questions(request.session.get('dmcore_play_list', []), request.session.get('answers', {}))
            if not play_list or request.session.get('q_index', 0) < len(play_list):
                return JsonResponse({'error': 'Interview is not complete'}, status=403)

            token = request.session.get('dmcore_token', '')
            unsaved_answers = request.session.get('unsaved_answers', [])
            if unsaved_answers:
                still_unsaved = []
                for item in unsaved_answers:
                    try:
                        save_answer(token, item['question_id'], item['answer'])
                    except DmcoreError as err:
                        if err.status == 400:
                            logger.warning('DMCore returned 400 during final retry for question_id=%s; continuing', item['question_id'])
                        else:
                            logger.error('Final retry to save question_id=%s failed: %s', item['question_id'], err)
                            still_unsaved.append(item)
                request.session['unsaved_answers'] = still_unsaved
                request.session.modified = True
                if still_unsaved:
                    logger.error('Failed to save %d answer(s) to DMCore at the end of interview', len(still_unsaved))
                    return JsonResponse({'error': 'We could not save your interview answers. Please try again or contact the recruiter.'}, status=503)

            if not request.session.get('interview_finished', False):
                for attempt in range(3):
                    try:
                        dmcore_complete_interview(token)
                        request.session['interview_finished'] = True
                        request.session.modified = True
                        break
                    except DmcoreError as error:
                        if attempt == 2:
                            logger.error('DMCore interview completion failed after retries (category=%s, HTTP %s): %s', error.kind, error.status, error)
                            return JsonResponse({'error': _dmcore_public_error(error)}, status=503)
                        else:
                            time.sleep(0.4)
            return JsonResponse({'success': True})
        if not (settings.DEBUG and request.session.get('demo_mode', False)):
            return JsonResponse({'error': 'Interview link required'}, status=403)
        answers = request.session.get('answers', {})
        addendum_text = None
        if not answers:
            return JsonResponse({'error': 'No answers found'}, status=400)
        has_exp_raw = answers.get('has_experience', '')
        has_exp_bool = True if 'Yes' in has_exp_raw else (False if has_exp_raw else None)
        app = CandidateApplication.objects.create(
            full_name=answers.get('full_name', ''),
            email=answers.get('email', ''),
            phone=answers.get('phone', ''),
            applied_role=answers.get('applied_role', ''),
            qualification=answers.get('qualification', ''),
            field_of_study=answers.get('field_of_study', ''),
            institution=answers.get('institution', ''),
            graduation_year=answers.get('graduation_year', ''),
            cgpa=answers.get('cgpa', ''),
            has_experience=has_exp_bool,
            company=answers.get('company', ''),
            previous_role=answers.get('previous_role', ''),
            work_duration=answers.get('work_duration', ''),
            skills=answers.get('skills', ''),
            notice_period=answers.get('notice_period', ''),
            expected_salary=answers.get('expected_salary', ''),
            linkedin=answers.get('linkedin', ''),
            cover_note=answers.get('cover_note', ''),
            status='completed',
            session_key=request.session.session_key or '',
        )
        request.session['answers'] = {}
        request.session['q_index'] = 0
        request.session.modified = True
        return JsonResponse({'success': True, 'application_id': app.id})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

def text_to_speech(request):
    import io
    import os
    import hashlib
    from django.http import HttpResponse
    from django.conf import settings
    from gtts import gTTS
    
    text = request.GET.get('text', '').strip()
    lang = request.GET.get('lang', 'en')
    
    if not text:
        return HttpResponse('No text provided', status=400)
        
    try:
        if lang not in ['ml', 'hi', 'ta', 'te', 'en']:
            lang = 'en'
            
        # Create cache directory
        cache_dir = os.path.join(settings.BASE_DIR, 'tts_cache')
        os.makedirs(cache_dir, exist_ok=True)
        
        # Calculate hash for cache filename
        cache_key = hashlib.md5(f"{lang}_{text}".encode('utf-8')).hexdigest()
        cache_file = os.path.join(cache_dir, f"{cache_key}.mp3")
        
        if os.path.exists(cache_file):
            with open(cache_file, 'rb') as f:
                audio_data = f.read()
        else:
            tts = gTTS(text=text, lang=lang)
            fp = io.BytesIO()
            tts.write_to_fp(fp)
            fp.seek(0)
            audio_data = fp.read()
            # Save to cache
            with open(cache_file, 'wb') as f:
                f.write(audio_data)
                
        response = HttpResponse(audio_data, content_type='audio/mp3')
        response['Content-Disposition'] = 'inline; filename="speech.mp3"'
        return response
    except Exception as e:
        return HttpResponse(str(e), status=500)


def success(request):
    app_id = request.GET.get('id')
    app = None
    if app_id:
        try:
            app = CandidateApplication.objects.get(id=app_id)
        except CandidateApplication.DoesNotExist:
            pass
    return render(request, 'screening/success.html', {'application': app})


# ─── HR Auth ───────────────────────────────────────────────────────────

def hr_signup(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    form = HRSignupForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        d = form.cleaned_data
        user = User.objects.create_user(
            username=d['email'],
            email=d['email'],
            password=d['password1'],
            first_name=d['first_name'],
            last_name=d['last_name'],
            is_active=True,
        )
        HRProfile.objects.create(
            user=user,
            company=d['company'],
            designation=d['designation'],
            phone=d['phone'],
            approval_status='pending',
        )
        return render(request, 'screening/hr_signup_done.html', {'name': d['first_name']})
    return render(request, 'screening/hr_signup.html', {'form': form})


@never_cache
def hr_login(request):
    if request.user.is_authenticated:
        if request.user.is_superuser:
            return redirect('admin_panel')
        return redirect('dashboard')
    error = None
    if request.method == 'POST':
        login_input = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')

        # Try authenticating directly (works if they typed their username)
        user = authenticate(request, username=login_input, password=password)

        # If that failed, try treating the input as an email address
        if user is None:
            try:
                matched = User.objects.get(email__iexact=login_input)
                user = authenticate(request, username=matched.username, password=password)
            except User.DoesNotExist:
                pass

        if user is None:
            error = 'Invalid username/email or password.'
        elif user.is_superuser:
            # Superusers have no HRProfile — grant access directly
            login(request, user)
            return redirect('admin_panel')
        else:
            try:
                profile = user.hr_profile
            except HRProfile.DoesNotExist:
                error = 'No HR profile found for this account.'
                profile = None
            if profile:
                if profile.approval_status == 'pending':
                    error = 'Your account is awaiting admin approval. You will be notified by email.'
                elif profile.approval_status == 'rejected':
                    error = f'Your account was not approved. Reason: {profile.rejection_reason or "Contact admin."}'
                else:
                    login(request, user)
                    return redirect('dashboard')
    return render(request, 'screening/hr_login.html', {'error': error})


def hr_logout(request):
    logout(request)
    return redirect('hr_login')


# ─── HR Dashboard (protected) ──────────────────────────────────────────

def hr_required(view_func):
    """Decorator: must be logged in AND approved HR."""
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('hr_login')
        if not request.user.is_superuser:
            try:
                if not request.user.hr_profile.is_approved():
                    return redirect('hr_login')
            except HRProfile.DoesNotExist:
                return redirect('hr_login')
        return view_func(request, *args, **kwargs)
    return wrapper


@hr_required
def dashboard(request):
    applications = CandidateApplication.objects.all()
    status_filter = request.GET.get('status', '')
    role_filter   = request.GET.get('role', '')
    if status_filter:
        applications = applications.filter(status=status_filter)
    if role_filter:
        applications = applications.filter(applied_role=role_filter)
    roles    = CandidateApplication.objects.values_list('applied_role', flat=True).distinct()
    stats = {
        'total':       CandidateApplication.objects.count(),
        'completed':   CandidateApplication.objects.filter(status='completed').count(),
        'shortlisted': CandidateApplication.objects.filter(status='shortlisted').count(),
        'reviewed':    CandidateApplication.objects.filter(status='reviewed').count(),
    }
    return render(request, 'screening/dashboard.html', {
        'applications': applications, 'roles': roles,
        'statuses': CandidateApplication.STATUS_CHOICES,
        'status_filter': status_filter, 'role_filter': role_filter,
        'stats': stats, 'hr_user': request.user,
    })


@hr_required
def application_detail(request, pk):
    app = get_object_or_404(CandidateApplication, pk=pk)
    if request.method == 'POST':
        new_status = request.POST.get('status')
        if new_status in dict(CandidateApplication.STATUS_CHOICES):
            app.status = new_status
            app.save()
        return redirect('application_detail', pk=pk)
    return render(request, 'screening/application_detail.html', {'application': app})


# ── CSRF token endpoint (cookie-blocked browser fallback) ───────────────
from django.middleware.csrf import get_token
from django.views.decorators.csrf import ensure_csrf_cookie
from django.utils import timezone

@ensure_csrf_cookie
def csrf_token_view(request):
    """Returns CSRF token in JSON body AND sets the cookie.
    Called by JS when document.cookie is empty/blocked."""
    return JsonResponse({'csrfToken': get_token(request)})


# ─── Admin Panel (superuser only) ─────────────────────────────────────────

def superuser_required(view_func):
    """Decorator: must be logged in AND is_superuser."""
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('hr_login')
        if not request.user.is_superuser:
            return redirect('dashboard')
        return view_func(request, *args, **kwargs)
    return wrapper


@superuser_required
def admin_panel(request):
    status_filter = request.GET.get('status', '')
    profiles = HRProfile.objects.select_related('user', 'approved_by').all()
    if status_filter:
        profiles = profiles.filter(approval_status=status_filter)

    # Handle bulk approve / reject
    if request.method == 'POST':
        action   = request.POST.get('bulk_action', '')
        selected = request.POST.getlist('selected_ids')
        if selected and action in ('approve', 'reject'):
            qs = HRProfile.objects.filter(pk__in=selected)
            if action == 'approve':
                qs.update(
                    approval_status='approved',
                    approved_by=request.user,
                    approved_at=timezone.now(),
                )
                messages.success(request, f'{qs.count()} account(s) approved.')
            else:
                qs.update(approval_status='rejected')
                messages.warning(request, f'{qs.count()} account(s) rejected.')
        return redirect('admin_panel')

    stats = {
        'total':    HRProfile.objects.count(),
        'pending':  HRProfile.objects.filter(approval_status='pending').count(),
        'approved': HRProfile.objects.filter(approval_status='approved').count(),
        'rejected': HRProfile.objects.filter(approval_status='rejected').count(),
    }
    statuses = HRProfile.STATUS_CHOICES
    return render(request, 'screening/admin_panel.html', {
        'hr_profiles':   profiles,
        'stats':         stats,
        'statuses':      statuses,
        'status_filter': status_filter,
    })


@superuser_required
def hr_detail(request, pk):
    profile = get_object_or_404(HRProfile, pk=pk)
    return render(request, 'screening/hr_detail.html', {'profile': profile})


@superuser_required
def hr_approval_action(request, pk):
    profile = get_object_or_404(HRProfile, pk=pk)
    error = None
    if request.method == 'POST':
        action           = request.POST.get('action', '')
        rejection_reason = request.POST.get('rejection_reason', '').strip()
        if action == 'approve':
            profile.approval_status = 'approved'
            profile.approved_by     = request.user
            profile.approved_at     = timezone.now()
            profile.rejection_reason = ''
            profile.save()
            messages.success(request, f'{profile.user.get_full_name()} has been approved.')
            return redirect('admin_panel')
        elif action == 'reject':
            if not rejection_reason:
                error = 'Please provide a rejection reason.'
            else:
                profile.approval_status  = 'rejected'
                profile.rejection_reason = rejection_reason
                profile.approved_by      = request.user
                profile.approved_at      = timezone.now()
                profile.save()
                messages.warning(request, f'{profile.user.get_full_name()} has been rejected.')
                return redirect('admin_panel')
        else:
            error = 'Invalid action.'
    return render(request, 'screening/hr_approval_action.html', {
        'profile': profile,
        'form':    {'non_field_errors': [error]} if error else {},
    })

