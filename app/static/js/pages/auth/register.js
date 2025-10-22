import { showNotification } from '../../utils/ui.js';

export function initRegisterPage() {
    const form = document.getElementById('register-form');
    if (!form) return;

    const usernameInput = document.getElementById('username');
    const emailInput = document.getElementById('email');
    const usernameFeedback = document.getElementById('username-feedback');
    const emailFeedback = document.getElementById('email-feedback');
    const submitBtn = form.querySelector('button[type="submit"]');

    let isUsernameValid = false;
    let isEmailValid = false;

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
                body: JSON.stringify({
                    [input.name]: value })
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

    usernameInput.addEventListener('blur', async () => {
        isUsernameValid = await checkAvailability(usernameInput, usernameFeedback, '/api/validate/username');
    });

    emailInput.addEventListener('blur', async () => {
        isEmailValid = await checkAvailability(emailInput, emailFeedback, '/api/validate/email');
    });

    form.addEventListener('submit', (e) => {
        if (!isUsernameValid || !isEmailValid) {
            e.preventDefault();
            if (usernameInput.value && !isUsernameValid) {
                showNotification('Username tidak tersedia atau belum divalidasi.', true);
            } else if (emailInput.value && !isEmailValid) {
                showNotification('Email tidak tersedia atau belum divalidasi.', true);
            } else {
                showNotification('Silakan isi dan validasi username dan email.', true);
            }
        } else {
            submitBtn.disabled = true;
            submitBtn.innerHTML = `<span class="spinner"></span> Mendaftar...`;
        }
    });
}