const apiUrl = window.location.origin || '';

let standards = [];
let indicators = [];
let openLogPanels = new Set();
let currentUser = null;

// --- Auth ---

async function requireAuth() {
    try {
        const res = await fetch(`${apiUrl}/api/auth/me`);
        if (!res.ok) throw new Error('not authenticated');
        currentUser = await res.json();
    } catch (err) {
        window.location.href = `login.html?next=indicators-tracker.html`;
        throw err;
    }
}

function renderAuthBar() {
    const bar = document.getElementById('auth-bar');
    const roleLabel = currentUser.role === 'admin'
        ? 'Admin'
        : `Standard ${currentUser.standard_number}`;
    bar.innerHTML = `${escapeHtml(currentUser.username)} <span class="badge">${escapeHtml(roleLabel)}</span>`;

    const isAdmin = currentUser.role === 'admin';
    document.getElementById('sheet-sync-section').hidden = !isAdmin;
    document.getElementById('generate-ssr-btn').hidden = !isAdmin;
    document.getElementById('team-access-section').hidden = !isAdmin;
}

function initLogout() {
    document.getElementById('logout-btn').addEventListener('click', async () => {
        await fetch(`${apiUrl}/api/auth/logout`, { method: 'POST' });
        window.location.href = 'login.html';
    });
}

/** Members can only edit rows under their own standard; grey out + lock the rest. */
function applyStandardAccessLocks() {
    if (currentUser.role === 'admin') return;
    document.querySelectorAll('tr[data-indicator-id]').forEach((row) => {
        const ind = indicators.find((i) => i.id === Number(row.dataset.indicatorId));
        if (ind && ind.standard_number !== currentUser.standard_number) {
            row.classList.add('indicator-readonly');
            row.querySelectorAll('input, select, button').forEach((el) => { el.disabled = true; });
        }
    });
}

/** Escape untrusted text before inserting into innerHTML. */
function escapeHtml(str) {
    const d = document.createElement('div');
    d.textContent = String(str ?? '');
    return d.innerHTML;
}

async function fetchJson(url, options) {
    const res = await fetch(url, options);
    if (res.status === 401) {
        window.location.href = `login.html?next=indicators-tracker.html`;
        throw new Error('Session expired');
    }
    if (!res.ok) {
        const detail = await res.json().catch(() => ({}));
        throw new Error(detail.detail || `Request failed (${res.status})`);
    }
    return res.json();
}

async function loadStandards() {
    standards = await fetchJson(`${apiUrl}/api/indicators/standards`);
    const filterSelect = document.getElementById('filter-standard');
    const newSelect = document.getElementById('new-standard');
    // Clear previously-appended <option>s (keeps the first placeholder option in filterSelect)
    while (filterSelect.options.length > 1) filterSelect.remove(1);
    newSelect.innerHTML = '';
    // Members can only add indicators under their own standard.
    const visibleStandards = (currentUser && currentUser.role !== 'admin')
        ? standards.filter((s) => s.standard_number === currentUser.standard_number)
        : standards;
    standards.forEach((s) => {
        const opt1 = document.createElement('option');
        opt1.value = s.standard_number;
        opt1.textContent = `${t('ind.standardLabel').replace('{n}', s.standard_number)} — ${s.standard_name}`;
        filterSelect.appendChild(opt1);
    });
    visibleStandards.forEach((s) => {
        const opt2 = document.createElement('option');
        opt2.value = s.standard_number;
        opt2.textContent = `${t('ind.standardLabel').replace('{n}', s.standard_number)} — ${s.standard_name}`;
        newSelect.appendChild(opt2);
    });
    if (currentUser && currentUser.role !== 'admin') newSelect.disabled = true;
}

