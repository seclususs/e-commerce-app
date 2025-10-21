/**
 * State management untuk keranjang belanja.
 * Mengelola state untuk pengguna login dan tamu, serta menyediakan
 * metode untuk berinteraksi dengan state tersebut.
 */
import * as cartAPI from '../services/cart-api.js';
import { showNotification } from '../utils/ui.js';

const GUEST_CART_KEY = 'hackthreadVariantCart';

const cartStore = (() => {
    let state = {
        items: [],
        subtotal: 0,
        isInitialized: false,
    };
    let listeners = [];

    const notify = () => {
        // Update count di navbar
        const cartCountEl = document.getElementById('cartCount');
        if (cartCountEl) {
            const totalItems = state.items.reduce((sum, item) => sum + item.quantity, 0);
            cartCountEl.textContent = totalItems;
            cartCountEl.style.display = totalItems > 0 ? 'flex' : 'none';
        }
        // Notifikasi listener lain (misal: halaman keranjang)
        listeners.forEach(listener => listener(state));
    };
    
    const loadGuestCart = () => {
        return JSON.parse(localStorage.getItem(GUEST_CART_KEY)) || {};
    }

    const refreshState = async () => {
        if (window.IS_USER_LOGGED_IN) {
            const data = await cartAPI.get();
            state.items = data.items || [];
            state.subtotal = data.subtotal || 0;
        } else {
            const guestCart = loadGuestCart();
            const cartKeys = Object.keys(guestCart);
            if (cartKeys.length === 0) {
                state.items = [];
                state.subtotal = 0;
            } else {
                const detailedItems = await cartAPI.getGuestCartDetails(guestCart);
                const subtotal = detailedItems.reduce((sum, p) => {
                    const effectivePrice = (p.discount_price && p.discount_price > 0) ? p.discount_price : p.price;
                    return sum + (effectivePrice * p.quantity);
                }, 0);
                state.items = detailedItems;
                state.subtotal = subtotal;
            }
        }
        notify();
    };

    return {
        init: async () => {
            if (state.isInitialized) return;
            await refreshState();
            state.isInitialized = true;
        },
        subscribe: (listener) => {
            listeners.push(listener);
            return () => { // Unsubscribe function
                listeners = listeners.filter(l => l !== listener);
            }
        },
        getState: () => {
            return { ...state };
        },
        addItem: async (productId, quantity, variantId, name, stock) => {
            if (window.IS_USER_LOGGED_IN) {
                const res = await cartAPI.add(productId, quantity, variantId);
                if (!res.success) {
                    showNotification(res.message, true);
                    return false;
                }
            } else {
                const cartKey = variantId ? `${productId}-${variantId}` : `${productId}-null`;
                const currentCart = loadGuestCart();
                const currentInCart = currentCart[cartKey]?.quantity || 0;
                
                if (currentInCart + quantity > stock) {
                    showNotification(`Stok tidak mencukupi. Anda sudah punya ${currentInCart} di keranjang.`, true);
                    return false;
                }
                 currentCart[cartKey] = { quantity: currentInCart + quantity };
                 localStorage.setItem(GUEST_CART_KEY, JSON.stringify(currentCart));
            }
            await refreshState();
            return true;
        },
        updateItem: async (productId, quantity, variantId) => {
             if (window.IS_USER_LOGGED_IN) {
                const res = await cartAPI.update(productId, quantity, variantId);
                if (!res.success && res.message) showNotification(res.message, true);
            } else {
                const cartKey = variantId ? `${productId}-${variantId}` : `${productId}-null`;
                const newCart = loadGuestCart();
                if (quantity <= 0) {
                    delete newCart[cartKey];
                } else {
                     const itemToUpdate = state.items.find(item => item.id == productId && (item.variant_id || 'null') == (variantId || 'null'));
                     if(itemToUpdate && quantity > itemToUpdate.stock) {
                         showNotification(`Stok tidak mencukupi. Sisa stok: ${itemToUpdate.stock}.`, true);
                         return;
                     }
                    newCart[cartKey] = { quantity: quantity };
                }
                localStorage.setItem(GUEST_CART_KEY, JSON.stringify(newCart));
            }
            await refreshState();
        },
        syncOnLogin: async () => {
            const localCart = loadGuestCart();
            if (Object.keys(localCart).length > 0) {
                await cartAPI.merge(localCart);
                localStorage.removeItem(GUEST_CART_KEY);
            }
            window.IS_USER_LOGGED_IN = true;
            await refreshState();
        }
    };
})();

export { cartStore };