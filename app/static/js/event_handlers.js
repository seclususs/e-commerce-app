const initOrderSuccessPage = () => {
    if (document.querySelector('.order-success-page')) {
        cartModule.clear();
    }
};

const initActionConfirmations = () => {
    const mainContent = document.querySelector('main.page-content-wrapper, .admin-main-content');
    if (!mainContent) return;

    mainContent.addEventListener('click', (e) => {
        const deleteLink = e.target.closest('.action-link-delete');
        if (deleteLink) {
            e.preventDefault();
            const form = deleteLink.closest('form');
            const url = deleteLink.href;
            confirmModal.show(
                'Konfirmasi Hapus',
                'Apakah Anda yakin ingin menghapus item ini? Tindakan ini tidak dapat diurungkan.',
                () => { 
                    if (form) {
                        const actionName = deleteLink.getAttribute('name');
                        const actionValue = deleteLink.getAttribute('value');

                        if (actionName && actionValue) {
                            const actionInput = document.createElement('input');
                            actionInput.type = 'hidden';
                            actionInput.name = actionName;
                            actionInput.value = actionValue;
                            form.appendChild(actionInput);
                        }
                        form.submit();
                    } else if(url) {
                        window.location.href = url; 
                    }
                }
            );
        }
    });

    mainContent.addEventListener('submit', (e) => {
        const cancelForm = e.target.closest('.cancel-order-form');
        if (cancelForm) {
            e.preventDefault();
            confirmModal.show(
                'Konfirmasi Pembatalan',
                'Apakah Anda yakin ingin membatalkan pesanan ini?',
                () => { cancelForm.submit(); }
            );
        }
    });
};

const initLogout = () => {
    document.body.addEventListener('click', (e) => {
        const logoutLink = e.target.closest('#logoutLink, #mobileLogoutLink');
        if (logoutLink) {
            e.preventDefault();
            localStorage.removeItem('hackthreadCart');
            window.location.href = logoutLink.href;
        }
    });
};

const initProductGallery = () => {
    const gallery = document.querySelector('.product-image-gallery');
    if (!gallery) return;

    gallery.addEventListener('click', function(e) {
        const thumbnail = e.target.closest('.thumbnail-item');
        if (!thumbnail) return;

        const clickedIndex = Array.from(gallery.querySelectorAll('.thumbnail-item')).findIndex(item => item === thumbnail);
        
        if (window.updateSwipeableGallery) {
             window.updateSwipeableGallery(clickedIndex);
        }
    });
};

const initSwipeableGallery = () => {
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

    let currentIndex = 0;
    let startX = 0;
    let currentTranslate = 0;
    let prevTranslate = 0;
    let isDragging = false;
    let animationID = 0;

    const updateGallery = (newIndex, animate = true, scrollThumb = true) => {
        if (newIndex < 0 || newIndex >= slides.length) return;
        
        currentIndex = newIndex;
        const offset = -currentIndex * container.offsetWidth;

        if (animate) {
            slider.style.transition = 'transform 0.4s cubic-bezier(0.25, 0.46, 0.45, 0.94)';
        } else {
            slider.style.transition = 'none';
        }

        slider.style.transform = `translateX(${offset}px)`;
        currentTranslate = offset;
        prevTranslate = offset;

        if (thumbnails.length > 0) {
            thumbnails.forEach((item, index) => {
                item.classList.toggle('active', index === currentIndex);
                if (index === currentIndex && scrollThumb) {
                    item.scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'center' });
                }
            });
        }
    };
    
    window.updateSwipeableGallery = updateGallery;
    
    const touchStart = (index) => (e) => {
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

        if (movedBy < -100 && currentIndex < slides.length - 1) {
            currentIndex += 1;
        }

        if (movedBy > 100 && currentIndex > 0) {
            currentIndex -= 1;
        }
        
        updateGallery(currentIndex);
    };

    function animation() {
        slider.style.transform = `translateX(${currentTranslate}px)`;
        if (isDragging) requestAnimationFrame(animation);
    }
    
    slides.forEach((slide, index) => {
        slide.addEventListener('touchstart', touchStart(index), { passive: true });
        slide.addEventListener('touchend', touchEnd);
        slide.addEventListener('touchmove', touchMove, { passive: true });
        slide.addEventListener('mousedown', touchStart(index));
        slide.addEventListener('mouseup', touchEnd);
        slide.addEventListener('mouseleave', touchEnd);
        slide.addEventListener('mousemove', touchMove);
    });

    window.addEventListener('resize', () => updateGallery(currentIndex, false, false));

    updateGallery(0, false, false);
};


