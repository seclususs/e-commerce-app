/**
 * File entri utama untuk semua skrip di sisi admin.
 * Mengimpor dan menginisialisasi modul yang diperlukan.
 */
import { initAnimations } from '../utils/animations.js';
import { initFlashMessages } from '../utils/ui.js';
import { initLogout } from '../shared/auth.js';
import { initActionConfirmations } from '../shared/confirmations.js';
import { initProductForms } from './product-forms.js';
import { initAdminCardToggle, initBulkActions } from './ui-handlers.js';
import { initDashboardCharts } from './dashboard-charts.js';
import { initSettingsPage } from './settings.js';

document.addEventListener('DOMContentLoaded', () => {
    // Inisialisasi efek transisi halaman
    const pageWrapper = document.querySelector('.admin-main-content');
    if (pageWrapper) {
        document.body.addEventListener('click', (e) => {
            const link = e.target.closest('a');
            if (link && link.href && link.hostname === location.hostname &&
                !link.href.includes('#') && link.target !== '_blank' &&
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
    initActionConfirmations();
    initAdminCardToggle();
    
    // Inisialisasi modul spesifik per halaman admin
    if (document.getElementById('salesChart')) {
        initDashboardCharts();
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