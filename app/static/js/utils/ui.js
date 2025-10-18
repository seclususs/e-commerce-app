/**
 * Menyediakan fungsi-fungsi pembantu untuk elemen UI umum seperti
 * notifikasi, pesan flash, dan modal konfirmasi.
 */

export const showNotification = (message, isError = false) => {
    const notification = document.createElement('div');
    notification.className = `notification ${isError ? 'error' : ''}`;
    notification.textContent = message;
    document.body.appendChild(notification);
    setTimeout(() => notification.remove(), 4000);
};

export const initFlashMessages = () => {
    document.querySelectorAll('.flash-message').forEach((message) => {
        setTimeout(() => {
            message.style.transition = 'opacity 0.5s ease, transform 0.5s ease, margin 0.5s ease, padding 0.5s ease, height 0.5s ease';
            message.style.opacity = '0';
            message.style.transform = 'translateY(-20px)';
            message.style.marginTop = '0';
            message.style.marginBottom = '0';
            message.style.paddingTop = '0';
            message.style.paddingBottom = '0';
            message.style.height = '0';
            setTimeout(() => message.remove(), 500);
        }, 5000);
    });
};

const initConfirmModalSingleton = () => {
    const modal = document.getElementById('confirmModal');
    if (!modal) return { show: () => {}, hide: () => {} };

    const okBtn = document.getElementById('confirmOkBtn');
    const cancelBtn = document.getElementById('confirmCancelBtn');
    const titleEl = document.getElementById('confirmModalTitle');
    const textEl = document.getElementById('confirmModalText');
    let callback = null;

    const show = (title, text, onConfirm) => {
        titleEl.textContent = title;
        textEl.textContent = text;
        callback = onConfirm;
        modal.classList.add('active');
    };

    const hide = () => {
        modal.classList.remove('active');
        callback = null;
    };

    okBtn.addEventListener('click', () => {
        if (callback) callback();
        hide();
    });
    cancelBtn.addEventListener('click', hide);
    modal.addEventListener('click', (e) => (e.target === modal) && hide());

    return { show, hide };
};

export const confirmModal = initConfirmModalSingleton();