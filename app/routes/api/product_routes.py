from flask import jsonify, request, render_template_string, url_for
from services.product_service import product_service
from . import api_bp

# Template untuk kartu produk yang akan dirender di sisi server
# Ini memastikan konsistensi tampilan dengan yang dirender oleh Jinja di halaman utama.
PRODUCT_CARD_TEMPLATE = """
{% for product in products %}
<div class="product-card animated-element {% if product.stock == 0 %}out-of-stock{% endif %}" data-animation-delay="{{ (loop.index0 % 8) * 75 }}">
    <a href="{{ url_for('product.product_detail', id=product.id) }}" class="product-card-link"></a>
    <div class="product-image">
        {% if product.discount_price and product.discount_price > 0 %}
            <span class="discount-badge">Hemat {{ product.discount_price|percentage(product.price) }}%</span>
        {% endif %}
        <img loading="lazy" src="{{ url_for('static', filename='uploads/' + product.image_url) if product.image_url and product.image_url != 'placeholder.jpg' else 'https://placehold.co/400x400/0f172a/f1f5f9?text=' + product.name }}" alt="{{ product.name }}">
        {% if product.stock == 0 %}<div class="stock-overlay">Stok Habis</div>{% endif %}
    </div>
    <div class="product-info">
        <h3 class="product-name">{{ product.name }}</h3>
        <p class="product-category">{{ product.category_name or 'N/A' }}</p>
        <div class="product-price-container">
            {% if product.discount_price and product.discount_price > 0 %}
                <span class="product-price discount-price">{{ product.discount_price|rupiah }}</span>
                <del class="original-price">{{ product.price|rupiah }}</del>
            {% else %}
                <span class="product-price">{{ product.price|rupiah }}</span>
            {% endif %}
        </div>
        <div class="additional-info">
            {% if product.sizes %}<span>Ukuran: {{ product.sizes }}</span><br>{% endif %}
            <span>Stok: {% if product.stock > 10 %}Tersedia{% elif product.stock > 0 %}Tersisa {{ product.stock }}{% else %}Habis{% endif %}</span>
        </div>
        <button class="cta-button add-to-cart-btn" data-id="{{ product.id }}" data-name="{{ product.name }}" data-stock="{{ product.stock }}" {% if product.stock == 0 %}disabled{% endif %}>
            <i class="fas fa-shopping-cart"></i>
            <span>{% if product.stock > 0 %}Tambah ke Keranjang{% else %}Stok Habis{% endif %}</span>
        </button>
    </div>
</div>
{% endfor %}
"""

@api_bp.route('/products')
def filter_products():
    """
    Endpoint untuk pemfilteran produk secara asinkron.
    Mengembalikan HTML kartu produk yang sudah dirender.
    """
    # Kumpulkan parameter filter dari URL
    filters = {
        'search': request.args.get('search'),
        'category': request.args.get('category'),
        'sort': request.args.get('sort', 'popularity')
    }
    
    # Panggil service untuk mendapatkan produk yang sudah difilter
    products = product_service.get_filtered_products(filters)
    
    # Render HTML di sisi server dan kirimkan sebagai JSON
    html = render_template_string(PRODUCT_CARD_TEMPLATE, products=products)
    return jsonify({'html': html})