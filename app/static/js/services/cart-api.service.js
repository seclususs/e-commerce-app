export const get = () => fetch('/api/user-cart').then(res => res.json());

export const add = (productId, quantity, variantId) => fetch('/api/user-cart', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ product_id: productId, quantity, variant_id: variantId })
}).then(res => res.json());

export const update = (productId, quantity, variantId) => fetch(`/api/user-cart/${productId}/${variantId || 'null'}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ quantity })
}).then(res => res.json());

export const merge = (localCart) => fetch('/api/user-cart/merge', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ local_cart: localCart })
}).then(res => res.json());

export const getGuestCartDetails = (cartItems) => fetch('/api/cart', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ cart_items: cartItems })
}).then(res => res.json());