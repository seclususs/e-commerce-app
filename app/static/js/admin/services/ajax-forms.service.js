import { showNotification } from '../../components/notification.js';
import { confirmModal } from '../../components/confirm-modal.js';
import { handleUIUpdate } from './ajax-update-handlers.service.js';

const formatPrice = (value) => {
    const numStr = String(value).replace(/[^0-9]/g, '');
    if (!numStr) return '';
    return parseInt(numStr, 10).toLocaleString('id-ID');
};


export async function handleAjaxSubmit(form, button) {
    if (button.disabled) {
        console.warn('Submit attempt ignored, button already disabled.');
        return;
    }
    button.disabled = true;

    const originalButtonHTML = button.innerHTML;
    const isUpdate = button.textContent.toLowerCase().includes('update') || button.textContent.toLowerCase().includes('simpan');
    button.innerHTML = `<span class="spinner" style="display: inline-block; animation: spin 0.8s ease-in-out infinite; width: 1em; height: 1em; border-width: 2px;"></span> ${isUpdate ? 'Menyimpan...' : 'Memproses...'}`;

    const priceInputs = form.querySelectorAll('input[inputmode="numeric"]');
    const originalPrices = new Map();
    priceInputs.forEach(input => {
        originalPrices.set(input, input.value);
        input.value = String(input.value).replace(/[^0-9]/g, '');
    });

    try {
        const formData = new FormData(form);

        if (button && button.name) {
            formData.append(button.name, button.value || '');
        }

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
            if (!(form.hasAttribute('data-reset-on-success') && form.getAttribute('data-reset-on-success') === 'true')) {
                 priceInputs.forEach(input => {
                     const inputName = input.name;
                     if (result.data && typeof result.data[inputName] !== 'undefined') {
                         if (input.name === 'price' || input.name === 'discount_price') {
                            input.value = formatPrice(result.data[inputName]);
                         } else {
                            input.value = result.data[inputName];
                         }
                     } else {
                         input.value = originalPrices.get(input);
                     }
                 });
            }

        } else {
            showNotification(result.message || 'Terjadi kesalahan.', true);
             priceInputs.forEach(input => input.value = originalPrices.get(input));
        }

    } catch (error) {
        console.error('Fetch error:', error);
        showNotification('Tidak dapat terhubung ke server.', true);
         priceInputs.forEach(input => input.value = originalPrices.get(input));
    } finally {
        const action = form.dataset.updateAction || 'none';
        if (action !== 'redirect') {
             setTimeout(() => {
                if (button) {
                    button.disabled = false;
                    button.innerHTML = originalButtonHTML;
                }
             }, 100);
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
            const originalLinkHTML = link.innerHTML;
            link.innerHTML = `<span class="spinner" style="display: inline-block; width: 0.8em; height: 0.8em; border-width: 2px;"></span>`;
            link.style.pointerEvents = 'none';

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
                         targetElement.style.transition = 'opacity 0.3s ease-out';
                         targetElement.style.opacity = '0';
                         setTimeout(() => {
                            targetElement.remove();
                            const tbody = targetElement.closest('tbody');
                            if (tbody && tbody.children.length === 0) {
                                 const colspan = tbody.previousElementSibling?.querySelector('tr')?.children.length || 1;
                                 tbody.innerHTML = `<tr class="no-items-row"><td colspan="${colspan}">Tidak ada data lagi.</td></tr>`;
                            }
                         }, 300);
                    } else {
                        window.location.reload();
                    }
                } else {
                    showNotification(result.message || 'Gagal menghapus.', true);
                    link.innerHTML = originalLinkHTML;
                    link.style.pointerEvents = 'auto';
                }
            } catch (error) {
                showNotification('Error koneksi.', true);
                link.innerHTML = originalLinkHTML;
                link.style.pointerEvents = 'auto';
            }
        },
        null,
        true
    );
}


async function handleAjaxToggle(link) {
    const url = link.href;
    const row = link.closest('tr');
    if (!row) {
        console.error('Toggle link clicked, but parent <tr> not found.', link);
        return;
    }
    
    const originalLinkText = link.textContent.trim();

    if (link.querySelector('.spinner')) {
        console.warn('Toggle request already in progress.');
        return;
    }
    
    link.innerHTML = `<span class="spinner" style="display: inline-block; width: 0.8em; height: 0.8em; border-width: 2px;"></span>`;
    link.style.pointerEvents = 'none';

    try {
        const response = await fetch(url, {
             method: 'POST',
             headers: {'X-Requested-With': 'XMLHttpRequest'}
        });
        
        const result = await response.json();

        if (response.ok && result.success && typeof result.new_is_active !== 'undefined') {
            showNotification(result.message || "Status diperbarui!");

            const statusCell = row.querySelector('.status-cell');
            const newStatus = result.new_is_active;

            if (statusCell) {
                const statusClass = newStatus ? 'completed' : 'cancelled';
                const statusText = newStatus ? 'Aktif' : 'Nonaktif';
                statusCell.innerHTML = `<span class="status-badge status-${statusClass}">${statusText}</span>`;
            } else {
                console.warn('Could not find .status-cell in row:', row);
            }
            
            link.textContent = newStatus ? 'Nonaktifkan' : 'Aktifkan';
            link.style.pointerEvents = 'auto';
            
        } else {
            let errorMsg = result.message || 'Gagal mengubah status.';
            if (typeof result.new_is_active === 'undefined') {
                 errorMsg = 'Gagal mengubah status: Respons server tidak valid.';
                 console.error('Server response missing "new_is_active" key.', result);
            }
            showNotification(errorMsg, true);
            link.textContent = originalLinkText;
            link.style.pointerEvents = 'auto';
        }
    } catch (error) {
        console.error('AJAX Toggle Error:', error);
        showNotification('Error koneksi.', true);
        link.textContent = originalLinkText;
        link.style.pointerEvents = 'auto';
    }
}


export function initAjaxAdminForms() {
    const adminContent = document.getElementById('adminContentArea');
    if (!adminContent) {
        console.warn("Admin content area not found for AJAX form initialization.");
        return;
    }

    let isSubmitting = false;

    adminContent.addEventListener('submit', e => {
        if (e.target.matches('form[data-ajax="true"]') && e.target.id !== 'bulk-action-form') {
            e.preventDefault();
            e.stopPropagation();

             if (isSubmitting) {
                console.warn('Submit ignored, another submission is in progress.');
                return;
             }
             isSubmitting = true;

            const submitter = e.submitter || e.target.querySelector('button[type="submit"]');
            if (submitter) {
                handleAjaxSubmit(e.target, submitter)
                    .finally(() => {
                         isSubmitting = false;
                    });
            } else {
                 console.warn("Submitter button not found for AJAX form:", e.target);
                 showNotification("Tidak dapat menemukan tombol submit.", true);
                 isSubmitting = false;
            }
        }
    });

    adminContent.addEventListener('click', e => {
        const link = e.target.closest('a[data-ajax="true"]');
        if (!link) return;

        e.preventDefault();
        e.stopPropagation();

        if (link.dataset.removeTarget || link.classList.contains('action-link-delete')) {
            handleAjaxDelete(link);
        } else if (link.classList.contains('toggle-voucher-btn')) {
            handleAjaxToggle(link);
        }
    });
}