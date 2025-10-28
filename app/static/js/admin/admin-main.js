import { initAnimations } from '../utils/animations.js';
import { initFlashMessages } from '../utils/flash-messages.js';
import { initThemeSwitcher } from '../utils/theme.js';
import { initLogout } from '../services/auth.service.js';
import { initAjaxAdminForms } from './services/ajax-forms.service.js';
import { initProductForms } from './components/product-forms.component.js';
import { initAdminCardToggle, initBulkActions } from './utils/ui-handlers.util.js';
import { initSettingsPage } from './components/settings.component.js';
import { initDashboardCharts } from './components/charts/dashboard-charts.component.js';
import { initAdminProductFilter } from './components/filters/product-filter.component.js';
import { initAdminOrderFilter } from './components/filters/order-filter.component.js';
import { initDashboardFilter } from './components/filters/dashboard-filter.component.js';
import { initCronButton } from './utils/cron-simulator.util.js';
import { initSidebarToggle } from './components/sidebar-toggle.component.js';

export function reinitializeAdminScripts() {
    console.log("Reinitializing Admin Scripts...");
    initAnimations();
    initFlashMessages();
    initAjaxAdminForms();
    initAdminCardToggle();

    if (document.getElementById('salesChart') && typeof Chart !== 'undefined') {
        console.log("Initializing Dashboard Charts...");
        initDashboardCharts();
        initDashboardFilter();
    } else if (document.getElementById('salesChart') && typeof Chart === 'undefined'){
         console.warn("Chart elements found, but Chart.js library is not defined globally.");
    }
    if (document.getElementById('admin-product-filter-form')) {
        console.log("Initializing Product Filter...");
        initAdminProductFilter();
    }
    if (document.getElementById('admin-order-filter-form')) {
         console.log("Initializing Order Filter...");
        initAdminOrderFilter();
    }
    if (document.getElementById('run-cron-btn')) {
         console.log("Initializing Cron Button...");
        initCronButton();
    }
    if (document.querySelector('form[action*="/admin/products"]') || document.querySelector('form[action*="/admin/edit_product"]') || document.querySelector('form[action*="/admin/manage_variants"]')) {
         console.log("Initializing Product Forms...");
        initProductForms();
    }
    if (document.getElementById('bulk-action-form')) {
         console.log("Initializing Bulk Actions...");
        initBulkActions();
    }
    if (document.getElementById('social-links-container')) {
         console.log("Initializing Settings Page...");
        initSettingsPage();
    }
}

document.addEventListener('DOMContentLoaded', () => {
    initLogout();
    initThemeSwitcher();
    initSidebarToggle();
    reinitializeAdminScripts();
});