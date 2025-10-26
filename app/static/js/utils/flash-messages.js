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