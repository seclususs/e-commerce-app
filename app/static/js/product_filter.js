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

    const handleFilterChange = async (form) => {
        const formData = new FormData(form);
        const params = new URLSearchParams(formData);
        const url = `/api/products?${params.toString()}`;

        // Tambahkan status loading untuk memberikan umpan balik visual
        container.style.opacity = '0.5';
        container.style.transition = 'opacity 0.3s ease-out';

        try {
            const response = await fetch(url);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const data = await response.json();

            // Perbarui URL di bilah alamat browser tanpa memuat ulang halaman
            const newUrl = `/products?${params.toString()}`;
            history.pushState({ path: newUrl }, '', newUrl);

            // Perbarui konten dengan efek fade
            if (data.html && data.html.trim() !== '') {
                 container.innerHTML = data.html;
            } else {
                 container.innerHTML = noProductsTemplate;
            }
           
        } catch (error) {
            console.error('Gagal mengambil data produk:', error);
            container.innerHTML = '<p class="no-products-found">Gagal memuat produk. Silakan coba lagi.</p>';
        } finally {
            // Hilangkan status loading
            container.style.opacity = '1';
        }
    };

    [formDesktop, formMobile].forEach(form => {
        if (form) {
            // Tangani pengiriman form (misalnya, menekan Enter di kolom pencarian)
            form.addEventListener('submit', (e) => {
                e.preventDefault();
                handleFilterChange(form);

                // Jika di perangkat mobile, tutup panel filter setelah diterapkan
                const canvas = document.getElementById('filterOffCanvas');
                if (canvas && canvas.classList.contains('active')) {
                    document.getElementById('closeFilterBtn').click();
                }
            });

            // Tangani perubahan langsung pada input radio (kategori, urutan)
            form.addEventListener('change', (e) => {
                if (e.target.type === 'radio') {
                    handleFilterChange(form);
                }
            });
        }
    });
}