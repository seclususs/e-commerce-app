import { initAnimations } from './utils/animations.js';
import { initFlashMessages } from './utils/ui.js';
import { initThemeSwitcher } from './utils/theme.js';
import { cartStore } from './state/cart-store.js';
import { initLogout } from './shared/auth.js';
import { initActionConfirmations } from './shared/confirmations.js';
import { initPageTransitions } from './utils/page-transitions.js';
import { initGlobalAddToCart } from './components/product-card.js';
import { initProductCatalogPage } from './pages/product-catalog.js';
import { initProductDetailPage } from './pages/product-detail.js';
import { initCheckoutPage } from './pages/checkout.js';
import { initPaymentPage } from './pages/payment.js';
import { initProfileEditor, initUserProfile } from './pages/profile.js';
import { initCartPage } from './pages/cart.js';
import { initRegisterPage } from './pages/auth/register.js';
import { initForgotPasswordPage } from './pages/auth/forgot-password.js';


document.addEventListener('DOMContentLoaded', async () => {
    // Inisialisasi modul global
    initPageTransitions('.page-content-wrapper');
    initAnimations();
    initFlashMessages();
    initLogout();
    initActionConfirmations();
    initThemeSwitcher();
    initGlobalAddToCart();
    
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
    if (document.querySelector('.profile-container form')) {
        initProfileEditor();
    }
    if (document.querySelector('.user-profile-section #orders-list')) {
        initUserProfile();
    }
    if (document.getElementById('register-form')) {
        initRegisterPage();
    }
    if (document.getElementById('forgot-password-form')) {
        initForgotPasswordPage();
    }
});