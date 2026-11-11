# TalentBot AI HR Screening Bot – DMCore Integration Audit Report

**Date of Audit:** November 3, 2026  
**Project Path:** `D:\candidate_screening_vdo_final\candidate_screening_vdo_final`  
**Scope:** Read-only architectural and behavioral audit against the DMCore integration contract.

---

## 1. OVERVIEW

### 1.1 Architecture & Stack
- **Language & Framework:** Python 3.11 with Django 4.2+ (`django>=4.2`).
- **Architecture:** Monolithic Django web application serving server-rendered HTML templates (`screening/templates/`) and static assets. The client uses vanilla JavaScript (`interview_v2.js`, `videoEngine.js`) communicating with Django backend JSON endpoints via standard `fetch()` requests.
- **Frontend vs Backend Split:**
  - **Backend:** Django app (`screening`) handling link ingestion, session management, questions dispatching, answer normalization/translation, DMCore HTTP proxying, STT routing, and TTS generation.
  - **Frontend:** Pure HTML5/CSS/JavaScript with HTML5 `<video>` and `<audio>` tags and browser `MediaRecorder` API. There is **no Node.js/npm build step** (no Webpack, Vite, Babel, or package.json). Static assets are served directly through WhiteNoise (`whitenoise==6.12.0`).

### 1.2 Startup & Deployment
- **Local Startup:**
  - With default MySQL: `python manage.py runserver`
  - With SQLite (local development): `python manage.py runserver --settings=config.settings_local`
- **Production Deployment:**
  - Configured for **cPanel / Phusion Passenger** WSGI via `passenger_wsgi.py` (which imports `config.wsgi.application`).
  - Uses `WhiteNoise` for static asset compression and caching (`CompressedManifestStaticFilesStorage`).
