const apiUrl = window.location.origin || '';

let documents = [];

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

// --- Mission ---

async function loadMission() {
    const versions = await fetchJson(`${apiUrl}/api/governance/mission`);
    const currentEl = document.getElementById('current-mission');
    currentEl.innerHTML = versions.length
        ? `<p class="governance-current-label">${t('gov.currentSaved').replace('{date}', escapeHtml(versions[0].created_at))}</p><p>${escapeHtml(versions[0].mission_text)}</p>`
        : `<p class="section-desc">${t('gov.noMission')}</p>`;

    document.getElementById('mission-history-list').innerHTML = versions.length > 1
        ? versions.slice(1).map((v) => `
            <li class="closing-loop-entry">
                <strong>${escapeHtml(v.created_at)}</strong>: ${escapeHtml(v.mission_text)}
            </li>
        `).join('')
        : `<li class="section-desc">${t('gov.noEarlierVersions')}</li>`;
}

function initMissionForm() {
    document.getElementById('save-mission-btn').addEventListener('click', async () => {
        const text = document.getElementById('new-mission-text').value.trim();
        if (!text) {
            alert(t('gov.missionRequired'));
            return;
        }
        try {
            await fetchJson(`${apiUrl}/api/governance/mission`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ mission_text: text }),
            });
            document.getElementById('new-mission-text').value = '';
            await loadMission();
        } catch (err) {
            alert(`Could not save mission: ${err.message}`);
        }
    });
}

// --- Documents ---

async function loadDocuments() {
    const committee = document.getElementById('filter-committee').value;
    const params = new URLSearchParams();
    if (committee) params.set('committee_name', committee);
    documents = await fetchJson(`${apiUrl}/api/governance/documents?${params.toString()}`);
    renderDocuments();
    updateCommitteeFilterOptions();
}

function renderDocuments() {
    document.getElementById('documents-tbody').innerHTML = documents.map((d) => `
        <tr>
            <td><a href="/api/governance/documents/${d.id}/file" target="_blank">${escapeHtml(d.title)}</a></td>
            <td>${escapeHtml(d.committee_name || '')}</td>
            <td>${escapeHtml(d.document_date || '')}</td>
            <td>${escapeHtml(d.uploaded_at)}</td>
            <td><button type="button" class="btn-header btn-header-secondary delete-doc-btn" data-id="${d.id}">${t('common.delete')}</button></td>
        </tr>
    `).join('') || `<tr><td colspan="5" class="section-desc">${t('gov.noDocuments')}</td></tr>`;

    document.querySelectorAll('.delete-doc-btn').forEach((btn) => {
        btn.addEventListener('click', async () => {
            if (!confirm('Delete this document?')) return;
            await fetchJson(`${apiUrl}/api/governance/documents/${btn.dataset.id}`, { method: 'DELETE' });
            await loadDocuments();
        });
    });
}

let knownCommittees = new Set();
function updateCommitteeFilterOptions() {
    documents.forEach((d) => { if (d.committee_name) knownCommittees.add(d.committee_name); });
    const select = document.getElementById('filter-committee');
    const current = select.value;
    select.innerHTML = `<option value="">${t('gov.allCommittees')}</option>` +
        [...knownCommittees].sort().map((c) => `<option value="${escapeHtml(c)}">${escapeHtml(c)}</option>`).join('');
    select.value = current;
}

function initDocumentForm() {
    document.getElementById('upload-doc-btn').addEventListener('click', async () => {
        const title = document.getElementById('doc-title').value.trim();
        const committee = document.getElementById('doc-committee').value.trim();
        const date = document.getElementById('doc-date').value;
        const fileInput = document.getElementById('doc-file');
        const file = fileInput.files[0];
        if (!title || !file) {
            alert(t('gov.titleFileRequired'));
            return;
        }
        const form = new FormData();
        form.append('file', file);
        form.append('title', title);
        if (committee) form.append('committee_name', committee);
        if (date) form.append('document_date', date);
        try {
            await fetchJson(`${apiUrl}/api/governance/documents`, { method: 'POST', body: form });
            document.getElementById('doc-title').value = '';
            document.getElementById('doc-committee').value = '';
            document.getElementById('doc-date').value = '';
            fileInput.value = '';
            await loadDocuments();
        } catch (err) {
            alert(`Could not upload document: ${err.message}`);
        }
    });

    document.getElementById('filter-committee').addEventListener('change', loadDocuments);
}

