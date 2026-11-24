/**
 * VideoEngine — seamless avatar video management
 * Handles: question, idle, error playback, transitions, preloading, state
 */
class VideoEngine {
  constructor() {
    this.elQuestion = document.getElementById('videoQuestion');
    this.elIdle = document.getElementById('videoIdle');
    this.elError = document.getElementById('videoError');
    this.elPreload = document.getElementById('videoPreload');
    this.elOverlay = document.getElementById('videoOverlay');
    this.elGlow = document.getElementById('videoGlow');
    this.elCaption = document.getElementById('avCaption');
    this.elLiveBadge = document.getElementById('liveBadge');
    this.elStatus = document.getElementById('avStatusText');
    this.elRepeatBtn = document.getElementById('repeatBtn');
    this.elOverlayText = this.elOverlay ? this.elOverlay.querySelector('span') : null;

    this.currentQuestionSrc = null;
    this.currentIdleSrc = null;
    this.currentPreloadSrc = null;
    this.state = 'idle'; // idle | speaking | waiting | error
    this._preloaded = {};
    this._loadingTimeout = null;
    this._fallbackAudio = null;
    this.elQuestion.addEventListener('error', () => {
      this._playAudioFallback();
    });

    // Anticipatory crossfade: start transitioning to idle slightly BEFORE the video ends
    // so the avatar doesn't "freeze" on the last frame during the fade.
    this.elQuestion.addEventListener('timeupdate', () => {
      if (this.state === 'speaking' && this.elQuestion.duration) {
        if (this.elQuestion.duration - this.elQuestion.currentTime <= 0.35) {
          this._switchToIdle();
        }
      }
    });
    // Fallback just in case
    this.elQuestion.addEventListener('ended', () => {
      if (this.state === 'speaking') this._switchToIdle();
    });

    this.elError.addEventListener('timeupdate', () => {
      if (this.state === 'error' && this.elError.duration) {
        if (this.elError.duration - this.elError.currentTime <= 0.35) {
          this._switchToIdle();
        }
      }
    });
    this.elError.addEventListener('ended', () => {
      if (this.state === 'error') this._switchToIdle();
    });
  }

  /** Preload only the NEXT question's video into the hidden video element. */
  preloadNext(url) {
    if (!url || url === this.currentPreloadSrc) return;
    this.currentPreloadSrc = url;
    if (this.elPreload) {
      this.elPreload.src = url;
      this.elPreload.preload = 'auto';
      this.elPreload.muted = true;
      this.elPreload.load();
    }
  }

  /** Preload idle/blink loop and outro video at interview start. */
  preloadGlobalAssets(idleUrl, outroUrl) {
    if (idleUrl && this.elIdle) {
      if (!this.elIdle.src || !this.elIdle.src.includes(idleUrl.split('?')[0])) {
        this.elIdle.src = idleUrl;
        this.elIdle.load();
      }
    }
    if (outroUrl && !this._preloaded[outroUrl]) {
      const v = document.createElement('video');
      v.preload = 'auto';
      v.muted = true;
      v.src = outroUrl;
      v.load();
      this._preloaded[outroUrl] = v;
    }
  }

  /** Keep only the current and next question video warm in the browser cache. */
  preloadPair(currentUrl, nextUrl) {
    if (nextUrl) this.preloadNext(nextUrl);
    const wanted = new Set([currentUrl, nextUrl].filter(Boolean));
    for (const [url, video] of Object.entries(this._preloaded)) {
      if (!wanted.has(url)) {
        video.pause();
        video.removeAttribute('src');
        video.load();
        delete this._preloaded[url];
      }
    }
    for (const url of wanted) {
      if (this._preloaded[url]) continue;
      const video = document.createElement('video');
      video.preload = 'auto';
      video.muted = true;
      video.src = url;
      this._preloaded[url] = video;
      video.load();
    }
  }

  /** Reveal the player (hide loading overlay) */
  ready() {
    this.elOverlay.classList.add('hidden');
    this.elLiveBadge.style.display = 'flex';
    this._setStatus('Ready', true);
  }

