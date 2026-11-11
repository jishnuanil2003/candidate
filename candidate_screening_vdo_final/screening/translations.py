# Static translations dictionary for TalentBot candidate screening
# Supports: English (en), Malayalam (ml), Hindi (hi), Tamil (ta), Telugu (te)
# Keyed by language code and question id (1-18) with backward-compatible key aliases.

QUESTION_ID_TO_KEY = {
    1: 'full_name',
    2: 'email',
    3: 'phone',
    4: 'role_applied',
    5: 'highest_qualification',
    6: 'field_of_study',
    7: 'college',
    8: 'graduation_year',
    9: 'academic_performance',
    10: 'has_experience',
    11: 'last_company',
    12: 'last_role',
    13: 'experience_duration',
    14: 'skills',
    15: 'notice_period',
    16: 'expected_salary',
    17: 'linkedin',
    18: 'why_good_fit',
    19: 'lead_source',
    20: 'location',
    21: 'internship_done',
    22: 'internship_start_date',
    23: 'internship_end_date',
    24: 'internship_topic',
}

KEY_TO_QUESTION_ID = {v: k for k, v in QUESTION_ID_TO_KEY.items()}
# Also alias legacy internal field keys
KEY_TO_QUESTION_ID.update({
    'applied_role': 4,
    'qualification': 5,
    'institution': 7,
    'cgpa': 9,
    'company': 11,
    'previous_role': 12,
    'work_duration': 13,
    'cover_note': 18,
})

# Canonical English error fallback text and scripts for questions 19-24 by field_key and reason.
# Note: internship_end_date.invalid uses start-date style placeholder wording as requested.
ADDENDUM_ERROR_TEXTS = {
    'lead_source': {
        'invalid': "Sorry, I couldn't catch that. Was it a friend, social media, your college, or a job portal?",
        'empty': "I don't have that on record yet. How did you first hear about us?",
    },
    'location': {
        'invalid': "I couldn't recognise that place. Could you tell me the name of your city or town again?",
        'empty': "I still need your current location. Which city or town do you live in?",
    },
    'internship_done': {
        'invalid': "Just to confirm, have you done an internship? A simple yes or no is fine.",
        'empty': "I haven't noted this yet. Have you completed any internship so far?",
    },
    'internship_start_date': {
        'invalid': "That date doesn't look right. Could you tell me the month and year your internship started, like June 2025?",
        'empty': "When did your internship begin? The month and year is enough.",
    },
    'internship_end_date': {
        'before_start': "That end date seems to come before the start date. Could you check and tell me again? If it's still going on, just say so.",
        'empty': "I'm missing the end date. When did your internship finish, or is it still ongoing?",
        'invalid': "I couldn't catch the date. Could you tell me the month and year your internship ended, like June 2025, or say it's still going on?",
    },
    'internship_topic': {
        'invalid': "I didn't quite get that. Could you describe in a few words what your internship was about?",
        'empty': "What was your internship about? Tell me the topic or the kind of work you did.",
    },
}


def get_error_text(field_key, reason, lang='en'):
    """
    Lookup order for error on-screen text / TTS:
    1. Translated text in chosen language (if present and non-empty)
    2. Canonical English text
    """
    if lang and lang != 'en':
        lang_data = TRANSLATIONS.get(lang, {})
        lang_addendum = lang_data.get('addendum_errors', {}).get(field_key, {})
        if reason in lang_addendum and lang_addendum[reason].strip():
            return lang_addendum[reason].strip()
    if field_key in ADDENDUM_ERROR_TEXTS and reason in ADDENDUM_ERROR_TEXTS[field_key]:
        return ADDENDUM_ERROR_TEXTS[field_key][reason]
    return None

