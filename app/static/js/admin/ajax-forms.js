import { showNotification, confirmModal } from '../utils/ui.js';

/**
 * Menangani aksi 'prepend' setelah AJAX berhasil.
 * Fungsi ini secara dinamis menambahkan baris HTML baru ke awal tabel
 * tanpa perlu me-refresh halaman, sesuai dengan permintaan.
 * @param {HTMLFormElement} form Form yang di-submit.
 * @param {object} result Objek JSON dari server yang berisi partial HTML.
 */
function handlePrependAction(form, result) {
    const target = document.querySelector(form.dataset.updateTarget);
    if (target && result.html) {
        // Hapus pesan "Belum ada item" jika ada sebelum menambahkan baris baru.
        const noItemRow = target.querySelector('.no-items-row');
        if (noItemRow) noItemRow.remove();

        // Menggunakan insertAdjacentHTML untuk menambahkan elemen HTML baru (baris produk)
        // ke bagian atas dari body tabel (target). Ini adalah inti dari pembaruan dinamis.
        target.insertAdjacentHTML('afterbegin', result.html);
        form.reset();
        
        // Reset khusus untuk form tambah produk untuk membersihkan preview gambar.
        if(form.id === 'add-product-form') {
            document.getElementById('image-previews').innerHTML = '';
            document.getElementById('file-name').textContent = 'Belum ada file dipilih';
        }
        
        // Memberikan efek highlight visual pada baris yang baru ditambahkan.
        const newRow = target.firstElementChild;
        if (newRow) {
            newRow.style.backgroundColor = 'rgba(59, 130, 246, 0.2)';
            setTimeout(() => {
                newRow.style.transition = 'background-color 0.5s ease';
                newRow.style.backgroundColor = '';
                setTimeout(() => newRow.style.transition = '', 500);
            }, 100);
        }
    }
}

/**
 * Menangani aksi 'update-text' setelah AJAX berhasil.
 * Memperbarui nilai input teks.
 * @param {HTMLFormElement} form Form yang di-submit.
 * @param {object} result Objek JSON dari server.
 */
function handleUpdateTextAction(form, result) {
    const target = document.querySelector(form.dataset.updateTarget);
    if (target && result.data && result.data.name) {
        target.value = result.data.name;
    }
}

/**
 * Menangani aksi 'update-status' untuk halaman detail pesanan.
 * @param {HTMLFormElement} form Form yang di-submit.
 * @param {object} result Objek JSON dari server.
 */
function handleUpdateStatusAction(form, result) {
     if (result.data) {
        const statusBadge = document.querySelector('.status-badge');
        const trackingInput = document.querySelector('input[name="tracking_number"]');
        if (statusBadge) {
            statusBadge.className = `status-badge status-${result.data.status_class}`;
            statusBadge.textContent = result.data.status;
        }
        if (trackingInput) {
            trackingInput.value = result.data.tracking_number || '';
        }
    }
}

/**
 * Menangani hasil dari aksi massal (bulk action).
 * @param {HTMLFormElement} form Form yang di-submit.
 * @param {object} result Objek JSON dari server.
 */
function handleBulkActionResult(form, result) {
    if(result.action === 'delete') {
        result.ids.forEach(id => {
            document.querySelector(`#product-row-${id}`)?.remove();
        });
    } else if (result.action === 'set_category') {
        result.ids.forEach(id => {
            const cell = document.querySelector(`#product-row-${id} .category-name-cell`);
            if(cell) cell.textContent = result.new_category_name;
        });
    }
    // Reset form dan pilihan setelah aksi berhasil
    const select = document.getElementById('bulk-action-select');
    if (select) select.value = '';
    document.querySelectorAll('.product-checkbox').forEach(cb => cb.checked = false);
    const selectAll = document.getElementById('select-all-products');
    if(selectAll) selectAll.checked = false;
    
    const categorySelector = document.getElementById('bulk-category-selector');
    if(categorySelector) categorySelector.classList.add('hidden');
}

/**
 * Menangani aksi 'redirect' setelah AJAX berhasil.
 * @param {HTMLFormElement} form Form yang di-submit.
 * @param {object} result Objek JSON dari server.
 */
function handleRedirectAction(form, result) {
    if (result.redirect_url) {
        window.location.href = result.redirect_url;
    }
}

/**
 * Menangani aksi 'update-inputs' setelah AJAX berhasil.
 * Memperbarui nilai input dalam baris tabel yang sama.
 * @param {HTMLFormElement} form Form yang di-submit.
 * @param {object} result Objek JSON dari server.
 */
function handleUpdateInputsAction(form, result) {
    if (result.data) {
        Object.keys(result.data).forEach(key => {
            const input = form.querySelector(`input[name="${key}"]`);
            if (input) {
                input.value = result.data[key];
            }
        });
    }
}


/**
 * Dispatcher: Memilih fungsi update UI yang sesuai berdasarkan data-update-action.
 * @param {HTMLFormElement} form - Form yang di-submit.
 * @param {object} result - Objek JSON yang diterima dari server.
 */
function handleUIUpdate(form, result) {
    const action = form.dataset.updateAction || 'none';
    const actionHandlers = {
        'prepend': handlePrependAction,
        'update-text': handleUpdateTextAction,
        'update-status': handleUpdateStatusAction,
        'bulk-action': handleBulkActionResult,
        'redirect': handleRedirectAction,
        'update-inputs': handleUpdateInputsAction
    };

    if (actionHandlers[action]) {
        actionHandlers[action](form, result);
    }
}


