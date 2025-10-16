document.addEventListener('DOMContentLoaded', () => {
    initFlashMessages();
    initAnimations();
    cartModule.init();

    // Event handler spesifik halaman
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
});