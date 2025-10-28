import { showNotification } from '../../../components/notification.js';
import { updateAllCharts } from '../charts/dashboard-charts.component.js';

const formatRupiah = (num) => {
    const number = Number(num);
    if (isNaN(number)) return 'Rp 0';
    return `Rp ${number.toLocaleString('id-ID', { minimumFractionDigits: 0 })}`;
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
        document.querySelectorAll('.dashboard-stats, .admin-card canvas').forEach(el => el.style.opacity = '0.5');

        const params = new URLSearchParams(new FormData(form));
        const url = `${form.action}?${params.toString()}`;

        try {
            const response = await fetch(url, {
                headers: { 'X-Requested-With': 'XMLHttpRequest' }
            });
            const result = await response.json();

            if (response.ok && result && result.success) {
                const newUrl = `${window.location.pathname}?${params.toString()}`;
                history.pushState({ path: newUrl }, '', newUrl);

                const stats = result.stats;
                if (!stats) {
                    console.error('Data stats tidak ditemukan dalam respons:', result);
                    showNotification('Gagal memuat data statistik dashboard.', true);
                    return;
                }

                const statTotalSales = document.getElementById('stat-total-sales');
                const statOrderCount = document.getElementById('stat-order-count');
                const statNewUserCount = document.getElementById('stat-new-user-count');
                const statProductCount = document.getElementById('stat-product-count');

                if (statTotalSales) statTotalSales.textContent = formatRupiah(stats.total_sales);
                if (statOrderCount) statOrderCount.textContent = stats.order_count;
                if (statNewUserCount) statNewUserCount.textContent = stats.new_user_count;
                if (statProductCount) statProductCount.textContent = stats.product_count;

                updateAllCharts(stats);

            } else {
                const errorMessage = result?.message || 'Gagal memuat data dashboard.';
                showNotification(errorMessage, true);
                console.error('Dashboard filter request failed:', result);
            }

        } catch (error) {
            console.error('Dashboard filter error:', error);
            showNotification('Error koneksi saat memuat data.', true);
        } finally {
            submitBtn.disabled = false;
            submitBtn.textContent = 'Terapkan Filter';
            document.querySelectorAll('.dashboard-stats, .admin-card canvas').forEach(el => el.style.opacity = '1');
        }
    };

    if (periodSelect) {
        periodSelect.addEventListener('change', function() {
            if (this.value !== 'custom') {
                if (customStart) customStart.value = '';
                if (customEnd) customEnd.value = '';
                handleDashboardUpdateRequest();
            }
        });
    }

    form.addEventListener('submit', function(e) {
        e.preventDefault();
        if (periodSelect && (customStart?.value || customEnd?.value)) {
             periodSelect.value = 'custom';
        }
        handleDashboardUpdateRequest();
    });
}