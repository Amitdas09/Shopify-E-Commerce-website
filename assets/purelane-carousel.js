/* ==========================================================================
   <purelane-carousel> — the hero product stage.

   Why a custom element rather than the prototype's IIFE:

   The prototype grabbed #hstage and #hdots by ID inside one script that ran
   once on DOMContentLoaded. In the theme editor that breaks three ways:
     1. Two hero sections on a page = duplicate IDs, and the second one is
        silently controlled by the first one's handler.
     2. Adding or reordering a section re-renders its HTML, and the old
        listeners point at detached nodes, so the carousel dies.
     3. Removing the section leaves an interval running forever.

   A custom element upgrades itself whenever its markup enters the DOM,
   including on shopify:section:load, and disconnectedCallback guarantees the
   timer is cleared. No IDs, no global state, any number of instances.
   ========================================================================== */

class PurelaneCarousel extends HTMLElement {
  connectedCallback() {
    this.slides = Array.from(this.querySelectorAll('.hslide'));
    this.dots = Array.from(this.querySelectorAll('[data-purelane-goto]'));
    this.toggle = this.querySelector('[data-purelane-toggle]');
    this.index = 0;
    this.timer = null;
    this.paused = false;

    if (this.slides.length < 2) return;

    this.reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
    this.interval = (parseFloat(this.dataset.autoplay) || 0) * 1000;

    this.onDot = this.onDot.bind(this);
    this.onToggle = this.onToggle.bind(this);
    this.onEnter = this.stop.bind(this);
    this.onLeave = this.resume.bind(this);
    this.onMotionChange = this.onMotionChange.bind(this);

    this.dots.forEach((dot) => dot.addEventListener('click', this.onDot));
    if (this.toggle) this.toggle.addEventListener('click', this.onToggle);

    /* Hover pause is a nicety; focus pause is a requirement — a keyboard user
       tabbing through the dots must not have the stage move under them. */
    this.addEventListener('mouseenter', this.onEnter);
    this.addEventListener('mouseleave', this.onLeave);
    this.addEventListener('focusin', this.onEnter);
    this.addEventListener('focusout', this.onLeave);

    this.reduceMotion.addEventListener('change', this.onMotionChange);

    /* Only run while actually on screen. An offscreen carousel repainting every
       four seconds is wasted main-thread time and battery. */
    if ('IntersectionObserver' in window) {
      this.observer = new IntersectionObserver(
        (entries) => {
          entries.forEach((entry) => (entry.isIntersecting ? this.resume() : this.stop()));
        },
        { threshold: 0.2 }
      );
      this.observer.observe(this);
    } else {
      this.resume();
    }
  }

  disconnectedCallback() {
    this.stop();
    if (this.observer) this.observer.disconnect();
    if (this.reduceMotion) this.reduceMotion.removeEventListener('change', this.onMotionChange);
    this.dots.forEach((dot) => dot.removeEventListener('click', this.onDot));
    if (this.toggle) this.toggle.removeEventListener('click', this.onToggle);
  }

  get canAutoplay() {
    return this.interval > 0 && !this.reduceMotion.matches && !this.paused;
  }

  onDot(event) {
    const next = parseInt(event.currentTarget.dataset.purelaneGoto, 10);
    if (Number.isNaN(next)) return;
    this.goTo(next);
    /* An explicit choice should hold for a beat rather than being overwritten
       by the timer a moment later. */
    this.restart();
  }

  onToggle() {
    this.paused = !this.paused;
    if (this.paused) {
      this.stop();
    } else {
      this.resume();
    }
    if (this.toggle) {
      this.toggle.setAttribute(
        'aria-label',
        this.paused ? 'Play the product slideshow' : 'Pause the product slideshow'
      );
      this.toggle.innerHTML = this.paused ? PurelaneCarousel.PLAY : PurelaneCarousel.PAUSE;
    }
  }

