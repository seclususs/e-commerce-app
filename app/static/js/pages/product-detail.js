import { initProductImageGallery } from '../components/image-gallery.js';
import { initSizeSelector } from './product-detail/size-selector.js';
import { initQuantitySelector } from './product-detail/quantity-handler.js';
import { initSocialShare } from './product-detail/social-share.js';
import { initReviewForm } from './product-detail/review-form.js';

export function initProductDetailPage() {
    initProductImageGallery();
    initSizeSelector();
    initQuantitySelector();
    initSocialShare();
    initReviewForm();
}