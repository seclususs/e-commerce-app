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