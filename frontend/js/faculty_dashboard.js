const apiUrl = window.location.origin || '';

let faculty = [];

function escapeHtml(str) {
    const d = document.createElement('div');
    d.textContent = String(str ?? '');
    return d.innerHTML;
}

async function fetchJson(url, options) {
    const res = await fetch(url, options);
    if (!res.ok) {
        const detail = await res.json().catch(() => ({}));
        throw new Error(detail.detail || `Request failed (${res.status})`);
    }
    return res.json();
}

function initSectionToggles() {
    document.querySelectorAll('.section-toggle').forEach((btn) => {
        btn.addEventListener('click', () => {
            const parent = btn.closest('.section-collapsible');
            if (!parent) return;
            const expanded = btn.getAttribute('aria-expanded') === 'true';
            btn.setAttribute('aria-expanded', String(!expanded));
            parent.classList.toggle('collapsed', expanded);
        });
    });
}

// --- Faculty roster ---

async function loadFaculty() {
    faculty = await fetchJson(`${apiUrl}/api/faculty/members`);
    renderFacultyTable();
    renderFacultySelects();
}

function renderFacultyTable() {
    document.getElementById('faculty-tbody').innerHTML = faculty.map((f) => `
        <tr>
            <td>${escapeHtml(f.name)}</td>
            <td>${escapeHtml(f.specialization || '')}</td>
            <td>${escapeHtml(f.degree || '')}</td>
            <td>${escapeHtml(f.rank || '')}</td>
            <td><button type="button" class="btn-header btn-header-secondary delete-faculty-btn" data-id="${f.id}">${t('common.delete')}</button></td>
        </tr>
    `).join('') || `<tr><td colspan="5" class="section-desc">${t('fac.noFacultyMembers')}</td></tr>`;

    document.querySelectorAll('.delete-faculty-btn').forEach((btn) => {
        btn.addEventListener('click', async () => {
            if (!confirm('Delete this faculty member? Their load and publication records will also be removed.')) return;
            await fetchJson(`${apiUrl}/api/faculty/members/${btn.dataset.id}`, { method: 'DELETE' });
            await refreshAll();
        });
    });
}

function renderFacultySelects() {
    const options = faculty.map((f) => `<option value="${f.id}">${escapeHtml(f.name)}</option>`).join('');
    document.getElementById('load-faculty-select').innerHTML = options || `<option value="">${t('fac.noFacultyYet')}</option>`;
    document.getElementById('pub-faculty-select').innerHTML = options || `<option value="">${t('fac.noFacultyYet')}</option>`;
}

function initFacultyForm() {
    document.getElementById('add-faculty-btn').addEventListener('click', async () => {
        const name = document.getElementById('new-faculty-name').value.trim();
        const spec = document.getElementById('new-faculty-spec').value.trim();
        const degree = document.getElementById('new-faculty-degree').value.trim();
        const rank = document.getElementById('new-faculty-rank').value.trim();
        if (!name) {
            alert(t('fac.nameRequired'));
            return;
        }
        try {
            await fetchJson(`${apiUrl}/api/faculty/members`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name, specialization: spec || null, degree: degree || null, rank: rank || null }),
            });
            document.getElementById('new-faculty-name').value = '';
            document.getElementById('new-faculty-spec').value = '';
            document.getElementById('new-faculty-degree').value = '';
            document.getElementById('new-faculty-rank').value = '';
            await refreshAll();
        } catch (err) {
            alert(`Could not add faculty member: ${err.message}`);
        }
    });
}

// --- Teaching load ---

async function loadTeachingLoad() {
    const rows = await fetchJson(`${apiUrl}/api/faculty/teaching-load`);
    document.getElementById('load-tbody').innerHTML = rows.map((r) => `
        <tr>
            <td>${escapeHtml(r.faculty_name)}</td>
            <td>${escapeHtml(r.semester)}</td>
            <td>${escapeHtml(r.course_name)}</td>
            <td>${r.hours}</td>
            <td><button type="button" class="btn-header btn-header-secondary delete-load-btn" data-id="${r.id}">${t('common.delete')}</button></td>
        </tr>
    `).join('') || `<tr><td colspan="5" class="section-desc">${t('fac.noLoadEntries')}</td></tr>`;

    document.querySelectorAll('.delete-load-btn').forEach((btn) => {
        btn.addEventListener('click', async () => {
            await fetchJson(`${apiUrl}/api/faculty/teaching-load/${btn.dataset.id}`, { method: 'DELETE' });
            await refreshAll();
        });
    });
}

