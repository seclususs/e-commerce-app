import { showNotification } from '../utils/ui.js';
import { initProductImageGallery } from '../components/image-gallery.js';

let selectedVariantId = null;

function initSizeSelector() {
    const sizeSelector = document.getElementById('size-selector');
    if (!sizeSelector) return;

    const sizeWarning = document.getElementById('size-warning');
    const addToCartBtn = document.querySelector('.add-to-cart-btn');
    const quantityInput = document.getElementById('quantity-input');
    const stockDisplay = document.getElementById('stock-display');

    sizeSelector.addEventListener('click', (e) => {
        const target = e.target.closest('.size-option-btn');
        if (!target || target.disabled) return;
        
        document.querySelectorAll('.size-option-btn').forEach(btn => btn.classList.remove('active'));
        target.classList.add('active');
        
        selectedVariantId = target.dataset.variantId;
        const maxStock = parseInt(target.dataset.stock, 10);

        sizeWarning.textContent = '';
        addToCartBtn.disabled = false;
        
        quantityInput.max = maxStock;
        if (parseInt(quantityInput.value) > maxStock) {
            quantityInput.value = maxStock;
        }
        
        stockDisplay.innerHTML = `<span style="color: #f59e0b;">Ukuran ${target.textContent}: ${maxStock}</span>`;
        
        // Perbarui state tombol kuantitas
        document.getElementById('quantity-plus').disabled = (parseInt(quantityInput.value) >= maxStock);
    });
}

function initQuantitySelector() {
    const quantityInput = document.getElementById('quantity-input');
    if (!quantityInput) return;

    const minusBtn = document.getElementById('quantity-minus');
    const plusBtn = document.getElementById('quantity-plus');
    const stockWarning = document.getElementById('stock-warning');
    const hasVariants = document.querySelector('.add-to-cart-btn').dataset.hasVariants === 'true';

    const validateStock = () => {
        const currentValue = parseInt(quantityInput.value, 10);
        let maxStock;

        if (hasVariants) {
            const activeSize = document.querySelector('.size-option-btn.active');
            if (!activeSize) { // Jika belum ada ukuran dipilih
                plusBtn.disabled = true;
                minusBtn.disabled = true;
                return;
            }
            maxStock = parseInt(activeSize.dataset.stock, 10);
        } else {
            maxStock = parseInt(quantityInput.max, 10);
        }
        
        let warningMessage = '';
        if (currentValue >= maxStock) {
            warningMessage = `Stok maksimum tercapai.`;
            plusBtn.disabled = true;
        } else {
            plusBtn.disabled = false;
        }

        minusBtn.disabled = currentValue <= 1;
        stockWarning.textContent = warningMessage;
    };

    const updateQuantity = (change) => {
        let currentValue = parseInt(quantityInput.value, 10) || 1;
        let newValue = currentValue + change;
        let maxStock;

        if (hasVariants) {
            const activeSize = document.querySelector('.size-option-btn.active');
            if (!activeSize) return; // Jangan ubah kuantitas jika ukuran belum dipilih
            maxStock = parseInt(activeSize.dataset.stock, 10);
        } else {
            maxStock = parseInt(quantityInput.max, 10);
        }

        if (newValue < 1) newValue = 1;
        if (newValue > maxStock) newValue = maxStock;
        
        quantityInput.value = newValue;
        validateStock();
    };

    minusBtn.addEventListener('click', () => updateQuantity(-1));
    plusBtn.addEventListener('click', () => updateQuantity(1));
    quantityInput.addEventListener('input', () => {
         let value = parseInt(quantityInput.value, 10);
         const max = parseInt(quantityInput.max, 10);
         if (isNaN(value) || value < 1) {
             quantityInput.value = 1;
         } else if (value > max) {
             quantityInput.value = max;
         }
         validateStock();
     });

    validateStock();
}

// Social Share Popup Handler
function initSocialShare() {
    const shareLinks = document.getElementById('social-share-links');
    if (!shareLinks) return;

    shareLinks.addEventListener('click', function(e) {
        const link = e.target.closest('a.social-share-btn');
        if (!link) return;

        e.preventDefault();
        const url = link.href;
        const width = 600;
        const height = 400;
        const left = (window.innerWidth / 2) - (width / 2);
        const top = (window.innerHeight / 2) - (height / 2);
        
        window.open(url, 'shareWindow', `width=${width},height=${height},top=${top},left=${left},toolbar=no,location=no,directories=no,status=no,menubar=no,scrollbars=yes,resizable=yes`);
    });
}

async function handleReviewSubmit(form, button) {
    button.disabled = true;
    button.innerHTML = `<span class="spinner"></span> Mengirim...`;

    try {
        const response = await fetch(form.action, {
            method: 'POST',
            headers: { 'X-Requested-With': 'XMLHttpRequest' },
            body: new FormData(form),
        });

        const result = await response.json();

        if (response.ok && result.success) {
            showNotification(result.message);
            const reviewsGrid = document.getElementById('reviews-grid');
            const noReviewsMsg = document.getElementById('no-reviews-message');
            if (noReviewsMsg) noReviewsMsg.remove();
            
            reviewsGrid.insertAdjacentHTML('afterbegin', result.review_html);
            document.getElementById('review-form-container').innerHTML = `
                <div class="admin-card add-review-form" style="text-align: center;">
                    <p style="color: var(--color-success); margin:0;">Terima kasih! Ulasan Anda telah ditambahkan.</p>
                </div>`;
        } else {
            showNotification(result.message || 'Gagal mengirim ulasan.', true);
            button.disabled = false;
            button.textContent = 'Kirim Ulasan';
        }

    } catch (error) {
        console.error('Review submit error:', error);
        showNotification('Terjadi kesalahan koneksi.', true);
        button.disabled = false;
        button.textContent = 'Kirim Ulasan';
    }
}


export function initProductDetailPage() {
    initSizeSelector();
    initQuantitySelector();
    initProductImageGallery();
    initSocialShare();

    const addToCartBtn = document.querySelector('.add-to-cart-btn');
    if (addToCartBtn && addToCartBtn.dataset.hasVariants === 'true') {
        addToCartBtn.disabled = true;
        const sizeWarning = document.getElementById('size-warning');
        if (sizeWarning) {
            sizeWarning.textContent = 'Silakan pilih ukuran terlebih dahulu.';
        }
    }

    const reviewForm = document.getElementById('add-review-form');
    if (reviewForm) {
        reviewForm.addEventListener('submit', function(e) {
            e.preventDefault();
            const submitBtn = reviewForm.querySelector('button[type="submit"]');
            handleReviewSubmit(reviewForm, submitBtn);
        });
    }
}