TRANSLATIONS = {
    "en": {
        "ui": {
            "begin_interview": "Begin Interview",
            "select_language": "Choose Language",
            "sarah_speaking": "Sarah is speaking...",
            "waiting_response": "Waiting for your response...",
            "listening": "Listening...",
            "validation_error": "Validation Error",
            "repeat_question": "Repeat question",
            "type_message": "Type a message...",
            "interview_complete": "Interview Complete!",
            "thank_you": "Thank you for completing your screening interview. Our team will review your responses and be in touch soon. Have a great day!",
            "return_home": "Return to Home",
            "current_question": "Current Question",
            "question_of": "Question {num} of {total}",
            "progress": "Interview Progress",
            "tips_title": "💡 Tips",
            "tips": [
                "Take your time and think before answering.",
                "You can repeat the question if needed.",
                "Your responses help us understand you better."
            ],
            "guide_text": "I'm here to guide you through the interview. Just type your answer or speak when ready.",
            "change_language": "Change Language"
        },
        "errors": {
            "error_cover.mp4": "Could you please add a little more detail to your answer?",
            "error_empty.mp4": "It seems no answer was provided. Please provide your answer.",
            "error_name.mp4": "Please enter your full name — first and last name.",
            "error_phone.mp4": "Please enter a valid phone number with at least 10 digits.",
            "error_skills.mp4": "Please enter at least 2 skills, separated by commas.",
            "error_year.mp4": "Please enter a valid 4-digit graduation year.",
            "error_email.mp4": "Please enter a valid email address.",
            "english_only": "Please enter your response in English only.",
            "q_complete.mp4": "Thank you for completing your screening interview. Our team will review your responses and be in touch soon. Have a great day!"
        },
        "questions": {
            1: {
                "question": "Hello, I'm Talentbot. Welcome to your screening interview. I'll guide you through a few quick questions. Just respond at your own pace. Let's begin. What is your <strong>full name</strong>?",
                "placeholder": "e.g. Priya Sharma",
                "hint": "Enter your first and last name"
            },
            2: {
                "question": "Nice to meet you. Could you please share your <strong>email address</strong>? We'll use it to send you updates about your application.",
                "placeholder": "e.g. priya@example.com",
                "hint": "Enter a valid email address"
            },
            3: {
                "question": "Thank you. What is your <strong>phone number</strong>? Please include your country code if outside India.",
                "placeholder": "e.g. +91 9876543210",
                "hint": "Minimum 10 digits"
            },
            4: {
                "question": "Which <strong>role</strong> are you applying for?",
                "options": [
                    "Software Engineer",
                    "Data Analyst",
                    "UI/UX Designer",
                    "Product Manager",
                    "DevOps Engineer",
                    "QA Engineer"
                ],
                "options_translated": [
                    "Software Engineer",
                    "Data Analyst",
                    "UI/UX Designer",
                    "Product Manager",
                    "DevOps Engineer",
                    "QA Engineer"
                ],
                "other_label": "Other (type your role)",
                "placeholder": "Type your role",
                "hint": "Select a role or type another"
            },
            5: {
                "question": "What is your <strong>highest educational qualification</strong>?",
                "options": [
                    "Bachelor's Degree",
                    "Master's Degree",
                    "PhD",
                    "Diploma",
                    "12th / Higher Secondary",
                    "Other"
                ],
                "options_translated": [
                    "Bachelor's Degree",
                    "Master's Degree",
                    "PhD",
                    "Diploma",
                    "12th / Higher Secondary",
                    "Other"
                ],
                "hint": "Select your highest level of education"
            },
            6: {
                "question": "What was your <strong>field of study or specialization</strong>?",
                "placeholder": "e.g. Computer Science, Electronics, MBA",
                "hint": "Your major or specialisation"
            },
            7: {
                "question": "Which <strong>college or university</strong> did you attend?",
                "placeholder": "Enter the full name of your college or university",
                "hint": "College or university name"
            },
            8: {
                "question": "Which <strong>year did you graduate</strong> or expect to graduate?",
                "placeholder": "e.g. 2023",
                "hint": "Enter a valid 4-digit year"
            },
            9: {
                "question": "What was your <strong>overall academic performance</strong>? You can mention your CGPA or percentage.",
                "placeholder": "e.g. 8.5 CGPA or 85%",
                "hint": "Enter your academic score"
            },
            10: {
                "question": "Do you have any <strong>prior work experience</strong>?",
                "options": [
                    "Yes, I have experience",
                    "No, I am a fresher"
                ],
                "options_translated": [
                    "Yes, I have experience",
                    "No, I am a fresher"
                ],
                "hint": "This helps us personalise the interview"
            },
            11: {
                "question": "Which <strong>company</strong> did you most recently work at?",
                "placeholder": "e.g. Infosys, TCS, Wipro",
                "hint": "Company name"
            },
            12: {
                "question": "What was your <strong>role or job title</strong> there?",
                "placeholder": "e.g. Junior Developer, Business Analyst",
                "hint": "Job title"
            },
            13: {
                "question": "How long did you work there? Please select your <strong>total experience</strong>.",
                "options": [
                    "Less than 1 year",
                    "1-2 years",
                    "2-4 years",
                    "4-6 years",
                    "6+ years"
                ],
                "options_translated": [
                    "Less than 1 year",
                    "1-2 years",
                    "2-4 years",
                    "4-6 years",
                    "6+ years"
                ],
                "hint": "Select your total experience"
            },
            14: {
                "question": "Could you list your <strong>top technical skills</strong>? Separate them with commas.",
                "placeholder": "e.g. Python, Django, React, SQL",
                "hint": "Enter at least 2 skills"
            },
            15: {
                "question": "What is your <strong>notice period</strong> or how soon can you start?",
                "options": [
                    "Immediate joiner",
                    "2 weeks",
                    "1 month",
                    "2 months",
                    "3+ months"
                ],
                "options_translated": [
                    "Immediate joiner",
                    "2 weeks",
                    "1 month",
                    "2 months",
                    "3+ months"
                ],
                "hint": "How soon can you join if selected?"
            },
            16: {
                "question": "What is your <strong>expected annual salary range</strong>?",
                "options": [
                    "3-5 LPA",
                    "5-8 LPA",
                    "8-12 LPA",
                    "12-20 LPA",
                    "20+ LPA"
                ],
                "options_translated": [
                    "3-5 LPA",
                    "5-8 LPA",
                    "8-12 LPA",
                    "12-20 LPA",
                    "20+ LPA"
                ],
                "hint": "Select your expected salary range"
            },
            17: {
                "question": "If you have a <strong>LinkedIn profile</strong>, please share the link. You can skip this if you prefer.",
                "placeholder": "https://linkedin.com/in/yourname",
                "hint": "Optional — press Submit to skip"
            },
            18: {
                "question": "Could you briefly tell me why you are a <strong>good fit for this role</strong>? A couple of sentences will be perfect.",
                "placeholder": "Tell us what makes you a great candidate for this role...",
                "hint": "Minimum 20 characters"
            },
            19: {
                "question": "How did you hear about this opportunity?",
                "placeholder": "e.g. Friend, Social Media, Campus",
                "hint": "Tell us how you found this opening"
            },
            20: {
                "question": "Which <strong>city or town</strong> are you currently located in?",
                "placeholder": "e.g. Bengaluru, Mumbai, Kochi",
                "hint": "Enter your current city or town"
            },
            21: {
                "question": "Have you completed any <strong>internships</strong>?",
                "options": ["Yes", "No"],
                "hint": "Select Yes or No"
            },
            22: {
                "question": "When did your internship <strong>start</strong>? Please provide the month and year.",
                "placeholder": "e.g. June 2025",
                "hint": "Enter month and year"
            },
            23: {
                "question": "When did your internship <strong>end</strong>, or is it still ongoing?",
                "placeholder": "e.g. August 2025 or Ongoing",
                "hint": "Enter month and year, or Ongoing"
            },
            24: {
                "question": "What was the <strong>topic or domain</strong> of your internship?",
                "placeholder": "e.g. Web Development with Django, Machine Learning",
                "hint": "Briefly describe your internship topic or work"
            }
        }
    },
    "ml": {
        "ui": {
            "begin_interview": "അഭിമുഖം ആരംഭിക്കുക",
            "select_language": "ഭാഷ തിരഞ്ഞെടുക്കുക",
            "sarah_speaking": "സാറ സംസാരിക്കുന്നു...",
            "waiting_response": "നിങ്ങളുടെ മറുപടിക്കായി കാത്തിരിക്കുന്നു...",
            "listening": "ശ്രദ്ധിക്കുന്നു...",
            "validation_error": "തെറ്റായ വിവരങ്ങൾ",
            "repeat_question": "ചോദ്യം വീണ്ടും കേൾക്കുക",
            "type_message": "സന്ദേശം ടൈപ്പ് ചെയ്യുക...",
            "interview_complete": "അഭിമുഖം പൂർത്തിയായി!",
            "thank_you": "Screening പൂർത്തിയാക്കിയതിന് നന്ദി. ഞങ്ങളുടെ Team നിങ്ങളുടെ Responses പരിശോധിച്ച് ഉടൻ നിങ്ങളെ ബന്ധപ്പെടും. നല്ലൊരു ദിവസം ആശംസിക്കുന്നു.",
            "return_home": "ഹോമിലേക്ക് മടങ്ങുക",
            "current_question": "നിലവിലെ ചോദ്യം",
            "question_of": "ചോദ്യം {num} / {total}",
            "progress": "അഭിമുഖ പുരോഗതി",
            "tips_title": "💡 നുറുങ്ങുകൾ",
            "tips": [
                "മറുപടി നൽകുന്നതിന് മുൻപ് ചിന്തിക്കാൻ ആവശ്യത്തിന് സമയമെടുക്കുക.",
                "ആവശ്യമെങ്കിൽ നിങ്ങൾക്ക് ചോദ്യം വീണ്ടും കേൾക്കാം.",
                "നിങ്ങളുടെ മറുപടികൾ നിങ്ങളെ നന്നായി മനസ്സിലാക്കാൻ സഹായിക്കുന്നു."
            ],
            "guide_text": "അഭിമുഖത്തിലൂടെ നിങ്ങളെ നയിക്കാൻ ഞാൻ ഇവിടെയുണ്ട്. തയ്യാറാകുമ്പോൾ മറുപടി ടൈപ്പ് ചെയ്യുക അല്ലെങ്കിൽ പറയുക.",
            "change_language": "ഭാഷ മാറ്റുക"
        },
        "errors": {
            "error_cover.mp4": "ദയവായി നിങ്ങളുടെ ഉത്തരത്തിൽ കുറച്ചുകൂടി വിശദാംശങ്ങൾ ചേർക്കാമോ?",
            "error_empty.mp4": "മറുപടി ലഭിച്ചില്ലെന്ന് തോന്നുന്നു. ദയവായി നിങ്ങളുടെ ഉത്തരം നൽകുക.",
            "error_name.mp4": "ഹും, ഇത് പൂർണ്ണമായ പേര് പോലെ തോന്നുന്നില്ല. ദയവായി നിങ്ങളുടെ ആദ്യ പേരും അവസാന പേരും നൽകുക.",
            "error_phone.mp4": "ഇത് സാധുവായ ഫോൺ നമ്പർ ആയി തോന്നുന്നില്ല. ദയവായി പരിശോധിച്ച് വീണ്ടും നൽകുക.",
            "error_skills.mp4": "ദയവായി കുറഞ്ഞത് രണ്ട് നൈപുണ്യങ്ങൾ എങ്കിലും നൽകുക.",
            "error_year.mp4": "ഇത് സാധുവായ വർഷമായി തോന്നുന്നില്ല. ദയവായി നാല് അക്കങ്ങളുള്ള വർഷം നൽകുക.",
            "error_email.mp4": "ഹും, ഇത് സാധുവായ ഇമെയിൽ വിലാസം ആയി തോന്നുന്നില്ല. ദയവായി വീണ്ടും നൽകുക.",
            "english_only": "ദയവായി നിങ്ങളുടെ മറുപടി ഇംഗ്ലീഷിൽ മാത്രം നൽകുക.",
            "q_complete.mp4": "അഭിമുഖം പൂർത്തിയാക്കിയതിന് നന്ദി. ഞങ്ങളുടെ സംഘം നിങ്ങളുടെ മറുപടികൾ പരിശോധിച്ച് ഉടൻ നിങ്ങളെ ബന്ധപ്പെടും. നല്ലൊരു ദിവസം ആശംസിക്കുന്നു."
        },
        "questions": {
            1: {
                "question": "ഹലോ, ഞാൻ Talentbot ആണ്. നിങ്ങളുടെ Screening Interview-ലേക്ക് സ്വാഗതം. ആദ്യം, നിങ്ങളുടെ <strong>Full Name</strong> എന്താണ്?",
                "placeholder": "ഉദാ. പ്രിയ ശർമ്മ",
                "hint": "നിങ്ങളുടെ ആദ്യ പേരും അവസാന പേരും നൽകുക"
            },
            2: {
                "question": "നിങ്ങളെ കണ്ടതിൽ സന്തോഷം. നിങ്ങളുടെ <strong>Email Address</strong> പങ്കുവെക്കാമോ? നിങ്ങളുടെ Application സംബന്ധിച്ച വിവരങ്ങൾ അയയ്ക്കാൻ അത് ഉപയോഗിക്കും.",
                "placeholder": "ഉദാ. priya@example.com",
                "hint": "സാധുവായ ഒരു ഇമെയിൽ വിലാസം നൽകുക"
            },
            3: {
                "question": "നന്ദി. നിങ്ങളുടെ <strong>Phone Number</strong> എന്താണ്? ഇന്ത്യയ്ക്ക് പുറത്താണെങ്കിൽ Country Code ഉൾപ്പെടുത്തുക.",
                "placeholder": "ഉദാ. +91 9876543210",
                "hint": "കുറഞ്ഞത് 10 അക്കങ്ങൾ"
            },
            4: {
                "question": "വളരെ നന്ന്. നിങ്ങൾ ഏത് <strong>Role</strong>-നാണ് Apply ചെയ്യുന്നത്?",
                "options": [
                    "Software Engineer",
                    "Data Analyst",
                    "UI/UX Designer",
                    "Product Manager",
                    "DevOps Engineer",
                    "QA Engineer"
                ],
                "options_translated": [
                    "സോഫ്റ്റ്‌വെയർ എഞ്ചിനീയർ",
                    "ഡാറ്റ അനലിസ്റ്റ്",
                    "യുഐ/യുഎക്സ് ഡിസൈനർ",
                    "പ്രൊഡക്ട് മാനേജർ",
                    "ഡെവോപ്സ് എഞ്ചിനീയർ",
                    "ക്യുഎ എഞ്ചിനീയർ"
                ],
                "other_label": "മറ്റുള്ളവ (നിങ്ങളുടെ തസ്തിക ടൈപ്പ് ചെയ്യുക)",
                "placeholder": "ഉദാ. ബാക്കെൻഡ് ഡെവലപ്പർ, എംഎൽ എഞ്ചിനീയർ...",
                "hint": "ഒരു തസ്തിക തിരഞ്ഞെടുക്കുക അല്ലെങ്കിൽ താഴെ പുതിയത് ടൈപ്പ് ചെയ്യുക"
            },
            5: {
                "question": "ഇനി നിങ്ങളുടെ വിദ്യാഭ്യാസത്തെക്കുറിച്ച് സംസാരിക്കാം. നിങ്ങളുടെ ഏറ്റവും ഉയർന്ന <strong>Educational Qualification</strong> എന്താണ്?",
                "options": [
                    "Bachelor's Degree",
                    "Master's Degree",
                    "PhD",
                    "Diploma",
                    "12th / Higher Secondary",
                    "Other"
                ],
                "options_translated": [
                    "ബാച്ചിലേഴ്സ് ബിരുദം",
                    "മാസ്റ്റേഴ്സ് ബിരുദം",
                    "പിഎച്ച്ഡി",
                    "ഡിപ്ലോമ",
                    "പന്ത്രണ്ടാം ക്ലാസ് / ഹയർ സെക്കൻഡറി",
                    "മറ്റുള്ളവ"
                ],
                "hint": "നിങ്ങളുടെ ഏറ്റവും ഉയർന്ന വിദ്യാഭ്യാസ നില തിരഞ്ഞെടുക്കുക"
            },
            6: {
                "question": "ശരി. നിങ്ങളുടെ <strong>Field of Study അല്ലെങ്കിൽ Specialization</strong> എന്തായിരുന്നു?",
                "placeholder": "ഉദാ. കമ്പ്യൂട്ടർ സയൻസ്, ഇലക്ട്രോണിക്സ്, എംബിഎ",
                "hint": "നിങ്ങളുടെ പ്രധാന പഠന വിഷയം"
            },
            7: {
                "question": "നിങ്ങൾ ഏത് <strong>College അല്ലെങ്കിൽ University</strong>-യിലാണ് പഠിച്ചത്?",
                "placeholder": "ഉദാ. ഐഐടി ബോംബെ, കേരള യൂണിവേഴ്സിറ്റി",
                "hint": "നിങ്ങളുടെ കോളേജ് അല്ലെങ്കിൽ യൂണിവേഴ്സിറ്റിയുടെ പൂർണ്ണമായ പേര് നൽകുക"
            },
            8: {
                "question": "നിങ്ങൾ <strong>Graduate</strong> ചെയ്തതോ അല്ലെങ്കിൽ ചെയ്യാൻ പോകുന്നതോ ഏത് വർഷത്തിലാണ്?",
                "placeholder": "ഉദാ. 2023",
                "hint": "സാധുവായ 4 അക്ക വർഷം നൽകുക"
            },
            9: {
                "question": "നിങ്ങളുടെ ആകെ Academic Performance എങ്ങനെയായിരുന്നു? നിങ്ങളുടെ <strong>CGPA അല്ലെങ്കിൽ Percentage</strong> പങ്കുവെക്കാമോ?",
                "placeholder": "ഉദാ. 8.5 CGPA അല്ലെങ്കിൽ 85%",
                "hint": "നിങ്ങളുടെ അക്കാദമിക് സ്കോർ നൽകുക"
            },
            10: {
                "question": "ഇനി നിങ്ങളുടെ Background-നെക്കുറിച്ച് അറിയാം. നിങ്ങൾക്ക് മുൻ <strong>Work Experience</strong> ഉണ്ടോ?",
                "options": [
                    "Yes, I have experience",
                    "No, I am a fresher"
                ],
                "options_translated": [
                    "അതെ, എനിക്ക് പരിചയമുണ്ട്",
                    "ഇല്ല, ഞാൻ ഒരു തുടക്കക്കാരനാണ്"
                ],
                "hint": "അഭിമുഖം വ്യക്തിഗതമാക്കാൻ ഇത് ഞങ്ങളെ സഹായിക്കുന്നു"
            },
            11: {
                "question": "ഉണ്ടെങ്കിൽ, നിങ്ങൾ ഏറ്റവും ഒടുവിൽ ജോലി ചെയ്ത <strong>Company</strong> ഏതാണ്?",
                "placeholder": "ഉദാ. ഇൻഫോസിസ്, ടിസിഎസ്, വിപ്രോ",
                "hint": "കമ്പനിയുടെ പൂർണ്ണമായ പേര് നൽകുക"
            },
            12: {
                "question": "അവിടെ നിങ്ങളുടെ <strong>Job Title അല്ലെങ്കിൽ Role</strong> എന്തായിരുന്നു?",
                "placeholder": "ഉദാ. ജൂനിയർ ഡെവലപ്പർ, ബിസിനസ് അനലിസ്റ്റ്",
                "hint": "നിങ്ങളുടെ കൃത്യമായ തൊഴിൽ പദവി"
            },
            13: {
                "question": "അവിടെ നിങ്ങൾ എത്ര കാലം ജോലി ചെയ്തു? നിങ്ങളുടെ ആകെ <strong>Work Experience</strong> തിരഞ്ഞെടുക്കുക.",
                "options": [
                    "Less than 1 year",
                    "1-2 years",
                    "2-4 years",
                    "4-6 years",
                    "6+ years"
                ],
                "options_translated": [
                    "1 വർഷത്തിൽ താഴെ",
                    "1-2 വർഷം",
                    "2-4 വർഷം",
                    "4-6 വർഷം",
                    "6+ വർഷം"
                ],
                "hint": "നിങ്ങളുടെ ഏകദേശ ആകെ പരിചയം തിരഞ്ഞെടുക്കുക"
            },
            14: {
                "question": "നിങ്ങളുടെ പ്രധാന <strong>Technical Skills</strong> എന്തൊക്കെയാണ്? Comma ഉപയോഗിച്ച് വേർതിരിച്ച് നൽകാം.",
                "placeholder": "ഉദാ. പൈത്തൺ, ജാങ്കോ, റിയാക്ട്, എസ്ക്യുഎൽ",
                "hint": "കുറഞ്ഞത് 2 കഴിവുകൾ നൽകുക"
            },
            15: {
                "question": "നന്ദി. നിങ്ങളുടെ <strong>Notice Period</strong> എത്രയാണ്, അല്ലെങ്കിൽ എത്ര വേഗം Join ചെയ്യാൻ കഴിയും?",
                "options": [
                    "Immediate joiner",
                    "2 weeks",
                    "1 month",
                    "2 months",
                    "3+ months"
                ],
                "options_translated": [
                    "ഉടൻ തന്നെ ചേരാം",
                    "2 ആഴ്ച",
                    "1 മാസം",
                    "2 മാസം",
                    "3+ മാസം"
                ],
                "hint": "തിരഞ്ഞെടുക്കപ്പെട്ടാൽ നിങ്ങൾക്ക് എത്രയും വേഗം ചേരാനാകും?"
            },
            16: {
                "question": "ശരി. നിങ്ങൾ പ്രതീക്ഷിക്കുന്ന വാർഷിക <strong>Salary Range</strong> എന്താണ്?",
                "options": [
                    "3-5 LPA",
                    "5-8 LPA",
                    "8-12 LPA",
                    "12-20 LPA",
                    "20+ LPA"
                ],
                "options_translated": [
                    "₹3-5 ലക്ഷം",
                    "₹5-8 ലക്ഷം",
                    "₹8-12 ലക്ഷം",
                    "₹12-20 ലക്ഷം",
                    "₹20+ ലക്ഷം"
                ],
                "hint": "നിങ്ങൾ പ്രതീക്ഷിക്കുന്ന ശമ്പള പരിധി തിരഞ്ഞെടുക്കുക"
            },
            17: {
                "question": "നിങ്ങൾക്ക് <strong>LinkedIn Profile</strong> ഉണ്ടെങ്കിൽ അതിന്റെ Link പങ്കുവെക്കാമോ? താൽപ്പര്യമില്ലെങ്കിൽ Skip ചെയ്യാം.",
                "placeholder": "https://linkedin.com/in/yourname",
                "hint": "ഓപ്ഷണൽ — ഒഴിവാക്കാൻ സബ്മിറ്റ് അമർത്തുക"
            },
            18: {
                "question": "നാം ഏകദേശം പൂർത്തിയാക്കി. ഈ <strong>Role-ന് നിങ്ങൾ അനുയോജ്യനാണെന്ന്</strong> ചുരുക്കത്തിൽ പറയാമോ? രണ്ടോ മൂന്നോ വാക്യങ്ങൾ മതി.",
                "placeholder": "നിങ്ങളെ എന്തുകൊണ്ടാണ് ഈ റോളിന് അനുയോജ്യനാക്കുന്നത് എന്ന് പറയുക...",
                "hint": "കുറഞ്ഞത് 20 അക്ഷരങ്ങൾ"
            }
        }
    },
    "hi": {
        "ui": {
            "begin_interview": "साक्षात्कार शुरू करें",
            "select_language": "भाषा चुनें",
            "sarah_speaking": "सारा बोल रही हैं...",
            "waiting_response": "आपकी प्रतिक्रिया की प्रतीक्षा है...",
            "listening": "सुन रही हूँ...",
            "validation_error": "सत्यापन त्रुटि",
            "repeat_question": "प्रश्न दोहराएं",
            "type_message": "संदेश टाइप करें...",
            "interview_complete": "साक्षात्कार पूर्ण!",
            "thank_you": "Screening पूरा करने के लिए धन्यवाद। हमारी Team आपके Responses की समीक्षा करेगी और जल्द ही आपसे संपर्क करेगी। आपका दिन शुभ हो।",
            "return_home": "होम पर वापस जाएं",
            "current_question": "वर्तमान प्रश्न",
            "question_of": "प्रश्न {num} / {total}",
            "progress": "साक्षात्कार प्रगति",
            "tips_title": "💡 सुझाव",
            "tips": [
                "उत्तर देने से पहले सोचने के लिए अपना समय लें।",
                "यदि आवश्यक हो तो आप प्रश्न दोहरा सकते हैं।",
                "आपकी प्रतिक्रियाएं हमें आपको बेहतर समझने में मदद करती हैं।"
            ],
            "guide_text": "मैं यहाँ साक्षात्कार में आपका मार्गदर्शन करने के लिए हूँ। तैयार होने पर टाइप करें या बोलें।",
            "change_language": "भाषा बदलें"
        },
        "errors": {
            "error_cover.mp4": "कृपया अपने उत्तर में थोड़ी और जानकारी जोड़ें।",
            "error_empty.mp4": "ऐसा लगता है कि उत्तर नहीं मिला। कृपया अपना उत्तर दें।",
            "error_name.mp4": "ह्म, यह पूरा नाम नहीं लगता। कृपया अपना पहला नाम और अंतिम नाम दर्ज करें।",
            "error_phone.mp4": "यह वैध फ़ोन नंबर नहीं लगता। कृपया जांचकर फिर से दर्ज करें।",
            "error_skills.mp4": "कृपया कम से कम दो कौशल दर्ज करें।",
            "error_year.mp4": "यह वैध वर्ष नहीं लगता। कृपया चार अंकों वाला वर्ष दर्ज करें।",
            "error_email.mp4": "ह्म, यह वैध ईमेल पता नहीं लगता। कृपया इसे फिर से दर्ज करें।",
            "english_only": "कृपया अपनी प्रतिक्रिया केवल अंग्रेजी में दर्ज करें।",
            "q_complete.mp4": "साक्षात्कार पूरा करने के लिए धन्यवाद। हमारी टीम आपके उत्तरों की समीक्षा करेगी और जल्द ही आपसे संपर्क करेगी। आपका दिन शुभ हो।"
        },
        "questions": {
            1: {
                "question": "नमस्ते, मैं Talentbot हूँ। आपके Screening Interview में आपका स्वागत है। आपका <strong>Full Name</strong> क्या है?",
                "placeholder": "जैसे. प्रिया शर्मा",
                "hint": "अपना पहला और अंतिम नाम दर्ज करें"
            },
            2: {
                "question": "आपसे मिलकर अच्छा लगा। क्या आप अपना <strong>Email Address</strong> साझा कर सकते हैं? हम इसका उपयोग आपके आवेदन पर अपडेट भेजने के लिए करेंगे।",
                "placeholder": "जैसे. priya@example.com",
                "hint": "एक वैध ईमेल पता दर्ज करें"
            },
            3: {
                "question": "धन्यवाद। आपका <strong>Phone Number</strong> क्या है? यदि आप भारत से बाहर हैं तो कृपया अपना Country Code शामिल करें।",
                "placeholder": "जैसे. +91 9876543210",
                "hint": "न्यूनतम 10 अंक"
            },
            4: {
                "question": "बहुत बढ़िया। आप किस <strong>Role</strong> के लिए आवेदन कर रहे हैं?",
                "options": [
                    "Software Engineer",
                    "Data Analyst",
                    "UI/UX Designer",
                    "Product Manager",
                    "DevOps Engineer",
                    "QA Engineer"
                ],
                "options_translated": [
                    "सॉफ्टवेयर इंजीनियर",
                    "डेटा विश्लेषक",
                    "यूआई/यूएक्स डिजाइनर",
                    "उत्पाद प्रबंधक",
                    "डेवऑप्स इंजीनियर",
                    "क्यूए इंजीनियर"
                ],
                "other_label": "अन्य (अपनी भूमिका टाइप करें)",
                "placeholder": "जैसे. बैकएंड डेवलपर, एमएल इंजीनियर...",
                "hint": "एक भूमिका चुनें या नीचे अपना पद टाइप करें"
            },
            5: {
                "question": "आइए आपकी शिक्षा के बारे में बात करते हैं। आपकी उच्चतम <strong>Educational Qualification</strong> क्या है?",
                "options": [
                    "Bachelor's Degree",
                    "Master's Degree",
                    "PhD",
                    "Diploma",
                    "12th / Higher Secondary",
                    "Other"
                ],
                "options_translated": [
                    "स्नातक डिग्री (Bachelor's)",
                    "स्नातकोत्तर डिग्री (Master's)",
                    "पीएचडी",
                    "डिप्लोमा",
                    "12वीं / उच्चतर माध्यमिक",
                    "अन्य"
                ],
                "hint": "अपनी उच्चतम शिक्षा स्तर चुनें"
            },
            6: {
                "question": "आपका <strong>Field of Study या Specialization</strong> क्या था?",
                "placeholder": "जैसे. कंप्यूटर साइंस, इलेक्ट्रॉनिक्स, एमबीए",
                "hint": "आपका मुख्य विषय या विशेषज्ञता"
            },
            7: {
                "question": "आपने किस <strong>College या University</strong> से पढ़ाई की?",
                "placeholder": "जैसे. आईआईटी बॉम्बे, दिल्ली विश्वविद्यालय",
                "hint": "अपने कॉलेज या विश्वविद्यालय का पूरा नाम दर्ज करें"
            },
            8: {
                "question": "आपने किस वर्ष <strong>Graduation</strong> पूरा किया या करने वाले हैं?",
                "placeholder": "जैसे. 2023",
                "hint": "वैध 4-अंकीय वर्ष दर्ज करें"
            },
            9: {
                "question": "आपका समग्र अकादमिक प्रदर्शन कैसा था? क्या आप अपना <strong>CGPA या Percentage</strong> साझा कर सकते हैं?",
                "placeholder": "जैसे. 8.5 CGPA या 85%",
                "hint": "अपना शैक्षणिक स्कोर दर्ज करें"
            },
            10: {
                "question": "आइए अब आपके अनुभव के बारे में जानते हैं। क्या आपके पास कोई पूर्व <strong>Work Experience</strong> है?",
                "options": [
                    "Yes, I have experience",
                    "No, I am a fresher"
                ],
                "options_translated": [
                    "हाँ, मेरे पास अनुभव है",
                    "नहीं, मैं एक फ्रेशर हूँ"
                ],
                "hint": "यह हमें साक्षात्कार को बेहतर बनाने में मदद करता है"
            },
            11: {
                "question": "यदि हाँ, तो आपने हाल ही में किस <strong>Company</strong> में काम किया?",
                "placeholder": "जैसे. इन्फोसिस, टीसीएस, विप्रो",
                "hint": "कंपनी का पूरा नाम दर्ज करें"
            },
            12: {
                "question": "वहाँ आपका <strong>Role या Job Title</strong> क्या था?",
                "placeholder": "जैसे. जूनियर डेवलपर, बिजनेस एनालिस्ट",
                "hint": "आपका सटीक पद"
            },
            13: {
                "question": "आपने वहाँ कितने समय तक काम किया? अपना कुल <strong>Work Experience</strong> चुनें।",
                "options": [
                    "Less than 1 year",
                    "1-2 years",
                    "2-4 years",
                    "4-6 years",
                    "6+ years"
                ],
                "options_translated": [
                    "1 वर्ष से कम",
                    "1-2 वर्ष",
                    "2-4 वर्ष",
                    "4-6 वर्ष",
                    "6+ वर्ष"
                ],
                "hint": "अपना कुल अनुमानित अनुभव चुनें"
            },
            14: {
                "question": "क्या आप अपने शीर्ष <strong>Technical Skills</strong> बता सकते हैं? उन्हें कॉमा लगाकर अलग करें।",
                "placeholder": "जैसे. पायथन, जैंगो, रिएक्ट, एसक्यूएल",
                "hint": "कम से कम 2 कौशल दर्ज करें"
            },
            15: {
                "question": "धन्यवाद। आपका <strong>Notice Period</strong> क्या है या आप कितनी जल्दी Join कर सकते हैं?",
                "options": [
                    "Immediate joiner",
                    "2 weeks",
                    "1 month",
                    "2 months",
                    "3+ months"
                ],
                "options_translated": [
                    "तुरंत शामिल हो सकते हैं",
                    "2 सप्ताह",
                    "1 महीना",
                    "2 महीने",
                    "3+ महीने"
                ],
                "hint": "यदि चुने जाते हैं तो आप कितनी जल्दी जुड़ सकते हैं?"
            },
            16: {
                "question": "आपकी अपेक्षित वार्षिक <strong>Salary Range</strong> क्या है?",
                "options": [
                    "3-5 LPA",
                    "5-8 LPA",
                    "8-12 LPA",
                    "12-20 LPA",
                    "20+ LPA"
                ],
                "options_translated": [
                    "₹3-5 लाख प्रति वर्ष",
                    "₹5-8 लाख प्रति वर्ष",
                    "₹8-12 लाख प्रति वर्ष",
                    "₹12-20 लाख प्रति वर्ष",
                    "₹20+ लाख प्रति वर्ष"
                ],
                "hint": "अपनी अपेक्षित वेतन सीमा चुनें"
            },
            17: {
                "question": "यदि आपके पास <strong>LinkedIn Profile</strong> है, तो उसका Link साझा करें। आप चाहें तो इसे छोड़ सकते हैं।",
                "placeholder": "https://linkedin.com/in/yourname",
                "hint": "वैकल्पिक — छोड़ने के लिए सबमिट दबाएं"
            },
            18: {
                "question": "हम लगभग समाप्त कर चुके हैं। कृपया संक्षेप में बताइए कि आप इस <strong>Role के लिए उपयुक्त</strong> क्यों हैं। दो या तीन वाक्य पर्याप्त होंगे।",
                "placeholder": "हमें बताएं कि आपको इस भूमिका के लिए क्या उपयुक्त बनाता है...",
                "hint": "कम से कम 20 वर्ण"
            }
        }
    },
    "ta": {
        "ui": {
            "begin_interview": "நேர்காணலைத் தொடங்குங்கள்",
            "select_language": "மொழியைத் தேர்ந்தெடுக்கவும்",
            "sarah_speaking": "சாரா பேசுகிறார்...",
            "waiting_response": "உங்கள் பதிலுக்காகக் காத்திருக்கிறது...",
            "listening": "கேட்கிறது...",
            "validation_error": "சரிபார்ப்புப் பிழை",
            "repeat_question": "கேள்வியை மீண்டும் கேட்க",
            "type_message": "பதில் தட்டச்சு செய்க...",
            "interview_complete": "நேர்காணல் நிறைவுற்றது!",
            "thank_you": "நேர்காணலை முடித்ததற்கு நன்றி. எங்கள் குழு உங்கள் பதில்களை ஆய்வு செய்து விரைவில் தொடர்பு கொள்ளும். இனிய நாளாக அமையட்டும்.",
            "return_home": "முகப்பு பக்கத்திற்குச் செல்க",
            "current_question": "தற்போதைய கேள்வி",
            "question_of": "கேள்வி {num} / {total}",
            "progress": "நேர்காணல் முன்னேற்றம்",
            "tips_title": "💡 குறிப்புகள்",
            "tips": [
                "பதிலளிப்பதற்கு முன் யோசித்து பதிலளிக்க போதுமான நேரம் எடுத்துக் கொள்ளுங்கள்.",
                "தேவைப்பட்டால் கேள்வியை மீண்டும் கேட்கலாம்.",
                "உங்கள் பதில்கள் உங்களை நன்கு புரிந்துகொள்ள உதவுகின்றன."
            ],
            "guide_text": "நேர்காணலில் உங்களை வழிநடத்த நான் இங்கு இருக்கிறேன். தயாராக இருக்கும்போது தட்டச்சு செய்யவும் அல்லது பேசவும்.",
            "change_language": "மொழியை மாற்றவும்"
        },
        "errors": {
            "error_cover.mp4": "உங்கள் பதிலில் இன்னும் கொஞ்சம் விவரங்களைச் சேர்க்க முடியுமா?",
            "error_empty.mp4": "பதில் இல்லை போலத் தெரிகிறது. தயவுசெய்து உங்கள் பதிலை வழங்குங்கள்.",
            "error_name.mp4": "இது முழுமையான பெயர் போலத் தெரியவில்லை. தயவுசெய்து உங்கள் முதல் பெயர் மற்றும் கடைசி பெயரை உள்ளிடுங்கள்.",
            "error_phone.mp4": "இது சரியான தொலைபேசி எண் போலத் தெரியவில்லை. சரிபார்த்து மீண்டும் உள்ளிடுங்கள்.",
            "error_skills.mp4": "குறைந்தது இரண்டு திறன்களை வழங்குங்கள்.",
            "error_year.mp4": "இது சரியான ஆண்டு போலத் தெரியவில்லை. தயவுசெய்து நான்கு இலக்க ஆண்டை உள்ளிடுங்கள்.",
            "error_email.mp4": "இது சரியான மின்னஞ்சல் முகவரி போலத் தெரியவில்லை. தயவுசெய்து மீண்டும் உள்ளிடுங்கள்.",
            "english_only": "தயவுசெய்து உங்கள் பதிலை ஆங்கிலத்தில் மட்டும் உள்ளிடவும்.",
            "q_complete.mp4": "நேர்காணலை முடித்ததற்கு நன்றி. எங்கள் குழு உங்கள் பதில்களை ஆய்வு செய்து விரைவில் தொடர்பு கொள்ளும். இனிய நாளாக அமையட்டும்."
        },
        "questions": {
            1: {
                "question": "வணக்கம், நான் Talentbot. உங்கள் Screening Interview-க்கு வரவேற்கிறேன். உங்கள் <strong>Full Name</strong> என்ன?",
                "placeholder": "உதா. பிரியா சர்மா",
                "hint": "உங்கள் முதல் மற்றும் கடைசிப் பெயரை உள்ளிடவும்"
            },
            2: {
                "question": "தயவுசெய்து உங்கள் <strong>Email Address</strong>-ஐ பகிரவும். உங்கள் விண்ணப்பத்தின் தகவல்களை அனுப்ப இதைப் பயன்படுத்துவோம்.",
                "placeholder": "உதா. priya@example.com",
                "hint": "சரியான மின்னஞ்சல் முகவரியை உள்ளிடவும்"
            },
            3: {
                "question": "நன்றி. உங்கள் <strong>Phone Number</strong> என்ன? இந்தியாவுக்கு வெளியே இருந்தால் நாட்டின் குறியீட்டைச் சேர்க்கவும்.",
                "placeholder": "உதா. +91 9876543210",
                "hint": "குறைந்தது 10 இலக்கங்கள்"
            },
            4: {
                "question": "எந்த <strong>Role</strong>-க்கு Apply செய்கிறீர்கள்?",
                "options": [
                    "Software Engineer",
                    "Data Analyst",
                    "UI/UX Designer",
                    "Product Manager",
                    "DevOps Engineer",
                    "QA Engineer"
                ],
                "options_translated": [
                    "மென்பொருள் பொறியாளர்",
                    "தரவு ஆய்வாளர்",
                    "UI/UX வடிவமைப்பாளர்",
                    "தயாரிப்பு மேலாளர்",
                    "DevOps பொறியாளர்",
                    "QA பொறியாளர்"
                ],
                "other_label": "மற்றவை (உங்கள் பணியை தட்டச்சு செய்க)",
                "placeholder": "உதா. பின்தள உருவாக்குநர், எம்.எல் பொறியாளர்...",
                "hint": "ஒரு பணியைத் தேர்ந்தெடுக்கவும் அல்லது கீழே புதியதைத் தட்டச்சு செய்யவும்"
            },
            5: {
                "question": "உங்கள் உயர்ந்த <strong>Educational Qualification</strong> என்ன?",
                "options": [
                    "Bachelor's Degree",
                    "Master's Degree",
                    "PhD",
                    "Diploma",
                    "12th / Higher Secondary",
                    "Other"
                ],
                "options_translated": [
                    "பட்டப்படிப்பு (Bachelor's)",
                    "முதுகலை பட்டப்படிப்பு (Master's)",
                    "முனைவர் பட்டம் (PhD)",
                    "டிப்ளோமா",
                    "12ஆம் வகுப்பு / மேல்நிலை",
                    "மற்றவை"
                ],
                "hint": "உங்கள் அதிகபட்ச கல்வித் தகுதியைத் தேர்ந்தெடுக்கவும்"
            },
            6: {
                "question": "உங்கள் <strong>Field of Study அல்லது Specialization</strong> என்ன?",
                "placeholder": "உதா. கணினி அறிவியல், மின்னணுவியல், எம்பிஏ",
                "hint": "உங்கள் முக்கிய பாடம் அல்லது சிறப்புத் துறை"
            },
            7: {
                "question": "நீங்கள் எந்த <strong>College அல்லது University</strong>-யில் படித்தீர்கள்?",
                "placeholder": "உதா. ஐஐடி பம்பாய், அண்ணா பல்கலைக்கழகம்",
                "hint": "உங்கள் கல்லூரி அல்லது பல்கலைக்கழகத்தின் முழுப் பெயரை உள்ளிடவும்"
            },
            8: {
                "question": "நீங்கள் எந்த ஆண்டில் <strong>Graduate</strong> செய்தீர்கள் அல்லது செய்யவிருக்கிறீர்கள்?",
                "placeholder": "உதா. 2023",
                "hint": "சரியான 4 இலக்க ஆண்டை உள்ளிடவும்"
            },
            9: {
                "question": "உங்கள் மொத்த Academic Performance எப்படி இருந்தது? உங்கள் <strong>CGPA அல்லது Percentage</strong>-ஐ கூறுங்கள்.",
                "placeholder": "உதா. 8.5 CGPA அல்லது 85%",
                "hint": "உங்கள் கல்வி மதிப்பெண்ணை உள்ளிடவும்"
            },
            10: {
                "question": "உங்களுக்கு முன் <strong>Work Experience</strong> உள்ளதா?",
                "options": [
                    "Yes, I have experience",
                    "No, I am a fresher"
                ],
                "options_translated": [
                    "ஆம், எனக்கு அனுபவம் உள்ளது",
                    "இல்லை, நான் புதியவர் (Fresher)"
                ],
                "hint": "இது நேர்காணலை உங்களுக்கேற்ப மாற்றியமைக்க உதவும்"
            },
            11: {
                "question": "ஆம் என்றால், நீங்கள் சமீபத்தில் எந்த <strong>Company</strong>-யில் வேலை செய்தீர்கள்?",
                "placeholder": "உதா. இன்ஃபோசிஸ், டிசிஎஸ், விப்ரோ",
                "hint": "நிறுவனத்தின் முழுப் பெயரை உள்ளிடவும்"
            },
            12: {
                "question": "அங்கு உங்கள் <strong>Role அல்லது Job Title</strong> என்ன?",
                "placeholder": "உதா. ஜூனியர் டெவலப்பர், பிசினஸ் அனலிஸ்ட்",
                "hint": "உங்கள் சரியான பதவி விவரம்"
            },
            13: {
                "question": "அங்கு எவ்வளவு காலம் வேலை செய்தீர்கள்? உங்கள் மொத்த <strong>Work Experience</strong>-ஐ தேர்வு செய்யுங்கள்.",
                "options": [
                    "Less than 1 year",
                    "1-2 years",
                    "2-4 years",
                    "4-6 years",
                    "6+ years"
                ],
                "options_translated": [
                    "1 வருடத்திற்கும் குறைவாக",
                    "1-2 ஆண்டுகள்",
                    "2-4 ஆண்டுகள்",
                    "4-6 ஆண்டுகள்",
                    "6+ ஆண்டுகள்"
                ],
                "hint": "உங்கள் மொத்த தோராய அனுபவத்தைத் தேர்ந்தெடுக்கவும்"
            },
            14: {
                "question": "உங்கள் முக்கிய <strong>Technical Skills</strong>-ஐ பட்டியலிடுங்கள்.",
                "placeholder": "உதா. பைதான், ஜாங்கோ, ரியாக்ட், SQL",
                "hint": "குறைந்தது 2 திறன்களை உள்ளிடவும்"
            },
            15: {
                "question": "உங்கள் <strong>Notice Period</strong> என்ன அல்லது எப்போது Join செய்ய முடியும்?",
                "options": [
                    "Immediate joiner",
                    "2 weeks",
                    "1 month",
                    "2 months",
                    "3+ months"
                ],
                "options_translated": [
                    "உடனடியாக சேரக்கூடியவர்",
                    "2 வாரங்கள்",
                    "1 மாதம்",
                    "2 மாதங்கள்",
                    "3+ மாதங்கள்"
                ],
                "hint": "தேர்ந்தெடுக்கப்பட்டால் எவ்வளவு விரைவில் பணியில் சேர முடியும்?"
            },
            16: {
                "question": "நீங்கள் எதிர்பார்க்கும் ஆண்டு <strong>Salary Range</strong> என்ன?",
                "options": [
                    "3-5 LPA",
                    "5-8 LPA",
                    "8-12 LPA",
                    "12-20 LPA",
                    "20+ LPA"
                ],
                "options_translated": [
                    "₹3-5 LPA",
                    "₹5-8 LPA",
                    "₹8-12 LPA",
                    "₹12-20 LPA",
                    "₹20+ LPA"
                ],
                "hint": "நீங்கள் எதிர்பார்க்கும் சம்பள வரம்பைத் தேர்ந்தெடுக்கவும்"
            },
            17: {
                "question": "உங்கள் <strong>LinkedIn Profile</strong> Link-ஐ பகிரலாம். விரும்பினால் இதைத் தவிர்க்கலாம்.",
                "placeholder": "https://linkedin.com/in/yourname",
                "hint": "விருப்பத்தேர்வு — தவிர்க்க சமர்ப்பி பொத்தானை அழுத்தவும்"
            },
            18: {
                "question": "இந்த <strong>Role-க்கு நீங்கள் ஏன் பொருத்தமானவர்</strong> என்பதைச் சுருக்கமாக கூறுங்கள். இரண்டு மூன்று வாக்கியங்கள் போதுமானது.",
                "placeholder": "இந்த பணிக்கு உங்களை தகுதியானவராக்குவது எது என்று சொல்லுங்கள்...",
                "hint": "குறைந்தது 20 எழுத்துக்கள்"
            }
        }
    },
    "te": {
        "ui": {
            "begin_interview": "ఇంటర్వ్యూ ప్రారంభించండి",
            "select_language": "భాషను ఎంచుకోండి",
            "sarah_speaking": "సారా మాట్లాడుతోంది...",
            "waiting_response": "మీ ప్రతిస్పందన కోసం వేచి ఉంది...",
            "listening": "వింటోంది...",
            "validation_error": "ధృవీకరణ లోపం",
            "repeat_question": "ప్రశ్నను మళ్ళీ వినండి",
            "type_message": "సందేశాన్ని టైప్ చేయండి...",
            "interview_complete": "ఇంటర్వ్యూ పూర్తయింది!",
            "thank_you": "Screening పూర్తి చేసినందుకు ధన్యవాదాలు. మా Team మీ Responses ను పరిశీలించి త్వరలో మిమ్మల్ని సంప్రదిస్తుంది. మీ రోజు శుభంగా గడవాలి.",
            "return_home": "హోమ్‌కి తిరిగి వెళ్ళండి",
            "current_question": "ప్రస్తుత ప్రశ్న",
            "question_of": "ప్రశ్న {num} / {total}",
            "progress": "ఇంటర్వ్యూ పురోగతి",
            "tips_title": "💡 చిట్కాలు",
            "tips": [
                "సమాధానం చెప్పే ముందు ఆలోచించడానికి తగినంత సమయం తీసుకోండి.",
                "అవసరమైతే ప్రశ్నను మళ్ళీ ప్లే చేయవచ్చు.",
                "మీ ప్రతిస్పందనలు మిమ్మల్ని బాగా అర్థం చేసుకోవడానికి సహాయపడతాయి."
            ],
            "guide_text": "ఇంటర్వ్యూలో మీకు మార్గనిర్దేశం చేయడానికి నేను ఇక్కడ ఉన్నాను. సిద్ధంగా ఉన్నప్పుడు టైప్ చేయండి లేదా మాట్లాడండి.",
            "change_language": "భాషను మార్చండి"
        },
        "errors": {
            "error_cover.mp4": "దయచేసి మీ సమాధానానికి కొంచెం మరింత వివరాలు జోడించగలరా?",
            "error_empty.mp4": "సమాధానం కనిపించడం లేదు. దయచేసి మీ సమాధానాన్ని ఇవ్వండి.",
            "error_name.mp4": "హ్మ్, ఇది పూర్తి పేరు లాగా కనిపించడం లేదు. దయచేసి మీ మొదటి పేరు మరియు చివరి పేరు నమోదు చేయండి.",
            "error_phone.mp4": "ఇది సరైన ఫోన్ నంబర్ లాగా కనిపించడం లేదు. దయచేసి తనిఖీ చేసి మళ్లీ నమోదు చేయండి.",
            "error_skills.mp4": "దయచేసి కనీసం రెండు నైపుణ్యాలు నమోదు చేయండి.",
            "error_year.mp4": "ఇది సరైన సంవత్సరం లాగా కనిపించడం లేదు. దయచేసి నాలుగు అంకెల సంవత్సరం నమోదు చేయండి.",
            "error_email.mp4": "హ్మ్, ఇది సరైన ఈమెయిల్ చిరునామా లాగా కనిపించడం లేదు. దయచేసి మళ్లీ నమోదు చేయండి.",
            "english_only": "దయచేసి మీ సమాధానాన్ని ఇంగ్లీషులో మాత్రమే నమోదు చేయండి.",
            "q_complete.mp4": "స్క్రీనింగ్ పూర్తి చేసినందుకు ధన్యవాదాలు. మా బృందం మీ సమాధానాలను పరిశీలించి త్వరలో మిమ్మల్ని సంప్రదిస్తుంది. మీ రోజు శుభంగా గడవాలి."
        },
        "questions": {
            1: {
                "question": "హలో, నేను Talentbot. మీ Screening Interview కు స్వాగతం. మీ <strong>Full Name</strong> ఏమిటి?",
                "placeholder": "ఉదా. ప్రియా శర్మ",
                "hint": "మీ మొదటి మరియు చివరి పేరును నమోదు చేయండి"
            },
            2: {
                "question": "మిమ్మల్ని కలవడం ఆనందంగా ఉంది. దయచేసి మీ <strong>Email Address</strong> ను పంచుకోండి. మీ దరఖాస్తు అప్‌డేట్‌లను పంపడానికి మేము దీనిని ఉపయోగిస్తాము.",
                "placeholder": "ఉదా. priya@example.com",
                "hint": "చెల్లుబాటు అయ్యే ఈమెయిల్ చిరునామాను నమోదు చేయండి"
            },
            3: {
                "question": "ధన్యవాదాలు. మీ <strong>Phone Number</strong> ఏమిటి? భారతదేశం వెలుపల ఉంటే దేశ కోడ్‌ను జోడించండి.",
                "placeholder": "ఉదా. +91 9876543210",
                "hint": "కనీసం 10 అంకెలు"
            },
            4: {
                "question": "మీరు ఏ <strong>Role</strong> కోసం Apply చేస్తున్నారు?",
                "options": [
                    "Software Engineer",
                    "Data Analyst",
                    "UI/UX Designer",
                    "Product Manager",
                    "DevOps Engineer",
                    "QA Engineer"
                ],
                "options_translated": [
                    "సాఫ్ట్‌వేర్ ఇంజనీర్",
                    "డేటా అనలిస్ట్",
                    "UI/UX డిజైనర్",
                    "ప్రొడక్ట్ మేనేజర్",
                    "దేవ్ఓప్స్ ఇంజనీర్",
                    "QA ఇంజనీర్"
                ],
                "other_label": "ఇతర (మీ పాత్రను టైప్ చేయండి)",
                "placeholder": "ఉదా. బ్యాకెండ్ డెవలపర్, ML ఇంజనీర్...",
                "hint": "ఒక పాత్రను ఎంచుకోండి లేదా క్రింద కస్టమ్ టైప్ చేయండి"
            },
            5: {
                "question": "మీ అత్యున్నత <strong>Educational Qualification</strong> ఏమిటి?",
                "options": [
                    "Bachelor's Degree",
                    "Master's Degree",
                    "PhD",
                    "Diploma",
                    "12th / Higher Secondary",
                    "Other"
                ],
                "options_translated": [
                    "బ్యాచిలర్ డిగ్రీ",
                    "మాస్టర్స్ డిగ్రీ",
                    "PhD",
                    "డిప్లొమా",
                    "12వ తరగతి / హయ్యర్ సెకండరీ",
                    "ఇతర"
                ],
                "hint": "మీ అత్యున్నత విద్యార్హత స్థాయిని ఎంచుకోండి"
            },
            6: {
                "question": "మీ <strong>Field of Study లేదా Specialization</strong> ఏమిటి?",
                "placeholder": "ఉదా. కంప్యూటర్ సైన్స్, ఎలక్ట్రానిక్స్, ఎంబీఏ",
                "hint": "మీ మేజర్ లేదా స్పెషలైజేషన్"
            },
            7: {
                "question": "మీరు ఏ <strong>College లేదా University</strong> లో చదివారు?",
                "placeholder": "ఉదా. ఐఐటీ బాంబే, ఉస్మానియా విశ్వవిద్యాలయం",
                "hint": "మీ కళాశాల లేదా విశ్వవిద్యాలయం యొక్క పూర్తి పేరును నమోదు చేయండి"
            },
            8: {
                "question": "మీరు ఏ సంవత్సరంలో <strong>Graduate</strong> అయ్యారు లేదా అవుతారని భావిస్తున్నారు?",
                "placeholder": "ఉదా. 2023",
                "hint": "చెల్లుబాటు అయ్యే 4 అంకెల సంవత్సరాన్ని నమోదు చేయండి"
            },
            9: {
                "question": "మీ మొత్తం Academic Performance ఎలా ఉంది? మీ <strong>CGPA లేదా Percentage</strong> చెప్పండి.",
                "placeholder": "ఉదా. 8.5 CGPA లేదా 85%",
                "hint": "మీ అకడమిక్ స్కోర్‌ను నమోదు చేయండి"
            },
            10: {
                "question": "మీకు ముందుగా <strong>Work Experience</strong> ఉందా?",
                "options": [
                    "Yes, I have experience",
                    "No, I am a fresher"
                ],
                "options_translated": [
                    "అవును, నాకు అనుభవం ఉంది",
                    "లేదు, నేను ఫ్రెషర్‌ని"
                ],
                "hint": "ఇంటర్వ్యూని వ్యక్తిగతీకరించడంలో ఇది మాకు సహాయపడుతుంది"
            },
            11: {
                "question": "అవును అయితే, మీరు ఇటీవల ఏ <strong>Company</strong> లో పనిచేశారు?",
                "placeholder": "ఉదా. ఇన్ఫోసిస్, టిసిఎస్, విప్రో",
                "hint": "కంపెనీ పూర్తి పేరును నమోదు చేయండి"
            },
            12: {
                "question": "అక్కడ మీ <strong>Role లేదా Job Title</strong> ఏమిటి?",
                "placeholder": "ఉదా. జూనియర్ డెవెలపర్, బిజినెస్ అనలిస్ట్",
                "hint": "మీ ఖచ్చితమైన ఉద్యోగ శీర్షిక"
            },
            13: {
                "question": "మీరు అక్కడ ఎంతకాలం పనిచేశారు? మీ మొత్తం <strong>Work Experience</strong> ఎంచుకోండి.",
                "options": [
                    "Less than 1 year",
                    "1-2 years",
                    "2-4 years",
                    "4-6 years",
                    "6+ years"
                ],
                "options_translated": [
                    "1 సంవత్సరం కంటే తక్కువ",
                    "1-2 సంవత్సరాలు",
                    "2-4 సంవత్సరాలు",
                    "4-6 సంవత్సరాలు",
                    "6+ సంవత్సరాలు"
                ],
                "hint": "మీ అంచనా మొత్తం అనుభవాన్ని ఎంచుకోండి"
            },
            14: {
                "question": "మీ ప్రధాన <strong>Technical Skills</strong> ను జాబితా చేయండి.",
                "placeholder": "ఉదా. పైథాన్, జ్యాంగో, రియాక్ట్, SQL",
                "hint": "కనీసం 2 నైపుణ్యాలను నమోదు చేయండి"
            },
            15: {
                "question": "మీ <strong>Notice Period</strong> ఎంత లేదా మీరు ఎంత త్వరగా Join అవగలరు?",
                "options": [
                    "Immediate joiner",
                    "2 weeks",
                    "1 month",
                    "2 months",
                    "3+ months"
                ],
                "options_translated": [
                    "వెంటనే చేరగలరు",
                    "2 వారాలు",
                    "1 నెల",
                    "2 నెలలు",
                    "3+ నెలలు"
                ],
                "hint": "ఎంపికైతే మీరు ఎంత త్వరగా చేరగలరు?"
            },
            16: {
                "question": "మీరు ఆశిస్తున్న వార్షిక <strong>Salary Range</strong> ఎంత?",
                "options": [
                    "3-5 LPA",
                    "5-8 LPA",
                    "8-12 LPA",
                    "12-20 LPA",
                    "20+ LPA"
                ],
                "options_translated": [
                    "₹3-5 LPA",
                    "₹5-8 LPA",
                    "₹8-12 LPA",
                    "₹12-20 LPA",
                    "₹20+ LPA"
                ],
                "hint": "మీరు ఆశిస్తున్న జీతం పరిధిని ఎంచుకోండి"
            },
            17: {
                "question": "మీ <strong>LinkedIn Profile</strong> Link ను పంచుకోండి. కావాలనుకుంటే దాటవేయవచ్చు.",
                "placeholder": "https://linkedin.com/in/yourname",
                "hint": "ఐచ్ఛికం — దాటవేయడానికి సబ్మిట్ నొక్కండి"
            },
            18: {
                "question": "ఈ <strong>Role</strong> కు మీరు ఎందుకు సరిపోతారో సంక్షిప్తంగా చెప్పండి. రెండు లేదా మూడు వాక్యాలు సరిపోతాయి.",
                "placeholder": "మిమ్మల్ని ఈ పాత్రకు ఏది అనుకూలంగా చేస్తుందో చెప్పండి...",
                "hint": "కనీసం 20 అక్షరాలు"
            }
        }
    }
}

