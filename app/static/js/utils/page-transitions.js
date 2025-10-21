/**
 * Menginisialisasi efek transisi 'fade out' saat meninggalkan halaman.
 * @param {string} wrapperSelector Selector untuk elemen wrapper konten utama.
 */
export function initPageTransitions(wrapperSelector) {
    const pageWrapper = document.querySelector(wrapperSelector);
    if (!pageWrapper) return;

    document.body.addEventListener('click', (e) => {
        const link = e.target.closest('a');

        const isDisabledCartLink = link && (link.id === 'checkout-link' || link.id === 'checkout-link-mobile') && link.classList.contains('disabled-link');
        if (isDisabledCartLink) {
             e.preventDefault();
             return;
        }

        if (link && link.href && link.hostname === location.hostname &&
            !link.href.includes('#') && 
            link.target !== '_blank' &&
            !link.hasAttribute('data-ajax') &&
            !link.hasAttribute('data-no-transition')) {
            
            e.preventDefault();
            pageWrapper.classList.add('page-is-leaving');
            setTimeout(() => { window.location.href = link.href; }, 300);
        }
    });
}