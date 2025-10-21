/**
 * File entri utama untuk semua skrip di sisi admin.
 * Mengimpor dan menginisialisasi modul yang diperlukan.
 */
import { initAnimations } from '../utils/animations.js';
import { initFlashMessages, showNotification } from '../utils/ui.js';
import { initThemeSwitcher } from '../utils/theme.js';
import { initLogout } from '../shared/auth.js';
import { initProductForms } from './product-forms.js';
import { initAdminCardToggle, initBulkActions } from './ui-handlers.js';
import { initDashboardCharts } from './dashboard-charts.js';
import { initSettingsPage } from './settings.js';
import { initAjaxAdminForms } from './ajax-forms.js';

// Handler untuk filter produk admin via AJAX
function initAdminProductFilter() {
    const filterForm = document.getElementById('admin-product-filter-form');
    const tableBody = document.getElementById('products-table-body');
    const resetBtn = document.getElementById('reset-filter-btn');

    if (!filterForm || !tableBody) return;

    const handleFilterSubmit = async (form) => {
        const submitButton = form.querySelector('button[type="submit"]');
        const originalButtonText = submitButton.textContent;
        submitButton.disabled = true;
        submitButton.textContent = 'Memfilter...';

        const params = new URLSearchParams(new FormData(form));
        // Hapus parameter kosong
        for(let pair of params.entries()){
            if(!pair[1]) params.delete(pair[0]);
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
                initAnimations(); // Re-initialize animations for new rows
            } else {
                showNotification('Gagal memfilter produk.', true);
            }
        } catch (error) {
            console.error('Filter error:', error);
            showNotification('Error koneksi saat memfilter.', true);
        } finally {
            tableBody.style.opacity = '1';
            submitButton.disabled = false;
            submitButton.textContent = originalButtonText;
        }
    };

    filterForm.addEventListener('submit', (e) => {
        e.preventDefault();
        handleFilterSubmit(filterForm);
    });
    
    // Auto-submit on change for select dropdowns
    filterForm.addEventListener('change', (e) => {
        if (e.target.tagName === 'SELECT') {
            handleFilterSubmit(filterForm);
        }
    });

    if (resetBtn) {
        resetBtn.addEventListener('click', (e) => {
            e.preventDefault();
            filterForm.reset();
            handleFilterSubmit(filterForm);
        });
    }
}


// Handler untuk tombol simulasi cron job
function initCronButton() {
    const btn = document.getElementById('run-cron-btn');
    if (!btn) return;

    btn.addEventListener('click', async () => {
        const originalText = btn.textContent;
        btn.disabled = true;
        btn.innerHTML = `<span class="spinner" style="display: inline-block; animation: spin 0.8s ease-in-out infinite; width: 1em; height: 1em; border-width: 2px; margin-right: 0.5rem;"></span>Menjalankan...`;

        try {
            const response = await fetch(btn.dataset.url, {
                method: 'POST',
                headers: { 'X-Requested-With': 'XMLHttpRequest', 'Content-Type': 'application/json' }
            });
            const result = await response.json();
            showNotification(result.message || 'Gagal menjalankan tugas.', !result.success);
        } catch (e) {
            console.error('Cron sim error:', e);
            showNotification('Error koneksi.', true);
        } finally {
            btn.disabled = false;
            btn.innerHTML = originalText;
        }
    });
}


document.addEventListener('DOMContentLoaded', () => {
    // Inisialisasi efek transisi halaman (non-AJAX)
    const pageWrapper = document.querySelector('.admin-main-content');
    if (pageWrapper) {
        document.body.addEventListener('click', (e) => {
            const link = e.target.closest('a');
            if (link && link.href && link.hostname === location.hostname &&
                !link.href.includes('#') && link.target !== '_blank' &&
                !link.hasAttribute('data-ajax') &&
                !link.hasAttribute('data-no-transition')) {
                e.preventDefault();
                pageWrapper.classList.add('page-is-leaving');
                setTimeout(() => { window.location.href = link.href; }, 300);
            }
        });
    }

    // Inisialisasi modul global admin
    initAnimations();
    initFlashMessages();
    initLogout();
    initAdminCardToggle();
    initThemeSwitcher();
    initAjaxAdminForms();
    
    // Inisialisasi modul spesifik per halaman admin
    if (document.getElementById('salesChart')) {
        initDashboardCharts();
    }
    if (document.getElementById('admin-product-filter-form')) {
        initAdminProductFilter();
    }
    if (document.getElementById('run-cron-btn')) {
        initCronButton();
    }
    if (document.querySelector('form[action*="/admin/products"]') || document.querySelector('form[action*="/admin/edit_product"]')) {
        initProductForms();
    }
    if (document.getElementById('bulk-action-form')) {
        initBulkActions();
    }
    if (document.getElementById('social-links-container')) {
        initSettingsPage();
    }
});