# Add key aliases to questions dictionary so TRANSLATIONS[lang]['questions']['full_name']
# and TRANSLATIONS[lang]['questions'][1] both resolve to the exact same question dictionary.
for lang_code, lang_content in TRANSLATIONS.items():
    q_dict = lang_content.get('questions', {})
    aliases = {}
    for q_id, q_data in list(q_dict.items()):
        if isinstance(q_id, int):
            canonical_key = QUESTION_ID_TO_KEY.get(q_id)
            if canonical_key:
                aliases[canonical_key] = q_data
    # Also add legacy field names
    legacy_aliases = {
        'applied_role': 4,
        'qualification': 5,
        'institution': 7,
        'cgpa': 9,
        'company': 11,
        'previous_role': 12,
        'work_duration': 13,
        'cover_note': 18,
    }
    for leg_key, q_id in legacy_aliases.items():
        if q_id in q_dict:
            aliases[leg_key] = q_dict[q_id]
    q_dict.update(aliases)


def get_canonical_question_id(question_or_id):
    if isinstance(question_or_id, dict):
        q_id = question_or_id.get('id')
    else:
        q_id = question_or_id
    if isinstance(q_id, int):
        return q_id
    if isinstance(q_id, str):
        if q_id.isdigit():
            return int(q_id)
        if q_id in KEY_TO_QUESTION_ID:
            return KEY_TO_QUESTION_ID[q_id]
    return None


