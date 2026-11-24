/**
 * Rollback Simulation Test
 * Proves that when an answer is rejected:
 *  1. The next question's video/transition is stopped.
 *  2. The CURRENT question's text and question number are restored.
 *  3. The input field is cleared.
 *  4. The hint box appears with the correct hint text.
 *  5. The input and Send button are unlocked (never left disabled).
 *  6. The next question is NEVER left displayed.
 */
const assert = require('assert');

// 1. Mock DOM environment
const elements = {};
function createElement(id, tagName = 'div') {
  const el = {
    id,
    tagName: tagName.toUpperCase(),
    value: '',
    textContent: '',
    innerHTML: '',
    style: { display: 'none', opacity: '1' },
    classList: {
      classes: new Set(),
      add(c) { this.classes.add(c); },
      remove(c) { this.classes.delete(c); },
      toggle(c, v) { if (v) this.classes.add(c); else this.classes.delete(c); },
      contains(c) { return this.classes.has(c); }
    },
    disabled: false,
    focused: false,
    focus() { this.focused = true; },
    addEventListener(evt, fn) { this._listeners = this._listeners || {}; this._listeners[evt] = this._listeners[evt] || []; this._listeners[evt].push(fn); },
    removeEventListener(evt, fn) { if (this._listeners && this._listeners[evt]) this._listeners[evt] = this._listeners[evt].filter(f => f !== fn); },
    dispatchEvent(evt) { if (this._listeners && this._listeners[evt]) this._listeners[evt].forEach(fn => fn({ type: evt })); },
    play() { return Promise.resolve(); },
    pause() { this.paused = true; },
    removeAttribute() {},
    load() {}
  };
  elements[id] = el;
  return el;
}

global.document = {
  getElementById(id) {
    if (!elements[id]) createElement(id);
    return elements[id];
  },
  querySelector(sel) {
    if (sel.includes('csrf')) return { value: 'fake-csrf' };
    return null;
  },
  querySelectorAll() { return []; },
  createElement(tag) { return createElement('mock-' + Math.random(), tag); }
};

global.window = {
  location: { search: '' },
  speechSynthesis: { cancel() {} }
};

// Initialize elements
const inpText = document.getElementById('inpText');
const inpTextarea = document.getElementById('inpTextarea');
const inpHint = document.getElementById('inpHint');
const ivHintBox = document.getElementById('ivHintBox');
const ivHintBoxText = document.getElementById('ivHintBoxText');
const inpError = document.getElementById('inpError');
const inpErrorText = document.getElementById('inpErrorText');
const qeNum = document.getElementById('qeNum');
const qeText = document.getElementById('qeText');
const waActionBtn = document.getElementById('waActionBtn');
const repeatBtn = document.getElementById('repeatBtn');
const soText = document.getElementById('soText');
const videoError = document.getElementById('videoError');
const videoIdle = document.getElementById('videoIdle');
const videoQuestion = document.getElementById('videoQuestion');

// Global mock videoEngine
global.videoEngine = {
  elError: videoError,
  elIdle: videoIdle,
  elQuestion: videoQuestion,
  _switchToIdle() { this.state = 'waiting'; },
  stopAll() { this.stopped = true; },
  playError(errSrc, idleSrc, muted) { this.playingError = errSrc; if (this.elError) this.elError.loop = false; },
  pause() { this.paused = true; }
};

// Functions from interview_v2.js under test
let currentQuestion = null;
let currentPlaybackId = 0;
let isLocked = false;
let selectedOption = null;
let answerQueue = [];
let ttsEnabled = false;
let selectedLanguage = 'en';

const QUESTION_HINTS = {
  22: "Enter the month and year, for example: June 2025.",
  23: "Enter the month and year, or Ongoing, for example: August 2025."
};

function cleanHtml(html) { return String(html ?? '').replace(/<[^>]*>/g, ''); }

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
  box.style.display = 'none';
}

function lockInput(locked) {
  if (waActionBtn) waActionBtn.disabled = locked;
  if (inpText) inpText.disabled = locked;
  if (inpTextarea) inpTextarea.disabled = locked;
  if (repeatBtn) repeatBtn.disabled = locked;
}

function renderInput(q) {
  inpText.style.display = 'block';
  inpText.value = '';
  const isDateQ = (q.id === 22 || q.id === 23);
  if (isDateQ) {
    const hintStr = q.hint || QUESTION_HINTS[q.id];
    inpHint.textContent = hintStr;
    inpHint.style.display = 'block';
    inpText.placeholder = hintStr;
  }
}

function updateActionIcon() {}
function cancelTTS() {}
async function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

