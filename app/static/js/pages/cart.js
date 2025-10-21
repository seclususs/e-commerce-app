import { showNotification } from '../utils/ui.js';
import { selectedVariantId } from './product-detail.js';
import { cartStore } from '../state/cart-store.js';

const formatRupiah = (num) => `Rp ${num.toLocaleString('id-ID')}`;

/**
 * Merender konten halaman keranjang berdasarkan state dari cartStore.
 * @param {object} state State keranjang saat ini dari cartStore.
 */
function renderCartPage(state) {
    const { items, subtotal } = state;
    const container = document.getElementById('cartPageItems');
    const listContainer = document.querySelector('.cart-items-list');
    const summary = document.querySelector('.cart-summary');
    const checkoutLink = document.getElementById('checkout-link');
    const checkoutLinkMobile = document.getElementById('checkout-link-mobile');
    
    if (!container || !listContainer || !summary) return;

    if (!items || items.length === 0) {
        listContainer.classList.add('is-empty');
        const productsUrl = document.querySelector('.cart-page-section')?.dataset.productsUrl || '/products';
        container.innerHTML = `<div class="cart-empty-container"><h2>Keranjang belanja Anda masih kosong</h2><p>Sepertinya Anda belum menambahkan produk apapun.</p><a href="${productsUrl}" class="cta-button">Lanjutkan Belanja</a></div>`;
        summary.style.display = 'none';
        if (checkoutLink) checkoutLink.classList.add('disabled-link');
        if (checkoutLinkMobile) checkoutLinkMobile.classList.add('disabled-link');
    } else {
        listContainer.classList.remove('is-empty');
        summary.style.display = 'block';
        if (checkoutLink) checkoutLink.classList.remove('disabled-link');
        if (checkoutLinkMobile) checkoutLinkMobile.classList.remove('disabled-link');
        
        container.innerHTML = items.map(p => {
            const effectivePrice = (p.discount_price && p.discount_price > 0) ? p.discount_price : p.price;
            const hasDiscount = (p.discount_price && p.discount_price > 0);
            const sizeInfo = p.size ? `<span>Ukuran: ${p.size}</span>` : '';
            const isOutOfStock = p.quantity > p.stock;
            return `
            <div class="cart-page-item ${isOutOfStock ? 'item-out-of-stock' : ''}">
                <div class="cart-page-item-img"><img src="${p.image_url ? `/static/uploads/${p.image_url}` : `https://placehold.co/80x80/0f172a/f1f5f9?text=${p.name}`}" alt="${p.name}"></div>
                <div class="cart-page-item-info">
                    <strong>${p.name}</strong>
                    ${sizeInfo}
                    <span>${hasDiscount ? `<del style="opacity: 0.7;">${formatRupiah(p.price)}</del> ${formatRupiah(effectivePrice)}` : formatRupiah(p.price)}</span>
                    ${isOutOfStock ? `<span class="stock-warning-message">Stok tidak cukup (tersisa ${p.stock})</span>` : ''}
                </div>
                <div class="cart-item-quantity">
                    <button class="quantity-btn" data-id="${p.id}" data-variant-id="${p.variant_id || ''}" data-change="-1" data-stock="${p.stock}">-</button>
                    <span>${p.quantity}</span>
                    <button class="quantity-btn" data-id="${p.id}" data-variant-id="${p.variant_id || ''}" data-change="1" data-stock="${p.stock}" ${p.quantity >= p.stock ? 'disabled' : ''}>+</button>
                </div>
                <div class="item-price">${formatRupiah(effectivePrice * p.quantity)}</div>
                <button class="remove-item-btn" data-id="${p.id}" data-variant-id="${p.variant_id || ''}">✕</button>
            </div>`;
        }).join('');
        document.getElementById('cartPageSubtotal').textContent = formatRupiah(subtotal);
        document.getElementById('cartPageTotal').textContent = formatRupiah(subtotal);
    }
}

/**
 * Menangani interaksi pengguna pada item di halaman keranjang (ubah kuantitas, hapus).
 * @param {Event} e Event klik.
 */
async function handleCartInteraction(e) {
    const target = e.target;
    if (!target.matches('.quantity-btn, .remove-item-btn')) return;

    const id = target.dataset.id;
    const variantId = target.dataset.variantId || null;
    if (!id) return;

    let newQuantity;
    if (target.matches('.quantity-btn')) {
        const currentItem = target.closest('.cart-item-quantity');
        const currentQty = parseInt(currentItem.querySelector('span').textContent, 10);
        const change = parseInt(target.dataset.change, 10);
        newQuantity = currentQty + change;
    } else { // remove button
        newQuantity = 0;
    }
    await cartStore.updateItem(parseInt(id, 10), newQuantity, variantId ? parseInt(variantId, 10) : null);
}

/**
 * Menangani klik pada tombol 'Tambah ke Keranjang'.
 * @param {HTMLButtonElement} btn Tombol yang diklik.
 */
async function handleAddToCart(btn) {
    if (!btn || btn.disabled || btn.classList.contains('is-added')) return;
    
    const id = parseInt(btn.dataset.id, 10);
    const name = btn.dataset.name;
    const hasVariants = btn.dataset.hasVariants === 'true';
    const quantityToAdd = parseInt(document.getElementById('quantity-input')?.value, 10) || 1;
    let variantId = selectedVariantId; // Diimpor dari product-detail.js

    if (hasVariants && !variantId) {
        showNotification('Silakan pilih ukuran terlebih dahulu.', true);
        return;
    }

    const activeSizeBtn = document.querySelector('.size-option-btn.active');
    const stock = activeSizeBtn ? parseInt(activeSizeBtn.dataset.stock) : parseInt(btn.dataset.stock);

    btn.disabled = true;
    const btnTextEl = btn.querySelector('span');
    const originalText = btnTextEl ? btnTextEl.textContent : '';
    if (btnTextEl) {
        btnTextEl.innerHTML = `<span class="spinner" style="display: inline-block; width: 1em; height: 1em; border-width: 2px;"></span>`;
    }

    const success = await cartStore.addItem(id, quantityToAdd, variantId ? parseInt(variantId, 10) : null, name, stock);

    if (success) {
        showNotification(`'${name}' x ${quantityToAdd} ditambahkan!`);
        const icon = document.querySelector('#bottomCartIconContainer .fa-shopping-cart');
        if (icon) {
            icon.classList.add('is-animating');
            setTimeout(() => icon.classList.remove('is-animating'), 600);
        }

        btn.classList.add('is-added');
        if(btnTextEl) btnTextEl.innerHTML = '<i class="fas fa-check checkmark-icon" style="display: inline-block;"></i> Ditambahkan!';
        setTimeout(() => {
            btn.classList.remove('is-added');
            if(btnTextEl) btnTextEl.innerHTML = originalText.includes('Tambah') ? `<i class="fas fa-shopping-cart"></i> ${originalText}` : originalText;
            btn.disabled = false;
        }, 2000);
    } else {
        btn.disabled = false;
        if(btnTextEl) btnTextEl.innerHTML = originalText;
    }
}

/**
 * Menginisialisasi fungsionalitas untuk halaman keranjang.
 */
export function initCartPage() {
    // Berlangganan ke perubahan state dari store
    const unsubscribe = cartStore.subscribe(renderCartPage);
    // Render awal saat halaman dimuat
    renderCartPage(cartStore.getState());
    // Tambahkan event listener untuk interaksi
    document.getElementById('cartPageItems')?.addEventListener('click', handleCartInteraction);

    // Mencegah klik pada link checkout jika keranjang kosong
    document.body.addEventListener('click', (e) => {
        if(e.target.closest('#checkout-link, #checkout-link-mobile')){
            if(cartStore.getState().items.length === 0){
                e.preventDefault();
                showNotification('Keranjang Anda kosong!', true);
            }
        }
    });
    
    // Cleanup on page unload (hypothetical)
    // window.addEventListener('beforeunload', unsubscribe);
}

// Inisialisasi global untuk tombol "Tambah ke Keranjang" di seluruh situs
document.body.addEventListener('click', e => {
    const addToCartBtn = e.target.closest('.add-to-cart-btn');
    if (addToCartBtn) {
        e.preventDefault();
        handleAddToCart(addToCartBtn);
    }
});