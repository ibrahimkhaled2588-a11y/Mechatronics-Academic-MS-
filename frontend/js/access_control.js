/**
 * Shared access-control rules, used by both page_guard.js (the pages that
 * only enforce access) and indicators_tracker.js (which handles its own
 * auth flow directly). Kept in one file so the redirect rules and the
 * nav-bar visibility always agree with each other.
 */

// Pages every signed-in member can reach, regardless of their standard.
const MEMBER_ALLOWED_PAGES = new Set([
    'index.html', '', 'dashboard.html', 'course-report.html',
    'program-report.html', 'survey-dashboard.html', 'qa-chat.html',
    'indicators-tracker.html', 'curriculum-mapping.html',
]);

// Standard-specific pages, keyed by the standard_number they belong to.
const STANDARD_OWN_PAGE = {
    1: 'governance.html',
    5: 'faculty-dashboard.html',
    6: 'resources.html',
};

function pageAllowedForUser(user, pageName) {
    if (!user || user.role === 'admin') return true;
    if (MEMBER_ALLOWED_PAGES.has(pageName)) return true;
    return STANDARD_OWN_PAGE[user.standard_number] === pageName;
}

/** Fetches the current user, retrying on anything that looks like the
 * server just waking up from Fly's auto-stop (network error, or a 5xx from
 * the proxy before the machine is ready) instead of immediately treating
 * it as "not signed in". A real 401 (bad/missing session) is NOT retried --
 * that's a genuine "please log in", not a transient failure.
 *
 * Without this, a page hit right as the machine cold-starts could see a
 * momentary failure, get redirected to login.html, and then login.html's
 * own check (now that the machine is awake) would say "already signed in"
 * and bounce back -- from the user's side, that reads as being logged in
 * and immediately kicked out, repeatedly. */
async function fetchCurrentUser() {
    const attempts = 4;
    const delays = [0, 600, 1200, 2000];
    let lastError = null;
    for (let i = 0; i < attempts; i++) {
        if (delays[i]) await new Promise((r) => setTimeout(r, delays[i]));
        try {
            const res = await fetch(`${window.location.origin}/api/auth/me`);
            if (res.status === 401) {
                throw Object.assign(new Error('not authenticated'), { terminal: true });
            }
            if (!res.ok) {
                lastError = new Error(`server returned ${res.status}`);
                continue;
            }
            return await res.json();
        } catch (err) {
            if (err.terminal) throw err;
            lastError = err;
        }
    }
    throw lastError || new Error('not authenticated');
}

/** Hides any top-nav link a member isn't allowed to click, so the nav bar
 * only ever shows pages that actually work for them. Admins see every
 * link; not signed in is not a state this runs in (guards redirect first). */
function filterNavForUser(user) {
    if (!user || user.role === 'admin') return;
    document.querySelectorAll('a.nav-link').forEach((link) => {
        const href = (link.getAttribute('href') || '').split('/').pop();
        if (!pageAllowedForUser(user, href)) {
            link.remove();
        }
    });
}
