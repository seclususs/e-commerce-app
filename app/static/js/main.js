document.addEventListener('DOMContentLoaded', () => {
    // Inisialisasi efek fade-out pada navigasi
    const pageWrapper = document.querySelector('.page-content-wrapper, .admin-main-content');
    if (pageWrapper) {
        document.body.addEventListener('click', (e) => {
            const link = e.target.closest('a');
            if (link && link.href && link.hostname === location.hostname &&
                !link.href.includes('#') && 
                link.target !== '_blank' &&
                !link.hasAttribute('data-no-transition')) {
                e.preventDefault();
                pageWrapper.classList.add('page-is-leaving');
                setTimeout(() => {
                    window.location.href = link.href;
                }, 300); // Sesuaikan dengan durasi transisi CSS
            }
        });
    }

    // Inisialisasi komponen lainnya
    initFlashMessages();
    initAnimations();
    cartModule.init();
    initOrderSuccessPage();
    initActionConfirmations();
    initQuickCheckout();
    initLogout();
    initProductGallery();
    initAdminImagePreviews();
    initFilterModal();
    initSwipeableGallery();
    initMobileCtaHandlers();
    initAdminCardToggle();
    initBulkActions();
    initAdminPriceFormatting();
    initProductFiltering(); // Untuk katalog produk
    initProductPage();      // Untuk detail produk
    initCheckoutForm();     // Untuk halaman checkout
});