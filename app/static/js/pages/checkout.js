function initCheckoutForm() {
    const form = document.getElementById('checkout-form');
    if (!form) return;

    const placeOrderBtn = document.getElementById('placeOrderBtn');
    const placeOrderBtnMobile = document.getElementById('placeOrderBtnMobile');
    const buttons = [placeOrderBtn, placeOrderBtnMobile].filter(Boolean);

    form.addEventListener('submit', () => {
        if (!form.checkValidity()) return;

        // Nonaktifkan tombol apply voucher saat submit
        const applyBtn = document.getElementById('applyVoucherBtn');
        if(applyBtn) applyBtn.disabled = true;

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

    const formatRupiah = (num) => `Rp ${num.toLocaleString('id-ID', { minimumFractionDigits: 0 })}`;

    const applyVoucher = async () => {
        const code = voucherInput.value.trim();
        if (!code) return;

        applyBtn.disabled = true;
        messageEl.textContent = 'Memvalidasi...';
        messageEl.className = 'voucher-feedback';

        const subtotalText = document.getElementById('checkoutSubtotal').textContent;
        const subtotal = parseFloat(subtotalText.replace(/[^0-9.]/g, '').replace(/\./g, ''));
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
                document.getElementById('checkoutTotal').textContent = formatRupiah(result.final_total);
                document.querySelector('.discount-row').style.display = 'flex';
                document.getElementById('city')?.dispatchEvent(new Event('change'));

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
        document.getElementById('city')?.dispatchEvent(new Event('change'));
    };

    applyBtn.addEventListener('click', applyVoucher);
    voucherInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            applyVoucher();
        }
    });
    voucherInput.addEventListener('input', resetDiscount);
}

function initStockHoldTimer(expiresAtIsoString) {
    const expiresAtInput = document.getElementById('stock_hold_expires_at');
    const timerEl = document.getElementById('timer');
    const container = document.getElementById('stock-hold-timer-container');
    const expiryTime = expiresAtIsoString || (expiresAtInput ? expiresAtInput.value : null);

    if (!expiryTime || !timerEl || !container) return;

    const expiresAt = new Date(expiryTime).getTime();
    
    const interval = setInterval(() => {
        const now = new Date().getTime();
        const distance = expiresAt - now;

        if (distance < 0) {
            clearInterval(interval);
            container.innerHTML = 'Waktu penahanan stok habis! <a href="/cart" style="color: white; text-decoration: underline;">Kembali ke keranjang</a> untuk validasi ulang.';
            container.classList.add('expired');
            document.getElementById('placeOrderBtn').disabled = true;
            const mobileBtn = document.getElementById('placeOrderBtnMobile');
            if(mobileBtn) mobileBtn.disabled = true;
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
    const subtotalEl = document.getElementById('checkoutSubtotal');
    const discountEl = document.getElementById('checkoutDiscount');
    const shippingCostInput = document.getElementById('shipping_cost_input');

    if (!totalEl || !shippingRow || !shippingCostEl || !shippingCostInput) return;

    const formatRupiah = (num) => `Rp ${num.toLocaleString('id-ID', { minimumFractionDigits: 0 })}`;

    const calculateAndUpdate = () => {
        let city = '';
        if (citySelect) { // Guest
            city = citySelect.value;
        } else if (cityDisplay) { // Logged in
            const cityParagraph = Array.from(cityDisplay.querySelectorAll('p')).find(p => p.textContent.includes(','));
            if(cityParagraph) {
                const parts = cityParagraph.textContent.split(',');
                if (parts.length > 1) {
                    city = parts[0].trim().split('\n').pop().trim();
                }
            }
        }
        
        let shippingCost = 0;
        const jabodetabek = ['Jakarta', 'Bogor', 'Depok', 'Tangerang', 'Bekasi'];

        if (jabodetabek.includes(city)) {
            shippingCost = 10000;
        } else if (city && city !== "") { // Any other city selected
            shippingCost = 20000;
        }
        
        if (shippingCost > 0) {
            shippingRow.style.display = 'flex';
            shippingCostEl.textContent = formatRupiah(shippingCost);
        } else {
            shippingRow.style.display = 'none';
        }

        const subtotalText = subtotalEl.textContent || '0';
        const discountText = discountEl.textContent || '0';
        const subtotal = parseFloat(subtotalText.replace(/[^0-9]/g, '')) || 0;
        const discount = parseFloat(discountText.replace(/[^0-9]/g, '')) || 0;

        const finalTotal = subtotal - discount + shippingCost;
        totalEl.textContent = formatRupiah(finalTotal);
        shippingCostInput.value = shippingCost;
    };

    if (citySelect) {
        citySelect.addEventListener('change', calculateAndUpdate);
    }
    
    const subtotalObserver = new MutationObserver(() => {
        calculateAndUpdate();
        const voucherMessageEl = document.getElementById('voucher-message');
        if (voucherMessageEl) {
            const voucherObserver = new MutationObserver(calculateAndUpdate);
            voucherObserver.observe(voucherMessageEl, { childList: true });
        }
    });

    if (subtotalEl) {
        subtotalObserver.observe(subtotalEl, { childList: true, subtree: true });
    }

    if (window.IS_USER_LOGGED_IN) {
        setTimeout(calculateAndUpdate, 100);
    }
}


async function initGuestCheckout() {
    const GUEST_CART_KEY = 'hackthreadVariantCart';
    const localCart = JSON.parse(localStorage.getItem(GUEST_CART_KEY)) || {};
    const form = document.getElementById('checkout-form');
    const timerContainer = document.getElementById('stock-hold-timer-container');

    if (Object.keys(localCart).length === 0) {
        window.location.href = '/cart';
        return;
    }

    try {
        const productRes = await fetch('/api/cart', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ cart_items: localCart })
        });
        if (!productRes.ok) {
            throw new Error('Gagal memuat detail produk dari keranjang.');
        }
        
        const detailedItems = await productRes.json();
        if (detailedItems.length === 0) {
             throw new Error('Keranjang Anda kosong atau item tidak valid.');
        }

        const prepareRes = await fetch('/api/checkout/prepare', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ items: detailedItems })
        });
        const prepareResult = await prepareRes.json();
        
        if (prepareResult.success) {
            initStockHoldTimer(prepareResult.expires_at);
            document.getElementById('placeOrderBtn')?.removeAttribute('disabled');
            document.getElementById('placeOrderBtnMobile')?.removeAttribute('disabled');
        } else {
            throw new Error(prepareResult.message || 'Gagal memvalidasi stok.');
        }
    } catch (error) {
        if (timerContainer) {
            timerContainer.innerHTML = `${error.message} <a href="/cart" style="color: white; text-decoration: underline;">Kembali ke keranjang</a>.`;
            timerContainer.classList.add('expired');
        }
        if (form) {
            form.querySelectorAll('input, button, select').forEach(el => el.disabled = true);
            const mobileBtn = document.getElementById('placeOrderBtnMobile');
            if(mobileBtn) mobileBtn.disabled = true;
        }
    }
}

export function initCheckoutPage() {
    initCheckoutForm();
    initMobileCtaHandlers();
    initVoucherHandler();
    initShippingCalculation();
    
    if (window.IS_USER_LOGGED_IN) {
        initStockHoldTimer(); 
    } else {
        initGuestCheckout();
    }
}