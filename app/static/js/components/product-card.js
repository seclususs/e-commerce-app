import { showNotification } from './notification.js';
import { cartStore } from '../store/cart-store.js';
import { selectedVariantId } from '../pages/product-detail/variant-selector.js';

async function handleAddToCart(btn) {
    if (!btn || btn.disabled || btn.classList.contains('is-added')) return;

    const id = parseInt(btn.dataset.id, 10);
    const name = btn.dataset.name;
    const hasVariants = btn.dataset.hasVariants === 'true';
    const quantityInput = document.getElementById('quantity-input');
    const quantityToAdd = quantityInput ? parseInt(quantityInput.value, 10) : 1;
    const isDetailPage = document.querySelector('.product-detail-section');

    let variantId = null;
    let stock = parseInt(btn.dataset.stock, 10);

    if (hasVariants) {
        if (isDetailPage) {
            if (selectedVariantId) {
                variantId = parseInt(selectedVariantId, 10);
                const variantDataEl = document.getElementById('variant-data');
                const allVariants = JSON.parse(variantDataEl.textContent);
                const variant = allVariants.find(v => v.id === variantId);
                stock = variant ? variant.stock : 0;
            } else {
                showNotification(
                    'Silakan pilih warna dan ukuran terlebih dahulu.', true
                );
                return;
            }
        } else {
            showNotification('Silakan pilih varian di halaman detail produk.', true);
            return;
        }
    }

    btn.disabled = true;
    const btnTextEl = btn.querySelector('span');
    const originalText = btnTextEl ? btnTextEl.textContent : '';
    if (btnTextEl) {
        btnTextEl.innerHTML = (
            '<span class="spinner" style="display: inline-block; ' +
            'width: 1em; height: 1em; border-width: 2px;"></span>'
        );
    }

    const success = await cartStore.addItem(
        id, quantityToAdd, variantId, name, stock
    );

    if (success) {
        showNotification(`'${name}' x ${quantityToAdd} ditambahkan!`);

        const icon = document.querySelector(
            '#bottomCartIconContainer .fa-shopping-cart'
        );
        if (icon) {
            icon.classList.add('is-animating');
            setTimeout(() => icon.classList.remove('is-animating'), 600);
        }

        btn.classList.add('is-added');
        if (btnTextEl) {
            btnTextEl.innerHTML = (
                '<i class="fas fa-check checkmark-icon" ' +
                'style="display: inline-block;"></i> Berhasil Ditambahkan!'
            );
        }

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