/**
 * Shared page guard for every page except login.html and
 * indicators-tracker.html (which handles its own auth + role logic,
 * since both admins and members belong there).
 *
 * - Not signed in -> straight to login.html.
 * - Signed in as a member (not admin) -> allowed onto the shared
 *   analysis/report pages (not tied to any one standard's data), plus
 *   the one standard-specific page that matches their own standard
 *   number (e.g. the Standard 2 lead gets Curriculum Mapping). Any other
 *   standard's page sends them back to the indicators tracker instead.
 * - Signed in as admin -> let the page load normally.
 *
 * Include this as the first script on every gated page, before any
 * page-specific script that assumes the page is actually allowed to run.
 */
const MEMBER_ALLOWED_PAGES = new Set([
    'index.html', '', 'dashboard.html', 'course-report.html',
    'program-report.html', 'survey-dashboard.html', 'qa-chat.html',
]);

// Standard-specific pages, keyed by the standard_number they belong to.
const STANDARD_OWN_PAGE = {
    1: 'governance.html',
    2: 'curriculum-mapping.html',
    5: 'faculty-dashboard.html',
    6: 'resources.html',
};

(async () => {
    try {
        const res = await fetch(`${window.location.origin}/api/auth/me`);
        if (!res.ok) throw new Error('not authenticated');
        const user = await res.json();
        if (user.role !== 'admin') {
            const here = window.location.pathname.split('/').pop();
            const ownPage = STANDARD_OWN_PAGE[user.standard_number];
            if (!MEMBER_ALLOWED_PAGES.has(here) && here !== ownPage) {
                window.location.replace('indicators-tracker.html');
            }
        }
    } catch (err) {
        const here = window.location.pathname.split('/').pop() || 'index.html';
        window.location.replace(`login.html?next=${encodeURIComponent(here)}`);
    }
})();
