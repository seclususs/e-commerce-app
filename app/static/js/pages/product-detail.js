import { showNotification } from '../utils/ui.js';

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

function initSwipeableGallery() {
    const container = document.querySelector('.gallery-slider-container');
    const slider = document.getElementById('gallerySlider');
    const thumbnailsContainer = document.querySelector('.thumbnail-gallery');

    if (!container || !slider) return;

    const slides = slider.querySelectorAll('.gallery-slide');
    const thumbnails = thumbnailsContainer ? Array.from(thumbnailsContainer.querySelectorAll('.thumbnail-item')) : [];
    
    if (slides.length <= 1) {
        if (thumbnailsContainer) thumbnailsContainer.style.display = 'none';
        return;
    }

    let currentIndex = 0, startX = 0, currentTranslate = 0, prevTranslate = 0;
    let isDragging = false, animationID = 0;

    const getPositionX = (e) => e.type.includes('mouse') ? e.pageX : e.touches[0].clientX;

    const updateGallery = (newIndex, animate = true, scrollThumb = true) => {
        if (newIndex < 0 || newIndex >= slides.length) return;
        
        currentIndex = newIndex;
        const offset = -currentIndex * container.offsetWidth;

        slider.style.transition = animate ? 'transform 0.4s cubic-bezier(0.25, 0.46, 0.45, 0.94)' : 'none';
        slider.style.transform = `translateX(${offset}px)`;
        currentTranslate = prevTranslate = offset;

        if (thumbnails.length > 0) {
            thumbnails.forEach((item, index) => {
                item.classList.toggle('active', index === currentIndex);
                if (index === currentIndex && scrollThumb) {
                    item.scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'center' });
                }
            });
        }
    };
    
    const animation = () => {
        slider.style.transform = `translateX(${currentTranslate}px)`;
        if (isDragging) requestAnimationFrame(animation);
    };

    const dragStart = (e) => {
        isDragging = true;
        startX = getPositionX(e);
        slider.style.transition = 'none';
        animationID = requestAnimationFrame(animation);
        
        if (e.type.includes('mouse')) {
            e.preventDefault();
            window.addEventListener('mousemove', dragMove);
            window.addEventListener('mouseup', dragEnd);
        }
    };

    const dragMove = (e) => {
        if (isDragging) {
            currentTranslate = prevTranslate + getPositionX(e) - startX;
        }
    };

    const dragEnd = (e) => {
        if (!isDragging) return;
        isDragging = false;
        cancelAnimationFrame(animationID);
        
        const movedBy = currentTranslate - prevTranslate;

        if (movedBy < -100 && currentIndex < slides.length - 1) currentIndex++;
        if (movedBy > 100 && currentIndex > 0) currentIndex--;
        
        updateGallery(currentIndex);
        
        if (e.type.includes('mouse')) {
            window.removeEventListener('mousemove', dragMove);
            window.removeEventListener('mouseup', dragEnd);
        }
    };

    container.addEventListener('touchstart', dragStart, { passive: true });
    container.addEventListener('touchmove', dragMove, { passive: true });
    container.addEventListener('touchend', dragEnd);
    container.addEventListener('mousedown', dragStart);

    thumbnails.forEach((thumb, index) => {
        thumb.addEventListener('click', () => updateGallery(index));
    });

    window.addEventListener('resize', () => updateGallery(currentIndex, false, false));
    updateGallery(0, false, false);
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

export function initProductDetailPage() {
    initSizeSelector();
    initQuantitySelector();
    initSwipeableGallery();
    initSocialShare();

    const addToCartBtn = document.querySelector('.add-to-cart-btn');
    if (addToCartBtn && addToCartBtn.dataset.hasVariants === 'true') {
        addToCartBtn.disabled = true;
        const sizeWarning = document.getElementById('size-warning');
        if (sizeWarning) {
            sizeWarning.textContent = 'Silakan pilih ukuran terlebih dahulu.';
        }
    }
}

export { selectedVariantId };