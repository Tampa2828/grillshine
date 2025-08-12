// ==============================
// GrillShine — Site Script
// ==============================

// Year (guard in case element is missing)
const yearEl = document.getElementById('year');
if (yearEl) yearEl.textContent = new Date().getFullYear();

// Elements
const toggle   = document.getElementById('menuToggle');
const drawer   = document.getElementById('siteNav');
const closeBtn = document.getElementById('closeMenu');
const backdrop = document.getElementById('backdrop');

// Motion preference
const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

// Helpers
function headerOffsetPx() {
  const header = document.querySelector('.site-header');
  return header ? header.offsetHeight + 12 : 0; // a little breathing room
}
function smoothScrollToEl(el) {
  const y = el.getBoundingClientRect().top + window.pageYOffset - headerOffsetPx();
  window.scrollTo({ top: y, behavior: prefersReducedMotion ? 'auto' : 'smooth' });
}

// Focus management for the drawer (accessibility)
let lastFocusedBeforeDrawer = null;
function getFocusable(container) {
  if (!container) return [];
  return Array.from(
    container.querySelectorAll(
      'a[href], button:not([disabled]), textarea, input, select, [tabindex]:not([tabindex="-1"])'
    )
  ).filter(el => !el.hasAttribute('disabled') && el.getAttribute('aria-hidden') !== 'true');
}
function trapTabKey(e) {
  if (!drawer || !drawer.classList.contains('open')) return;
  if (e.key !== 'Tab') return;

  const focusables = getFocusable(drawer);
  if (focusables.length === 0) return;

  const first = focusables[0];
  const last  = focusables[focusables.length - 1];

  if (e.shiftKey && document.activeElement === first) {
    e.preventDefault(); last.focus();
  } else if (!e.shiftKey && document.activeElement === last) {
    e.preventDefault(); first.focus();
  }
}

// Drawer open/close
const originalBodyOverflow = document.body.style.overflow || '';

function openDrawer() {
  if (!drawer) return;
  lastFocusedBeforeDrawer = document.activeElement;

  drawer.classList.add('open');
  if (backdrop) {
    backdrop.hidden = false;
    requestAnimationFrame(() => backdrop.classList.add('show'));
  }
  if (toggle) toggle.setAttribute('aria-expanded', 'true');
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
    setTimeout(() => { if (!drawer.classList.contains('open')) backdrop.hidden = true; }, 200);
  }
  if (toggle) toggle.setAttribute('aria-expanded', 'false');
  drawer.setAttribute('aria-hidden', 'true');
  document.body.style.overflow = originalBodyOverflow;

  if (lastFocusedBeforeDrawer && typeof lastFocusedBeforeDrawer.focus === 'function') {
    lastFocusedBeforeDrawer.focus();
  } else if (toggle) {
    toggle.focus();
  }

  document.removeEventListener('keydown', trapTabKey);
}

// Toggle button
if (toggle) {
  toggle.addEventListener('click', () => {
    if (drawer?.classList.contains('open')) closeDrawer();
    else openDrawer();
  });
}

// Close via ✕
if (closeBtn) closeBtn.addEventListener('click', closeDrawer);

// Close when clicking outside
if (backdrop) backdrop.addEventListener('click', closeDrawer);

// Close on ESC
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape' && drawer?.classList.contains('open')) closeDrawer();
});

// Drawer links: close + smooth scroll with sticky-header offset
if (drawer) {
  drawer.querySelectorAll('a.nav-link[href^="#"]').forEach((a) => {
    a.addEventListener('click', (e) => {
      const targetSel = a.getAttribute('href'); // e.g. "#services"
      const target = targetSel ? document.querySelector(targetSel) : null;
      if (!target) return;
      e.preventDefault();
      closeDrawer();
      setTimeout(() => smoothScrollToEl(target), 150);
    });
  });
}

// Global smooth scrolling for any in-page link not inside the drawer
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

// Handle initial hash & history changes (sticky header offset)
function adjustForHash() {
  if (!location.hash) return;
  const target = document.querySelector(location.hash);
  if (!target) return;
  setTimeout(() => smoothScrollToEl(target), 50); // ensure layout is ready
}
window.addEventListener('load', adjustForHash);
window.addEventListener('hashchange', adjustForHash);

// Close drawer on resize (debounced) to avoid odd states
let resizeTimer = null;
window.addEventListener('resize', () => {
  if (!drawer?.classList.contains('open')) return;
  clearTimeout(resizeTimer);
  resizeTimer = setTimeout(closeDrawer, 120);
});
