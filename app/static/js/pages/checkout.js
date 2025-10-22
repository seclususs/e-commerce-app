import { cartStore } from '../state/cart-store.js';

const formatRupiah = (num) => `Rp ${num.toLocaleString('id-ID', { minimumFractionDigits: 0 })}`;

function renderCheckoutSummary(state) {
    const { items, subtotal } = state;
    const summaryContainer = document.getElementById('checkout-summary-items');
    if (!summaryContainer) return;

    const subtotalEl = document.getElementById('checkoutSubtotal');
    const totalEl = document.getElementById('checkoutTotal');
    const placeOrderBtn = document.getElementById('placeOrderBtn');
    const cartDataInput = document.getElementById('cart_data_input');

    if (items.length === 0) {
        summaryContainer.innerHTML = '<p>Keranjang Anda kosong.</p>';
        if (placeOrderBtn) placeOrderBtn.disabled = true;
        if (window.location.pathname.includes('/checkout')) {
            window.location.href = '/cart';
        }
        return;
    }

    summaryContainer.innerHTML = items.map(p => {
        const effectivePrice = (p.discount_price && p.discount_price > 0) ? p.discount_price : p.price;
        const sizeInfo = p.size ? ` (Ukuran: ${p.size})` : '';
        return `<div class="summary-row"><span>${p.name}${sizeInfo} (x${p.quantity})</span><span>${formatRupiah(effectivePrice * p.quantity)}</span></div>`;
    }).join('');

    if (subtotalEl) subtotalEl.textContent = formatRupiah(subtotal);
    if (totalEl) totalEl.textContent = formatRupiah(subtotal);

    if (!window.IS_USER_LOGGED_IN && cartDataInput) {
        const guestCart = items.reduce((acc, item) => {
            const key = item.variant_id ? `${item.id}-${item.variant_id}` : `${item.id}-null`;
            acc[key] = { quantity: item.quantity };
            return acc;
        }, {});
        cartDataInput.value = JSON.stringify(guestCart);
    }

    const cityElement = document.getElementById('city') || document.querySelector('.address-display-box');
    cityElement?.dispatchEvent(new Event('recalc'));
}

function initCheckoutForm() {
    const form = document.getElementById('checkout-form');
    if (!form) return;

    const placeOrderBtn = document.getElementById('placeOrderBtn');
    const placeOrderBtnMobile = document.getElementById('placeOrderBtnMobile');
    const buttons = [placeOrderBtn, placeOrderBtnMobile].filter(Boolean);

    form.addEventListener('submit', (e) => {
        if (!form.checkValidity()) {
            const firstInvalidField = form.querySelector(':invalid');
            if (firstInvalidField) {
                firstInvalidField.focus();
                showNotification('Harap lengkapi semua field yang wajib diisi.', true);
            }
            e.preventDefault();
            return;
        }

        const applyBtn = document.getElementById('applyVoucherBtn');
        if (applyBtn) applyBtn.disabled = true;

        buttons.forEach(btn => {
            btn.disabled = true;
            btn.classList.add('is-loading');
            btn.innerHTML = `<span class="spinner"></span><span>Memproses...</span>`;
        });
    });
}

function initMobileCtaHandlers() {
    const mobileCheckoutBtn = document.getElementById('placeOrderBtnMobile');
    const mainCheckoutBtn = document.getElementById('placeOrderBtn');
    const checkoutForm = document.getElementById('checkout-form');

    if (mobileCheckoutBtn && mainCheckoutBtn && checkoutForm) {
        const observer = new MutationObserver(mutations => {
            mutations.forEach(mutation => {
                if (mutation.attributeName === 'disabled') {
                    mobileCheckoutBtn.disabled = mainCheckoutBtn.disabled;
                }
            });
        });
        observer.observe(mainCheckoutBtn, { attributes: true });
        mobileCheckoutBtn.disabled = mainCheckoutBtn.disabled;

        mobileCheckoutBtn.addEventListener('click', () => {
            if (!mobileCheckoutBtn.disabled) {
                checkoutForm.requestSubmit();
            }
        });
    }
}

