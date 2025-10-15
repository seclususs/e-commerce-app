const initOrderSuccessPage = () => {
    // Membersihkan keranjang setelah pesanan berhasil
    if (document.querySelector('.order-success-page')) {
        // Panggil fungsi clear dari cartModule setelah halaman dimuat
        cartModule.clear();
    }
};

const initActionConfirmations = () => {
    const mainContent = document.querySelector('main.page-content-wrapper, .admin-main-content');
    if (!mainContent) return;

    // Listener untuk klik (misalnya, tombol hapus)
    mainContent.addEventListener('click', (e) => {
        const deleteButton = e.target.closest('.btn-delete');
        if (deleteButton) {
            e.preventDefault();
            const url = deleteButton.href;
            confirmModal.show(
                'Konfirmasi Hapus',
                'Apakah Anda yakin ingin menghapus item ini? Tindakan ini tidak dapat diurungkan.',
                () => { window.location.href = url; }
            );
        }
    });

    // Listener untuk submit form (misalnya, form pembatalan pesanan)
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
                // Redirect akan membersihkan keranjang melalui initOrderSuccessPage
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
        
        // Jika link logout ditemukan
        if (logoutLink) {
            e.preventDefault(); // Hentikan aksi default link
            localStorage.removeItem('hackthreadCart'); // Hapus keranjang dari local storage
            // Arahkan ke URL yang ada di atribut href dari link yang benar
            window.location.href = logoutLink.href;
        }
    });
};

const initProductGallery = () => {
    const mainImage = document.getElementById('mainProductImage');
    const gallery = document.querySelector('.product-image-gallery');
    
    if (!mainImage || !gallery) return;

    const thumbnails = gallery.querySelectorAll('.thumbnail-item');
    
    gallery.addEventListener('click', function(e) {
        const thumbnail = e.target.closest('.thumbnail-item');
        if (!thumbnail) return;

        const fullSrc = thumbnail.querySelector('img').getAttribute('data-full-src');
        
        // Cari index thumbnail yang diklik
        const clickedIndex = Array.from(thumbnails).findIndex(item => item === thumbnail);
        
        // Panggil fungsi swipeable gallery untuk update (jika ada)
        // Ini akan mengupdate gambar utama, thumbnail aktif, dan titik-titik
        if(window.updateSwipeableGallery) {
             window.updateSwipeableGallery(clickedIndex);
        } else {
            // Fallback jika swipeable gallery tidak ada
            thumbnails.forEach(item => item.classList.remove('active'));
            thumbnail.classList.add('active');
            if (mainImage.src !== fullSrc) {
                mainImage.style.opacity = 0;
                setTimeout(() => {
                    mainImage.src = fullSrc;
                    mainImage.style.opacity = 1;
                }, 200);
            }
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

    // Buat dots
    if (dotsContainer) {
        dotsContainer.innerHTML = ''; // Hapus dots yang mungkin sudah ada
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
                if (index === currentIndex) {
                    item.classList.add('active');
                    item.scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'center' });
                } else {
                    item.classList.remove('active');
                }
            });
        }
        
        if (dots.length > 0) {
            dots.forEach((dot, index) => dot.classList.toggle('active', index === currentIndex));
        }
    };
    
    // Jadikan fungsi update dapat diakses secara global
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
        if (Math.abs(diffX) > 50) { // Swipe threshold
            updateGallery(currentIndex + (diffX > 0 ? 1 : -1));
        }
        isSwiping = false;
    });

    updateGallery(0); // Inisialisasi
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

// [BARU] Handler untuk tombol CTA mobile di halaman checkout
const initMobileCtaHandlers = () => {
    const mobileCheckoutBtn = document.getElementById('placeOrderBtnMobile');
    const mainCheckoutBtn = document.getElementById('placeOrderBtn');
    const checkoutForm = document.getElementById('checkout-form');

    if (mobileCheckoutBtn && mainCheckoutBtn && checkoutForm) {
        // Sinkronisasi status disabled antara tombol utama dan mobile
        const observer = new MutationObserver(mutations => {
            mutations.forEach(mutation => {
                if (mutation.attributeName === 'disabled') {
                    mobileCheckoutBtn.disabled = mainCheckoutBtn.disabled;
                }
            });
        });
        observer.observe(mainCheckoutBtn, { attributes: true });
        mobileCheckoutBtn.disabled = mainCheckoutBtn.disabled; // Sinkronisasi awal

        // Event listener untuk tombol mobile
        mobileCheckoutBtn.addEventListener('click', () => {
            checkoutForm.requestSubmit(); // Submit form terkait
        });
    }
};

// Handler untuk tombol detail di kartu admin mobile
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
            // Perbarui teks tombol dan ikon
            toggleBtn.innerHTML = `${btnText} <i class="fas fa-chevron-down"></i>`;
        }
    });
};