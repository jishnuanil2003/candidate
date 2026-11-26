/**
 * TalentBot Interview Controller v2
 * Robust CSRF handling — works even when browser cookies are blocked
 */

// ─── CSRF Token: 3-layer fallback ────────────────────────────────────────────
let _csrfCache = '';

async function getCSRF() {
  if (_csrfCache) return _csrfCache;

  // Layer 1: hidden {% csrf_token %} input injected by Django template
  const el = document.querySelector('[name=csrfmiddlewaretoken]');
  if (el && el.value) { _csrfCache = el.value; return _csrfCache; }

  // Layer 2: cookie (standard Django behaviour)
  const cookieMatch = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
  if (cookieMatch) { _csrfCache = decodeURIComponent(cookieMatch[1]); return _csrfCache; }

  // Layer 3: fetch from server (when cookies are blocked by browser/extension)
  try {
    const r = await fetch('/api/csrf/', { credentials: 'same-origin' });
    const d = await r.json();
    if (d.csrfToken) { _csrfCache = d.csrfToken; return _csrfCache; }
  } catch (e) { console.warn('CSRF fetch fallback failed', e); }

  console.error('Could not obtain CSRF token — form submissions will fail.');
  return '';
}

// ─── State ───────────────────────────────────────────────────────────────────
let currentQuestion = null;
let nextQuestionData = null;
let conditionalNextMap = null;
let answerQueue = [];
let isProcessingQueue = false;
let selectedOption = null;
let isLocked = false;
let selectedLanguage = document.getElementById('langSelect')?.value || new URLSearchParams(window.location.search).get('lang') || 'en';
let ttsEnabled = true;
let currentPlaybackId = 0;
let submissionSequence = 0;
let localizedEnglishOnlyError = "Please enter your response in English only.";

// ─── Language & Text-To-Speech Functions ──────────────────────────────────────
async function changeLanguage(lang) {
  if (currentQuestion && currentQuestion.number > 1) {
    alert("Language cannot be changed once the interview has started.");
    const selectEl = document.getElementById('langSelect');
    if (selectEl) selectEl.value = selectedLanguage;
    return;
  }
  selectedLanguage = lang;
  cancelTTS();
  const selectEl = document.getElementById('langSelect');
  if (selectEl) selectEl.value = lang;
  await fetchQuestion();
}

function toggleTTS() {
  ttsEnabled = !ttsEnabled;
  const btn = document.getElementById('soundToggleBtn');
  const label = document.getElementById('soundToggleLabel');
  const onIcon = document.getElementById('soundOnIcon');
  const offIcon = document.getElementById('soundOffIcon');
  
  if (ttsEnabled) {
    if (btn) btn.classList.remove('muted');
    if (label) label.textContent = "Voice On";
    if (onIcon) onIcon.style.display = "block";
    if (offIcon) offIcon.style.display = "none";
    if (currentQuestion && currentQuestion.text && selectedLanguage !== 'en' && videoEngine.state !== 'speaking') {
      speakText(cleanHtml(currentQuestion.text), selectedLanguage);
    }
  } else {
    if (btn) btn.classList.add('muted');
    if (label) label.textContent = "Voice Off";
    if (onIcon) onIcon.style.display = "none";
    if (offIcon) offIcon.style.display = "block";
    cancelTTS();
    if (selectedLanguage !== 'en' && videoEngine.state === 'speaking') {
      videoEngine._switchToIdle();
    }
  }
}

let currentAudio = null;

function cancelTTS() {
  if (currentAudio) {
    currentAudio.pause();
    currentAudio = null;
  }
  if (window.speechSynthesis) {
    window.speechSynthesis.cancel();
  }
}

function cleanHtml(html) {
  return String(html ?? '').replace(/<[^>]*>/g, '');
}

function escapeHTML(value) {
  return String(value ?? '').replace(/[&<>"']/g, char => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
  })[char]);
}

function speakText(text, lang) {
  if (!ttsEnabled) return;
  cancelTTS();
  
  const url = `/api/tts/?lang=${lang}&text=${encodeURIComponent(text)}`;
  currentAudio = new Audio(url);
  currentAudio.addEventListener('ended', () => {
    if (selectedLanguage !== 'en' && videoEngine.state === 'speaking') {
      videoEngine._switchToIdle();
    }
  });
  currentAudio.play().catch(e => console.warn("Audio playback failed", e));
}

function handleRepeat() {
  cancelTTS();
  if (!currentQuestion) return;
  const q = currentQuestion;
  const shouldMuteVideo = (selectedLanguage !== 'en' && q.video_is_fallback !== false);
  videoEngine.repeatQuestion(shouldMuteVideo);
  if (selectedLanguage !== 'en' && ttsEnabled) {
    setTimeout(() => {
      speakText(cleanHtml(q.text), selectedLanguage);
    }, 300);
  }
}

function localizeUI(ui) {
  if (ui && ui.english_only) {
    localizedEnglishOnlyError = ui.english_only;
  }
  const subText = document.getElementById('tbSubText');
  const overlayLabel = document.getElementById('soText');
  const ansLabel = document.querySelector('.iv-answer-label');
  const progLabel = document.querySelector('.iv-card-label');
  const repeatBtn = document.getElementById('repeatBtn');
  const tipsTitle = document.querySelector('.iv-tips-title');
  const tipsList = document.querySelector('.iv-tips-list');
  const botText = document.querySelector('.iv-bot-text');
  const csThankYou = document.getElementById('csThankYou');

  if (!ui || Object.keys(ui).length === 0) {
    if (subText) subText.textContent = "Conversational AI Interviewer";
    if (overlayLabel) overlayLabel.textContent = "Waiting for your response...";
    if (ansLabel) ansLabel.textContent = "Your Answer";
    if (progLabel) progLabel.textContent = "Interview Progress";
    if (repeatBtn) repeatBtn.title = "Repeat question";
    if (tipsTitle) tipsTitle.textContent = "💡 Tips";
    if (tipsList) {
      tipsList.innerHTML = `
        <li>Take your time and think before answering.</li>
        <li>You can repeat the question if you need to.</li>
        <li>Your responses help us understand you better.</li>
      `;
    }
    if (botText) {
      botText.innerHTML = `
        <p>I'm here to guide you through the interview.</p>
        <p>Just type your answer when you're ready.</p>
      `;
    }
    if (csThankYou) {
      csThankYou.textContent = "Thank you for completing your screening interview. Our team will review your responses and be in touch soon. Have a great day!";
    }
    return;
  }
  
  if (ui.sarah_speaking && document.getElementById('avStatusText')) {
    document.getElementById('avStatusText').textContent = ui.sarah_speaking;
  }
  if (ui.waiting_response && overlayLabel) {
    overlayLabel.textContent = ui.waiting_response;
  }
  if (ui.repeat_question && repeatBtn) {
    repeatBtn.title = ui.repeat_question;
  }
  if (ui.tips_title && tipsTitle) {
    tipsTitle.textContent = ui.tips_title;
  }
  if (ui.tips && ui.tips.length > 0 && tipsList) {
      tipsList.innerHTML = ui.tips.map(tip => `<li>${escapeHTML(tip)}</li>`).join('');
  }
  if (ui.guide_text && botText) {
    botText.innerHTML = `<p>${escapeHTML(ui.guide_text)}</p>`;
  }
  if (ui.thank_you && csThankYou) {
    csThankYou.textContent = ui.thank_you;
  }
}