  /**
   * Show a brief loading overlay, wait for canplay, then play.
   * Keeps the idle video visible as backdrop while buffering
   * so the screen is NEVER blank during transitions.
   */
  playQuestion(src, idleSrc, muted) {
    if (this._fallbackAudio) { this._fallbackAudio.pause(); this._fallbackAudio = null; }
    this.currentQuestionSrc = src;
    this.currentIdleSrc = idleSrc;
    this.state = 'speaking';
    this.currentMuted = !!muted;

    this._setStatus('Sarah is speaking...', true);
    this._setCaption('🎙 Speaking');
    this.elGlow.classList.add('active');
    this.elGlow.classList.remove('error-glow');
    this.elRepeatBtn.disabled = false;

    if (!src) {
      if (this._overlayTimeout) clearTimeout(this._overlayTimeout);
      this._hideOverlay();
      if (idleSrc && this.elIdle.src !== idleSrc) {
        this.elIdle.src = idleSrc;
        this.elIdle.load();
      }
      if (idleSrc) {
        this.elIdle.style.zIndex = 2;
        this.elIdle.classList.remove('hidden');
        this.elIdle.play().catch(() => { });
      }
      return;
    }

    // Delay loading overlay so fast/preloaded transitions don't flash
    if (this._overlayTimeout) clearTimeout(this._overlayTimeout);
    this._overlayTimeout = setTimeout(() => {
      if (this.state === 'speaking') {
        this._showOverlay('Loading next question...');
      }
    }, 600);

    // Keep idle/blink loop visible as a backdrop while question video buffers
    this.elError.classList.add('hidden');
    this.elError.style.zIndex = 1;

    // Keep idle loop active and visible until next video is ready
    if (idleSrc && this.elIdle.src !== idleSrc) {
      this.elIdle.src = idleSrc;
      this.elIdle.load();
    }
    if (idleSrc) {
      this.elIdle.style.zIndex = 2;
      this.elIdle.classList.remove('hidden');
      this.elIdle.play().catch(() => { });
    }

    // Keep question behind idle loop until playback begins
    this.elQuestion.style.zIndex = 1;
    this.elQuestion.classList.add('hidden');

    // Load new question video if changed
    if (this.elQuestion.src !== src) {
      this.elQuestion.src = src;
      this.elQuestion.currentTime = 0;
      this.elQuestion.muted = !!muted;
      this.elQuestion.load();
    } else {
      this.elQuestion.currentTime = 0;
      this.elQuestion.muted = !!muted;
    }

    // Safety timeout: if canplay never fires, start playback after max 4s
    if (this._loadingTimeout) clearTimeout(this._loadingTimeout);
    this._loadingTimeout = setTimeout(() => this._startPlayback(), 4000);

    // If already sufficiently buffered, play immediately; otherwise wait for canplay
    if (this.elQuestion.readyState >= 3) {
      this._startPlayback();
    } else {
      this.elQuestion.addEventListener('canplay', () => this._startPlayback(), { once: true });
    }
  }

  /** Internal: hide overlay and start playing the question video */
  _startPlayback() {
    if (this._loadingTimeout) { clearTimeout(this._loadingTimeout); this._loadingTimeout = null; }
    if (this._overlayTimeout) { clearTimeout(this._overlayTimeout); this._overlayTimeout = null; }
    if (this.state !== 'speaking') return;

    this._hideOverlay();

    // Bring question video to front and reveal
    this.elQuestion.style.zIndex = 2;
    this.elQuestion.classList.remove('hidden');
    this.elQuestion.muted = !!this.currentMuted;

    const playPromise = this.elQuestion.play();
    if (playPromise) {
      const hideIdleWhenPlaying = () => {
        if (this.state === 'speaking') {
          this.elIdle.style.zIndex = 1;
          this.elIdle.classList.add('hidden');
        }
      };
      this.elQuestion.addEventListener('playing', hideIdleWhenPlaying, { once: true });
      playPromise.then(() => {
        // Fallback hide after play starts
        setTimeout(hideIdleWhenPlaying, 50);
      }).catch(() => {
        this._playAudioFallback();
      });
    }
  }

  _playAudioFallback() {
    if (this.state !== 'speaking' || !this.currentQuestionSrc || this._fallbackAudio) return;
    this._setCaption('Playing question audio...');
    this._fallbackAudio = new Audio(this.currentQuestionSrc);
    this._fallbackAudio.addEventListener('ended', () => {
      this._fallbackAudio = null;
      this._switchToIdle();
    }, { once: true });
    this._fallbackAudio.addEventListener('error', () => {
      this._fallbackAudio = null;
      this._switchToIdle();
    }, { once: true });
    this._fallbackAudio.play().catch(() => {
      this._fallbackAudio = null;
      this._switchToIdle();
    });
  }

