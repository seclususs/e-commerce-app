import { showNotification } from '../components/notification.js';
import { confirmModal } from '../components/confirm-modal.js';

async function handleMembershipSubmit(form, button) {
    const originalButtonHTML = button.innerHTML;
    button.disabled = true;
    button.innerHTML = `<span class="spinner"></span><span>Memproses...</span>`;

    const action = form.querySelector('input[name="action"]').value;
    const url = form.getAttribute('action');

    let confirmTitle = '';
    let confirmText = '';

    if (action === 'subscribe') {
        confirmTitle = 'Konfirmasi Pembelian';
        confirmText = 'Anda akan membeli paket membership ini. Lanjutkan?';
    } else if (action === 'upgrade') {
        confirmTitle = 'Konfirmasi Upgrade';
        confirmText = 'Anda akan upgrade ke paket ini. Biaya prorata akan dihitung. Lanjutkan?';
    } else {
        showNotification('Aksi tidak dikenal.', true);
        button.disabled = false;
        button.innerHTML = originalButtonHTML;
        return;
    }

    const performSubmit = async () => {
        try {
            const response = await fetch(url, {
                method: 'POST',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                },
                body: new FormData(form)
            });

            const result = await response.json();

            if (response.ok && result.success) {
                showNotification(result.message || 'Berhasil!');
                
                if (result.redirect_url) {
                    window.location.href = result.redirect_url;
                } else {
                    window.location.reload(); 
                }
            } else {
                showNotification(result.message || 'Terjadi kesalahan.', true);
                button.disabled = false;
                button.innerHTML = originalButtonHTML;
            }
        } catch (error) {
            console.error('Membership submit error:', error);
            showNotification('Tidak dapat terhubung ke server.', true);
            button.disabled = false;
            button.innerHTML = originalButtonHTML;
        }
    };

    const onCancel = () => {
        button.disabled = false;
        button.innerHTML = originalButtonHTML;
    };
    
    confirmModal.show(confirmTitle, confirmText, performSubmit, onCancel, false);
}


export function initMembershipPage() {
    const container = document.querySelector('.membership-page-section');
    if (!container) return;

    container.addEventListener('submit', e => {
        const form = e.target.closest('.membership-action-form');
        if (form && form.dataset.ajax === 'true') {
            e.preventDefault();
            const submitter = e.submitter || form.querySelector('button[type="submit"]');
            if (submitter) {
                handleMembershipSubmit(form, submitter);
            }
        }
    });
}