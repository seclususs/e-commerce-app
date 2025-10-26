export function initLogout() {
    document.body.addEventListener('click', (e) => {
        const logoutLink = e.target.closest('#logoutLink, #mobileLogoutLink');
        if (logoutLink) {
            e.preventDefault();
            localStorage.removeItem('hackthreadVariantCart');
            window.location.href = logoutLink.href;
        }
    });
}