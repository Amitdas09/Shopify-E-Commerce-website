/* ==========================================================================
   Ambient backdrop: depth crossfade + parallax.

   The prototype's scene picker ran this on every scroll frame:

       for each zone:
         var top = 0, el = zone;
         while (el) { top += el.offsetTop; el = el.offsetParent; }

   Reading offsetTop forces a synchronous layout, and it did that once per
   ancestor per zone, per frame, for the life of the page. On a long homepage
   with thirteen zones that is the main-thread cost of the whole design.

   IntersectionObserver gives the same answer for free: the browser already
   knows what is on screen. Scroll work is now only the parallax transform,
   which is rAF-throttled and writes nothing but custom properties.
   ========================================================================== */

(function () {
  'use strict';

  if (window.__purelaneAmbient) return;
  window.__purelaneAmbient = true;

  var reduce = window.matchMedia('(prefers-reduced-motion: reduce)');
  var fine = window.matchMedia('(min-width: 1024px)');

  var stage = null;
  var scenes = [];
  var layers = [];
  var current = 0;
  var visible = new Map();
  var sceneObserver = null;
  var frame = null;
  var mouseX = 0;
  var mouseY = 0;

  var DEPTHS = [0.05, 0.09, 0.03, 0.02];

  function collect() {
    stage = document.querySelector('[data-purelane-ambient]');
    if (!stage) return false;

    scenes = Array.prototype.slice.call(stage.querySelectorAll('.scene'));
    layers = Array.prototype.slice.call(stage.querySelectorAll('.wl'));
    return true;
  }

  function setDepth(depth) {
    if (depth === current || !stage) return;
    current = depth;

    scenes.forEach(function (scene, i) {
      scene.classList.toggle('on', i + 1 === depth);
    });

    stage.setAttribute('data-d', String(depth));
  }

  /* Of everything currently on screen, the topmost element wins — that is the
     one the visitor is reading. */
  function resolveDepth() {
    var best = null;
    var bestTop = Infinity;

    visible.forEach(function (_, el) {
      var top = el.getBoundingClientRect().top;
      if (top < bestTop) {
        bestTop = top;
        best = el;
      }
    });

    if (!best) return;

    var depth = parseInt(best.getAttribute('data-purelane-scene'), 10);
    if (depth >= 1 && depth <= 4) setDepth(depth);
  }

  function observeZones(root) {
    if (!sceneObserver) return;
    var scope = root && root.querySelectorAll ? root : document;

    Array.prototype.forEach.call(scope.querySelectorAll('[data-purelane-scene]'), function (zone) {
      if (zone.dataset.plSceneBound === '1') return;
      zone.dataset.plSceneBound = '1';
      sceneObserver.observe(zone);
    });
  }

  function parallaxEnabled() {
    return stage && stage.dataset.parallax !== 'false' && !reduce.matches;
  }

  function render() {
    frame = null;
    if (!parallaxEnabled()) return;

    var y = window.scrollY || window.pageYOffset;

    for (var i = 0; i < layers.length; i++) {
      var d = DEPTHS[i] || 0.05;
      layers[i].style.setProperty('--px', (mouseX * d * 130).toFixed(1) + 'px');
      layers[i].style.setProperty('--py', (-y * d + mouseY * d * 90).toFixed(1) + 'px');
    }
  }

  function schedule() {
    if (frame) return;
    frame = window.requestAnimationFrame(render);
  }

  function onPointer(event) {
    mouseX = (event.clientX / window.innerWidth - 0.5) * 2;
    mouseY = (event.clientY / window.innerHeight - 0.5) * 2;
    schedule();
  }

  function clearParallax() {
    layers.forEach(function (layer) {
      layer.style.removeProperty('--px');
      layer.style.removeProperty('--py');
    });
  }

  function boot() {
    if (!collect()) return;

    if ('IntersectionObserver' in window) {
      sceneObserver = new IntersectionObserver(
        function (entries) {
          entries.forEach(function (entry) {
            if (entry.isIntersecting) visible.set(entry.target, true);
            else visible.delete(entry.target);
          });
          resolveDepth();
        },
        /* A band across the middle of the viewport, so the depth changes when a
           section owns the screen rather than when it first peeks in. */
        { rootMargin: '-45% 0px -45% 0px' }
      );
    }

    observeZones(document);

    window.addEventListener('scroll', schedule, { passive: true });
    window.addEventListener('resize', schedule);

    if (fine.matches) {
      window.addEventListener('mousemove', onPointer, { passive: true });
    }

    reduce.addEventListener('change', function () {
      if (reduce.matches) clearParallax();
      else schedule();
    });

    schedule();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot, { once: true });
  } else {
    boot();
  }

  /* Theme editor: sections come and go. Re-resolve both ends of the link —
     the backdrop itself may have been added, and new zones may have appeared. */
  document.addEventListener('shopify:section:load', function (event) {
    if (!stage || !document.body.contains(stage)) {
      visible.clear();
      current = 0;
      boot();
      return;
    }
    observeZones(event.target);
    resolveDepth();
  });

  document.addEventListener('shopify:section:unload', function (event) {
    Array.prototype.forEach.call(event.target.querySelectorAll('[data-purelane-scene]'), function (zone) {
      visible.delete(zone);
      if (sceneObserver) sceneObserver.unobserve(zone);
    });
    resolveDepth();
  });
})();
