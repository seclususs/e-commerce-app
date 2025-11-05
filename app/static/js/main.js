import { initAnimations } from './utils/animations.js';
import { initFlashMessages } from './utils/flash-messages.js';
import { initThemeSwitcher } from './utils/theme.js';
import { cartStore } from './store/cart-store.js';
import { initLogout } from './services/auth.service.js';
import { initActionConfirmations } from './utils/confirmations.util.js';
import { initPageTransitions } from './utils/page-transitions.js';
import { initAjaxNavigationPublic } from './utils/ajax-navigation.js';
import { initGlobalAddToCart } from './components/product-card.js';
import { initProductCatalogPage } from './pages/product-catalog.js';
import { initProductDetailPage } from './pages/product-detail.js';
import { initCheckoutPage } from './pages/checkout.js';
import { initPaymentPage } from './pages/payment.js';
import { initProfileEditor, initUserProfile } from './pages/profile.js';
import { initCartPage } from './pages/cart.js';
import { initRegisterPage } from './pages/auth/register.js';
import { initForgotPasswordPage } from './pages/auth/forgot-password.js';
import { initMembershipPage } from './pages/membership.js';
import { initSuccessPage } from './pages/success.js';
import { initGuestSubscribePage } from './pages/guest-subscribe.js';

function initializePageScripts() {
    initAnimations();
    initFlashMessages();
    initThemeSwitcher();
    initGlobalAddToCart();
    initActionConfirmations();

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
    if (document.querySelector('.membership-page-section')) {
        initMembershipPage();
    }
    if (document.querySelector('.guest-subscribe-page')) {
        initGuestSubscribePage();
    }
    if (document.querySelector('.order-success-page')) {
        initSuccessPage();
    }
}

document.addEventListener('DOMContentLoaded', async () => {
    initLogout();
    initAjaxNavigationPublic();
    initPageTransitions('main.page-content-wrapper');

    await cartStore.init();

    const justLoggedInFlag = document.getElementById('just-logged-in-flag');
    if (justLoggedInFlag) {
        await cartStore.syncOnLogin();
    }

    initializePageScripts();

});