const initFilterModal = () => {
    const toggleBtn = document.getElementById('filterToggleButton');
    const closeBtn = document.getElementById('closeFilterBtn');
    const canvas = document.getElementById('filterOffCanvas');
    const overlay = document.getElementById('filterOverlay');

    if (!toggleBtn || !canvas || !overlay || !closeBtn) return;

    const openFilter = () => {
        canvas.classList.add('active');
        overlay.classList.add('active');
        document.body.style.overflow = 'hidden';
    };

    const closeFilter = () => {
        canvas.classList.remove('active');
        overlay.classList.remove('active');
        document.body.style.overflow = '';
    };

    toggleBtn.addEventListener('click', openFilter);
    closeBtn.addEventListener('click', closeFilter);
    overlay.addEventListener('click', closeFilter);
};

const initAdminImagePreviews = () => {
    const imageInput = document.getElementById('images');
    const addPreviewContainer = document.getElementById('image-previews');
    const mainImageInput = document.getElementById('main_image_input');
    const addFileDisplay = document.getElementById('file-name');

    if (imageInput && addPreviewContainer && mainImageInput && addFileDisplay) {
        imageInput.addEventListener('change', function(event) {
            addPreviewContainer.innerHTML = '';
            const files = Array.from(event.target.files);

            if (files.length === 0) {
                addFileDisplay.textContent = 'Belum ada file dipilih';
                mainImageInput.value = '';
                return;
            }
            
            addFileDisplay.textContent = `${files.length} file dipilih`;

            files.forEach((file, index) => {
                const reader = new FileReader();
                reader.onload = function(e) {
                    const previewItem = document.createElement('div');
                    previewItem.classList.add('preview-item');
                    const img = document.createElement('img');
                    img.src = e.target.result;
                    const radio = document.createElement('input');
                    radio.type = 'radio';
                    radio.name = 'main_image_selector';
                    radio.classList.add('main-image-radio');
                    radio.value = file.name;
                    
                    if (index === 0) {
                        radio.checked = true;
                        mainImageInput.value = file.name;
                        previewItem.classList.add('is-main');
                    }

                    radio.addEventListener('change', function() {
                        document.querySelectorAll('#image-previews .preview-item').forEach(item => item.classList.remove('is-main'));
                        mainImageInput.value = this.value;
                        previewItem.classList.add('is-main');
                    });
                    
                    previewItem.appendChild(img);
                    previewItem.appendChild(radio);
                    addPreviewContainer.appendChild(previewItem);
                }
                reader.readAsDataURL(file);
            });
        });
    }

    const existingPreviews = document.getElementById('existing-image-previews');
    if (existingPreviews) {
        existingPreviews.addEventListener('change', function(e) {
            if (e.target.matches('.main-image-radio')) {
                existingPreviews.querySelectorAll('.preview-item').forEach(item => item.classList.remove('is-main'));
                e.target.closest('.preview-item').classList.add('is-main');
            }
            if (e.target.matches('.delete-image-checkbox')) {
                e.target.closest('.preview-item').classList.toggle('marked-for-deletion', e.target.checked);
            }
        });
    }

    const newImageInput = document.getElementById('new_images');
    const newPreviewContainer = document.getElementById('new-image-previews');
    const editFileDisplay = document.getElementById('new-file-name');
    if (newImageInput && newPreviewContainer && editFileDisplay) {
        newImageInput.addEventListener('change', function(event) {
            newPreviewContainer.innerHTML = '';
            const files = Array.from(event.target.files);
            editFileDisplay.textContent = files.length > 0 ? `${files.length} file baru dipilih` : 'Belum ada file baru dipilih';
            files.forEach(file => {
                const reader = new FileReader();
                reader.onload = function(e) {
                    const previewItem = document.createElement('div');
                    previewItem.classList.add('preview-item');
                    const img = document.createElement('img');
                    img.src = e.target.result;
                    previewItem.appendChild(img);
                    newPreviewContainer.appendChild(previewItem);
                }
                reader.readAsDataURL(file);
            });
        });
    }
};

