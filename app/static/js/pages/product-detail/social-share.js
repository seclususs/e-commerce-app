export function initSocialShare() {
    const shareLinksContainer = document.getElementById('social-share-links');
    if (!shareLinksContainer) return;

    shareLinksContainer.addEventListener('click', function(e) {
        const link = e.target.closest('a.social-share-btn');
        if (!link) return;

        e.preventDefault();
        const url = link.href;
        const windowWidth = 600;
        const windowHeight = 400;
        const left = (window.innerWidth / 2) - (windowWidth / 2);
        const top = (window.innerHeight / 2) - (windowHeight / 2);

        window.open(url, 'shareWindow',
            `width=${windowWidth},height=${windowHeight},top=${top},left=${left},` +
            `toolbar=no,location=no,directories=no,status=no,menubar=no,scrollbars=yes,resizable=yes`);
    });
}