import { showNotification } from '../components/notification.js';
import { confirmModal } from '../components/confirm-modal.js';

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

            if (result.data) {
                for (const key in result.data) {
                    const input = form.querySelector(`[name="${key}"]`);
                    if (input) {
                        input.value = result.data[key];
                    }
                }
            }

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
                        if (aksiCell && !aksiCell.querySelector('button')) {
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
        },
        null,
        true
    );
}

function initProfileTabs() {
    const tabContainer = document.querySelector('.profile-tabs');
    if (!tabContainer) return;

    tabContainer.addEventListener('click', (e) => {
        const tabButton = e.target.closest('.profile-tab-btn');
        if (!tabButton || tabButton.classList.contains('active')) return;

        const targetTabId = tabButton.dataset.tab;
        if (!targetTabId) return;

        document.querySelectorAll('.profile-tab-btn').forEach(btn => {
            btn.classList.remove('active');
        });
        document.querySelectorAll('.profile-tab-content').forEach(content => {
            content.classList.remove('active');
        });

        tabButton.classList.add('active');
        const targetContent = document.getElementById(targetTabId);
        if (targetContent) {
            targetContent.classList.add('active');
        }
    });
}

function initMyVouchers() {
    const claimForm = document.getElementById('claim-voucher-form');
    if (claimForm) {
        claimForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const input = claimForm.querySelector('input[name="voucher_code"]');
            const button = claimForm.querySelector('button[type="submit"]');
            const code = input.value.trim();

            if (!code) {
                showNotification('Silakan masukkan kode voucher.', true);
                return;
            }

            const originalButtonHTML = button.innerHTML;
            button.disabled = true;
            button.innerHTML = `<span class="spinner"></span>`;

            try {
                const response = await fetch(claimForm.dataset.url, {
                    method: 'POST',
                    headers: {
                        'X-Requested-With': 'XMLHttpRequest',
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ voucher_code: code })
                });
                const result = await response.json();

                if (response.ok && result.success) {
                    showNotification(result.message);
                    location.reload();
                } else {
                    showNotification(result.message || 'Gagal mengklaim voucher.', true);
                    button.disabled = false;
                    button.innerHTML = originalButtonHTML;
                }
            } catch (error) {
                showNotification('Error koneksi.', true);
                button.disabled = false;
                button.innerHTML = originalButtonHTML;
            }
        });
    }

    const voucherList = document.querySelector('.voucher-list-container');
    if (voucherList) {
        voucherList.addEventListener('click', (e) => {
            const copyBtn = e.target.closest('.copy-voucher-btn');
            if (copyBtn) {
                const code = copyBtn.dataset.code;
                const tempInput = document.createElement('textarea');
                tempInput.value = code;
                document.body.appendChild(tempInput);
                tempInput.select();
                try {
                    document.execCommand('copy');
                    showNotification(`Kode "${code}" disalin!`);
                } catch (err) {
                    showNotification('Gagal menyalin kode.', true);
                }
                document.body.removeChild(tempInput);
            }
        });
    }
}

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

export function initUserProfile() {
    initProfileTabs();
    initMyVouchers();

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