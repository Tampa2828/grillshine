// ==============================
// GrillShine — Drawer nav (stable open; closes only via X/backdrop/ESC; links work)
// ==============================

// Footer year
const yearEl = document.getElementById('year');
if (yearEl) yearEl.textContent = new Date().getFullYear();

// Elements
const toggle   = document.getElementById('menuToggle');
const drawer   = document.getElementById('siteNav');
const closeBtn = document.getElementById('closeMenu');
const backdrop = document.getElementById('backdrop');

const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

// Sticky-header aware smooth scroll
function headerOffsetPx() {
  const header = document.querySelector('.site-header');
  return header ? header.offsetHeight + 12 : 0;
}
function smoothScrollToEl(el) {
  const y = el.getBoundingClientRect().top + window.pageYOffset - headerOffsetPx();
  window.scrollTo({ top: y, behavior: prefersReducedMotion ? 'auto' : 'smooth' });
}

// Focus trap helpers
let lastFocusedBeforeDrawer = null;
function getFocusable(container) {
  return container
    ? Array.from(container.querySelectorAll(
        'a[href], button:not([disabled]), textarea, input, select, [tabindex]:not([tabindex="-1"])'
      )).filter(el => !el.hasAttribute('disabled') && el.getAttribute('aria-hidden') !== 'true')
    : [];
}
function trapTabKey(e) {
  if (!drawer?.classList.contains('open') || e.key !== 'Tab') return;
  const focusables = getFocusable(drawer);
  if (!focusables.length) return;
  const first = focusables[0];
  const last  = focusables[focusables.length - 1];
  if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
  else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
}

// Open / close
const originalOverflow = document.body.style.overflow || '';

function openDrawer() {
  if (!drawer) return;
  lastFocusedBeforeDrawer = document.activeElement;
  drawer.classList.add('open');

  if (backdrop) {
    backdrop.hidden = false;
    // ensure new frame so transition can run
    requestAnimationFrame(() => backdrop.classList.add('show'));
  }

  toggle?.setAttribute('aria-expanded', 'true');
  drawer.setAttribute('aria-hidden', 'false');
  document.body.style.overflow = 'hidden';

  const first = getFocusable(drawer)[0];
  if (first) first.focus();

  document.addEventListener('keydown', trapTabKey);
}

function closeDrawer() {
  if (!drawer) return;
  drawer.classList.remove('open');

  if (backdrop) {
    backdrop.classList.remove('show');
    // hide node after fade
    setTimeout(() => { if (!drawer.classList.contains('open')) backdrop.hidden = true; }, 200);
  }

  toggle?.setAttribute('aria-expanded', 'false');
  drawer.setAttribute('aria-hidden', 'true');
  document.body.style.overflow = originalOverflow;

  if (lastFocusedBeforeDrawer && typeof lastFocusedBeforeDrawer.focus === 'function') {
    lastFocusedBeforeDrawer.focus();
  } else {
    toggle?.focus();
  }

  document.removeEventListener('keydown', trapTabKey);
}

// Toggle & close controls
toggle?.addEventListener('click', () => {
  drawer?.classList.contains('open') ? closeDrawer() : openDrawer();
});
closeBtn?.addEventListener('click', closeDrawer);

// IMPORTANT: use pointerdown on the BACKDROP only
// (prevents weird bubbling when mousedown/up start/end on different elements)
backdrop?.addEventListener('pointerdown', (e) => {
  if (e.target === backdrop) closeDrawer();
});

// ESC closes
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape' && drawer?.classList.contains('open')) closeDrawer();
});

// Keep clicks inside the drawer from ever reaching the backdrop/document
drawer?.addEventListener('click', (e) => e.stopPropagation());
drawer?.addEventListener('pointerdown', (e) => e.stopPropagation());

// Drawer link handling (anchors + page nav)
if (drawer) {
  drawer.addEventListener('click', (e) => {
    const a = e.target.closest('a');
    if (!a || !drawer.contains(a)) return;

    // we already stopped propagation above; this is just for safety
    e.stopPropagation();

    const href = a.getAttribute('href') || '';
    const targetBlank = a.getAttribute('target') === '_blank';
    const modified = e.metaKey || e.ctrlKey || e.shiftKey || e.altKey || e.button === 1;

    // New tab / modified click → let browser handle
    if (!href || targetBlank || modified) return;

    // Same-page anchors (e.g. #services or index.html#services)
    const isSamePageHash = href.startsWith('#') || /^index\.html#/.test(href);
    if (isSamePageHash) {
      e.preventDefault();
      const selector = href.startsWith('#') ? href : href.replace(/^index\.html/, '');
      closeDrawer();
      // Scroll after the drawer starts closing
      requestAnimationFrame(() => {
        const el = document.querySelector(selector);
        if (el) smoothScrollToEl(el);
        else window.location.hash = selector; // fallback
      });
      return;
    }

    // Cross-page links
    e.preventDefault();
    const url = href;
    closeDrawer();
    // Let the close animation begin, then navigate
    setTimeout(() => { window.location.assign(url); }, 100);
  });
}

// Smooth scrolling for in-page links OUTSIDE the drawer
document.querySelectorAll('a[href^="#"]').forEach((anchor) => {
  if (anchor.closest('#siteNav')) return; // drawer links handled above
  anchor.addEventListener('click', (e) => {
    const hash = anchor.getAttribute('href');
    if (!hash || hash === '#') return;
    const target = document.querySelector(hash);
    if (!target) return;
    e.preventDefault();
    smoothScrollToEl(target);
  });
});

// Respect sticky header on initial hash loads & hash changes
function adjustForHash() {
  if (!location.hash) return;
  const tgt = document.querySelector(location.hash);
  if (!tgt) return;
  setTimeout(() => smoothScrollToEl(tgt), 50);
}
window.addEventListener('load', adjustForHash);
window.addEventListener('hashchange', adjustForHash);

// Close drawer on resize (safety)
let resizeTimer = null;
window.addEventListener('resize', () => {
  if (!drawer?.classList.contains('open')) return;
  clearTimeout(resizeTimer);
  resizeTimer = setTimeout(closeDrawer, 120);
});
