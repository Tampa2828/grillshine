// ==============================
// GrillShine - Site Script
// ==============================

// --- Year (guard in case element is missing)
const yearEl = document.getElementById('year');
if (yearEl) yearEl.textContent = new Date().getFullYear();

// --- Elements
const toggle   = document.getElementById('menuToggle');
const drawer   = document.getElementById('siteNav');
const closeBtn = document.getElementById('closeMenu');
const backdrop = document.getElementById('backdrop');

// --- Motion preference
const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

// --- Helpers
function headerOffsetPx() {
  const header = document.querySelector('.site-header');
  return header ? header.offsetHeight + 12 : 0; // add a little breathing room
}
function smoothScrollToEl(el) {
  const y = el.getBoundingClientRect().top + window.pageYOffset - headerOffsetPx();
  window.scrollTo({ top: y, behavior: prefersReducedMotion ? 'auto' : 'smooth' });
}

// --- Focus management for the drawer (accessibility)
let lastFocusedBeforeDrawer = null;
function getFocusable(container) {
  if (!container) return [];
  return Array.from(
    container.querySelectorAll(
      'a[href], button:not([disabled]), input, select, textarea, [tabindex]:not([tabindex="-1"])'
    )
  ).filter(el => !el.hasAttribute('disabled') && !el.getAttribute('aria-hidden'));
}
function trapTabKey(e) {
  if (!drawer?.classList.contains('open')) return;
  const focusables = getFocusable(drawer);
  if (focusables.length === 0) return;

  const first = focusables[0];
  const last  = focusables[focusables.length - 1];

  if (e.key === 'Tab') {
    if (e.shiftKey && document.activeElement === first) {
      e.preventDefault();
      last.focus();
    } else if (!e.shiftKey && document.activeElement === last) {
      e.preventDefault();
      first.focus();
    }
  }
}

// --- Drawer open/close
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

  // Move focus into the drawer
  const first = getFocusable(drawer)[0];
  if (first) first.focus();

  // Enable tab trapping
  document.addEventListener('keydown', trapTabKey);
}

function closeDrawer() {
  if (!drawer) return;

  drawer.classList.remove('open');
  if (backdrop) {
    backdrop.classList.remove('show');
    // hide backdrop after transition
    setTimeout(() => { if (!drawer.classList.contains('open')) backdrop.hidden = true; }, 200);
  }
  if (toggle) toggle.setAttribute('aria-expanded', 'false');
  drawer.setAttribute('aria-hidden', 'true');
  document.body.style.overflow = '';

  // Return focus to the toggle for accessibility
  if (lastFocusedBeforeDrawer && typeof lastFocusedBeforeDrawer.focus === 'function') {
    lastFocusedBeforeDrawer.focus();
  } else if (toggle) {
    toggle.focus();
  }

  // Disable tab trapping
  document.removeEventListener('keydown', trapTabKey);
}

// --- Toggle button
if (toggle) {
  toggle.addEventListener('click', () => {
    if (drawer?.classList.contains('open')) { closeDrawer(); } else { openDrawer(); }
  });
}

// --- Close via ✕
if (closeBtn) closeBtn.addEventListener('click', closeDrawer);

// --- Close when clicking outside
if (backdrop) backdrop.addEventListener('click', closeDrawer);

// --- Close on ESC
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape' && drawer?.classList.contains('open')) closeDrawer();
});

// --- Drawer links: close + smooth scroll with sticky-header offset
if (drawer) {
  drawer.querySelectorAll('a.nav-link[href^="#"]').forEach((a) => {
    a.addEventListener('click', (e) => {
      const targetSel = a.getAttribute('href'); // e.g. "#services"
      const target = targetSel ? document.querySelector(targetSel) : null;
      if (!target) return;
      e.preventDefault();
      closeDrawer();
      // let the drawer start closing before scrolling
      setTimeout(() => smoothScrollToEl(target), 150);
    });
  });
}

// --- Global smooth scrolling for any in-page link not inside the drawer
document.querySelectorAll('a[href^="#"]').forEach((anchor) => {
  // Skip links managed by the drawer handler above
  if (anchor.closest('#siteNav')) return;

  anchor.addEventListener('click', (e) => {
    const hash = anchor.getAttribute('href');
    if (!hash || hash === '#') return;
    const target = document.querySelector(hash);
    if (!target) return;
    e.preventDefault();
    smoothScrollToEl(target);
  });
});

// --- If page loads with a hash, adjust to account for sticky header
function adjustForInitialHash() {
  if (location.hash) {
    const target = document.querySelector(location.hash);
    if (target) {
      // small delay to ensure layout is ready, then adjust
      setTimeout(() => smoothScrollToEl(target), 50);
    }
  }
}
window.addEventListener('load', adjustForInitialHash);

// --- If hash changes via back/forward, adjust too
window.addEventListener('hashchange', adjustForInitialHash);

// --- If resized (e.g., rotation), close drawer to avoid odd states
window.addEventListener('resize', () => {
  if (drawer?.classList.contains('open')) closeDrawer();
});
