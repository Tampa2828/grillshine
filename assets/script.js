// year
document.getElementById('year').textContent = new Date().getFullYear();

// elements
const toggle = document.getElementById('menuToggle');
const drawer = document.getElementById('siteNav');
const closeBtn = document.getElementById('closeMenu');
const backdrop = document.getElementById('backdrop');

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

// close when clicking a nav link
drawer.querySelectorAll('.nav-link').forEach(a => a.addEventListener('click', closeDrawer));
