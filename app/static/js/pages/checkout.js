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

// Fungsi untuk menangani logika voucher
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
        const subtotalText = document.getElementById('checkoutSubtotal').textContent;
        const subtotal = parseFloat(subtotalText.replace(/[^0-9.]/g, '').replace(/\./g, ''));
        
        messageEl.textContent = '';
        messageEl.className = 'voucher-feedback';
        document.querySelector('.discount-row').style.display = 'none';
        document.getElementById('checkoutTotal').textContent = formatRupiah(subtotal);
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

export function initCheckoutPage() {
    initCheckoutForm();
    initMobileCtaHandlers();
    initVoucherHandler();
}