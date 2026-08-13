/* ==========================================================================
   Page chrome: header scroll state, mobile drawer, progress rail.

   The prototype's rail did the same offsetTop walk per link per scroll frame
   that the scene picker did, with the same forced-layout cost. Both are
   IntersectionObserver here, and both survive the theme editor.
   ========================================================================== */

(function () {
  'use strict';

  if (window.__purelaneChrome) return;
  window.__purelaneChrome = true;

  /* ---------------------------------------------------------------- header */

  var header = null;
  var frame = null;

  function onScroll() {
    if (frame) return;
    frame = window.requestAnimationFrame(function () {
      frame = null;
      if (header) {
        var y = window.scrollY || window.pageYOffset;
        header.classList.toggle('up', y > 90);
      }
      /* The observer alone cannot drive the rail, because its fallback depends
         on scroll position rather than on an intersection changing. */
      syncRail();
    });
  }

  function bindHeader() {
    header = document.querySelector('[data-purelane-header]');
    if (header) onScroll();
  }

  /* ---------------------------------------------------------------- drawer */

  function onClick(event) {
    var toggle = event.target.closest('[data-purelane-menu]');

    if (toggle) {
      var drawer = document.getElementById(toggle.getAttribute('aria-controls'));
      if (!drawer) return;
      var open = drawer.classList.toggle('open');
      toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
      return;
    }

    /* Click outside closes it. A menu you cannot dismiss is worse than no menu. */
    var openDrawer = document.querySelector('.purelane-header .drawer.open');
    if (openDrawer && !event.target.closest('.purelane-header')) {
      openDrawer.classList.remove('open');
      var btn = document.querySelector('[data-purelane-menu]');
      if (btn) btn.setAttribute('aria-expanded', 'false');
    }
  }

  function onKey(event) {
    if (event.key !== 'Escape') return;
    var drawer = document.querySelector('.purelane-header .drawer.open');
    if (!drawer) return;
    drawer.classList.remove('open');
    var btn = document.querySelector('[data-purelane-menu]');
    if (btn) {
      btn.setAttribute('aria-expanded', 'false');
      btn.focus();
    }
  }

  /* ------------------------------------------------------------------ rail */

  var railObserver = null;
  var visible = new Map();

  function syncRail() {
    var links = Array.prototype.slice.call(document.querySelectorAll('.purelane-rail a'));
    if (!links.length) return;

    var bestId = null;
    var bestTop = Infinity;

    visible.forEach(function (_, el) {
      var top = el.getBoundingClientRect().top;
      if (top < bestTop) {
        bestTop = top;
        bestId = el.id;
      }
    });

    /* The observer band is the middle 10% of the viewport, which is precise
       while a section is crossing it and empty the rest of the time: at the
       top of the page, between two sections during a fast scroll, and any time
       a section is shorter than the band. The rail then had no dot lit at all,
       which reads as broken rather than as "between sections".

       So when nothing is in the band, fall back to the last section that has
       started — one rect read per link, only on that path. */
    if (!bestId) {
      var mid = window.innerHeight * 0.42;
      links.forEach(function (a) {
        var id = (a.getAttribute('href') || '').replace('#', '');
        var el = id && document.getElementById(id);
        if (el && el.getBoundingClientRect().top <= mid) bestId = id;
      });
      if (!bestId) {
        var first = (links[0].getAttribute('href') || '').replace('#', '');
        if (first) bestId = first;
      }
    }

    links.forEach(function (a) {
      var href = a.getAttribute('href') || '';
      var active = bestId && href === '#' + bestId;
      a.classList.toggle('on', !!active);
      if (active) a.setAttribute('aria-current', 'true');
      else a.removeAttribute('aria-current');
    });
  }

  function bindRail() {
    var links = Array.prototype.slice.call(document.querySelectorAll('.purelane-rail a'));
    if (!links.length || !('IntersectionObserver' in window)) return;

    if (!railObserver) {
      railObserver = new IntersectionObserver(
        function (entries) {
          entries.forEach(function (entry) {
            if (entry.isIntersecting) visible.set(entry.target, true);
            else visible.delete(entry.target);
          });
          syncRail();
        },
        { rootMargin: '-45% 0px -45% 0px' }
      );
    }

    links.forEach(function (a) {
      var id = (a.getAttribute('href') || '').replace('#', '');
      if (!id) return;
      var target = document.getElementById(id);
      if (!target || target.dataset.plRailBound === '1') return;
      target.dataset.plRailBound = '1';
      railObserver.observe(target);
    });
  }

  /* ------------------------------------------------------------------ boot */

  function boot() {
    bindHeader();
    bindRail();
  }

  window.addEventListener('scroll', onScroll, { passive: true });
  document.addEventListener('click', onClick);
  document.addEventListener('keydown', onKey);

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot, { once: true });
  } else {
    boot();
  }

  document.addEventListener('shopify:section:load', boot);
  document.addEventListener('shopify:section:unload', function () {
    visible.clear();
    boot();
  });
})();
