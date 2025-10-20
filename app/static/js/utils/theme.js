/**
 * Mengelola logika untuk peralihan tema (terang/gelap).
 * - Menerapkan tema awal berdasarkan localStorage atau preferensi sistem.
 * - Menangani klik pada tombol untuk mengubah tema.
 * - Menyimpan preferensi pengguna di localStorage.
 */

// Menerapkan kelas tema ke elemen <html>
const applyTheme = (theme) => {
    const html = document.documentElement;
    if (theme === 'light') {
        html.classList.add('light-theme');
        html.classList.remove('dark-theme');
    } else {
        html.classList.remove('light-theme');
        html.classList.add('dark-theme');
    }
    // Mengirim event kustom agar skrip lain (seperti chart) dapat bereaksi
    window.dispatchEvent(new CustomEvent('themeChanged'));
};

// Memperbarui ikon pada tombol pengalih tema
const updateToggleIcon = (theme) => {
    const sunIcon = document.getElementById('theme-toggle-sun');
    const moonIcon = document.getElementById('theme-toggle-moon');
    if (!sunIcon || !moonIcon) return;

    if (theme === 'light') {
        sunIcon.style.display = 'none';
        moonIcon.style.display = 'block';
    } else {
        sunIcon.style.display = 'block';
        moonIcon.style.display = 'none';
    }
};

export function initThemeSwitcher() {
    const themeToggleBtn = document.getElementById('themeToggle');
    const adminThemeToggleBtn = document.getElementById('adminThemeToggle');

    // Fungsi yang dijalankan saat tombol diklik
    const toggleTheme = () => {
        const isLightTheme = document.documentElement.classList.contains('light-theme');
        const newTheme = isLightTheme ? 'dark' : 'light';
        localStorage.setItem('theme', newTheme);
        applyTheme(newTheme);
        updateToggleIcon(newTheme);
    };

    // Menambahkan event listener ke tombol yang ada
    if (themeToggleBtn) {
        themeToggleBtn.addEventListener('click', toggleTheme);
    }
    if (adminThemeToggleBtn) {
        adminThemeToggleBtn.addEventListener('click', toggleTheme);
    }

    // Mengatur status ikon saat halaman dimuat (setelah skrip <head> berjalan)
    const currentTheme = document.documentElement.classList.contains('light-theme') ? 'light' : 'dark';
    updateToggleIcon(currentTheme);
}