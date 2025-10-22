import { initAnimations } from '../utils/animations.js';
import { initFlashMessages } from '../utils/ui.js';
import { initThemeSwitcher } from '../utils/theme.js';
import { initLogout } from '../shared/auth.js';
import { initPageTransitions } from '../utils/page-transitions.js';
import { initAjaxAdminForms } from './ajax-forms.js';
import { initProductForms } from './modules/product-forms.js';
import { initAdminCardToggle, initBulkActions } from './modules/ui-handlers.js';
import { initSettingsPage } from './modules/settings.js';
import { initDashboardCharts } from './charts/dashboard-charts.js';
import { initAdminProductFilter } from './filters/product-filter.js';
import { initAdminOrderFilter } from './filters/order-filter.js';
import { initDashboardFilter } from './filters/dashboard-filter.js';
import { initCronButton } from './utils/cron-simulator.js';

document.addEventListener('DOMContentLoaded', () => {
    initPageTransitions('.admin-main-content');
    initAnimations();
    initFlashMessages();
    initLogout();
    initThemeSwitcher();
    initAjaxAdminForms();
    initAdminCardToggle();

    if (document.getElementById('salesChart')) {
        initDashboardCharts();
        initDashboardFilter();
    }
    if (document.getElementById('admin-product-filter-form')) {
        initAdminProductFilter();
    }
    if (document.getElementById('admin-order-filter-form')) {
        initAdminOrderFilter();
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