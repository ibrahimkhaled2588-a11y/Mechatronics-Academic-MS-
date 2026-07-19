/**
 * Shared page guard for every page except login.html (indicators-tracker.html
 * now includes this too, since access_control.js always allows it).
 *
 * - Not signed in -> straight to login.html.
 * - Signed in as a member (not admin) -> allowed onto the shared
 *   analysis/report pages plus their own standard's dedicated page (see
 *   access_control.js); any other page sends them back to the indicators
 *   tracker. The nav bar is also filtered so members never even see a
 *   link to a page they can't reach.
 * - Signed in as admin -> let the page load normally, nav untouched.
 *
 * Include access_control.js immediately before this script, and this as
 * the first script on every gated page, before any page-specific script
 * that assumes the page is actually allowed to run.
 */
(async () => {
    try {
        const user = await fetchCurrentUser();
        const here = window.location.pathname.split('/').pop();
        if (!pageAllowedForUser(user, here)) {
            window.location.replace('indicators-tracker.html');
            return;
        }
        const applyNavFilter = () => filterNavForUser(user);
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', applyNavFilter);
        } else {
            applyNavFilter();
        }
    } catch (err) {
        const here = window.location.pathname.split('/').pop() || 'index.html';
        window.location.replace(`login.html?next=${encodeURIComponent(here)}`);
    }
})();