function initLoadForm() {
    document.getElementById('add-load-btn').addEventListener('click', async () => {
        const facultyId = Number(document.getElementById('load-faculty-select').value);
        const semester = document.getElementById('load-semester').value.trim();
        const course = document.getElementById('load-course').value.trim();
        const hours = Number(document.getElementById('load-hours').value);
        if (!facultyId || !semester || !course || !hours) {
            alert(t('fac.loadRequired'));
            return;
        }
        try {
            await fetchJson(`${apiUrl}/api/faculty/teaching-load`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ faculty_id: facultyId, semester, course_name: course, hours }),
            });
            document.getElementById('load-semester').value = '';
            document.getElementById('load-course').value = '';
            document.getElementById('load-hours').value = '';
            await refreshAll();
        } catch (err) {
            alert(`Could not add teaching load: ${err.message}`);
        }
    });
}

// --- Publications ---

async function loadPublications() {
    const rows = await fetchJson(`${apiUrl}/api/faculty/publications`);
    document.getElementById('pub-tbody').innerHTML = rows.map((p) => `
        <tr>
            <td>${escapeHtml(p.faculty_name)}</td>
            <td>${escapeHtml(p.title)}</td>
            <td>${escapeHtml(p.venue || '')}</td>
            <td>${p.year || ''}</td>
            <td>${escapeHtml(p.pub_type || '')}</td>
            <td><button type="button" class="btn-header btn-header-secondary delete-pub-btn" data-id="${p.id}">${t('common.delete')}</button></td>
        </tr>
    `).join('') || `<tr><td colspan="6" class="section-desc">${t('fac.noPublications')}</td></tr>`;

    document.querySelectorAll('.delete-pub-btn').forEach((btn) => {
        btn.addEventListener('click', async () => {
            await fetchJson(`${apiUrl}/api/faculty/publications/${btn.dataset.id}`, { method: 'DELETE' });
            await loadPublications();
        });
    });
}

function initPublicationForm() {
    document.getElementById('add-pub-btn').addEventListener('click', async () => {
        const facultyId = Number(document.getElementById('pub-faculty-select').value);
        const title = document.getElementById('pub-title').value.trim();
        const venue = document.getElementById('pub-venue').value.trim();
        const year = document.getElementById('pub-year').value ? Number(document.getElementById('pub-year').value) : null;
        const pubType = document.getElementById('pub-type').value.trim();
        if (!facultyId || !title) {
            alert(t('fac.pubRequired'));
            return;
        }
        try {
            await fetchJson(`${apiUrl}/api/faculty/publications`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ faculty_id: facultyId, title, venue: venue || null, year, pub_type: pubType || null }),
            });
            document.getElementById('pub-title').value = '';
            document.getElementById('pub-venue').value = '';
            document.getElementById('pub-year').value = '';
            document.getElementById('pub-type').value = '';
            await loadPublications();
        } catch (err) {
            alert(`Could not add publication: ${err.message}`);
        }
    });
}

// --- Dashboard (KPIs + flags) ---