async function loadSummary() {
    const summary = await fetchJson(`${apiUrl}/api/indicators/summary`);
    const grid = document.getElementById('standard-summary-grid');
    grid.innerHTML = summary.map((s) => {
        const pct = s.total > 0 ? Math.round((s.complete / s.total) * 100) : 0;
        return `
            <div class="indicator-summary-card">
                <h3>${t('ind.standardLabel').replace('{n}', s.standard_number)}</h3>
                <p class="indicator-summary-name">${escapeHtml(s.standard_name)}</p>
                <div class="indicator-progress-bar">
                    <div class="indicator-progress-fill" style="width:${pct}%"></div>
                </div>
                <p class="indicator-summary-counts">
                    <span class="badge badge-complete">${t('ind.badgeComplete').replace('{n}', s.complete)}</span>
                    <span class="badge badge-partial">${t('ind.badgePartial').replace('{n}', s.partial)}</span>
                    <span class="badge badge-missing">${t('ind.badgeMissing').replace('{n}', s.missing)}</span>
                </p>
            </div>
        `;
    }).join('');
}

function currentFilters() {
    const standardNumber = document.getElementById('filter-standard').value;
    const status = document.getElementById('filter-status').value;
    return { standardNumber, status };
}

async function loadIndicators() {
    const { standardNumber, status } = currentFilters();
    const params = new URLSearchParams();
    if (standardNumber) params.set('standard_number', standardNumber);
    if (status) params.set('status', status);
    indicators = await fetchJson(`${apiUrl}/api/indicators?${params.toString()}`);
    renderIndicators();
}

function statusBadgeClass(status) {
    return `badge badge-${status}`;
}

function renderIndicators() {
    const container = document.getElementById('standards-container');
    const byStandard = {};
    indicators.forEach((i) => {
        (byStandard[i.standard_number] = byStandard[i.standard_number] || []).push(i);
    });

    const numbers = Object.keys(byStandard).map(Number).sort((a, b) => a - b);
    if (numbers.length === 0) {
        container.innerHTML = `<p class="section-desc">${t('ind.noMatch')}</p>`;
        return;
    }

    container.innerHTML = numbers.map((num) => {
        const rows = byStandard[num];
        const standardName = rows[0].standard_name;
        return `
            <div class="dashboard-section section-collapsible">
                <button type="button" class="section-toggle" aria-expanded="true" data-toggle-standard="${num}">
                    <span class="section-title">${t('ind.standardLabel').replace('{n}', num)} — ${escapeHtml(standardName)}</span>
                    <span class="toggle-icon">▼</span>
                </button>
                <div class="section-body">
                    <table class="data-table indicators-table">
                        <thead>
                            <tr>
                                <th>${t('ind.colIndicator')}</th>
                                <th>${t('common.status')}</th>
                                <th>${t('ind.colResponsible')}</th>
                                <th>${t('ind.colEvidence')}</th>
                                <th>${t('ind.colDueDate')}</th>
                                <th>${t('ind.colLog')}</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${rows.map(renderIndicatorRow).join('')}
                        </tbody>
                    </table>
                </div>
            </div>
        `;
    }).join('');

    attachRowHandlers();
    applyStandardAccessLocks();
}

function renderIndicatorRow(ind) {
    const logOpen = openLogPanels.has(ind.id);
    return `
        <tr data-indicator-id="${ind.id}">
            <td>${escapeHtml(ind.indicator_text)}</td>
            <td>
                <select class="indicator-status-select" data-field="status" data-id="${ind.id}">
                    <option value="missing" ${ind.status === 'missing' ? 'selected' : ''}>${t('status.missing')}</option>
                    <option value="partial" ${ind.status === 'partial' ? 'selected' : ''}>${t('status.partial')}</option>
                    <option value="complete" ${ind.status === 'complete' ? 'selected' : ''}>${t('status.complete')}</option>
                </select>
            </td>
            <td>
                <input type="text" class="indicator-inline-input" data-field="responsible_person" data-id="${ind.id}"
                       value="${escapeHtml(ind.responsible_person || '')}" placeholder="${t('ind.phUnassigned')}">
            </td>
            <td>
                <input type="text" class="indicator-inline-input" data-field="evidence_link" data-id="${ind.id}"
                       value="${escapeHtml(ind.evidence_link || '')}" placeholder="${t('ind.phPathUrl')}">
            </td>
            <td>
                <input type="date" class="indicator-inline-input" data-field="due_date" data-id="${ind.id}"
                       value="${escapeHtml(ind.due_date || '')}">
            </td>
            <td>
                <button type="button" class="btn-header btn-header-secondary indicator-log-toggle" data-id="${ind.id}">
                    ${t('ind.logButton').replace('{n}', (ind.closing_the_loop_log || []).length || '')}
                </button>
            </td>
        </tr>
        <tr class="indicator-log-row" data-log-for="${ind.id}" ${logOpen ? '' : 'hidden'}>
            <td colspan="6">
                <div class="indicator-log-panel" data-log-panel="${ind.id}">Loading…</div>
            </td>
        </tr>
    `;
}

