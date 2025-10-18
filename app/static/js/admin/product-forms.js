/**
 * Mengelola fungsionalitas khusus untuk formulir produk di area admin,
 * seperti pratinjau gambar dan pemformatan harga.
 */
export function initAdminImagePreviews() {
    const setupImagePreview = (inputId, previewContainerId, fileNameDisplayId, mainImageInputId) => {
        const imageInput = document.getElementById(inputId);
        const previewContainer = document.getElementById(previewContainerId);
        const fileDisplay = document.getElementById(fileNameDisplayId);
        const mainImageInput = mainImageInputId ? document.getElementById(mainImageInputId) : null;

        if (!imageInput || !previewContainer || !fileDisplay) return;

        imageInput.addEventListener('change', function(event) {
            previewContainer.innerHTML = '';
            const files = Array.from(event.target.files);

            if (files.length === 0) {
                fileDisplay.textContent = 'Belum ada file dipilih';
                if (mainImageInput) mainImageInput.value = '';
                return;
            }
            
            fileDisplay.textContent = `${files.length} file dipilih`;

            files.forEach((file, index) => {
                const reader = new FileReader();
                reader.onload = function(e) {
                    const previewItem = document.createElement('div');
                    previewItem.classList.add('preview-item');
                    const img = document.createElement('img');
                    img.src = e.target.result;
                    previewItem.appendChild(img);

                    if (mainImageInput) {
                        const radio = document.createElement('input');
                        radio.type = 'radio';
                        radio.name = 'main_image_selector';
                        radio.className = 'main-image-radio';
                        radio.value = file.name;
                        
                        if (index === 0) {
                            radio.checked = true;
                            mainImageInput.value = file.name;
                            previewItem.classList.add('is-main');
                        }
                        
                        radio.addEventListener('change', function() {
                            document.querySelectorAll(`#${previewContainerId} .preview-item`).forEach(item => item.classList.remove('is-main'));
                            mainImageInput.value = this.value;
                            previewItem.classList.add('is-main');
                        });
                        previewItem.appendChild(radio);
                    }
                    previewContainer.appendChild(previewItem);
                }
                reader.readAsDataURL(file);
            });
        });
    };

    // Untuk form tambah produk
    setupImagePreview('images', 'image-previews', 'file-name', 'main_image_input');
    
    // Untuk form edit produk (gambar baru)
    setupImagePreview('new_images', 'new-image-previews', 'new-file-name', null);

    // Event listener untuk gambar yang sudah ada di form edit
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
}

export function initAdminPriceFormatting() {
    const productForms = document.querySelectorAll('form[action*="/admin/products"], form[action*="/admin/edit_product"]');
    if (productForms.length === 0) return;

    const formatPrice = (value) => {
        const numStr = String(value).replace(/[^0-9]/g, '');
        return numStr ? parseInt(numStr, 10).toLocaleString('id-ID') : '';
    };

    const unformatPrice = (value) => String(value).replace(/[^0-9]/g, '');

    productForms.forEach(form => {
        const priceInputs = form.querySelectorAll('input[name="price"], input[name="discount_price"]');

        priceInputs.forEach(input => {
            input.type = 'text';
            input.setAttribute('inputmode', 'numeric');
            input.value = formatPrice(input.value);
            input.addEventListener('input', (e) => e.target.value = formatPrice(e.target.value));
        });

        form.addEventListener('submit', () => {
            priceInputs.forEach(input => input.value = unformatPrice(input.value));
        });
    });
}

export function initProductForms() {
    initAdminImagePreviews();
    initAdminPriceFormatting();
}