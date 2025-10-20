/**
 * Menginisialisasi logika untuk halaman pembayaran,
 * khususnya untuk simulasi webhook pembayaran.
 */
export function initPaymentPage() {
    const simulateBtn = document.getElementById('simulate-payment-btn');
    if (!simulateBtn) return;

    const webhookUrl = simulateBtn.dataset.webhookUrl;
    const apiKey = simulateBtn.dataset.apiKey;
    const successUrl = simulateBtn.dataset.successUrl;
    const transactionId = simulateBtn.dataset.transactionId;

    simulateBtn.addEventListener('click', async () => {
        simulateBtn.disabled = true;
        simulateBtn.textContent = 'Memproses...';

        try {
            const response = await fetch(webhookUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-API-Key': apiKey
                },
                body: JSON.stringify({
                    event: 'payment_status_update',
                    transaction_id: transactionId,
                    status: 'success'
                })
            });

            if (response.ok) {
                window.location.href = successUrl;
            } else {
                const errorData = await response.json();
                alert(`Simulasi gagal: ${errorData.description || 'Cek konsol untuk detail.'}`);
                console.error('Webhook simulation failed:', response.status, errorData);
                simulateBtn.disabled = false;
                simulateBtn.textContent = 'Simulasikan Pembayaran Berhasil';
            }
        } catch (error) {
            console.error('Error simulating payment:', error);
            alert('Terjadi kesalahan saat simulasi.');
            simulateBtn.disabled = false;
            simulateBtn.textContent = 'Simulasikan Pembayaran Berhasil';
        }
    });
}