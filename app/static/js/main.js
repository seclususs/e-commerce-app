import { initAnimations } from './utils/animations.js';
import { initFlashMessages } from './utils/ui.js';
import { initThemeSwitcher } from './utils/theme.js';
import { cartStore } from './state/cart-store.js';
import { initLogout } from './shared/auth.js';
import { initActionConfirmations } from './shared/confirmations.js';
import { initProductCatalogPage } from './pages/product-catalog.js';
import { initProductDetailPage } from './pages/product-detail.js';
import { initCheckoutPage } from './pages/checkout.js';
import { initPaymentPage } from './pages/payment.js';
import { initProfileEditor } from './pages/profile.js';
import { initCartPage } from './pages/cart.js';


document.addEventListener('DOMContentLoaded', async () => {
    // Inisialisasi efek transisi halaman
    const pageWrapper = document.querySelector('.page-content-wrapper');
    if (pageWrapper) {
        document.body.addEventListener('click', (e) => {
            const link = e.target.closest('a');
            
            // Cek jika link checkout/cart dinonaktifkan
            const isDisabledLink = link && (link.id === 'checkout-link' || link.id === 'checkout-link-mobile') && link.classList.contains('disabled-link');
            if (isDisabledLink) {
                 e.preventDefault();
                 return;
            }

            if (link && link.href && link.hostname === location.hostname &&
                !link.href.includes('#') && 
                link.target !== '_blank' &&
                !link.hasAttribute('data-no-transition')) {
                e.preventDefault();
                pageWrapper.classList.add('page-is-leaving');
                setTimeout(() => { window.location.href = link.href; }, 300);
            }
        });
    }

    // Inisialisasi modul
    initAnimations();
    initFlashMessages();
    initLogout();
    initActionConfirmations();
    initThemeSwitcher();
    
    // Inisialisasi state keranjang
    await cartStore.init();

    // Cek jika pengguna baru saja login untuk sinkronisasi keranjang
    const justLoggedInFlag = document.getElementById('just-logged-in-flag');
    if(justLoggedInFlag){
        await cartStore.syncOnLogin();
    }

    // Inisialisasi modul spesifik per halaman
    if (document.querySelector('.products-page-section')) {
        initProductCatalogPage();
    }
    if (document.querySelector('.product-detail-section')) {
        initProductDetailPage();
    }
    if (document.querySelector('.cart-page-section')) {
        initCartPage();
    }
    if (document.querySelector('.checkout-page-section')) {
        initCheckoutPage();
    }
    if (document.querySelector('.payment-page-section')) {
        initPaymentPage();
    }
    if (document.querySelector('.user-profile-section .profile-container form')) {
        initProfileEditor();
    }
});