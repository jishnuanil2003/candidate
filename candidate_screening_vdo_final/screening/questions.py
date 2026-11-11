"""One canonical lookup for the permanent DMCore interview question IDs."""
import datetime
import logging
import zoneinfo
import re

logger = logging.getLogger(__name__)
NO_QUESTIONS_MESSAGE = 'No interview questions are available right now, please contact the recruiter'
FRESHER_ANSWER = 'No, I am a fresher'
MAX_INVALID_ATTEMPTS = 3

MONTH_MAP = {
    'january': 1, 'jan': 1, 'february': 2, 'feb': 2, 'march': 3, 'mar': 3,
    'april': 4, 'apr': 4, 'may': 5, 'june': 6, 'jun': 6, 'july': 7, 'jul': 7,
    'august': 8, 'aug': 8, 'september': 9, 'sep': 9, 'sept': 9, 'october': 10, 'oct': 10,
    'november': 11, 'nov': 11, 'december': 12, 'dec': 12,
    # Hindi
    'जनवरी': 1, 'फ़रवरी': 2, 'फरवरी': 2, 'मार्च': 3, 'अप्रैल': 4, 'मई': 5, 'जून': 6,
    'जुलाई': 7, 'अगस्त': 8, 'सितंबर': 9, 'सितम्बर': 9, 'अक्टूबर': 10, 'अक्तूबर': 10,
    'नवंबर': 11, 'नवम्बर': 11, 'दिसंबर': 12, 'दिसम्बर': 12,
    # Malayalam
    'ജനുവരി': 1, 'ഫെബ്രുവരി': 2, 'മാർച്ച്': 3, 'ഏപ്രിൽ': 4, 'മെയ്': 5, 'ജൂൺ': 6,
    'ജൂലൈ': 7, 'ഓഗസ്റ്റ്': 8, 'സെപ്റ്റംബർ': 9, 'ഒക്ടോബർ': 10, 'നവംബർ': 11, 'ഡിസംബർ': 12,
    # Tamil
    'ஜனவரி': 1, 'பிப்ரவரி': 2, 'மார்ச்': 3, 'ஏப்ரல்': 4, 'மே': 5, 'ஜூன்': 6,
    'ஜூலை': 7, 'ஆகஸ்ட்': 8, 'செப்டம்பர்': 9, 'அக்டோபர்': 10, 'நவம்பர்': 11, 'டிசம்பர்': 12,
    # Telugu
    'జనవరి': 1, 'ఫిబ్రవరి': 2, 'మార్చి': 3, 'ఏప్రిల్': 4, 'మే': 5, 'జూన్': 6,
    'జూలై': 7, 'ఆగస్టు': 8, 'సెప్టెంబర్': 9, 'అక్టోబర్': 10, 'నవంబర్': 11, 'డిసెంబర్': 12,
}

MONTH_NAMES = {
    1: 'January', 2: 'February', 3: 'March', 4: 'April', 5: 'May', 6: 'June',
    7: 'July', 8: 'August', 9: 'September', 10: 'October', 11: 'November', 12: 'December'
}


def get_current_kolkata_year_month():
    try:
        now = datetime.datetime.now(zoneinfo.ZoneInfo('Asia/Kolkata'))
    except Exception:
        tz = datetime.timezone(datetime.timedelta(hours=5, minutes=30))
        now = datetime.datetime.now(tz)
    return now.year, now.month


def parse_month_year(value):
    val = value.strip().lower()
    val = re.sub(r'[,/\-]', ' ', val)
    tokens = val.split()

    month = None
    year = None

    for t in tokens:
        if t in MONTH_MAP:
            month = MONTH_MAP[t]
        elif t.isdigit():
            num = int(t)
            if 1900 <= num <= 2100:
                year = num
            elif 1 <= num <= 12 and month is None:
                month = num

    if not (month and year):
        m = re.search(r'\b(0?[1-9]|1[0-2])\s+(20\d\d)\b', val)
        if m:
            month = int(m.group(1))
            year = int(m.group(2))
        else:
            m = re.search(r'\b(20\d\d)\s+(0?[1-9]|1[0-2])\b', val)
            if m:
                year = int(m.group(1))
                month = int(m.group(2))

    return month, year


