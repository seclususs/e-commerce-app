import { showNotification } from '../../components/notification.js';

export function initAdminImagePreviews() {
    const setupImagePreview = (inputId, previewContainerId, fileNameDisplayId) => {
        const imageInput = document.getElementById(inputId);
        const previewContainer = document.getElementById(previewContainerId);
        const fileDisplay = document.getElementById(fileNameDisplayId);

        if (!imageInput || !previewContainer) return;

        imageInput.addEventListener('change', function(event) {
            previewContainer.querySelectorAll('.new-preview').forEach(el => el.remove());

            const files = Array.from(event.target.files);

            if (files.length === 0) {
                if (fileDisplay) fileDisplay.textContent = 'Belum ada file baru dipilih';
                ensureMainImageSelection();
                return;
            }

            if (fileDisplay) fileDisplay.textContent = `${files.length} file dipilih`;

            files.forEach((file, index) => {
                const reader = new FileReader();
                reader.onload = function(e) {
                    const previewItem = document.createElement('div');
                    previewItem.classList.add('preview-item', 'new-preview');
                    previewItem.setAttribute('role', 'radio');
                    previewItem.setAttribute('aria-label', `Pilih ${file.name} sebagai gambar utama`);
                    previewItem.tabIndex = 0;

                    const img = document.createElement('img');
                    img.src = e.target.result;
                    img.alt = `Pratinjau ${file.name}`;
                    previewItem.appendChild(img);

                    const radio = document.createElement('input');
                    radio.type = 'radio';
                    radio.name = 'main_image';
                    radio.className = 'main-image-radio';
                    radio.value = file.name;
                    radio.tabIndex = -1;
                    previewItem.appendChild(radio);

                    const mainIndicator = document.createElement('div');
                    mainIndicator.className = 'main-image-indicator';
                    mainIndicator.innerHTML = '<i class="fas fa-star"></i> Utama';
                    previewItem.appendChild(mainIndicator);

                    previewContainer.appendChild(previewItem);

                    const anyMainSelected = document.querySelector('input[name="main_image"]:checked');
                    if (!anyMainSelected && index === 0) {
                         radio.checked = true;
                         handleMainImageChange(radio);
                    }
                }
                reader.readAsDataURL(file);
            });
            ensureMainImageSelection();
        });
    };

    const handleMainImageChange = (radioInput) => {
        document.querySelectorAll('.preview-item').forEach(item => {
            item.classList.remove('is-main');
            item.setAttribute('aria-checked', 'false');
        });

        if (radioInput && radioInput.checked) {
            const parentItem = radioInput.closest('.preview-item');
            if (parentItem && !parentItem.classList.contains('marked-for-deletion')) {
                parentItem.classList.add('is-main');
                parentItem.setAttribute('aria-checked', 'true');
            } else {
                 radioInput.checked = false;
                 ensureMainImageSelection();
            }
        }
    };

    const ensureMainImageSelection = () => {
         const checkedRadio = document.querySelector('input[name="main_image"]:checked');
         const allAvailableImages = document.querySelectorAll('.preview-item:not(.marked-for-deletion)');

         let isCheckedValid = false;
         if (checkedRadio) {
             const parentItem = checkedRadio.closest('.preview-item');
             if (parentItem && !parentItem.classList.contains('marked-for-deletion')) {
                 isCheckedValid = true;
             } else if (parentItem) {
                 checkedRadio.checked = false;
                 isCheckedValid = false;
             } else {
                 checkedRadio.checked = false;
                 isCheckedValid = false;
             }
         }

         if (!isCheckedValid) {
             const firstAvailableRadio = document.querySelector('.preview-item:not(.marked-for-deletion) .main-image-radio');

             if (firstAvailableRadio) {
                 firstAvailableRadio.checked = true;
                 handleMainImageChange(firstAvailableRadio);
             } else {
                 document.querySelectorAll('.preview-item').forEach(item => {
                     item.classList.remove('is-main');
                     item.setAttribute('aria-checked', 'false');
                 });
                 const anyImageExists = document.querySelector('.preview-item');
                 if (anyImageExists) {
                    showNotification('Peringatan: Tidak ada gambar yang tersisa untuk dijadikan gambar utama.', true);
                 }
             }
         } else if (checkedRadio){
             handleMainImageChange(checkedRadio);
         }
    };

    const form = document.querySelector('form[action*="/admin/edit_product"], form[action*="/admin/products"]');
    if (form) {
        if (form.action.includes('/admin/edit_product')) {
            setupImagePreview('new_images', 'new-image-previews', 'new-file-name');
        } else {
            setupImagePreview('images', 'image-previews', 'file-name');
        }
    }

    const formArea = document.querySelector('.admin-card form[data-ajax="true"]');
    if (formArea) {
        formArea.addEventListener('change', function(e) {
            if (e.target.matches('input[name="main_image"].main-image-radio')) {
                handleMainImageChange(e.target);
            }
            if (e.target.matches('.delete-image-checkbox')) {
                const previewItem = e.target.closest('.preview-item');
                if (previewItem) {
                    const isDeleting = e.target.checked;
                    previewItem.classList.toggle('marked-for-deletion', isDeleting);
                    ensureMainImageSelection();
                }
            }
        });

        formArea.addEventListener('click', function(e) {
            const previewItem = e.target.closest('.preview-item');
            
            if (previewItem && !e.target.closest('.custom-checkbox')) {
                const radio = previewItem.querySelector('.main-image-radio');
                if (radio && !radio.checked && !radio.disabled && !previewItem.classList.contains('marked-for-deletion')) {
                    radio.checked = true;
                    handleMainImageChange(radio);
                }
            }
        });

        formArea.addEventListener('keydown', function(e) {
            const previewItem = e.target.closest('.preview-item');
            
            if (previewItem && (e.key === 'Enter' || e.key === ' ') && !e.target.closest('.custom-checkbox')) {
                 e.preventDefault();
                 const radio = previewItem.querySelector('.main-image-radio');
                 if (radio && !radio.checked && !radio.disabled && !previewItem.classList.contains('marked-for-deletion')) {
                     radio.checked = true;
                     handleMainImageChange(radio);
                 }
            }
        });

        formArea.querySelectorAll('.delete-image-checkbox').forEach(cb => {
            const item = cb.closest('.preview-item');
            if (item) {
                item.classList.toggle('marked-for-deletion', cb.checked);
            }
        });

        const initiallyCheckedRadio = formArea.querySelector('.preview-item.is-main .main-image-radio');
        if (initiallyCheckedRadio) {
             initiallyCheckedRadio.checked = true;
        }

        ensureMainImageSelection();

    }
}

