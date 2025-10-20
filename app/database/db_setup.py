import sqlite3
import os
import json
from werkzeug.security import generate_password_hash

# KONFIGURASI
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
instance_dir = os.path.join(project_root, 'instance')
os.makedirs(instance_dir, exist_ok=True)  # Pastikan folder instance ada
db_file = os.path.join(instance_dir, 'database.db')

# HAPUS DATABASE LAMA JIKA ADA
if os.path.exists(db_file):
    os.remove(db_file)
    print(f"File database lama '{db_file}' berhasil dihapus.")

# BUAT KONEKSI BARU
connection = sqlite3.connect(db_file)
print(f"Database '{db_file}' berhasil dibuat.")

with connection:
    cursor = connection.cursor()

    # BUAT SKEMA TABEL
    print("\nMembuat skema tabel...")
    cursor.execute("""
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
    """)
    print("- Tabel 'users' berhasil dibuat.")
    
    cursor.execute("""
        CREATE TABLE categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE
        );
    """)
    print("- Tabel 'categories' berhasil dibuat.")

    cursor.execute("""
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
    """)
    print("- Tabel 'products' berhasil dibuat.")
    
    # Tabel baru untuk varian produk
    cursor.execute("""
        CREATE TABLE product_variants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            size TEXT NOT NULL,
            stock INTEGER NOT NULL,
            weight_grams INTEGER DEFAULT 0,
            sku TEXT UNIQUE,
            FOREIGN KEY(product_id) REFERENCES products(id) ON DELETE CASCADE
        );
    """)
    print("- Tabel 'product_variants' berhasil dibuat.")

    cursor.execute("CREATE TABLE content (key TEXT PRIMARY KEY, value TEXT NOT NULL);")
    print("- Tabel 'content' berhasil dibuat.")

    cursor.execute("""
        CREATE TABLE orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER,
            order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP, 
            subtotal REAL NOT NULL,
            discount_amount REAL DEFAULT 0,
            shipping_cost REAL DEFAULT 0,
            total_amount REAL NOT NULL,
            voucher_code TEXT,
            status TEXT NOT NULL CHECK(status IN ('Menunggu Pembayaran', 'Diproses', 'Dikirim', 'Selesai', 'Dibatalkan')),
            payment_method TEXT, 
            payment_transaction_id TEXT,
            shipping_name TEXT, shipping_phone TEXT,
            shipping_address_line_1 TEXT, shipping_address_line_2 TEXT,
            shipping_city TEXT, shipping_province TEXT, shipping_postal_code TEXT,
            tracking_number TEXT,
            FOREIGN KEY(user_id) REFERENCES users(id)
        );
    """)
    print("- Tabel 'orders' berhasil dibuat.")

    cursor.execute("""
        CREATE TABLE order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT, order_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL, 
            variant_id INTEGER,
            quantity INTEGER NOT NULL, 
            price REAL NOT NULL,
            size_at_order TEXT,
            FOREIGN KEY (order_id) REFERENCES orders (id),
            FOREIGN KEY (product_id) REFERENCES products (id),
            FOREIGN KEY (variant_id) REFERENCES product_variants(id)
        );
    """)
    print("- Tabel 'order_items' berhasil dibuat.")
   
    cursor.execute("""
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
    """)
    print("- Tabel 'reviews' berhasil dibuat.")

    cursor.execute("""
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
    """)
    print("- Tabel 'user_carts' berhasil dibuat.")

    cursor.execute("""
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
    """)
    print("- Tabel 'vouchers' berhasil dibuat.")

    cursor.execute("""
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
    """)
    print("- Tabel 'stock_holds' berhasil dibuat.")


    # MASUKKAN DATA AWAL (SEEDING)
    print("\nMemasukkan data awal...")
    
    initial_content = [
        ('app_name', 'HACKTHREAD'),
        ('short_description', 'Wear The Code'),
        ('about_title', 'Tentang HackThread'), 
        ('about_p1', 'HackThread adalah brand fashion untuk generasi digital yang menghargai kreativitas, inovasi, dan teknologi. Kami percaya bahwa fashion adalah ekspresi identitas, dan bagi para programmer, desainer, dan tech enthusiast, identitas itu terukir dalam baris-baris kode dan algoritma yang elegan.'),
        ('about_p2', 'Setiap desain di HackThread terinspirasi dari dunia digital—mulai dari lelucon "Hello, World!" yang ikonik, struktur data yang kompleks, hingga konsep-konsep AI yang futuristik. Kami menggabungkan estetika modern dengan sentuhan humor geek yang khas, menciptakan pakaian yang tidak hanya nyaman dipakai, tetapi juga memicu percakapan.'),
        ('about_p3', 'Kami berkomitmen untuk menggunakan bahan berkualitas tinggi dan proses produksi yang etis. Karena sama seperti menulis kode yang bersih, kami percaya dalam menciptakan produk yang solid dan tahan lama. Selamat datang di HackThread, di mana Anda bisa "Wear The Code".'),
        ('about_teaser_title', 'Filosofi Kami'),
        ('about_teaser_text', 'HackThread adalah brand fashion untuk generasi digital yang menghargai kreativitas, inovasi, dan teknologi. Kami percaya bahwa fashion adalah ekspresi identitas.'),
        ('contact_email', 'kontak@hackthread.dev'), 
        ('contact_phone', '+62 812-3456-7890'),
        ('contact_location', 'Depok, Jawa Barat, Indonesia'),
        ('social_links', '["https://github.com/seclususs"]')
    ]
    cursor.executemany("INSERT INTO content (key, value) VALUES (?, ?)", initial_content)
    print("- Data 'content' berhasil dimasukkan.")

    hashed_password = generate_password_hash('password123')
    users_to_add = [
        ('admin', 'admin@hackthread.dev', generate_password_hash('admin123'), None, None, None, None, None, None, 1)
    ]
    for i in range(1, 53):
        users_to_add.append(
            (f'user{i}', f'user{i}@example.com', hashed_password, None, None, None, None, None, None, 0)
        )
    
    cursor.executemany("""
        INSERT INTO users (username, email, password, phone, address_line_1, address_line_2, city, province, postal_code, is_admin) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, users_to_add)
    print(f"- Data untuk {len(users_to_add)} 'users' (termasuk admin) berhasil dimasukkan.")

    categories_to_add = [('T-Shirt',), ('Hoodie',), ('Aksesoris',), ('Sweater',)]
    cursor.executemany("INSERT INTO categories (name) VALUES (?)", categories_to_add)
    print("- Data 'categories' berhasil dimasukkan.")

    products_to_add = [
        ('Kaos "Hello, World!"', 175000, 150000, 'Kaos katun premium dengan sablon klasik "Hello, World!". Sempurna untuk memulai hari (atau proyek coding). Bahan adem dan nyaman.', 1, 'Hitam, Putih, Biru Navy', 55, 'kaos_hello_world.webp', json.dumps(['kaos_hello_world_2.webp']), 0, 1, 150, None),
        ('Hoodie "Binary Tree"', 350000, None, 'Hoodie tebal dengan desain struktur data binary tree yang artistik. Jaga kehangatanmu saat begadang debugging. Fleece 280gsm.', 2, 'Hitam, Abu-abu', 85, 'hoodie_binary.webp', json.dumps([]), 0, 1, 500, None),
        ('Topi "Git Commit"', 125000, None, 'Topi baseball dengan bordir command "git commit". Sebuah pengingat untuk selalu menyimpan progresmu.', 3, 'Hitam', 70, 'topi_git.webp', json.dumps(['topi_git_2.webp']), 75, 0, 100, 'TOPI-GIT-HITAM'),
        ('Sweater "Eat, Sleep, Code, Repeat"', 295000, 250000, 'Sweater ringan yang cocok untuk kerja di ruangan ber-AC. Slogan yang mewakili gaya hidup setiap developer.', 4, 'Biru Navy', 95, 'sweater_code.webp', json.dumps(['sweater_code_2.webp']), 60, 0, 400, 'SWTR-ESCR-NAVY')
    ]
    cursor.executemany("""
        INSERT INTO products (name, price, discount_price, description, category_id, colors, popularity, image_url, additional_image_urls, stock, has_variants, weight_grams, sku)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, products_to_add)
    print("- Data 'products' berhasil dimasukkan.")
    
    variants_to_add = [
        (1, 'S', 20, 150, 'KAOS-HW-S'), (1, 'M', 30, 160, 'KAOS-HW-M'), (1, 'L', 30, 170, 'KAOS-HW-L'), (1, 'XL', 20, 180, 'KAOS-HW-XL'),
        (2, 'M', 15, 500, 'HOOD-BIN-M'), (2, 'L', 20, 520, 'HOOD-BIN-L'), (2, 'XL', 15, 540, 'HOOD-BIN-XL')
    ]
    cursor.executemany("INSERT INTO product_variants (product_id, size, stock, weight_grams, sku) VALUES (?, ?, ?, ?, ?)", variants_to_add)
    print("- Data 'product_variants' berhasil dimasukkan.")
    
    # Update total stock for products with variants
    cursor.execute("UPDATE products SET stock = (SELECT SUM(stock) FROM product_variants WHERE product_id = 1) WHERE id = 1")
    cursor.execute("UPDATE products SET stock = (SELECT SUM(stock) FROM product_variants WHERE product_id = 2) WHERE id = 2")
    print("- Stok total produk bervarian berhasil dimasukkan.")

    # Seeding data orders
    orders_to_add = [
        (1, 2, '2024-09-10 14:30:00', 500000, 0, 15000, 515000, None, 'Selesai', 'Bank Transfer', 'TX1001', 'User 1', '081200000001', 'Jl. Dummy No. 1', '', 'Depok', 'Jawa Barat', '16424', 'JN10001'),
        (2, 3, '2024-10-01 11:00:00', 125000, 0, 10000, 135000, None, 'Dikirim', 'E-Wallet', 'TX1002', 'User 2', '081200000002', 'Jl. Dummy No. 2', '', 'Jakarta', 'DKI Jakarta', '10220', 'SC10002'),
        (3, 4, '2024-10-14 20:00:00', 400000, 0, 20000, 420000, None, 'Diproses', 'COD', None, 'User 3', '081200000003', 'Jl. Dummy No. 3', '', 'Bandung', 'Jawa Barat', '40111', None),
        (4, 15, '2024-10-15 09:00:00', 150000, 15000, 15000, 150000, 'HEMAT10', 'Selesai', 'E-Wallet', 'TX1003', 'User 14', '081200000014', 'Jl. Dummy No. 14', '', 'Surabaya', 'Jawa Timur', '60111', 'JN10002'),
        (5, 5, '2024-10-18 10:00:00', 175000, 0, 15000, 190000, None, 'Menunggu Pembayaran', 'Virtual Account', None, 'User 5', '081200000005', 'Jl. Dummy No. 5', '', 'Yogyakarta', 'DIY', '55222', None),
    ]
    cursor.executemany("""
        INSERT INTO orders (id, user_id, order_date, subtotal, discount_amount, shipping_cost, total_amount, voucher_code, status, payment_method, payment_transaction_id, shipping_name, shipping_phone, shipping_address_line_1, shipping_address_line_2, shipping_city, shipping_province, shipping_postal_code, tracking_number)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, orders_to_add)
    print("- Data 'orders' berhasil dimasukkan.")
    
    order_items_to_add = [
        (1, 1, 1, 2, 1, 150000, 'M'), (2, 1, 2, 6, 1, 350000, 'L'), 
        (3, 2, 3, None, 1, 125000, None),                     
        (4, 3, 4, None, 1, 250000, None), (5, 3, 1, 3, 1, 150000, 'L'), 
        (6, 4, 1, 1, 1, 150000, 'S'),
        (7, 5, 1, 4, 1, 175000, 'XL')
    ]
    cursor.executemany("INSERT INTO order_items (id, order_id, product_id, variant_id, quantity, price, size_at_order) VALUES (?, ?, ?, ?, ?, ?, ?)", order_items_to_add)
    print("- Data 'order_items' berhasil dimasukkan.")

    reviews_to_add = [
        (1, 2, 5, 'Bahan kaosnya adem banget, sablonnya juga rapi. Keren!', '2024-09-15 10:00:00'),
        (2, 2, 4, 'Hoodienya tebal dan hangat, pas buat ngoding malem. Desainnya juga subtle, suka!', '2024-09-16 12:00:00'),
        (3, 3, 5, 'Topinya keren, bordirannya rapi banget.', '2024-10-05 18:00:00'),
        (1, 15, 5, 'Sama kayak user lain, kaosnya memang top!', '2024-10-20 18:00:00')
    ]
    cursor.executemany("INSERT INTO reviews (product_id, user_id, rating, comment, created_at) VALUES (?, ?, ?, ?, ?)", reviews_to_add)
    print("- Data 'reviews' berhasil dimasukkan.")
    
    vouchers_to_add = [
        ('HEMAT10', 'PERCENTAGE', 10, 100, 1, None, None, 50000, 1),
        ('POTONGAN50K', 'FIXED_AMOUNT', 50000, 50, 0, None, None, 250000, 1),
        ('KADALUWARSA', 'FIXED_AMOUNT', 100000, 10, 0, '2023-01-01', '2023-12-31', 0, 1)
    ]
    cursor.executemany("INSERT INTO vouchers (code, type, value, max_uses, use_count, start_date, end_date, min_purchase_amount, is_active) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", vouchers_to_add)
    print("- Data 'vouchers' berhasil dimasukkan.")

print("\nSetup database selesai.")
connection.close()