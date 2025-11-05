import { showNotification } from '../components/notification.js';

const checkAvailability = async (input, feedbackEl, endpoint) => {
    const value = input.value.trim();
    if (value.length < 3) {
        feedbackEl.textContent = '';
        feedbackEl.className = 'validation-feedback';
        return false;
    }

    feedbackEl.textContent = 'Memeriksa...';
    feedbackEl.className = 'validation-feedback';

    try {
        const response = await fetch(endpoint, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ [input.name]: value })
        });
        const result = await response.json();

        feedbackEl.textContent = result.message;
        feedbackEl.classList.toggle('success', result.available);
        feedbackEl.classList.toggle('error', !result.available);
        return result.available;

    } catch (error) {
        feedbackEl.textContent = 'Gagal memeriksa.';
        feedbackEl.className = 'validation-feedback error';
        return false;
    }
};


export function initSuccessPage() {
    const layoutContainer = document.getElementById('success-layout-container');
    if (!layoutContainer) {
        return;
    }
    const transitionDelay = 500;

    setTimeout(() => {
        layoutContainer.classList.add('show-register');
    }, transitionDelay);

    const registerForm = layoutContainer.querySelector('form[action*="register_from_order"]');
    if (registerForm) {
        const emailInput = registerForm.querySelector('input[name="email"]');
        const emailFeedback = registerForm.querySelector('#email-feedback');
        const submitBtn = registerForm.querySelector('button[type="submit"]');
        let isEmailValid = false;

        if (emailInput && !emailInput.disabled && emailFeedback) {
            emailInput.addEventListener('blur', async () => {
                isEmailValid = await checkAvailability(emailInput, emailFeedback, '/api/validate/email');
            });

            registerForm.addEventListener('submit', (e) => {
                if (!isEmailValid) {
                    e.preventDefault();
                    showNotification('Email tidak tersedia atau belum divalidasi.', true);
                } else {
                    submitBtn.disabled = true;
                    submitBtn.innerHTML = `<span class="spinner"></span> Membuat Akun...`;
                }
            });
        } else if (submitBtn) {
             registerForm.addEventListener('submit', () => {
                 submitBtn.disabled = true;
                 submitBtn.innerHTML = `<span class="spinner"></span> Membuat Akun...`;
             });
        }
    }
}