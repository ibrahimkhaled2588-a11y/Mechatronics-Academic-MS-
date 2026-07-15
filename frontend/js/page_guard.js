/**
 * Shared page guard for every page except login.html and
 * indicators-tracker.html (which handles its own auth + role logic,
 * since both admins and members belong there).
 *
 * - Not signed in -> straight to login.html.
 * - Signed in as a member (not admin) -> the indicators tracker is the
 *   only page they're allowed on, so send them back there. Members
 *   shouldn't be able to reach the other tool pages at all, not even to
 *   look.
 * - Signed in as admin -> let the page load normally.
 *
 * Include this as the first script on every gated page, before any
 * page-specific script that assumes the page is actually allowed to run.
 */
(async () => {
    try {
        const res = await fetch(`${window.location.origin}/api/auth/me`);
        if (!res.ok) throw new Error('not authenticated');
        const user = await res.json();
        if (user.role !== 'admin') {
            window.location.replace('indicators-tracker.html');
        }
    } catch (err) {
        const here = window.location.pathname.split('/').pop() || 'index.html';
        window.location.replace(`login.html?next=${encodeURIComponent(here)}`);
    }
})();
