import { showNotification } from '../../components/notification.js';

export function initCronButton() {
    const btn = document.getElementById('run-cron-btn');
    if (!btn) return;

    btn.addEventListener('click', async () => {
        const originalText = btn.textContent;
        btn.disabled = true;
        btn.innerHTML = `<span class="spinner" style="display: inline-block; animation: spin 0.8s ease-in-out infinite; width: 1em; height: 1em; border-width: 2px; margin-right: 0.5rem;"></span>Menjalankan...`;

        try {
            const response = await fetch(btn.dataset.url, {
                method: 'POST',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'Content-Type': 'application/json'
                }
            });
            const result = await response.json();
            showNotification(result.message || 'Gagal menjalankan tugas.', !result.success);
        } catch (e) {
            console.error('Cron sim error:', e);
            showNotification('Error koneksi.', true);
        } finally {
            btn.disabled = false;
            btn.innerHTML = originalText;
        }
    });
}