class ValidationResult(tuple):
    """
    Tuple representing (is_valid, value_or_msg).
    Unpacks as 2 items for 100% backward compatibility with `is_valid, msg = validate(...)`.
    Exposes `res.reason` ('empty', 'invalid', 'before_start', or None).
    """
    def __new__(cls, is_valid, value_or_msg, reason=None):
        return super().__new__(cls, (is_valid, value_or_msg))

    def __init__(self, is_valid, value_or_msg, reason=None):
        self.is_valid = is_valid
        self.value_or_msg = value_or_msg
        self.reason = reason


FILLER_WORDS = {
    'um', 'uh', 'ah', 'er', 'hmm', 'hm', 'mm', 'mmm', 'uhh', 'umm', 'ahh',
    '...', '.', '..', '-', '--', 'none', 'n/a', 'na', 'nil', 'null', 'nothing',
    'no answer', 'silence', '[silence]', '(silence)', '[no speech]', '(no speech)',
    '[blank]', '(blank)', 'filler',
}


def is_empty_or_filler(text):
    if not text:
        return True
    val = text.strip().lower()
    if not val:
        return True
    cleaned = re.sub(r'^[.\-,\s]+|[.\-,\s]+$', '', val)
    if not cleaned:
        return True
    if cleaned in FILLER_WORDS:
        return True
    tokens = [t.strip('.,-') for t in cleaned.split()]
    if tokens and all(t in FILLER_WORDS for t in tokens):
        return True
    return False


def validate_lead_source(value, answers=None):
    if is_empty_or_filler(value):
        return ValidationResult(False, "I don't have that on record yet. How did you first hear about us?", reason='empty')
    val = value.strip()
    if val.isdigit():
        return ValidationResult(False, "Sorry, I couldn't catch that. Was it a friend, social media, your college, or a job portal?", reason='invalid')
    letters = re.findall(r'[a-zA-Z]', val)
    if len(letters) < 2:
        return ValidationResult(False, "Sorry, I couldn't catch that. Was it a friend, social media, your college, or a job portal?", reason='invalid')

    val_lower = val.lower()

    friend_keywords = ['friend', 'friends', 'referral', 'referred', 'colleague', 'coworker', 'peer', 'relative', 'family']
    if any(re.search(r'\b' + re.escape(kw) + r'\b', val_lower) for kw in friend_keywords):
        return ValidationResult(True, "Friend/Referral")

    campus_keywords = ['college', 'campus', 'university', 'placement', 'placement cell', 'faculty', 'professor', 'teacher', 'institute', 'school']
    if any(kw in val_lower for kw in campus_keywords):
        return ValidationResult(True, "College/Campus")

    # Job portal category (checked before social_keywords so "LinkedIn Jobs" matches Job Portal, not Social Media)
    job_portal_keywords = [
        'job portal', 'job site', 'job board', 'portal', 'naukri', 'indeed',
        'linkedin jobs', 'linkedin job', 'internshala', 'monster', 'hirist',
        'glassdoor', 'foundit', 'shine', 'instahyre', 'unstop', 'cuvette',
        'wellfound', 'angelist', 'angellist', 'hiring portal', 'career site', 'careers page',
    ]
    if any(re.search(r'\b' + re.escape(kw) + r'\b', val_lower) if ' ' not in kw else kw in val_lower for kw in job_portal_keywords):
        return ValidationResult(True, "Job Portal")

    social_keywords = ['social media', 'social', 'instagram', 'facebook', 'linkedin', 'youtube', 'whatsapp', 'twitter', 'reddit', 'telegram', 'tiktok']
    if any(kw in val_lower for kw in social_keywords):
        return ValidationResult(True, "Social Media")

    clean_other = re.sub(r'^(other\s*:?\s*)', '', val, flags=re.IGNORECASE).strip()
    return ValidationResult(True, f"Other: {clean_other}")


