// year
document.getElementById('year').textContent = new Date().getFullYear();

// hamburger
const toggle = document.getElementById('menuToggle');
const drawer = document.getElementById('siteNav');
toggle.addEventListener('click', () => {
  const open = drawer.classList.toggle('open');
  toggle.setAttribute('aria-expanded', String(open));
  drawer.setAttribute('aria-hidden', String(!open));
});
drawer.querySelectorAll('.nav-link').forEach(a => a.addEventListener('click', () => {
  drawer.classList.remove('open');
  toggle.setAttribute('aria-expanded', 'false');
  drawer.setAttribute('aria-hidden', 'true');
}));

// simple form validation + placeholder “submit”
const form = document.getElementById('quoteForm');
const msg = document.getElementById('formMsg');
const errors = {
  name: document.querySelector('.error[data-for="name"]'),
  email: document.querySelector('.error[data-for="email"]'),
};

function validate() {
  let ok = true;
  // name
  if (!form.name.value.trim()) {
    errors.name.textContent = 'Please enter your name.';
    ok = false;
  } else {
    errors.name.textContent = '';
  }
  // email
  const email = form.email.value.trim();
  const emailOk = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
  if (!emailOk) {
    errors.email.textContent = 'Please enter a valid email.';
    ok = false;
  } else {
    errors.email.textContent = '';
  }
  return ok;
}

form.addEventListener('submit', (e) => {
  e.preventDefault();
  msg.textContent = '';
  if (!validate()) return;

  // Placeholder behavior: open mail client prefilled (works anywhere, no backend needed).
  const subject = encodeURIComponent('GrillShine Quote Request');
  const body = encodeURIComponent(
    `Name: ${form.name.value}\nEmail: ${form.email.value}\nPhone: ${form.phone.value || ''}\n\nMessage: Please send me a quote.`
  );
  window.location.href = `mailto:hello@grillshine.com?subject=${subject}&body=${body}`;

  // User feedback
  msg.textContent = 'Opening your email app… If nothing opens, email us at hello@grillshine.com.';
});