async function saveField(id, field, value) {
    try {
        await fetchJson(`${apiUrl}/api/indicators/${id}`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ [field]: value }),
        });
        await loadSummary();
    } catch (err) {
        alert(`Could not save: ${err.message}`);
    }
}

function renderLogPanel(indicatorId, entries) {
    const panel = document.querySelector(`[data-log-panel="${indicatorId}"]`);
    if (!panel) return;
    const entriesHtml = entries.length
        ? entries.map((e) => `
            <li class="closing-loop-entry">
                <strong>${escapeHtml(e.entry_date)}</strong>
                — ${t('ind.weaknessLabel')}: ${escapeHtml(e.weakness_identified)}
                ${e.action_taken ? `— ${t('ind.actionLabel')}: ${escapeHtml(e.action_taken)}` : ''}
                ${e.entry_status ? `<span class="badge badge-${escapeHtml(e.entry_status)}">${escapeHtml(e.entry_status)}</span>` : ''}
            </li>
        `).join('')
        : `<li class="section-desc">${t('ind.noLogEntries')}</li>`;

    panel.innerHTML = `
        <ul class="closing-loop-list">${entriesHtml}</ul>
        <div class="closing-loop-form">
            <input type="text" class="log-weakness-input" placeholder="${t('ind.phWeakness')}">
            <input type="text" class="log-action-input" placeholder="${t('ind.phAction')}">
            <input type="text" class="log-status-input" placeholder="${t('ind.phStatusNote')}">
            <button type="button" class="btn-header btn-header-primary log-submit-btn" data-id="${indicatorId}">${t('ind.addLogEntry')}</button>
        </div>
    `;

    panel.querySelector('.log-submit-btn').addEventListener('click', async () => {
        const weakness = panel.querySelector('.log-weakness-input').value.trim();
        if (!weakness) {
            alert(t('ind.weaknessRequired'));
            return;
        }
        const action = panel.querySelector('.log-action-input').value.trim();
        const statusNote = panel.querySelector('.log-status-input').value.trim();
        try {
            const updated = await fetchJson(`${apiUrl}/api/indicators/${indicatorId}/log`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    weakness_identified: weakness,
                    action_taken: action || null,
                    entry_status: statusNote || null,
                }),
            });
            renderLogPanel(indicatorId, updated.closing_the_loop_log || []);
            const idx = indicators.findIndex((i) => i.id === indicatorId);
            if (idx >= 0) indicators[idx] = updated;
        } catch (err) {
            alert(`Could not add log entry: ${err.message}`);
        }
    });
}

async function toggleLogPanel(id) {
    const row = document.querySelector(`[data-log-for="${id}"]`);
    if (!row) return;
    if (openLogPanels.has(id)) {
        openLogPanels.delete(id);
        row.hidden = true;
        return;
    }
    openLogPanels.add(id);
    row.hidden = false;
    try {
        const full = await fetchJson(`${apiUrl}/api/indicators/${id}`);
        renderLogPanel(id, full.closing_the_loop_log || []);
    } catch (err) {
        const panel = document.querySelector(`[data-log-panel="${id}"]`);
        if (panel) panel.textContent = `Could not load log: ${err.message}`;
    }
}

