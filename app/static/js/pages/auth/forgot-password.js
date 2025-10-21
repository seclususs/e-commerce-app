/**
 * Mengelola logika untuk form lupa password.
 */
export function initForgotPasswordPage() {
    const form = document.getElementById('forgot-password-form');
    const container = document.getElementById('forgot-password-container');

    if (!form || !container) return;
    
    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        const submitBtn = form.querySelector('button[type="submit"]');
        const originalBtnHTML = submitBtn.innerHTML;
        submitBtn.disabled = true;
        submitBtn.innerHTML = `<span class="spinner"></span> Mengirim...`;

        try {
            const response = await fetch(form.action, {
                method: 'POST',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                },
                body: new FormData(form)
            });
            const result = await response.json();
            
            if (response.ok && result.success) {
                // Dapatkan URL login dari link yang sudah ada di halaman
                const loginLink = container.querySelector('a[href*="/login"]').href;
                container.innerHTML = `
                    <h2 class="section-title">Email Terkirim</h2>
                    <p style="text-align: center; color: var(--color-text-med); margin-bottom: 1.5rem;">
                        ${result.message}
                    </p>
                    <a href="${loginLink}" class="cta-button" style="width:100%;">Kembali ke Login</a>
                `;
            } else {
                alert(result.message || 'Terjadi kesalahan.');
                submitBtn.disabled = false;
                submitBtn.innerHTML = originalBtnHTML;
            }
        } catch (error) {
            alert('Tidak dapat terhubung ke server. Silakan coba lagi.');
            submitBtn.disabled = false;
            submitBtn.innerHTML = originalBtnHTML;
        }
    });
}