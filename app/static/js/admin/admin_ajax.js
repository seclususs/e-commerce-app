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
                // headers: {
                //     'X-Requested-With': 'XMLHttpRequest',
                //     'Accept': 'text/html' 
                //  }
            });

            if (!response.ok) {
                 let errorMsg = `HTTP error! status: ${response.status} ${response.statusText}`;
                 try {
                     const errorJson = await response.json();
                     errorMsg = errorJson.message || errorJson.error || errorMsg;
                 } catch (e) { /* Ignore if not JSON */ }
                 throw new Error(errorMsg);
            }

            const html = await response.text();
            const parser = new DOMParser();
            const doc = parser.parseFromString(html, 'text/html');

            const newContent = doc.getElementById('adminContentArea');
            const newTitle = doc.querySelector('title');
            const newHeader = doc.getElementById('adminHeaderTitle');
            const newFlashMessages = doc.getElementById('flashMessagesContainer');

            if (newContent) {
                contentArea.innerHTML = newContent.innerHTML;
                if (newHeader) {
                    headerTitle.innerHTML = newHeader.innerHTML;
                } else {
                     const h2Fallback = doc.querySelector('.admin-main-header h2');
                     headerTitle.innerHTML = h2Fallback ? h2Fallback.innerHTML : 'Admin Area';
                }
                if (newTitle) {
                    document.title = newTitle.textContent;
                }
                 if (newFlashMessages) {
                    flashMessagesContainer.innerHTML = newFlashMessages.innerHTML;
                } else {
                     flashMessagesContainer.innerHTML = '';
                 }

                history.pushState({ endpoint: targetEndpoint }, '', url);
                setActiveLink(targetEndpoint);
                document.documentElement.dataset.currentEndpoint = targetEndpoint;
                contentArea.style.display = 'block';
                contentArea.style.opacity = '1';
                reinitializeAdminScripts();

            } else {
                console.error('Could not find #adminContentArea in fetched HTML');
                showNotification('Gagal memuat konten halaman (struktur tidak valid).', true);
                 contentArea.style.display = 'block';
                 contentArea.style.opacity = '1';
                 contentArea.innerHTML = '<p style="color: var(--color-danger);">Gagal memuat konten. Silakan coba lagi.</p>';
            }

        } catch (error) {
            console.error('Error loading content via AJAX:', error);
            showNotification(`Gagal memuat halaman: ${error.message}. Coba muat ulang.`, true);
             loadingIndicator.innerHTML = `<p style="color: var(--color-danger);">Gagal memuat konten. Silakan <a href="${url}">muat ulang halaman</a>.</p>`;
             contentArea.style.display = 'none';
             loadingIndicator.style.display = 'block';

        } finally {
             if (!loadingIndicator.innerHTML.includes('Gagal memuat')) {
                  loadingIndicator.style.display = 'none';
             }
             document.documentElement.classList.remove('content-loading');
        }
    };

    const handleLinkClick = (e) => {
        const link = e.target.closest('a.ajax-link');
        if (!link || !link.href || link.classList.contains('active') || link.hostname !== location.hostname || link.pathname === location.pathname || link.hash) {
            return;
        }

        if (link.id === 'logoutLink') {
            return;
        }

        e.preventDefault();
        e.stopPropagation();

        const url = link.href;
        const targetEndpoint = link.dataset.endpoint;

        if (!targetEndpoint) {
            console.warn("AJAX link clicked but missing data-endpoint:", link);
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
         console.warn("Initial endpoint not found in dataset.");
    }
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initAdminAjaxNavigation);
} else {
    initAdminAjaxNavigation();
}