/**
 * TalentBot AI Screening — Language Selection Interaction
 * Handles smooth selection feedback with safety timeout fallback,
 * respects prefers-reduced-motion, and supports keyboard navigation.
 */
document.addEventListener('DOMContentLoaded', function () {
  var form = document.getElementById('langForm');
  var cards = document.querySelectorAll('.lang-card');
  if (!form || !cards.length) return;

  var isSubmitting = false;
  var prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  cards.forEach(function (card) {
    card.addEventListener('click', function (e) {
      if (isSubmitting) {
        e.preventDefault();
        return;
      }

      // If user prefers reduced motion, let native form submit proceed immediately
      if (prefersReducedMotion) {
        return;
      }

      // Prevent immediate form submission to play selection animation
      e.preventDefault();
      isSubmitting = true;

      // Reset all cards and select this one
      cards.forEach(function (c) {
        c.classList.remove('is-selected');
        c.setAttribute('aria-pressed', 'false');
      });
      card.classList.add('is-selected');
      card.setAttribute('aria-pressed', 'true');

      var langValue = card.getAttribute('value') || card.value;

      // Create or set hidden input for standard form submission
      var hiddenInput = form.querySelector('input[name="lang"]');
      if (!hiddenInput) {
        hiddenInput = document.createElement('input');
        hiddenInput.type = 'hidden';
        hiddenInput.name = 'lang';
        form.appendChild(hiddenInput);
      }
      hiddenInput.value = langValue;

      // Animation delay ~280ms, guaranteed fallback at 350ms
      var submitted = false;
      function submitForm() {
        if (!submitted) {
          submitted = true;
          form.submit();
        }
      }

      setTimeout(submitForm, 280);
      setTimeout(submitForm, 350); // safety fallback
    });
  });
});
