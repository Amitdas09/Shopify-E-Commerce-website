/* ==========================================================================
   Reviews marquee pause control.

   The prototype paused the rail on :hover and :focus-within only. Neither
   exists on a touch device, so on mobile the reviews scrolled forever with no
   way to stop them — WCAG 2.2.2 (Pause, Stop, Hide) applies to any motion that
   starts automatically and runs longer than five seconds.

   The CSS keeps doing the hover/focus pausing. This only adds the explicit
   control and remembers the visitor's choice for the session.
   ========================================================================== */

(function () {
  'use strict';

  if (window.__purelaneMarquee) return;
  window.__purelaneMarquee = true;

  var STORAGE_KEY = 'purelane:marquee-paused';

  var ICON_PAUSE =
    '<svg class="pl-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" aria-hidden="true" focusable="false"><path d="M9 5v14M15 5v14"/></svg>';
  var ICON_PLAY =
    '<svg class="pl-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false"><path d="M7 4.5 19 12 7 19.5Z"/></svg>';

  function readPreference() {
    try {
      return window.sessionStorage.getItem(STORAGE_KEY) === '1';
    } catch (e) {
      return false;
    }
  }

  function writePreference(paused) {
    try {
      window.sessionStorage.setItem(STORAGE_KEY, paused ? '1' : '0');
    } catch (e) {
      /* Private mode or storage disabled: the control still works, it just
         does not persist. Not worth failing over. */
    }
  }

  function apply(scope, paused) {
    var root = scope && scope.querySelectorAll ? scope : document;

    Array.prototype.forEach.call(root.querySelectorAll('[data-purelane-marquee]'), function (rail) {
      rail.setAttribute('data-paused', paused ? 'true' : 'false');
    });

    Array.prototype.forEach.call(root.querySelectorAll('[data-purelane-marquee-toggle]'), function (button) {
      var label = button.querySelector('[data-label]');
      var icon = button.querySelector('svg');

      if (label) label.textContent = paused ? 'Play' : 'Pause';
      if (icon) icon.outerHTML = paused ? ICON_PLAY : ICON_PAUSE;
    });
  }

  function onClick(event) {
    var button = event.target.closest('[data-purelane-marquee-toggle]');
    if (!button) return;

    var section = button.closest('.purelane-reviews') || document;
    var rail = section.querySelector('[data-purelane-marquee]');
    var paused = !(rail && rail.getAttribute('data-paused') === 'true');

    apply(section, paused);
    writePreference(paused);
  }

  function boot() {
    if (readPreference()) apply(document, true);
  }

  document.addEventListener('click', onClick);

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot, { once: true });
  } else {
    boot();
  }

  /* A section re-rendered in the theme editor comes back unpaused; restore. */
  document.addEventListener('shopify:section:load', function (event) {
    if (readPreference()) apply(event.target, true);
  });
})();
