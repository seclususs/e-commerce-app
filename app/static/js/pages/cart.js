import { showNotification } from '../utils/ui.js';
import { selectedVariantId } from './product-detail.js';

const cartModule = (() => {
    let cart = {}; 
    const GUEST_CART_KEY = 'hackthreadVariantCart';
    const cartCountEl = document.getElementById('cartCount');
    const formatRupiah = (num) => `Rp ${num.toLocaleString('id-ID')}`;

    const saveGuestCart = () => localStorage.setItem(GUEST_CART_KEY, JSON.stringify(cart));
    const loadGuestCart = () => JSON.parse(localStorage.getItem(GUEST_CART_KEY)) || {};

    const api = {
        get: () => fetch('/api/user-cart').then(res => res.json()),
        add: (productId, quantity, variantId) => fetch('/api/user-cart', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ product_id: productId, quantity, variant_id: variantId })
        }).then(res => res.json()),
        update: (productId, quantity, variantId) => fetch(`/api/user-cart/${productId}/${variantId || 'null'}`, {
            method: 'PUT', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ quantity })
        }).then(res => res.json()),
        merge: (localCart) => fetch('/api/user-cart/merge', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ local_cart: localCart })
        }).then(res => res.json())
    };

    const updateCount = (items) => {
        if (!cartCountEl) return;
        const totalItems = items.reduce((sum, item) => sum + item.quantity, 0);
        cartCountEl.textContent = totalItems;
        cartCountEl.style.display = totalItems > 0 ? 'flex' : 'none';
    };
    
    const triggerCartAnimation = () => {
        const icon = document.querySelector('#bottomCartIconContainer .fa-shopping-cart');
        if (icon) {
            icon.classList.add('is-animating');
            setTimeout(() => icon.classList.remove('is-animating'), 600);
        }
    };

    const render = (items, total) => {
        if (document.getElementById('cartPageItems')) renderCartPage(items, total);
        if (document.getElementById('checkout-summary-items')) renderCheckoutPage(items, total);
    };
    
    const renderCartPage = (items, subtotal) => {
        const container = document.getElementById('cartPageItems');
        const listContainer = document.querySelector('.cart-items-list');
        const summary = document.querySelector('.cart-summary');
        
        if (!items || items.length === 0) {
            listContainer.classList.add('is-empty');
            const productsUrl = document.querySelector('.cart-page-section')?.dataset.productsUrl || '/products';
            container.innerHTML = `<div class="cart-empty-container"><h2>Keranjang belanja Anda masih kosong</h2><p>Sepertinya Anda belum menambahkan produk apapun.</p><a href="${productsUrl}" class="cta-button">Lanjutkan Belanja</a></div>`;
            if (summary) summary.style.display = 'none';
        } else {
            listContainer.classList.remove('is-empty');
            if (summary) summary.style.display = 'block';
            container.innerHTML = items.map(p => {
                const effectivePrice = (p.discount_price && p.discount_price > 0) ? p.discount_price : p.price;
                const hasDiscount = (p.discount_price && p.discount_price > 0);
                const sizeInfo = p.size ? `<span>Ukuran: ${p.size}</span>` : '';
                return `
                <div class="cart-page-item">
                    <div class="cart-page-item-img"><img src="${p.image_url ? `/static/uploads/${p.image_url}` : `https://placehold.co/80x80/0f172a/f1f5f9?text=${p.name}`}" alt="${p.name}"></div>
                    <div class="cart-page-item-info">
                        <strong>${p.name}</strong>
                        ${sizeInfo}
                        <span>${hasDiscount ? `<del style="opacity: 0.7;">${formatRupiah(p.price)}</del> ${formatRupiah(effectivePrice)}` : formatRupiah(p.price)}</span>
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
    };

    const renderCheckoutPage = (items, total) => {
        const summaryContainer = document.getElementById('checkout-summary-items');
        if (!summaryContainer) return;
        const subtotalEl = document.getElementById('checkoutSubtotal');
        const totalEl = document.getElementById('checkoutTotal');
        const placeOrderBtn = document.getElementById('placeOrderBtn');
        const cartDataInput = document.getElementById('cart_data_input');
        
        if (items.length === 0) {
            summaryContainer.innerHTML = '<p>Keranjang Anda kosong.</p>';
            if (placeOrderBtn) placeOrderBtn.disabled = true;
            return;
        }
        summaryContainer.innerHTML = items.map(p => {
            const effectivePrice = (p.discount_price && p.discount_price > 0) ? p.discount_price : p.price;
            const sizeInfo = p.size ? ` (Ukuran: ${p.size})` : '';
            return `<div class="summary-row"><span>${p.name}${sizeInfo} (x${p.quantity})</span><span>${formatRupiah(effectivePrice * p.quantity)}</span></div>`;
        }).join('');
        
        if(subtotalEl) subtotalEl.textContent = formatRupiah(total);
        if(totalEl) totalEl.textContent = formatRupiah(total);
        if(cartDataInput) cartDataInput.value = JSON.stringify(cart);
        if (placeOrderBtn) placeOrderBtn.disabled = false;
    };

    const refreshViews = async () => {
        if (window.IS_USER_LOGGED_IN) {
            const { items, subtotal } = await api.get();
            updateCount(items || []);
            render(items || [], subtotal || 0);
        } else {
            const cartKeys = Object.keys(cart);
            if (cartKeys.length === 0) {
                updateCount([]);
                render([], 0);
                return;
            }
            const res = await fetch('/api/cart', {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ cart_items: cart })
            });
            const detailedItems = await res.json();
            const subtotal = detailedItems.reduce((sum, p) => {
                const effectivePrice = (p.discount_price && p.discount_price > 0) ? p.discount_price : p.price;
                return sum + (effectivePrice * p.quantity);
            }, 0);
            updateCount(detailedItems);
            render(detailedItems, subtotal);
        }
    };

    const handleInteraction = async (e) => {
        const target = e.target;
        if (!target.matches('.quantity-btn, .remove-item-btn')) return;

        const id = target.dataset.id;
        const variantId = target.dataset.variantId || null;
        if (!id) return;

        let newQuantity;
        if (target.matches('.quantity-btn')) {
            const currentItem = target.parentElement;
            const currentQty = parseInt(currentItem.querySelector('span').textContent, 10);
            const change = parseInt(target.dataset.change, 10);
            newQuantity = currentQty + change;
        } else { // remove button
            newQuantity = 0;
        }

        if (window.IS_USER_LOGGED_IN) {
            const res = await api.update(id, newQuantity, variantId);
            if (!res.success && res.message) showNotification(res.message, true);
        } else {
            const cartKey = variantId ? `${id}-${variantId}` : `${id}-null`;
            if (newQuantity <= 0) {
                delete cart[cartKey];
            } else {
                cart[cartKey] = { quantity: newQuantity };
            }
            saveGuestCart();
        }
        refreshViews();
    };

    const handleAddToCart = async (btn) => {
        if (!btn || btn.disabled || btn.classList.contains('is-added')) return;
        
        const id = btn.dataset.id;
        const name = btn.dataset.name;
        const hasVariants = btn.dataset.hasVariants === 'true';
        const quantityToAdd = parseInt(document.getElementById('quantity-input')?.value, 10) || 1;
        
        if (hasVariants && !selectedVariantId) {
            showNotification('Silakan pilih ukuran terlebih dahulu.', true);
            return;
        }

        btn.disabled = true;
        const btnTextEl = btn.querySelector('span');
        const originalText = btnTextEl ? btnTextEl.textContent : '';

        if (window.IS_USER_LOGGED_IN) {
            const res = await api.add(id, quantityToAdd, selectedVariantId);
            if (!res.success) {
                showNotification(res.message, true);
                btn.disabled = false; return;
            }
        } else {
            const cartKey = selectedVariantId ? `${id}-${selectedVariantId}` : `${id}-null`;
            const currentInCart = cart[cartKey]?.quantity || 0;
            const activeSizeBtn = document.querySelector('.size-option-btn.active');
            const maxStock = activeSizeBtn ? parseInt(activeSizeBtn.dataset.stock) : parseInt(btn.dataset.stock);

            if (currentInCart + quantityToAdd > maxStock) {
                showNotification(`Stok tidak mencukupi. Anda sudah punya ${currentInCart} di keranjang.`, true);
                btn.disabled = false; return;
            }
            cart[cartKey] = { quantity: currentInCart + quantityToAdd };
            saveGuestCart();
        }

        showNotification(`'${name}' x ${quantityToAdd} ditambahkan!`);
        triggerCartAnimation();
        refreshViews();

        btn.classList.add('is-added');
        if(btnTextEl) btnTextEl.textContent = 'Ditambahkan!';
        setTimeout(() => {
            btn.classList.remove('is-added');
            if(btnTextEl) btnTextEl.textContent = originalText;
            btn.disabled = false;
        }, 2000);
    };

    return {
        init: () => {
            if (window.IS_USER_LOGGED_IN) {
                refreshViews();
            } else {
                cart = loadGuestCart();
                refreshViews();
            }
            
            if (document.querySelector('.order-success-page')) {
                localStorage.removeItem(GUEST_CART_KEY);
            }

            document.body.addEventListener('click', e => {
                const addToCartBtn = e.target.closest('.add-to-cart-btn');
                if (addToCartBtn) {
                    e.preventDefault();
                    handleAddToCart(addToCartBtn);
                }
            });
            document.getElementById('cartPageItems')?.addEventListener('click', handleInteraction);
        },
        syncOnLogin: async () => {
            const localCart = loadGuestCart();
            if (Object.keys(localCart).length > 0) {
                await api.merge(localCart);
                localStorage.removeItem(GUEST_CART_KEY);
            }
            window.IS_USER_LOGGED_IN = true;
            refreshViews();
        }
    };
})();
export { cartModule };