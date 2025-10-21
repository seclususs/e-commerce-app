/**
 * Modul ini berisi semua panggilan fetch API terkait keranjang belanja pengguna.
 * Setiap fungsi mengembalikan promise yang me-resolve dengan data JSON dari server.
 */

/**
 * Mengambil semua item dan subtotal dari keranjang pengguna saat ini.
 * @returns {Promise<object>} Promise yang resolve dengan data keranjang.
 */
export const get = () => fetch('/api/user-cart').then(res => res.json());

/**
 * Menambahkan item ke keranjang pengguna.
 * @param {number} productId ID produk yang akan ditambahkan.
 * @param {number} quantity Jumlah item yang akan ditambahkan.
 * @param {number|null} variantId ID varian produk (jika ada).
 * @returns {Promise<object>} Promise yang resolve dengan hasil operasi dari server.
 */
export const add = (productId, quantity, variantId) => fetch('/api/user-cart', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ product_id: productId, quantity, variant_id: variantId })
}).then(res => res.json());

/**
 * Memperbarui kuantitas item di keranjang pengguna.
 * @param {number} productId ID produk.
 * @param {number} quantity Kuantitas baru.
 * @param {number|null} variantId ID varian produk (jika ada).
 * @returns {Promise<object>} Promise yang resolve dengan hasil operasi dari server.
 */
export const update = (productId, quantity, variantId) => fetch(`/api/user-cart/${productId}/${variantId || 'null'}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ quantity })
}).then(res => res.json());

/**
 * Menggabungkan keranjang lokal (dari localStorage) dengan keranjang pengguna di database setelah login.
 * @param {object} localCart Objek keranjang lokal.
 * @returns {Promise<object>} Promise yang resolve dengan hasil operasi dari server.
 */
export const merge = (localCart) => fetch('/api/user-cart/merge', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ local_cart: localCart })
}).then(res => res.json());

/**
 * Mengambil detail produk berdasarkan item dari keranjang tamu.
 * @param {object} cartItems Objek keranjang tamu.
 * @returns {Promise<Array>} Promise yang resolve dengan array item yang detail.
 */
export const getGuestCartDetails = (cartItems) => fetch('/api/cart', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ cart_items: cartItems })
}).then(res => res.json());