// --- Stakeholder log ---

async function loadStakeholderLog() {
    const rows = await fetchJson(`${apiUrl}/api/governance/stakeholder-log`);
    document.getElementById('stakeholder-tbody').innerHTML = rows.map((r) => `
        <tr>
            <td>${escapeHtml(r.stakeholder_name)}</td>
            <td>${escapeHtml(r.stakeholder_role || '')}</td>
            <td>${escapeHtml(r.consulted_on)}</td>
            <td>${escapeHtml(r.topic)}</td>
        </tr>
    `).join('') || `<tr><td colspan="4" class="section-desc">${t('gov.noStakeholderEntries')}</td></tr>`;
}

function initStakeholderForm() {
    document.getElementById('add-stakeholder-btn').addEventListener('click', async () => {
        const name = document.getElementById('sh-name').value.trim();
        const role = document.getElementById('sh-role').value.trim();
        const date = document.getElementById('sh-date').value;
        const topic = document.getElementById('sh-topic').value.trim();
        if (!name || !date || !topic) {
            alert(t('gov.stakeholderRequired'));
            return;
        }
        try {
            await fetchJson(`${apiUrl}/api/governance/stakeholder-log`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    stakeholder_name: name,
                    stakeholder_role: role || null,
                    consulted_on: date,
                    topic,
                }),
            });
            document.getElementById('sh-name').value = '';
            document.getElementById('sh-role').value = '';
            document.getElementById('sh-date').value = '';
            document.getElementById('sh-topic').value = '';
            await loadStakeholderLog();
        } catch (err) {
            alert(`Could not add entry: ${err.message}`);
        }
    });
}

// --- Standard 1 indicators integration ---

async function loadStandard1Indicators() {
    const rows = await fetchJson(`${apiUrl}/api/indicators?standard_number=1`);
    const container = document.getElementById('std1-indicators-container');
    container.innerHTML = rows.map((ind) => `
        <div class="indicator-summary-card">
            <p>${escapeHtml(ind.indicator_text)}</p>
            <p class="indicator-summary-name">${t('ind.statusLabel')} <span class="badge badge-${ind.status}">${t('status.' + ind.status)}</span></p>
            <button type="button" class="btn-header btn-header-primary mark-complete-btn" data-id="${ind.id}">
                ${t('gov.markCompleteRegister')}
            </button>
        </div>
    `).join('') || `<p class="section-desc">${t('ind.noneForStandard')}</p>`;

    container.querySelectorAll('.mark-complete-btn').forEach((btn) => {
        btn.addEventListener('click', async () => {
            try {
                await fetchJson(`${apiUrl}/api/indicators/${btn.dataset.id}`, {
                    method: 'PATCH',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        status: 'complete',
                        evidence_link: '/governance.html',
                    }),
                });
                await loadStandard1Indicators();
            } catch (err) {
                alert(`Could not update indicator: ${err.message}`);
            }
        });
    });
}

const PAGE_STANDARD_NUMBER = 1;

/** Blocking access check that never auto-redirects -- see the identical
 * pattern in curriculum_mapping.js for why (avoids the login/page bounce
 * loop a redirect-on-failure guard could produce during a slow session
 * check). Shows a static loading/denied message instead of navigating. */
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
        linkEl.href = 'login.html?next=governance.html';
        linkEl.hidden = false;
        gate.classList.add('access-denied');
        return;
    }

    const allowed = user.role === 'admin' || user.standard_number === PAGE_STANDARD_NUMBER;
    if (!allowed) {
        messageEl.textContent = `This page belongs to Standard ${PAGE_STANDARD_NUMBER} (Governance). ` +
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
    initMissionForm();
    initDocumentForm();
    initStakeholderForm();
    await Promise.all([loadMission(), loadDocuments(), loadStakeholderLog(), loadStandard1Indicators()]);
}

document.addEventListener('DOMContentLoaded', initAccessGate);
document.addEventListener('i18n:applied', () => {
    if (!document.getElementById('page-main').hidden) {
        Promise.all([loadMission(), loadDocuments(), loadStakeholderLog(), loadStandard1Indicators()]);
    }
});
