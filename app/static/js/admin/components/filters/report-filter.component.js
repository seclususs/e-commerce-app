import { showNotification } from '../../../components/notification.js';
import { initAnimations } from '../../../utils/animations.js';

export function initReportFilter() {
    const filterForm = document.getElementById('reports-filter-form');
    const adminContentArea = document.getElementById('adminContentArea');
    
    if (!filterForm || !adminContentArea) return;
    
    const startDateInput = document.getElementById('start_date');
    const endDateInput = document.getElementById('end_date');

    if (!startDateInput || !endDateInput) {
        console.warn('Elemen filter tanggal (mulai/selesai) tidak ditemukan.');
        return;
    }

    const handleReportFilterRequest = async (isReset = false) => {
        const params = isReset ? new URLSearchParams() : new URLSearchParams(new FormData(filterForm));
        
        const url = `${filterForm.action}?${params.toString()}`;
        adminContentArea.style.opacity = '0.5';

        try {
            const response = await fetch(url, {
                headers: { 
                    'X-Requested-With': 'XMLHttpRequest',
                    'Accept': 'application/json' 
                }
            });
            const result = await response.json();

            if (response.ok && result.success && result.html) {
                const newUrl = `${window.location.pathname}?${params.toString()}`;
                history.pushState({ path: newUrl }, '', newUrl);
                adminContentArea.innerHTML = result.html;
                initAnimations();
                initReportFilter(); 
            } else {
                showNotification(result.message || 'Gagal memfilter laporan.', true);
            }
        } catch (error) {
            console.error('Report filter error:', error);
            showNotification('Error koneksi saat memfilter.', true);
        } finally {
            adminContentArea.style.opacity = '1';
        }
    };

    const checkAndTriggerUpdate = () => {
        if (startDateInput.value && endDateInput.value) {
            handleReportFilterRequest(false);
        }
    };

    startDateInput.addEventListener('change', checkAndTriggerUpdate);
    endDateInput.addEventListener('change', checkAndTriggerUpdate);

    const resetBtn = filterForm.querySelector('a.cta-button-secondary');
    if(resetBtn) {
        resetBtn.addEventListener('click', (e) => {
            e.preventDefault();
            filterForm.reset();
            handleReportFilterRequest(true);
        });
    }
}