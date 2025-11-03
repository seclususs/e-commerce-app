export let selectedVariantId = null;

export function initVariantSelector() {
    const dataEl = document.getElementById('variant-data');
    if (!dataEl) {
        selectedVariantId = null;
        return;
    }

    const allVariants = JSON.parse(dataEl.textContent);
    const colorSelector = document.getElementById('color-selector');
    const sizeSelector = document.getElementById('size-selector');
    const warningEl = document.getElementById('variant-warning');
    const addToCartBtn = document.querySelector('.add-to-cart-btn');
    const quantityInput = document.getElementById('quantity-input');
    const stockDisplay = document.getElementById('stock-display');
    const originalStockText = stockDisplay ? stockDisplay.innerHTML : '';

    let selectedColor = null;
    let selectedSize = null;
    let selectedVariant = null;

    const resetSelections = () => {
        selectedColor = null;
        selectedSize = null;
        selectedVariant = null;
        selectedVariantId = null;

        document.querySelectorAll('.color-option-btn, .size-option-btn').forEach(
            btn => {
                btn.classList.remove('active');
                btn.classList.remove('out-of-stock');
            }
        );
        document.querySelectorAll('.size-option-btn').forEach(
            btn => btn.disabled = true
        );
        document.querySelectorAll('.color-option-btn').forEach(
            btn => btn.disabled = false
        );

        if (warningEl) {
            warningEl.textContent = 'Silakan pilih warna terlebih dahulu.';
        }
        if (addToCartBtn) {
            addToCartBtn.disabled = true;
        }
        if (quantityInput) {
            quantityInput.value = 1;
            quantityInput.max = 1;
        }
        if (stockDisplay) {
            stockDisplay.innerHTML = originalStockText;
        }
        
        quantityInput?.dispatchEvent(new CustomEvent('variantUpdated'));
    };

    const updateUIForSelectedVariant = () => {
        if (selectedVariant) {
            selectedVariantId = selectedVariant.id;
            if (warningEl) warningEl.textContent = '';
            
            const stock = selectedVariant.stock || 0;
            
            if (addToCartBtn) {
                addToCartBtn.disabled = (stock <= 0);
            }
            if (quantityInput) {
                quantityInput.max = stock;
                if (parseInt(quantityInput.value) > stock) {
                    quantityInput.value = stock;
                }
                if (stock === 0) {
                    quantityInput.value = 1;
                }
            }
            if (stockDisplay) {
                if (stock > 0) {
                    stockDisplay.innerHTML =
                        `<span style="color: #f59e0b;">Stok ${selectedVariant.color} / ${selectedVariant.size}: ${stock}</span>`;
                } else {
                     stockDisplay.innerHTML =
                        `<span style="color: var(--color-danger);">Stok ${selectedVariant.color} / ${selectedVariant.size}: HABIS</span>`;
                }
            }
        } else {
            selectedVariantId = null; // Update state
            if (addToCartBtn) addToCartBtn.disabled = true;
            if (quantityInput) {
                quantityInput.value = 1;
                quantityInput.max = 1;
            }

            if (stockDisplay) {
                if (!selectedColor && !selectedSize) {
                    stockDisplay.innerHTML = originalStockText;
                } else if (selectedColor && selectedSize) {
                    stockDisplay.innerHTML =
                        '<span style="color: var(--color-danger);">Kombinasi tidak tersedia</span>';
                } else {
                    stockDisplay.innerHTML =
                        '<span style="color: #f59e0b;">Pilih Opsi Lengkap</span>';
                }
            }
            
            if (!selectedColor) {
                if (warningEl) {
                    warningEl.textContent = 'Silakan pilih warna.';
                }
            } else if (!selectedSize) {
                if (warningEl) {
                    warningEl.textContent = 'Silakan pilih ukuran.';
                }
            }
        }
        quantityInput?.dispatchEvent(new CustomEvent('variantUpdated'));
    };

    const updateAvailableSizes = () => {
        const availableSizes = new Map();
        allVariants.forEach(v => {
            if (v.color === selectedColor) {
                availableSizes.set(v.size, (v.stock || 0));
            }
        });

        document.querySelectorAll('.size-option-btn').forEach(btn => {
            const size = btn.dataset.value;
            const stock = availableSizes.get(size);

            if (stock !== undefined) {
                btn.disabled = false;
                btn.classList.toggle('out-of-stock', stock <= 0);
            } else {
                btn.disabled = true;
                btn.classList.remove('active');
                btn.classList.remove('out-of-stock');
            }
        });
    };

    const updateAvailableColors = () => {
        const availableColors = new Map();
        allVariants.forEach(v => {
            if (v.size === selectedSize) {
                availableColors.set(v.color, (v.stock || 0));
            }
        });

        document.querySelectorAll('.color-option-btn').forEach(btn => {
            const color = btn.dataset.value;
            const stock = availableColors.get(color);
            if (stock !== undefined) {
                btn.disabled = false;
                 btn.classList.toggle('out-of-stock', stock <= 0);
            } else {
                btn.disabled = true;
                btn.classList.remove('active');
                btn.classList.remove('out-of-stock');
            }
        });
    };

    const findSelectedVariant = () => {
        if (!selectedColor || !selectedSize) {
            selectedVariant = null;
            return;
        }
        selectedVariant = allVariants.find(
            v => v.color === selectedColor && v.size === selectedSize
        ) || null;
    };

    colorSelector.addEventListener('click', (e) => {
        const target = e.target.closest('.color-option-btn');
        if (!target || target.disabled) return;

        const color = target.dataset.value;
        if (selectedColor === color) {
            selectedColor = null;
            resetSelections();
        } else {
            selectedColor = color;
            document.querySelectorAll('.color-option-btn').forEach(
                btn => btn.classList.remove('active')
            );
            target.classList.add('active');
            
            updateAvailableSizes();
            
            if (
                selectedSize &&
                !document.querySelector(
                    `.size-option-btn[data-value="${selectedSize}"]:not(:disabled)`
                )
            ) {
                selectedSize = null;
                document.querySelectorAll('.size-option-btn').forEach(
                    btn => btn.classList.remove('active')
                );
            }
        }
        findSelectedVariant();
        updateUIForSelectedVariant();
    });

    sizeSelector.addEventListener('click', (e) => {
        const target = e.target.closest('.size-option-btn');
        if (!target || target.disabled) return;

        const size = target.dataset.value;
        if (selectedSize === size) {
            selectedSize = null;
            target.classList.remove('active');
            updateAvailableColors();
        } else {
            selectedSize = size;
            document.querySelectorAll('.size-option-btn').forEach(
                btn => btn.classList.remove('active')
            );
            target.classList.add('active');
            
            updateAvailableColors();
            
            if (
                selectedColor &&
                !document.querySelector(
                    `.color-option-btn[data-value="${selectedColor}"]:not(:disabled)`
                )
            ) {
                selectedColor = null;
                document.querySelectorAll('.color-option-btn').forEach(
                    btn => btn.classList.remove('active')
                );
            }
        }
        findSelectedVariant();
        updateUIForSelectedVariant();
    });

    resetSelections();
}