function initVoucherHandler() {
    const applyBtn = document.getElementById('applyVoucherBtn');
    const voucherInput = document.getElementById('voucher_code');
    const messageEl = document.getElementById('voucher-message');
    if (!applyBtn || !voucherInput || !messageEl) return;

    const applyVoucher = async () => {
        const code = voucherInput.value.trim();
        if (!code) return;

        applyBtn.disabled = true;
        messageEl.textContent = 'Memvalidasi...';
        messageEl.className = 'voucher-feedback';

        const subtotal = cartStore.getState().subtotal;
        if (isNaN(subtotal)) {
            applyBtn.disabled = false;
            return;
        };

        try {
            const response = await fetch('/api/apply-voucher', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ voucher_code: code, subtotal: subtotal })
            });
            const result = await response.json();

            if (result.success) {
                messageEl.textContent = result.message;
                messageEl.classList.add('success');

                document.getElementById('checkoutDiscount').textContent = `- ${formatRupiah(result.discount_amount)}`;
                document.querySelector('.discount-row').style.display = 'flex';
                const cityElement = document.getElementById('city') || document.querySelector('.address-display-box');
                cityElement?.dispatchEvent(new Event('recalc'));
            } else {
                messageEl.textContent = result.message;
                messageEl.classList.add('error');
                resetDiscount();
            }
        } catch (error) {
            messageEl.textContent = 'Gagal terhubung ke server.';
            messageEl.classList.add('error');
        } finally {
            applyBtn.disabled = false;
        }
    };

    const resetDiscount = () => {
        messageEl.textContent = '';
        messageEl.className = 'voucher-feedback';
        document.querySelector('.discount-row').style.display = 'none';
        document.getElementById('checkoutDiscount').textContent = '- Rp 0';
        voucherInput.value = '';
        document.getElementById('voucher_code').name = 'voucher_code';
        const cityElement = document.getElementById('city') || document.querySelector('.address-display-box');
        cityElement?.dispatchEvent(new Event('recalc'));
    };

    applyBtn.addEventListener('click', applyVoucher);
    voucherInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            applyVoucher();
        }
    });
    voucherInput.addEventListener('input', () => {
        if (messageEl.textContent !== '') {
            resetDiscount();
        }
    });
}

