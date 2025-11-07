export function initGlobalPriceFormatting() {
    const adminForms = document.querySelectorAll('#adminContentArea form');
    if (adminForms.length === 0) return;

    const formatPrice = (value) => {
        const numStr = String(value).replace(/[^0-9]/g, '');
        if (!numStr) return '';
        return parseInt(numStr, 10).toLocaleString('id-ID');
    };

    const unformatPrice = (value) => String(value).replace(/[^0-9]/g, '');

    adminForms.forEach(form => {
        const priceInputs = form.querySelectorAll('input[inputmode="numeric"]');

        priceInputs.forEach(input => {
            if (input.dataset.formatted) return;

            input.type = 'text';
            input.setAttribute('inputmode', 'numeric');
            input.setAttribute('pattern', '[0-9.,]*');
            input.value = formatPrice(input.value);
            input.dataset.formatted = 'true';

            input.addEventListener('input', (e) => {
                const cursorPosition = e.target.selectionStart;
                const originalValue = e.target.value;
                const originalLength = originalValue.length;
                const unformatted = unformatPrice(originalValue);
                const formatted = formatPrice(unformatted);
                e.target.value = formatted;
                const newLength = formatted.length;
                let newCursorPosition = cursorPosition + (newLength - originalLength);
                newCursorPosition = Math.max(0, newCursorPosition);
                newCursorPosition = Math.min(newLength, newCursorPosition);

                if (originalLength > newLength && cursorPosition === originalLength) {
                    newCursorPosition = newLength;
                }

                e.target.setSelectionRange(newCursorPosition, newCursorPosition);
            });
        });
    });
}