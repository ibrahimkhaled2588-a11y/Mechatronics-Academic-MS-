const apiUrl = window.location.origin || '';

function nextUrl() {
    const params = new URLSearchParams(window.location.search);
    return params.get('next') || 'indicators-tracker.html';
}

document.getElementById('login-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const username = document.getElementById('login-username').value.trim();
    const password = document.getElementById('login-password').value;
    const errorEl = document.getElementById('login-error');
    errorEl.hidden = true;

    try {
        const res = await fetch(`${apiUrl}/api/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password }),
        });
        if (!res.ok) {
            const detail = await res.json().catch(() => ({}));
            throw new Error(detail.detail || 'Sign in failed.');
        }
        window.location.href = nextUrl();
    } catch (err) {
        errorEl.textContent = err.message;
        errorEl.hidden = false;
    }
});

// If already signed in, skip straight past the login form.
(async () => {
    try {
        const res = await fetch(`${apiUrl}/api/auth/me`);
        if (res.ok) window.location.href = nextUrl();
    } catch (err) {
        // not signed in; stay on the login page
    }
})();
