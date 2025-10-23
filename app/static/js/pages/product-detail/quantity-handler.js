export function initQuantitySelector() {
    const quantityInput = document.getElementById('quantity-input');
    if (!quantityInput) return;

    const minusBtn = document.getElementById('quantity-minus');
    const plusBtn = document.getElementById('quantity-plus');
    const stockWarning = document.getElementById('stock-warning');
    const hasVariants = document.querySelector('.add-to-cart-btn')?.dataset.hasVariants === 'true';

    const validateStock = () => {
        const currentValue = parseInt(quantityInput.value, 10);
        let maxStock;

        if (hasVariants) {
            const activeSize = document.querySelector('.size-option-btn.active');
            if (!activeSize) {
                if (plusBtn) plusBtn.disabled = true;
                if (minusBtn) minusBtn.disabled = true;
                return;
            }
            maxStock = parseInt(activeSize.dataset.stock, 10);
        } else {
            maxStock = parseInt(quantityInput.max, 10);
        }

        let warningMessage = '';
        if (currentValue >= maxStock) {
            warningMessage = `Stok maksimum tercapai (${maxStock}).`;
            if (plusBtn) plusBtn.disabled = true;
        } else {
            if (plusBtn) plusBtn.disabled = false;
        }

        if (minusBtn) minusBtn.disabled = currentValue <= 1;
        if (stockWarning) stockWarning.textContent = warningMessage;
    };


    const updateQuantity = (change) => {
        let currentValue = parseInt(quantityInput.value, 10) || 1;
        let newValue = currentValue + change;
        let maxStock;

        if (hasVariants) {
            const activeSize = document.querySelector('.size-option-btn.active');

            if (!activeSize) return;
            maxStock = parseInt(activeSize.dataset.stock, 10);
        } else {
            maxStock = parseInt(quantityInput.max, 10);
        }

        if (newValue < 1) newValue = 1;
        if (newValue > maxStock) newValue = maxStock;

        quantityInput.value = newValue;
        validateStock();
    };

    if (minusBtn) minusBtn.addEventListener('click', () => updateQuantity(-1));
    if (plusBtn) plusBtn.addEventListener('click', () => updateQuantity(1));

    quantityInput.addEventListener('input', () => {
        let value = parseInt(quantityInput.value, 10);
        let max;

        if (hasVariants) {
            const activeSize = document.querySelector('.size-option-btn.active');
            max = activeSize ? parseInt(activeSize.dataset.stock, 10) : 1;
        } else {
            max = parseInt(quantityInput.max, 10);
        }

        if (isNaN(value) || value < 1) {
            quantityInput.value = 1;
        } else if (value > max) {
            quantityInput.value = max;
        }
        validateStock();
    });

    validateStock();
}