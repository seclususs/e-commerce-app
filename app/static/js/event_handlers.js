const initOrderSuccessPage = () => {
    if (document.querySelector('.order-success-page')) {
        cartModule.clear();
    }
};

const initActionConfirmations = () => {
    const mainContent = document.querySelector('main.page-content-wrapper, .admin-main-content');
    if (!mainContent) return;

    mainContent.addEventListener('click', (e) => {
        const deleteButton = e.target.closest('.btn-delete, .btn-delete-lookalike');
        if (deleteButton) {
            e.preventDefault();
            const form = deleteButton.closest('form');
            const url = deleteButton.href;
            confirmModal.show(
                'Konfirmasi Hapus',
                'Apakah Anda yakin ingin menghapus item ini? Tindakan ini tidak dapat diurungkan.',
                () => { 
                    if (form) {
                        const actionName = deleteButton.getAttribute('name');
                        const actionValue = deleteButton.getAttribute('value');

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

const initQuickCheckout = () => {
    const checkoutBtn = document.getElementById('checkoutBtn');
    if (!checkoutBtn) return;
    
    checkoutBtn.addEventListener('click', async () => {
        const paymentMethodEl = document.getElementById('paymentMethodModal');
        const paymentMethod = paymentMethodEl ? paymentMethodEl.value : null;
        const cart = cartModule.getCart();

        if (Object.keys(cart).length === 0) return showNotification("Keranjang Anda kosong!", true);
        if (!paymentMethod) return showNotification("Silakan pilih metode pembayaran.", true);

        checkoutBtn.disabled = true;
        checkoutBtn.textContent = 'Memproses...';

        try {
            const response = await fetch('/api/quick_checkout', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ cart, payment_method: paymentMethod })
            });
            const result = await response.json();

            if (response.ok) {
                window.location.href = '/order_success';
            } else {
                showNotification(result.message || 'Gagal membuat pesanan.', true);
                if (result.redirect) {
                     setTimeout(() => { window.location.href = result.redirect; }, 2000);
                }
            }
        } catch (error) {
            showNotification('Terjadi kesalahan saat checkout.', true);
        } finally {
            checkoutBtn.disabled = false;
            checkoutBtn.textContent = 'Checkout Cepat';
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
    const mainImage = document.getElementById('mainProductImage');
    const gallery = document.querySelector('.product-image-gallery');
    
    if (!mainImage || !gallery) return;

    gallery.addEventListener('click', function(e) {
        const thumbnail = e.target.closest('.thumbnail-item');
        if (!thumbnail) return;

        const clickedIndex = Array.from(gallery.querySelectorAll('.thumbnail-item')).findIndex(item => item === thumbnail);
        
        if(window.updateSwipeableGallery) {
             window.updateSwipeableGallery(clickedIndex);
        }
    });
};

const initSwipeableGallery = () => {
    const mainImageContainer = document.querySelector('.product-image-gallery .main-image');
    const mainImage = document.getElementById('mainProductImage');
    const thumbnailsContainer = document.querySelector('.thumbnail-gallery');
    const dotsContainer = document.getElementById('galleryDots');

    if (!mainImageContainer || !mainImage) return;

    const thumbnails = thumbnailsContainer ? Array.from(thumbnailsContainer.querySelectorAll('.thumbnail-item')) : [];
    if (thumbnails.length <= 1) {
        if(dotsContainer) dotsContainer.style.display = 'none';
        return;
    }

    const imageUrls = thumbnails.map(thumb => thumb.querySelector('img').getAttribute('data-full-src'));
    let currentIndex = 0;
    let startX = 0;
    let isSwiping = false;

    if (dotsContainer) {
        dotsContainer.innerHTML = '';
        imageUrls.forEach((_, index) => {
            const dot = document.createElement('span');
            dot.classList.add('gallery-dot');
            dot.dataset.index = index;
            dotsContainer.appendChild(dot);
        });
    }
    const dots = dotsContainer ? Array.from(dotsContainer.querySelectorAll('.gallery-dot')) : [];

    const updateGallery = (newIndex) => {
        if (newIndex < 0) newIndex = imageUrls.length - 1;
        else if (newIndex >= imageUrls.length) newIndex = 0;
        
        currentIndex = newIndex;

        mainImage.style.opacity = 0;
        setTimeout(() => { mainImage.src = imageUrls[currentIndex]; mainImage.style.opacity = 1; }, 200);

        if (thumbnails.length > 0) {
            thumbnails.forEach((item, index) => {
                item.classList.toggle('active', index === currentIndex);
                if (index === currentIndex) item.scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'center' });
            });
        }
        
        if (dots.length > 0) {
            dots.forEach((dot, index) => dot.classList.toggle('active', index === currentIndex));
        }
    };
    
    window.updateSwipeableGallery = updateGallery;

    if(dotsContainer) {
        dotsContainer.addEventListener('click', (e) => {
            if(e.target.matches('.gallery-dot')) {
                updateGallery(parseInt(e.target.dataset.index));
            }
        });
    }

    mainImageContainer.addEventListener('touchstart', (e) => { startX = e.touches[0].clientX; isSwiping = true; }, { passive: true });
    mainImageContainer.addEventListener('touchend', (e) => {
        if (!isSwiping) return;
        const endX = e.changedTouches[0].clientX;
        const diffX = startX - endX;
        if (Math.abs(diffX) > 50) {
            updateGallery(currentIndex + (diffX > 0 ? 1 : -1));
        }
        isSwiping = false;
    });

    updateGallery(0);
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