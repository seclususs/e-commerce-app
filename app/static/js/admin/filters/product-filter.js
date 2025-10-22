import { showNotification } from '../../utils/ui.js';
import { initAnimations } from '../../utils/animations.js';

let debounceTimer;
const debounce = (callback, time) => {
    window.clearTimeout(debounceTimer);
    debounceTimer = window.setTimeout(callback, time);
};

export function initAdminProductFilter() {
    const filterForm = document.getElementById('admin-product-filter-form');
    const tableBody = document.getElementById('products-table-body');
    const resetBtn = document.getElementById('reset-filter-btn');
    const searchInput = filterForm ? filterForm.querySelector('input[name="search"]') : null;

    if (!filterForm || !tableBody || !searchInput) return;

    const handleFilterRequest = async (isReset = false) => {
        const params = isReset ? new URLSearchParams() : new URLSearchParams(new FormData(filterForm));

        if (!isReset) {
            for (let [key, value] of new FormData(filterForm).entries()) {
                if (!value) {
                    params.delete(key);
                }
            }
        }

        const url = `${filterForm.action}?${params.toString()}`;
        tableBody.style.opacity = '0.5';

        try {
            const response = await fetch(url, {
                headers: { 'X-Requested-With': 'XMLHttpRequest' }
            });
            const result = await response.json();

            if (response.ok && result.success) {
                const newUrl = `${window.location.pathname}?${params.toString()}`;
                window.history.pushState({ path: newUrl }, '', newUrl);

                tableBody.innerHTML = result.html;
                initAnimations();
            } else {
                showNotification('Gagal memfilter produk.', true);
            }
        } catch (error) {
            console.error('Filter error:', error);
            showNotification('Error koneksi saat memfilter.', true);
        } finally {
            tableBody.style.opacity = '1';
        }
    };

    searchInput.addEventListener('input', () => {
        debounce(() => handleFilterRequest(), 400);
    });

    filterForm.addEventListener('change', (e) => {
        if (e.target.tagName === 'SELECT') {
            handleFilterRequest();
        }
    });

    filterForm.addEventListener('submit', (e) => {
        e.preventDefault();
        handleFilterRequest();
    });

    if (resetBtn) {
        resetBtn.addEventListener('click', (e) => {
            e.preventDefault();
            filterForm.reset();
            handleFilterRequest(true);
        });
    }
}