const initMobileCtaHandlers = () => {
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
            checkoutForm.requestSubmit();
        });
    }
};

const initAdminCardToggle = () => {
    const adminTable = document.querySelector('.admin-table');
    if (!adminTable) return;

    adminTable.addEventListener('click', (e) => {
        const toggleBtn = e.target.closest('.mobile-details-toggle');
        if (toggleBtn) {
            const row = toggleBtn.closest('.admin-card-row');
            row.classList.toggle('is-expanded');
            
            const isExpanded = row.classList.contains('is-expanded');
            const btnText = isExpanded ? 'Sembunyikan Detail' : 'Lihat Detail';
            toggleBtn.innerHTML = `${btnText} <i class="fas fa-chevron-down"></i>`;
        }
    });
};

// Menggunakan modal kustom untuk konfirmasi hapus massal
const initBulkActions = () => {
    const selectAllCheckbox = document.getElementById('select-all-products');
    const productCheckboxes = document.querySelectorAll('.product-checkbox');
    const bulkActionSelect = document.getElementById('bulk-action-select');
    const bulkCategorySelector = document.getElementById('bulk-category-selector');
    const bulkActionForm = document.getElementById('bulk-action-form');

    if (selectAllCheckbox && productCheckboxes.length > 0) {
        selectAllCheckbox.addEventListener('change', function() {
            productCheckboxes.forEach(checkbox => {
                checkbox.checked = this.checked;
            });
        });
    }

    if (bulkActionSelect && bulkCategorySelector) {
        bulkActionSelect.addEventListener('change', function() {
            if (this.value === 'set_category') {
                bulkCategorySelector.classList.remove('hidden');
            } else {
                bulkCategorySelector.classList.add('hidden');
            }
        });
    }

    if (bulkActionForm) {
        bulkActionForm.addEventListener('submit', function(e) {
            const selectedAction = bulkActionSelect ? bulkActionSelect.value : '';
            const anyProductSelected = document.querySelector('.product-checkbox:checked');

            if (!selectedAction) {
                e.preventDefault();
                showNotification('Silakan pilih aksi massal terlebih dahulu.', true);
                return;
            }
            
            if (!anyProductSelected) {
                e.preventDefault();
                showNotification('Silakan pilih setidaknya satu produk.', true);
                return;
            }

            if (selectedAction === 'delete') {
                e.preventDefault(); // Selalu cegah submit untuk menampilkan modal
                confirmModal.show(
                    'Konfirmasi Hapus Massal',
                    'Apakah Anda yakin ingin menghapus semua produk yang dipilih? Tindakan ini tidak dapat diurungkan.',
                    () => {
                        bulkActionForm.submit(); // Submit form jika dikonfirmasi
                    }
                );
            }
        });
    }
};


// Fungsi untuk memformat input harga di halaman admin
const initAdminPriceFormatting = () => {
    const productForms = document.querySelectorAll('form[action*="/admin/products"], form[action*="/admin/edit_product"]');
    if (productForms.length === 0) {
        return;
    }

    const formatPrice = (value) => {
        if (!value) return '';
        const numberString = String(value).replace(/[^0-9]/g, '');
        if (numberString === '') return '';
        return parseInt(numberString, 10).toLocaleString('id-ID');
    };

    const unformatPrice = (value) => {
        return String(value).replace(/[^0-9]/g, '');
    };

    productForms.forEach(form => {
        const priceInputs = form.querySelectorAll('input[name="price"], input[name="discount_price"]');

        priceInputs.forEach(input => {
            input.type = 'text';
            input.setAttribute('inputmode', 'numeric');
            
            input.value = formatPrice(input.value);

            input.addEventListener('input', (e) => {
                const originalValue = e.target.value;
                const formattedValue = formatPrice(originalValue);
                if (originalValue !== formattedValue) {
                    e.target.value = formattedValue;
                }
            });
        });

        form.addEventListener('submit', () => {
            priceInputs.forEach(input => {
                input.value = unformatPrice(input.value);
            });
        });
    });
};