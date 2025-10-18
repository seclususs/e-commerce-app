/**
 * Mengelola semua interaksi di halaman detail produk,
 * termasuk galeri gambar dan pemilih kuantitas.
 */

function initQuantitySelector() {
    const quantityInput = document.getElementById('quantity-input');
    if (!quantityInput) return;

    const minusBtn = document.getElementById('quantity-minus');
    const plusBtn = document.getElementById('quantity-plus');
    const stockWarning = document.getElementById('stock-warning');
    const maxStock = parseInt(quantityInput.max, 10);

    const validateStock = () => {
        const currentValue = parseInt(quantityInput.value, 10);
        let warningMessage = '';

        if (currentValue >= maxStock) {
            warningMessage = `Stok tidak mencukupi, maksimum pembelian adalah ${maxStock} unit.`;
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
        
        if (newValue < 1) newValue = 1;
        if (newValue > maxStock) newValue = maxStock;
        
        quantityInput.value = newValue;
        validateStock();
    };

    minusBtn.addEventListener('click', () => updateQuantity(-1));
    plusBtn.addEventListener('click', () => updateQuantity(1));
    quantityInput.addEventListener('input', () => {
        let value = parseInt(quantityInput.value, 10);
        if (isNaN(value) || value < 1) {
            quantityInput.value = 1;
        } else if (value > maxStock) {
            quantityInput.value = maxStock;
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
    
    const touchStart = (e) => {
        isDragging = true;
        startX = e.type.includes('mouse') ? e.pageX : e.touches[0].clientX;
        animationID = requestAnimationFrame(animation);
        slider.style.transition = 'none';
    };

    const touchMove = (e) => {
        if (isDragging) {
            const currentPosition = e.type.includes('mouse') ? e.pageX : e.touches[0].clientX;
            currentTranslate = prevTranslate + currentPosition - startX;
        }
    };

    const touchEnd = () => {
        isDragging = false;
        cancelAnimationFrame(animationID);
        const movedBy = currentTranslate - prevTranslate;

        if (movedBy < -100 && currentIndex < slides.length - 1) currentIndex++;
        if (movedBy > 100 && currentIndex > 0) currentIndex--;
        
        updateGallery(currentIndex);
    };

    function animation() {
        slider.style.transform = `translateX(${currentTranslate}px)`;
        if (isDragging) requestAnimationFrame(animation);
    }
    
    container.addEventListener('touchstart', touchStart, { passive: true });
    container.addEventListener('touchend', touchEnd);
    container.addEventListener('touchmove', touchMove, { passive: true });
    container.addEventListener('mousedown', touchStart);
    container.addEventListener('mouseup', touchEnd);
    container.addEventListener('mouseleave', touchEnd);
    container.addEventListener('mousemove', touchMove);

    thumbnails.forEach((thumb, index) => {
        thumb.addEventListener('click', () => updateGallery(index));
    });

    window.addEventListener('resize', () => updateGallery(currentIndex, false, false));
    updateGallery(0, false, false);
}

export function initProductDetailPage() {
    initQuantitySelector();
    initSwipeableGallery();
}