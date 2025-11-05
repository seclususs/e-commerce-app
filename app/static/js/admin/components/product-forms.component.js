import { showNotification } from '../../components/notification.js';

export function initAdminImagePreviews() {
    const setupImagePreview = (inputId, previewContainerId, fileNameDisplayId) => {
        const imageInput = document.getElementById(inputId);
        const previewContainer = document.getElementById(previewContainerId);
        const fileDisplay = document.getElementById(fileNameDisplayId);

        if (!imageInput || !previewContainer) return;
        imageInput.value = null;
        if (imageInput.fileStore) {
            imageInput.fileStore = new DataTransfer().files;
        }

        imageInput.addEventListener('change', function(event) {
            if (previewContainer.id === 'image-previews') {
                 previewContainer.innerHTML = '';
            }

            const files = Array.from(event.target.files);

            if (inputId === 'images') {
                 imageInput.fileStore = event.target.files;
            }

            if (files.length === 0) {
                if (fileDisplay) fileDisplay.textContent = 'Belum ada file baru dipilih';
                ensureMainImageSelection();
                return;
            }

            if (fileDisplay) {
                const totalFiles = (previewContainer.id === 'image-previews') 
                    ? files.length 
                    : (document.querySelectorAll('.preview-item.new-preview').length + files.length);
                fileDisplay.textContent = `${files.length} file baru dipilih`;
            }


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
                    radio.value = (inputId === 'images') ? file.name : `new_${file.name}`;
                    radio.tabIndex = -1;
                    previewItem.appendChild(radio);

                    const mainIndicator = document.createElement('div');
                    mainIndicator.className = 'main-image-indicator';
                    mainIndicator.innerHTML = '<i class="fas fa-star"></i> Utama';
                    previewItem.appendChild(mainIndicator);

                    const removeBtn = document.createElement('button');
                    removeBtn.type = 'button';
                    removeBtn.className = 'remove-new-preview-btn';
                    removeBtn.innerHTML = '&times;';
                    removeBtn.title = 'Hapus gambar ini';
                    removeBtn.onclick = (e) => {
                        e.stopPropagation();
                        previewItem.remove();
                        if (inputId === 'images' && imageInput.fileStore) {
                            const dt = new DataTransfer();
                            const currentFiles = Array.from(imageInput.fileStore);
                            const fileToRemove = currentFiles.find(f => f.name === file.name);
                            if (fileToRemove) {
                                currentFiles.splice(currentFiles.indexOf(fileToRemove), 1);
                            }
                            currentFiles.forEach(f => dt.items.add(f));
                            imageInput.files = dt.files;
                            imageInput.fileStore = dt.files;
                        }
                         if (fileDisplay) fileDisplay.textContent = `${document.querySelectorAll('.preview-item.new-preview').length} file baru dipilih`;
                        ensureMainImageSelection();
                    };
                    previewItem.appendChild(removeBtn);
                    previewContainer.appendChild(previewItem);

                    const anyMainSelected = document.querySelector('input[name="main_image"]:checked');
                    if (!anyMainSelected) {
                         radio.checked = true;
                         handleMainImageChange(radio);
                    } else {
                         handleMainImageChange(anyMainSelected);
                    }
                }
                reader.readAsDataURL(file);
            });
            setTimeout(ensureMainImageSelection, 100);
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
            } else if (parentItem) {
                 radioInput.checked = false;
                 ensureMainImageSelection();
            } else if (!parentItem) {
                 radioInput.checked = false;
                 ensureMainImageSelection();
            }
        } else if (!radioInput) {
            ensureMainImageSelection();
        }
    };

    const ensureMainImageSelection = () => {
         const checkedRadio = document.querySelector('input[name="main_image"]:checked');
         
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
                 const addProductForm = document.getElementById('add-product-form');
                 if (anyImageExists && !addProductForm) {
                    showNotification('Peringatan: Tidak ada gambar yang tersisa untuk dijadikan gambar utama.', true);
                 }
             }
         } else if (checkedRadio){
             handleMainImageChange(checkedRadio);
         }
    };

    const addProductForm = document.getElementById('add-product-form');
    const editProductForm = document.querySelector('form[action*="/admin/edit_product"]');

    let formArea = null;

    if (editProductForm) {
        formArea = editProductForm;
        setupImagePreview('new_images', 'new-image-previews', 'new-file-name');
    } else if (addProductForm) {
        formArea = addProductForm;
        setupImagePreview('images', 'image-previews', 'file-name');
    }

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
            
            if (previewItem && !e.target.closest('.custom-checkbox') && !e.target.closest('.remove-new-preview-btn')) {
                const radio = previewItem.querySelector('.main-image-radio');
                if (radio && !radio.checked && !radio.disabled && !previewItem.classList.contains('marked-for-deletion')) {
                    radio.checked = true;
                    handleMainImageChange(radio);
                }
            }
        });

        formArea.addEventListener('keydown', function(e) {
            const previewItem = e.target.closest('.preview-item');
            
            if (previewItem && (e.key === 'Enter' || e.key === ' ') && !e.target.closest('.custom-checkbox')  && !e.target.closest('.remove-new-preview-btn')) {
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
    const isInitiallyVariant = checkbox.dataset.initialState === 'true';
    const variantTabButton = document.getElementById('tab-btn-variants');

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

        if (variantTabButton) {
            variantTabButton.style.display = isChecked ? 'flex' : 'none';
            if (!isChecked && variantTabButton.classList.contains('active')) {
                const infoTabButton = document.querySelector('.admin-tab-btn[data-tab="tab-info"]');
                if (infoTabButton) infoTabButton.click();
            }
        }
    };

    checkbox.addEventListener('change', toggleInputs);
    if (document.readyState === 'complete') {
        toggleInputs();
    } else {
        window.addEventListener('load', toggleInputs, { once: true });
    }
}

export function initProductForms() {
    initAdminImagePreviews();
    initVariantCheckbox();
}