if (window.speechSynthesis && window.speechSynthesis.onvoiceschanged !== undefined) {
  window.speechSynthesis.onvoiceschanged = () => {
    // Voices loaded successfully
  };
}

// ─── DOM refs ────────────────────────────────────────────────────────────────
const speakingOverlay = document.getElementById('speakingOverlay');
const questionEcho = document.getElementById('questionEcho');
const qeNum = document.getElementById('qeNum');
const qeText = document.getElementById('qeText');
const inputArea = document.getElementById('inputArea');
const inpOpts = document.getElementById('inpOpts');
const inpHint = document.getElementById('inpHint');
const inpError = document.getElementById('inpError');
const inpErrorText = document.getElementById('inpErrorText');
const inpText = document.getElementById('inpText');
const inpTextarea = document.getElementById('inpTextarea');
const waActionBtn = document.getElementById('waActionBtn');
const waRecording = document.getElementById('waRecording');
const micIcon = document.getElementById('micIcon');
const sendIcon = document.getElementById('sendIcon');
const avpFill = document.getElementById('avpFill');
const avpLabel = document.getElementById('avpLabel');
const rpStep = document.getElementById('rpStep');
const completionScreen = document.getElementById('completionScreen');
const csMeta = document.getElementById('csMeta');

function isEnglishOnly(text) {
  if (!text) return true;
  // Allow printable ASCII characters, smart punctuation, common currency symbols (Rupee, Pound, Euro)
  const englishRegex = /^[\sA-Za-z0-9!"#$%&'()*+,\-./:;<=>?@\[\\\]^_`{|}~\u2010-\u201f\u2026\u2022\u20B9\u20A8\xA3\u20AC]*$/;
  return englishRegex.test(text);
}

// ─── Voice Typing ─────────────────────────────────────────────────────────────
let isRecording = false;
let isTranscribing = false;
let mediaRecorder = null;
let audioChunks = [];
let audioStream = null;
let originalActionBtnHtml = '';

async function startRecording() {
  if (isRecording) return;
  
  try {
    audioChunks = [];
    audioStream = await navigator.mediaDevices.getUserMedia({ 
      audio: {
        echoCancellation: true,
        noiseSuppression: true,
        autoGainControl: true,
        channelCount: { ideal: 1 },
        sampleRate: { ideal: 16000 }
      } 
    });
    
    let options = {};
    if (MediaRecorder.isTypeSupported('audio/webm;codecs=opus')) {
      options = { 
        mimeType: 'audio/webm;codecs=opus',
        audioBitsPerSecond: 64000 // 64 kbps is ideal for speech clarity and fast uploads
      };
    }
    
    mediaRecorder = new MediaRecorder(audioStream, options);
    audioChunks = [];
    
    mediaRecorder.ondataavailable = e => {
      if (e.data.size > 0) audioChunks.push(e.data);
    };
    mediaRecorder.start();
  } catch(err) {
    console.warn("Could not start MediaRecorder", err);
    return alert("Microphone access denied. Please type your answer.");
  }

  isRecording = true;
  waActionBtn.classList.add('is-recording');
  waRecording.style.display = 'flex';
  micIcon.style.display = 'none';
  sendIcon.style.display = 'none';
}

function stopRecording() {
  if (!isRecording) return;
  isRecording = false;

  
  waActionBtn.classList.remove('is-recording');
  waRecording.style.display = 'none';
  
  // Process with Groq Whisper if available
  if (mediaRecorder && mediaRecorder.state !== 'inactive') {
    isTranscribing = true;
    waActionBtn.classList.add('is-send');
    micIcon.style.display = 'none';
    sendIcon.style.display = 'none';
    
    // Inject Spinner
    const tempSpinner = document.createElement('div');
    tempSpinner.id = 'tempSpinner';
    tempSpinner.className = 'spinner';
    tempSpinner.style.cssText = 'width: 20px; height: 20px; border: 2px solid rgba(255,255,255,0.3); border-radius: 50%; border-top-color: #fff; animation: spin 1s ease-in-out infinite;';
    waActionBtn.appendChild(tempSpinner);
    
    mediaRecorder.onstop = async () => {
      const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
      const formData = new FormData();
      formData.append('audio', audioBlob, 'recording.webm');
      formData.append('language', selectedLanguage);
      if (currentQuestion && currentQuestion.id) {
        formData.append('question_id', currentQuestion.id);
      }
      
      try {
        const response = await fetch('/api/transcribe/', {
          method: 'POST',
          headers: { 'X-CSRFToken': await getCSRF() },
          body: formData
        });
        const data = await response.json();
        
        if (response.ok) {
          if (data.text && data.text.trim()) {
            const activeInput = currentQuestion?.type === 'textarea' ? inpTextarea : inpText;
            activeInput.value = data.text.trim();
            updateActionIcon();
          } else {
            showError("No speech detected. Please speak clearly or type your response.");
          }
        } else {
          console.warn("Transcription error", data ? data.error : "Unknown error");
          showError("Speech recognition is temporarily unavailable. Please type your response.");
        }
      } catch (err) {
        console.error("Transcription failed", err);
        showError("Speech recognition is temporarily unavailable. Please type your response.");
      } finally {
        isTranscribing = false;
        const spinner = document.getElementById('tempSpinner');
        if (spinner) spinner.remove();
        updateActionIcon();
        if (audioStream) audioStream.getTracks().forEach(track => track.stop());
      }
    };
    mediaRecorder.stop();
  } else {
    updateActionIcon();
  }
}

function updateActionIcon() {
  if (isRecording || isTranscribing) return;
  const activeInput = currentQuestion?.type === 'textarea' ? inpTextarea : inpText;
  
  let hasText = false;
  if (selectedOption !== null && selectedOption !== '__custom__') {
    hasText = true;
  } else {
    hasText = activeInput.value.trim().length > 0 || currentQuestion?.optional;
  }
  
  if (hasText) {
    waActionBtn.classList.add('is-send');
    micIcon.style.display = 'none';
    sendIcon.style.display = 'block';
  } else {
    waActionBtn.classList.remove('is-send');
    micIcon.style.display = 'block';
    sendIcon.style.display = 'none';
  }
}

function handleWaAction() {
  if (isLocked || isTranscribing) return;
  if (isRecording) { stopRecording(); return; }
  
  const activeInput = currentQuestion?.type === 'textarea' ? inpTextarea : inpText;
  
  let hasText = false;
  if (selectedOption !== null && selectedOption !== '__custom__') {
    hasText = true;
  } else {
    hasText = activeInput.value.trim().length > 0 || currentQuestion?.optional;
  }
  
  if (hasText) handleSubmit();
  else startRecording();
}

// ─── Question Hints & Month-Year Validator ────────────────────────────────────
const QUESTION_HINTS = {
  1: "Enter your full name, for example: Anil Kumar.",
  2: "Enter a valid email address, for example: name@example.com.",
  3: "Enter a 10-digit mobile number, for example: 9876543210.",
  4: "Enter the role you are applying for, for example: Digital Marketing Executive.",
  5: "Enter your highest qualification, for example: B.Tech, MCA or MBA.",
  6: "Enter your field of study, for example: Computer Science.",
  7: "Enter your college name.",
  8: "Enter the 4-digit year, for example: 2024.",
  9: "Enter your CGPA or percentage, for example: 8.2 or 78%.",
  10: "Select or enter whether you have experience, for example: Yes, I have experience or No, I am a fresher.",
  11: "Enter your last company name, for example: Infosys or TCS.",
  12: "Enter your previous job title, for example: Software Engineer or Analyst.",
  13: "Select your total experience, for example: 1-2 years.",
  14: "List your key skills separated by commas, for example: SEO, Google Ads, Excel.",
  15: "Select your notice period, for example: Immediate joiner, 1 month or 2 months.",
  16: "Select your expected annual salary range, for example: 3-5 LPA or 5-8 LPA.",
  17: "Enter your LinkedIn profile link (e.g. https://linkedin.com/in/yourname), or leave blank to skip.",
  18: "Write 2 or 3 sentences about why you are a good fit.",
  19: "Tell us where you heard about this job, for example: LinkedIn, Naukri or a friend.",
  20: "Enter your current city, for example: Kochi.",
  21: "Select or enter Yes or No, for example: Yes.",
  22: "Enter the month and year, for example: June 2025 or 06/2025.",
  23: "Enter the month and year, or Ongoing, for example: August 2025 or 08/2025.",
  24: "Enter your internship domain or project topic, for example: Web Development with Django."
};

const DATE_MIN_YEAR = 2000;

function parseMonthYearClient(val) {
  if (!val || typeof val !== 'string') return null;
  const str = val.trim().toLowerCase();
  if (!str) return null;

  const cleaned = str.replace(/[,/\-]/g, ' ');
  const tokens = cleaned.split(/\s+/).filter(Boolean);
  if (tokens.length !== 2) return null;

  const currentYear = new Date().getFullYear();
  const maxYear = currentYear + 1;

  const monthNames = {
    'january': 1, 'jan': 1, 'february': 2, 'feb': 2, 'march': 3, 'mar': 3,
    'april': 4, 'apr': 4, 'may': 5, 'june': 6, 'jun': 6, 'july': 7, 'jul': 7,
    'august': 8, 'aug': 8, 'september': 9, 'sep': 9, 'sept': 9, 'october': 10, 'oct': 10,
    'november': 11, 'nov': 11, 'december': 12, 'dec': 12,
    'जनवरी': 1, 'फ़रवरी': 2, 'फरवरी': 2, 'मार्च': 3, 'अप्रैल': 4, 'मई': 5, 'जून': 6,
    'जुलाई': 7, 'अगस्त': 8, 'सितंबर': 9, 'सितम्बर': 9, 'अक्टूबर': 10, 'अक्तूबर': 10,
    'नवंबर': 11, 'नवम्बर': 11, 'दिसंबर': 12, 'दिसम्बर': 12,
    'ജനുവരി': 1, 'ഫെബ്രുവരി': 2, 'മാർച്ച്': 3, 'ഏപ്രിൽ': 4, 'മെയ്': 5, 'ജൂൺ': 6,
    'ജൂലൈ': 7, 'ഓഗസ്റ്റ്': 8, 'സെപ്റ്റംബർ': 9, 'ഒക്ടോബർ': 10, 'നവംബർ': 11, 'ഡിസംബർ': 12,
    'ஜனவரி': 1, 'பிப்ரவரி': 2, 'மார்ச்': 3, 'ஏப்ரல்': 4, 'மே': 5, 'ஜூன்': 6,
    'ஜூலை': 7, 'ஆகஸ்ட்': 8, 'செப்டம்பர்': 9, 'அக்டோபர்': 10, 'நவம்பர்': 11, 'டிசம்பர்': 12,
    'జనవరి': 1, 'ఫిబ్రవరి': 2, 'మార్చి': 3, 'ఏప్రిల్': 4, 'మే': 5, 'జూన్': 6,
    'జూలై': 7, 'ఆగస్టు': 8, 'సెప్టెంబర్': 9, 'అక్టోబర్': 10, 'నవంబర్': 11, 'డిసెంబర్': 12
  };

  function asYear(t) {
    if (/^\d{4}$/.test(t)) {
      const y = parseInt(t, 10);
      if (y >= DATE_MIN_YEAR && y <= maxYear) return y;
    }
    return null;
  }

  function asMonth(t) {
    if (monthNames[t]) return monthNames[t];
    if (/^(0?[1-9]|1[0-2])$/.test(t)) return parseInt(t, 10);
    return null;
  }

  const [t1, t2] = tokens;
  const m1 = asMonth(t1), y2 = asYear(t2);
  if (m1 && y2) return { month: m1, year: y2 };

  const y1 = asYear(t1), m2 = asMonth(t2);
  if (y1 && m2) return { month: m2, year: y1 };

  return null;
}

function showHintBox(hintText) {
  const box = document.getElementById('ivHintBox');
  const span = document.getElementById('ivHintBoxText');
  if (!box || !span) return;
  const msg = hintText || "Please enter a valid input.";
  span.textContent = "Invalid input. " + msg;
  box.style.display = 'flex';
  box.style.opacity = '1';
}

function hideHintBox() {
  const box = document.getElementById('ivHintBox');
  if (!box) return;
  box.style.opacity = '0';
  setTimeout(() => {
    if (box.style.opacity === '0') box.style.display = 'none';
  }, 250);
}

if (inpText) {
  inpText.addEventListener('input', () => {
    hideHintBox();
    hideError();
    updateActionIcon();
  });
}
if (inpTextarea) {
  inpTextarea.addEventListener('input', () => {
    hideHintBox();
    hideError();
    updateActionIcon();
  });
}

// Fallback delay when video has no duration (placeholder files)
const FALLBACK_DELAY_MS = 0;

// ─── INIT ─────────────────────────────────────────────────────────────────────
async function init() {
  const greeting = document.getElementById('tbSubText');
  const candidateName = greeting?.dataset.candidateName || '';
  if (candidateName) greeting.textContent = `Hello, ${candidateName}. Your interview is ready.`;
  // Warm up CSRF before anything else
  await getCSRF();

  if (rpStep && rpStep.textContent && rpStep.textContent.includes('/')) {
    const parts = rpStep.textContent.split('/');
    const n = parseInt(parts[0], 10);
    const t = parseInt(parts[1], 10);
    if (!isNaN(n) && !isNaN(t) && t > 0) {
      updateProgressUI(n, t);
    }
  }

  setSpeakingOverlay(true, 'Starting your interview...');
  lockInput(true);
  await sleep(400);
  videoEngine.ready();
  await sleep(1000); // A little gap before the first video
  await fetchQuestion();
}

// ─── FETCH QUESTION ──────────────────────────────────────────────────────────
async function fetchQuestion() {
  let data;
  try {
    const res = await api('/api/question/', { lang: selectedLanguage });
    data = await res.json();
  } catch (e) {
    console.error('Failed to fetch question:', e);
    setSpeakingOverlay(false);
    showError('Connection error. Please refresh the page.');
    return;
  }

  if (data.done) {
    localizeUI(data.ui);
    const langSelectEl = document.getElementById('langSelect');
    if (langSelectEl) {
      langSelectEl.value = selectedLanguage;
      if (typeof currentQuestion !== 'undefined' && currentQuestion && currentQuestion.number > 1) {
        langSelectEl.disabled = true;
        langSelectEl.title = "Language is locked during the interview";
      }
    }
    await handleCompletion(data.outro_video || data.completion_video, data.ui);
    return;
  }

  await displayQuestion(data);
}

// ─── DISPLAY QUESTION ────────────────────────────────────────────────────────
async function displayQuestion(data) {
  const playbackId = ++currentPlaybackId;

  const q = data.question;
  if (!q) return;

  if (data.debug) {
    console.log(`[DEBUG] Language: ${data.debug.language} | Question: ${data.debug.question_id} | Resolved File: ${data.debug.resolved_file} | Absolute Path: ${data.debug.absolute_path}`);
  }

  currentQuestion = q;
  selectedOption = null;
  hideHintBox();
  hideError();

  if (data.next_question) {
    nextQuestionData = data.next_question;
  }
  if (data.conditional_next) {
    conditionalNextMap = data.conditional_next;
  }

  // Preload only the NEXT question's video into the hidden preload element
  if (nextQuestionData && nextQuestionData.question_video) {
    videoEngine.preloadNext(nextQuestionData.question_video);
  }
  // Preload blink/idle and outro at start/as available
  if (data.idle_video || data.outro_video) {
    videoEngine.preloadGlobalAssets(data.idle_video, data.outro_video);
  }

  if (data.ui) localizeUI(data.ui);
  updateProgressUI(q.number, q.total, data.progress);
  setSpeakingOverlay(true, 'Sarah is speaking...');
  lockInput(true);

  qeText.textContent = cleanHtml(q.text);

  // Start preloading regional TTS in the background immediately
  let preloadedAudio = null;
  if (selectedLanguage !== 'en' && ttsEnabled) {
    const url = `/api/tts/?lang=${selectedLanguage}&text=${encodeURIComponent(cleanHtml(q.text))}`;
    preloadedAudio = new Audio(url);
    preloadedAudio.load();
  }

  if (playbackId !== currentPlaybackId) return;

  const shouldMuteVideo = (selectedLanguage !== 'en');

  videoEngine.playQuestion(q.question_video, q.idle_video, shouldMuteVideo);

  if (selectedLanguage !== 'en' && ttsEnabled) {
    await sleep(300); // 300ms delay to prevent resource collision and improve mouth-sync realism
    if (playbackId !== currentPlaybackId) return;

    if (preloadedAudio) {
      cancelTTS();
      currentAudio = preloadedAudio;
      currentAudio.addEventListener('ended', () => {
        if (selectedLanguage !== 'en' && videoEngine.state === 'speaking') {
          videoEngine._switchToIdle();
        }
      });
      currentAudio.play().catch(e => console.warn("Audio playback failed", e));
    } else {
      speakText(cleanHtml(q.text), selectedLanguage);
    }
  } else {
    cancelTTS();
  }

  if (selectedLanguage !== 'en' && ttsEnabled) {
    await waitForAudio(currentAudio);
  } else {
    const waitMs = await getVideoWaitTime(q.question_video);
    if (videoEngine._fallbackAudio) await waitForAudio(videoEngine._fallbackAudio);
    else await sleep(waitMs);
  }
  if (playbackId !== currentPlaybackId) return;

  setSpeakingOverlay(false);
  renderInput(q);
  lockInput(false);
}

// ─── VIDEO WAIT ───────────────────────────────────────────────────────────────
async function getVideoWaitTime(src) {
  if (!src) return 0;
  try {
    const duration = await Promise.race([
      getVideoDuration(src),
      sleep(4000).then(() => 0)
    ]);
    if (!duration || duration <= 0 || isNaN(duration)) return FALLBACK_DELAY_MS;
    return (duration + 0.3) * 1000;
  } catch (e) { return FALLBACK_DELAY_MS; }
}

// ─── RENDER INPUT ─────────────────────────────────────────────────────────────
function renderInput(q) {
  inpText.style.display = 'none';
  inpTextarea.style.display = 'none';
  inpOpts.style.display = 'none';
  inpOpts.innerHTML = '';
  inpHint.textContent = q.hint || '';
  hideError();

  // Remove old custom input if present
  const oldCustom = document.getElementById('customRoleWrap');
  if (oldCustom) oldCustom.remove();

  if (q.type === 'options' || q.type === 'options_or_text') {
    inpOpts.style.display = 'flex';

    q.options.forEach(opt => {
      const btn = document.createElement('button');
      btn.className = 'opt-pill';
      btn.textContent = opt;
      btn.onclick = () => {
        document.querySelectorAll('.opt-pill').forEach(b => b.classList.remove('selected'));
        btn.classList.add('selected');
        selectedOption = opt;
        // Hide inpText since it's not custom
        inpText.style.display = 'none';
        inpText.value = '';
        hideError();
        updateActionIcon();

        // Branch-aware preloading on option click
        if (conditionalNextMap) {
          if (q.id === 10) {
            const isFresher = opt.toLowerCase().includes('fresher') || opt.toLowerCase().includes('no');
            const target = isFresher ? conditionalNextMap['fresher'] : conditionalNextMap['experienced'];
            if (target && target.question_video) {
              nextQuestionData = target;
              videoEngine.preloadNext(target.question_video);
            }
          } else if (q.id === 21) {
            const isNo = opt.toLowerCase().startsWith('no');
            const target = isNo ? conditionalNextMap['no'] : conditionalNextMap['yes'];
            if (target) {
              nextQuestionData = target;
              if (target.outro_video) videoEngine.preloadNext(target.outro_video);
              else if (target.question_video) videoEngine.preloadNext(target.question_video);
            }
          }
        }
      };
      inpOpts.appendChild(btn);
    });

    // "Other" pill + freetext input for options_or_text
    if (q.type === 'options_or_text') {
      const otherBtn = document.createElement('button');
      otherBtn.className = 'opt-pill other-pill';
      otherBtn.textContent = q.other_label || 'Other — type below';

      otherBtn.onclick = () => {
        document.querySelectorAll('.opt-pill').forEach(b => b.classList.remove('selected'));
        otherBtn.classList.add('selected');
        selectedOption = '__custom__';
        // Reuse main input bar so voice typing works
        inpText.style.display = 'block';
        inpText.placeholder = q.placeholder || 'Type your answer...';
        setTimeout(() => inpText.focus(), 50);
        hideError();
        updateActionIcon();
      };

      inpOpts.appendChild(otherBtn);
    }

  } else if (q.type === 'textarea') {
    inpTextarea.style.display = 'block';
    inpTextarea.value = '';
    inpTextarea.placeholder = q.placeholder || '';
    setTimeout(() => inpTextarea.focus(), 100);

  } else {
    inpText.style.display = 'block';
    inpText.value = '';
    const isDateQ = (q.id === 22 || q.id === 23 || q.key === 'internship_start_date' || q.key === 'internship_end_date');
    if (isDateQ) {
      const hintStr = q.hint || QUESTION_HINTS[q.id] || (q.id === 22 ? 'Enter the month and year, for example: June 2025 or 06/2025.' : 'Enter the month and year, or Ongoing, for example: August 2025 or 08/2025.');
      inpHint.textContent = hintStr;
      inpHint.style.display = 'block';
      inpText.placeholder = hintStr;
    } else {
      inpText.placeholder = q.placeholder || '';
    }
    inpText.type = q.type === 'email' ? 'email' : 'text';
    setTimeout(() => inpText.focus(), 100);
  }
  updateActionIcon();
}

// ─── ANSWER QUEUE ─────────────────────────────────────────────────────────────
async function processAnswerQueue() {
  if (isProcessingQueue) return;
  isProcessingQueue = true;

  while (true) {
    const item = answerQueue.find(i => i.status === 'pending');
    if (!item) break;

    item.status = 'sending';
    const statusText = document.getElementById('soText');
    if (statusText) statusText.textContent = 'Saving your answer...';

    let data;
    try {
      const res = await api('/api/answer/', {
        question_id: item.question.id,
        value: item.value,
        lang: item.lang
      });
      data = await res.json();
    } catch (err) {
      console.error('Submit error:', err);
      data = { valid: false, network_error: true, error: 'Network error. Please check your connection and try again.' };
    }

    // Ignore late or out-of-order responses: only apply response if it belongs to the latest submission for this question
    if (item.id !== submissionSequence || (currentQuestion && item.questionId !== currentQuestion.id && !item.optimisticTarget)) {
      console.warn('Ignoring stale or out-of-order response for submission', item.id);
      const idx = answerQueue.indexOf(item);
      if (idx !== -1) answerQueue.splice(idx, 1);
      continue;
    }

    if (data.valid) {
      item.status = 'confirmed';
      item.responseData = data;
      if (statusText) statusText.textContent = data.done ? 'Interview finished.' : 'Answer saved.';
      if (data.ui) localizeUI(data.ui);
      if (data.question) {
        updateProgressUI(data.question.number, data.question.total, data.progress);
      } else if (data.progress !== undefined && data.progress !== null) {
        updateProgressUI(null, null, data.progress);
      }
      if (data.next_question) {
        nextQuestionData = data.next_question;
        if (nextQuestionData.question_video) {
          videoEngine.preloadNext(nextQuestionData.question_video);
        }
      }
      if (data.conditional_next) {
        conditionalNextMap = data.conditional_next;
      }

      // If optimistic advancement was done:
      if (item.optimisticTarget) {
        const idx = answerQueue.indexOf(item);
        if (idx !== -1) answerQueue.splice(idx, 1);
        // If client and server disagree about the current question, the server wins
        if (data.question && currentQuestion && data.question.id !== currentQuestion.id) {
          console.warn('Client-server mismatch detected on advance. Server wins.');
          await displayQuestion(data);
        }
      }
    } else {
      if (data.error === 'Question mismatch.' || (typeof data.error === 'string' && data.error.includes('mismatch'))) {
        console.warn('Question mismatch detected. Resyncing question from server...');
        const idx = answerQueue.indexOf(item);
        if (idx !== -1) answerQueue.splice(idx, 1);
        isProcessingQueue = false;
        isLocked = false;
        isSubmitting = false;
        await fetchQuestion();
        return;
      }
      item.errorData = data;
      isProcessingQueue = false;
      await handleAnswerFailure(item);
      item.status = 'failed';
      return;
    }
  }

  isProcessingQueue = false;
}

async function handleAnswerFailure(item) {
  currentPlaybackId++;
  cancelTTS();
  if (typeof videoEngine !== 'undefined' && videoEngine.cancelError) {
    videoEngine.cancelError();
  }

  const answeringQuestion = item.question;
  const data = item.errorData || {};

  const idx = answerQueue.indexOf(item);
  if (idx !== -1) answerQueue.splice(idx, 1);
  isProcessingQueue = false;

  // Reset optimistic targets
  nextQuestionData = null;
  conditionalNextMap = null;

  const statusText = document.getElementById('soText');
  if (statusText) statusText.textContent = data.network_error ? 'Connection error.' : 'Invalid answer.';

  if (data.skipped) {
    hideHintBox();
    showError(data.error_text || data.error || 'Question skipped.');
    updateProgressUI(data.current_number, data.total, data.progress);
    if (data.done) {
      localizeUI(data.ui);
      await handleCompletion(data.outro_video || data.completion_video, data.ui);
      return;
    }
    isLocked = false;
    isSubmitting = false;
    await fetchQuestion();
    return;
  }

  // 1. ROLLBACK OPTIMISTIC TRANSITION: safely pause active playback
  videoEngine.pause();

  // 2. Restore CURRENT question (number, text, options)
  currentQuestion = answeringQuestion;
  selectedOption = null;
  updateProgressUI(answeringQuestion.number, answeringQuestion.total, data.progress);
  const qeText = document.getElementById('qeText');
  if (qeText) qeText.innerHTML = cleanHtml(answeringQuestion.text);

  // 3. Clear input and re-render current question input
  renderInput(answeringQuestion);
  if (inpText) inpText.value = '';
  if (inpTextarea) inpTextarea.value = '';
  updateActionIcon();

  const errVideo = data.error_video_url || data.error_video;
  const qHint = data.hint || answeringQuestion.hint || QUESTION_HINTS[answeringQuestion.id] || 'Please enter a valid response.';

  // Show the hint box only for the 6 strictly validated questions on invalid reason
  const STRICTLY_VALIDATED_QIDS = [2, 3, 8, 13, 22, 23];
  if (data.reason === 'invalid' && STRICTLY_VALIDATED_QIDS.includes(answeringQuestion.id)) {
    showHintBox(qHint);
  } else {
    hideHintBox();
  }

  try {
    if (errVideo) {
      const shouldMuteVideo = (selectedLanguage !== 'en');
      // videoEngine.playError returns a Promise resolving on ended, switch to idle, error, or (duration + 2s)
      await videoEngine.playError(errVideo, data.idle_video, shouldMuteVideo);

      if (selectedLanguage !== 'en' && ttsEnabled) {
        speakText(cleanHtml(data.error_text || data.error || qHint), selectedLanguage);
        await waitForAudio(currentAudio);
      }
    } else {
      // If invalid_input.mp4 is missing for candidate's language:
      // Do not fall back to per-field video and do not hang: show hint box text and continue.
      if (selectedLanguage !== 'en' && ttsEnabled) {
        speakText(cleanHtml(data.error_text || data.error || qHint), selectedLanguage);
        await waitForAudio(currentAudio);
      } else {
        await sleep(400);
      }
    }
  } catch (err) {
    console.warn('Error during invalid answer flow:', err);
  } finally {
    // Return to waiting state (blink/idle loop)
    if (typeof videoEngine !== 'undefined' && videoEngine.cancelError) {
      videoEngine.cancelError();
    }
    videoEngine._switchToIdle();

    // Re-enable input and Send button immediately
    lockInput(false);
    isLocked = false;
    isSubmitting = false;

    // Focus input
    if (inpText && inpText.style.display !== 'none') {
      inpText.focus();
    } else if (inpTextarea && inpTextarea.style.display !== 'none') {
      inpTextarea.focus();
    }
  }
}

let isSubmitting = false;

// ─── SUBMIT ───────────────────────────────────────────────────────────────────
async function handleSubmit() {
  if (isLocked || isSubmitting || !currentQuestion) return;

  let value = '';
  const qtype = currentQuestion.type;

  if (qtype === 'options' || qtype === 'options_or_text') {
    if (selectedOption === '__custom__') {
      value = inpText.value.trim();
    } else {
      value = selectedOption || '';
    }
  } else if (qtype === 'textarea') {
    value = inpTextarea.value.trim();
  } else {
    value = inpText.value.trim();
  }

  // Client-side English-only validation for typed inputs (strictly validated questions only)
  const STRICTLY_VALIDATED_QIDS = [2, 3, 8, 13, 22, 23];
  if (STRICTLY_VALIDATED_QIDS.includes(currentQuestion?.id)) {
    const isTyped = (qtype !== 'options' && qtype !== 'options_or_text') || (qtype === 'options_or_text' && selectedOption === '__custom__');
    if (isTyped && value && !isEnglishOnly(value)) {
      showError(localizedEnglishOnlyError);
      lockInput(false);
      isLocked = false;
      isSubmitting = false;
      return;
    }
  }

  // Check required / empty
  if (!value && !currentQuestion.optional) {
    showError('Please provide an answer.');
    lockInput(false);
    isLocked = false;
    isSubmitting = false;
    return;
  }

  if (isRecording) stopRecording();
  isSubmitting = true;
  isLocked = true;
  lockInput(true);
  hideError();

  const answeringQuestion = currentQuestion;

  // Client-side date validation check for internship date questions (22, 23)
  const isDateQ = (answeringQuestion.id === 22 || answeringQuestion.id === 23 ||
                   answeringQuestion.key === 'internship_start_date' || answeringQuestion.key === 'internship_end_date');
  let isClientInvalidDate = false;
  if (isDateQ && value) {
    if (answeringQuestion.id === 23 || answeringQuestion.key === 'internship_end_date') {
      const isOngoing = ['ongoing', 'still going on', 'present', 'currently', 'continuing', 'current', 'till now'].some(kw => value.toLowerCase().includes(kw)) ||
                        ['തുടരുന്നു', 'चल रहा है', 'தொடர்கிறது', 'కొనసాగుతోంది'].some(kw => value.includes(kw));
      if (!isOngoing && !parseMonthYearClient(value)) {
        isClientInvalidDate = true;
      }
    } else {
      if (!parseMonthYearClient(value)) {
        isClientInvalidDate = true;
      }
    }
  }

  // Queue answer and send in background in order
  const subId = ++submissionSequence;
  const queueItem = {
    id: subId,
    questionId: answeringQuestion.id,
    question: answeringQuestion,
    value: value,
    lang: selectedLanguage,
    status: 'pending',
    errorData: null,
    responseData: null,
    optimisticTarget: null
  };
  answerQueue.push(queueItem);

  // Trigger background queue processing without awaiting
  processAnswerQueue();

  // If client-side date validation failed, do not advance optimistically to next question
  let targetNext = isClientInvalidDate ? null : nextQuestionData;
  if (conditionalNextMap) {
    if (answeringQuestion.id === 10) {
      const isFresher = (selectedOption && (selectedOption.toLowerCase().includes('fresher') || selectedOption.toLowerCase().includes('no'))) ||
                        (value && (value.toLowerCase().includes('fresher') || value.toLowerCase().includes('no')));
      targetNext = isFresher ? conditionalNextMap['fresher'] : conditionalNextMap['experienced'];
    } else if (answeringQuestion.id === 21) {
      const isNo = (selectedOption && selectedOption.toLowerCase().startsWith('no')) ||
                   (value && value.toLowerCase().startsWith('no'));
      targetNext = isNo ? conditionalNextMap['no'] : conditionalNextMap['yes'];
    }
  }

  // Play next question IMMEDIATELY as answer is accepted locally
  if (targetNext) {
    queueItem.optimisticTarget = targetNext;
    if (targetNext.done) {
      await handleCompletion(targetNext.outro_video, null);
      return;
    }
    isLocked = false;
    isSubmitting = false;
    await displayQuestion({
      question: targetNext,
      next_question: null,
      conditional_next: null,
      ui: null,
      progress: null,
      idle_video: targetNext.idle_video,
      outro_video: null
    });
  } else {
    // If targetNext not yet computed or reset after rejection, wait for this answer to be processed
    try {
      while (queueItem.status === 'pending' || queueItem.status === 'sending') {
        await sleep(30);
      }
      if (queueItem.status === 'failed') {
        return;
      }
      const data = queueItem.responseData;
      const idx = answerQueue.indexOf(queueItem);
      if (idx !== -1) answerQueue.splice(idx, 1);

      if (!data || !data.valid) {
        // Anything other than a clean accept: re-sync with server
        await fetchQuestion();
      } else if (data.done) {
        if (data.ui) localizeUI(data.ui);
        await handleCompletion(data.outro_video || data.completion_video, data.ui);
      } else if (data.question) {
        await displayQuestion(data);
      } else {
        await fetchQuestion();
      }
    } catch (advanceErr) {
      console.error('Error during advance sequence:', advanceErr);
      await fetchQuestion();
    } finally {
      isLocked = false;
      isSubmitting = false;
    }
  }
}

let completionHandled = false;

// ─── COMPLETION ───────────────────────────────────────────────────────────────
async function handleCompletion(outroVideoSrc, ui) {
  if (completionHandled) return;
  completionHandled = true;
  currentPlaybackId++;
  cancelTTS();
  lockInput(true);
  if (questionEcho) questionEcho.style.display = 'none';
  if (inputArea) inputArea.style.display = 'none';
  if (currentQTotal > 0) {
    updateProgressUI(currentQTotal, currentQTotal, 100);
  } else {
    setProgress(100);
  }

  // Block "complete" until every queued answer has been confirmed:
  const completePromise = (async () => {
    while (answerQueue.some(i => i.status === 'pending' || i.status === 'sending')) {
      await sleep(100);
    }
    if (answerQueue.some(i => i.status === 'failed')) {
      return { success: false, error: 'Could not save all interview answers.' };
    }
    try {
      const res = await api('/api/complete/', {});
      return await res.json();
    } catch (e) {
      console.error('Completion error:', e);
      return { success: false, error: 'Connection error' };
    }
  })();

  if (outroVideoSrc) {
    // Play the chosen language's outro.mp4 once, with sound, on the final screen
    videoEngine.playQuestion(outroVideoSrc, null, false);

    const waitMs = await getVideoWaitTime(outroVideoSrc);
    await new Promise(resolve => {
      let finished = false;
      const onEnd = () => {
        if (!finished) {
          finished = true;
          videoEngine.elQuestion.removeEventListener('ended', onEnd);
          resolve();
        }
      };
      videoEngine.elQuestion.addEventListener('ended', onEnd, { once: true });
      setTimeout(onEnd, Math.max(waitMs, 1000));
    });
  } else {
    // If the chosen language has no outro.mp4: play NO video, show thank-you text, log warning
    console.warn(`No outro video found for language ${selectedLanguage}; showing thank-you text only.`);
  }

  videoEngine.stopAll();
  setSpeakingOverlay(false);

  // Wait for background completion call (which waited for all queued answers to be confirmed)
  let data = {};
  try {
    data = await completePromise;
  } catch (e) {
    console.error('Completion error:', e);
  }

  if (data && data.success) {
    csMeta.replaceChildren();
    if (data.application_id !== undefined) {
      const row = document.createElement('div');
      row.className = 'cs-meta-row';
      const label = document.createElement('span');
      label.textContent = 'Application ID';
      const value = document.createElement('strong');
      value.textContent = `#${data.application_id}`;
      row.append(label, value);
      csMeta.appendChild(row);
    }
    const statusRow = document.createElement('div');
    statusRow.className = 'cs-meta-row';
    const statusLabel = document.createElement('span');
    statusLabel.textContent = 'Status';
    const statusValue = document.createElement('strong');
    statusValue.style.color = 'var(--green)';
    statusValue.textContent = 'Submitted ✓';
    statusRow.append(statusLabel, statusValue);
    csMeta.appendChild(statusRow);

    if (ui && ui.thank_you) {
      const csThankYou = document.getElementById('csThankYou');
      if (csThankYou) csThankYou.textContent = ui.thank_you;
    }

    completionScreen.style.display = 'flex';
  } else {
    // If completion fails after its retries, show the existing error message after the outro
    completionHandled = false;
    if (inputArea) inputArea.style.display = 'block';
    showError((data && data.error) || 'Failed to submit interview. Please try again or contact the recruiter.');
    lockInput(false);
  }
}

// ─── HELPERS ──────────────────────────────────────────────────────────────────
let currentQNumber = 1;
let currentQTotal = 0;

function updateProgressUI(qNum, qTotal, pct) {
  try {
    if (qNum !== undefined && qNum !== null && !isNaN(Number(qNum)) && Number(qNum) > 0) {
      currentQNumber = Number(qNum);
    }
    if (qTotal !== undefined && qTotal !== null && !isNaN(Number(qTotal)) && Number(qTotal) > 0) {
      currentQTotal = Number(qTotal);
    }

    if (currentQTotal > 0) {
      const num = Math.min(currentQNumber, currentQTotal);
      const total = currentQTotal;
      const formattedStep = `${num}/${total}`;
      const ariaLabelText = `Question ${num} of ${total}`;

      if (rpStep) {
        rpStep.textContent = formattedStep;
        if (rpStep.setAttribute) rpStep.setAttribute('aria-label', ariaLabelText);
      }
      if (avpLabel) {
        avpLabel.textContent = ariaLabelText;
        if (avpLabel.setAttribute) avpLabel.setAttribute('aria-label', ariaLabelText);
      }
      if (qeNum) {
        qeNum.textContent = ariaLabelText;
      }

      let fillPct = pct;
      if (fillPct === undefined || fillPct === null || isNaN(Number(fillPct))) {
        fillPct = Math.min(100, Math.round(((num - 1) / total) * 100));
      }
      if (avpFill) {
        avpFill.style.width = fillPct + '%';
      }
    } else if (pct !== undefined && pct !== null && !isNaN(Number(pct))) {
      if (avpFill) {
        avpFill.style.width = pct + '%';
      }
    }
  } catch (err) {
    console.error('Error updating progress UI:', err);
  } finally {
    // try/finally ensures no preceding or internal exception leaves callers stalled
  }
}

function setProgress(pct, qNum, qTotal) {
  updateProgressUI(qNum, qTotal, pct);
}

function setSpeakingOverlay(visible, text) {
  const soText = document.getElementById('soText');
  if (soText && text) soText.textContent = text;
  speakingOverlay.classList.toggle('hidden', !visible);
}

function lockInput(locked) {
  if (waActionBtn) waActionBtn.disabled = locked;
  if (inpText) inpText.disabled = locked;
  if (inpTextarea) inpTextarea.disabled = locked;
  document.querySelectorAll('.opt-pill').forEach(p => p.disabled = locked);
  const repeatBtn = document.getElementById('repeatBtn');
  if (repeatBtn) repeatBtn.disabled = locked;
}

function showError(msg) {
  inpErrorText.textContent = msg;
  inpError.style.display = 'flex';
}

function hideError() {
  inpError.style.display = 'none';
}

async function getVideoDuration(src) {
  return new Promise((resolve, reject) => {
    const cached = videoEngine._preloaded[src];
    if (cached && cached.duration && !isNaN(cached.duration) && cached.duration > 0) {
      return resolve(cached.duration);
    }
    const v = document.createElement('video');
    v.preload = 'metadata';
    v.onloadedmetadata = () => resolve(v.duration);
    v.onerror = () => reject(new Error('Video load failed'));
    v.src = src;
    v.load();
  });
}

// ─── API WRAPPER ──────────────────────────────────────────────────────────────
async function api(url, body) {
  const token = await getCSRF();
  return fetch(url, {
    method: 'POST',
    credentials: 'same-origin',          // always send session cookie
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': token,
    },
    body: JSON.stringify(body),
  });
}

