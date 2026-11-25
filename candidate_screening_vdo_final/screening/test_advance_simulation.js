/**
 * Client-Side Simulation Test for Invalid-then-Valid Flow & Rollback
 * Tests the full sequence:
 *  1. Invalid then valid on question 22 advances to question 23 without a refresh
 *  2. Two invalid answers then a valid one advances
 *  3. Queue is empty after rejection
 *  4. No leftover timer or listener fires after unlock
 *  5. Late response from rejected answer does not overwrite state
 *  6. Progress counter stays the same on retry and increases by 1 on advance
 */
const assert = require('assert');

// 1. Mock DOM
const elements = {};
function createElement(id) {
  const el = {
    id,
    value: '',
    textContent: '',
    innerHTML: '',
    style: { display: 'none', opacity: '1' },
    attributes: {},
    setAttribute(k, v) { this.attributes[k] = v; },
    getAttribute(k) { return this.attributes[k]; },
    classList: {
      classes: new Set(),
      add(c) { this.classes.add(c); },
      remove(c) { this.classes.delete(c); },
      contains(c) { return this.classes.has(c); }
    },
    disabled: false,
    focused: false,
    focus() { this.focused = true; }
  };
  elements[id] = el;
  return el;
}

global.document = {
  getElementById(id) {
    if (!elements[id]) createElement(id);
    return elements[id];
  },
  querySelector(sel) { return null; },
  querySelectorAll() { return []; }
};

const inpText = document.getElementById('inpText');
const inpTextarea = document.getElementById('inpTextarea');
const waActionBtn = document.getElementById('waActionBtn');
const repeatBtn = document.getElementById('repeatBtn');
const soText = document.getElementById('soText');
const ivHintBox = document.getElementById('ivHintBox');
const ivHintBoxText = document.getElementById('ivHintBoxText');
const qeText = document.getElementById('qeText');
const qeNum = document.getElementById('qeNum');
const rpStep = document.getElementById('rpStep');
const avpFill = document.getElementById('avpFill');
const avpLabel = document.getElementById('avpLabel');

// Timer and Listener tracking
let activeTimers = new Set();
let activeListeners = new Map();

function trackSetTimeout(fn, ms) {
  const id = setTimeout(() => {
    activeTimers.delete(id);
    fn();
  }, ms);
  activeTimers.add(id);
  return id;
}

function trackClearTimeout(id) {
  activeTimers.delete(id);
  clearTimeout(id);
}

const vEl = {
  duration: 2.0,
  currentTime: 0,
  paused: true,
  src: '',
  addEventListener(evt, fn) {
    if (!activeListeners.has(evt)) activeListeners.set(evt, new Set());
    activeListeners.get(evt).add(fn);
  },
  removeEventListener(evt, fn) {
    if (activeListeners.has(evt)) activeListeners.get(evt).delete(fn);
  },
  play() { this.paused = false; return Promise.resolve(); },
  pause() { this.paused = true; },
  load() {}
};

// VideoEngine implementation with cancelError
class VideoEngine {
  constructor() {
    this.state = 'idle';
    this.elQuestion = vEl;
    this._errorResolve = null;
    this._errorCleanup = null;
  }
  _switchToIdle() {
    this.state = 'waiting';
    this.elQuestion.pause();
  }
  cancelError() {
    if (this._errorCleanup) {
      this._errorCleanup();
      this._errorCleanup = null;
    }
  }
  pause() {
    this.cancelError();
    this.elQuestion.pause();
  }
  playError(errSrc, idleSrc, muted) {
    this.cancelError();
    this.state = 'error';
    return new Promise(resolve => {
      let settled = false;
      let safetyTimer = null;

      const cleanup = () => {
        if (safetyTimer) { trackClearTimeout(safetyTimer); safetyTimer = null; }
        vEl.removeEventListener('ended', onEnded);
        vEl.removeEventListener('error', onError);
        vEl.removeEventListener('timeupdate', onTimeUpdate);
        this._errorResolve = null;
        this._errorCleanup = null;
      };

      const finish = () => {
        if (settled) return;
        settled = true;
        cleanup();
        this._switchToIdle();
        resolve();
      };

      this._errorResolve = finish;
      this._errorCleanup = () => {
        if (settled) return;
        settled = true;
        cleanup();
        resolve();
      };

      const onEnded = () => finish();
      const onError = () => finish();
      const onTimeUpdate = () => {
        if (this.state === 'error' && vEl.duration && vEl.duration - vEl.currentTime <= 0.35) {
          finish();
        }
      };

      vEl.addEventListener('ended', onEnded);
      vEl.addEventListener('error', onError);
      vEl.addEventListener('timeupdate', onTimeUpdate);
      safetyTimer = trackSetTimeout(finish, 50);
      vEl.play();
    });
  }
  playQuestion(src) {
    this.cancelError();
    this.state = 'speaking';
    vEl.src = src;
    vEl.play();
  }
}
const videoEngine = new VideoEngine();

