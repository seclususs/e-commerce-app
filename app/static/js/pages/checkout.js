import { cartStore } from '../store/cart-store.js';

const formatRupiah = (num) => (
    `Rp ${Number(num).toLocaleString('id-ID', {
        minimumFractionDigits: 0, maximumFractionDigits: 0
    })}`
);

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
        const priceNum = Number(p.price) || 0;
        const discountPriceNum = Number(p.discount_price) || 0;
        const effectivePrice = (
            (discountPriceNum && discountPriceNum > 0)
            ? discountPriceNum
            : priceNum
        );
        const colorInfo = p.color ? `${p.color}` : '';
        const sizeInfo = p.size ? `${p.size}` : '';
        const variantInfo = (colorInfo || sizeInfo)
            ? ` (${[colorInfo, sizeInfo].filter(Boolean).join(' / ')})`
            : '';
            
        return (
            `<div class="summary-row">
                <span>${p.name}${variantInfo} (x${p.quantity})</span>
                <span>${formatRupiah(effectivePrice * p.quantity)}</span>
            </div>`
        );
    }).join('');

    const subtotalNum = Number(subtotal) || 0;
    if (subtotalEl) subtotalEl.textContent = formatRupiah(subtotalNum);
    if (totalEl) totalEl.textContent = formatRupiah(subtotalNum);

    if (!window.IS_USER_LOGGED_IN && cartDataInput) {
        const guestCart = items.reduce((acc, item) => {
            const key = (
                item.variant_id
                ? `${item.id}-${item.variant_id}`
                : `${item.id}-null`
            );
            acc[key] = { quantity: item.quantity };
            return acc;
        }, {});
        cartDataInput.value = JSON.stringify(guestCart);
    }

    const cityElement = (
        document.getElementById('city') ||
        document.querySelector('.address-display-box')
    );
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
                console.warn('Harap lengkapi semua field yang wajib diisi.');
            }
            e.preventDefault();
            return;
        }

        const applyBtn = document.getElementById('applyVoucherBtn');
        if (applyBtn) applyBtn.disabled = true;
        const voucherSelect = document.getElementById('user_voucher_id_select');
        if (voucherSelect) voucherSelect.disabled = true;

        buttons.forEach(btn => {
            btn.disabled = true;
            btn.classList.add('is-loading');
            btn.innerHTML = (
                `<span class="spinner"></span><span>Memproses...</span>`
            );
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
    const voucherCodeInput = document.getElementById('voucher_code');
    const messageEl = document.getElementById('voucher-message');
    const voucherSelect = document.getElementById('user_voucher_id_select');
    const userVoucherIdInput = document.getElementById('user_voucher_id_input');

    if (!applyBtn || !voucherCodeInput || !messageEl || !userVoucherIdInput) {
        return;
    }

    const setVoucherLoading = (isLoading) => {
        if (applyBtn) applyBtn.disabled = isLoading;
        if (voucherCodeInput) voucherCodeInput.disabled = isLoading;
        if (voucherSelect) voucherSelect.disabled = isLoading;
        messageEl.textContent = isLoading ? 'Memvalidasi...' : '';
        messageEl.className = 'voucher-feedback';
    };

    const resetDiscount = () => {
        messageEl.textContent = '';
        messageEl.className = 'voucher-feedback';
        const discountEl = document.getElementById('checkoutDiscount');
        discountEl.textContent = '- Rp 0';
        discountEl.dataset.rawAmount = '0';
        document.querySelector('.discount-row').style.display = 'none';

        if (voucherSelect) voucherSelect.value = '';
        if (voucherCodeInput) voucherCodeInput.value = '';
        if (userVoucherIdInput) userVoucherIdInput.value = '';

        if (voucherCodeInput) voucherCodeInput.disabled = false;
        if (voucherSelect) voucherSelect.disabled = false;
        if (applyBtn) applyBtn.disabled = false;

        const cityElement = (
            document.getElementById('city') ||
            document.querySelector('.address-display-box')
        );
        cityElement?.dispatchEvent(new Event('recalc'));
    };

    const applyVoucherRequest = async (payload) => {
        setVoucherLoading(true);
        const subtotal = Number(cartStore.getState().subtotal) || 0;
        if (isNaN(subtotal)) {
            setVoucherLoading(false);
            return;
        }

        try {
            const response = await fetch('/api/apply-voucher', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ ...payload, subtotal: subtotal })
            });
            const result = await response.json();

            if (result.success) {
                messageEl.textContent = result.message;
                messageEl.classList.add('success');

                const discountAmount = result.discount_amount;
                const discountEl = document.getElementById('checkoutDiscount');
                discountEl.textContent = `- ${formatRupiah(discountAmount)}`;
                discountEl.dataset.rawAmount = discountAmount;
                document.querySelector('.discount-row').style.display = 'flex';

                if (result.user_voucher_id) {
                    userVoucherIdInput.value = result.user_voucher_id;
                    voucherCodeInput.value = '';
                    voucherCodeInput.disabled = true;
                } else if (result.code) {
                    userVoucherIdInput.value = '';
                    if (voucherSelect) voucherSelect.value = '';
                    if (voucherSelect) voucherSelect.disabled = true;
                }

                const cityElement = (
                    document.getElementById('city') ||
                    document.querySelector('.address-display-box')
                );
                cityElement?.dispatchEvent(new Event('recalc'));
            } else {
                messageEl.textContent = result.message;
                messageEl.classList.add('error');
                resetDiscount();
            }
        } catch (error) {
            console.error('Voucher apply error:', error);
            messageEl.textContent = 'Gagal terhubung ke server.';
            messageEl.classList.add('error');
            resetDiscount();
        } finally {
            setVoucherLoading(false);
            if (payload.voucher_code) {
                if (voucherSelect) {
                    voucherSelect.disabled = !messageEl.classList.contains(
                        'error'
                    );
                }
            } else if (payload.user_voucher_id) {
                voucherCodeInput.disabled = !messageEl.classList.contains(
                    'error'
                );
            }
        }
    };

    applyBtn.addEventListener('click', () => {
        const code = voucherCodeInput.value.trim();
        if (code) {
            applyVoucherRequest({ voucher_code: code });
        }
    });

    voucherCodeInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            const code = voucherCodeInput.value.trim();
            if (code) {
                applyVoucherRequest({ voucher_code: code });
            }
        }
    });

    voucherCodeInput.addEventListener('input', () => {
        if (
            messageEl.textContent !== '' ||
            (voucherSelect && voucherSelect.value !== '')
        ) {
            resetDiscount();
        }
    });

    if (voucherSelect) {
        voucherSelect.addEventListener('change', (e) => {
            const userVoucherId = e.target.value;
            if (userVoucherId) {
                applyVoucherRequest({ user_voucher_id: userVoucherId });
            } else {
                resetDiscount();
            }
        });
    }
}


