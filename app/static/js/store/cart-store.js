import * as cartAPI from '../services/cart-api.service.js';
import { showNotification } from '../components/notification.js';

const GUEST_CART_KEY = 'hackthreadVariantCart';

const cartStore = (() => {
    let state = {
        items: [],
        subtotal: 0,
        isInitialized: false,
    };
    let listeners = [];

    const notify = () => {
        const cartCountEl = document.getElementById('cartCount');
        if (cartCountEl) {
            const totalItems = state.items.reduce((sum, item) => sum + item.quantity, 0);
            cartCountEl.textContent = totalItems;
            cartCountEl.style.display = totalItems > 0 ? 'flex' : 'none';
        }
        listeners.forEach(listener => listener(state));
    };

    const loadGuestCart = () => {
        try {
            return JSON.parse(localStorage.getItem(GUEST_CART_KEY)) || {};
        } catch (e) {
            console.error("Error loading guest cart from localStorage:", e);
            localStorage.removeItem(GUEST_CART_KEY);
            return {};
        }
    }

    const saveGuestCart = (cart) => {
         try {
             localStorage.setItem(GUEST_CART_KEY, JSON.stringify(cart));
         } catch (e) {
              console.error("Error saving guest cart to localStorage:", e);
              showNotification("Gagal menyimpan keranjang Anda. Penyimpanan lokal mungkin penuh.", true);
         }
    };

    const refreshState = async () => {
        try {
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
                        const effectivePrice = Number(p.effective_price) || 0;
                        return sum + (effectivePrice * p.quantity);
                    }, 0);
                    state.items = detailedItems;
                    state.subtotal = subtotal;
                }
            }
        } catch (error) {
            console.error("Error refreshing cart state:", error);
            showNotification("Gagal memuat keranjang. Coba segarkan halaman.", true);
            state.items = [];
            state.subtotal = 0;
        } finally {
             notify();
        }
    };

    return {
        init: async () => {
            if (state.isInitialized) return;
            await refreshState();
            state.isInitialized = true;
        },
        subscribe: (listener) => {
            listeners.push(listener);
            return () => {
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
                    showNotification(`Stok tidak mencukupi. Anda sudah punya ${currentInCart} di keranjang. Sisa stok: ${stock}.`, true);
                    return false;
                }
                currentCart[cartKey] = { quantity: currentInCart + quantity };
                saveGuestCart(currentCart);
            }
            await refreshState();
            return true;
        },
        updateItem: async (productId, quantity, variantId) => {
             let success = true;
            if (window.IS_USER_LOGGED_IN) {
                const res = await cartAPI.update(productId, quantity, variantId);
                if (!res.success) {
                     success = false;
                     if (res.message) showNotification(res.message, true);
                }
            } else {
                const cartKey = variantId ? `${productId}-${variantId}` : `${productId}-null`;
                const newCart = loadGuestCart();
                if (quantity <= 0) {
                    delete newCart[cartKey];
                } else {
                    
                    const itemToUpdate = state.items.find(item => item.id == productId && (item.variant_id || 'null') == (variantId || 'null'));
                    if (itemToUpdate && quantity > itemToUpdate.stock) {
                        showNotification(`Stok tidak mencukupi. Sisa stok: ${itemToUpdate.stock}. Kuantitas tidak diubah.`, true);
                        success = false;
                        
                        return;
                    }
                    newCart[cartKey] = { quantity: quantity };
                }
                if (success) {
                    saveGuestCart(newCart);
                }
            }
            if (success) {
               await refreshState();
            }
        },
        syncOnLogin: async () => {
            const localCart = loadGuestCart();
            let mergeSuccess = true;
            if (Object.keys(localCart).length > 0) {
                try {
                    const mergeResult = await cartAPI.merge(localCart);
                    if (!mergeResult.success) {
                        mergeSuccess = false;
                        showNotification(mergeResult.message || "Gagal menggabungkan keranjang tamu.", true);
                    }
                } catch (error) {
                     mergeSuccess = false;
                     console.error("Error merging cart:", error);
                     showNotification("Gagal terhubung untuk menggabungkan keranjang.", true);
                }
            }

            if (mergeSuccess && Object.keys(localCart).length > 0) {
                 localStorage.removeItem(GUEST_CART_KEY);
            }

            window.IS_USER_LOGGED_IN = true;
            await refreshState();
        }
    };
})();

export { cartStore };