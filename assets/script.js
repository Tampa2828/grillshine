// ==============================
// GrillShine — robust drawer (Home works across pages; X/ESC/backdrop close)
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
      )).filter(el =>
        !el.hasAttribute('disabled') &&
        el.getAttribute('aria-hidden') !== 'true' &&
        el.offsetParent !== null
      )
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

// Path helpers
function normPath(p) {
  return p.replace(/\/index\.html$/i, '/').replace(/\/+$/, '/') || '/';
}
function isSameDocument(url) {
  try {
    const u = new URL(url, location.href);
    return u.origin === location.origin && normPath(u.pathname) === normPath(location.pathname);
  } catch { return false; }
}

// Open / close
const originalOverflow = document.body.style.overflow || '';

function openDrawer() {
  if (!drawer) return;
  lastFocusedBeforeDrawer = document.activeElement;
  drawer.classList.add('open');

  if (backdrop) {
    backdrop.hidden = false;
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
toggle?.addEventListener('click', () =>
  drawer?.classList.contains('open') ? closeDrawer() : openDrawer()
);
closeBtn?.addEventListener('click', (e) => { e.preventDefault(); e.stopPropagation(); closeDrawer(); });

// Close only when clicking the backdrop itself
backdrop?.addEventListener('pointerdown', (e) => {
  if (e.target === backdrop) closeDrawer();
});

// ESC closes
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape' && drawer?.classList.contains('open')) closeDrawer();
});

// Drawer link handling (anchors + cross-page)
drawer?.addEventListener('click', (e) => {
  e.stopPropagation();
  const a = e.target.closest('a');
  if (!a || !drawer.contains(a)) return;

  const href = a.getAttribute('href') || '';
  if (!href) return;

  const targetBlank = a.getAttribute('target') === '_blank';
  const modified = e.metaKey || e.ctrlKey || e.shiftKey || e.altKey || e.button === 1;
  if (targetBlank || modified) return;

  // 1) Pure hash on current page
  if (href.startsWith('#')) {
    e.preventDefault();
    const selector = href;
    closeDrawer();
    requestAnimationFrame(() => {
      const el = document.querySelector(selector);
      if (el) smoothScrollToEl(el);
      else window.location.hash = selector;
    });
    return;
  }

  // 2) Same document link (incl. index.html#... when already on index)
  if (isSameDocument(href)) {
    const u = new URL(href, location.href);
    if (u.hash) {
      e.preventDefault();
      closeDrawer();
      requestAnimationFrame(() => {
        const el = document.querySelector(u.hash);
        if (el) smoothScrollToEl(el);
        else window.location.hash = u.hash;
      });
      return;
    }
    // no hash: fall through to navigate (rare)
  }

  // 3) Different page: navigate
  e.preventDefault();
  closeDrawer();
  setTimeout(() => { window.location.assign(href); }, 100);
});

// Prevent pointerdown inside drawer from triggering outside logic
drawer?.addEventListener('pointerdown', (e) => e.stopPropagation());

// Smooth scrolling for in-page links OUTSIDE the drawer
document.querySelectorAll('a[href^="#"]').forEach((anchor) => {
  if (anchor.closest('#siteNav')) return;
  anchor.addEventListener('click', (e) => {
    const hash = anchor.getAttribute('href');
    if (!hash || hash === '#') return;
    const target = document.querySelector(hash);
    if (target) { e.preventDefault(); smoothScrollToEl(target); }
  });
});

// Respect sticky header on initial hash loads & hash changes
function adjustForHash() {
  if (!location.hash) return;
  const tgt = document.querySelector(location.hash);
  if (tgt) setTimeout(() => smoothScrollToEl(tgt), 100);
}
window.addEventListener('load', adjustForHash);
window.addEventListener('hashchange', adjustForHash);

// Safety: close on resize
let resizeTimer = null;
window.addEventListener('resize', () => {
  if (!drawer?.classList.contains('open')) return;
  clearTimeout(resizeTimer);
  resizeTimer = setTimeout(closeDrawer, 120);
});
