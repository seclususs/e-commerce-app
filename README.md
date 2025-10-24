```bash
e-commerce-app/
├── app/
│   ├── configs/
│   │   └── default_config.py         # Konfigurasi aplikasi (variabel lingkungan)
│
│   ├── core/
│   │   ├── __init__.py               
│   │   └── db.py                     # Inisialisasi & koneksi database MySQL
│
│   ├── exceptions/                   # Modul penanganan error & exception
│   │   ├── __init__.py
│   │   ├── error_handlers.py          # Handler global Flask untuk error (404, 500, dsb.)
│   │   ├── api_exceptions.py          # Kelas error khusus API (ValidationError, AuthError)
│   │   ├── service_exceptions.py      # Error bisnis (OutOfStockError, PaymentFailedError)
│   │   ├── database_exceptions.py     # Error koneksi atau query database
│   │   ├── file_exceptions.py         # Error terkait file/gambar/upload
│   │   └── http_error_responses.py    # Response standar untuk error JSON (format & template)
│
│   ├── routes/
│   │   ├── __init__.py               
│   │   ├── admin/                    # Rute panel admin
│   │   │   ├── __init__.py
│   │   │   ├── category_routes.py    # CRUD Kategori
│   │   │   ├── dashboard_routes.py   # Dashboard & Scheduler
│   │   │   ├── order_routes.py       # Detail & Update Pesanan
│   │   │   ├── product_routes.py     # CRUD Produk, Filter, Bulk Action
│   │   │   ├── report_routes.py      # Ekspor & Tampilan Laporan
│   │   │   ├── setting_routes.py     # Pengaturan Konten Website
│   │   │   ├── variant_routes.py     # CRUD Varian Produk
│   │   │   └── voucher_routes.py     # CRUD Voucher Diskon
│   │   ├── api/                      # Rute API untuk frontend (AJAX)
│   │   │   ├── __init__.py
│   │   │   ├── auth_routes.py        # Validasi Username/Email
│   │   │   ├── cart_routes.py        # Ambil/Tambah/Update Keranjang
│   │   │   ├── payment_routes.py     # Webhook Pembayaran & Cron Job
│   │   │   ├── product_routes.py     # Filter Produk (Catalog Page)
│   │   │   └── voucher_routes.py     # Terapkan Voucher
│   │   ├── auth/                     # Rute Otentikasi
│   │   │   ├── __init__.py
│   │   │   ├── forgot_password_routes.py
│   │   │   ├── login_routes.py
│   │   │   ├── logout_routes.py
│   │   │   └── register_routes.py
│   │   ├── common/                   # Rute umum
│   │   │   ├── __init__.py
│   │   │   └── image_routes.py       # Menyajikan file gambar
│   │   ├── product/                  # Rute produk publik
│   │   │   ├── __init__.py
│   │   │   ├── catalog_routes.py     # Halaman katalog
│   │   │   ├── detail_routes.py      # Detail produk & submit ulasan
│   │   │   └── general_routes.py     # Beranda & Tentang Kami
│   │   ├── purchase/                 # Rute pembelian (Cart & Checkout)
│   │   │   ├── __init__.py
│   │   │   ├── checkout_routes.py    # Checkout & Edit Alamat
│   │   │   └── order_routes.py       # Pembayaran & Halaman Sukses
│   │   └── user/                     # Rute profil pengguna
│   │       ├── __init__.py
│   │       └── profile_routes.py     # Profil, Edit Profil, Lacak Pesanan
│
│   ├── services/
│   │   ├── orders/
│   │   │   ├── cart_service.py       # Logika keranjang (DB & Local merge)
│   │   │   ├── order_service.py      # Pembuatan/Pembatalan pesanan
│   │   │   ├── payment_service.py    # Pemrosesan pembayaran sukses
│   │   │   ├── stock_service.py      # Manajemen & penahanan stok
│   │   │   └── voucher_service.py    # Validasi voucher
│   │   ├── products/
│   │   │   ├── category_service.py   # CRUD kategori
│   │   │   ├── product_bulk_service.py  # Aksi massal produk
│   │   │   ├── product_query_service.py # Pengambilan data produk (filter & relasi)
│   │   │   ├── product_service.py    # CRUD produk utama & gambar
│   │   │   ├── review_service.py     # CRUD ulasan
│   │   │   └── variant_service.py    # CRUD varian produk
│   │   ├── reports/
│   │   │   ├── customer_report_service.py  # Laporan pelanggan & cart analytics
│   │   │   ├── inventory_report_service.py # Laporan inventaris
│   │   │   ├── product_report_service.py   # Laporan produk (terlaris, dilihat)
│   │   │   ├── report_service.py           # Koordinator laporan dashboard
│   │   │   └── sales_report_service.py     # Laporan penjualan (revenue, voucher)
│   │   └── utils/
│   │       └── scheduler_service.py  # Cron job (pembatalan pesanan kedaluwarsa)
│
│   ├── static/                       # Aset statis (CSS, JS, font)
│   │   ├── css/
│   │   │   ├── admin/
│   │   │   │   ├── components/
│   │   │   │   │   ├── admin-components.css
│   │   │   │   │   └── admin-tables.css
│   │   │   │   ├── layout/
│   │   │   │   │   └── admin-layout.css
│   │   │   │   └── pages/
│   │   │   │       ├── dashboard.css
│   │   │   │       └── reports.css
│   │   │   ├── base/
│   │   │   │   ├── base.css
│   │   │   │   └── theme.css
│   │   │   ├── components/
│   │   │   │   ├── animations.css
│   │   │   │   ├── badges.css
│   │   │   │   ├── buttons.css
│   │   │   │   ├── cards.css
│   │   │   │   ├── forms.css
│   │   │   │   ├── modals.css
│   │   │   │   ├── product-card.css
│   │   │   │   └── tables.css
│   │   │   ├── layout/
│   │   │   │   ├── footer.css
│   │   │   │   └── navbar.css
│   │   │   ├── pages/
│   │   │   │   ├── about.css
│   │   │   │   ├── auth.css
│   │   │   │   ├── cart.css
│   │   │   │   ├── checkout.css
│   │   │   │   ├── landing.css
│   │   │   │   ├── order-success.css
│   │   │   │   ├── order-tracking.css
│   │   │   │   ├── payment.css
│   │   │   │   ├── product-catalog.css
│   │   │   │   ├── product-detail.css
│   │   │   │   └── profile.css
│   │   │   └── all.min.css          # FontAwesome CSS
│   │   ├── js/
│   │   │   ├── admin/
│   │   │   │   ├── charts/
│   │   │   │   │   ├── chart-utils.js
│   │   │   │   │   ├── dashboard-charts.js
│   │   │   │   │   ├── low-stock-chart.js
│   │   │   │   │   ├── sales-chart.js
│   │   │   │   │   └── top-products-chart.js
│   │   │   │   ├── filters/
│   │   │   │   │   ├── dashboard-filter.js
│   │   │   │   │   ├── order-filter.js
│   │   │   │   │   └── product-filter.js
│   │   │   │   ├── modules/
│   │   │   │   │   ├── product-forms.js
│   │   │   │   │   ├── settings.js
│   │   │   │   │   └── ui-handlers.js
│   │   │   │   ├── utils/
│   │   │   │   │   └── cron-simulator.js
│   │   │   │   ├── admin-main.js        # Entry point JS admin
│   │   │   │   ├── ajax-forms.js        # Universal AJAX form handler
│   │   │   │   └── ajax-update-handlers.js # Update UI setelah AJAX
│   │   │   ├── components/
│   │   │   │   ├── image-gallery.js     # Slider & Thumbnail Produk
│   │   │   │   └── product-card.js      # Tombol Add to Cart
│   │   │   ├── pages/
│   │   │   │   ├── auth/
│   │   │   │   │   ├── forgot-password.js
│   │   │   │   │   ├── login.js
│   │   │   │   │   └── register.js
│   │   │   │   ├── product-detail/
│   │   │   │   │   ├── quantity-handler.js
│   │   │   │   │   ├── review-form.js
│   │   │   │   │   ├── size-selector.js
│   │   │   │   │   └── social-share.js
│   │   │   │   ├── cart.js
│   │   │   │   ├── checkout.js
│   │   │   │   ├── payment.js
│   │   │   │   ├── product-catalog.js
│   │   │   │   └── profile.js
│   │   │   ├── services/
│   │   │   │   └── cart-api.js          # Wrapper API untuk Cart
│   │   │   ├── shared/
│   │   │   │   ├── auth.js              # Logout & hapus cart lokal
│   │   │   │   └── confirmations.js     # Modal konfirmasi
│   │   │   ├── state/
│   │   │   │   └── cart-store.js        # State management keranjang
│   │   │   ├── utils/
│   │   │   │   ├── animations.js
│   │   │   │   ├── page-transitions.js
│   │   │   │   ├── theme.js             # Logika dark/light mode
│   │   │   │   └── ui.js                # Notifikasi & modals
│   │   │   └── main.js                  # Entry point JS publik
│   │   └── webfonts/                    # Font Awesome (woff2 files)
│   │       ├── fa-brands-400.woff2
│   │       ├── fa-regular-400.woff2
│   │       ├── fa-solid-900.woff2
│   │       └── fa-v4compatibility.woff2
│
│   ├── templates/
│   │   ├── admin/
│   │   │   ├── partials/                # Partial tabel admin (AJAX update)
│   │   │   │   ├── _category_row.html
│   │   │   │   ├── _category_table_body.html
│   │   │   │   ├── _order_table_body.html
│   │   │   │   ├── _product_row.html
│   │   │   │   ├── _product_table_body.html
│   │   │   │   ├── _variant_row.html
│   │   │   │   ├── _variant_table_body.html
│   │   │   │   ├── _voucher_row.html
│   │   │   │   └── _voucher_table_body.html
│   │   │   ├── dashboard.html
│   │   │   ├── invoice.html
│   │   │   ├── manage_categories.html
│   │   │   ├── manage_orders.html
│   │   │   ├── manage_products.html
│   │   │   ├── manage_variants.html
│   │   │   ├── manage_vouchers.html
│   │   │   ├── product_editor.html
│   │   │   ├── reports.html
│   │   │   ├── site_settings.html
│   │   │   └── view_order.html
│   │   ├── auth/
│   │   │   ├── forgot_password.html
│   │   │   ├── login.html
│   │   │   └── register.html
│   │   ├── layouts/
│   │   │   ├── admin_layout.html
│   │   │   └── base_layout.html
│   │   ├── partials/                   # Partial publik
│   │   │   ├── _product_card.html
│   │   │   └── _review.html
│   │   ├── public/
│   │   │   ├── about.html
│   │   │   ├── landing_page.html
│   │   │   ├── product_catalog.html
│   │   │   └── product_detail.html
│   │   ├── purchase/
│   │   │   ├── cart.html
│   │   │   ├── checkout_page.html
│   │   │   ├── edit_address_page.html
│   │   │   ├── payment_page.html
│   │   │   └── success_page.html
│   │   └── user/
│   │       ├── order_tracking.html
│   │       ├── profile_editor.html
│   │       └── user_profile.html
│
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── date_utils.py              # Utilitas tanggal untuk laporan
│   │   ├── export_utils.py            # Utilitas ekspor CSV
│   │   ├── image_utils.py             # Pemrosesan gambar
│   │   ├── logging_utils.py           # Konfigurasi logging
│   │   ├── route_decorators.py        # Decorator @login_required / @admin_required
│   │   ├── template_filters.py        # Filter Jinja2 (rupiah, tojson_safe, dll)
│   │   └── error_utils.py             # Utilitas umum error logging & format traceback
│
│   └── __init__.py                    # Pabrik aplikasi Flask (create_app)
│
├── database/
│   ├── images/                        # Folder gambar produk
│   └── seed/
│       ├── data.json                  # Data awal seeding
│       ├── schema.sql                 # Skema database MySQL
│       └── seed.py                    # Skrip isi ulang database
│
├── .env                               # Variabel lingkungan (DB, Secret Key)
├── .gitignore                         # File/folder diabaikan Git
├── requirements.txt                   # Dependensi Python
└── run.py                             # Entry point Flask
```