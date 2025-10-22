const applyTheme = (theme) => {
    const html = document.documentElement;
    if (theme === 'light') {
        html.classList.add('light-theme');
        html.classList.remove('dark-theme');
    } else {
        html.classList.remove('light-theme');
        html.classList.add('dark-theme');
    }
    window.dispatchEvent(new CustomEvent('themeChanged'));
};

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

    const toggleTheme = () => {
        const isLightTheme = document.documentElement.classList.contains('light-theme');
        const newTheme = isLightTheme ? 'dark' : 'light';
        localStorage.setItem('theme', newTheme);
        applyTheme(newTheme);
        updateToggleIcon(newTheme);
    };

    if (themeToggleBtn) {
        themeToggleBtn.addEventListener('click', toggleTheme);
    }
    if (adminThemeToggleBtn) {
        adminThemeToggleBtn.addEventListener('click', toggleTheme);
    }

    const currentTheme = document.documentElement.classList.contains('light-theme') ? 'light' : 'dark';
    updateToggleIcon(currentTheme);
}