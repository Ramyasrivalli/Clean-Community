/* Small accessibility and usability enhancements; all core actions work without JavaScript. */
document.addEventListener('DOMContentLoaded', () => {
  const navToggle = document.querySelector('[data-nav-toggle]');
  const nav = document.querySelector('[data-nav]');
  if (navToggle && nav) {
    navToggle.addEventListener('click', () => {
      const open = nav.classList.toggle('is-open');
      navToggle.setAttribute('aria-expanded', open);
      navToggle.innerHTML = `<i class="fa-solid ${open ? 'fa-xmark' : 'fa-bars'}"></i>`;
    });
  }

  document.querySelectorAll('[data-dismiss-flash]').forEach((button) => {
    button.addEventListener('click', () => button.parentElement.remove());
  });

  document.querySelectorAll('.password-toggle').forEach((button) => {
    button.addEventListener('click', () => {
      const input = button.parentElement.querySelector('input');
      const visible = input.type === 'text';
      input.type = visible ? 'password' : 'text';
      button.setAttribute('aria-label', visible ? 'Show password' : 'Hide password');
      button.innerHTML = `<i class="fa-solid ${visible ? 'fa-eye' : 'fa-eye-slash'}"></i>`;
    });
  });

  const imageInput = document.querySelector('[data-image-input]');
  const imagePreview = document.querySelector('[data-image-preview]');
  if (imageInput && imagePreview) {
    imageInput.addEventListener('change', () => {
      const [file] = imageInput.files;
      if (!file) return;
      imagePreview.src = URL.createObjectURL(file);
      imagePreview.hidden = false;
      imageInput.closest('.upload-box').querySelector('strong').textContent = file.name;
    });
  }

  document.querySelectorAll('[data-validate]').forEach((form) => {
    form.addEventListener('submit', (event) => {
      const password = form.querySelector('input[name="password"]');
      const confirm = form.querySelector('input[name="confirm_password"]');
      if (password && confirm && password.value !== confirm.value) {
        event.preventDefault();
        confirm.setCustomValidity('The passwords do not match.');
        confirm.reportValidity();
      } else if (confirm) {
        confirm.setCustomValidity('');
      }
    });
  });

  document.querySelectorAll('[data-delete-form]').forEach((form) => {
    form.addEventListener('submit', (event) => {
      if (!window.confirm('Delete this complaint permanently?')) event.preventDefault();
    });
  });

  const pledge = document.querySelector('[data-pledge]');
  if (pledge) {
    pledge.addEventListener('click', () => {
      pledge.innerHTML = '<i class="fa-solid fa-circle-check"></i> Promise Made!';
      pledge.classList.add('pledge-made');
      pledge.disabled = true;
    });
  }
});