// Client state variables from interview_v2.js
let currentQuestion = null;
let nextQuestionData = null;
let conditionalNextMap = null;
let answerQueue = [];
let isProcessingQueue = false;
let selectedOption = null;
let isLocked = false;
let isSubmitting = false;
let currentPlaybackId = 0;
let submissionSequence = 0;
let currentQNumber = 1;
let currentQTotal = 0;
let selectedLanguage = 'en';
let ttsEnabled = false;

const QUESTION_HINTS = {
  22: "Enter the month and year, for example: June 2025 or 06/2025.",
  23: "Enter the month and year, or Ongoing, for example: August 2025 or 08/2025."
};

function lockInput(locked) {
  waActionBtn.disabled = locked;
  inpText.disabled = locked;
  repeatBtn.disabled = locked;
}

function updateProgressUI(qNum, qTotal, pct) {
  if (qNum) currentQNumber = Number(qNum);
  if (qTotal) currentQTotal = Number(qTotal);
  rpStep.textContent = currentQNumber + '/' + currentQTotal;
  avpLabel.textContent = `Question ${currentQNumber} of ${currentQTotal}`;
}

function showHintBox(hint) {
  ivHintBox.style.display = 'flex';
  ivHintBoxText.textContent = hint;
}
function hideHintBox() { ivHintBox.style.display = 'none'; }
function showError(msg) {}
function hideError() {}
function cleanHtml(h) { return String(h || '').replace(/<[^>]*>/g, ''); }
function cancelTTS() {}
function localizeUI(ui) {}

function renderInput(q) {
  inpText.value = '';
  inpText.style.display = 'block';
  inpText.disabled = false;
}

function parseMonthYearClient(val) {
  if (!val || typeof val !== 'string') return null;
  const str = val.trim().toLowerCase();
  const cleaned = str.replace(/[,/\-]/g, ' ');
  const tokens = cleaned.split(/\s+/).filter(Boolean);
  if (tokens.length !== 2) return null;
  const monthNames = { 'june': 6, 'jun': 6, 'august': 8, 'aug': 8 };
  if (!monthNames[tokens[0]]) return null;
  if (!/^\d{4}$/.test(tokens[1])) return null;
  return { month: monthNames[tokens[0]], year: parseInt(tokens[1], 10) };
}

// Mock API routing
let mockApiHandler = null;
async function api(url, body) {
  if (mockApiHandler) return mockApiHandler(url, body);
  throw new Error("No mock handler");
}

async function displayQuestion(data) {
  const playbackId = ++currentPlaybackId;
  const q = data.question;
  if (!q) return;
  currentQuestion = q;
  selectedOption = null;
  hideHintBox();
  hideError();

  if (data.next_question) nextQuestionData = data.next_question;
  if (data.conditional_next) conditionalNextMap = data.conditional_next;

  updateProgressUI(q.number, q.total, data.progress);
  lockInput(true);
  qeText.innerHTML = cleanHtml(q.text);
  qeNum.textContent = `Question ${q.number} of ${q.total}`;

  videoEngine.playQuestion(q.question_video);
  await new Promise(r => setTimeout(r, 20));
  renderInput(q);
  lockInput(false);
}

async function fetchQuestion() {
  const res = await api('/api/question/', { lang: selectedLanguage });
  const data = await res.json();
  await displayQuestion(data);
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

  nextQuestionData = null;
  conditionalNextMap = null;

  if (data.skipped) {
    hideHintBox();
    updateProgressUI(data.current_number, data.total, data.progress);
    isLocked = false;
    isSubmitting = false;
    await fetchQuestion();
    return;
  }

  videoEngine.pause();
  currentQuestion = answeringQuestion;
  selectedOption = null;
  updateProgressUI(answeringQuestion.number, answeringQuestion.total, data.progress);
  qeText.innerHTML = cleanHtml(answeringQuestion.text);

  renderInput(answeringQuestion);

  const errVideo = data.error_video_url || data.error_video;
  const qHint = data.hint || answeringQuestion.hint || QUESTION_HINTS[answeringQuestion.id] || 'Please enter a valid response.';
  showHintBox(qHint);

  try {
    if (errVideo) {
      await videoEngine.playError(errVideo, data.idle_video, false);
    }
  } catch (err) {
  } finally {
    if (typeof videoEngine !== 'undefined' && videoEngine.cancelError) {
      videoEngine.cancelError();
    }
    videoEngine._switchToIdle();
    lockInput(false);
    isLocked = false;
    isSubmitting = false;
    inpText.focus();
  }
}

