export function initQuantitySelector() {
    const quantityInput = document.getElementById('quantity-input');
    if (!quantityInput) return;

    const minusBtn = document.getElementById('quantity-minus');
    const plusBtn = document.getElementById('quantity-plus');
    const stockWarning = document.getElementById('stock-warning');
    const hasVariants = (
        document.querySelector('.add-to-cart-btn')?.dataset.hasVariants === 'true'
    );

    const validateStock = () => {
        const currentValue = parseInt(quantityInput.value, 10) || 1;
        const maxStock = parseInt(quantityInput.max, 10);

        let warningMessage = '';
        let messageColor = 'var(--color-text-med)';

        if (isNaN(maxStock) || maxStock <= 0) {
            if (plusBtn) plusBtn.disabled = true;
            if (minusBtn) minusBtn.disabled = true;
            
            if (hasVariants) {
                warningMessage = (maxStock === 0) ? 'Stok untuk varian ini habis.' : '';
            } else {
                warningMessage = 'Stok produk ini habis.';
            }
            if (warningMessage) messageColor = 'var(--color-danger)';

        } else {

            if (minusBtn) minusBtn.disabled = (currentValue <= 1);
            if (currentValue >= maxStock) {
                if (plusBtn) plusBtn.disabled = true;
                warningMessage = `Stok maksimum tercapai (${maxStock}).`;
                messageColor = 'var(--color-warning)';
            } else {
                if (plusBtn) plusBtn.disabled = false;
                warningMessage = `Stok tersedia: ${maxStock}`;
            }
        }
        
        if (stockWarning) {
            stockWarning.textContent = warningMessage;
            stockWarning.style.color = messageColor;
        }
    };

    const updateQuantity = (change) => {
        let currentValue = parseInt(quantityInput.value, 10) || 1;
        let newValue = currentValue + change;
        const maxStock = parseInt(quantityInput.max, 10);

        if (hasVariants && isNaN(maxStock)) {
            if (maxStock === 1 && change > 0) return;
        }
        
        if (isNaN(maxStock) || maxStock <= 0) {
             if (change > 0) return;
        }

        if (newValue < 1) newValue = 1;
        if (newValue > maxStock && maxStock > 0) {
             newValue = maxStock;
        }
        quantityInput.value = newValue;
        validateStock();
    };

    if (minusBtn) minusBtn.addEventListener('click', () => updateQuantity(-1));
    if (plusBtn) plusBtn.addEventListener('click', () => updateQuantity(1));

    quantityInput.addEventListener('variantUpdated', () => {
        if (quantityInput.value !== "1") {
            quantityInput.value = 1;
        }
        validateStock();
    });

    validateStock();
}