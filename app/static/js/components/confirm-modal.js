const initConfirmModalSingleton = () => {
    const modal = document.getElementById('confirmModal');
    if (!modal) return { show: () => {}, hide: () => {} };

    const okBtn = document.getElementById('confirmOkBtn');
    const cancelBtn = document.getElementById('confirmCancelBtn');
    const titleEl = document.getElementById('confirmModalTitle');
    const textEl = document.getElementById('confirmModalText');
    let onConfirmCallback = null;
    let onCancelCallback = null;

    const show = (title, text, onConfirm, onCancel = null) => {
        titleEl.textContent = title;
        textEl.textContent = text;
        onConfirmCallback = onConfirm;
        onCancelCallback = onCancel;
        modal.classList.add('active');
    };

    const hide = (isCancel = false) => {
        modal.classList.remove('active');
        if (isCancel && onCancelCallback) {
            onCancelCallback();
        }
        onConfirmCallback = null;
        onCancelCallback = null;
    };

    okBtn.addEventListener('click', () => {
        if (onConfirmCallback) onConfirmCallback();
        hide(false);
    });
    
    cancelBtn.addEventListener('click', () => hide(true));
    modal.addEventListener('click', (e) => (e.target === modal) && hide(true));

    return { show, hide };
};

export const confirmModal = initConfirmModalSingleton();