async function processAnswerQueue() {
  if (isProcessingQueue) return;
  isProcessingQueue = true;

  while (true) {
    const item = answerQueue.find(i => i.status === 'pending');
    if (!item) break;

    item.status = 'sending';
    let data;
    try {
      const res = await api('/api/answer/', {
        question_id: item.question.id,
        value: item.value,
        lang: item.lang
      });
      data = await res.json();
    } catch (err) {
      data = { valid: false, network_error: true, error: 'Network error.' };
    }

    if (item.id !== submissionSequence || (currentQuestion && item.questionId !== currentQuestion.id && !item.optimisticTarget)) {
      console.log('  [TEST] Stale/out-of-order response ignored for submission ID:', item.id);
      const idx = answerQueue.indexOf(item);
      if (idx !== -1) answerQueue.splice(idx, 1);
      continue;
    }

    if (data.valid) {
      item.status = 'confirmed';
      item.responseData = data;
      if (data.ui) localizeUI(data.ui);
      if (data.next_question) nextQuestionData = data.next_question;
      if (data.conditional_next) conditionalNextMap = data.conditional_next;

      if (item.optimisticTarget) {
        const idx = answerQueue.indexOf(item);
        if (idx !== -1) answerQueue.splice(idx, 1);
        if (data.question && currentQuestion && data.question.id !== currentQuestion.id) {
          await displayQuestion(data);
        }
      }
    } else {
      item.errorData = data;
      isProcessingQueue = false;
      await handleAnswerFailure(item);
      item.status = 'failed';
      return;
    }
  }
  isProcessingQueue = false;
}

async function handleSubmit(typedValue) {
  if (isLocked || isSubmitting || !currentQuestion) return false;
  let value = typedValue;
  isSubmitting = true;
  isLocked = true;
  lockInput(true);
  hideError();

  const answeringQuestion = currentQuestion;
  const isDateQ = (answeringQuestion.id === 22 || answeringQuestion.id === 23);
  let isClientInvalidDate = false;
  if (isDateQ && value && !parseMonthYearClient(value)) {
    isClientInvalidDate = true;
  }

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
  processAnswerQueue();

  let targetNext = isClientInvalidDate ? null : nextQuestionData;

  if (targetNext) {
    queueItem.optimisticTarget = targetNext;
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
    return true;
  } else {
    try {
      while (queueItem.status === 'pending' || queueItem.status === 'sending') {
        await new Promise(r => setTimeout(r, 10));
      }
      if (queueItem.status === 'failed') {
        return false;
      }
      const data = queueItem.responseData;
      const idx = answerQueue.indexOf(queueItem);
      if (idx !== -1) answerQueue.splice(idx, 1);

      if (!data || !data.valid) {
        await fetchQuestion();
      } else if (data.done) {
        // completion
      } else if (data.question) {
        await displayQuestion(data);
      } else {
        await fetchQuestion();
      }
      return true;
    } catch (err) {
      await fetchQuestion();
      return false;
    } finally {
      isLocked = false;
      isSubmitting = false;
    }
  }
}

