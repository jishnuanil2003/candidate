TalentBot Interview Media
========================
This directory holds pre-recorded video clips organized by language:
- english/
- malayalam/
- hindi/
- tamil/
- telugu/

Naming convention:
- Question videos: Each question video must be named q<id>.<ext> where <id> is the canonical question ID (1 to 24), e.g. q1.mp4 ... q24.mp4.
  Example: q1.mp4 is the "full name" question in every language folder.
- Fallback: If a question file is absent in a regional language folder, the system falls back to english/q<id>.<ext> and displays regional question text. If absent in all languages, the bot shows question text in the chosen language and falls back to dynamic TTS without crashing.
- Error videos (OPTIONAL):
  For each question with validation, case-specific or generic error videos can be placed in any language folder:
  1. Specific error cases (Questions 19-24):
     - <field_key>_invalid.mp4 (e.g. lead_source_invalid.mp4, location_invalid.mp4, etc.)
     - <field_key>_empty.mp4 (e.g. lead_source_empty.mp4, location_empty.mp4, etc.)
     - internship_end_date_before_start.mp4 (end date earlier than start date)
  2. Generic error videos:
     - <field_key>_error.mp4 (e.g. lead_source_error.mp4, email_error.mp4, phone_error.mp4, etc.)
     - empty_error.mp4
  Lookup order for a case:
    1. Chosen language specific file (<field_key>_<reason>.mp4)
    2. English specific file (<field_key>_<reason>.mp4)
    3. Chosen language generic file (<field_key>_error.mp4)
    4. English generic file (<field_key>_error.mp4)
    5. On-screen text in chosen language (falls back to English text and TTS)