function initVariantCheckbox() {
    const checkbox = document.getElementById('has-variants-checkbox');
    if (!checkbox) return;

    const nonVariantFields = document.getElementById('non-variant-fields');
    const stockInput = document.getElementById('stock');
    const weightInput = document.getElementById('weight_grams');
    const skuInput = document.getElementById('sku');
    const conversionHint = document.getElementById('variant-conversion-hint');
    const nonVariantConversionHint = document.getElementById('non-variant-conversion-hint');
    const manageVariantsPlaceholder = document.getElementById('manage-variants-link-placeholder');
    const isInitiallyVariant = checkbox.dataset.initialState === 'true';

    const toggleInputs = () => {
        const isChecked = checkbox.checked;

        if (nonVariantFields) {
            nonVariantFields.style.display = isChecked ? 'none' : 'block';
        }

        if (stockInput) stockInput.required = !isChecked;
        if (weightInput) weightInput.required = !isChecked;


        if (conversionHint) {
            conversionHint.style.display = !isInitiallyVariant && isChecked ? 'block' : 'none';
        }

        if (nonVariantConversionHint) {
            nonVariantConversionHint.style.display = isInitiallyVariant && !isChecked ? 'block' : 'none';
        }

        if (manageVariantsPlaceholder) {
            const form = checkbox.closest('form');
            const showManageVariants = (!isInitiallyVariant && isChecked) || (isChecked && form && form.action.includes('/admin/products'));
            manageVariantsPlaceholder.style.display = showManageVariants ? 'inline' : 'none';
        }
    };

    checkbox.addEventListener('change', toggleInputs);
    toggleInputs();
}

export function initProductForms() {
    initAdminImagePreviews();
    initVariantCheckbox();
}