def validate_location(value, answers=None):
    if is_empty_or_filler(value):
        return ValidationResult(False, "I still need your current location. Which city or town do you live in?", reason='empty')
    val = value.strip()
    if len(val) < 2 or len(val) > 60:
        return ValidationResult(False, "I couldn't recognise that place. Could you tell me the name of your city or town again?", reason='invalid')
    if val.isdigit() or re.sub(r'[\s\d+\-(),.]', '', val) == '':
        return ValidationResult(False, "I couldn't recognise that place. Could you tell me the name of your city or town again?", reason='invalid')
    digits = re.findall(r'\d', val)
    if len(digits) >= 7:
        return ValidationResult(False, "I couldn't recognise that place. Could you tell me the name of your city or town again?", reason='invalid')
    letters = re.findall(r'[a-zA-Z]', val)
    if len(letters) < 2:
        return ValidationResult(False, "I couldn't recognise that place. Could you tell me the name of your city or town again?", reason='invalid')
    non_space_chars = len(re.sub(r'\s+', '', val))
    if len(letters) / max(non_space_chars, 1) < 0.5:
        return ValidationResult(False, "I couldn't recognise that place. Could you tell me the name of your city or town again?", reason='invalid')
    return ValidationResult(True, val)


def validate_internship_done(value, answers=None):
    if is_empty_or_filler(value):
        return ValidationResult(False, "I haven't noted this yet. Have you completed any internship so far?", reason='empty')
    val_lower = value.strip().lower()
    no_synonyms = ['no', 'nope', 'nah', 'not done', 'never', "haven't", 'have not', 'fresher', 'no, i am a fresher', 'ഇല്ല', 'नहीं', 'இல்லை', 'లేదు']
    if any(s == val_lower for s in ['no', 'nope', 'nah']) or any(s in val_lower for s in ['fresher', 'not done', "haven't"]) or val_lower in no_synonyms or any(s in value for s in ['ഇല്ല', 'नहीं', 'இல்லை', 'లేదు']):
        return ValidationResult(True, 'No')
    yes_synonyms = ['yes', 'yeah', 'yep', 'yup', 'done', 'i have', 'have done', 'yes, i have', 'yes i have', 'അതെ', 'हाँ', 'ஆம்', 'అవును']
    if any(s == val_lower for s in ['yes', 'yeah', 'yep', 'yup', 'done']) or any(s in val_lower for s in ['have done', 'i have', 'yes, i have', 'yes i have']) or any(s in value for s in ['അതെ', 'हाँ', 'ஆம்', 'అవును']):
        return ValidationResult(True, 'Yes')
    return ValidationResult(False, "Just to confirm, have you done an internship? A simple yes or no is fine.", reason='invalid')


def validate_internship_start_date(value, answers=None):
    if is_empty_or_filler(value):
        return ValidationResult(False, "When did your internship begin? The month and year is enough.", reason='empty')
    month, year = parse_month_year(value)
    if not (month and year):
        return ValidationResult(False, "That date doesn't look right. Could you tell me the month and year your internship started, like June 2025?", reason='invalid')
    cur_year, cur_month = get_current_kolkata_year_month()
    if year < 2000 or year > cur_year:
        return ValidationResult(False, "That date doesn't look right. Could you tell me the month and year your internship started, like June 2025?", reason='invalid')
    if year == cur_year and month > cur_month:
        return ValidationResult(False, "That date doesn't look right. Could you tell me the month and year your internship started, like June 2025?", reason='invalid')
    return ValidationResult(True, f"{MONTH_NAMES[month]} {year}")


def validate_internship_end_date(value, answers=None):
    if is_empty_or_filler(value):
        return ValidationResult(False, "I'm missing the end date. When did your internship finish, or is it still ongoing?", reason='empty')
    val_lower = value.strip().lower()
    if any(kw in val_lower for kw in ['ongoing', 'still going on', 'present', 'currently', 'continuing', 'current', 'till now']) or \
       any(kw in value for kw in ['തുടരുന്നു', 'चल रहा है', 'தொடர்கிறது', 'కొనసాగుతోంది']):
        return ValidationResult(True, 'Ongoing')

    month, year = parse_month_year(value)
    if not (month and year):
        return ValidationResult(False, "I couldn't catch the date. Could you tell me the month and year your internship ended, like June 2025, or say it's still going on?", reason='invalid')

    cur_year, cur_month = get_current_kolkata_year_month()
    if year < 2000 or year > cur_year:
        return ValidationResult(False, "I couldn't catch the date. Could you tell me the month and year your internship ended, like June 2025, or say it's still going on?", reason='invalid')
    if year == cur_year and month > cur_month:
        return ValidationResult(False, "I couldn't catch the date. Could you tell me the month and year your internship ended, like June 2025, or say it's still going on?", reason='invalid')

    if answers:
        start_raw = answers.get('internship_start_date') or answers.get(22) or answers.get('22')
        if start_raw:
            s_month, s_year = parse_month_year(str(start_raw))
            if s_month and s_year:
                if (year, month) < (s_year, s_month):
                    return ValidationResult(False, "That end date seems to come before the start date. Could you check and tell me again? If it's still going on, just say so.", reason='before_start')

    return ValidationResult(True, f"{MONTH_NAMES[month]} {year}")


