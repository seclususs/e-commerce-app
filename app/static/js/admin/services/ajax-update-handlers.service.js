import { showNotification } from '../../components/notification.js';
import { initAnimations } from '../../utils/animations.js';

function handlePrependAction(form, result) {
    const targetSelector = form.dataset.updateTarget;
    const target = targetSelector ? document.querySelector(targetSelector) : null;

    if (target && result.html) {
        const noItemRow = target.querySelector('.no-items-row');
        if (noItemRow) noItemRow.remove();

        target.insertAdjacentHTML('afterbegin', result.html);

        if (form.hasAttribute('data-reset-on-success')) {
            form.reset();
            if (form.id === 'add-product-form') {
                const previewContainer = document.getElementById('image-previews');
                const fileNameDisplay = document.getElementById('file-name');
                const fileInput = document.getElementById('images');

                if (previewContainer) previewContainer.innerHTML = '';
                if (fileNameDisplay) fileNameDisplay.textContent = 'Belum ada file dipilih';
                if (fileInput) fileInput.value = null;

                const hasVariantsCheckbox = document.getElementById('has-variants-checkbox');
                if (hasVariantsCheckbox) {
                    hasVariantsCheckbox.checked = false;
                    hasVariantsCheckbox.dispatchEvent(new Event('change'));
                }
                const priceInputs = form.querySelectorAll('input[inputmode="numeric"]');
                priceInputs.forEach(input => input.value = '');
            }
        }

        const newRow = target.firstElementChild;
        if (newRow && newRow.tagName === 'TR') {
            newRow.style.backgroundColor = 'rgba(59, 130, 246, 0.2)';
            setTimeout(() => {
                newRow.style.transition = 'background-color 0.5s ease';
                newRow.style.backgroundColor = '';
                setTimeout(() => newRow.style.transition = '', 500);
            }, 100);
        }

        initAnimations();
        
    } else {
        console.warn('Target prepend tidak ditemukan atau tidak ada HTML dalam response:', targetSelector);
    }
}

function handleUpdateTextAction(form, result) {
    const targetSelector = form.dataset.updateTarget;
    const target = targetSelector ? document.querySelector(targetSelector) : null;

    if (target && target.tagName === 'INPUT' && result.data && typeof result.data.name !== 'undefined') {
        target.value = result.data.name;
    } else if (target && result.data && typeof result.data.name !== 'undefined') {
        target.textContent = result.data.name;
    } else {
        console.warn('Target update-text tidak ditemukan, bukan input, atau data nama tidak ada:', targetSelector);
    }
}

function handleUpdateStatusAction(form, result) {
    console.log("Handling update status action", result);
    if (result.data) {
        const statusDisplayParagraph = document.getElementById('order-status-display');
        const statusBadge = statusDisplayParagraph ? statusDisplayParagraph.querySelector('.status-badge') : null;

        if (statusBadge && result.data.status && result.data.status_class) {
            statusBadge.className = `status-badge status-${result.data.status_class}`;
            statusBadge.textContent = result.data.status;
            console.log("Status badge updated:", statusBadge.className, statusBadge.textContent);
        } else {
            console.warn("Status badge element not found (#order-status-display .status-badge) or data missing for update.");
        }

        const trackingInput = form.querySelector('input[name="tracking_number"]');
        if (trackingInput && typeof result.data.tracking_number !== 'undefined') {
            trackingInput.value = result.data.tracking_number || '';
            console.log("Tracking number input updated:", trackingInput.value);
        } else {
            console.log("Tracking number input element not found in the form or not in response data.");
        }

        const statusSelect = form.querySelector('select[name="status"]');
        if (statusSelect && result.data.status) {
            statusSelect.value = result.data.status;
            console.log("Status select updated:", statusSelect.value);
        }
    } else {
        console.warn('Data tidak ditemukan dalam response untuk update-status.');
    }
}

function handleBulkActionResult(form, result) {
    if (!result.ids || !result.action) {
        console.warn('ID atau aksi tidak ditemukan dalam response bulk-action.');
        return;
    }

    if (result.action === 'delete') {
        result.ids.forEach(id => {
            document.querySelector(`#product-row-${id}`)?.remove();
        });

        const tbody = document.getElementById('products-table-body');
        if (tbody && tbody.children.length === 0) {
            tbody.innerHTML = '<tr class="no-items-row"><td colspan="9">Tidak ada produk lagi.</td></tr>';
        }

    } else if (result.action === 'set_category') {
        result.ids.forEach(id => {
            const cell = document.querySelector(`#product-row-${id} .category-name-cell`);
            if (cell) cell.textContent = result.new_category_name || 'N/A';
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
    } else {
        console.warn('URL redirect tidak ditemukan dalam response.');
    }
}

function handleUpdateInputsAction(form, result) {
    if (result.data) {
        Object.keys(result.data).forEach(key => {
            const input = form.querySelector(`input[name="${key}"], select[name="${key}"], textarea[name="${key}"]`);
            if (input) {
                input.value = result.data[key];
                if (input.type === 'number' && isNaN(input.value)) {
                    input.value = 0;
                }
                console.log(`Updated input ${key} in form ${form.id} to: ${input.value}`);
            } else {
                console.warn(`Input dengan nama "${key}" tidak ditemukan dalam form ${form.id}`);
            }
        });
    } else {
        console.warn('Data tidak ditemukan dalam response untuk update-inputs.');
    }
}

export function handleUIUpdate(form, result) {
    const action = form.dataset.updateAction || 'none';

    const actionHandlers = {
        'prepend': handlePrependAction,
        'update-text': handleUpdateTextAction,
        'update-status': handleUpdateStatusAction,
        'bulk-action': handleBulkActionResult,
        'redirect': handleRedirectAction,
        'update-inputs': handleUpdateInputsAction,
        'none': () => {}
    };

    if (actionHandlers[action]) {
        console.log(`Handling action: ${action} for form ${form.id || 'without ID'}`);
        try {
            actionHandlers[action](form, result);
        } catch (error) {
            console.error(`Error handling action "${action}":`, error);
            showNotification(`Gagal memperbarui tampilan: ${error.message}`, true);
        }
    } else {
        console.warn(`Handler untuk aksi "${action}" tidak ditemukan.`);
    }
}