const cartModule = (() => {
    let cart = JSON.parse(localStorage.getItem('hackthreadCart')) || {};
    const cartCountEl = document.getElementById('cartCount');

    const save = () => localStorage.setItem('hackthreadCart', JSON.stringify(cart));
    const formatRupiah = (num) => `Rp ${num.toLocaleString('id-ID')}`;

    const updateCount = () => {
        if (!cartCountEl) return;
        const totalItems = Object.values(cart).reduce((sum, item) => sum + item.quantity, 0);
        cartCountEl.textContent = totalItems;
        cartCountEl.style.display = totalItems > 0 ? 'flex' : 'none';
    };
    
    const triggerCartAnimation = () => {
        const bottomCartIcon = document.querySelector('#bottomCartIconContainer .fa-shopping-cart');
        if (bottomCartIcon) {
            bottomCartIcon.classList.add('is-animating');
            setTimeout(() => {
                bottomCartIcon.classList.remove('is-animating');
            }, 600);
        }
    };

    const fetchProducts = async () => {
        const ids = Object.keys(cart);
        if (ids.length === 0) return { products: [], total: 0 };
        const response = await fetch('/api/cart', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ product_ids: ids })
        });
        const products = await response.json();
        const total = products.reduce((sum, p) => {
            const effectivePrice = (p.discount_price && p.discount_price > 0) ? p.discount_price : p.price;
            return sum + (effectivePrice * (cart[p.id]?.quantity || 0));
        }, 0);
        return { products, total };
    };

    const renderCartPage = async () => {
        const container = document.getElementById('cartPageItems');
        if (!container) return;
        const listContainer = document.querySelector('.cart-items-list');
        const summary = document.querySelector('.cart-summary');
        
        const { products, total } = await fetchProducts();
        const productsInCart = products.filter(p => (cart[p.id]?.quantity || 0) > 0);

        if (productsInCart.length === 0) {
            listContainer.classList.add('is-empty');
            container.innerHTML = '<div class="cart-empty">Keranjang belanja Anda masih kosong.</div>';
            if(summary) summary.style.display = 'none';
        } else {
            listContainer.classList.remove('is-empty');
            if(summary) summary.style.display = 'block';
            container.innerHTML = productsInCart.map(p => {
                const quantity = cart[p.id].quantity || 0;
                const imageUrl = (p.image_url && p.image_url !== 'placeholder.jpg')
                    ? `/static/uploads/${p.image_url}`
                    : `https://placehold.co/80x80/0f172a/f1f5f9?text=${p.name}`;
                const effectivePrice = (p.discount_price && p.discount_price > 0) ? p.discount_price : p.price;
                const hasDiscount = (p.discount_price && p.discount_price > 0);
                return `
                <div class="cart-page-item">
                    <div class="cart-page-item-img"><img src="${imageUrl}" alt="${p.name}"></div>
                    <div class="cart-page-item-info">
                        <strong>${p.name}</strong>
                        <span>
                           ${hasDiscount ? `<del style="opacity: 0.7;">${formatRupiah(p.price)}</del> ${formatRupiah(effectivePrice)}` : formatRupiah(p.price)}
                        </span>
                        <div class="stock-warning-message" data-id="${p.id}"></div>
                    </div>
                    <div class="cart-item-quantity">
                        <button class="quantity-btn" data-id="${p.id}" data-change="-1" data-stock="${p.stock}">-</button>
                        <span>${quantity}</span>
                        <button class="quantity-btn" data-id="${p.id}" data-change="1" data-stock="${p.stock}" ${quantity >= p.stock ? 'disabled' : ''}>+</button>
                    </div>
                    <div class="item-price">${formatRupiah(effectivePrice * quantity)}</div>
                    <button class="remove-item-btn" data-id="${p.id}">✕</button>
                </div>
            `}).join('');
            document.getElementById('cartPageSubtotal').textContent = formatRupiah(total);
            document.getElementById('cartPageTotal').textContent = formatRupiah(total);
        }
    };

    const renderCheckoutPage = async () => {
        const summaryContainer = document.getElementById('checkout-summary-items');
        if (!summaryContainer) return;

        const { products, total } = await fetchProducts();
        const productsInCart = products.filter(p => (cart[p.id]?.quantity || 0) > 0);
        const totalEl = document.getElementById('checkoutTotal');
        const placeOrderBtn = document.getElementById('placeOrderBtn');
        const cartDataInput = document.getElementById('cart_data_input');
        
        const cartForCheckout = {};
        Object.keys(cart).forEach(id => {
            cartForCheckout[id] = cart[id].quantity;
        });

        if (productsInCart.length === 0) {
            summaryContainer.innerHTML = '<p>Keranjang Anda kosong.</p>';
            if (placeOrderBtn) placeOrderBtn.disabled = true;
            return;
        }

        summaryContainer.innerHTML = productsInCart.map(p => {
            const effectivePrice = (p.discount_price && p.discount_price > 0) ? p.discount_price : p.price;
            return `
            <div class="summary-row">
                <span>${p.name} (x${cart[p.id].quantity})</span>
                <span>${formatRupiah(effectivePrice * cart[p.id].quantity)}</span>
            </div>
        `}).join('');
        
        totalEl.textContent = formatRupiah(total);
        cartDataInput.value = JSON.stringify(cartForCheckout);
        if (placeOrderBtn) placeOrderBtn.disabled = false;
    };

    const saveAndRender = () => {
        save();
        updateCount();
        if (document.getElementById('cartPageItems')) {
            renderCartPage();
        }
        if (document.getElementById('checkout-summary-items')) {
            renderCheckoutPage();
        }
    };

    const handleInteraction = (e) => {
        const target = e.target;
        const id = target.dataset.id;
        if (!id) return;

        if (target.matches('.quantity-btn')) {
            const change = parseInt(target.dataset.change);
            const maxStock = parseInt(target.dataset.stock);
            const currentQty = cart[id]?.quantity || 0;
            const newQty = currentQty + change;

            if (change > 0 && newQty > maxStock) {
                const warningEl = e.target.closest('.cart-page-item')?.querySelector('.stock-warning-message');
                if (warningEl) {
                    warningEl.textContent = `Maks. ${maxStock} unit.`;
                    setTimeout(() => { if(warningEl) warningEl.textContent = ''; }, 3000);
                } else {
                    showNotification(`Stok tidak mencukupi (tersisa ${maxStock} unit).`, true);
                }
                return;
            }
            if (newQty <= 0) delete cart[id];
            else cart[id].quantity = newQty;
            saveAndRender();
        }
        if (target.matches('.remove-item-btn')) {
            delete cart[id];
            saveAndRender();
        }
    };

    return {
        init: () => {
            updateCount();
            if (document.getElementById('cartPageItems')) {
                renderCartPage();
            }
            if (document.getElementById('checkout-summary-items')) {
                renderCheckoutPage();
            }

            document.body.addEventListener('click', (e) => {
                const btn = e.target.closest('.add-to-cart-btn');
                if (!btn || btn.disabled || btn.classList.contains('is-added')) return;
                
                e.preventDefault();
                const id = btn.dataset.id, name = btn.dataset.name, maxStock = parseInt(btn.dataset.stock);
                const quantityInput = document.getElementById('quantity-input');
                const quantityToAdd = quantityInput ? parseInt(quantityInput.value, 10) : 1;
                const currentInCart = cart[id]?.quantity || 0;

                if (currentInCart + quantityToAdd > maxStock) {
                    showNotification(`Stok tidak mencukupi. Anda sudah punya ${currentInCart} di keranjang.`, true);
                    return;
                }

                btn.disabled = true;
                const btnTextEl = btn.querySelector('span');
                const originalText = btnTextEl ? btnTextEl.textContent : '';

                if (!btn.querySelector('.checkmark-icon')) {
                    const checkmark = document.createElement('i');
                    checkmark.className = 'fas fa-check checkmark-icon';
                    btn.prepend(checkmark);
                }

                cart[id] = { quantity: currentInCart + quantityToAdd };
                save();
                updateCount();
                showNotification(`'${name}' x ${quantityToAdd} ditambahkan!`);
                triggerCartAnimation();

                btn.classList.add('is-added');
                if (btnTextEl) btnTextEl.textContent = 'Ditambahkan!';
                
                setTimeout(() => {
                    btn.classList.remove('is-added');
                    if (btnTextEl) btnTextEl.textContent = originalText;
                    btn.disabled = false;
                }, 2000);
            });
            
            const cartPageItemsEl = document.getElementById('cartPageItems');
            if (cartPageItemsEl) {
                cartPageItemsEl.addEventListener('click', handleInteraction);
            }
        },
        getCart: () => cart,
        clear: () => { cart = {}; saveAndRender(); },
    };
})();