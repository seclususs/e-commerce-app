/**
 * Menangani filter pesanan di halaman admin via AJAX.
 */
import { showNotification } from '../../utils/ui.js';

export function initAdminOrderFilter() {
    const filterForm = document.getElementById('admin-order-filter-form');
    const tableBody = document.getElementById('orders-table-body');
    const resetBtn = filterForm.querySelector('.cta-button-secondary');

    if (!filterForm || !tableBody) return;

    const handleFilterRequest = async (form, isReset = false) => {
        const params = isReset ? new URLSearchParams() : new URLSearchParams(new FormData(form));
        if (!isReset) {
            for (let pair of params.entries()) {
                if (!pair[1]) params.delete(pair[0]);
            }
        }
        const url = `${form.action}?${params.toString()}`;
        tableBody.style.opacity = '0.5';

        try {
            const response = await fetch(url, {
                headers: { 'X-Requested-With': 'XMLHttpRequest' }
            });
            const result = await response.json();

            if (response.ok && result.success) {
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

    filterForm.addEventListener('submit', (e) => {
        e.preventDefault();
        const submitter = e.submitter || filterForm.querySelector('button[type="submit"]');
        const originalText = submitter.textContent;
        submitter.textContent = 'Memfilter...';
        handleFilterRequest(filterForm).finally(() => {
            submitter.textContent = originalText;
        });
    });

    if (resetBtn) {
        resetBtn.addEventListener('click', (e) => {
            e.preventDefault();
            filterForm.reset();
            handleFilterRequest(filterForm, true);
        });
    }
}