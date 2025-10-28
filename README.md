```bash
e-commerce-app/
│
├── .env                      # Environment variables
├── .gitignore               # Git ignore rules
├── README.md                # Project documentation
├── requirements.txt         # Daftar dependensi (library) Python
├── run.py                   # Titik masuk (entry point)
│
├── app/                     # Folder utama yang berisi semua kode aplikasi
│   │
│   ├── __init__.py         # Titik masuk aplikasi, menggunakan pola factory (create_app)
│   │
│   ├── configs/            # Konfigurasi aplikasi
│   │   └── default_config.py
│   │
│   ├── core/               # Komponen inti
│   │   └── db.py
│   │
│   ├── exceptions/         # Penanganan error kustom dan global
│   │   ├── __init__.py
│   │   ├── api_exceptions.py
│   │   ├── database_exceptions.py
│   │   ├── error_handlers.py
│   │   ├── file_exceptions.py
│   │   ├── http_error_responses.py
│   │   └── service_exceptions.py
│   │
│   ├── routes/             # Mendefinisikan semua URL endpoint (Controllers)
│   │   ├── __init__.py
│   │   │
│   │   ├── admin/          # Rute untuk panel admin
│   │   │   ├── __init__.py
│   │   │   ├── category_routes.py
│   │   │   ├── dashboard_routes.py
│   │   │   ├── order_routes.py
│   │   │   ├── product_detail_routes.py
│   │   │   ├── product_list_routes.py
│   │   │   ├── report_routes.py
│   │   │   ├── setting_routes.py
│   │   │   ├── variant_routes.py
│   │   │   └── voucher_routes.py
│   │   │
│   │   ├── api/            # Rute untuk API
│   │   │   ├── __init__.py
│   │   │   ├── auth_routes.py
│   │   │   ├── cart_routes.py
│   │   │   ├── payment_routes.py
│   │   │   ├── product_routes.py
│   │   │   ├── scheduler_routes.py
│   │   │   └── voucher_routes.py
│   │   │
│   │   ├── auth/           # Rute untuk autentikasi
│   │   │   ├── __init__.py
│   │   │   ├── forgot_password_routes.py
│   │   │   ├── login_routes.py
│   │   │   ├── logout_routes.py
│   │   │   └── register_routes.py
│   │   │
│   │   ├── common/         # Rute umum
│   │   │   ├── __init__.py
│   │   │   └── image_routes.py
│   │   │
│   │   ├── product/        # Rute untuk halaman produk publik
│   │   │   ├── __init__.py
│   │   │   ├── catalog_routes.py
│   │   │   ├── detail_routes.py
│   │   │   └── general_routes.py
│   │   │
│   │   ├── purchase/       # Rute untuk alur pembelian
│   │   │   ├── __init__.py
│   │   │   ├── cart_routes.py
│   │   │   ├── checkout_routes.py
│   │   │   └── order_routes.py
│   │   │
│   │   └── user/           # Rute untuk halaman profil pengguna
│   │       ├── __init__.py
│   │       ├── order_routes.py
│   │       └── profile_routes.py
│   │
│   ├── services/           # Logika bisnis inti (Business Logic Layer)
│   │   ├── __init__.py
│   │   │
│   │   ├── auth/           # Logika untuk registrasi, login, reset password
│   │   │   ├── __init__.py
│   │   │   ├── authentication_service.py
│   │   │   ├── password_reset_service.py
│   │   │   └── registration_service.py
│   │   │
│   │   ├── orders/         # Logika untuk pesanan, keranjang, pembayaran
│   │   │   ├── __init__.py
│   │   │   ├── cart_service.py
│   │   │   ├── checkout_service.py
│   │   │   ├── checkout_validation_service.py
│   │   │   ├── discount_service.py
│   │   │   ├── order_cancel_service.py
│   │   │   ├── order_creation_service.py
│   │   │   ├── order_query_service.py
│   │   │   ├── order_service.py
│   │   │   ├── order_update_service.py
│   │   │   ├── payment_service.py
│   │   │   ├── stock_service.py
│   │   │   └── voucher_service.py
│   │   │
│   │   ├── products/       # Logika untuk produk, kategori, ulasan
│   │   │   ├── __init__.py
│   │   │   ├── category_service.py
│   │   │   ├── image_service.py
│   │   │   ├── product_bulk_service.py
│   │   │   ├── product_query_service.py
│   │   │   ├── product_repository_service.py
│   │   │   ├── product_service.py
│   │   │   ├── review_service.py
│   │   │   ├── variant_conversion_service.py
│   │   │   └── variant_service.py
│   │   │
│   │   ├── reports/        # Logika untuk membuat laporan
│   │   │   ├── __init__.py
│   │   │   ├── customer_report_service.py
│   │   │   ├── dashboard_report_service.py
│   │   │   ├── inventory_report_service.py
│   │   │   ├── product_report_service.py
│   │   │   ├── report_service.py
│   │   │   └── sales_report_service.py
│   │   │
│   │   ├── users/          # Logika untuk manajemen profil pengguna
│   │   │   ├── __init__.py
│   │   │   ├── user_address_service.py
│   │   │   ├── user_password_service.py
│   │   │   ├── user_profile_service.py
│   │   │   └── user_service.py
│   │   │
│   │   └── utils/          # Servis utilitas
│   │       ├── __init__.py
│   │       ├── scheduler_service.py
│   │       └── validation_service.py
│   │
│   ├── static/             # Aset statis (CSS, JS, Font, Gambar)
│   │   │
│   │   ├── css/            # Stylesheets
│   │   │   ├── all.min.css
│   │   │   ├── main.css
│   │   │   │
│   │   │   ├── admin/      # Styles untuk admin panel
│   │   │   │   ├── components/
│   │   │   │   │   ├── admin-components.css
│   │   │   │   │   └── admin-tables.css
│   │   │   │   ├── layout/
│   │   │   │   │   └── admin-layout.css
│   │   │   │   └── pages/
│   │   │   │       ├── dashboard.css
│   │   │   │       └── reports.css
│   │   │   │
│   │   │   ├── base/       # Base styles
│   │   │   │   ├── base.css
│   │   │   │   └── theme.css
│   │   │   │
│   │   │   ├── components/ # Component styles
│   │   │   │   ├── animations.css
│   │   │   │   ├── badges.css
│   │   │   │   ├── buttons.css
│   │   │   │   ├── cards.css
│   │   │   │   ├── forms.css
│   │   │   │   ├── modals.css
│   │   │   │   ├── product-card.css
│   │   │   │   └── tables.css
│   │   │   │
│   │   │   ├── layout/     # Layout styles
│   │   │   │   ├── footer.css
│   │   │   │   └── navbar.css
│   │   │   │
│   │   │   └── pages/      # Page-specific styles
│   │   │       ├── about.css
│   │   │       ├── auth.css
│   │   │       ├── cart.css
│   │   │       ├── checkout.css
│   │   │       ├── landing.css
│   │   │       ├── order-success.css
│   │   │       ├── order-tracking.css
│   │   │       ├── payment.css
│   │   │       ├── product-catalog.css
│   │   │       ├── product-detail.css
│   │   │       └── profile.css
│   │   │
│   │   ├── js/             # JavaScript files
│   │   │   ├── main.js
│   │   │   │
│   │   │   ├── admin/      # Admin panel scripts
│   │   │   │   ├── admin-main.js
│   │   │   │   ├── admin_ajax.js
│   │   │   │   │
│   │   │   │   ├── components/
│   │   │   │   │   ├── product-forms.component.js
│   │   │   │   │   ├── settings.component.js
│   │   │   │   │   └── sidebar-toggle.component.js
│   │   │   │   │
│   │   │   │   ├── charts/
│   │   │   │   │   ├── dashboard-charts.component.js
│   │   │   │   │   ├── low-stock-chart.component.js
│   │   │   │   │   ├── sales-chart.component.js
│   │   │   │   │   └── top-products-chart.component.js
│   │   │   │   │
│   │   │   │   ├── filters/
│   │   │   │   │   ├── dashboard-filter.component.js
│   │   │   │   │   ├── order-filter.component.js
│   │   │   │   │   └── product-filter.component.js
│   │   │   │   │
│   │   │   │   ├── services/
│   │   │   │   │   ├── ajax-forms.service.js
│   │   │   │   │   └── ajax-update-handlers.service.js
│   │   │   │   │
│   │   │   │   └── utils/
│   │   │   │       ├── chart.util.js
│   │   │   │       ├── cron-simulator.util.js
│   │   │   │       └── ui-handlers.util.js
│   │   │   │
│   │   │   ├── components/ # Reusable components
│   │   │   │   ├── confirm-modal.js
│   │   │   │   ├── image-gallery.js
│   │   │   │   ├── notification.js
│   │   │   │   └── product-card.js
│   │   │   │
│   │   │   ├── pages/      # Page-specific scripts
│   │   │   │   ├── cart.js
│   │   │   │   ├── checkout.js
│   │   │   │   ├── payment.js
│   │   │   │   ├── product-catalog.js
│   │   │   │   ├── product-detail.js
│   │   │   │   ├── profile.js
│   │   │   │   │
│   │   │   │   ├── auth/
│   │   │   │   │   ├── forgot-password.js
│   │   │   │   │   ├── login.js
│   │   │   │   │   └── register.js
│   │   │   │   │
│   │   │   │   └── product-detail/
│   │   │   │       ├── quantity-handler.js
│   │   │   │       ├── review-form.js
│   │   │   │       ├── size-selector.js
│   │   │   │       └── social-share.js
│   │   │   │
│   │   │   ├── services/   # Service layer
│   │   │   │   ├── auth.service.js
│   │   │   │   └── cart-api.service.js
│   │   │   │
│   │   │   ├── store/      # State management
│   │   │   │   └── cart-store.js
│   │   │   │
│   │   │   └── utils/      # Utility functions
│   │   │       ├── ajax-navigation.js
│   │   │       ├── animations.js
│   │   │       ├── confirmations.util.js
│   │   │       ├── flash-messages.js
│   │   │       ├── page-transitions.js
│   │   │       └── theme.js
│   │   │
│   │   └── webfonts/       # Font files (FontAwesome)
│   │       ├── fa-brands-400.woff2
│   │       ├── fa-regular-400.woff2
│   │       ├── fa-solid-900.woff2
│   │       └── fa-v4compatibility.woff2
│   │
│   ├── templates/          # File HTML (Jinja2)
│   │   │
│   │   ├── admin/          # Template untuk panel admin
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
│   │   │
│   │   ├── auth/           # Template untuk login, register, dll.
│   │   │   ├── forgot_password.html
│   │   │   ├── login.html
│   │   │   └── register.html
│   │   │
│   │   ├── layouts/        # Template layout dasar
│   │   │   ├── admin_layout.html
│   │   │   └── base_layout.html
│   │   │
│   │   ├── partials/       # Komponen HTML yang dapat digunakan kembali
│   │   │   │
│   │   │   ├── admin/      # Komponen HTML admin yang dapat digunakan kembali
│   │   │   │   ├── _category_row.html
│   │   │   │   ├── _category_table_body.html
│   │   │   │   ├── _dashboard.html
│   │   │   │   ├── _invoice.html
│   │   │   │   ├── _manage_categories.html
│   │   │   │   ├── _manage_orders.html
│   │   │   │   ├── _manage_products.html
│   │   │   │   ├── _manage_variants.html
│   │   │   │   ├── _manage_vouchers.html
│   │   │   │   ├── _order_table_body.html
│   │   │   │   ├── _product_editor.html
│   │   │   │   ├── _product_row.html
│   │   │   │   ├── _product_table_body.html
│   │   │   │   ├── _reports.html
│   │   │   │   ├── _site_settings.html
│   │   │   │   ├── _variant_row.html
│   │   │   │   ├── _variant_table_body.html
│   │   │   │   ├── _view_order.html
│   │   │   │   ├── _voucher_row.html
│   │   │   │   └── _voucher_table_body.html
│   │   │   │
│   │   │   ├── public/     # Komponen HTML publik
│   │   │   │   ├── _about.html
│   │   │   │   ├── _landing.html
│   │   │   │   ├── _product_card.html
│   │   │   │   ├── _product_catalog.html
│   │   │   │   ├── _product_detail.html
│   │   │   │   └── _review.html
│   │   │   │
│   │   │   ├── purchase/   # Komponen alur pembelian
│   │   │   │   ├── _cart.html
│   │   │   │   ├── _checkout_page.html
│   │   │   │   ├── _edit_address_page.html
│   │   │   │   ├── _payment_page.html
│   │   │   │   └── _success_page.html
│   │   │   │
│   │   │   └── user/       # Komponen profil pengguna
│   │   │       ├── _order_tracking.html
│   │   │       ├── _profile_editor.html
│   │   │       └── _user_profile.html
│   │   │
│   │   ├── public/         # Template halaman publik
│   │   │   ├── about.html
│   │   │   ├── landing_page.html
│   │   │   ├── product_catalog.html
│   │   │   └── product_detail.html
│   │   │
│   │   ├── purchase/       # Template alur pembelian
│   │   │   ├── cart.html
│   │   │   ├── checkout_page.html
│   │   │   ├── edit_address_page.html
│   │   │   ├── payment_page.html
│   │   │   └── success_page.html
│   │   │
│   │   └── user/           # Template profil pengguna
│   │       ├── order_tracking.html
│   │       ├── profile_editor.html
│   │       └── user_profile.html
│   │
│   └── utils/              # Fungsi helper
│       ├── __init__.py
│       ├── date_utils.py
│       ├── error_utils.py
│       ├── export_utils.py
│       ├── image_utils.py
│       ├── logging_utils.py
│       ├── route_decorators.py
│       └── template_filters.py
│
├── database/               # Skrip dan data terkait database
│   │
│   ├── images/            # Gambar produk yang diunggah
│   │   └── *.webp
│   │
│   └── seed/              # Skrip untuk mengisi data awal
│       ├── data.json      # Data dummy untuk di-load
│       ├── schema.sql     # Skema DDL
│       └── seed.py        # Skrip untuk menjalankan seeding
│
└── logs/                  # Folder untuk menyimpan file log
    └── *.log
```