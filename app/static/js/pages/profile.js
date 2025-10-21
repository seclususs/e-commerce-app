import { showNotification, confirmModal } from '../utils/ui.js';

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

async function handleCancelOrder(button) {
    const orderId = button.dataset.orderId;
    const url = button.dataset.url;

    confirmModal.show(
        'Konfirmasi Pembatalan',
        `Apakah Anda yakin ingin membatalkan pesanan #${orderId}?`,
        async () => {
            button.disabled = true;
            button.textContent = 'Memproses...';

            try {
                const response = await fetch(url, {
                    method: 'POST',
                    headers: {
                        'X-Requested-With': 'XMLHttpRequest',
                        'Content-Type': 'application/json'
                    }
                });
                const result = await response.json();

                if (response.ok && result.success) {
                    showNotification(result.message);
                    const orderRow = document.getElementById(`order-row-${orderId}`);
                    if (orderRow) {
                        const statusBadge = orderRow.querySelector('.status-badge');
                        statusBadge.className = 'status-badge status-cancelled';
                        statusBadge.textContent = 'Dibatalkan';
                        button.remove();

                        const aksiCell = orderRow.querySelector('td[data-label="Aksi:"]');
                        if(aksiCell && !aksiCell.querySelector('button')) {
                            aksiCell.textContent = '-';
                        }
                    }
                } else {
                    showNotification(result.message || 'Gagal membatalkan pesanan.', true);
                    button.disabled = false;
                    button.textContent = 'Batalkan';
                }
            } catch (error) {
                showNotification('Terjadi kesalahan koneksi.', true);
                button.disabled = false;
                button.textContent = 'Batalkan';
            }
        }
    );
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

/**
 * Initializes event listeners for the user profile page (order cancellation).
 */
export function initUserProfile() {
    const ordersList = document.getElementById('orders-list');
    if (!ordersList) return;

    ordersList.addEventListener('click', (e) => {
        const cancelButton = e.target.closest('.ajax-cancel-order');
        if (cancelButton) {
            e.preventDefault();
            handleCancelOrder(cancelButton);
        }
    });
}