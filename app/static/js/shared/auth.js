/**
 * Menangani event logout, memastikan keranjang belanja di localStorage dibersihkan.
 */
export function initLogout() {
    document.body.addEventListener('click', (e) => {
        const logoutLink = e.target.closest('#logoutLink, #mobileLogoutLink');
        if (logoutLink) {
            e.preventDefault();
            localStorage.removeItem('hackthreadCart');
            window.location.href = logoutLink.href;
        }
    });
}