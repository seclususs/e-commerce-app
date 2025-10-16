const cartModule = (() => {
    let cart = JSON.parse(localStorage.getItem('hackthreadCart')) || {};
    const cartModalEl = document.getElementById('cartModal');
    const cartCountEl = document.getElementById('cartCount');
    const cartItemsContainer = document.getElementById('cartItemsContainer');
    const cartTotalEl = document.getElementById('cartTotal');
    const cartFooter = document.getElementById('cartFooter');
    let isLoggedIn = false;

    const save = () => localStorage.setItem('hackthreadCart', JSON.stringify(cart));
    const formatRupiah = (num) => `Rp ${num.toLocaleString('id-ID')}`;

    const updateCount = () => {
        if (!cartCountEl) return;
        const totalItems = Object.values(cart).reduce((sum, qty) => sum + qty, 0);
        cartCountEl.textContent = totalItems;
        cartCountEl.style.display = totalItems > 0 ? 'flex' : 'none';
    };
    
    // Fungsi untuk memicu animasi ikon keranjang
    const triggerCartAnimation = () => {
        const bottomCartIcon = document.querySelector('#bottomCartIconContainer .fa-shopping-cart');
        if (bottomCartIcon) {
            bottomCartIcon.classList.add('is-animating');
            setTimeout(() => {
                bottomCartIcon.classList.remove('is-animating');
            }, 600); // Durasi harus cocok dengan CSS
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
        // Hitung total menggunakan harga diskon jika ada
        const total = products.reduce((sum, p) => {
            const effectivePrice = (p.discount_price && p.discount_price > 0) ? p.discount_price : p.price;
            return sum + (effectivePrice * (cart[p.id] || 0));
        }, 0);
        return { products, total };
    };

    const renderCartPage = async () => {
        const container = document.getElementById('cartPageItems');
        if (!container) return;
        const listContainer = document.querySelector('.cart-items-list');
        
        const { products, total } = await fetchProducts();
        const productsInCart = products.filter(p => (cart[p.id] || 0) > 0);

        if (productsInCart.length === 0) {
            listContainer.classList.add('is-empty');
            container.innerHTML = '<div class="cart-empty">Keranjang belanja Anda masih kosong.</div>';
            document.querySelector('.cart-summary').style.display = 'none';
        } else {
            listContainer.classList.remove('is-empty');
            document.querySelector('.cart-summary').style.display = 'block';
            container.innerHTML = productsInCart.map(p => {
                const quantity = cart[p.id] || 0;
                const imageUrl = (p.image_url && p.image_url !== 'placeholder.jpg')
                    ? `/static/uploads/${p.image_url}`
                    : `https://placehold.co/80x80/0f172a/f1f5f9?text=${p.name}`;
                // Tentukan harga efektif dan apakah ada diskon
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
                    </div>
                    <div class="cart-item-quantity">
                        <button class="quantity-btn" data-id="${p.id}" data-change="-1">-</button>
                        <span>${quantity}</span>
                        <button class="quantity-btn" data-id="${p.id}" data-change="1">+</button>
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
        const productsInCart = products.filter(p => (cart[p.id] || 0) > 0);
        const totalEl = document.getElementById('checkoutTotal');
        const placeOrderBtn = document.getElementById('placeOrderBtn');
        const cartDataInput = document.getElementById('cart_data_input');

        if (productsInCart.length === 0) {
            summaryContainer.innerHTML = '<p>Keranjang Anda kosong.</p>';
            placeOrderBtn.disabled = true;
            return;
        }

        summaryContainer.innerHTML = productsInCart.map(p => {
            const effectivePrice = (p.discount_price && p.discount_price > 0) ? p.discount_price : p.price;
            return `
            <div class="summary-row">
                <span>${p.name} (x${cart[p.id]})</span>
                <span>${formatRupiah(effectivePrice * cart[p.id])}</span>
            </div>
        `}).join('');
        
        totalEl.textContent = formatRupiah(total);
        cartDataInput.value = JSON.stringify(cart);
        placeOrderBtn.disabled = false;
    };

    const renderModal = async () => {
        if (!cartItemsContainer || !cartFooter) return;
        const { products, total } = await fetchProducts();
        const productsInCart = products.filter(p => (cart[p.id] || 0) > 0);

        if (productsInCart.length === 0) {
            cartItemsContainer.innerHTML = '<div class="cart-empty">Keranjang masih kosong</div>';
            cartFooter.classList.add('hidden');
        } else {
            cartItemsContainer.innerHTML = productsInCart.map(p => {
                const quantity = cart[p.id];
                // Tentukan harga efektif dan apakah ada diskon
                const effectivePrice = (p.discount_price && p.discount_price > 0) ? p.discount_price : p.price;
                const hasDiscount = (p.discount_price && p.discount_price > 0);
                return `
                <div class="cart-item">
                    <div class="cart-item-info">
                        <strong>${p.name}</strong>
                         <span>
                           ${hasDiscount ? `<del style="opacity: 0.7;">${formatRupiah(p.price)}</del> ${formatRupiah(effectivePrice)}` : formatRupiah(p.price)}
                        </span>
                    </div>
                    <div class="cart-item-quantity">
                        <button class="quantity-btn" data-id="${p.id}" data-change="-1">-</button>
                        <span>${quantity}</span>
                        <button class="quantity-btn" data-id="${p.id}" data-change="1">+</button>
                    </div>
                    <div class="item-price">${formatRupiah(effectivePrice * quantity)}</div>
                    <button class="remove-item-btn" data-id="${p.id}">✕</button>
                </div>`
            }).join('');
            cartTotalEl.textContent = formatRupiah(total);
            cartFooter.classList.remove('hidden');
        }
    };
    

    const saveAndRender = () => {
        save();
        updateCount();
        
        if (isLoggedIn && cartModalEl && cartModalEl.classList.contains('active')) {
            renderModal();
        }
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
            cart[id] = (cart[id] || 0) + change;
            if (cart[id] <= 0) delete cart[id];
            saveAndRender();
        }
        if (target.matches('.remove-item-btn')) {
            delete cart[id];
            saveAndRender();
        }
    };

    const toggleModal = () => {
        if (!isLoggedIn || !cartModalEl) return;
        const isActive = cartModalEl.classList.toggle('active');
        if (isActive) renderModal();
    };

    return {
        init: () => {
            isLoggedIn = !!document.getElementById('closeCartBtn');
            updateCount();

            if (document.getElementById('cartPageItems')) renderCartPage();
            if (document.getElementById('checkout-summary-items')) renderCheckoutPage();

            document.body.addEventListener('click', (e) => {
                const btn = e.target.closest('.add-to-cart-btn');
                if (!btn) return;
                
                e.preventDefault();
                const id = btn.dataset.id;
                const name = btn.dataset.name;
                cart[id] = (cart[id] || 0) + 1;
                save();
                updateCount();
                showNotification(`'${name}' ditambahkan ke keranjang!`);
                triggerCartAnimation(); // Panggil animasi
                if (isLoggedIn) toggleModal();
            });
            
            if (isLoggedIn && cartModalEl) {
                document.getElementById('closeCartBtn').addEventListener('click', toggleModal);
                cartModalEl.addEventListener('click', (e) => (e.target === cartModalEl) && toggleModal());
                if (cartItemsContainer) cartItemsContainer.addEventListener('click', handleInteraction);
            }

            const cartPageItemsEl = document.getElementById('cartPageItems');
            if (cartPageItemsEl) {
                cartPageItemsEl.addEventListener('click', handleInteraction);
            }
        },
        getCart: () => cart,
        clear: () => {
            cart = {};
            saveAndRender();
        },
    };
})();