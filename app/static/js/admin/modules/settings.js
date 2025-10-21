/**
 * Mengelola fungsionalitas untuk halaman pengaturan situs,
 * seperti menambah dan menghapus tautan sosial media secara dinamis.
 */
export function initSettingsPage() {
    const socialLinksContainer = document.getElementById('social-links-container');
    const addSocialLinkBtn = document.getElementById('add-social-link');
    const newSocialLinkInput = document.getElementById('new_social_link');
    const socialLinksInput = document.getElementById('social_links_input');

    if (!socialLinksContainer || !addSocialLinkBtn || !newSocialLinkInput || !socialLinksInput) {
        return;
    }

    let socialLinks = [];
    try {
        socialLinks = JSON.parse(socialLinksInput.value || '[]');
    } catch (e) {
        console.error("Error parsing social links JSON:", e);
        socialLinks = [];
    }

    function renderSocialLinks() {
        socialLinksContainer.innerHTML = '';
        socialLinksContainer.style.marginBottom = socialLinks.length > 0 ? '1.5rem' : '0';

        socialLinks.forEach((link, index) => {
            const linkEl = document.createElement('div');
            linkEl.className = 'social-link-item';
            linkEl.innerHTML = `
                <span class="social-link-text">${link}</span>
                <button type="button" class="remove-social-link" data-index="${index}" title="Hapus">&times;</button>
            `;
            socialLinksContainer.appendChild(linkEl);
        });
        updateHiddenInput();
    }

    function updateHiddenInput() {
        socialLinksInput.value = JSON.stringify(socialLinks);
    }

    addSocialLinkBtn.addEventListener('click', () => {
        const newLink = newSocialLinkInput.value.trim();
        if (newLink && newLink.startsWith('http') && !socialLinks.includes(newLink)) {
            socialLinks.push(newLink);
            newSocialLinkInput.value = '';
            newSocialLinkInput.focus();
            renderSocialLinks();
        } else if (!newLink.startsWith('http')) {
            alert('Silakan masukkan URL yang valid (dimulai dengan http atau https).');
        } else if (socialLinks.includes(newLink)) {
            alert('Tautan ini sudah ada.');
        }
    });

    newSocialLinkInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            addSocialLinkBtn.click();
        }
    });

    socialLinksContainer.addEventListener('click', (e) => {
        if (e.target.classList.contains('remove-social-link')) {
            const index = parseInt(e.target.dataset.index, 10);
            socialLinks.splice(index, 1);
            renderSocialLinks();
        }
    });

    renderSocialLinks();
}