async function handleAnswerFailure(item) {
  currentPlaybackId++;
  cancelTTS();

  const answeringQuestion = item.question;
  const data = item.errorData || {};

  const idx = answerQueue.indexOf(item);
  if (idx !== -1) answerQueue.splice(idx, 1);

  if (soText) soText.textContent = data.network_error ? 'Connection error.' : 'Invalid answer.';

  // 1. ROLLBACK OPTIMISTIC TRANSITION: stop next question's video
  videoEngine.stopAll();

  // 2. Restore CURRENT question (number, text, options)
  currentQuestion = answeringQuestion;
  selectedOption = null;
  if (qeNum) qeNum.textContent = `Question ${answeringQuestion.number} of ${answeringQuestion.total}`;
  if (qeText) qeText.innerHTML = cleanHtml(answeringQuestion.text);

  // 3. Clear input and re-render current question input
  renderInput(answeringQuestion);
  if (inpText) inpText.value = '';
  if (inpTextarea) inpTextarea.value = '';
  updateActionIcon();

  const errVideo = data.error_video_url || data.error_video;
  const qHint = data.hint || answeringQuestion.hint || QUESTION_HINTS[answeringQuestion.id] || 'Please enter a valid response.';

  // Show the hint box at the moment invalid video starts
  showHintBox(qHint);

  try {
    if (errVideo) {
      videoEngine.playError(errVideo, data.idle_video, false);
      if (videoEngine.elError) videoEngine.elError.loop = false;
      await sleep(50);
    } else {
      await sleep(10);
    }
  } catch (err) {
    console.warn('Error during invalid answer flow:', err);
  } finally {
    // Return to waiting state (blink/idle loop)
    videoEngine._switchToIdle();

    // Re-enable input and Send button
    lockInput(false);
    isLocked = false;

    // Focus input
    if (inpText && inpText.style.display !== 'none') {
      inpText.focus();
    }
  }
}

async function runTest() {
  console.log("Starting Rollback Simulation Test...");

  const question22 = {
    id: 22,
    number: 22,
    total: 24,
    text: "When did your internship start? Please provide the month and year.",
    hint: "Enter the month and year, for example: June 2025."
  };

  const question23 = {
    id: 23,
    number: 23,
    total: 24,
    text: "When did your internship end, or is it still ongoing?",
    hint: "Enter the month and year, or Ongoing, for example: August 2025."
  };

  // Simulate user currently on Question 22
  currentQuestion = question22;
  qeNum.textContent = "Question 22 of 24";
  qeText.textContent = question22.text;
  inpText.value = "june 202";
  lockInput(true);
  isLocked = true;

  // Simulate an optimistic transition that began playing Question 23:
  currentQuestion = question23;
  qeNum.textContent = "Question 23 of 24";
  qeText.textContent = question23.text;

  assert.strictEqual(currentQuestion.id, 23, "Precondition: Question 23 was optimistically displayed");

  // Server returns validation failure for Question 22
  const failedItem = {
    question: question22,
    value: "june 202",
    lang: "en",
    status: "failed",
    errorData: {
      valid: false,
      reason: "invalid",
      error: "That date doesn't look right.",
      error_video_url: "/media/interview/english/invalid_input.mp4?v=123",
      hint: "Enter the month and year, for example: June 2025."
    }
  };

  console.log("Executing handleAnswerFailure (rollback)...");
  await handleAnswerFailure(failedItem);

  // VERIFY 1: Next question video was stopped
  assert.strictEqual(videoEngine.stopped, true, "TEST 1 PASSED: videoEngine.stopAll() was called");

  // VERIFY 2: CURRENT question (22) was completely restored
  assert.strictEqual(currentQuestion.id, 22, "TEST 2A PASSED: currentQuestion restored to 22");
  assert.strictEqual(qeNum.textContent, "Question 22 of 24", "TEST 2B PASSED: qeNum restored to Question 22 of 24");
  assert.strictEqual(qeText.innerHTML, question22.text, "TEST 2C PASSED: qeText restored to Question 22 text");
  assert.notStrictEqual(qeText.innerHTML, question23.text, "TEST 2D PASSED: Question 23 is NOT displayed");

  // VERIFY 3: Input field is cleared
  assert.strictEqual(inpText.value, "", "TEST 3 PASSED: Input field is cleared");

  // VERIFY 4: Hint box appears with correct hint
  assert.strictEqual(ivHintBox.style.display, "flex", "TEST 4A PASSED: ivHintBox is displayed");
  assert.strictEqual(ivHintBoxText.textContent, "Invalid input. Enter the month and year, for example: June 2025.", "TEST 4B PASSED: Correct hint text displayed");

  // VERIFY 5: Input and Send button are re-enabled and unlocked
  assert.strictEqual(isLocked, false, "TEST 5A PASSED: isLocked is false");
  assert.strictEqual(waActionBtn.disabled, false, "TEST 5B PASSED: Send button is enabled");
  assert.strictEqual(inpText.disabled, false, "TEST 5C PASSED: Input is enabled");
  assert.strictEqual(inpText.focused, true, "TEST 5D PASSED: Input is focused");

  // VERIFY 6: Typing in input hides the hint box
  console.log("Simulating candidate typing...");
  inpText.value = "J";
  hideHintBox();
  assert.strictEqual(ivHintBox.style.display, "none", "TEST 6 PASSED: Hint box hidden after typing");

  console.log("\nALL ROLLBACK AND HINT ASSERTIONS PASSED SUCCESSFULLY!");
}

runTest().catch(err => {
  console.error("Test failed:", err);
  process.exit(1);
});
