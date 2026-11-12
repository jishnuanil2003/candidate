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
let selectedOption = null;
let isLocked = false;
let selectedLanguage = document.getElementById('langSelect')?.value || new URLSearchParams(window.location.search).get('lang') || 'en';
let ttsEnabled = true;
let currentPlaybackId = 0;
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
      csThankYou.textContent = "Thank you for your time. Your application has been submitted successfully.";
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

if (inpText) inpText.addEventListener('input', updateActionIcon);
if (inpTextarea) inpTextarea.addEventListener('input', updateActionIcon);

// Fallback delay when video has no duration (placeholder files)
const FALLBACK_DELAY_MS = 0;

// ─── INIT ─────────────────────────────────────────────────────────────────────
async function init() {
  const greeting = document.getElementById('tbSubText');
  const candidateName = greeting?.dataset.candidateName || '';
  if (candidateName) greeting.textContent = `Hello, ${candidateName}. Your interview is ready.`;
  // Warm up CSRF before anything else
  await getCSRF();

  setSpeakingOverlay(true, 'Starting your interview...');
  lockInput(true);
  await sleep(400);
  videoEngine.ready();
  await sleep(1000); // A little gap before the first video
  await fetchQuestion();
}

// ─── FETCH QUESTION ──────────────────────────────────────────────────────────
async function fetchQuestion() {
  const playbackId = ++currentPlaybackId;
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
    if (q.number > 1) {
      langSelectEl.disabled = true;
      langSelectEl.title = "Language is locked during the interview";
    }
  }
    await handleCompletion(data.completion_video, data.ui);
    return;
  }
  if (playbackId !== currentPlaybackId) return;

  const q = data.question;
  if (data.debug) {
    console.log(`[DEBUG] Language: ${data.debug.language} | Question: ${data.debug.question_id} | Resolved File: ${data.debug.resolved_file} | Absolute Path: ${data.debug.absolute_path}`);
  }
  videoEngine.preloadPair(q.question_video, q.next_question_video);
  currentQuestion = q;
  selectedOption = null;

  localizeUI(data.ui);
  setProgress(data.progress, q.number, q.total);
  setSpeakingOverlay(true, 'Sarah is speaking...');
  lockInput(true);

  qeNum.textContent = `Question ${q.number} of ${q.total}`;
  qeText.textContent = cleanHtml(q.text);

  // Start preloading regional TTS in the background immediately
  let preloadedAudio = null;
  if (selectedLanguage !== 'en' && ttsEnabled) {
    const url = `/api/tts/?lang=${selectedLanguage}&text=${encodeURIComponent(cleanHtml(q.text))}`;
    preloadedAudio = new Audio(url);
    preloadedAudio.load();
  }

  await sleep(1000); // A little gap between videos
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
    inpText.placeholder = q.placeholder || '';
    inpText.type = q.type === 'email' ? 'email' : 'text';
    setTimeout(() => inpText.focus(), 100);
  }
  updateActionIcon();
}

