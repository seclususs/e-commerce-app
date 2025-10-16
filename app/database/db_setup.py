import sqlite3
import os
import json
from werkzeug.security import generate_password_hash

# KONFIGURASI
db_dir = os.path.dirname(__file__)
db_file = os.path.join(db_dir, 'database.db')

# HAPUS DATABASE LAMA
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
    
    # Tabel Kategori
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
            discount_price REAL, -- [DITAMBAHKAN] Kolom untuk harga diskon
            description TEXT NOT NULL,
            category_id INTEGER, -- [DIUBAH] Menggunakan ID Kategori
            sizes TEXT,
            colors TEXT,
            popularity INTEGER DEFAULT 0,
            image_url TEXT,
            additional_image_urls TEXT,
            stock INTEGER NOT NULL DEFAULT 10,
            FOREIGN KEY(category_id) REFERENCES categories(id) -- [DITAMBAHKAN] Foreign key
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
            tracking_number TEXT, -- [DITAMBAHKAN] Kolom untuk nomor resi
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
        ('about_title', 'Tentang HackThread'), 
        ('about_p1', 'HackThread adalah brand fashion untuk generasi digital yang menghargai kreativitas, inovasi, dan teknologi. Kami percaya bahwa fashion adalah ekspresi identitas, dan bagi para programmer, desainer, dan tech enthusiast, identitas itu terukir dalam baris-baris kode dan algoritma yang elegan.'),
        ('about_p2', 'Setiap desain di HackThread terinspirasi dari dunia digital—mulai dari lelucon "Hello, World!" yang ikonik, struktur data yang kompleks, hingga konsep-konsep AI yang futuristik. Kami menggabungkan estetika modern dengan sentuhan humor geek yang khas, menciptakan pakaian yang tidak hanya nyaman dipakai, tetapi juga memicu percakapan.'),
        ('about_p3', 'Kami berkomitmen untuk menggunakan bahan berkualitas tinggi dan proses produksi yang etis. Karena sama seperti menulis kode yang bersih, kami percaya dalam menciptakan produk yang solid dan tahan lama. Selamat datang di HackThread, di mana Anda bisa "Wear The Code".'),
        ('contact_email', 'kontak@hackthread.dev'), 
        ('contact_phone', '+62 812-3456-7890'),
        ('contact_location', 'Depok, Jawa Barat, Indonesia')
    ]
    cursor.executemany("INSERT INTO content (key, value) VALUES (?, ?)", initial_content)
    print("- Data 'content' berhasil dimasukkan.")

    # 2. Pengguna
    users_to_add = [
        ('admin', 'admin@hackthread.dev', generate_password_hash('admin123'), None, None, None, None, None, None, 1),
        ('user', 'user@example.com', generate_password_hash('password'), '081298765432', 'Jl. Merdeka No. 10', '', 'Depok', 'Jawa Barat', '16424', 0),
        ('johndoe', 'john@example.com', generate_password_hash('password123'), None, None, None, None, None, None, 0)
    ]
    cursor.executemany("""
        INSERT INTO users (username, email, password, phone, address_line_1, address_line_2, city, province, postal_code, is_admin) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, users_to_add)
    print("- Data 'users' (termasuk admin) berhasil dimasukkan.")

    # 3. Kategori
    categories_to_add = [('T-Shirt',), ('Hoodie',), ('Aksesoris',), ('Sweater',)]
    cursor.executemany("INSERT INTO categories (name) VALUES (?)", categories_to_add)
    print("- Data 'categories' berhasil dimasukkan.")

    # 4. Produk
    products_to_add = [
        # name, price, discount_price, description, category_id, sizes, colors, popularity, image_url, additional_images, stock
        ('Kaos "Hello, World!"', 175000, 150000, 'Kaos katun premium dengan sablon klasik "Hello, World!". Sempurna untuk memulai hari (atau proyek coding). Bahan adem dan nyaman.', 1, 'S, M, L, XL, XXL', 'Hitam, Putih, Biru Navy', 50, 'kaos_hello_world.webp', json.dumps(['kaos_hello_world_2.webp']), 100),
        ('Hoodie "Binary Tree"', 350000, None, 'Hoodie tebal dengan desain struktur data binary tree yang artistik. Jaga kehangatanmu saat begadang debugging. Fleece 280gsm.', 2, 'M, L, XL', 'Hitam, Abu-abu', 85, 'hoodie_binary.webp', json.dumps([]), 50),
        ('Topi "Git Commit"', 125000, None, 'Topi baseball dengan bordir command "git commit". Sebuah pengingat untuk selalu menyimpan progresmu.', 3, 'All Size', 'Hitam', 70, 'topi_git.webp', json.dumps(['topi_git_2.webp']), 75),
        ('Kaos "404 Not Found"', 185000, None, 'Humor programmer dalam selembar kaos. Ketika kamu merasa hilang, setidaknya gayamu tetap ditemukan. Bahan katun 24s.', 1, 'S, M, L, XL', 'Putih', 95, 'kaos_404.webp', json.dumps([]), 4),
        ('Sweater "Code, Sleep, Repeat"', 295000, 250000, 'Sweater ringan yang cocok untuk kerja di ruangan ber-AC. Slogan yang mewakili gaya hidup setiap developer.', 4, 'M, L, XL, XXL', 'Biru Navy', 80, 'sweater_code.webp', json.dumps(['sweater_code_2.webp']), 60),
        ('T-Shirt "SQL Injection"', 175000, None, 'Sebuah lelucon keamanan siber yang hanya dimengerti oleh kalangan tertentu. Tunjukkan keahlianmu dengan gaya.', 1, 'L, XL', 'Hitam', 60, 'kaos_sql.webp', json.dumps([]), 2),
        ('Mug "Syntax Error"', 95000, None, 'Mulai harimu dengan kopi dan pengingat bahwa semua orang bisa membuat kesalahan. Keramik berkualitas tinggi.', 3, 'N/A', 'Putih', 90, 'mug_syntax.webp', json.dumps([]), 120),
        ('Sticker Pack Developer', 50000, 45000, 'Satu set stiker vinyl tahan air berisi logo bahasa pemrograman dan teknologi populer. Tempel di laptopmu!', 3, 'N/A', 'Multi-warna', 100, 'sticker_pack.webp', json.dumps([]), 200)
    ]
    cursor.executemany("""
        INSERT INTO products (name, price, discount_price, description, category_id, sizes, colors, popularity, image_url, additional_image_urls, stock)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, products_to_add)
    print("- Data 'products' berhasil dimasukkan.")

    # 5. Pesanan
    orders_to_add = [
        (1, 2, '2025-09-10 14:30:00', 525000, 'Completed', 'Bank Transfer', 'user', '081298765432', 'Jl. Merdeka No. 10', '', 'Depok', 'Jawa Barat', '16424', 'JN10001'),
        (2, 2, '2025-10-01 11:00:00', 125000, 'Shipped', 'E-Wallet', 'user', '081298765432', 'Jl. Merdeka No. 10', '', 'Depok', 'Jawa Barat', '16424', 'SC10002'),
        (3, 3, '2025-10-14 20:00:00', 270000, 'Processing', 'COD', 'John Doe', '085611223344', 'Jl. Koding No. 42', '', 'Jakarta', 'DKI Jakarta', '12345', None)
    ]
    cursor.executemany("""
        INSERT INTO orders (id, user_id, order_date, total_amount, status, payment_method, shipping_name, shipping_phone, shipping_address_line_1, shipping_address_line_2, shipping_city, shipping_province, shipping_postal_code, tracking_number)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, orders_to_add)
    
    order_items_to_add = [
        (1, 1, 1, 1, 175000), (2, 1, 2, 1, 350000),
        (3, 2, 3, 1, 125000),
        (4, 3, 7, 1, 95000),  (5, 3, 1, 1, 175000)
    ]
    cursor.executemany("INSERT INTO order_items (id, order_id, product_id, quantity, price) VALUES (?, ?, ?, ?, ?)", order_items_to_add)
    print("- Data 'orders' dan 'order_items' berhasil dimasukkan.")

    # 6. Ulasan
    reviews_to_add = [
        (1, 2, 5, 'Bahan kaosnya adem banget, sablonnya juga rapi. Keren!', '2025-09-15 10:00:00'),
        (2, 2, 4, 'Hoodienya tebal dan hangat, pas buat ngoding malem. Desainnya juga subtle, suka!', '2025-09-16 12:00:00'),
        (1, 3, 5, 'Sama kayak user lain, kaosnya memang top!', '2025-10-20 18:00:00'),
        (7, 3, 5, 'Mugnya mantap, bikin error jadi keliatan estetik. Recommended.', '2025-10-21 09:00:00')
    ]
    cursor.executemany("INSERT INTO reviews (product_id, user_id, rating, comment, created_at) VALUES (?, ?, ?, ?, ?)", reviews_to_add)
    print("- Data 'reviews' berhasil dimasukkan.")

print("\nSetup database selesai.")
connection.close()