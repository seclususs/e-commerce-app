import { showNotification, confirmModal } from '../utils/ui.js';

function handlePrependAction(form, result) {
    const target = document.querySelector(form.dataset.updateTarget);
    if (target && result.html) {
        const noItemRow = target.querySelector('.no-items-row');
        if (noItemRow) noItemRow.remove();

        target.insertAdjacentHTML('afterbegin', result.html);
        form.reset();

        if (form.id === 'add-product-form') {
            document.getElementById('image-previews').innerHTML = '';
            document.getElementById('file-name').textContent = 'Belum ada file dipilih';
        }

        const newRow = target.firstElementChild;
        if (newRow) {
            newRow.style.backgroundColor = 'rgba(59, 130, 246, 0.2)';
            setTimeout(() => {
                newRow.style.transition = 'background-color 0.5s ease';
                newRow.style.backgroundColor = '';
                setTimeout(() => newRow.style.transition = '', 500);
            }, 100);
        }
    }
}

function handleUpdateTextAction(form, result) {
    const target = document.querySelector(form.dataset.updateTarget);
    if (target && result.data && result.data.name) {
        target.value = result.data.name;
    }
}

function handleUpdateStatusAction(form, result) {
    if (result.data) {
        const statusBadge = document.querySelector('.status-badge');
        const trackingInput = document.querySelector('input[name="tracking_number"]');
        if (statusBadge) {
            statusBadge.className = `status-badge status-${result.data.status_class}`;
            statusBadge.textContent = result.data.status;
        }
        if (trackingInput) {
            trackingInput.value = result.data.tracking_number || '';
        }
    }
}

function handleBulkActionResult(form, result) {
    if (result.action === 'delete') {
        result.ids.forEach(id => {
            document.querySelector(`#product-row-${id}`)?.remove();
        });
    } else if (result.action === 'set_category') {
        result.ids.forEach(id => {
            const cell = document.querySelector(`#product-row-${id} .category-name-cell`);
            if (cell) cell.textContent = result.new_category_name;
        });
    }

    const select = document.getElementById('bulk-action-select');
    if (select) select.value = '';
    document.querySelectorAll('.product-checkbox').forEach(cb => cb.checked = false);
    const selectAll = document.getElementById('select-all-products');
    if (selectAll) selectAll.checked = false;

    const categorySelector = document.getElementById('bulk-category-selector');
    if (categorySelector) categorySelector.classList.add('hidden');
}

function handleRedirectAction(form, result) {
    if (result.redirect_url) {
        window.location.href = result.redirect_url;
    }
}

function handleUpdateInputsAction(form, result) {
    if (result.data) {
        Object.keys(result.data).forEach(key => {
            const input = form.querySelector(`input[name="${key}"]`);
            if (input) {
                input.value = result.data[key];
            }
        });
    }
}

function handleUIUpdate(form, result) {
    const action = form.dataset.updateAction || 'none';
    const actionHandlers = {
        'prepend': handlePrependAction,
        'update-text': handleUpdateTextAction,
        'update-status': handleUpdateStatusAction,
        'bulk-action': handleBulkActionResult,
        'redirect': handleRedirectAction,
        'update-inputs': handleUpdateInputsAction
    };

    if (actionHandlers[action]) {
        actionHandlers[action](form, result);
    }
}

export async function handleAjaxSubmit(form, button) {
    const originalButtonHTML = button.innerHTML;
    const isUpdate = button.textContent.toLowerCase().includes('update');
    button.disabled = true;
    button.innerHTML = `<span class="spinner" style="display: inline-block; animation: spin 0.8s ease-in-out infinite; width: 1em; height: 1em; border-width: 2px;"></span> ${isUpdate ? 'Updating...' : 'Menyimpan...'}`;

    const priceInputs = form.querySelectorAll('input[name="price"], input[name="discount_price"]');
    const originalPrices = new Map();
    priceInputs.forEach(input => {
        originalPrices.set(input, input.value);
        input.value = String(input.value).replace(/[^0-9]/g, '');
    });

    try {
        const response = await fetch(form.getAttribute('action'), {
            method: form.method || 'POST',
            body: new FormData(form),
        });

        const result = await response.json();

        if (response.ok && result.success) {
            showNotification(result.message || 'Berhasil!', false);
            handleUIUpdate(form, result);
            if (form.hasAttribute('data-reset-on-success')) {
                form.reset();
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
                input.value = originalPrices.get(input);
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
                const response = await fetch(url, { method: 'POST' });
                const result = await response.json();
                if (response.ok && result.success) {
                    showNotification(result.message || 'Berhasil dihapus.');
                    const targetElement = document.querySelector(targetSelector);
                    if (targetElement) {
                        targetElement.remove();
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
        const response = await fetch(url, { method: 'POST' });
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
            }
        }
    });

    adminContent.addEventListener('click', e => {
        const link = e.target.closest('a[data-ajax="true"]');
        if (!link) return;

        e.preventDefault();

        if (link.classList.contains('action-link-delete')) {
            handleAjaxDelete(link);
        } else if (link.classList.contains('toggle-voucher-btn')) {
            handleAjaxToggle(link);
        }
    });
}