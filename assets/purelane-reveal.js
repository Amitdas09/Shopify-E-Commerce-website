/* ==========================================================================
   Scroll reveal.

   Three fixes over the prototype's version:

   1. It queried .rv once, at load. Anything a merchant added afterwards in the
      theme editor stayed at opacity:0 forever — the section looked deleted.
      This re-scans on shopify:section:load and on any DOM insertion.

   2. The CSS hid .rv unconditionally. If the script 404'd or threw, the page
      rendered blank. The hidden state now lives behind .purelane-js, which is
      set here, so a script failure degrades to "no animation" rather than
      "no content".

   3. Elements already in view on first paint were still animated in, which
      pushed the largest contentful paint later than it needed to be. Anything
      inside the initial viewport is marked revealed immediately.
   ========================================================================== */

(function () {
  'use strict';

  /* Every Purelane section requests this file. The browser caches the fetch but
     still executes each tag, so without this guard a page with five sections
     would run five MutationObservers over the whole document. */
  if (window.__purelaneReveal) return;
  window.__purelaneReveal = true;

  var SELECTOR = '[data-purelane-reveal], .purelane .rv';
  var reduce = window.matchMedia('(prefers-reduced-motion: reduce)');
  var observer = null;

  document.documentElement.classList.add('purelane-js');

  function revealNow(el) {
    el.classList.add('in');
  }

  function getObserver() {
    if (observer) return observer;
    if (!('IntersectionObserver' in window)) return null;

    observer = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (entry) {
          if (!entry.isIntersecting) return;
          revealNow(entry.target);
          observer.unobserve(entry.target);
        });
      },
      { rootMargin: '0px 0px -12% 0px', threshold: 0.12 }
    );

    return observer;
  }

  function scan(root) {
    var scope = root && root.querySelectorAll ? root : document;
    var nodes = scope.querySelectorAll(SELECTOR);
    if (!nodes.length) return;

    var io = getObserver();
    var viewportHeight = window.innerHeight || document.documentElement.clientHeight;

    Array.prototype.forEach.call(nodes, function (el) {
      if (el.classList.contains('in') || el.dataset.plRevealBound === '1') return;
      el.dataset.plRevealBound = '1';

      if (!io || reduce.matches) {
        revealNow(el);
        return;
      }

      // Already on screen at first paint: show it without animating.
      if (el.getBoundingClientRect().top < viewportHeight * 0.9) {
        revealNow(el);
        return;
      }

      io.observe(el);
    });
  }

  function boot() {
    scan(document);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot, { once: true });
  } else {
    boot();
  }

  // Theme editor: a section that is added, moved or reconfigured is re-rendered.
  document.addEventListener('shopify:section:load', function (event) {
    scan(event.target);
  });

  // Anything else that injects markup (cart drawer, app blocks, paginated loads).
  if ('MutationObserver' in window) {
    var pending = false;
    new MutationObserver(function () {
      if (pending) return;
      pending = true;
      window.requestAnimationFrame(function () {
        pending = false;
        scan(document);
      });
    }).observe(document.documentElement, { childList: true, subtree: true });
  }

  reduce.addEventListener('change', function () {
    if (!reduce.matches) return;
    Array.prototype.forEach.call(document.querySelectorAll(SELECTOR), revealNow);
  });
})();