// ─── TEST SUITE ───────────────────────────────────────────────────────────────
async function runAllTests() {
  console.log("=== RUNNING ADVANCE & ROLLBACK VERIFICATION TESTS ===\n");

  const q22 = { id: 22, number: 2, total: 5, text: "When did your internship start?", question_video: "/media/q22.mp4" };
  const q23 = { id: 23, number: 3, total: 5, text: "When did your internship end?", question_video: "/media/q23.mp4" };
  const q24 = { id: 24, number: 4, total: 5, text: "What were your duties?", question_video: "/media/q24.mp4" };

  // TEST 1: Invalid then valid on Question 22 advances to Question 23 without refresh
  console.log("TEST 1: Invalid answer then valid answer on question 22...");
  currentQuestion = q22;
  nextQuestionData = q23;
  updateProgressUI(2, 5, 20);

  let calls = 0;
  mockApiHandler = async (url, body) => {
    if (url === '/api/answer/') {
      calls++;
      if (body.value === 'invalid_date') {
        return {
          json: async () => ({
            valid: false,
            reason: 'invalid',
            error: 'Invalid date',
            error_video_url: '/media/invalid_input.mp4',
            hint: 'Enter the month and year, for example: June 2025.',
            attempts_left: 2
          })
        };
      } else if (body.value === 'June 2025') {
        return {
          json: async () => ({
            valid: true,
            question: q23,
            next_question: q24,
            progress: 40
          })
        };
      }
    }
  };

  // Step 1: Submit invalid answer
  const res1 = await handleSubmit('invalid_date');
  assert.strictEqual(res1, false, "Invalid submission returns false");
  assert.strictEqual(currentQuestion.id, 22, "Current question remains 22 after invalid");
  assert.strictEqual(answerQueue.length, 0, "Queue is empty after rejection");
  assert.strictEqual(isLocked, false, "Input is unlocked after invalid video");
  assert.strictEqual(inpText.disabled, false, "Input field is enabled");
  assert.strictEqual(rpStep.textContent, "2/5", "Progress counter unchanged at 2/5 on invalid");

  // Verify no leftover timers or listeners
  assert.strictEqual(activeTimers.size, 0, "No pending timers after invalid video completes");
  let totalListeners = 0;
  for (let s of activeListeners.values()) totalListeners += s.size;
  assert.strictEqual(totalListeners, 0, "No active event listeners left from invalid video");

  // Step 2: Submit valid answer to the SAME question
  const res2 = await handleSubmit('June 2025');
  assert.strictEqual(res2, true, "Valid submission returns true");
  assert.strictEqual(currentQuestion.id, 23, "Client advanced to Question 23 without refresh!");
  assert.strictEqual(answerQueue.length, 0, "Queue is empty after valid advancement");
  assert.strictEqual(isLocked, false, "Input is unlocked for Question 23");
  assert.strictEqual(rpStep.textContent, "3/5", "Progress counter increased to 3/5 on advance");
  console.log("  ✓ TEST 1 PASSED: Advances from 22 to 23 without refresh. Counter 2/5 -> 3/5.\n");

  // TEST 2: Two invalid answers then a valid one advances
  console.log("TEST 2: Two invalid answers then a valid one advances...");
  currentQuestion = q22;
  nextQuestionData = q23;
  updateProgressUI(2, 5, 20);

  let attemptCount = 0;
  mockApiHandler = async (url, body) => {
    if (url === '/api/answer/') {
      attemptCount++;
      if (body.value.startsWith('bad_date')) {
        return {
          json: async () => ({
            valid: false,
            reason: 'invalid',
            error: 'Invalid date',
            error_video_url: '/media/invalid_input.mp4',
            hint: 'Enter the month and year.',
            attempts_left: 3 - attemptCount
          })
        };
      } else {
        return {
          json: async () => ({
            valid: true,
            question: q23,
            next_question: q24,
            progress: 40
          })
        };
      }
    }
  };

  // Attempt 1: Invalid
  await handleSubmit('bad_date_1');
  assert.strictEqual(currentQuestion.id, 22);
  assert.strictEqual(rpStep.textContent, "2/5");

  // Attempt 2: Invalid
  await handleSubmit('bad_date_2');
  assert.strictEqual(currentQuestion.id, 22);
  assert.strictEqual(rpStep.textContent, "2/5");

  // Attempt 3: Valid
  const res3 = await handleSubmit('June 2025');
  assert.strictEqual(res3, true);
  assert.strictEqual(currentQuestion.id, 23);
  assert.strictEqual(rpStep.textContent, "3/5");
  console.log("  ✓ TEST 2 PASSED: Two invalid then valid cleanly advances to 23.\n");

  // TEST 3: Late response from rejected answer is ignored and does not overwrite state
  console.log("TEST 3: Late response from rejected answer does not overwrite state...");
  currentQuestion = q23; // Already advanced to 23
  submissionSequence = 10; // Late response from sequence 9
  const lateItem = {
    id: 9,
    questionId: 22,
    question: q22,
    value: 'old_bad_date',
    status: 'pending'
  };
  answerQueue.push(lateItem);
  mockApiHandler = async () => ({
    json: async () => ({ valid: false, error: 'late error' })
  });
  await processAnswerQueue();
  // Ensure currentQuestion was NOT rolled back to 22
  assert.strictEqual(currentQuestion.id, 23, "Current question remains 23; late rejected response was safely ignored");
  console.log("  ✓ TEST 3 PASSED: Late rejected response ignored; state preserved.\n");

  console.log("ALL 3 VERIFICATION TESTS PASSED SUCCESSFULLY!");
}

runAllTests().catch(e => {
  console.error("Test failed:", e);
  process.exit(1);
});
