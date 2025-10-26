import { initAnimations } from '../utils/animations.js';
import { initFlashMessages } from '../utils/flash-messages.js';
import { initThemeSwitcher } from '../utils/theme.js';
import { initLogout } from '../services/auth.service.js';
import { initPageTransitions } from '../utils/page-transitions.js';
import { initAjaxAdminForms } from './services/ajax-forms.service.js';
import { initProductForms } from './components/product-forms.component.js';
import { initAdminCardToggle, initBulkActions } from './utils/ui-handlers.util.js';
import { initSettingsPage } from './components/settings.component.js';
import { initDashboardCharts } from './components/charts/dashboard-charts.component.js';
import { initAdminProductFilter } from './components/filters/product-filter.component.js';
import { initAdminOrderFilter } from './components/filters/order-filter.component.js';
import { initDashboardFilter } from './components/filters/dashboard-filter.component.js';
import { initCronButton } from './utils/cron-simulator.util.js';

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