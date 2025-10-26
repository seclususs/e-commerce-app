import { confirmModal } from '../components/confirm-modal.js';

export function initActionConfirmations() {
    const mainContent = document.querySelector('main.page-content-wrapper, .admin-main-content');
    if (!mainContent) return;

    mainContent.addEventListener('click', (e) => {
        const deleteLink = e.target.closest('.action-link-delete');
        if (deleteLink) {
            e.preventDefault();
            const url = deleteLink.href;
            confirmModal.show(
                'Konfirmasi Hapus',
                'Apakah Anda yakin ingin menghapus item ini? Tindakan ini tidak dapat diurungkan.',
                () => { if(url) window.location.href = url; }
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
}