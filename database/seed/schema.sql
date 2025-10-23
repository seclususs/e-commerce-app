CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    email TEXT NOT NULL UNIQUE,
    password TEXT NOT NULL,
    phone TEXT,
    address_line_1 TEXT,
    address_line_2 TEXT,
    city TEXT,
    province TEXT,
    postal_code TEXT,
    is_admin BOOLEAN NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    price REAL NOT NULL,
    discount_price REAL,
    description TEXT NOT NULL,
    category_id INTEGER,
    colors TEXT,
    popularity INTEGER DEFAULT 0,
    image_url TEXT,
    additional_image_urls TEXT,
    stock INTEGER NOT NULL DEFAULT 10,
    has_variants BOOLEAN DEFAULT 0,
    weight_grams INTEGER DEFAULT 0,
    sku TEXT UNIQUE,
    FOREIGN KEY(category_id) REFERENCES categories(id)
);

CREATE TABLE product_variants (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL,
    size TEXT NOT NULL,
    stock INTEGER NOT NULL,
    weight_grams INTEGER DEFAULT 0,
    sku TEXT UNIQUE,
    FOREIGN KEY(product_id) REFERENCES products(id) ON DELETE CASCADE
);

CREATE TABLE content (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    subtotal REAL NOT NULL,
    discount_amount REAL DEFAULT 0,
    shipping_cost REAL DEFAULT 0,
    total_amount REAL NOT NULL,
    voucher_code TEXT,
    status TEXT NOT NULL CHECK(status IN ('Menunggu Pembayaran', 'Diproses', 'Dikirim', 'Selesai', 'Dibatalkan', 'Pesanan Dibuat')),
    payment_method TEXT,
    payment_transaction_id TEXT,
    shipping_name TEXT,
    shipping_phone TEXT,
    shipping_address_line_1 TEXT,
    shipping_address_line_2 TEXT,
    shipping_city TEXT,
    shipping_province TEXT,
    shipping_postal_code TEXT,
    tracking_number TEXT,
    FOREIGN KEY(user_id) REFERENCES users(id)
);

CREATE TABLE order_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    variant_id INTEGER,
    quantity INTEGER NOT NULL,
    price REAL NOT NULL,
    size_at_order TEXT,
    FOREIGN KEY (order_id) REFERENCES orders (id),
    FOREIGN KEY (product_id) REFERENCES products (id),
    FOREIGN KEY (variant_id) REFERENCES product_variants(id)
);

CREATE TABLE order_status_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL,
    status TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    notes TEXT,
    FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE
);

CREATE TABLE reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    rating INTEGER NOT NULL CHECK(rating >= 1 AND rating <= 5),
    comment TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (product_id) REFERENCES products(id),
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE user_carts (
    user_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    variant_id INTEGER,
    quantity INTEGER NOT NULL,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, product_id, variant_id),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE,
    FOREIGN KEY (variant_id) REFERENCES product_variants(id) ON DELETE CASCADE
);

CREATE TABLE vouchers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL UNIQUE,
    type TEXT NOT NULL CHECK(type IN ('PERCENTAGE', 'FIXED_AMOUNT')),
    value REAL NOT NULL,
    max_uses INTEGER,
    use_count INTEGER DEFAULT 0,
    start_date TIMESTAMP,
    end_date TIMESTAMP,
    min_purchase_amount REAL DEFAULT 0,
    is_active BOOLEAN DEFAULT 1
);

CREATE TABLE stock_holds (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    session_id TEXT,
    product_id INTEGER NOT NULL,
    variant_id INTEGER,
    quantity INTEGER NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE,
    FOREIGN KEY (variant_id) REFERENCES product_variants(id) ON DELETE CASCADE
);