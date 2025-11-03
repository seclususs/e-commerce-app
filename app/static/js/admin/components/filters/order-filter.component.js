import { showNotification } from '../../../components/notification.js';

let debounceTimer;
const debounce = (callback, time) => {
    window.clearTimeout(debounceTimer);
    debounceTimer = window.setTimeout(callback, time);
};

export function initAdminOrderFilter() {
    const filterForm = document.getElementById('admin-order-filter-form');
    const tableBody = document.getElementById('orders-table-body');
    const resetBtn = filterForm.querySelector('.cta-button-secondary');
    const searchInput = filterForm.querySelector('input[name="search"]');
    const statusSelect = filterForm.querySelector('select[name="status"]');
    const startDate = filterForm.querySelector('input[name="start_date"]');
    const endDate = filterForm.querySelector('input[name="end_date"]');

    if (!filterForm || !tableBody || !searchInput || !statusSelect || !startDate || !endDate) return;

    const handleFilterRequest = async (form, isReset = false) => {
        const params = isReset ? new URLSearchParams() : new URLSearchParams(new FormData(form));
        if (!isReset) {
            for (let pair of params.entries()) {
                if (!pair[1]) params.delete(pair[0]);
            }
        }
        
        params.set('is_filter_request', 'true');

        const url = `${form.action}?${params.toString()}`;
        tableBody.style.opacity = '0.5';

        try {
            const response = await fetch(url, {
                headers: { 'X-Requested-With': 'XMLHttpRequest' }
            });
            const result = await response.json();

            if (response.ok && result.success) {
                params.delete('is_filter_request');
                const newUrl = `${window.location.pathname}?${params.toString()}`;
                history.pushState({ path: newUrl }, '', newUrl);
                tableBody.innerHTML = result.html;
            } else {
                showNotification('Gagal memfilter pesanan.', true);
            }
        } catch (error) {
            console.error('Filter error:', error);
            showNotification('Error koneksi saat memfilter.', true);
        } finally {
            tableBody.style.opacity = '1';
        }
    };

    searchInput.addEventListener('input', () => {
        debounce(() => handleFilterRequest(filterForm), 400);
    });

    statusSelect.addEventListener('change', () => {
        handleFilterRequest(filterForm);
    });

    startDate.addEventListener('change', () => {
        handleFilterRequest(filterForm);
    });

    endDate.addEventListener('change', () => {
        handleFilterRequest(filterForm);
    });

    if (resetBtn) {
        resetBtn.addEventListener('click', (e) => {
            e.preventDefault();
            filterForm.reset();
            handleFilterRequest(filterForm, true);
        });
    }
}