async function loadDashboard() {
    const summary = await fetchJson(`${apiUrl}/api/faculty/dashboard`);

    document.getElementById('kpi-grid').innerHTML = `
        <div class="indicator-summary-card">
            <h3>${summary.total_faculty}</h3>
            <p class="indicator-summary-name">${t('fac.kpiFaculty')}</p>
        </div>
        <div class="indicator-summary-card">
            <h3>${summary.average_load_hours}</h3>
            <p class="indicator-summary-name">${t('fac.kpiAvgLoad')}</p>
        </div>
        <div class="indicator-summary-card">
            <h3>${summary.overloaded_count}</h3>
            <p class="indicator-summary-name">${t('fac.kpiOverloaded')}</p>
        </div>
        <div class="indicator-summary-card">
            <h3>${summary.underloaded_count}</h3>
            <p class="indicator-summary-name">${t('fac.kpiUnderloaded')}</p>
        </div>
        <div class="indicator-summary-card">
            <h3>${summary.specialization_gap_count}</h3>
            <p class="indicator-summary-name">${t('fac.kpiGaps')}</p>
        </div>
    `;

    document.getElementById('imbalance-tbody').innerHTML = summary.load_imbalance_flags.map((f) => `
        <tr class="${f.flag === 'overloaded' ? 'high-risk' : ''}">
            <td>${escapeHtml(f.faculty_name)}</td>
            <td>${escapeHtml(f.semester)}</td>
            <td>${f.total_hours}</td>
            <td>${f.z_score}</td>
            <td><span class="badge badge-${f.flag === 'overloaded' ? 'missing' : 'partial'}">${t('fac.' + f.flag)}</span></td>
        </tr>
    `).join('') || `<tr><td colspan="5" class="section-desc">${t('fac.noImbalance')}</td></tr>`;

    document.getElementById('gaps-tbody').innerHTML = summary.specialization_gap_flags.map((g) => `
        <tr>
            <td>${escapeHtml(g.course_name)}</td>
            <td>${escapeHtml(g.semester)}</td>
            <td>${escapeHtml(g.faculty_name)}</td>
            <td>${g.faculty_specialization ? escapeHtml(g.faculty_specialization) : t('fac.notSet')}</td>
        </tr>
    `).join('') || `<tr><td colspan="4" class="section-desc">${t('fac.noGaps')}</td></tr>`;
}

// --- Standard 5 indicators integration ---

async function loadStandard5Indicators() {
    const rows = await fetchJson(`${apiUrl}/api/indicators?standard_number=5`);
    const container = document.getElementById('std5-indicators-container');
    container.innerHTML = rows.map((ind) => `
        <div class="indicator-summary-card">
            <p>${escapeHtml(ind.indicator_text)}</p>
            <p class="indicator-summary-name">${t('ind.statusLabel')} <span class="badge badge-${ind.status}">${t('status.' + ind.status)}</span></p>
            <button type="button" class="btn-header btn-header-primary mark-complete-btn" data-id="${ind.id}">
                ${t('fac.markCompleteDashboard')}
            </button>
        </div>
    `).join('') || `<p class="section-desc">${t('ind.noneForStandard')}</p>`;

    container.querySelectorAll('.mark-complete-btn').forEach((btn) => {
        btn.addEventListener('click', async () => {
            try {
                await fetchJson(`${apiUrl}/api/indicators/${btn.dataset.id}`, {
                    method: 'PATCH',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ status: 'complete', evidence_link: '/faculty-dashboard.html' }),
                });
                await loadStandard5Indicators();
            } catch (err) {
                alert(`Could not update indicator: ${err.message}`);
            }
        });
    });
}

async function refreshAll() {
    await loadFaculty();
    await Promise.all([loadTeachingLoad(), loadPublications(), loadDashboard(), loadStandard5Indicators()]);
}

const PAGE_STANDARD_NUMBER = 5;

/** Blocking access check that never auto-redirects -- see the identical
 * pattern in curriculum_mapping.js for why. */
async function initAccessGate() {
    const gate = document.getElementById('access-gate');
    const messageEl = document.getElementById('access-gate-message');
    const linkEl = document.getElementById('access-gate-link');
    const header = document.getElementById('page-header');
    const main = document.getElementById('page-main');

    let user;
    try {
        user = await fetchCurrentUser();
    } catch (err) {
        messageEl.textContent = 'Could not verify your session. Please refresh this page, or log in again if that keeps failing.';
        linkEl.textContent = 'Go to Login';
        linkEl.href = 'login.html?next=faculty-dashboard.html';
        linkEl.hidden = false;
        gate.classList.add('access-denied');
        return;
    }

    const allowed = user.role === 'admin' || user.standard_number === PAGE_STANDARD_NUMBER;
    if (!allowed) {
        messageEl.textContent = `This page belongs to Standard ${PAGE_STANDARD_NUMBER} (Faculty & Supporting Staff). ` +
            `Your account is assigned to ${user.standard_number ? 'Standard ' + user.standard_number : 'no standard'}.`;
        linkEl.hidden = false;
        gate.classList.add('access-denied');
        return;
    }

    gate.hidden = true;
    header.hidden = false;
    main.hidden = false;
    filterNavForUser(user);
    initSectionToggles();
    initFacultyForm();
    initLoadForm();
    initPublicationForm();
    await refreshAll();
}

document.addEventListener('DOMContentLoaded', initAccessGate);
document.addEventListener('i18n:applied', () => {
    if (!document.getElementById('page-main').hidden) refreshAll();
});
