import { showNotification } from '../../components/notification.js';
import { confirmModal } from '../../components/confirm-modal.js';
import { handleUIUpdate } from './ajax-update-handlers.service.js';


export async function handleAjaxSubmit(form, button) {
    const originalButtonHTML = button.innerHTML;
    const isUpdate = button.textContent.toLowerCase().includes('update');
    button.disabled = true;
    button.innerHTML = `<span class="spinner" style="display: inline-block; animation: spin 0.8s ease-in-out infinite; width: 1em; height: 1em; border-width: 2px;"></span> ${isUpdate ? 'Updating...' : 'Menyimpan...'}`;

    const priceInputs = form.querySelectorAll('input[inputmode="numeric"]');
    const originalPrices = new Map();
    priceInputs.forEach(input => {
        originalPrices.set(input, input.value);
        input.value = String(input.value).replace(/[^0-9]/g, '');
    });

    try {
        const formData = new FormData(form);
        const response = await fetch(form.getAttribute('action'), {
            method: form.method || 'POST',
            body: formData,
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            }
        });

        const result = await response.json();

        if (response.ok && result.success) {
            showNotification(result.message || 'Berhasil!', false);
            handleUIUpdate(form, result);
            if (form.hasAttribute('data-reset-on-success')) {
                form.reset();
                priceInputs.forEach(input => input.value = '');
            }
        } else {
            showNotification(result.message || 'Terjadi kesalahan.', true);
        }
    } catch (error) {
        console.error('Fetch error:', error);
        showNotification('Tidak dapat terhubung ke server.', true);
    } finally {
        button.disabled = false;
        button.innerHTML = originalButtonHTML;

        if (!form.hasAttribute('data-reset-on-success')) {

            priceInputs.forEach(input => {
                const originalValue = originalPrices.get(input);
                if (input.value) {
                     const numStr = String(input.value).replace(/[^0-9]/g, '');
                     input.value = numStr ? parseInt(numStr, 10).toLocaleString('id-ID') : '';
                } else {
                     input.value = '';
                }
            });
        }
    }
}


function handleAjaxDelete(link) {
    const url = link.href;
    const targetSelector = link.dataset.removeTarget;

    confirmModal.show(
        'Konfirmasi Hapus',
        'Apakah Anda yakin ingin menghapus item ini? Tindakan ini tidak dapat diurungkan.',
        async () => {
            try {
                const response = await fetch(url, {
                    method: 'POST',
                    headers: {'X-Requested-With': 'XMLHttpRequest'}
                });
                const result = await response.json();
                if (response.ok && result.success) {
                    showNotification(result.message || 'Berhasil dihapus.');
                    const targetElement = document.querySelector(targetSelector);
                    if (targetElement) {
                        targetElement.remove();

                        const tbody = targetElement.closest('tbody');
                        if (tbody && tbody.children.length === 0) {
                             const colspan = tbody.previousElementSibling?.querySelector('tr')?.children.length || 1;
                             tbody.innerHTML = `<tr class="no-items-row"><td colspan="${colspan}">Tidak ada data lagi.</td></tr>`;
                        }
                    } else {
                        window.location.reload();
                    }
                } else {
                    showNotification(result.message || 'Gagal menghapus.', true);
                }
            } catch (error) {
                showNotification('Error koneksi.', true);
            }
        }
    );
}


async function handleAjaxToggle(link) {
    const url = link.href;
    const row = link.closest('tr');

    try {
        const response = await fetch(url, {
             method: 'POST',
             headers: {'X-Requested-With': 'XMLHttpRequest'}
        });
        const result = await response.json();
        if (response.ok && result.success) {
            showNotification(result.message);

            if (row && result.data) {
                const statusCell = row.querySelector('.status-cell');
                const newStatus = result.data.is_active;
                if (statusCell) {
                    statusCell.innerHTML = `<span class="status-badge status-${newStatus ? 'completed' : 'cancelled'}">${newStatus ? 'Aktif' : 'Nonaktif'}</span>`;
                }
                link.textContent = newStatus ? 'Nonaktifkan' : 'Aktifkan';
            }
        } else {
            showNotification(result.message || 'Gagal mengubah status.', true);
        }
    } catch (error) {
        showNotification('Error koneksi.', true);
    }
}


export function initAjaxAdminForms() {
    const adminContent = document.querySelector('.admin-content-area');
    if (!adminContent) return;

    adminContent.addEventListener('submit', e => {

        if (e.target.matches('form[data-ajax="true"]') && e.target.id !== 'bulk-action-form') {
            e.preventDefault();
            const submitter = e.submitter || e.target.querySelector('button[type="submit"]');
            if (submitter) {
                handleAjaxSubmit(e.target, submitter);
            } else {
                 console.warn("Submitter tidak ditemukan untuk form AJAX:", e.target);
            }
        }
    });

    adminContent.addEventListener('click', e => {
        const link = e.target.closest('a[data-ajax="true"]');
        if (!link) return;

        e.preventDefault();

        if (link.dataset.removeTarget || link.classList.contains('action-link-delete')) {
            handleAjaxDelete(link);
        } else if (link.classList.contains('toggle-voucher-btn')) {
            handleAjaxToggle(link);
        }
    });
}