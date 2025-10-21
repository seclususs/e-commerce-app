import { showNotification } from '../utils/ui.js';

/**
 * Handles asynchronous form submission for the profile editor page.
 * @param {HTMLFormElement} form The form being submitted.
 * @param {HTMLElement} button The submit button that was clicked.
 */
async function handleProfileSubmit(form, button) {
    const originalButtonHTML = button.innerHTML;
    button.disabled = true;
    button.innerHTML = `<span class="spinner"></span><span>Menyimpan...</span>`;

    try {
        const response = await fetch(form.action, {
            method: 'POST',
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            },
            body: new FormData(form)
        });

        const result = await response.json();

        if (response.ok && result.success) {
            showNotification(result.message || 'Profil berhasil diperbarui!', false);

            // Update UI based on response data
            if (result.data) {
                for (const key in result.data) {
                    const input = form.querySelector(`[name="${key}"]`);
                    if (input) {
                        input.value = result.data[key];
                    }
                }
            }

            // Reset password form on success
            if (form.hasAttribute('data-reset-on-success')) {
                form.reset();
            }

        } else {
            showNotification(result.message || 'Terjadi kesalahan.', true);
        }
    } catch (error) {
        console.error('Profile update error:', error);
        showNotification('Tidak dapat terhubung ke server.', true);
    } finally {
        button.disabled = false;
        button.innerHTML = originalButtonHTML;
    }
}

/**
 * Initializes event listeners for the profile editor forms.
 */
export function initProfileEditor() {
    const profileContainer = document.querySelector('.profile-container');
    if (!profileContainer) return;

    profileContainer.addEventListener('submit', e => {
        const form = e.target;
        if (form.matches('form[data-ajax="true"]')) {
            e.preventDefault();
            const submitter = e.submitter || form.querySelector('button[type="submit"]');
            if (submitter) {
                handleProfileSubmit(form, submitter);
            }
        }
    });
}