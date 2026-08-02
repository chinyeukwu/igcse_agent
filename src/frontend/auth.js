/**
 * Shared authentication helper for the Agentic AI Tutor frontend.
 *
 * Standardizes token storage (single key: `authToken`), attaches the
 * Authorization header to API calls, and redirects to /login on 401 or when
 * no session is present. Include on every page that talks to protected APIs:
 *
 *   <script src="/static/auth.js"></script>
 */
const AUTH = {
    TOKEN_KEY: 'authToken',
    USER_KEY: 'authUser',

    /** Return the stored bearer token (empty string if none). */
    getToken() {
        return localStorage.getItem(this.TOKEN_KEY) || '';
    },

    /** Return the stored user object, or null. */
    getUser() {
        try {
            return JSON.parse(localStorage.getItem(this.USER_KEY) || 'null');
        } catch (e) {
            return null;
        }
    },

    /** Persist a session after login. */
    setSession(token, user) {
        if (token) localStorage.setItem(this.TOKEN_KEY, token);
        if (user) localStorage.setItem(this.USER_KEY, JSON.stringify(user));
    },

    /** Clear the stored session. */
    clear() {
        localStorage.removeItem(this.TOKEN_KEY);
        localStorage.removeItem(this.USER_KEY);
    },

    /** True if a token is present. */
    isAuthenticated() {
        return this.getToken().length > 0;
    },

    /**
     * Redirect to /login if there is no session. Call at the top of a
     * protected page's script. Returns true when authenticated.
     */
    requireAuth() {
        if (!this.isAuthenticated()) {
            window.location.href = '/login';
            return false;
        }
        return true;
    },

    /**
     * fetch() wrapper that adds the Authorization header and handles expired
     * sessions by clearing state and redirecting to /login on 401.
     */
    async authFetch(url, options = {}) {
        const headers = Object.assign({}, options.headers || {}, {
            'Authorization': `Bearer ${this.getToken()}`,
        });
        const resp = await fetch(url, Object.assign({}, options, { headers }));
        if (resp.status === 401) {
            this.clear();
            window.location.href = '/login';
        }
        return resp;
    },

    /** Invalidate the session server-side, clear local state, go to /login. */
    async logout() {
        try {
            await this.authFetch('/auth/logout', { method: 'POST' });
        } catch (e) {
            /* ignore network errors on logout */
        }
        this.clear();
        window.location.href = '/login';
    },
};
