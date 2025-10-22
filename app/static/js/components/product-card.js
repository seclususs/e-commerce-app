import { showNotification } from '../utils/ui.js';
import { cartStore } from '../state/cart-store.js';

async function handleAddToCart(btn) {
    if (!btn || btn.disabled || btn.classList.contains('is-added')) return;

    const id = parseInt(btn.dataset.id, 10);
    const name = btn.dataset.name;
    const hasVariants = btn.dataset.hasVariants === 'true';
    const quantityInput = document.getElementById('quantity-input');
    const quantityToAdd = quantityInput ? parseInt(quantityInput.value, 10) : 1;

    let variantId = null;
    let stock = parseInt(btn.dataset.stock, 10);

    const activeSizeBtn = document.querySelector('.size-option-btn.active');
    if (hasVariants && activeSizeBtn) {
        variantId = parseInt(activeSizeBtn.dataset.variantId, 10);
        stock = parseInt(activeSizeBtn.dataset.stock, 10);
    } else if (hasVariants && !activeSizeBtn && document.querySelector('.product-detail-section')) {
        showNotification('Silakan pilih ukuran terlebih dahulu.', true);
        return;
    }

    btn.disabled = true;
    const btnTextEl = btn.querySelector('span');
    const originalText = btnTextEl ? btnTextEl.textContent : '';
    if (btnTextEl) {
        btnTextEl.innerHTML = `<span class="spinner" style="display: inline-block; width: 1em; height: 1em; border-width: 2px;"></span>`;
    }

    const success = await cartStore.addItem(id, quantityToAdd, variantId, name, stock);

    if (success) {
        showNotification(`'${name}' x ${quantityToAdd} ditambahkan!`);

        const icon = document.querySelector('#bottomCartIconContainer .fa-shopping-cart');
        if (icon) {
            icon.classList.add('is-animating');
            setTimeout(() => icon.classList.remove('is-animating'), 600);
        }

        btn.classList.add('is-added');
        if (btnTextEl) btnTextEl.innerHTML = '<i class="fas fa-check checkmark-icon" style="display: inline-block;"></i> Ditambahkan!';

        setTimeout(() => {
            btn.classList.remove('is-added');
            if (btnTextEl) btnTextEl.innerHTML = originalText;
            btn.disabled = false;
        }, 2000);
    } else {
        btn.disabled = false;
        if (btnTextEl) btnTextEl.innerHTML = originalText;
    }
}

export function initGlobalAddToCart() {
    document.body.addEventListener('click', e => {
        const addToCartBtn = e.target.closest('.add-to-cart-btn');
        if (addToCartBtn) {
            e.preventDefault();
            handleAddToCart(addToCartBtn);
        }
    });
}