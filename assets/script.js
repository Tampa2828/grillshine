// year (guard in case element is missing)
const yearEl = document.getElementById('year');
if (yearEl) yearEl.textContent = new Date().getFullYear();

// elements
const toggle   = document.getElementById('menuToggle');
const drawer   = document.getElementById('siteNav');
const closeBtn = document.getElementById('closeMenu');
const backdrop = document.getElementById('backdrop');

// helpers
function headerOffsetPx() {
  const header = document.querySelector('.site-header');
  return header ? header.offsetHeight + 12 : 0; // add a little breathing room
}
function smoothScrollToEl(el) {
  const y = el.getBoundingClientRect().top + window.pageYOffset - headerOffsetPx();
  window.scrollTo({ top: y, behavior: 'smooth' });
}

function openDrawer() {
  drawer.classList.add('open');
  backdrop.hidden = false;
  requestAnimationFrame(() => backdrop.classList.add('show'));
  toggle.setAttribute('aria-expanded', 'true');
  drawer.setAttribute('aria-hidden', 'false');
  document.body.style.overflow = 'hidden';
}

function closeDrawer() {
  drawer.classList.remove('open');
  backdrop.classList.remove('show');
  toggle.setAttribute('aria-expanded', 'false');
  drawer.setAttribute('aria-hidden', 'true');
  document.body.style.overflow = '';
  // hide backdrop after transition
  setTimeout(() => { if (!drawer.classList.contains('open')) backdrop.hidden = true; }, 200);
}

// open/close via hamburger
toggle.addEventListener('click', () => {
  if (drawer.classList.contains('open')) { closeDrawer(); } else { openDrawer(); }
});

// close via ✕
closeBtn.addEventListener('click', closeDrawer);

// close when clicking outside
backdrop.addEventListener('click', closeDrawer);

// close on ESC
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape' && drawer.classList.contains('open')) closeDrawer();
});

// close when clicking a nav link AND smooth-scroll to section
drawer.querySelectorAll('a.nav-link[href^="#"]').forEach((a) => {
  a.addEventListener('click', (e) => {
    const targetSel = a.getAttribute('href'); // e.g. "#services"
    const target = document.querySelector(targetSel);
    if (!target) return;
    e.preventDefault();
    closeDrawer();
    // let the drawer start closing before scrolling
    setTimeout(() => smoothScrollToEl(target), 150);
  });
});