  onMotionChange() {
    if (this.reduceMotion.matches) this.stop();
    else this.resume();
  }

  goTo(next) {
    const total = this.slides.length;
    this.index = ((next % total) + total) % total;

    this.slides.forEach((slide, i) => slide.classList.toggle('on', i === this.index));
    this.dots.forEach((dot, i) => {
      const active = i === this.index;
      dot.classList.toggle('on', active);
      if (active) dot.setAttribute('aria-current', 'true');
      else dot.removeAttribute('aria-current');
    });
  }

  resume() {
    if (this.timer || !this.canAutoplay) return;
    this.timer = window.setInterval(() => this.goTo(this.index + 1), this.interval);
  }

  stop() {
    if (!this.timer) return;
    window.clearInterval(this.timer);
    this.timer = null;
  }

  restart() {
    this.stop();
    this.resume();
  }
}

PurelaneCarousel.PAUSE =
  '<svg class="pl-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" aria-hidden="true" focusable="false"><path d="M9 5v14M15 5v14"/></svg>';
PurelaneCarousel.PLAY =
  '<svg class="pl-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false"><path d="M7 4.5 19 12 7 19.5Z"/></svg>';

if (!customElements.get('purelane-carousel')) {
  customElements.define('purelane-carousel', PurelaneCarousel);
}

/* ==========================================================================
   Hero product parallax.

   Lives with the hero rather than with the backdrop, because it must still
   work when a merchant has not added the backdrop section. The prototype ran
   this inside the same scroll handler as the scene picker, so removing the
   background would have taken the hero motion with it.
   ========================================================================== */

(function () {
  'use strict';

  if (window.__purelaneHeroParallax) return;
  window.__purelaneHeroParallax = true;

  var reduce = window.matchMedia('(prefers-reduced-motion: reduce)');
  var fine = window.matchMedia('(min-width: 1024px)');
  var targets = [];
  var frame = null;
  var mouseX = 0;
  var mouseY = 0;

  function reset(el) {
    el.style.transform = '';
    el.style.opacity = '';
  }

  function render() {
    frame = null;
    if (reduce.matches) return;

    var y = window.scrollY || window.pageYOffset;

    targets.forEach(function (el) {
      if (!el.isConnected) return;

      /* Only animate while the hero is anywhere near the viewport. Past that
         the element is off screen and the work is invisible. */
      var rect = el.getBoundingClientRect();
      if (rect.bottom < -200 || rect.top > window.innerHeight + 200) return;

      var f = Math.min(y / 700, 1);
      var x = mouseX * -16;
      var yShift = -f * 54 + mouseY * -10;

      el.style.transform =
        'translate3d(' + x.toFixed(2) + 'px,' + yShift.toFixed(2) + 'px,0) scale(' + (1 - f * 0.06).toFixed(3) + ')';
      el.style.opacity = (1 - f * 0.55).toFixed(3);
    });
  }

  function onPointer(event) {
    mouseX = (event.clientX / window.innerWidth - 0.5) * 2;
    mouseY = (event.clientY / window.innerHeight - 0.5) * 2;
    schedule();
  }

  function schedule() {
    if (frame) return;
    frame = window.requestAnimationFrame(render);
  }

  function scan() {
    targets = Array.prototype.slice.call(document.querySelectorAll('[data-purelane-parallax]'));
    if (targets.length) schedule();
  }

  function boot() {
    scan();
    window.addEventListener('scroll', schedule, { passive: true });
    window.addEventListener('resize', schedule);

    if (fine.matches && !reduce.matches) {
      window.addEventListener('mousemove', onPointer, { passive: true });
    }

    reduce.addEventListener('change', function () {
      if (reduce.matches) targets.forEach(reset);
      else schedule();
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot, { once: true });
  } else {
    boot();
  }

  document.addEventListener('shopify:section:load', scan);
  document.addEventListener('shopify:section:unload', scan);
})();
