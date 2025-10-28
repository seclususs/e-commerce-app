import { showNotification } from '../components/notification.js';
import { reinitializeAdminScripts } from './admin-main.js';

function initAdminAjaxNavigation() {
    const adminNav = document.getElementById('adminNav');
    const bottomNav = document.querySelector('.bottom-navbar');
    const contentArea = document.getElementById('adminContentArea');
    const headerTitle = document.getElementById('adminHeaderTitle');
    const loadingIndicator = document.getElementById('loadingIndicator');
    const flashMessagesContainer = document.getElementById('flashMessagesContainer');

    const setActiveLink = (targetEndpoint) => {
        const links = document.querySelectorAll('#adminNav .ajax-link, .bottom-navbar .ajax-link');
        links.forEach(link => {
            link.classList.remove('active');
            if (link.dataset.endpoint && link.dataset.endpoint === targetEndpoint) {
                link.classList.add('active');
            }
        });
    };

    const loadContent = async (url, targetEndpoint) => {
        if (!contentArea || !headerTitle || !loadingIndicator || !flashMessagesContainer) {
             console.error("Essential AJAX elements not found.");
             return;
        }

        flashMessagesContainer.innerHTML = '';
        contentArea.style.opacity = '0';
        contentArea.style.display = 'none';
        loadingIndicator.style.display = 'block';
        document.documentElement.classList.add('content-loading');

        try {
            const response = await fetch(url, {
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'Accept': 'application/json'
                 }
            });

            const result = await response.json();

            if (!response.ok || !result.success) {
                 throw new Error(result.message || `HTTP error! status: ${response.status}`);
            }

            if (result.html && result.page_title && result.header_title) {
                contentArea.innerHTML = result.html;
                headerTitle.textContent = result.header_title;
                document.title = result.page_title;
                history.pushState({ endpoint: targetEndpoint }, '', url);
                setActiveLink(targetEndpoint);
                document.documentElement.dataset.currentEndpoint = targetEndpoint;
                contentArea.style.display = 'block';
                contentArea.style.opacity = '1';
                reinitializeAdminScripts();

            } else {
                console.error('Invalid JSON structure received:', result);
                throw new Error('Gagal memuat konten halaman (struktur respons tidak valid).');
            }

        } catch (error) {
            console.error('Error loading content via AJAX:', error);
            showNotification(`Gagal memuat halaman: ${error.message}. Coba muat ulang.`, true);
            loadingIndicator.innerHTML = `<p style="color: var(--color-danger);">Gagal memuat konten. Silakan <a href="${url}">muat ulang halaman</a>.</p>`;
            contentArea.style.display = 'none';
            loadingIndicator.style.display = 'block';

        } finally {
             if (!loadingIndicator.innerHTML.includes('Gagal memuat konten')) {
                  loadingIndicator.style.display = 'none';
             }
             document.documentElement.classList.remove('content-loading');
        }
    };

    const handleLinkClick = (e) => {
        const link = e.target.closest('a.ajax-link');
        if (!link || !link.href || link.classList.contains('active') || link.hostname !== location.hostname || link.pathname === location.pathname || link.hash || link.hasAttribute('data-no-transition')) {
            return;
        }

        if (link.id === 'logoutLink' || link.id === 'mobileLogoutLink') {
            return;
        }

        e.preventDefault();
        e.stopPropagation();

        const url = link.href;
        const targetEndpoint = link.dataset.endpoint;

        if (!targetEndpoint) {
            console.warn("AJAX link clicked but missing data-endpoint:", link, ". Falling back to standard navigation.");
            window.location.href = url;
            return;
        }

        loadContent(url, targetEndpoint);

        const rootElement = document.documentElement;
        if (rootElement.classList.contains('sidebar-mobile-open')) {
             rootElement.classList.remove('sidebar-mobile-open');
             const overlay = document.getElementById('sidebarOverlay');
             if (overlay) overlay.classList.remove('active');
             document.body.style.overflow = '';
        }
    };

    if (adminNav) {
        adminNav.addEventListener('click', handleLinkClick);
    }
    if (bottomNav) {
        bottomNav.addEventListener('click', handleLinkClick);
    }

    window.addEventListener('popstate', (e) => {
        const targetEndpoint = e.state ? e.state.endpoint : document.documentElement.dataset.initialEndpoint;
        const currentDisplayedEndpoint = document.documentElement.dataset.currentEndpoint;
        console.log("Popstate event:", "Target:", targetEndpoint, "Current:", currentDisplayedEndpoint);
        if (targetEndpoint && targetEndpoint !== currentDisplayedEndpoint) {
            const link = document.querySelector(`.ajax-link[data-endpoint="${targetEndpoint}"]`);
            if (link) {
                 console.log("Loading content for popstate:", link.href, targetEndpoint);
                loadContent(link.href, targetEndpoint);
            } else {
                 console.warn("Could not find link for popstate endpoint:", targetEndpoint, ". Reloading page.");
                 window.location.reload();
            }
        } else if (!targetEndpoint && currentDisplayedEndpoint) {
             console.log("Popstate to initial page state. Reloading.");
             window.location.reload();
        }
    });

    const initialEndpoint = document.documentElement.dataset.currentEndpoint;
    if (initialEndpoint) {
         document.documentElement.dataset.initialEndpoint = initialEndpoint;
         history.replaceState({ endpoint: initialEndpoint }, '', window.location.href);
         console.log("Initial state saved for endpoint:", initialEndpoint);
    } else {
         console.warn("Initial endpoint not found in dataset on page load.");
    }
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initAdminAjaxNavigation);
} else {
    initAdminAjaxNavigation();
}