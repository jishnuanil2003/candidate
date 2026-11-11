# TalentBot Candidate Screening Platform

TalentBot is an AI-powered conversational candidate screening platform with a live virtual recruiter presence. It features advanced multilingual speech recognition (STT), translation processing, and dynamic text-to-speech (TTS) voice generation.

## Supported Languages
- English (en)
- Malayalam (ml)
- Hindi (hi)
- Tamil (ta)
- Telugu (te)

## Quick Start Setup

### 1. Install Dependencies
Make sure you have Python 3.10+ installed. Install all the required packages:
```bash
pip install -r requirements.txt
```

### 2. Configure Environment Variables
Create a `.env` file in the root directory and configure your Groq API key:
```ini
GROQ_API_KEY=your_groq_api_key_here
```

### 3. Run Database Migrations
Set up your local SQLite database:
```bash
python manage.py migrate
```

### 4. Create an Admin Account
To access the HR and Admin dashboard panels:
```bash
python manage.py createsuperuser
```

### 5. Start the Server
Launch the local Django development server:
```bash
python manage.py runserver
```
Visit the platform in your browser at `http://127.0.0.1:8000/`.

## Interview Questions (IDs 1–24)
1. `full_name`: Full Name (first and last name)
2. `email`: Email Address
3. `phone`: Phone Number (min 10 digits)
4. `role_applied`: Role Applied For (options or custom text)
5. `highest_qualification`: Highest Education Qualification
6. `field_of_study`: Field of Study / Specialization
7. `college`: College / University attended
8. `graduation_year`: Year of Graduation (1950-2030)
9. `academic_performance`: CGPA or Percentage
10. `has_experience`: Prior Work Experience (Experience / Fresher)
11. `last_company`: Last Company Worked At (conditional on 10)
12. `last_role`: Last Job Title / Role (conditional on 10)
13. `experience_duration`: Total Experience Duration (conditional on 10)
14. `skills`: Technical Skills (min 2 separated by commas)
15. `notice_period`: Notice Period
16. `expected_salary`: Expected Annual Salary Range
17. `linkedin`: LinkedIn Profile Link (optional)
18. `why_good_fit`: Why Good Fit / Cover Note (min 20 characters)
19. `lead_source`: How candidate heard about the role ("Friend/Referral", "Social Media", "College/Campus", "Job Portal", "Other: <text>")
20. `location`: City or Town
21. `internship_done`: Yes/No (Internship experience)
22. `internship_start_date`: Start Month and Year (conditional: skipped if 21 is "No")
23. `internship_end_date`: End Month and Year, or "Ongoing" (conditional: skipped if 21 is "No")
24. `internship_topic`: Internship Topic / Domain (min 8 characters, conditional: skipped if 21 is "No")

## Video Verification & Media Structure
- **Question videos:** Located at `interview_media/<language>/q<id>.mp4` (IDs 1–24). If missing, gracefully falls back to `english/q<id>.mp4` or TTS with localized on-screen text.
- **Error videos (Optional):** Located at `interview_media/<language>/`. Supports case-specific error videos (`<field_key>_invalid.mp4`, `<field_key>_empty.mp4`, `internship_end_date_before_start.mp4`) as well as generic `<field_key>_error.mp4`. Lookup order: chosen language specific file -> English specific file -> chosen language generic file -> English generic file -> localized on-screen text and TTS.
- **Verification command:**
  ```bash
  python manage.py check_videos --settings=config.settings_local
  ```

## Key Multilingual Capabilities
- **Speech Recognition (STT):** Converts spoken candidate responses in Malayalam, Hindi, Tamil, Telugu, and English into text using Groq's Whisper Large v3 model.
- **Dynamic Translation Layer:** Translates candidate responses to English internally before validation and storage, keeping HR records standardized.
- **Speech Synthesis (TTS):** Generates voice readouts for the virtual recruiter dynamically using Google Text-to-Speech (gTTS) streaming.
