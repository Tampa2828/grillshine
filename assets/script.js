// --- Year (guard in case element is missing)
const yearEl = document.getElementById('year');
if (yearEl) yearEl.textContent = new Date().getFullYear();

// --- Elements
const toggle   = document.getElementById('menuToggle');
const drawer   = document.getElementById('siteNav');
const closeBtn = document.getElementById('closeMenu');
const backdrop = document.getElementById('backdrop');

// --- Helpers
function headerOffsetPx() {
  const header = document.querySelector('.site-header');
  return header ? header.offsetHeight + 12 : 0; // add a little breathing room
}
function smoothScrollToEl(el) {
  const y = el.getBoundingClientRect().top + window.pageYOffset - headerOffsetPx();
  window.scrollTo({ top: y, behavior: 'smooth' });
}

// --- Drawer open/close
function openDrawer() {
  if (!drawer) return;
  drawer.classList.add('open');
  if (backdrop) {
    backdrop.hidden = false;
    requestAnimationFrame(() => backdrop.classList.add('show'));
  }
  if (toggle) toggle.setAttribute('aria-expanded', 'true');
  drawer.setAttribute('aria-hidden', 'false');
  document.body.style.overflow = 'hidden';
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
  // Skip links that are managed by the drawer handler above
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
window.addEventListener('load', () => {
  if (location.hash) {
    const target = document.querySelector(location.hash);
    if (target) {
      // small delay to ensure layout is ready, then adjust
      setTimeout(() => smoothScrollToEl(target), 50);
    }
  }
});
