import { cartStore } from '../store/cart-store.js';
import { showNotification } from '../components/notification.js';

const formatRupiah = (num) => `Rp ${Number(num).toLocaleString('id-ID', { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`;

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
            const priceNum = Number(p.price) || 0;
            const discountPriceNum = Number(p.discount_price) || 0;
            const effectivePrice = (discountPriceNum && discountPriceNum > 0) ? discountPriceNum : priceNum;
            const hasDiscount = (discountPriceNum && discountPriceNum > 0);
            const sizeInfo = p.size ? `<span>Ukuran: ${p.size}</span>` : '';
            const isOutOfStock = p.quantity > p.stock;
            const imageUrl = p.image_url ? `/images/${p.image_url}` : `https://placehold.co/80x80/0f172a/f1f5f9?text=${encodeURIComponent(p.name)}`;
            return `
            <div class="cart-page-item ${isOutOfStock ? 'item-out-of-stock' : ''}">
                <div class="cart-page-item-img"><img src="${imageUrl}" alt="${p.name}"></div>
                <div class="cart-page-item-info">
                    <strong>${p.name}</strong>
                    ${sizeInfo}
                    <span>${hasDiscount ? `<del style="opacity: 0.7;">${formatRupiah(priceNum)}</del> ${formatRupiah(effectivePrice)}` : formatRupiah(priceNum)}</span>
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
        const subtotalNum = Number(subtotal) || 0;
        document.getElementById('cartPageSubtotal').textContent = formatRupiah(subtotalNum);
        document.getElementById('cartPageTotal').textContent = formatRupiah(subtotalNum);
    }
}

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
    } else {
        newQuantity = 0;
    }
    await cartStore.updateItem(parseInt(id, 10), newQuantity, variantId ? parseInt(variantId, 10) : null);
}

export function initCartPage() {
    cartStore.subscribe(renderCartPage);
    renderCartPage(cartStore.getState());
    document.getElementById('cartPageItems')?.addEventListener('click', handleCartInteraction);

    document.body.addEventListener('click', (e) => {
        if (e.target.closest('#checkout-link, #checkout-link-mobile')) {
            if (cartStore.getState().items.length === 0) {
                e.preventDefault();
                showNotification('Keranjang Anda kosong!', true);
            }
        }
    });
}