def validate_internship_topic(value, answers=None):
    if is_empty_or_filler(value):
        return ValidationResult(False, "What was your internship about? Tell me the topic or the kind of work you did.", reason='empty')
    val = value.strip()
    if len(val) < 8:
        return ValidationResult(False, "I didn't quite get that. Could you describe in a few words what your internship was about?", reason='invalid')
    if not re.search(r'[a-zA-Z]', val):
        return ValidationResult(False, "I didn't quite get that. Could you describe in a few words what your internship was about?", reason='invalid')

    words = re.findall(r'[a-zA-Z0-9]+', val.lower())
    if len(words) > 1 and len(set(words)) == 1:
        return ValidationResult(False, "I didn't quite get that. Could you describe in a few words what your internship was about?", reason='invalid')

    if len(words) == 1:
        w = words[0]
        for chunk_len in range(1, len(w) // 2 + 1):
            if len(w) % chunk_len == 0:
                chunk = w[:chunk_len]
                if chunk * (len(w) // chunk_len) == w:
                    return ValidationResult(False, "I didn't quite get that. Could you describe in a few words what your internship was about?", reason='invalid')

    return ValidationResult(True, val)

# Keep this as the sole source of question IDs, local field keys, prompts,
# input metadata, and existing recorded video filenames.
QUESTION_LOOKUP = {
    1: {'id': 1, 'key': 'full_name', 'field': 'full_name', 'translation_key': 'full_name',
        'question_video': 'q_fullname.mp4', 'error_video': 'error_name.mp4',
        'question': "Hello, I'm Talentbot. Welcome to your screening interview. I'll guide you through a few quick questions. Just respond at your own pace. Let's begin. What is your <strong>full name</strong>?",
        'type': 'text', 'placeholder': 'e.g. Priya Sharma', 'hint': 'Enter your first and last name'},
    2: {'id': 2, 'key': 'email', 'field': 'email', 'translation_key': 'email',
        'question_video': 'q_email.mp4', 'error_video': 'error_email.mp4',
        'question': "Nice to meet you. Could you please share your <strong>email address</strong>? We'll use it to send you updates about your application.",
        'type': 'email', 'placeholder': 'e.g. priya@example.com', 'hint': 'Enter a valid email address'},
    3: {'id': 3, 'key': 'phone', 'field': 'phone', 'translation_key': 'phone',
        'question_video': 'q_phone.mp4', 'error_video': 'error_phone.mp4',
        'question': 'Thank you. What is your <strong>phone number</strong>? Please include your country code if outside India.',
        'type': 'text', 'placeholder': 'e.g. +91 9876543210', 'hint': 'Minimum 10 digits'},
    4: {'id': 4, 'key': 'role_applied', 'field': 'applied_role', 'translation_key': 'applied_role',
        'question_video': 'q_role.mp4', 'error_video': 'error_empty.mp4',
        'question': 'Which <strong>role</strong> are you applying for?', 'type': 'options_or_text',
        'options': ['Software Engineer', 'Data Analyst', 'UI/UX Designer', 'Product Manager', 'DevOps Engineer', 'QA Engineer'],
        'other_label': 'Other (type your role)', 'placeholder': 'Type your role', 'hint': 'Select a role or type another'},
    5: {'id': 5, 'key': 'highest_qualification', 'field': 'qualification', 'translation_key': 'qualification',
        'question_video': 'q_qualification.mp4', 'error_video': 'error_empty.mp4',
        'question': 'What is your <strong>highest educational qualification</strong>?', 'type': 'options',
        'options': ["Bachelor's Degree", "Master's Degree", 'PhD', 'Diploma', '12th / Higher Secondary', 'Other'],
        'hint': 'Select your highest level of education'},
    6: {'id': 6, 'key': 'field_of_study', 'field': 'field_of_study', 'translation_key': 'field_of_study',
        'question_video': 'q_field.mp4', 'error_video': 'error_empty.mp4',
        'question': 'What was your <strong>field of study or specialization</strong>?', 'type': 'text',
        'placeholder': 'e.g. Computer Science, Electronics, MBA', 'hint': 'Your major or specialisation'},
    7: {'id': 7, 'key': 'college', 'field': 'institution', 'translation_key': 'institution',
        'question_video': 'q_institution.mp4', 'error_video': 'error_empty.mp4',
        'question': 'Which <strong>college or university</strong> did you attend?', 'type': 'text',
        'placeholder': 'Enter the full name of your college or university'},
    8: {'id': 8, 'key': 'graduation_year', 'field': 'graduation_year', 'translation_key': 'graduation_year',
        'question_video': 'q_gradyear.mp4', 'error_video': 'error_year.mp4',
        'question': 'Which <strong>year did you graduate</strong> or expect to graduate?', 'type': 'text',
        'placeholder': 'e.g. 2023', 'hint': 'Enter a valid 4-digit year'},
    9: {'id': 9, 'key': 'academic_performance', 'field': 'cgpa', 'translation_key': 'cgpa',
        'question_video': 'q_cgpa.mp4', 'error_video': 'error_empty.mp4',
        'question': 'What was your <strong>overall academic performance</strong>? You can mention your CGPA or percentage.', 'type': 'text',
        'placeholder': 'e.g. 8.5 CGPA or 85%', 'hint': 'Enter your academic score'},
    10: {'id': 10, 'key': 'has_experience', 'field': 'has_experience', 'translation_key': 'has_experience',
         'question_video': 'q_experience.mp4', 'error_video': 'error_empty.mp4',
         'question': 'Do you have any <strong>prior work experience</strong>?', 'type': 'options',
         'options': ['Yes, I have experience', FRESHER_ANSWER], 'hint': 'This helps us personalise the interview'},
    11: {'id': 11, 'key': 'last_company', 'field': 'company', 'translation_key': 'company',
         'question_video': 'q_company.mp4', 'error_video': 'error_empty.mp4',
         'question': 'Which <strong>company</strong> did you most recently work at?', 'type': 'text',
         'placeholder': 'e.g. Infosys, TCS, Wipro', 'condition': {'field': 'has_experience', 'value': 'Yes, I have experience'}},
    12: {'id': 12, 'key': 'last_role', 'field': 'previous_role', 'translation_key': 'previous_role',
         'question_video': 'q_prevrole.mp4', 'error_video': 'error_empty.mp4',
         'question': 'What was your <strong>role or job title</strong> there?', 'type': 'text',
         'placeholder': 'e.g. Junior Developer, Business Analyst', 'condition': {'field': 'has_experience', 'value': 'Yes, I have experience'}},
    13: {'id': 13, 'key': 'experience_duration', 'field': 'work_duration', 'translation_key': 'work_duration',
         'question_video': 'q_duration.mp4', 'error_video': 'error_empty.mp4',
         'question': 'How long did you work there? Please select your <strong>total experience</strong>.', 'type': 'options',
         'options': ['Less than 1 year', '1-2 years', '2-4 years', '4-6 years', '6+ years'],
         'condition': {'field': 'has_experience', 'value': 'Yes, I have experience'}},
    14: {'id': 14, 'key': 'skills', 'field': 'skills', 'translation_key': 'skills',
         'question_video': 'q_skills.mp4', 'error_video': 'error_skills.mp4',
         'question': 'Could you list your <strong>top technical skills</strong>? Separate them with commas.', 'type': 'text',
         'placeholder': 'e.g. Python, Django, React, SQL', 'hint': 'Enter at least 2 skills'},
    15: {'id': 15, 'key': 'notice_period', 'field': 'notice_period', 'translation_key': 'notice_period',
         'question_video': 'q_notice.mp4', 'error_video': 'error_empty.mp4',
         'question': 'What is your <strong>notice period</strong> or how soon can you start?', 'type': 'options',
         'options': ['Immediate joiner', '2 weeks', '1 month', '2 months', '3+ months']},
    16: {'id': 16, 'key': 'expected_salary', 'field': 'expected_salary', 'translation_key': 'expected_salary',
         'question_video': 'q_salary.mp4', 'error_video': 'error_empty.mp4',
         'question': 'What is your <strong>expected annual salary range</strong>?', 'type': 'options',
         'options': ['3-5 LPA', '5-8 LPA', '8-12 LPA', '12-20 LPA', '20+ LPA']},
    17: {'id': 17, 'key': 'linkedin', 'field': 'linkedin', 'translation_key': 'linkedin',
         'question_video': 'q_linkedin.mp4', 'error_video': 'error_empty.mp4',
         'question': 'If you have a <strong>LinkedIn profile</strong>, please share the link. You can skip this if you prefer.', 'type': 'text',
         'placeholder': 'https://linkedin.com/in/yourname', 'hint': 'Optional — press Submit to skip', 'optional': True},
    18: {'id': 18, 'key': 'why_good_fit', 'field': 'cover_note', 'translation_key': 'cover_note',
         'question_video': 'q_cover.mp4', 'error_video': 'error_cover.mp4',
         'question': 'Could you briefly tell me why you are a <strong>good fit for this role</strong>? A couple of sentences will be perfect.', 'type': 'textarea',
         'placeholder': 'Tell us what makes you a great candidate for this role...', 'hint': 'Minimum 20 characters'},
    19: {'id': 19, 'key': 'lead_source', 'field': 'lead_source', 'translation_key': 'lead_source',
         'question_video': 'q19.mp4', 'error_video': 'lead_source_error.mp4',
         'question': 'How did you hear about this opportunity?', 'type': 'text',
         'placeholder': 'e.g. Friend, Social Media, Campus', 'hint': 'Tell us how you found this opening',
         'validator': validate_lead_source},
    20: {'id': 20, 'key': 'location', 'field': 'location', 'translation_key': 'location',
         'question_video': 'q20.mp4', 'error_video': 'location_error.mp4',
         'question': 'Which <strong>city or town</strong> are you currently located in?', 'type': 'text',
         'placeholder': 'e.g. Bengaluru, Mumbai, Kochi', 'hint': 'Enter your current city or town',
         'validator': validate_location},
    21: {'id': 21, 'key': 'internship_done', 'field': 'internship_done', 'translation_key': 'internship_done',
         'question_video': 'q21.mp4', 'error_video': 'internship_done_error.mp4',
         'question': 'Have you completed any <strong>internships</strong>?', 'type': 'options',
         'options': ['Yes', 'No'], 'hint': 'Select Yes or No',
         'validator': validate_internship_done},
    22: {'id': 22, 'key': 'internship_start_date', 'field': 'internship_start_date', 'translation_key': 'internship_start_date',
         'question_video': 'q22.mp4', 'error_video': 'internship_start_date_error.mp4',
         'question': 'When did your internship <strong>start</strong>? Please provide the month and year.', 'type': 'text',
         'placeholder': 'e.g. June 2025', 'hint': 'Enter month and year',
         'condition': {'field': 'internship_done', 'value': 'Yes'},
         'validator': validate_internship_start_date},
    23: {'id': 23, 'key': 'internship_end_date', 'field': 'internship_end_date', 'translation_key': 'internship_end_date',
         'question_video': 'q23.mp4', 'error_video': 'internship_end_date_error.mp4',
         'question': 'When did your internship <strong>end</strong>, or is it still ongoing?', 'type': 'text',
         'placeholder': 'e.g. August 2025 or Ongoing', 'hint': 'Enter month and year, or Ongoing',
         'condition': {'field': 'internship_done', 'value': 'Yes'},
         'validator': validate_internship_end_date},
    24: {'id': 24, 'key': 'internship_topic', 'field': 'internship_topic', 'translation_key': 'internship_topic',
         'question_video': 'q24.mp4', 'error_video': 'internship_topic_error.mp4',
         'question': 'What was the <strong>topic or domain</strong> of your internship?', 'type': 'text',
         'placeholder': 'e.g. Web Development with Django, Machine Learning', 'hint': 'Briefly describe your internship topic or work',
         'condition': {'field': 'internship_done', 'value': 'Yes'},
         'validator': validate_internship_topic},
}

# Compatibility list for the local demo flow; entries are derived from the
# one permanent lookup above and do not define a second mapping.
QUESTIONS = list(QUESTION_LOOKUP.values())


def build_dmcore_playlist(dmcore_questions):
    """Build the exact DMCore order, skipping IDs absent from the fixed lookup."""
    playlist = []
    if not isinstance(dmcore_questions, list):
        logger.warning('DMCore session questions was not a list; using an empty playlist')
        return playlist
    for item in dmcore_questions:
        question_id = item.get('question_id') if isinstance(item, dict) else item
        if isinstance(question_id, str) and question_id.isdigit():
            question_id = int(question_id)
        if isinstance(question_id, bool) or not isinstance(question_id, int) or question_id not in QUESTION_LOOKUP:
            logger.warning('unknown question_id=%r, skipping', question_id)
            continue
        question = QUESTION_LOOKUP[question_id]
        field_key = item.get('field_key') if isinstance(item, dict) else None
        if field_key and field_key != question['key']:
            logger.warning('DMCore field_key mismatch for question_id=%s; using the fixed local key', question_id)
        playlist.append({'question_id': question_id, 'field_key': question['key']})
    return playlist


def get_dmcore_active_questions(playlist, answers):
    """Apply the fresher skip rule only when question 10 is in this playlist."""
    asked_experience = any(item.get('question_id') == 10 for item in playlist)
    has_exp_ans = answers.get('has_experience') or answers.get(10) or answers.get('10')
    skip_experience_details = asked_experience and has_exp_ans == FRESHER_ANSWER
    asked_internship = any(item.get('question_id') == 21 for item in playlist)
    internship_ans = answers.get('internship_done') or answers.get(21) or answers.get('21')
    skip_internship_details = asked_internship and str(internship_ans).strip().lower() == 'no'
    active = []
    for item in playlist:
        question = QUESTION_LOOKUP[item['question_id']]
        if skip_internship_details and question['id'] in (22, 23, 24):
            continue
        if skip_experience_details and question['id'] in (11, 12, 13):
            continue
        active.append(question)
    return active


def validate_answer(question, value, answers=None):



    validator = question.get('validator')
    optional = question.get('optional', False)
    if is_empty_or_filler(value):
        if optional:
            return ValidationResult(True, value)
        if validator:
            return validator(value, answers=answers)
        return ValidationResult(False, 'This field cannot be empty. Please provide an answer.', reason='empty')
    if validator:
        res = validator(value, answers=answers)
        if isinstance(res, ValidationResult):
            return res
        return ValidationResult(res[0], res[1], reason=getattr(res, 'reason', None) or (None if res[0] else 'invalid'))



    question_id = question['id']






    if question_id == 1:
        parts = value.strip().split()
        if len(parts) < 2:
            return ValidationResult(False, 'Please enter your full name — first and last name.', reason='invalid')
        if any(char.isdigit() for char in value):
            return ValidationResult(False, 'Name should not contain numbers.', reason='invalid')
    elif question_id == 2:
        if not re.match(r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$', value.strip()):
            return ValidationResult(False, 'Please enter a valid email address.', reason='invalid')
    elif question_id in (3, 'phone'):
        digits = re.sub(r'[^\d]', '', value)
        if not digits.isdigit() or len(digits) < 10:
            return ValidationResult(False, 'Please enter a valid phone number with at least 10 digits.', reason='invalid')
    elif question_id == 8:
        year = value.strip()
        if not re.match(r'^\d{4}$', year) or not (1950 <= int(year) <= 2030):
            return ValidationResult(False, 'Please enter a valid 4-digit graduation year.', reason='invalid')
    elif question_id == 14:
        skills = [skill.strip() for skill in value.split(',') if skill.strip()]
        if len(skills) < 2:
            return ValidationResult(False, 'Please enter at least 2 skills, separated by commas.', reason='invalid')
    elif question_id == 17 and value.strip():
        if not (value.startswith('http://') or value.startswith('https://')):
            return ValidationResult(False, 'Please enter a valid URL starting with https://', reason='invalid')
    elif question_id == 18:
        if len(value.strip()) < 20:
            return ValidationResult(False, 'Please write at least 20 characters for your answer.', reason='invalid')
    elif question['type'] == 'options':
        if value not in question.get('options', []):
            return ValidationResult(False, 'Please select one of the provided options.', reason='invalid')
    return ValidationResult(True, value)


def get_active_questions(session_answers):
    """Conditional demo questions, using the same canonical question lookup."""
    active = []
    for question in QUESTIONS:
        condition = question.get('condition')
        if condition and session_answers.get(condition['field'], '') != condition['value']:
            continue
        active.append(question)
    return active