  /** Switch to looping idle video */
  _switchToIdle() {
    this.state = 'waiting';
    if (this._fallbackAudio) { this._fallbackAudio.pause(); this._fallbackAudio = null; }
    this.elQuestion.pause();
    this.elError.pause();
    this._setStatus('Waiting for your response...', true);
    this._setCaption('👂 Listening...');
    this.elGlow.classList.remove('active', 'error-glow');

    this.elQuestion.style.zIndex = 1;
    this.elQuestion.classList.add('hidden');
    this.elError.style.zIndex = 1;
    this.elError.classList.add('hidden');

    if (this.currentIdleSrc) {
      if (this.elIdle.src !== this.currentIdleSrc) {
        this.elIdle.src = this.currentIdleSrc;
      }
      this.elIdle.style.zIndex = 2;
      this.elIdle.classList.remove('hidden');
      this.elIdle.play().catch(() => { });
    }
  }

  /** Play error video, then auto-return to idle */
  playError(errorSrc, idleSrc, muted) {
    this.currentIdleSrc = idleSrc;
    this.state = 'error';

    this._setStatus('Please try again...', true);
    this._setCaption('⚠ Validation error');
    this.elGlow.classList.remove('active');
    this.elGlow.classList.add('error-glow');

    this.elQuestion.style.zIndex = 1;
    this.elQuestion.classList.add('hidden');
    this.elIdle.style.zIndex = 1;
    this.elIdle.classList.add('hidden');

    this.elError.loop = false;
    this.elError.src = errorSrc;
    this.elError.style.zIndex = 2;
    this.elError.classList.remove('hidden');
    this.elError.currentTime = 0;
    this.elError.muted = !!muted;
    this.elError.play().catch(() => { });
  }

  /** Safely pause all active video/audio playback */
  pause() {
    if (this._loadingTimeout) { clearTimeout(this._loadingTimeout); this._loadingTimeout = null; }
    if (this._overlayTimeout) { clearTimeout(this._overlayTimeout); this._overlayTimeout = null; }
    if (this.elQuestion) this.elQuestion.pause();
    if (this.elError) this.elError.pause();
    if (this.elIdle) this.elIdle.pause();
    if (this._fallbackAudio) { this._fallbackAudio.pause(); this._fallbackAudio = null; }
  }

  /** Replay the last question video */
  repeatQuestion(muted) {
    if (this.currentQuestionSrc) {
      const isMuted = (muted !== undefined) ? !!muted : !!this.currentMuted;
      this.playQuestion(this.currentQuestionSrc, this.currentIdleSrc, isMuted);
    }
  }

  /** Stop everything (for completion) */
  stopAll() {
    if (this._loadingTimeout) { clearTimeout(this._loadingTimeout); this._loadingTimeout = null; }
    if (this._overlayTimeout) { clearTimeout(this._overlayTimeout); this._overlayTimeout = null; }
    this.elQuestion.pause();
    this.elIdle.pause();
    this.elError.pause();
    if (this._fallbackAudio) { this._fallbackAudio.pause(); this._fallbackAudio = null; }
    this.elQuestion.classList.add('hidden');
    this.elIdle.classList.add('hidden');
    this.elError.classList.add('hidden');
    this.elGlow.classList.remove('active', 'error-glow');
    this.elRepeatBtn.disabled = true;
    this._setStatus('Interview complete', false);
    this._setCaption('');
  }

  /** Show loading overlay with custom message */
  _showOverlay(msg) {
    if (this.elOverlayText) this.elOverlayText.textContent = msg || 'Loading...';
    this.elOverlay.classList.remove('hidden');
  }

  /** Hide loading overlay */
  _hideOverlay() {
    this.elOverlay.classList.add('hidden');
  }

  _setCaption(text) {
    this.elCaption.textContent = text;
  }

  _setStatus(text, online) {
    this.elStatus.textContent = text;
    const dot = document.querySelector('.status-pulse');
    if (dot) dot.style.background = online ? 'var(--green)' : '#888';
  }

  /** Call this after a user gesture (click) to ensure audio is unlocked */
  unlockAudio() {
    [this.elQuestion, this.elIdle, this.elError].forEach(v => {
      v.muted = false;
      // Play and immediately pause to unlock audio context
      const p = v.play();
      if (p) p.then(() => v.pause()).catch(() => { });
    });
  }
}

// Global instance
const videoEngine = new VideoEngine();
