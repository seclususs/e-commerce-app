/**
 * Mengelola pemfilteran produk secara asinkron menggunakan Fetch API.
 * Mencegah muat ulang halaman penuh saat filter diubah.
 */
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
        // Tampilkan jumlah skeleton yang sesuai, misal 8
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

            if (data.html && data.html.trim() !== '') {
                 container.innerHTML = data.html;
            } else {
                 container.innerHTML = noProductsTemplate;
            }
           
            // Panggil kembali fungsi animasi setelah konten baru dimuat
            // agar kartu produk yang baru muncul juga memiliki efek animasi.
            if (typeof initAnimations === 'function') {
                initAnimations();
            }
           
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

                const canvas = document.getElementById('filterOffCanvas');
                if (canvas && canvas.classList.contains('active')) {
                    document.getElementById('closeFilterBtn').click();
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