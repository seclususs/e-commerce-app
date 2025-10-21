/**
 * Mengelola fungsionalitas UI spesifik admin seperti
 * aksi massal dan kartu yang dapat diperluas di tabel mobile.
 */
import { showNotification, confirmModal } from '../utils/ui.js';
import { handleAjaxSubmit } from './ajax-forms.js';

export function initAdminCardToggle() {
    const adminTable = document.querySelector('.admin-table');
    if (!adminTable) return;

    adminTable.addEventListener('click', (e) => {
        const toggleBtn = e.target.closest('.mobile-details-toggle');
        if (toggleBtn) {
            const row = toggleBtn.closest('.admin-card-row');
            row.classList.toggle('is-expanded');
            const isExpanded = row.classList.contains('is-expanded');
            toggleBtn.innerHTML = `${isExpanded ? 'Sembunyikan Detail' : 'Lihat Detail'} <i class="fas fa-chevron-down"></i>`;
        }
    });
}

export function initBulkActions() {
    const bulkActionForm = document.getElementById('bulk-action-form');
    if (!bulkActionForm) return;

    const selectAllCheckbox = document.getElementById('select-all-products');
    const productCheckboxes = document.querySelectorAll('.product-checkbox');
    const bulkActionSelect = document.getElementById('bulk-action-select');
    const bulkCategorySelector = document.getElementById('bulk-category-selector');

    if (selectAllCheckbox) {
        selectAllCheckbox.addEventListener('change', function() {
            productCheckboxes.forEach(checkbox => checkbox.checked = this.checked);
        });
    }

    if (bulkActionSelect) {
        bulkActionSelect.addEventListener('change', function() {
            if (bulkCategorySelector) {
                bulkCategorySelector.classList.toggle('hidden', this.value !== 'set_category');
            }
        });
    }

    bulkActionForm.addEventListener('submit', function(e) {
        e.preventDefault(); // Selalu cegah pengiriman form standar terlebih dahulu
        
        const selectedAction = bulkActionSelect ? bulkActionSelect.value : '';
        const anyProductSelected = document.querySelector('.product-checkbox:checked');
        const submitButton = bulkActionForm.querySelector('button[type="submit"]');

        if (!selectedAction || !anyProductSelected) {
            showNotification(
                !selectedAction ? 'Silakan pilih aksi massal.' : 'Silakan pilih setidaknya satu produk.', 
                true
            );
            return;
        }
        
        // Fungsi untuk menjalankan pengiriman AJAX
        const performSubmit = () => {
            if (submitButton) {
                handleAjaxSubmit(bulkActionForm, submitButton);
            }
        };

        if (selectedAction === 'delete') {
            // Tampilkan modal konfirmasi untuk tindakan hapus
            confirmModal.show(
                'Konfirmasi Hapus Massal',
                'Apakah Anda yakin ingin menghapus semua produk yang dipilih? Tindakan ini tidak dapat diurungkan.',
                performSubmit // Jalankan pengiriman AJAX hanya setelah konfirmasi
            );
        } else {
            performSubmit();
        }
    });
}