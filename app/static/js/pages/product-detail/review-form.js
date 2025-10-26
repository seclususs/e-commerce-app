import { showNotification } from '../../components/notification.js';


async function handleReviewSubmit(form, button) {
    const originalButtonText = button.textContent;
    button.disabled = true;
    button.innerHTML = `<span class="spinner" style="display: inline-block; animation: spin 0.8s ease-in-out infinite; width: 1em; height: 1em; border-width: 2px;"></span> Mengirim...`;

    try {
        const response = await fetch(form.action, {
            method: 'POST',
            headers: { 'X-Requested-With': 'XMLHttpRequest' },
            body: new FormData(form),
        });

        const result = await response.json();

        if (response.ok && result.success) {
            showNotification(result.message);
            const reviewsGrid = document.getElementById('reviews-grid');
            const noReviewsMsg = document.getElementById('no-reviews-message');

            if (noReviewsMsg) noReviewsMsg.remove();

            if (reviewsGrid && result.review_html) {
                reviewsGrid.insertAdjacentHTML('afterbegin', result.review_html);
                form.querySelectorAll('.star-rating input[type="radio"]').forEach(radio => radio.checked = false);
            }

            const formContainer = document.getElementById('review-form-container');
             if (formContainer) {
                 formContainer.innerHTML = `
                    <div class="admin-card add-review-form" style="text-align: center;">
                        <p style="color: var(--color-success); margin:0;">Terima kasih! Ulasan Anda telah ditambahkan.</p>
                    </div>`;
             } else {
                 form.reset();
             }

        } else {
            showNotification(result.message || 'Gagal mengirim ulasan.', true);
            button.disabled = false;
            button.textContent = originalButtonText;
        }

    } catch (error) {
        console.error('Review submit error:', error);
        showNotification('Terjadi kesalahan koneksi.', true);
        button.disabled = false;
        button.textContent = originalButtonText;
    }
}


export function initReviewForm() {
    const reviewForm = document.getElementById('add-review-form');
    if (reviewForm) {
        reviewForm.addEventListener('submit', function(e) {
            e.preventDefault();
            const submitBtn = reviewForm.querySelector('button[type="submit"]');
            handleReviewSubmit(reviewForm, submitBtn);
        });
    }
}