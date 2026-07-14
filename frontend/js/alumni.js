const apiUrl = window.location.origin || '';

let alumniList = [];
let knownGradYears = new Set();

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

async function loadAlumni() {
    const yearFilter = document.getElementById('filter-alum-year').value;
    const params = new URLSearchParams();
    if (yearFilter) params.set('graduation_year', yearFilter);
    alumniList = await fetchJson(`${apiUrl}/api/alumni?${params.toString()}`);
    renderAlumniTable();
    updateYearFilterOptions();
}

function renderAlumniTable() {
    document.getElementById('alumni-tbody').innerHTML = alumniList.map((a) => `
        <tr>
            <td>${escapeHtml(a.name)}</td>
            <td>${escapeHtml(a.student_id || '')}</td>
            <td>${a.graduation_year || ''}</td>
            <td>${escapeHtml(a.employer || '')}</td>
            <td>${escapeHtml(a.current_role || '')}</td>
            <td>
                ${a.surveyed_at
                    ? `<span class="badge badge-complete">${t('ind.yes')}</span>`
                    : `<button type="button" class="btn-header btn-header-secondary mark-surveyed-btn" data-id="${a.id}">${t('ind.markSurveyed')}</button>`}
            </td>
            <td><button type="button" class="btn-header btn-header-secondary delete-alum-btn" data-id="${a.id}">${t('common.delete')}</button></td>
        </tr>
    `).join('') || `<tr><td colspan="7" class="section-desc">${t('ind.noAlumni')}</td></tr>`;

    document.querySelectorAll('.mark-surveyed-btn').forEach((btn) => {
        btn.addEventListener('click', async () => {
            await fetchJson(`${apiUrl}/api/alumni/${btn.dataset.id}/mark-surveyed`, { method: 'POST' });
            await refreshAll();
        });
    });
    document.querySelectorAll('.delete-alum-btn').forEach((btn) => {
        btn.addEventListener('click', async () => {
            await fetchJson(`${apiUrl}/api/alumni/${btn.dataset.id}`, { method: 'DELETE' });
            await refreshAll();
        });
    });
}

function updateYearFilterOptions() {
    alumniList.forEach((a) => { if (a.graduation_year) knownGradYears.add(a.graduation_year); });
    const select = document.getElementById('filter-alum-year');
    const current = select.value;
    select.innerHTML = `<option value="">${t('survey.allYears')}</option>` +
        [...knownGradYears].sort((a, b) => b - a).map((y) => `<option value="${y}">${y}</option>`).join('');
    select.value = current;
}

function initAlumniForm() {
    document.getElementById('add-alum-btn').addEventListener('click', async () => {
        const name = document.getElementById('new-alum-name').value.trim();
        const studentId = document.getElementById('new-alum-student-id').value.trim();
        const year = document.getElementById('new-alum-year').value ? Number(document.getElementById('new-alum-year').value) : null;
        const employer = document.getElementById('new-alum-employer').value.trim();
        const role = document.getElementById('new-alum-role').value.trim();
        if (!name) {
            alert(t('ind.nameRequired'));
            return;
        }
        try {
            await fetchJson(`${apiUrl}/api/alumni`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    name, student_id: studentId || null, graduation_year: year,
                    employer: employer || null, current_role: role || null,
                }),
            });
            document.getElementById('new-alum-name').value = '';
            document.getElementById('new-alum-student-id').value = '';
            document.getElementById('new-alum-year').value = '';
            document.getElementById('new-alum-employer').value = '';
            document.getElementById('new-alum-role').value = '';
            await refreshAll();
        } catch (err) {
            alert(`Could not add alumnus: ${err.message}`);
        }
    });

    document.getElementById('filter-alum-year').addEventListener('change', loadAlumni);
}

async function loadAlumniSummary() {
    const summary = await fetchJson(`${apiUrl}/api/alumni/summary`);
    document.getElementById('alumni-kpi-grid').innerHTML = `
        <div class="indicator-summary-card">
            <h3>${summary.total_alumni}</h3>
            <p class="indicator-summary-name">${t('survey.kpiTotalAlumni')}</p>
        </div>
        <div class="indicator-summary-card">
            <h3>${summary.employment_rate}%</h3>
            <p class="indicator-summary-name">${t('survey.kpiEmploymentRate')}</p>
        </div>
        <div class="indicator-summary-card">
            <h3>${summary.survey_participation_rate}%</h3>
            <p class="indicator-summary-name">${t('survey.kpiParticipationRate')}</p>
        </div>
    `;
}

async function loadStandard4Indicators() {
    const rows = await fetchJson(`${apiUrl}/api/indicators?standard_number=4`);
    const container = document.getElementById('std4-indicators-container');
    container.innerHTML = rows.map((ind) => `
        <div class="indicator-summary-card">
            <p>${escapeHtml(ind.indicator_text)}</p>
            <p class="indicator-summary-name">${t('ind.statusLabel')} <span class="badge badge-${ind.status}">${t('status.' + ind.status)}</span></p>
            <button type="button" class="btn-header btn-header-primary mark-complete-btn" data-id="${ind.id}">
                ${t('ind.markCompleteGeneric')}
            </button>
        </div>
    `).join('') || `<p class="section-desc">${t('ind.noneForStandard')}</p>`;

    container.querySelectorAll('.mark-complete-btn').forEach((btn) => {
        btn.addEventListener('click', async () => {
            try {
                await fetchJson(`${apiUrl}/api/indicators/${btn.dataset.id}`, {
                    method: 'PATCH',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ status: 'complete', evidence_link: '/survey-dashboard.html' }),
                });
                await loadStandard4Indicators();
            } catch (err) {
                alert(`Could not update indicator: ${err.message}`);
            }
        });
    });
}

async function refreshAll() {
    await loadAlumni();
    await Promise.all([loadAlumniSummary(), loadStandard4Indicators()]);
}

async function init() {
    initSectionToggles();
    initAlumniForm();
    await refreshAll();
}

document.addEventListener('DOMContentLoaded', init);
document.addEventListener('i18n:applied', () => refreshAll());
