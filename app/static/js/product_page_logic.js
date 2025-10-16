/**
 * Mengelola interaksi di halaman detail produk,
 * seperti validasi stok pada input kuantitas.
 */
function initProductPage() {
    const quantityInput = document.getElementById('quantity-input');
    if (!quantityInput) return;

    const minusBtn = document.getElementById('quantity-minus');
    const plusBtn = document.getElementById('quantity-plus');
    const stockWarning = document.getElementById('stock-warning');
    const maxStock = parseInt(quantityInput.max, 10);
    const addToCartButtons = document.querySelectorAll('.add-to-cart-btn');

    const validateStock = () => {
        const currentValue = parseInt(quantityInput.value, 10);
        let warningMessage = '';

        if (currentValue >= maxStock) {
            warningMessage = `Stok tidak mencukupi, maksimum pembelian adalah ${maxStock} unit.`;
            plusBtn.disabled = true;
        } else {
            plusBtn.disabled = false;
        }

        minusBtn.disabled = currentValue <= 1;
        stockWarning.textContent = warningMessage;
    };

    const updateQuantity = (change) => {
        let currentValue = parseInt(quantityInput.value, 10);
        if (isNaN(currentValue)) currentValue = 1;

        let newValue = currentValue + change;
        if (newValue < 1) newValue = 1;
        if (newValue > maxStock) newValue = maxStock;
        
        quantityInput.value = newValue;
        validateStock();
    };

    minusBtn.addEventListener('click', () => updateQuantity(-1));
    plusBtn.addEventListener('click', () => updateQuantity(1));

    quantityInput.addEventListener('input', () => {
        let value = parseInt(quantityInput.value, 10);
        if (isNaN(value) || value < 1) {
            quantityInput.value = 1;
        } else if (value > maxStock) {
            quantityInput.value = maxStock;
        }
        validateStock();
    });

    // Inisialisasi status tombol
    validateStock();
}