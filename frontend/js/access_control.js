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
    'indicators-tracker.html',
]);

// Standard-specific pages, keyed by the standard_number they belong to.
const STANDARD_OWN_PAGE = {
    1: 'governance.html',
    2: 'curriculum-mapping.html',
    5: 'faculty-dashboard.html',
    6: 'resources.html',
};

function pageAllowedForUser(user, pageName) {
    if (!user || user.role === 'admin') return true;
    if (MEMBER_ALLOWED_PAGES.has(pageName)) return true;
    return STANDARD_OWN_PAGE[user.standard_number] === pageName;
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
