import { initDashboardCharts } from './charts/dashboard-charts.component.js';

export function initSidebarToggle() {
    const desktopToggleBtn = document.getElementById('sidebarToggleBtn');
    const mobileToggleBtn = document.getElementById('mobileSidebarToggleBtn');
    const closeBtn = document.getElementById('sidebarCloseBtn');
    const overlay = document.getElementById('sidebarOverlay');
    const rootElement = document.documentElement;
    const desktopIcon = desktopToggleBtn ? desktopToggleBtn.querySelector('i') : null;
    const chartWrappers = [
        document.getElementById('salesChart')?.parentElement,
        document.getElementById('topProductsChart')?.parentElement,
        document.getElementById('lowStockChart')?.parentElement
    ].filter(Boolean);

    const toggleSidebar = () => {
        const isMobile = window.innerWidth <= 767;
        let isCollapsedNow = false;
        const isDashboard = chartWrappers.length > 0;

        if (isDashboard) {
            chartWrappers.forEach(wrapper => {
                wrapper.style.display = 'none';
            });
        }

        if (isMobile) {
            rootElement.classList.toggle('sidebar-mobile-open');
            rootElement.classList.remove('sidebar-collapsed');
            localStorage.removeItem('sidebarState');
        } else {
            isCollapsedNow = rootElement.classList.toggle('sidebar-collapsed');
            localStorage.setItem('sidebarState', isCollapsedNow ? 'collapsed' : 'expanded');
            rootElement.classList.remove('sidebar-mobile-open');
        }

        if (isDashboard) {
            setTimeout(() => {
                chartWrappers.forEach(wrapper => {
                    wrapper.style.display = 'block';
                });
                initDashboardCharts();
            }, 350);
        }
    };

    if (desktopToggleBtn) {
        desktopToggleBtn.addEventListener('click', toggleSidebar);
    }
    if (mobileToggleBtn) {
        mobileToggleBtn.addEventListener('click', toggleSidebar);
    }

    if (closeBtn) {
        closeBtn.addEventListener('click', () => {
            rootElement.classList.remove('sidebar-mobile-open');
        });
    }

    if (overlay) {
        overlay.addEventListener('click', () => {
            rootElement.classList.remove('sidebar-mobile-open');
        });
    }

    window.addEventListener('resize', () => {
        const isMobile = window.innerWidth <= 767;
        let isCollapsedOnResize = false;
        if (!isMobile) {
            rootElement.classList.remove('sidebar-mobile-open');
            if (localStorage.getItem('sidebarState') === 'collapsed') {
                rootElement.classList.add('sidebar-collapsed');
                isCollapsedOnResize = true;
            } else {
                rootElement.classList.remove('sidebar-collapsed');
                isCollapsedOnResize = false;
            }
        } else {
             rootElement.classList.remove('sidebar-collapsed');
             isCollapsedOnResize = false;
        }
    });

     window.dispatchEvent(new Event('resize'));
}