function sleep(ms) { return new Promise(r => setTimeout(r, Math.max(0, ms))); }

async function waitForAudio(audio) {
  return new Promise((resolve) => {
    if (!audio) return resolve();
    if (audio.ended) return resolve();
    if (audio.paused && audio.currentTime > 0) return resolve();
    
    const onEnded = () => {
      cleanup();
      resolve();
    };
    
    const onPause = () => {
      cleanup();
      resolve();
    };
    
    const onError = () => {
      cleanup();
      resolve();
    };
    
    const cleanup = () => {
      audio.removeEventListener('ended', onEnded);
      audio.removeEventListener('pause', onPause);
      audio.removeEventListener('error', onError);
    };
    
    audio.addEventListener('ended', onEnded);
    audio.addEventListener('pause', onPause);
    audio.addEventListener('error', onError);
    
    // Safety fallback timeout
    const duration = audio.duration || 5;
    setTimeout(() => {
      cleanup();
      resolve();
    }, (duration + 3) * 1000);
  });
}

// ─── KEYBOARD ─────────────────────────────────────────────────────────────────
document.addEventListener('keydown', e => {
  if (e.key === 'Enter' && !e.shiftKey && document.activeElement !== inpTextarea) {
    if (!isLocked && !isSubmitting && !waActionBtn.disabled) { e.preventDefault(); handleSubmit(); }
  }
  if (e.key === 'Enter' && e.ctrlKey && document.activeElement === inpTextarea) {
    if (!isLocked && !isSubmitting && !waActionBtn.disabled) handleSubmit();
  }
});

// ─── START ────────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', init);
