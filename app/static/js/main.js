document.addEventListener('DOMContentLoaded', () => {
    // Inisialisasi modul UI
    initFlashMessages();
    
    // Inisialisasi modul lain
    initAnimations();
    cartModule.init();

    // Inisialisasi event handler spesifik halaman
    initOrderSuccessPage();
    initActionConfirmations();
    initQuickCheckout();
    initLogout();
    initProductGallery();
    initAdminImagePreviews();
    initFilterModal();
    initSwipeableGallery();
    initMobileCtaHandlers(); // Untuk tombol checkout mobile
    initAdminCardToggle();   // Untuk kartu admin mobile
});