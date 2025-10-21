/**
 * Menangani filter produk di halaman admin via AJAX secara real-time.
 */
import { showNotification } from '../../utils/ui.js';
import { initAnimations } from '../../utils/animations.js';

// Helper untuk debounce, menunda eksekusi fungsi agar tidak berjalan pada setiap ketikan
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

    /**
     * Mengirim request filter ke server dan memperbarui tabel.
     * @param {boolean} isReset - Apakah ini aksi reset filter.
     */
    const handleFilterRequest = async (isReset = false) => {
        const params = isReset ? new URLSearchParams() : new URLSearchParams(new FormData(filterForm));
        
        // Hapus parameter kosong dari URL agar lebih bersih
        if (!isReset) {
            for (let [key, value] of new FormData(filterForm).entries()) {
                if (!value) {
                    params.delete(key);
                }
            }
        }
        
        const url = `${filterForm.action}?${params.toString()}`;
        tableBody.style.opacity = '0.5'; // Indikator loading

        try {
            const response = await fetch(url, {
                headers: { 'X-Requested-With': 'XMLHttpRequest' }
            });
            const result = await response.json();

            if (response.ok && result.success) {
                // Perbarui URL di browser tanpa me-reload halaman
                const newUrl = `${window.location.pathname}?${params.toString()}`;
                window.history.pushState({ path: newUrl }, '', newUrl);
                
                // Ganti isi tabel dengan hasil baru
                tableBody.innerHTML = result.html;
                initAnimations(); // Inisialisasi ulang animasi untuk baris baru
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

    // Listener untuk input pencarian dengan debounce
    searchInput.addEventListener('input', () => {
        debounce(() => handleFilterRequest(), 400); // Tunda 400ms setelah user berhenti mengetik
    });

    // Listener untuk perubahan pada dropdown (select)
    filterForm.addEventListener('change', (e) => {
        if (e.target.tagName === 'SELECT') {
            handleFilterRequest();
        }
    });
    
    // Mencegah form di-submit secara tradisional (misal: menekan Enter)
    filterForm.addEventListener('submit', (e) => {
        e.preventDefault();
        handleFilterRequest();
    });

    // Listener untuk tombol reset
    if (resetBtn) {
        resetBtn.addEventListener('click', (e) => {
            e.preventDefault();
            filterForm.reset();
            handleFilterRequest(true); // Kirim request dengan flag reset
        });
    }
}