- **Environment Variable Changes:**
  - Environment variables are read at process initialization via `python-dotenv` in [`config/settings.py:6`](file:///D:/candidate_screening_vdo_final/candidate_screening_vdo_final/config/settings.py#L6).
  - **No build step is needed** after updating `.env`. However, the WSGI server process must be reloaded/restarted (e.g., `touch tmp/restart.txt` on Passenger or restarting the daemon) for new values to take effect.

### 1.3 Project Tree (Top 3 Levels)

```
D:\candidate_screening_vdo_final\candidate_screening_vdo_final\
├── .env                                  # Environment variables (runtime credentials)
├── .env.example                          # Sample environment configuration file
├── .gitignore                            # Git ignore patterns
├── check_dmcore.py                       # Standalone CLI tool to probe DMCore reachability & X-API-Key
├── db.sqlite3                            # Local SQLite database file
├── manage.py                             # Django CLI administrative entry point
├── passenger_wsgi.py                     # Phusion Passenger WSGI entry point for cPanel hosting
├── README.md                             # Project setup and overview documentation
├── requirements.txt                      # Python package dependencies
├── config/                               # Project-level Django configuration
│   ├── asgi.py                           # ASGI application entry point
│   ├── settings.py                       # Base Django settings (MySQL default, WhiteNoise, CSRF)
│   ├── settings_local.py                 # Development override settings (switches DB to SQLite)
│   ├── urls.py                           # Root URL routing, Chrome devtools shim, 403 handler
│   └── wsgi.py                           # WSGI application entry point
├── screening/                            # Core interview application
│   ├── admin.py                          # Django admin registrations for HR/Candidate models
│   ├── apps.py                           # AppConfig with DMCore startup validation hook
│   ├── dmcore.py                         # DMCore HTTP client (load_session, save_answer, complete)
│   ├── forms.py                          # HR signup and authentication forms
│   ├── matching.py                       # [Legacy] Keyword and fuzzy matching for question fields
│   ├── models.py                         # Models: CandidateApplication and HRProfile
│   ├── questions.py                      # Canonical QUESTION_LOOKUP (18 questions), playlist & validation
│   ├── question_keywords.json            # [Legacy] Keyword dictionary for fuzzy matching
│   ├── tests.py                          # Unit tests for text cleaning, normalization & translations
│   ├── test_dmcore.py                    # Unit tests for DMCore client, error handling, session flow
│   ├── test_question_flow.py             # Unit tests for question ordering, fresher skips
│   ├── translations.py                   # Multi-language translations dictionary (en, ml, hi, ta, te)
│   ├── urls.py                           # URL routing for candidate API and HR dashboard
│   ├── views.py                          # Views for candidate interview, STT, TTS, auth, dashboard
│   ├── migrations/                       # Database schema migrations
│   ├── static/screening/                 # Static assets
│   │   ├── css/                          # CSS stylesheets (interview.css, base.css, etc.)
│   │   ├── js/                           # JavaScript: interview_v2.js, videoEngine.js
│   │   └── videos/                       # 18 question videos, error videos, idle video, completion video
│   └── templates/screening/              # Django HTML templates (interview.html, index.html, etc.)
```

### 1.4 Dependencies & AI Services

#### Dependencies ([`requirements.txt`](file:///D:/candidate_screening_vdo_final/candidate_screening_vdo_final/requirements.txt))
- `django>=4.2` – Web framework
- `mysqlclient==2.3.0` – MySQL database driver for production
- `whitenoise==6.12.0` – Static file serving
- `groq` – Python SDK for Groq API (STT & LLM)
- `python-dotenv` – Reading `.env` files
- `gtts` – Google Text-to-Speech library

#### AI Services Used
1. **Speech-to-Text (STT):**
   - **Groq Whisper (`whisper-large-v3`):** Called via `groq` SDK in [`screening/views.py:837-843`](file:///D:/candidate_screening_vdo_final/candidate_screening_vdo_final/screening/views.py#L837-L843) (`client.audio.transcriptions.create(model="whisper-large-v3", language="en")`). Handles all English and general voice recordings.
   - **Sarvam AI (`saaras:v3`):** Called via `requests.post` to `https://api.sarvam.ai/speech-to-text` with header `api-subscription-key` in [`screening/views.py:781-806`](file:///D:/candidate_screening_vdo_final/candidate_screening_vdo_final/screening/views.py#L781-L806). Invoked exclusively when candidate language is Hindi (`hi`) and answering question 18 (`why_good_fit` / `cover_note`).
2. **Large Language Model (LLM):**
   - **Groq LLaMA-3.1-8b-instant:** Called via `groq` SDK (`client.chat.completions.create`) with `temperature=0.0`:
     - Spoken email parsing and phonetic error correction in [`screening/views.py:188-195`](file:///D:/candidate_screening_vdo_final/candidate_screening_vdo_final/screening/views.py#L188-L195).
     - Spoken numeric normalization for phone, year, and CGPA in [`screening/views.py:92-100`](file:///D:/candidate_screening_vdo_final/candidate_screening_vdo_final/screening/views.py#L92-L100).
     - Multilingual translation to English with transliteration prompts for proper nouns (names, colleges, companies) in [`screening/views.py:312-325`](file:///D:/candidate_screening_vdo_final/candidate_screening_vdo_final/screening/views.py#L312-L325).
     - Validation error message translation into regional languages in [`screening/views.py:349-357`](file:///D:/candidate_screening_vdo_final/candidate_screening_vdo_final/screening/views.py#L349-L357).
3. **Avatar System:**
   - **Pre-recorded Video State Engine:** There is **no generative or streaming avatar API** (such as HeyGen, Synthesia, or D-ID). The avatar is simulated via a pre-recorded video state engine ([`screening/static/screening/js/videoEngine.js`](file:///D:/candidate_screening_vdo_final/candidate_screening_vdo_final/screening/static/screening/js/videoEngine.js)) that transitions seamlessly between an idle loop (`idle_waiting.mp4`), 18 fixed question clips (`q_*.mp4`), error reaction clips (`error_*.mp4`), and a completion clip (`q_complete.mp4`).
4. **Text-to-Speech (TTS):**
   - **gTTS (Google Text-to-Speech):** Called dynamically via [`screening/views.py:945-970`](file:///D:/candidate_screening_vdo_final/candidate_screening_vdo_final/screening/views.py#L945-L970) at `/api/tts/`. When a candidate chooses Malayalam, Hindi, Tamil, or Telugu, the video audio is muted and replaced by translated TTS streamed through HTML5 Audio.

---

## 2. CONFIGURATION

### 2.1 Environment Variables & Configuration Keys
All environment variables read by the project, their presence in `.env`, and their masked values:

| Variable Name | Location Read | Present in `.env`? | Masked Value | Purpose |
| :--- | :--- | :---: | :---: | :--- |
| `GROQ_API_KEY` | `config/settings.py:8` | Yes | `gsk***` | Groq Whisper STT & LLaMA translation |
| `SARVAM_API_KEY` | `config/settings.py:9` | Yes | `sk_***` | Sarvam AI Hindi STT for question 18 |
| `DMCORE_BASE_URL` | `screening/dmcore.py:36` | Yes | `htt***` | Base URL of the DMCore Django server |
| `DMCORE_API_KEY` | `screening/dmcore.py:37` | Yes | `8Ei***` | Shared secret key for DMCore authentication |

#### Hardcoded Configuration in Code (Not in `.env`):
- `SECRET_KEY`: Hardcoded in [`config/settings.py:10`](file:///D:/candidate_screening_vdo_final/candidate_screening_vdo_final/config/settings.py#L10) (`django-insecure-talentbot-screening-secret-key-change-in-production`).
- `DEBUG`: Hardcoded to `True` in [`config/settings.py:11`](file:///D:/candidate_screening_vdo_final/candidate_screening_vdo_final/config/settings.py#L11).
- `ALLOWED_HOSTS`: Hardcoded to `['*']` in [`config/settings.py:12`](file:///D:/candidate_screening_vdo_final/candidate_screening_vdo_final/config/settings.py#L12).
- `DATABASES['default']`: Hardcoded MySQL credentials in [`config/settings.py:53-62`](file:///D:/candidate_screening_vdo_final/candidate_screening_vdo_final/config/settings.py#L53-L62):
  - Database: `infoxtec_DBIEEE30ml23062026`, User: `infoxtec_DBIEEE30ml23062026`, Host: `localhost`, Port: `3306`.
  - Development override to SQLite is in [`config/settings_local.py:3-8`](file:///D:/candidate_screening_vdo_final/candidate_screening_vdo_final/config/settings_local.py#L3-L8).
- `CSRF_TRUSTED_ORIGINS`: Hardcoded list in [`config/settings.py:96-103`](file:///D:/candidate_screening_vdo_final/candidate_screening_vdo_final/config/settings.py#L96-L103):
  - `http://127.0.0.1:8000`, `http://localhost:8000`, `http://127.0.0.1`, `http://localhost`, `https://website132.altostechnologies.in`, `http://website132.altostechnologies.in`.
- **CORS / Allowed Origins:** `django-cors-headers` is **not installed** and there are **no CORS settings** in `settings.py`.

### 2.2 `.env.example` Audit
- `.env.example` exists at [`D:\candidate_screening_vdo_final\candidate_screening_vdo_final\.env.example`](file:///D:/candidate_screening_vdo_final/candidate_screening_vdo_final/.env.example).
- **Contents:**
  ```ini
  DMCORE_BASE_URL=replace_with_dmcore_base_url
  DMCORE_API_KEY=replace_with_same_value_as_AI_HR_API_KEY
  ```
- **Discrepancy:** It lists only `DMCORE_BASE_URL` and `DMCORE_API_KEY`. It **omits** `GROQ_API_KEY` and `SARVAM_API_KEY`, both of which are active dependencies.

### 2.3 Configuration Loading & Startup Behavior
1. **Loading:** Loaded at the top of [`config/settings.py:6`](file:///D:/candidate_screening_vdo_final/candidate_screening_vdo_final/config/settings.py#L6) via `load_dotenv(BASE_DIR / ".env")`.
2. **Startup Validation:** In [`screening/apps.py:8-10`](file:///D:/candidate_screening_vdo_final/candidate_screening_vdo_final/screening/apps.py#L8-L10), the `ScreeningConfig.ready()` method invokes `validate_configuration()`:
   ```python
   # screening/dmcore.py:26-32
   def validate_configuration():
       """Log missing DMCore settings without ever logging their values."""
       missing = [name for name in ('DMCORE_BASE_URL', 'DMCORE_API_KEY') if not os.environ.get(name, '').strip()]
       if missing:
           logger.error('DMCore configuration missing required .env variable(s): %s', ', '.join(missing))
           return False
       return True
   ```
3. **Behavior if Keys Missing:**
   - On startup, missing keys log an error (`logger.error`) but **do not crash the server** (Django starts up normally).
   - At runtime, if a candidate navigates to the interview URL and `DMCORE_BASE_URL` or `DMCORE_API_KEY` is missing:
     - `_request()` in [`screening/dmcore.py:38-41`](file:///D:/candidate_screening_vdo_final/candidate_screening_vdo_final/screening/dmcore.py#L38-L41) raises `DmcoreError('DMCore configuration is missing: ...', kind='configuration')`.
     - `index()` in [`screening/views.py:439-442`](file:///D:/candidate_screening_vdo_final/candidate_screening_vdo_final/screening/views.py#L439-L442) catches it and renders `screening/entry_message.html` with HTTP 500: `"Interview service configuration is missing. Please contact the recruiter."`.

---

## 3. LINK HANDLING

### 3.1 URL Query Parameter Ingestion
- **Code Location:** [`screening/views.py:416-421`](file:///D:/candidate_screening_vdo_final/candidate_screening_vdo_final/screening/views.py#L416-L421)
- **Implementation:**
  ```python
  def index(request):
      token = request.GET.get('token', '').strip()
      if not token:
          return render(request, 'screening/entry_message.html', {
              'message': 'Please use the interview link sent to you'
          }, status=400)
  ```
- **CRITICAL FINDING:** `views.index()` **only** inspects `request.GET.get('token')`. It completely ignores `data`, `exp`, and `sig`.

### 3.2 Signature (`sig`) & Expiration (`exp`) Verification
- **In Live Request Flow (`views.index`):** **NO verification is performed.** The `sig` and `exp` parameters are never inspected.
- **Orphaned Helper Code in Codebase:**
  [`screening/dmcore.py:117-156`](file:///D:/candidate_screening_vdo_final/candidate_screening_vdo_final/screening/dmcore.py#L117-L156) contains a function `decode_interview_link(encoded, expires_at, signature, now=None)`.
  ```python
  # screening/dmcore.py:128-132
  expected = hmac.new(key.encode('utf-8'), f'{encoded}.{expires_at}'.encode('utf-8'), hashlib.sha256).hexdigest()
  if not hmac.compare_digest(expected, signature):
      raise DmcoreError('Invalid interview link', 400, kind='invalid_link')
  if expiration <= int(time.time() if now is None else now):
      raise DmcoreError('Interview link has expired', 410, kind='expired')
  ```
  - **HMAC Scheme Check:** The HMAC scheme in this function matches the user contract: `hmac.new(key, f'{encoded}.{expires_at}', sha256).hexdigest()`.
  - **Status:** This function is **never called anywhere in the active views or models**.
  - **Schema Incompatibility:** Furthermore, lines 147–153 of this orphaned function assert that every question in `data` has `{'field_name', 'description'}`:
    ```python
    if (not isinstance(question, dict) or set(question) != {'field_name', 'description'}
            or not isinstance(question['field_name'], str) or not isinstance(question['description'], str)):
        raise DmcoreError('Invalid interview link', 400, kind='invalid_link')
    ```
    If `decode_interview_link()` were called with the actual contract payload (`[{"question_id": 1, "field_key": "full_name"}]`), it would **fail with HTTP 400: 'Invalid interview link'**.

### 3.3 Data and Token Storage
- `data`: Completely ignored and discarded by the application.
- `token`: Passed to `load_session(token)` to fetch data from DMCore. If valid, stored in session:
  - `request.session['dmcore_token'] = token` ([`screening/views.py:469`](file:///D:/candidate_screening_vdo_final/candidate_screening_vdo_final/screening/views.py#L469))
  - `request.session['token_interview'] = True` ([`screening/views.py:468`](file:///D:/candidate_screening_vdo_final/candidate_screening_vdo_final/screening/views.py#L468))

### 3.4 Fallback & Candidate-Facing Error Messages

#### Exact Message: *"No interview questions are available right now, please contact the recruiter"*
- **Definition:** [`screening/questions.py:6`](file:///D:/candidate_screening_vdo_final/candidate_screening_vdo_final/screening/questions.py#L6):
  ```python
  NO_QUESTIONS_MESSAGE = 'No interview questions are available right now, please contact the recruiter'
  ```
- **Trigger Conditions in [`screening/views.py:458-466`](file:///D:/candidate_screening_vdo_final/candidate_screening_vdo_final/screening/views.py#L458-L466):**
  1. DMCore session endpoint returns an empty questions list:
     ```python
     dmcore_questions = session_data.get('questions') or []
     if not dmcore_questions:
         logger.info('DMCore session returned no interview questions')
         return render(request, 'screening/entry_message.html', {'message': NO_QUESTIONS_MESSAGE})
     ```
  2. None of the question IDs in the list match known IDs 1–18 in `QUESTION_LOOKUP`:
     ```python
     playlist = build_dmcore_playlist(dmcore_questions)
     if not playlist:
         logger.info('No known DMCore question IDs remain after filtering')
         return render(request, 'screening/entry_message.html', {'message': NO_QUESTIONS_MESSAGE})
     ```

#### Complete Catalog of Candidate-Facing Error Messages:
1. **Entry Page Errors ([`screening/views.py:419-456`](file:///D:/candidate_screening_vdo_final/candidate_screening_vdo_final/screening/views.py#L419-L456)):**
   - `"Please use the interview link sent to you"` (HTTP 400, when `?token=` parameter is missing).
   - `"This link is not valid"` (HTTP 400, when DMCore returns 400 or 404).
   - `"This link has expired, please contact the recruiter"` (HTTP 410, when DMCore returns 410).
   - `"This interview has already been completed"` (HTTP 409, when DMCore returns 409).
   - `"Something went wrong. Please try again shortly or contact the recruiter."` (HTTP 403, when DMCore rejects the API key with 401 or 403).
   - `"Interview service timed out. Please try again shortly."` (HTTP 504, DMCore request timeout).
   - `"Interview service is unreachable. Please try again shortly."` (HTTP 503, connection refused or network unreachable).
   - `"Interview service configuration is missing. Please contact the recruiter."` (HTTP 500, when `DMCORE_BASE_URL` or `DMCORE_API_KEY` is not set).
   - Generic fallback via `_dmcore_public_error()` ([`screening/views.py:27-39`](file:///D:/candidate_screening_vdo_final/candidate_screening_vdo_final/screening/views.py#L27-L39)):
     - `"Interview service refused the connection. Please try again shortly."`
     - `"Interview service returned HTTP {status}. Please try again shortly."`
     - `"Interview service failed. Please contact the recruiter."`
2. **Question Flow Errors ([`screening/views.py:527, 575`](file:///D:/candidate_screening_vdo_final/candidate_screening_vdo_final/screening/views.py#L527-L575)):**
   - `"Interview link required"` (HTTP 403, if session has no active token mode).
   - `"Could not load the next question."` (HTTP 400, on unhandled exception).
3. **Answer Submission Errors ([`screening/views.py:584-648`](file:///D:/candidate_screening_vdo_final/candidate_screening_vdo_final/screening/views.py#L584-L648)):**
   - `"Please enter a text answer."` (HTTP 400).
   - `"Question mismatch."` (HTTP 400).
   - `"Please enter an answer of up to 10,000 characters."` (HTTP 400).
   - `"Please enter your response in English only."` (Localized for Malayalam, Tamil, Telugu).
4. **Validation Errors ([`screening/questions.py:134-165`](file:///D:/candidate_screening_vdo_final/candidate_screening_vdo_final/screening/questions.py#L134-L165)):**
   - `"This field cannot be empty. Please provide an answer."`
   - `"Please enter your full name — first and last name."`
   - `"Name should not contain numbers."`
   - `"Please enter a valid email address."`
   - `"Please enter a valid phone number with at least 10 digits."`
   - `"Please enter a valid 4-digit graduation year."`
   - `"Please enter at least 2 skills, separated by commas."`
   - `"Please enter a valid URL starting with https://"`
   - `"Please write at least 20 characters for your answer."`
   - `"Please select one of the provided options."`
5. **Interview Completion Errors ([`screening/views.py:868, 887, 899`](file:///D:/candidate_screening_vdo_final/candidate_screening_vdo_final/screening/views.py#L868-L899)):**
   - `"Interview is not complete"` (HTTP 403).
   - `"We could not save your interview answers. Please try again or contact the recruiter."` (HTTP 503).
6. **Frontend UI Messages ([`screening/static/screening/js/interview_v2.js:263, 318, 322, 612`](file:///D:/candidate_screening_vdo_final/candidate_screening_vdo_final/screening/static/screening/js/interview_v2.js)):**
   - `"Microphone access denied. Please type your answer."`
   - `"No speech detected. Please speak clearly or type your response."`
   - `"Speech recognition is temporarily unavailable. Please type your response."`
   - `"Network error. Please check your connection and try again."`

---

## 4. DMCORE CALLS

### 4.1 All DMCore API Calls
All external calls are centralized in [`screening/dmcore.py`](file:///D:/candidate_screening_vdo_final/candidate_screening_vdo_final/screening/dmcore.py):

#### 1. Session Endpoint: `load_session(token)`
- **Path:** [`screening/dmcore.py:93-94`](file:///D:/candidate_screening_vdo_final/candidate_screening_vdo_final/screening/dmcore.py#L93-L94)
- **URL:** `{DMCORE_BASE_URL}/api/interview/session/`
- **Method:** `GET`
- **Headers:**
  - `X-API-Key: {DMCORE_API_KEY}`
  - `X-Interview-Token: {token}`
  - `Accept: application/json`
- **Body:** `None`
- **Response Parsing:** `json.loads(response_body.decode('utf-8'))`

#### 2. Answer Endpoint: `save_answer(token, question_id, answer)`
- **Path:** [`screening/dmcore.py:97-106`](file:///D:/candidate_screening_vdo_final/candidate_screening_vdo_final/screening/dmcore.py#L97-L106)
- **URL:** `{DMCORE_BASE_URL}/api/interview/answer/`
- **Method:** `POST`
- **Headers:**
  - `X-API-Key: {DMCORE_API_KEY}`
  - `X-Interview-Token: {token}`
  - `Content-Type: application/json`
  - `Accept: application/json`
- **Body:**
  ```json
  {
    "token": "<token>",
    "answers": [
      {
        "question_id": 4,
        "answer": "<truncated to 855 chars>"
      }
    ]
  }
  ```
- **Response Parsing:** `json.loads(response_body.decode('utf-8'))`. Expects `result.get('success') is True`. If not, raises `DmcoreError('DMCore did not confirm saving the answer', kind='invalid_response')`.

#### 3. Completion Endpoint: `complete_interview(token)`
- **Path:** [`screening/dmcore.py:109-114`](file:///D:/candidate_screening_vdo_final/candidate_screening_vdo_final/screening/dmcore.py#L109-L114)
- **URL:** `{DMCORE_BASE_URL}/api/interview/complete/`
- **Method:** `POST`
- **Headers:** Same as above (`X-API-Key`, `X-Interview-Token`, `Content-Type: application/json`)
- **Body:** `{}`
- **Response Parsing:** Expects `result.get('success') is True`.

### 4.2 Caller Origin (Browser vs Backend)
- **All calls to DMCore are executed strictly from the Django backend server** in `screening/dmcore.py` using Python's standard `urllib.request`.
- The candidate's browser communicates exclusively with the local Django server (`/api/question/`, `/api/answer/`, `/api/complete/`).
- **Security & CORS implications:**
  - The shared `DMCORE_API_KEY` is **never exposed to the candidate's browser**.
  - No CORS setup between the candidate browser and DMCore is necessary.

### 4.3 Error Handling & Logging
[`screening/dmcore.py:53-85`](file:///D:/candidate_screening_vdo_final/candidate_screening_vdo_final/screening/dmcore.py#L53-L85) implements error handling:
- **HTTP 401 / 403:** Logs `logger.error('key rejected (HTTP %s)', error.code)`. Raises `DmcoreError('DMCore rejected the configured API key', error.code, kind='authentication')`. (API key value is never logged).
- **HTTP 400 / 404 / 410 / 409 / 5xx:** Logs `logger.error('DMCore returned a non-2xx response (HTTP %s)', error.code)`. Raises `DmcoreError('DMCore returned HTTP %s' % error.code, error.code, kind='http')`.
- **Timeouts:** Timeout is set to 10 seconds (`TIMEOUT_SECONDS = 10`). Caught via `(socket.timeout, TimeoutError)` and `URLError`. Logs `logger.error('DMCore request timed out after %s seconds', TIMEOUT_SECONDS)`. Raises `DmcoreError('DMCore request timed out', kind='timeout')`.
- **Connection Refused:** Caught via `ConnectionRefusedError`. Logs `logger.error('DMCore connection was refused; confirm DMCore is running and reachable')`. Raises `DmcoreError('DMCore connection was refused', kind='connection_refused')`.
- **General Unreachable:** Caught via `URLError`, `OSError`. Logs `logger.error('DMCore is unreachable (%s)', type(reason).__name__)`. Raises `DmcoreError('DMCore is unreachable', kind='connection')`.

### 4.4 Expected Session Response Shape vs DMCore Contract

| Attribute | Contract Specified by DMCore | Bot Expected Response Shape | Differences / Potential Issues |
| :--- | :--- | :--- | :--- |
| **Endpoint URL** | `DMCORE_BASE_URL/api/interview/session/` | `DMCORE_BASE_URL/api/interview/session/` | Matches |
| **HTTP Method** | `GET` or `POST` | `GET` only ([`dmcore.py:47`](file:///D:/candidate_screening_vdo_final/candidate_screening_vdo_final/screening/dmcore.py#L47)) | If DMCore requires `POST`, bot gets HTTP 405 |
| **Token Delivery** | `(API key + token)` | Header `X-Interview-Token: <token>` | If DMCore expects query param or body, request fails |
| **Response Root** | `{"candidate": {...}, "questions": [...]}` | `{"candidate": {...}, "questions": [...]}` | Matches structure |
| **Candidate Object** | `{"name": "..."}` | `candidate_data.get('name', '')` | Matches |
| **Question List Item** | `{"question_id": N, "field_key": "..."}` | `{"question_id": N, "field_key": "..."}` | Matches in `build_dmcore_playlist` |
| **Completion Call** | Not part of contract | Calls `POST /api/interview/complete/` | **High Risk:** Bot fails interview if DMCore lacks this endpoint |
| **Answer Confirmation** | Not specified | Requires `{"success": true}` | **High Risk:** If DMCore returns `{"status": "ok"}` or HTTP 200 `{}` without `success: true`, bot reports failure |

---

## 5. QUESTIONS AND PLAYBACK

### 5.1 The 18 Canonical Questions & Media Mapping
- **Location:** [`screening/questions.py:11-87`](file:///D:/candidate_screening_vdo_final/candidate_screening_vdo_final/screening/questions.py#L11-L87) (`QUESTION_LOOKUP`).
- **Disk Path for Media:** [`screening/static/screening/videos/`](file:///D:/candidate_screening_vdo_final/candidate_screening_vdo_final/screening/static/screening/videos/)

| ID | Field Key | Question Prompt Text | Input Type | Options / Condition | Question Video | Error Video | Disk Status |
| :---: | :--- | :--- | :---: | :--- | :--- | :--- | :---: |
| **1** | `full_name` | "Hello, I'm Talentbot. Welcome to your screening interview... What is your full name?" | `text` | First & last name required; no digits | `q_fullname.mp4` | `error_name.mp4` | Present (17.5 MB) |
| **2** | `email` | "Nice to meet you. Could you please share your email address?..." | `email` | Standard email regex; cleaned via Groq LLM | `q_email.mp4` | `error_email.mp4` | Present (7.4 MB) |
| **3** | `phone` | "Thank you. What is your phone number?..." | `text` | Min 10 digits | `q_phone.mp4` | `error_phone.mp4` | Present (7.7 MB) |
| **4** | `role_applied` | "Which role are you applying for?" | `options_or_text` | 'Software Engineer', 'Data Analyst', 'UI/UX Designer', 'Product Manager', 'DevOps Engineer', 'QA Engineer', Other | `q_role.mp4` | `error_empty.mp4` | Present (10.5 MB) |
| **5** | `highest_qualification`| "What is your highest educational qualification?" | `options` | "Bachelor's Degree", "Master's Degree", 'PhD', 'Diploma', '12th / Higher Secondary', 'Other' | `q_qualification.mp4` | `error_empty.mp4` | Present (3.1 MB) |
| **6** | `field_of_study` | "What was your field of study or specialization?" | `text` | Non-empty text | `q_field.mp4` | `error_empty.mp4` | Present (4.7 MB) |
| **7** | `college` | "Which college or university did you attend?" | `text` | Non-empty text | `q_institution.mp4` | `error_empty.mp4` | Present (2.2 MB) |
| **8** | `graduation_year` | "Which year did you graduate or expect to graduate?" | `text` | 4-digit year (1950–2030) | `q_gradyear.mp4` | `error_year.mp4` | Present (3.5 MB) |
| **9** | `academic_performance`| "What was your overall academic performance?..." | `text` | Non-empty text | `q_cgpa.mp4` | `error_empty.mp4` | Present (8.8 MB) |
| **10**| `has_experience` | "Do you have any prior work experience?" | `options` | 'Yes, I have experience', 'No, I am a fresher' | `q_experience.mp4` | `error_empty.mp4` | Present (4.1 MB) |
| **11**| `last_company` | "Which company did you most recently work at?" | `text` | Skipped if Q10 was fresher | `q_company.mp4` | `error_empty.mp4` | Present (3.6 MB) |
| **12**| `last_role` | "What was your role or job title there?" | `text` | Skipped if Q10 was fresher | `q_prevrole.mp4` | `error_empty.mp4` | Present (2.9 MB) |
| **13**| `experience_duration`| "How long did you work there?..." | `options` | 'Less than 1 year', '1-2 years', '2-4 years', '4-6 years', '6+ years' | `q_duration.mp4` | `error_empty.mp4` | Present (4.0 MB) |
| **14**| `skills` | "Could you list your top technical skills?..." | `text` | At least 2 skills comma-separated | `q_skills.mp4` | `error_skills.mp4` | Present (19.6 MB) |
| **15**| `notice_period` | "What is your notice period or how soon can you start?" | `options` | 'Immediate joiner', '2 weeks', '1 month', '2 months', '3+ months' | `q_notice.mp4` | `error_empty.mp4` | Present (9.9 MB) |
| **16**| `expected_salary` | "What is your expected annual salary range?" | `options` | '3-5 LPA', '5-8 LPA', '8-12 LPA', '12-20 LPA', '20+ LPA' | `q_salary.mp4` | `error_empty.mp4` | Present (2.6 MB) |
| **17**| `linkedin` | "If you have a LinkedIn profile, please share the link..." | `text` | Optional (`optional: True`), must start with `http://` or `https://` if provided | `q_linkedin.mp4` | `error_empty.mp4` | Present (4.8 MB) |
| **18**| `why_good_fit` | "Could you briefly tell me why you are a good fit for this role?..." | `textarea` | Min 20 characters | `q_cover.mp4` | `error_cover.mp4` | Present (9.1 MB) |

- **Additional Videos Present:**
  - `idle_waiting.mp4` (5.1 MB) – Looping backdrop avatar while listening.
  - `q_complete.mp4` (9.2 MB) – Thank-you video played upon interview completion.
- **Media File Verification:** All 18 question videos, all 7 error videos, the idle video, and the completion video are present on disk. **No media files are missing.**

### 5.2 Question Selection Logic
- In token interview mode, questions are **NOT** chosen via LLM or keyword matching.
- [`screening/questions.py:94-112`](file:///D:/candidate_screening_vdo_final/candidate_screening_vdo_final/screening/questions.py#L94-L112) implements `build_dmcore_playlist(dmcore_questions)`:
  - Iterates over the array received from DMCore.
  - For each element, checks `question_id in QUESTION_LOOKUP`.
  - Rejects unknown IDs with a warning.
  - Returns a playlist containing **strictly the question IDs sent by DMCore in their received order**.

### 5.3 Conditional Logic & Skipping
- **Fresher Skip Logic ([`screening/questions.py:115-126`](file:///D:/candidate_screening_vdo_final/candidate_screening_vdo_final/screening/questions.py#L115-L126)):**
  - Evaluates `get_dmcore_active_questions(playlist, answers)`.
  - Condition: If question 10 was present in the playlist AND the candidate answered `'No, I am a fresher'`, question IDs 11, 12, and 13 (`last_company`, `last_role`, `experience_duration`) are filtered out.
  - If question 10 was not sent by DMCore, questions 11–13 remain in the active playlist.
- **LinkedIn Question (17):**
  - Configured with `'optional': True`.
  - If the candidate submits an empty answer, [`screening/views.py:713-714`](file:///D:/candidate_screening_vdo_final/candidate_screening_vdo_final/screening/views.py#L713-L714) skips saving to DMCore and advances directly to question 18.

### 5.4 State Machine & Video Preloading
- **Backend State:** Tracked in Django session (`request.session['q_index']`), pointing to the index in the active questions playlist.
- **Frontend State:** Managed by `VideoEngine` ([`screening/static/screening/js/videoEngine.js`](file:///D:/candidate_screening_vdo_final/candidate_screening_vdo_final/screening/static/screening/js/videoEngine.js)) with states: `'idle'`, `'speaking'`, `'waiting'`, `'error'`.
- **Preloading:** [`VideoEngine.preloadPair(currentUrl, nextUrl)`](file:///D:/candidate_screening_vdo_final/candidate_screening_vdo_final/screening/static/screening/js/videoEngine.js#L55) maintains only the active question video and next question video in the browser cache, evicting earlier videos to prevent browser memory leaks.

### 5.5 Handling of Question IDs 1, 2, 3 (Full Name, Email, Phone)
- **Current Behavior:** Questions 1, 2, and 3 **are asked if DMCore includes them in the session questions list**.
- The candidate name returned in the session data (`candidate.name`) is only used to populate the greeting banner (`"Hello, {name}. Your interview is ready."`) in [`screening/static/screening/js/interview_v2.js:388-390`](file:///D:/candidate_screening_vdo_final/candidate_screening_vdo_final/screening/static/screening/js/interview_v2.js#L388-L390).
- The bot does **not** automatically skip questions 1, 2, or 3 based on link metadata.

---

## 6. ANSWERS

### 6.1 Voice & Text Ingestion, STT & Extraction
1. **Audio Recording:** Candidate audio is recorded via browser `MediaRecorder` at 64 kbps WebM and POSTed to `/api/transcribe/`.
2. **Transcription ([`screening/views.py:763-858`](file:///D:/candidate_screening_vdo_final/candidate_screening_vdo_final/screening/views.py#L763-L858)):**
   - Hindi question 18 is routed to Sarvam AI (`https://api.sarvam.ai/speech-to-text`).
   - All other questions are routed to Groq Whisper (`whisper-large-v3`, `language='en'`).
3. **Data Extraction & Phonetic Correction:**
   - **Email (Question 2):** Handled by `clean_transcribed_email()` ([`screening/views.py:210-272`](file:///D:/candidate_screening_vdo_final/candidate_screening_vdo_final/screening/views.py#L210-L272)). Calls Groq LLaMA-3.1-8b-instant to clean expressions like *"rahul at the rate of gmail dot com"* into `rahul@gmail.com`. Includes regex fallback.
   - **Phone (Question 3):** Handled by `clean_transcribed_phone()` ([`screening/views.py:203-208`](file:///D:/candidate_screening_vdo_final/candidate_screening_vdo_final/screening/views.py#L203-L208)), stripping all non-digits except a leading `+`.
   - **Year (Question 8) & CGPA (Question 9):** Cleaned and normalized in [`screening/views.py:105-116`](file:///D:/candidate_screening_vdo_final/candidate_screening_vdo_final/screening/views.py#L105-L116).
4. **Validation:** Executed in [`screening/questions.py:129-166`](file:///D:/candidate_screening_vdo_final/candidate_screening_vdo_final/screening/questions.py#L129-L166) (`validate_answer`).

### 6.2 Answer Persistence
- **Storage Target:**
  - In DMCore mode (`token_interview = True`), answers are **saved exclusively to DMCore**. They are **not saved to the local SQLite/MySQL database**.
  - Local database `CandidateApplication` records are created **only** in local demo mode (`request.session['demo_mode'] = True`).
- **Timing & Request Format:**
  - Answers are sent **immediately and individually** as each question is answered ([`screening/views.py:722`](file:///D:/candidate_screening_vdo_final/candidate_screening_vdo_final/screening/views.py#L722)).
  - Request format sent to `POST /api/interview/answer/`:
    ```json
    {
      "token": "<token>",
      "answers": [
        {
          "question_id": 4,
          "answer": "<answer text truncated to 855 chars>"
        }
      ]
    }
    ```
  - Headers: `X-API-Key: <key>`, `X-Interview-Token: <token>`, `Content-Type: application/json`.
  - **Comparison with Contract:** This matches the contract requirement: `{"token": "...", "answers": [{"question_id": N, "answer": "..."}]}` with ONE answer per request and API key header.

### 6.3 Retry Logic & Failure Handling
- **Immediate Question Retry ([`screening/views.py:720-739`](file:///D:/candidate_screening_vdo_final/candidate_screening_vdo_final/screening/views.py#L720-L739)):**
  - Tries up to 2 times (`for attempt in range(2)`).
  - If DMCore returns HTTP 400: Logs warning and continues immediately without failing (treats as unsupported question ID).
  - If DMCore returns any other error (e.g., 500, timeout): Retries once.
  - If still failing after retry: Saves the item to session queue:
    `request.session['unsaved_answers'].append({'question_id': q['id'], 'answer': answer_text})`.
  - The candidate's interview flow is **not interrupted**; the UI continues to the next question.
- **End-of-Interview Batch Retry ([`screening/views.py:871-887`](file:///D:/candidate_screening_vdo_final/candidate_screening_vdo_final/screening/views.py#L871-L887)):**
  - In `complete_application()`, re-attempts saving all items in `request.session['unsaved_answers']`.
  - If any answers still cannot be saved: Returns HTTP 503:
    `"We could not save your interview answers. Please try again or contact the recruiter."`
  - If all answers succeed: Calls `dmcore_complete_interview(token)` with up to 3 retries. If completion fails, returns HTTP 503.

---

## 7. WHAT BREAKS TODAY

### 7.1 Read-Only Checks Executed
- **Django Configuration Check:**
  `python manage.py check --settings=config.settings_local` exited with code 0 (`System check identified no issues (0 silenced)`).
- **Test Suite Execution:**
  Ran `python manage.py test screening --settings=config.settings_local`:
  - 31 tests ran: 28 passed, 3 failed.
  - All DMCore integration tests in `test_dmcore.py` and `test_question_flow.py` passed.
  - The 3 failures in `tests.py` are caused by:
    1. `test_clean_transcribed_email`: Sandbox network isolation blocked Groq API call; regex fallback preserved `"My email is "`.
    2. `test_phone_validation_with_spaces_commas_dashes`: Test passed mock `{"id": "phone"}` instead of integer `3`.
    3. `test_transcribe_audio_routes_hindi_cover_note_to_sarvam`: Test passed `question_id: 'cover_note'`, but view expects `'18'`.

---

### 7.2 Ranked Breakdown of Mismatches Against the DMCore Contract

Ordered by likelihood of causing *"No interview questions are available"* or HTTP 503 / 400 errors:

#### 1. CRITICAL: Query Parameter Ingestion Ignores `data`, `exp`, `sig`
- **Location:** [`screening/views.py:417`](file:///D:/candidate_screening_vdo_final/candidate_screening_vdo_final/screening/views.py#L417)
- **Problem:** When DMCore sends `<bot URL>/?data=...&token=...&exp=...&sig=...`, the bot reads **only** `token`. It discards `data`, `exp`, and `sig`.
- **Failure Impact:**
  - If DMCore supplies candidate and question definitions primarily via the signed `data` param in the URL, the bot never unpacks them.
  - The bot immediately issues a network call to `GET /api/interview/session/`. If DMCore's session endpoint is slow, down, or returns an empty list, the bot immediately renders:
    **"No interview questions are available right now, please contact the recruiter"**.

#### 2. CRITICAL: Link Decoder Has Schema Incompatibility with Contract
- **Location:** [`screening/dmcore.py:148-150`](file:///D:/candidate_screening_vdo_final/candidate_screening_vdo_final/screening/dmcore.py#L148-L150)
- **Problem:** If `decode_interview_link` is wired into `views.index` as currently written, it strictly checks:
  ```python
  if (not isinstance(question, dict) or set(question) != {'field_name', 'description'} ...):
      raise DmcoreError('Invalid interview link', 400, kind='invalid_link')
  ```
  The DMCore contract defines `questions` as: `[{"question_id": 1, "field_key": "full_name"}, ...]`.
- **Failure Impact:** The bot throws HTTP 400 `"Invalid interview link"` on every valid incoming link.

#### 3. HIGH: Bot Calls Uncontracted `/api/interview/complete/` Endpoint
- **Location:** [`screening/dmcore.py:110`](file:///D:/candidate_screening_vdo_final/candidate_screening_vdo_final/screening/dmcore.py#L110) & [`screening/views.py:892`](file:///D:/candidate_screening_vdo_final/candidate_screening_vdo_final/screening/views.py#L892)
- **Problem:** When the candidate completes the last question, the bot issues a POST to `{DMCORE_BASE_URL}/api/interview/complete/`.
- **Failure Impact:** This endpoint is **not in DMCore's contract**. If DMCore returns HTTP 404 or 405, the bot retries 3 times and then returns **HTTP 503** (`"Interview service returned HTTP 404"`) right at the final completion screen.

#### 4. HIGH: Session Endpoint Call Uses `GET` and Header Token
- **Location:** [`screening/dmcore.py:45-52`](file:///D:/candidate_screening_vdo_final/candidate_screening_vdo_final/screening/dmcore.py#L45-L52)
- **Problem:** The bot executes a `GET` request and passes the candidate token exclusively via the HTTP header `X-Interview-Token: <token>`.
- **Failure Impact:** If DMCore expects a `POST` request or expects `token` in the request body (`{"token": "..."}`) or URL query param (`?token=...`), DMCore will return 400 Bad Request or 401 Unauthorized, causing the bot to fail immediately on entry.

#### 5. HIGH: Strict Requirement for `{"success": true}` in DMCore Responses
- **Location:** [`screening/dmcore.py:103, 111`](file:///D:/candidate_screening_vdo_final/candidate_screening_vdo_final/screening/dmcore.py#L103)
- **Problem:** In `save_answer()`, the bot checks:
  ```python
  if not isinstance(result, dict) or result.get('success') is not True:
      raise DmcoreError('DMCore did not confirm saving the answer', kind='invalid_response')
  ```
- **Failure Impact:** If DMCore returns HTTP 200/201 with `{"status": "saved"}` or `{}` without a literal boolean `success: true`, the bot marks every save as failed, queues them into `unsaved_answers`, and aborts the interview with HTTP 503 at completion.

#### 6. MEDIUM: Hardcoded Localhost & Domain Assumptions
- **Location:** [`config/settings.py:53-62, 96-103`](file:///D:/candidate_screening_vdo_final/candidate_screening_vdo_final/config/settings.py#L53-L62)
- **Problem:**
  - `DATABASES['default']` hardcodes MySQL host `localhost:3306` with user `infoxtec_DBIEEE30ml23062026`.
  - `CSRF_TRUSTED_ORIGINS` hardcodes `http://127.0.0.1:8000`, `http://localhost:8000`, `https://website132.altostechnologies.in`.
- **Failure Impact:** If deployed on any other domain without updating `CSRF_TRUSTED_ORIGINS`, every browser POST (`/api/question/`, `/api/answer/`, `/api/complete/`) will fail with CSRF 403 (redirected to `/hr/login/`).

---

### 7.3 Leftover Code From Earlier Integrations
The codebase contains leftover artifacts from earlier attempts:
1. **`screening/matching.py` (95 lines):** Implements fuzzy keyword matching (`match_fields`, `load_catalog`, `_phrase_matches`, `FUZZY_CUTOFF = 0.80`) between DMCore field names/descriptions and video clips. This was used when DMCore sent arbitrary field names instead of numeric question IDs. It is currently unreferenced by `views.py`.
2. **`screening/question_keywords.json`:** A keyword catalog with synonym arrays (`requires_one_of`, `keywords`) for matching questions.
3. **`screening/dmcore.py:117-156` (`decode_interview_link`):** Validates a legacy payload shape (`{'candidate': {'name'}, 'questions': [{'field_name', 'description'}]}`) designed for `matching.py`.

---

## 8. TESTS AND LOGS

### 8.1 Existing Tests and How to Run Them
- **Test Files:**
  1. [`screening/test_dmcore.py`](file:///D:/candidate_screening_vdo_final/candidate_screening_vdo_final/screening/test_dmcore.py): Tests `load_session`, `save_answer`, `validate_configuration`, HTTP error handling (401/403/timeout/unreachable), answer retry, and 400 ignore behavior.
  2. [`screening/test_question_flow.py`](file:///D:/candidate_screening_vdo_final/candidate_screening_vdo_final/screening/test_question_flow.py): Tests question ordering, empty playlist fallback message, and fresher skip rules.
  3. [`screening/tests.py`](file:///D:/candidate_screening_vdo_final/candidate_screening_vdo_final/screening/tests.py): Tests input normalization, Indic translations, email parsing, and Sarvam routing.
- **How to Run Tests:**
  ```powershell
  # Run all DMCore integration tests with local SQLite settings:
  .\venv\Scripts\python.exe manage.py test screening.test_dmcore screening.test_question_flow --settings=config.settings_local

  # Run full screening test suite:
  .\venv\Scripts\python.exe manage.py test screening --settings=config.settings_local
  ```

### 8.2 Logging Destination
- Logs use standard Python logging: `logger = logging.getLogger(__name__)`.
- There is **no explicit `LOGGING` configuration dictionary** in `config/settings.py`.
- As a result, Django logs to standard `sys.stderr` / console (and the WSGI server error log, such as Passenger's error log in production).
- No log files are written to disk by default.

### 8.3 Health & Diagnostic Endpoints
- **Application Health Endpoint:** **NOT FOUND.** There is no `/health` or `/api/health` HTTP endpoint defined in `config/urls.py` or `screening/urls.py`.
- **CLI Diagnostic Script:** [`check_dmcore.py`](file:///D:/candidate_screening_vdo_final/candidate_screening_vdo_final/check_dmcore.py) in the project root:
  - Can be run from terminal: `python check_dmcore.py`.
  - Verifies reachability of `DMCORE_BASE_URL` and validates `DMCORE_API_KEY` authentication without logging secrets.
- **Other Utility Endpoints:**
  - `/.well-known/appspecific/com.chrome.devtools.json` (returns empty JSON `{}` to silence Chrome DevTools 404s).
  - `/demo/` (interactive demo flow enabled only when `DEBUG = True`).
