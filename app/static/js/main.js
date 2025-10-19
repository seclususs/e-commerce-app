import { initAnimations } from './utils/animations.js';
import { initFlashMessages } from './utils/ui.js';
import { cartModule } from './pages/cart.js';
import { initLogout } from './shared/auth.js';
import { initActionConfirmations } from './shared/confirmations.js';
import { initProductCatalogPage } from './pages/product-catalog.js';
import { initProductDetailPage } from './pages/product-detail.js';
import { initCheckoutPage } from './pages/checkout.js';

document.addEventListener('DOMContentLoaded', async () => {
    // Inisialisasi efek transisi halaman
    const pageWrapper = document.querySelector('.page-content-wrapper');
    if (pageWrapper) {
        document.body.addEventListener('click', (e) => {
            const link = e.target.closest('a');
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
    
    // Inisialisasi modul keranjang
    cartModule.init();

    // Cek jika pengguna baru saja login untuk sinkronisasi keranjang
    const justLoggedInFlag = document.getElementById('just-logged-in-flag');
    if(justLoggedInFlag){
        await cartModule.syncOnLogin();
    }

    // Inisialisasi modul spesifik per halaman
    if (document.querySelector('.products-page-section')) {
        initProductCatalogPage();
    }
    if (document.querySelector('.product-detail-section')) {
        initProductDetailPage();
    }
    if (document.querySelector('.checkout-page-section')) {
        initCheckoutPage();
    }
});