function initStockHoldTimer(expiresAtIsoString) {
    const expiresAtInput = document.getElementById('stock_hold_expires_at');
    const timerEl = document.getElementById('timer');
    const container = document.getElementById('stock-hold-timer-container');
    const expiryTime = (
        expiresAtIsoString ||
        (expiresAtInput ? expiresAtInput.value : null)
    );

    if (!expiryTime || !timerEl || !container) {
        console.warn("Timer elements not found or expiry time missing.");
        return;
    }

    const expiresAt = new Date(expiryTime).getTime();

    if (expiresAt > new Date().getTime()) {
        const placeOrderBtn = document.getElementById('placeOrderBtn');
        const placeOrderBtnMobile = document.getElementById('placeOrderBtnMobile');
        if (placeOrderBtn) placeOrderBtn.disabled = false;
        if (placeOrderBtnMobile) placeOrderBtnMobile.disabled = false;
    } else {
        container.innerHTML = (
            'Waktu penahanan stok habis! <a href="/cart" ' +
            'style="color: white; text-decoration: underline;">' +
            'Kembali ke keranjang</a> untuk validasi ulang.'
        );
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
            container.innerHTML = (
                'Waktu penahanan stok habis! <a href="/cart" ' +
                'style="color: white; text-decoration: underline;">' +
                'Kembali ke keranjang</a> untuk validasi ulang.'
            );
            container.classList.add('expired');
            const placeOrderBtn = document.getElementById('placeOrderBtn');
            const placeOrderBtnMobile = document.getElementById('placeOrderBtnMobile');
            if (placeOrderBtn) placeOrderBtn.disabled = true;
            if (placeOrderBtnMobile) placeOrderBtnMobile.disabled = true;
            return;
        }

        const minutes = Math.floor((distance % (1000 * 60 * 60)) / (1000 * 60));
        const seconds = Math.floor((distance % (1000 * 60)) / 1000);
        timerEl.textContent = (
            `${minutes.toString().padStart(2, '0')}:` +
            `${seconds.toString().padStart(2, '0')}`
        );
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

    if (!totalEl || !shippingRow || !shippingCostEl || !shippingCostInput) {
        return;
    }

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
        const jabodetabek = [
            'jakarta', 'bogor', 'depok', 'tangerang', 'bekasi'
        ];

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

        const subtotal = Number(cartStore.getState().subtotal) || 0;
        const discount = parseFloat(discountEl.dataset.rawAmount || '0') || 0;
        const finalTotal = subtotal + shippingCost - discount;
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
        console.error("Checkout preparation error:", error);
        if (timerContainer) {
            timerContainer.innerHTML = (
                `${error.message} <a href="/cart" ` +
                `style="color: white; text-decoration: underline;">` +
                `Kembali ke keranjang</a>.`
            );
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