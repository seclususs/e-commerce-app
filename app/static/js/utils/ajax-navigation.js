import { showNotification } from '../components/notification.js';
import { initAnimations } from './animations.js';
import { initProductCatalogPage } from '../pages/product-catalog.js';
import { initProductDetailPage } from '../pages/product-detail.js';
import { initCartPage } from '../pages/cart.js';
import { initCheckoutPage } from '../pages/checkout.js';
import { initPaymentPage } from '../pages/payment.js';
import { initProfileEditor, initUserProfile } from '../pages/profile.js';

const contentWrapperSelector = 'main.page-content-wrapper';
const loadingClass = 'page-loading';
let isFallbackReloading = false;

function reinitializePublicScripts() {
    console.log("Reinitializing Public Scripts after AJAX load...");
    initAnimations();

    if (document.querySelector('.products-page-section')) {
        console.log("Initializing Product Catalog...");
        initProductCatalogPage();
    }
    if (document.querySelector('.product-detail-section')) {
        console.log("Initializing Product Detail...");
        initProductDetailPage();
    }
    if (document.querySelector('.cart-page-section')) {
        console.log("Initializing Cart Page...");
        initCartPage();
    }
    if (document.querySelector('.checkout-page-section')) {
        console.log("Initializing Checkout Page...");
        initCheckoutPage();
    }
     if (document.querySelector('.payment-page-section')) {
        console.log("Initializing Payment Page...");
        initPaymentPage();
    }
    if (document.querySelector('.profile-container form')) {
        console.log("Initializing Profile Editor...");
        initProfileEditor();
    }
     if (document.querySelector('.user-profile-section #orders-list')) {
        console.log("Initializing User Profile View...");
        initUserProfile();
    }
     if (document.querySelector('.order-tracking-section')) {
        console.log("Initializing Order Tracking...");
    }
     if (document.querySelector('.about-section-full')) {
         console.log("Initializing About Page...");
     }
     if (document.querySelector('.hero')) {
         console.log("Initializing Landing Page...");
     }
}

async function loadContentPublic(url, isPopState = false) {
    const contentWrapper = document.querySelector(contentWrapperSelector);
    if (!contentWrapper) {
        console.error("Content wrapper not found:", contentWrapperSelector);
        window.location.href = url;
        return;
    }

    isFallbackReloading = false;
    document.body.classList.add(loadingClass);
    contentWrapper.style.opacity = '0.5';

    try {
        const response = await fetch(url, {
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'Accept': 'application/json'
            }
        });

        const result = await response.json();

        if (!response.ok || !result.success) {
            if (result.redirect_url) {
                showNotification(result.message || 'Sesi tidak valid, mengarahkan ke login...', true);
                isFallbackReloading = true;
                setTimeout(() => { window.location.href = result.redirect_url; }, 1500);
                return;
            }
            throw new Error(result.message || `HTTP error! status: ${response.status}`);
        }

        contentWrapper.innerHTML = result.html;
        document.title = result.page_title || document.title;

        if (!isPopState) {
            history.pushState({ url: url, title: result.page_title }, result.page_title, url);
        }

        window.scrollTo(0, 0);
        reinitializePublicScripts();


    } catch (error) {
        console.error('Error loading public content via AJAX:', error);
        showNotification(`Gagal memuat halaman: ${error.message}. Memuat ulang...`, true);
        isFallbackReloading = true;
        setTimeout(() => { window.location.href = url; }, 1500);
        return;

    } finally {
        if (!isFallbackReloading) {
           document.body.classList.remove(loadingClass);
           contentWrapper.style.opacity = '1';
        }
    }
}

export function initAjaxNavigationPublic() {
    document.body.addEventListener('click', (e) => {
        const link = e.target.closest('a[data-ajax-nav="true"]');

        if (!link || !link.href || e.ctrlKey || e.metaKey || e.shiftKey || link.target === '_blank' || link.hostname !== location.hostname) {
            return;
        }

        e.preventDefault();

        const url = link.href;
        if (url === window.location.href) {
            return;
        }

        loadContentPublic(url);
    });

    window.addEventListener('popstate', (e) => {
        if (e.state && e.state.url) {
            if (e.state.url !== window.location.href) {
                console.log("Popstate event:", e.state.url);
                loadContentPublic(e.state.url, true);
            }
        } else {
             console.log("Popstate to initial state or invalid state, checking if reload needed.");
        }
    });

    history.replaceState({ url: window.location.href, title: document.title }, document.title, window.location.href);
    console.log("Initial public page state saved:", window.location.href);
}