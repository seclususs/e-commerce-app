/**
 * Mengelola pemfilteran produk secara asinkron menggunakan Fetch API
 * dan fungsionalitas modal filter di perangkat mobile.
 */
import { initAnimations } from '../utils/animations.js';

function initProductFiltering() {
    const formDesktop = document.getElementById('filter-form-desktop');
    const formMobile = document.getElementById('filter-form-mobile');
    const container = document.getElementById('product-grid-container');
    const noProductsTemplate = `<p class="no-products-found animated-element is-visible">Tidak ada produk yang cocok dengan pencarian atau filter Anda.</p>`;

    if (!formDesktop || !container) {
        return;
    }

    const createSkeletonCard = () => `
        <div class="product-card skeleton-card">
            <div class="skeleton-image"></div>
            <div class="skeleton-info">
                <div class="skeleton-line"></div>
                <div class="skeleton-line short"></div>
                <div class="skeleton-line button"></div>
            </div>
        </div>
    `;

    const showLoadingState = () => {
        let skeletons = '';
        for(let i = 0; i < 8; i++) {
            skeletons += createSkeletonCard();
        }
        container.innerHTML = skeletons;
    };

    const handleFilterChange = async (form) => {
        const formData = new FormData(form);
        const params = new URLSearchParams(formData);
        const url = `/api/products?${params.toString()}`;

        showLoadingState();

        try {
            const response = await fetch(url);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const data = await response.json();

            const newUrl = `/products?${params.toString()}`;
            history.pushState({ path: newUrl }, '', newUrl);

            container.innerHTML = data.html.trim() !== '' ? data.html : noProductsTemplate;
           
            // Panggil kembali animasi untuk kartu produk baru.
            initAnimations();
           
        } catch (error) {
            console.error('Gagal mengambil data produk:', error);
            container.innerHTML = '<p class="no-products-found">Gagal memuat produk. Silakan coba lagi.</p>';
        }
    };

    [formDesktop, formMobile].forEach(form => {
        if (form) {
            form.addEventListener('submit', (e) => {
                e.preventDefault();
                handleFilterChange(form);

                if (form.id === 'filter-form-mobile') {
                    document.getElementById('closeFilterBtn')?.click();
                }
            });

            form.addEventListener('change', (e) => {
                if (e.target.type === 'radio') {
                    handleFilterChange(form);
                }
            });
        }
    });
}

function initFilterModal() {
    const toggleBtn = document.getElementById('filterToggleButton');
    const closeBtn = document.getElementById('closeFilterBtn');
    const canvas = document.getElementById('filterOffCanvas');
    const overlay = document.getElementById('filterOverlay');

    if (!toggleBtn || !canvas || !overlay || !closeBtn) return;

    const openFilter = () => {
        canvas.classList.add('active');
        overlay.classList.add('active');
        document.body.style.overflow = 'hidden';
    };

    const closeFilter = () => {
        canvas.classList.remove('active');
        overlay.classList.remove('active');
        document.body.style.overflow = '';
    };

    toggleBtn.addEventListener('click', openFilter);
    closeBtn.addEventListener('click', closeFilter);
    overlay.addEventListener('click', closeFilter);
}

export function initProductCatalogPage() {
    initProductFiltering();
    initFilterModal();
}