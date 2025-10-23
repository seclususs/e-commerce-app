export let selectedVariantId = null;


export function initSizeSelector() {
    const sizeSelector = document.getElementById('size-selector');
    if (!sizeSelector) return;

    const sizeWarning = document.getElementById('size-warning');
    const addToCartBtn = document.querySelector('.add-to-cart-btn');
    const quantityInput = document.getElementById('quantity-input');
    const stockDisplay = document.getElementById('stock-display');


    selectedVariantId = null;
    document.querySelectorAll('.size-option-btn').forEach(btn => btn.classList.remove('active'));
     if (addToCartBtn && addToCartBtn.dataset.hasVariants === 'true') {
        addToCartBtn.disabled = true;
         if (sizeWarning) sizeWarning.textContent = 'Silakan pilih ukuran terlebih dahulu.';
    }


    sizeSelector.addEventListener('click', (e) => {
        const target = e.target.closest('.size-option-btn');
        if (!target || target.disabled) return;

        document.querySelectorAll('.size-option-btn').forEach(btn => btn.classList.remove('active'));
        target.classList.add('active');

        selectedVariantId = target.dataset.variantId;
        const maxStock = parseInt(target.dataset.stock, 10);

        if (sizeWarning) sizeWarning.textContent = '';
        if (addToCartBtn) addToCartBtn.disabled = false;

        if (quantityInput) {
            quantityInput.max = maxStock;
            if (parseInt(quantityInput.value) > maxStock) {
                quantityInput.value = maxStock;
            }
            quantityInput.dispatchEvent(new Event('input'));
        }

        if (stockDisplay) {
             stockDisplay.innerHTML = `<span style="color: #f59e0b;">Ukuran ${target.textContent}: ${maxStock}</span>`;
        }

        const plusBtn = document.getElementById('quantity-plus');
        if (plusBtn) {
            plusBtn.disabled = (quantityInput && parseInt(quantityInput.value) >= maxStock);
        }
    });
}