function attachRowHandlers() {
    document.querySelectorAll('.indicator-status-select, .indicator-inline-input').forEach((el) => {
        const evt = el.tagName === 'SELECT' ? 'change' : 'blur';
        el.addEventListener(evt, () => {
            saveField(Number(el.dataset.id), el.dataset.field, el.value);
        });
    });
    document.querySelectorAll('.indicator-log-toggle').forEach((btn) => {
        btn.addEventListener('click', () => toggleLogPanel(Number(btn.dataset.id)));
    });
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

function initFilters() {
    document.getElementById('filter-standard').addEventListener('change', loadIndicators);
    document.getElementById('filter-status').addEventListener('change', loadIndicators);
}

function initAddIndicatorForm() {
    const form = document.getElementById('add-indicator-form');
    document.getElementById('add-indicator-btn').addEventListener('click', () => {
        form.hidden = !form.hidden;
    });
    document.getElementById('cancel-new-indicator-btn').addEventListener('click', () => {
        form.hidden = true;
    });
    document.getElementById('save-new-indicator-btn').addEventListener('click', async () => {
        const standardNumber = Number(document.getElementById('new-standard').value);
        const text = document.getElementById('new-text').value.trim();
        const responsible = document.getElementById('new-responsible').value.trim();
        const dueDate = document.getElementById('new-due-date').value;
        if (!text) {
            alert('Indicator text is required.');
            return;
        }
        try {
            await fetchJson(`${apiUrl}/api/indicators`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    standard_number: standardNumber,
                    indicator_text: text,
                    responsible_person: responsible || null,
                    due_date: dueDate || null,
                }),
            });
            document.getElementById('new-text').value = '';
            document.getElementById('new-responsible').value = '';
            document.getElementById('new-due-date').value = '';
            form.hidden = true;
            await Promise.all([loadIndicators(), loadSummary()]);
        } catch (err) {
            alert(`Could not create indicator: ${err.message}`);
        }
    });
}

const SHEET_URL_STORAGE_KEY = 'indicatorsTrackerSheetUrl';

async function initSheetSync() {
    const input = document.getElementById('sheet-url-input');
    const statusEl = document.getElementById('sync-status-text');
    const saved = localStorage.getItem(SHEET_URL_STORAGE_KEY);
    if (saved) {
        input.value = saved;
    } else {
        try {
            const cfg = await fetchJson(`${apiUrl}/api/indicators/sheet-config`);
            if (cfg.default_sheet_url) input.value = cfg.default_sheet_url;
        } catch (err) {
            // no server-configured default; leave blank
        }
    }

    document.getElementById('sync-sheet-btn').addEventListener('click', async () => {
        const url = input.value.trim();
        if (!url) {
            alert(t('ind.pasteSheetLink'));
            return;
        }
        localStorage.setItem(SHEET_URL_STORAGE_KEY, url);
        statusEl.textContent = t('ind.syncing');
        try {
            const result = await fetchJson(`${apiUrl}/api/indicators/sync-sheet`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ sheet_url: url }),
            });
            statusEl.textContent = `Synced: ${result.updated} updated, ${result.added} added` +
                (result.skipped_tabs.length ? `, skipped tabs: ${result.skipped_tabs.join(', ')}` : '') +
                (result.warnings.length ? `. Warnings: ${result.warnings.join('; ')}` : '');
            await Promise.all([loadIndicators(), loadSummary()]);
        } catch (err) {
            statusEl.textContent = `Sync failed: ${err.message}`;
        }
    });
}

function initSsrGeneration() {
    const btn = document.getElementById('generate-ssr-btn');
    btn.addEventListener('click', async () => {
        const originalText = btn.textContent;
        btn.disabled = true;
        btn.textContent = t('ind.generating');
        try {
            const res = await fetch(`${apiUrl}/export-ssr-docx`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({}),
            });
            if (!res.ok) {
                const detail = await res.json().catch(() => ({}));
                throw new Error(detail.detail || `Request failed (${res.status})`);
            }
            const blob = await res.blob();
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'Self_Study_Report.docx';
            document.body.appendChild(a);
            a.click();
            a.remove();
            URL.revokeObjectURL(url);
        } catch (err) {
            alert(`Could not generate SSR: ${err.message}`);
        } finally {
            btn.disabled = false;
            btn.textContent = originalText;
        }
    });
}

