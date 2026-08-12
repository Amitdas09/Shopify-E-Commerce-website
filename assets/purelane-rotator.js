/* ==========================================================================
   <purelane-rotator> — the product showcase in the proof section.

   The prototype's version read the caption text out of data-name and data-note
   attributes on each image and wrote it back with innerHTML. Two problems:
   innerHTML for text a merchant controls is an injection surface for no benefit,
   and the whole rotator was aria-hidden, so the product name and its benefit
   line — real copy — reached sighted visitors only.

   Here the caption is a polite live region updated with textContent, and the
   dots are real buttons, so the same information is available either way.
   ========================================================================== */

class PurelaneRotator extends HTMLElement {
  connectedCallback() {
    this.images = Array.from(this.querySelectorAll('.frame .pl-pimg'));
    this.dots = Array.from(this.querySelectorAll('[data-rot-goto]'));
    this.name = this.querySelector('[data-rot-name]');
    this.note = this.querySelector('[data-rot-note]');
    this.index = 0;
    this.timer = null;

    if (this.images.length < 2) return;

    this.reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
    this.interval = (parseFloat(this.dataset.interval) || 0) * 1000;

    /* Names come from the alt attribute — already present, already the thing a
       merchant edits when they rename a product. Benefit lines arrive as one
       JSON array, because image_tag cannot take a hyphenated argument name. */
    let notes = [];
    try {
      notes = JSON.parse(this.dataset.notes || '[]');
    } catch (e) {
      notes = [];
    }

    this.captions = this.images.map(function (img, i) {
      return {
        name: img.getAttribute('alt') || '',
        note: notes[i] || ''
      };
    });

    this.onDot = this.onDot.bind(this);
    this.onEnter = this.stop.bind(this);
    this.onLeave = this.resume.bind(this);

    this.dots.forEach((dot) => dot.addEventListener('click', this.onDot));
    this.addEventListener('mouseenter', this.onEnter);
    this.addEventListener('mouseleave', this.onLeave);
    this.addEventListener('focusin', this.onEnter);
    this.addEventListener('focusout', this.onLeave);

    if ('IntersectionObserver' in window) {
      this.observer = new IntersectionObserver(
        (entries) => {
          entries.forEach((entry) => (entry.isIntersecting ? this.resume() : this.stop()));
        },
        { threshold: 0.25 }
      );
      this.observer.observe(this);
    } else {
      this.resume();
    }
  }

  disconnectedCallback() {
    this.stop();
    if (this.observer) this.observer.disconnect();
    this.dots.forEach((dot) => dot.removeEventListener('click', this.onDot));
  }

  onDot(event) {
    const next = parseInt(event.currentTarget.dataset.rotGoto, 10);
    if (Number.isNaN(next)) return;
    this.goTo(next);
    this.stop();
    this.resume();
  }

  goTo(next) {
    const total = this.images.length;
    this.index = ((next % total) + total) % total;

    this.images.forEach((img, i) => img.classList.toggle('on', i === this.index));
    this.dots.forEach((dot, i) => {
      const active = i === this.index;
      dot.classList.toggle('on', active);
      if (active) dot.setAttribute('aria-current', 'true');
      else dot.removeAttribute('aria-current');
    });

    const caption = this.captions[this.index];
    if (caption) {
      if (this.name) this.name.textContent = caption.name;
      if (this.note) this.note.textContent = caption.note;
    }
  }

  resume() {
    if (this.timer || this.interval <= 0 || this.reduceMotion.matches) return;
    this.timer = window.setInterval(() => this.goTo(this.index + 1), this.interval);
  }

  stop() {
    if (!this.timer) return;
    window.clearInterval(this.timer);
    this.timer = null;
  }
}

if (!customElements.get('purelane-rotator')) {
  customElements.define('purelane-rotator', PurelaneRotator);
}