def map_option_to_canonical_english(question_or_id, selected_value, lang='en'):
    """
    Given an answer selected by candidate in any language, map it back
    to the canonical English option string.
    """
    if not selected_value:
        return selected_value

    q_id = get_canonical_question_id(question_or_id)
    if not q_id:
        return selected_value

    from .questions import QUESTION_LOOKUP
    canonical_question = QUESTION_LOOKUP.get(q_id)
    if not canonical_question or 'options' not in canonical_question:
        return selected_value

    canonical_options = canonical_question['options']
    norm_val = selected_value.strip().lower().replace('–', '-').replace('₹', '')

    # 1. Direct canonical check
    for opt in canonical_options:
        norm_opt = opt.strip().lower().replace('–', '-').replace('₹', '')
        if norm_val == norm_opt or norm_val == norm_opt.replace(' ', ''):
            return opt

    # 2. Check translated options in the given language or across all languages
    languages_to_check = [lang] if lang and lang != 'en' else ['ml', 'hi', 'ta', 'te']
    for l in languages_to_check:
        lang_trans = TRANSLATIONS.get(l, {}).get('questions', {}).get(q_id, {})
        options_translated = lang_trans.get('options_translated', [])
        options_en = lang_trans.get('options', canonical_options)
        for i, opt_trans in enumerate(options_translated):
            if opt_trans.strip().lower() == selected_value.strip().lower():
                return options_en[i] if i < len(options_en) else canonical_options[i]

    # 3. Handle specific known variants
    if q_id == 10:
        if 'fresher' in selected_value.lower() or 'തുടക്കക്കാരൻ' in selected_value or 'फ्रेशर' in selected_value or 'புதியவர்' in selected_value or 'ఫ్రెషర్' in selected_value:
            return 'No, I am a fresher'
        if 'experience' in selected_value.lower() or 'പരിചയം' in selected_value or 'अनुभव' in selected_value or 'அனுபவம்' in selected_value or 'అనుభవం' in selected_value:
            return 'Yes, I have experience'
    if q_id == 21:
        val_lower = selected_value.strip().lower()
        if any(s == val_lower for s in ['no', 'nope', 'nah']) or any(s in val_lower for s in ['fresher', 'not done', "haven't"]) or any(s in selected_value for s in ['ഇല്ല', 'नहीं', 'இல்லை', 'లేదు']):
            return 'No'
        if any(s == val_lower for s in ['yes', 'yeah', 'yep', 'yup', 'done']) or any(s in val_lower for s in ['have done', 'i have', 'yes, i have', 'yes i have']) or any(s in selected_value for s in ['അതെ', 'हाँ', 'ஆம்', 'అవును']):
            return 'Yes'

    return selected_value