// --- Team access management (admin only) ---

async function loadUsers() {
    if (currentUser.role !== 'admin') return;
    const users = await fetchJson(`${apiUrl}/api/auth/users`);
    document.getElementById('users-tbody').innerHTML = users.map((u) => `
        <tr>
            <td>${escapeHtml(u.username)}</td>
            <td>${escapeHtml(u.role)}</td>
            <td>${u.standard_number ? t('ind.standardLabel').replace('{n}', u.standard_number) : ''}</td>
            <td>
                <button type="button" class="btn-header btn-header-secondary reset-pw-btn" data-id="${u.id}">Reset password</button>
                <button type="button" class="btn-header btn-header-secondary delete-user-btn" data-id="${u.id}">${t('common.delete')}</button>
            </td>
        </tr>
    `).join('') || '<tr><td colspan="4" class="section-desc">No accounts yet.</td></tr>';

    document.querySelectorAll('.reset-pw-btn').forEach((btn) => {
        btn.addEventListener('click', async () => {
            const pw = prompt('New temporary password (8+ characters):');
            if (!pw) return;
            try {
                await fetchJson(`${apiUrl}/api/auth/users/${btn.dataset.id}/password`, {
                    method: 'PATCH',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ password: pw }),
                });
                alert('Password reset.');
            } catch (err) {
                alert(`Could not reset password: ${err.message}`);
            }
        });
    });
    document.querySelectorAll('.delete-user-btn').forEach((btn) => {
        btn.addEventListener('click', async () => {
            if (!confirm('Remove this account?')) return;
            try {
                await fetchJson(`${apiUrl}/api/auth/users/${btn.dataset.id}`, { method: 'DELETE' });
                await loadUsers();
            } catch (err) {
                alert(`Could not remove account: ${err.message}`);
            }
        });
    });
}

function initUserManagementForm() {
    if (currentUser.role !== 'admin') return;

    const standardSelect = document.getElementById('new-user-standard');
    standardSelect.innerHTML = standards.map((s) =>
        `<option value="${s.standard_number}">${t('ind.standardLabel').replace('{n}', s.standard_number)} — ${escapeHtml(s.standard_name)}</option>`
    ).join('');

    const roleSelect = document.getElementById('new-user-role');
    roleSelect.addEventListener('change', () => {
        standardSelect.disabled = roleSelect.value === 'admin';
    });

    document.getElementById('add-user-btn').addEventListener('click', async () => {
        const username = document.getElementById('new-user-username').value.trim();
        const password = document.getElementById('new-user-password').value;
        const role = roleSelect.value;
        const standardNumber = role === 'member' ? Number(standardSelect.value) : null;
        if (!username || !password) {
            alert('Username and password are required.');
            return;
        }
        try {
            await fetchJson(`${apiUrl}/api/auth/users`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, password, role, standard_number: standardNumber }),
            });
            document.getElementById('new-user-username').value = '';
            document.getElementById('new-user-password').value = '';
            await loadUsers();
        } catch (err) {
            alert(`Could not create account: ${err.message}`);
        }
    });
}

async function init() {
    await requireAuth();
    renderAuthBar();
    initLogout();
    await loadStandards();
    await Promise.all([loadSummary(), loadIndicators()]);
    initFilters();
    initAddIndicatorForm();
    if (currentUser.role === 'admin') {
        initSsrGeneration();
        await initSheetSync();
        initUserManagementForm();
        await loadUsers();
    }
}

document.addEventListener('DOMContentLoaded', init);
document.addEventListener('i18n:applied', async () => {
    if (!currentUser) return;
    await loadStandards();
    await Promise.all([loadSummary(), loadIndicators()]);
});
