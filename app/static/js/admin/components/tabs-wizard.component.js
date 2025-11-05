import { showNotification } from '../../components/notification.js';

export function initAdminTabs() {
    const tabContainers = document.querySelectorAll('.admin-tabs-container, #product-editor-container');

    tabContainers.forEach(container => {
        const tabList = container.querySelector('.admin-tabs');
        if (!tabList) return;

        tabList.addEventListener('click', (e) => {
            const tabButton = e.target.closest('.admin-tab-btn');
            if (!tabButton || tabButton.classList.contains('active')) return;

            const targetTabId = tabButton.dataset.tab;
            if (!targetTabId) return;

            const contentContainer = container.querySelector('.admin-tab-content') ? container : document;

            tabList.querySelectorAll('.admin-tab-btn').forEach(btn => {
                btn.classList.remove('active');
            });
            contentContainer.querySelectorAll('.admin-tab-content').forEach(content => {
                content.classList.remove('active');
            });

            tabButton.classList.add('active');
            const targetContent = contentContainer.querySelector(`#${targetTabId}`);
            if (targetContent) {
                targetContent.classList.add('active');
            }
        });
    });
}

export function initAdminWizard() {
    const wizardContainer = document.getElementById('add-product-wizard-container');
    if (!wizardContainer) return;

    const form = document.getElementById('add-product-form');
    const steps = Array.from(wizardContainer.querySelectorAll('.wizard-step'));
    const navPrev = wizardContainer.querySelector('#wizard-prev');
    const navNext = wizardContainer.querySelector('#wizard-next');
    const navSubmit = wizardContainer.querySelector('#wizard-submit');
    const progressBar = wizardContainer.querySelector('#wizard-progress-bar');
    const progressSteps = wizardContainer.querySelectorAll('.wizard-progress-step');

    let currentStep = 1;
    const totalSteps = steps.length;
    let variantCounter = 0;

    const updateWizardUI = () => {
        steps.forEach((step, index) => {
            step.classList.toggle('active', (index + 1) === currentStep);
        });

        navPrev.style.display = currentStep === 1 ? 'none' : 'inline-flex';
        navNext.style.display = currentStep === totalSteps ? 'none' : 'inline-flex';
        navSubmit.style.display = currentStep === totalSteps ? 'inline-flex' : 'none';

        const progressPercent = totalSteps > 1 ? ((currentStep - 1) / (totalSteps - 1)) * 100 : 0;
        progressBar.style.width = `${progressPercent}%`;

        progressSteps.forEach((stepEl, index) => {
            stepEl.classList.toggle('active', (index + 1) <= currentStep);
        });
    };
    
    const productTypeRadios = form.querySelectorAll('input[name="product_type"]');
    const simpleStockFields = wizardContainer.querySelector('#wizard-simple-stock-fields');
    const variantStockFields = wizardContainer.querySelector('#wizard-variant-stock-fields');
    const hiddenHasVariants = document.getElementById('has_variants_hidden_input');
    const simpleStockInput = wizardContainer.querySelector('#stock');
    const simpleWeightInput = wizardContainer.querySelector('#weight_grams');

    const updateStep4Content = () => {
        const selectedType = form.querySelector('input[name="product_type"]:checked').value;
        const isSimple = selectedType === 'simple';
        if (simpleStockFields) simpleStockFields.style.display = isSimple ? 'block' : 'none';
        if (variantStockFields) variantStockFields.style.display = isSimple ? 'none' : 'block';
        if (hiddenHasVariants) hiddenHasVariants.value = isSimple ? 'false' : 'true';
        if (simpleStockInput) simpleStockInput.required = isSimple;
        if (simpleWeightInput) simpleWeightInput.required = isSimple;
    };
    
    const addVariantBtn = document.getElementById('wizard-add-variant-btn');
    const variantListWrapper = document.getElementById('wizard-variant-list-items-wrapper');
    const noVariantsHint = document.getElementById('wizard-no-variants-hint');
    const variantListHeader = document.getElementById('wizard-variant-list-header');

    if (addVariantBtn && variantListWrapper && noVariantsHint && variantListHeader) {
        addVariantBtn.addEventListener('click', () => {
            const colorInput = document.getElementById('new_variant_color');
            const sizeInput = document.getElementById('new_variant_size');
            const stockInput = document.getElementById('new_variant_stock');
            const weightInput = document.getElementById('new_variant_weight');
            const skuInput = document.getElementById('new_variant_sku');

            const color = colorInput.value.trim();
            const size = sizeInput.value.trim();
            const stock = stockInput.value.trim();
            const weight = weightInput.value.trim();
            const sku = skuInput.value.trim();

            if (!color || !size || !stock || !weight) {
                showNotification('Warna, Ukuran, Stok, dan Berat wajib diisi.', true);
                if (!color) colorInput.focus();
                else if (!size) sizeInput.focus();
                else if (!stock) stockInput.focus();
                else if (!weight) weightInput.focus();
                return;
            }

            noVariantsHint.style.display = 'none';
            variantListHeader.style.display = 'grid';

            const variantIndex = variantCounter++;
            const variantItem = document.createElement('div');
            
            variantItem.className = 'wizard-variant-list-item';
            variantItem.style.display = 'grid';
            variantItem.style.gridTemplateColumns = '2fr 1fr 1fr 1.5fr 0.5fr';
            variantItem.style.gap = '1rem';
            variantItem.style.padding = '1rem';
            variantItem.style.borderBottom = '1px solid var(--color-border-subtle)';
            variantItem.style.alignItems = 'center';
            variantItem.style.background = 'var(--color-background-body)';

            variantItem.innerHTML = `
                <div>
                    <strong style="color: var(--color-text-primary); font-size: 0.9em;">${color} / ${size}</strong>
                </div>
                <div style="font-size: 0.9em;">${stock}</div>
                <div style="font-size: 0.9em;">${weight}g</div>
                <div style="font-size: 0.9em; word-break: break-all;">${sku || 'N/A'}</div>
                <div style="text-align: right;">
                    <button type="button" class="remove-social-link wizard-remove-variant" title="Hapus Varian" style="margin-left: auto; padding: 0 0.25rem;">&times;</button>
                </div>
                
                <input type="hidden" name="variants[${variantIndex}][color]" value="${color}">
                <input type="hidden" name="variants[${variantIndex}][size]" value="${size}">
                <input type="hidden" name="variants[${variantIndex}][stock]" value="${stock}">
                <input type="hidden" name="variants[${variantIndex}][weight_grams]" value="${weight}">
                <input type="hidden" name="variants[${variantIndex}][sku]" value="${sku || ''}">
            `;
            variantListWrapper.appendChild(variantItem);
            if(variantListWrapper.querySelector('.wizard-variant-list-item:last-child')) {
                 variantListWrapper.querySelectorAll('.wizard-variant-list-item').forEach(item => item.style.borderBottom = '1px solid var(--color-border-subtle)');
                 variantListWrapper.querySelector('.wizard-variant-list-item:last-child').style.borderBottom = 'none';
            }

            colorInput.value = '';
            sizeInput.value = '';
            stockInput.value = '';
            weightInput.value = '';
            skuInput.value = '';
            colorInput.focus();
        });

        variantListWrapper.addEventListener('click', (e) => {
            if (e.target.classList.contains('wizard-remove-variant')) {
                e.target.closest('.wizard-variant-list-item').remove();
                
                if (variantListWrapper.querySelectorAll('.wizard-variant-list-item').length === 0) {
                    noVariantsHint.style.display = 'block';
                    variantListHeader.style.display = 'none';
                } else {
                    if(variantListWrapper.querySelector('.wizard-variant-list-item:last-child')) {
                         variantListWrapper.querySelectorAll('.wizard-variant-list-item').forEach(item => item.style.borderBottom = '1px solid var(--color-border-subtle)');
                         variantListWrapper.querySelector('.wizard-variant-list-item:last-child').style.borderBottom = 'none';
                    }
                }
            }
        });
    }

    const validateStep = (step) => {
        const stepElement = steps[step - 1];
        if (!stepElement) return false;

        const inputs = stepElement.querySelectorAll('input[required], textarea[required], select[required]');
        for (const input of inputs) {
            if (input.offsetParent !== null) { 
                if (input.type === 'file') {
                    const fileInput = document.getElementById('images');
                    if (!fileInput.fileStore || fileInput.fileStore.size === 0) {
                        showNotification(`Harap pilih gambar produk`, true);
                        return false;
                    }
                } else if (!input.value.trim()) {
                    input.focus();
                    const label = input.labels?.[0]?.textContent || input.name;
                    showNotification(`Harap isi kolom '${label}'`, true);
                    return false;
                }
            }
        }
        
        if (step === 4) {
            const selectedType = form.querySelector('input[name="product_type"]:checked').value;
            if (selectedType === 'variant') {
                const variantCount = variantListWrapper.querySelectorAll('.wizard-variant-list-item').length;
                if (variantCount === 0) {
                    showNotification('Harap tambahkan setidaknya satu varian.', true);
                    document.getElementById('new_variant_color').focus();
                    return false;
                }
            }
        }
        return true;
    };

    navNext.addEventListener('click', () => {
        if (validateStep(currentStep) && currentStep < totalSteps) {
            if (currentStep === 3) {
                updateStep4Content();
            }
            currentStep++;
            updateWizardUI();
        }
    });

    navPrev.addEventListener('click', () => {
        if (currentStep > 1) {
            currentStep--;
            updateWizardUI();
        }
    });

    if (productTypeRadios.length > 0) {
        updateStep4Content();
        productTypeRadios.forEach(radio => {
             radio.addEventListener('change', updateStep4Content);
        });
    }
    updateWizardUI();
}