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
            sizes TEXT,
            colors TEXT,
            popularity INTEGER DEFAULT 0,
            image_url TEXT,
            additional_image_urls TEXT,
            stock INTEGER NOT NULL DEFAULT 10,
            FOREIGN KEY(category_id) REFERENCES categories(id)
        );
    """)
    print("- Tabel 'products' berhasil dibuat.")
    
    cursor.execute("CREATE TABLE content (key TEXT PRIMARY KEY, value TEXT NOT NULL);")
    print("- Tabel 'content' berhasil dibuat.")

    cursor.execute("""
        CREATE TABLE orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER,
            order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP, total_amount REAL NOT NULL,
            status TEXT NOT NULL CHECK(status IN ('Pending', 'Processing', 'Shipped', 'Completed', 'Cancelled')),
            payment_method TEXT, shipping_name TEXT, shipping_phone TEXT,
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
            product_id INTEGER NOT NULL, quantity INTEGER NOT NULL, price REAL NOT NULL,
            FOREIGN KEY (order_id) REFERENCES orders (id),
            FOREIGN KEY (product_id) REFERENCES products (id)
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

    # MASUKKAN DATA AWAL (SEEDING)
    print("\nMemasukkan data awal...")
    
    # 1. Konten Website
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
        ('contact_location', 'Depok, Jawa Barat, Indonesia')
    ]
    cursor.executemany("INSERT INTO content (key, value) VALUES (?, ?)", initial_content)
    print("- Data 'content' berhasil dimasukkan.")

    # 2. Pengguna
    hashed_password = generate_password_hash('password123')
    users_to_add = [
        ('admin', 'admin@hackthread.dev', generate_password_hash('admin123'), None, None, None, None, None, None, 1)
    ]
    # Tambah 52 pengguna dummy
    for i in range(1, 53):
        users_to_add.append(
            (f'user{i}', f'user{i}@example.com', hashed_password, None, None, None, None, None, None, 0)
        )
    
    cursor.executemany("""
        INSERT INTO users (username, email, password, phone, address_line_1, address_line_2, city, province, postal_code, is_admin) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, users_to_add)
    print(f"- Data untuk {len(users_to_add)} 'users' (termasuk admin) berhasil dimasukkan.")

    # 3. Kategori
    categories_to_add = [('T-Shirt',), ('Hoodie',), ('Aksesoris',), ('Sweater',)]
    cursor.executemany("INSERT INTO categories (name) VALUES (?)", categories_to_add)
    print("- Data 'categories' berhasil dimasukkan.")

    # 4. Produk
    products_to_add = [
        # name, price, discount_price, description, category_id, sizes, colors, popularity, image_url, additional_images, stock
        ('Kaos', 175000, 150000, 'Kaos katun premium dengan sablon klasik "Hello, World!". Sempurna untuk memulai hari (atau proyek coding). Bahan adem dan nyaman.', 1, 'S, M, L, XL, XXL', 'Hitam, Putih, Biru Navy', 55, 'kaos_hello_world.webp', json.dumps(['kaos_hello_world_2.webp']), 100),
        ('Hoodie', 350000, None, 'Hoodie tebal dengan desain struktur data binary tree yang artistik. Jaga kehangatanmu saat begadang debugging. Fleece 280gsm.', 2, 'M, L, XL', 'Hitam, Abu-abu', 85, 'hoodie_binary.webp', json.dumps([]), 50),
        ('Topi', 125000, None, 'Topi baseball dengan bordir command "git commit". Sebuah pengingat untuk selalu menyimpan progresmu.', 3, 'All Size', 'Hitam', 70, 'topi_git.webp', json.dumps(['topi_git_2.webp']), 75),
        ('Sweater', 295000, 250000, 'Sweater ringan yang cocok untuk kerja di ruangan ber-AC. Slogan yang mewakili gaya hidup setiap developer.', 4, 'M, L, XL, XXL', 'Biru Navy', 95, 'sweater_code.webp', json.dumps(['sweater_code_2.webp']), 60)
    ]
    cursor.executemany("""
        INSERT INTO products (name, price, discount_price, description, category_id, sizes, colors, popularity, image_url, additional_image_urls, stock)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, products_to_add)
    print("- Data 'products' berhasil dimasukkan.")

    # 5. Pesanan
    orders_to_add = [
        (1, 2, '2025-09-10 14:30:00', 500000, 'Completed', 'Bank Transfer', 'User 1', '081200000001', 'Jl. Dummy No. 1', '', 'Depok', 'Jawa Barat', '16424', 'JN10001'),
        (2, 3, '2025-10-01 11:00:00', 125000, 'Shipped', 'E-Wallet', 'User 2', '081200000002', 'Jl. Dummy No. 2', '', 'Jakarta', 'DKI Jakarta', '10220', 'SC10002'),
        (3, 4, '2025-10-14 20:00:00', 400000, 'Processing', 'COD', 'User 3', '081200000003', 'Jl. Dummy No. 3', '', 'Bandung', 'Jawa Barat', '40111', None),
        (4, 15, '2025-10-15 09:00:00', 150000, 'Completed', 'E-Wallet', 'User 14', '081200000014', 'Jl. Dummy No. 14', '', 'Surabaya', 'Jawa Timur', '60111', 'JN10002')
    ]
    cursor.executemany("""
        INSERT INTO orders (id, user_id, order_date, total_amount, status, payment_method, shipping_name, shipping_phone, shipping_address_line_1, shipping_address_line_2, shipping_city, shipping_province, shipping_postal_code, tracking_number)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, orders_to_add)
    
    order_items_to_add = [
        (1, 1, 1, 1, 150000), (2, 1, 2, 1, 350000), # Order 1 by User 1 (id 2)
        (3, 2, 3, 1, 125000),                     # Order 2 by User 2 (id 3)
        (4, 3, 4, 1, 250000), (5, 3, 1, 1, 150000), # Order 3 by User 3 (id 4)
        (6, 4, 1, 1, 150000)                      # Order 4 by User 14 (id 15)
    ]
    cursor.executemany("INSERT INTO order_items (id, order_id, product_id, quantity, price) VALUES (?, ?, ?, ?, ?)", order_items_to_add)
    print("- Data 'orders' dan 'order_items' berhasil dimasukkan.")

    # 6. Ulasan
    reviews_to_add = [
        (1, 2, 5, 'Bahan kaosnya adem banget, sablonnya juga rapi. Keren!', '2025-09-15 10:00:00'),
        (2, 2, 4, 'Hoodienya tebal dan hangat, pas buat ngoding malem. Desainnya juga subtle, suka!', '2025-09-16 12:00:00'),
        (3, 3, 5, 'Topinya keren, bordirannya rapi banget.', '2025-10-05 18:00:00'),
        (1, 15, 5, 'Sama kayak user lain, kaosnya memang top!', '2025-10-20 18:00:00')
    ]
    cursor.executemany("INSERT INTO reviews (product_id, user_id, rating, comment, created_at) VALUES (?, ?, ?, ?, ?)", reviews_to_add)
    print("- Data 'reviews' berhasil dimasukkan.")

print("\nSetup database selesai.")
connection.close()