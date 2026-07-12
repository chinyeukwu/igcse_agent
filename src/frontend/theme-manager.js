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
        try {
            // Load saved theme preference or detect system preference
            let savedTheme = null;
            try {
                savedTheme = localStorage.getItem(this.STORAGE_KEY);
            } catch (e) {
                console.warn('localStorage access blocked:', e);
            }

            const systemDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
            const theme = savedTheme || (systemDark ? 'dark' : 'light');

            this.setTheme(theme);
        } catch (e) {
            console.warn('Theme init error:', e);
        }
    }

    setTheme(theme) {
        try {
            if (theme !== 'light' && theme !== 'dark') {
                theme = 'light';
            }

            // Apply theme to HTML element
            document.documentElement.setAttribute('data-theme', theme);

            try {
                localStorage.setItem(this.STORAGE_KEY, theme);
            } catch (e) {
                console.warn('Cannot save theme preference:', e);
            }

            // Update all theme toggle buttons
            this.updateToggleButtons(theme);
        } catch (e) {
            console.warn('setTheme error:', e);
        }
    }

    toggleTheme() {
        try {
            const currentTheme = document.documentElement.getAttribute('data-theme') || 'light';
            const newTheme = currentTheme === 'light' ? 'dark' : 'light';
            this.setTheme(newTheme);
        } catch (e) {
            console.warn('toggleTheme error:', e);
        }
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
try {
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => {
            try {
                window.themeManager = new ThemeManager();
            } catch (e) {
                console.warn('Theme manager initialization error:', e);
            }
        });
    } else {
        window.themeManager = new ThemeManager();
    }
} catch (e) {
    console.warn('Theme manager setup error:', e);
}
