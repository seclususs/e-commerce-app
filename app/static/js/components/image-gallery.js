export function initProductImageGallery() {
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

    let currentIndex = 0,
        startX = 0,
        currentTranslate = 0,
        prevTranslate = 0;
    let isDragging = false,
        animationID = 0;

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