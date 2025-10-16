/**
 * Mengelola logika untuk halaman checkout,
 * termasuk menampilkan indikator pemrosesan pada tombol.
 */
function initCheckoutForm() {
    const form = document.getElementById('checkout-form');
    if (!form) return;

    const placeOrderBtn = document.getElementById('placeOrderBtn');
    const placeOrderBtnMobile = document.getElementById('placeOrderBtnMobile');
    const buttons = [placeOrderBtn, placeOrderBtnMobile].filter(Boolean);

    // Menangani klik pada tombol mobile untuk mengirimkan form utama
    if (placeOrderBtnMobile) {
        placeOrderBtnMobile.addEventListener('click', () => {
            if (!placeOrderBtnMobile.disabled) {
                form.requestSubmit();
            }
        });
    }

    form.addEventListener('submit', (e) => {
        // Validasi sederhana sebelum menonaktifkan tombol
        if (!form.checkValidity()) {
            return;
        }

        buttons.forEach(btn => {
            btn.disabled = true;
            btn.classList.add('is-loading');
            btn.innerHTML = `<span class="spinner"></span><span>Memproses...</span>`;
        });
    });
}