// ─── SUBMIT ───────────────────────────────────────────────────────────────────
async function handleSubmit() {
  if (isLocked || !currentQuestion) return;
  currentPlaybackId++;
  cancelTTS();
  if (isRecording) stopRecording();
  isLocked = true;

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

  // Client-side English-only validation for typed inputs
  const isTyped = (qtype !== 'options' && qtype !== 'options_or_text') || (qtype === 'options_or_text' && selectedOption === '__custom__');
  if (isTyped && value && !isEnglishOnly(value)) {
    const isCoverNoteHindi = (currentQuestion?.id === 18 && selectedLanguage === 'hi');
    if (!isCoverNoteHindi) {
      showError(localizedEnglishOnlyError);
      lockInput(false);
      isLocked = false;
      return;
    }
  }

  lockInput(true);
  hideError();
  const statusText = document.getElementById('soText');
  if (statusText) statusText.textContent = 'Saving your answer...';

  let data;
  try {
    const res = await api('/api/answer/', { question_id: currentQuestion.id, value, lang: selectedLanguage });
    data = await res.json();
  } catch (e) {
    console.error('Submit error:', e);
    showError('Network error. Please check your connection and try again.');
    if (statusText) statusText.textContent = 'There was a connection error.';
    renderInput(currentQuestion);
    lockInput(false);
    isLocked = false;
    return;
  }

  if (!data.valid) {
    if (data.skipped) {
      showError(data.error_text || data.error || 'Question skipped.');
      if (statusText) statusText.textContent = 'Question skipped.';
      setProgress(data.progress);
      if (data.done) {
        localizeUI(data.ui);
        await handleCompletion(data.completion_video, data.ui);
        return;
      }
      isLocked = false;
      await sleep(1000);
      await fetchQuestion();
      return;
    }

    const errVideo = data.error_video_url || data.error_video;
    showError(data.error_text || data.error || 'Invalid input. Please try again.');
    if (data.retryable) {
      lockInput(false);
      isLocked = false;
      return;
    }
    if (errVideo) {
      const shouldMuteVideo = (selectedLanguage !== 'en');

      videoEngine.playError(errVideo, data.idle_video, shouldMuteVideo);

      if (selectedLanguage !== 'en' && ttsEnabled) {
        await sleep(300);
        speakText(cleanHtml(data.error_text || data.error), selectedLanguage);
      }

      if (selectedLanguage !== 'en' && ttsEnabled) {
        await waitForAudio(currentAudio);
      } else {
        const waitMs = await getVideoWaitTime(errVideo);
        await sleep(waitMs + 500);
      }
    } else {
      if (ttsEnabled) {
        speakText(cleanHtml(data.error_text || data.error), selectedLanguage);
        await waitForAudio(currentAudio);
      } else {
        await sleep(600);
      }
    }
    renderInput(currentQuestion);
    lockInput(false);
    isLocked = false;
    return;
  }

  if (statusText) statusText.textContent = data.done ? 'Interview finished.' : 'Answer saved.';

  setProgress(data.progress);
  if (data.done) {
    localizeUI(data.ui);
    await handleCompletion(data.completion_video, data.ui);
    return;
  }
  isLocked = false;
  await fetchQuestion();
}

// ─── COMPLETION ───────────────────────────────────────────────────────────────
async function handleCompletion(completionVideoSrc, ui) {
  currentPlaybackId++;
  cancelTTS();
  if (completionVideoSrc) {
    await sleep(1000); // A little gap before completion video
    const shouldMuteVideo = (selectedLanguage !== 'en');

    videoEngine.playQuestion(completionVideoSrc, null, shouldMuteVideo);

    if (selectedLanguage !== 'en' && ttsEnabled && ui && ui.thank_you) {
      await sleep(300);
      speakText(cleanHtml(ui.thank_you), selectedLanguage);
    }

    if (selectedLanguage !== 'en' && ttsEnabled) {
      await waitForAudio(currentAudio);
    } else {
      const waitMs = await getVideoWaitTime(completionVideoSrc);
      await sleep(waitMs);
    }
  }
  videoEngine.stopAll();
  setSpeakingOverlay(false);
  setProgress(100);

  let data = {};
  try {
    const res = await api('/api/complete/', {});
    data = await res.json();
  } catch (e) { console.error('Completion error:', e); }

  if (data.success) {
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

    completionScreen.style.display = 'flex';
    questionEcho.style.display = 'none';
    inputArea.style.display = 'none';
    lockInput(true);
  } else {
    showError(data.error || 'Failed to submit interview. Please try again or contact the recruiter.');
    lockInput(false);
  }
}

// ─── HELPERS ──────────────────────────────────────────────────────────────────
function setProgress(pct, qNum, qTotal) {
  avpFill.style.width = pct + '%';
  if (qNum && qTotal) {
    avpLabel.textContent = `Question ${qNum} of ${qTotal}`;
    rpStep.textContent = `${qNum} / ${qTotal}`;
  }
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
    if (!isLocked && (!waActionBtn.disabled)) { e.preventDefault(); handleSubmit(); }
  }
  if (e.key === 'Enter' && e.ctrlKey && document.activeElement === inpTextarea) {
    if (!isLocked && (!waActionBtn.disabled)) handleSubmit();
  }
});

// ─── START ────────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', init);
