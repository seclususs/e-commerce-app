import { showNotification } from '../../utils/ui.js';
import { updateAllCharts } from '../charts/dashboard-charts.js';

const formatRupiah = (num) => {
    if (typeof num !== 'number') return 'Rp 0';
    return `Rp ${num.toLocaleString('id-ID', { minimumFractionDigits: 0 })}`;
};

export function initDashboardFilter() {
    const form = document.getElementById('dashboard-filter-form');
    if (!form) return;

    const periodSelect = document.getElementById('period');
    const customStart = document.getElementById('custom_start');
    const customEnd = document.getElementById('custom_end');
    const submitBtn = form.querySelector('button[type="submit"]');

    const handleDashboardUpdateRequest = async () => {
        submitBtn.disabled = true;
        submitBtn.textContent = 'Memuat...';
        document.querySelector('.dashboard-stats').style.opacity = '0.5';
        document.querySelector('.admin-card h3 + div').style.opacity = '0.5';

        const params = new URLSearchParams(new FormData(form));
        const url = `${form.action}?${params.toString()}`;

        try {
            const response = await fetch(url, {
                headers: { 'X-Requested-With': 'XMLHttpRequest' }
            });
            const result = await response.json();

            if (response.ok && result.success) {
                const newUrl = `${window.location.pathname}?${params.toString()}`;
                history.pushState({ path: newUrl }, '', newUrl);

                const stats = result.data.stats;
                document.getElementById('stat-total-sales').textContent = formatRupiah(stats.total_sales);
                document.getElementById('stat-order-count').textContent = stats.order_count;
                document.getElementById('stat-new-user-count').textContent = stats.new_user_count;
                document.getElementById('stat-product-count').textContent = stats.product_count;

                updateAllCharts(stats);

            } else {
                showNotification('Gagal memuat data dashboard.', true);
            }

        } catch (error) {
            console.error('Dashboard filter error:', error);
            showNotification('Error koneksi saat memuat data.', true);
        } finally {
            submitBtn.disabled = false;
            submitBtn.textContent = 'Terapkan Filter';
            document.querySelector('.dashboard-stats').style.opacity = '1';
            document.querySelector('.admin-card h3 + div').style.opacity = '1';
        }
    };

    periodSelect.addEventListener('change', function() {
        if (this.value !== 'custom') {
            customStart.value = '';
            customEnd.value = '';
            handleDashboardUpdateRequest();
        }
    });

    form.addEventListener('submit', function(e) {
        e.preventDefault();
        periodSelect.value = 'custom';
        handleDashboardUpdateRequest();
    });
}