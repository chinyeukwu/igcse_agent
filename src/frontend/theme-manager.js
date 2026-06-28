/**
 * Theme Manager: Handles dark/light mode toggle across all interfaces
 * Stores preference in localStorage and applies theme to html[data-theme]
 */

class ThemeManager {
    constructor() {
        this.STORAGE_KEY = 'agentic-tutor-theme';
        this.init();
    }

    init() {
        // Load saved theme preference or detect system preference
        const savedTheme = localStorage.getItem(this.STORAGE_KEY);
        const systemDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
        const theme = savedTheme || (systemDark ? 'dark' : 'light');

        this.setTheme(theme);
    }

    setTheme(theme) {
        if (theme !== 'light' && theme !== 'dark') {
            theme = 'light';
        }

        // Apply theme to HTML element
        document.documentElement.setAttribute('data-theme', theme);
        localStorage.setItem(this.STORAGE_KEY, theme);

        // Update all theme toggle buttons
        this.updateToggleButtons(theme);
    }

    toggleTheme() {
        const currentTheme = document.documentElement.getAttribute('data-theme') || 'light';
        const newTheme = currentTheme === 'light' ? 'dark' : 'light';
        this.setTheme(newTheme);
    }

    updateToggleButtons(theme) {
        const buttons = document.querySelectorAll('[data-toggle-theme]');
        buttons.forEach(btn => {
            btn.textContent = theme === 'light' ? '🌙' : '☀️';
            btn.setAttribute('aria-label', theme === 'light' ? 'Switch to dark mode' : 'Switch to light mode');
        });
    }

    getCurrentTheme() {
        return document.documentElement.getAttribute('data-theme') || 'light';
    }
}

// Initialize theme manager when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        window.themeManager = new ThemeManager();
    });
} else {
    window.themeManager = new ThemeManager();
}