function initStockHoldTimer(expiresAtIsoString) {
    const expiresAtInput = document.getElementById('stock_hold_expires_at');
    const timerEl = document.getElementById('timer');
    const container = document.getElementById('stock-hold-timer-container');
    const expiryTime = expiresAtIsoString || (expiresAtInput ? expiresAtInput.value : null);

    if (!expiryTime || !timerEl || !container) return;

    const expiresAt = new Date(expiryTime).getTime();

    if (expiresAt > new Date().getTime()) {
        const placeOrderBtn = document.getElementById('placeOrderBtn');
        const placeOrderBtnMobile = document.getElementById('placeOrderBtnMobile');
        if (placeOrderBtn) placeOrderBtn.disabled = false;
        if (placeOrderBtnMobile) placeOrderBtnMobile.disabled = false;
    } else {
        container.innerHTML = 'Waktu penahanan stok habis! <a href="/cart" style="color: white; text-decoration: underline;">Kembali ke keranjang</a> untuk validasi ulang.';
        container.classList.add('expired');
        const placeOrderBtn = document.getElementById('placeOrderBtn');
        const placeOrderBtnMobile = document.getElementById('placeOrderBtnMobile');
        if (placeOrderBtn) placeOrderBtn.disabled = true;
        if (placeOrderBtnMobile) placeOrderBtnMobile.disabled = true;
        return;
    }

    const interval = setInterval(() => {
        const now = new Date().getTime();
        const distance = expiresAt - now;

        if (distance < 0) {
            clearInterval(interval);
            container.innerHTML = 'Waktu penahanan stok habis! <a href="/cart" style="color: white; text-decoration: underline;">Kembali ke keranjang</a> untuk validasi ulang.';
            container.classList.add('expired');
            const placeOrderBtn = document.getElementById('placeOrderBtn');
            const placeOrderBtnMobile = document.getElementById('placeOrderBtnMobile');
            if (placeOrderBtn) placeOrderBtn.disabled = true;
            if (placeOrderBtnMobile) placeOrderBtnMobile.disabled = true;
            return;
        }

        const minutes = Math.floor((distance % (1000 * 60 * 60)) / (1000 * 60));
        const seconds = Math.floor((distance % (1000 * 60)) / 1000);
        timerEl.textContent = `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
    }, 1000);
}

function initShippingCalculation() {
    const citySelect = document.getElementById('city');
    const cityDisplay = document.querySelector('.address-display-box');
    const shippingRow = document.querySelector('.shipping-row');
    const shippingCostEl = document.getElementById('checkoutShipping');
    const totalEl = document.getElementById('checkoutTotal');
    const discountEl = document.getElementById('checkoutDiscount');
    const shippingCostInput = document.getElementById('shipping_cost_input');

    if (!totalEl || !shippingRow || !shippingCostEl || !shippingCostInput) return;

    const calculateAndUpdate = () => {
        let city = '';
        if (citySelect) {
            city = citySelect.value;
        } else if (cityDisplay) {
            const addressParagraphs = cityDisplay.querySelectorAll('p');
            let fullAddress = '';
            addressParagraphs.forEach(p => {
                if (p.textContent.includes(',')) {
                    fullAddress += p.textContent + ' ';
                }
            });
            fullAddress = fullAddress.trim();

            if (fullAddress) {
                const parts = fullAddress.split(',');
                if (parts.length >= 2) {
                    city = parts[parts.length - 2].trim().split(' ').slice(-1)[0];
                } else if (parts.length === 1 && !fullAddress.includes('(')) {
                    city = parts[0].trim();
                }
            }
        }

        let shippingCost = 0;
        const jabodetabek = ['jakarta', 'bogor', 'depok', 'tangerang', 'bekasi'];

        if (city && jabodetabek.includes(city.toLowerCase())) {
            shippingCost = 10000;
        } else if (city && city !== "") {
            shippingCost = 20000;
        }

        if (shippingCost > 0) {
            shippingRow.style.display = 'flex';
            shippingCostEl.textContent = formatRupiah(shippingCost);
        } else {
            shippingRow.style.display = 'none';
            shippingCostEl.textContent = formatRupiah(0);
        }

        const subtotal = cartStore.getState().subtotal || 0;
        const discountText = discountEl.textContent || '0';
        const discount = parseFloat(discountText.replace(/[^\d.-]/g, '')) || 0;

        const finalTotal = subtotal + discount + shippingCost;
        totalEl.textContent = formatRupiah(finalTotal);
        shippingCostInput.value = shippingCost;
    };

    if (citySelect) {
        citySelect.addEventListener('change', calculateAndUpdate);
        if (citySelect.value) setTimeout(calculateAndUpdate, 150);
    }
    const triggerElement = citySelect || cityDisplay || document.body;
    triggerElement.addEventListener('recalc', calculateAndUpdate);

    setTimeout(calculateAndUpdate, 150);
}

async function prepareCheckout() {
    const timerContainer = document.getElementById('stock-hold-timer-container');
    const form = document.getElementById('checkout-form');
    let itemsToHold = cartStore.getState().items;

    if (!itemsToHold || itemsToHold.length === 0) {
        window.location.href = '/cart';
        return;
    }

    const placeOrderBtn = document.getElementById('placeOrderBtn');
    const placeOrderBtnMobile = document.getElementById('placeOrderBtnMobile');
    if (placeOrderBtn) placeOrderBtn.disabled = true;
    if (placeOrderBtnMobile) placeOrderBtnMobile.disabled = true;

    try {
        const prepareRes = await fetch('/api/checkout/prepare', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ items: itemsToHold })
        });
        const prepareResult = await prepareRes.json();

        if (prepareResult.success) {
            initStockHoldTimer(prepareResult.expires_at);
        } else {
            throw new Error(prepareResult.message || 'Gagal memvalidasi stok.');
        }
    } catch (error) {
        if (timerContainer) {
            timerContainer.innerHTML = `${error.message} <a href="/cart" style="color: white; text-decoration: underline;">Kembali ke keranjang</a>.`;
            timerContainer.classList.add('expired');
        }
        if (form) {
            form.querySelectorAll('input, button, select').forEach(el => {
                if (el.id !== 'voucher_code' && el.id !== 'applyVoucherBtn') {
                    el.disabled = true;
                }
            });
            if (placeOrderBtn) placeOrderBtn.disabled = true;
            if (placeOrderBtnMobile) placeOrderBtnMobile.disabled = true;
        }
    }
}

export function initCheckoutPage() {
    initCheckoutForm();
    initMobileCtaHandlers();
    initVoucherHandler();
    initShippingCalculation();

    cartStore.subscribe(renderCheckoutSummary);
    renderCheckoutSummary(cartStore.getState());

    if (window.IS_USER_LOGGED_IN) {
        initStockHoldTimer();
    } else {
        prepareCheckout();
    }
}