/**
 * Mengirim data form secara asinkron.
 * @param {HTMLFormElement} form - Form yang di-submit.
 * @param {HTMLElement} button - Tombol submit yang diklik.
 */
export async function handleAjaxSubmit(form, button) {
    const originalButtonHTML = button.innerHTML;
    const isUpdate = button.textContent.toLowerCase().includes('update');
    button.disabled = true;
    button.innerHTML = `<span class="spinner" style="display: inline-block; animation: spin 0.8s ease-in-out infinite; width: 1em; height: 1em; border-width: 2px;"></span> ${isUpdate ? 'Updating...' : 'Menyimpan...'}`;

    // Unformat harga sebelum submit
    const priceInputs = form.querySelectorAll('input[name="price"], input[name="discount_price"]');
    const originalPrices = new Map();
    priceInputs.forEach(input => {
        originalPrices.set(input, input.value);
        input.value = String(input.value).replace(/[^0-9]/g, '');
    });

    try {
        const response = await fetch(form.getAttribute('action'), {
            method: form.method || 'POST',
            body: new FormData(form),
        });

        const result = await response.json();

        if (response.ok && result.success) {
            showNotification(result.message || 'Berhasil!', false);
            handleUIUpdate(form, result);
             // Reset form jika ada flag
            if (form.hasAttribute('data-reset-on-success')) {
                form.reset();
            }
        } else {
            showNotification(result.message || 'Terjadi kesalahan.', true);
        }
    } catch (error) {
        console.error('Fetch error:', error);
        showNotification('Tidak dapat terhubung ke server.', true);
    } finally {
        button.disabled = false;
        button.innerHTML = originalButtonHTML;
        // Format kembali harga ke nilai aslinya jika submit gagal dan form tidak di-reset
        if (!form.hasAttribute('data-reset-on-success')) {
             priceInputs.forEach(input => {
                input.value = originalPrices.get(input);
             });
        }
    }
}

/**
 * Menangani aksi hapus via AJAX dengan modal konfirmasi.
 * @param {HTMLAnchorElement} link - Tautan hapus yang diklik.
 */
function handleAjaxDelete(link) {
    const url = link.href;
    const targetSelector = link.dataset.removeTarget;
    
    confirmModal.show(
        'Konfirmasi Hapus',
        'Apakah Anda yakin ingin menghapus item ini? Tindakan ini tidak dapat diurungkan.',
        async () => {
            try {
                const response = await fetch(url, { method: 'POST' });
                const result = await response.json();
                if (response.ok && result.success) {
                    showNotification(result.message || 'Berhasil dihapus.');
                    const targetElement = document.querySelector(targetSelector);
                    if (targetElement) {
                        targetElement.remove();
                    } else {
                        window.location.reload(); // Fallback
                    }
                } else {
                    showNotification(result.message || 'Gagal menghapus.', true);
                }
            } catch (error) {
                showNotification('Error koneksi.', true);
            }
        }
    );
}

/**
 * Menangani aksi toggle (misal: aktif/nonaktif) via AJAX.
 * @param {HTMLAnchorElement} link - Tautan toggle yang diklik.
 */
async function handleAjaxToggle(link) {
    const url = link.href;
    const row = link.closest('tr');
    
    try {
        const response = await fetch(url, { method: 'POST' });
        const result = await response.json();
        if (response.ok && result.success) {
            showNotification(result.message);
            // Perbarui UI berdasarkan data yang dikembalikan
            if (row && result.data) {
                const statusCell = row.querySelector('.status-cell');
                const newStatus = result.data.is_active;
                if (statusCell) {
                    statusCell.innerHTML = `<span class="status-badge status-${newStatus ? 'completed' : 'cancelled'}">${newStatus ? 'Aktif' : 'Nonaktif'}</span>`;
                }
                link.textContent = newStatus ? 'Nonaktifkan' : 'Aktifkan';
            }
        } else {
            showNotification(result.message || 'Gagal mengubah status.', true);
        }
    } catch (error) {
        showNotification('Error koneksi.', true);
    }
}


/**
 * Menginisialisasi semua event listener untuk form dan link AJAX di area admin.
 */
export function initAjaxAdminForms() {
    const adminContent = document.querySelector('.admin-content-area');
    if (!adminContent) return;

    // Listener untuk submit form
    adminContent.addEventListener('submit', e => {
        // Form `bulk-action-form` ditangani secara terpisah di `ui-handlers.js`
        if (e.target.matches('form[data-ajax="true"]') && e.target.id !== 'bulk-action-form') {
            e.preventDefault();
            const submitter = e.submitter || e.target.querySelector('button[type="submit"]');
            if (submitter) {
                handleAjaxSubmit(e.target, submitter);
            }
        }
    });

    // Listener untuk klik pada link
    adminContent.addEventListener('click', e => {
        const link = e.target.closest('a[data-ajax="true"]');
        if (!link) return;

        e.preventDefault();
        
        if (link.classList.contains('action-link-delete')) {
            handleAjaxDelete(link);
        } else if (link.classList.contains('toggle-voucher-btn')) {
            handleAjaxToggle(link);
        }
    });
}