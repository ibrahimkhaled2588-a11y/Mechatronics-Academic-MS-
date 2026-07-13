const apiUrl = window.location.origin || '';

let standards = [];
let indicators = [];
let openLogPanels = new Set();

/** Escape untrusted text before inserting into innerHTML. */
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

async function loadStandards() {
    standards = await fetchJson(`${apiUrl}/api/indicators/standards`);
    const filterSelect = document.getElementById('filter-standard');
    const newSelect = document.getElementById('new-standard');
    standards.forEach((s) => {
        const opt1 = document.createElement('option');
        opt1.value = s.standard_number;
        opt1.textContent = `Standard ${s.standard_number} — ${s.standard_name}`;
        filterSelect.appendChild(opt1);

        const opt2 = document.createElement('option');
        opt2.value = s.standard_number;
        opt2.textContent = `Standard ${s.standard_number} — ${s.standard_name}`;
        newSelect.appendChild(opt2);
    });
}

async function loadSummary() {
    const summary = await fetchJson(`${apiUrl}/api/indicators/summary`);
    const grid = document.getElementById('standard-summary-grid');
    grid.innerHTML = summary.map((s) => {
        const pct = s.total > 0 ? Math.round((s.complete / s.total) * 100) : 0;
        return `
            <div class="indicator-summary-card">
                <h3>Standard ${s.standard_number}</h3>
                <p class="indicator-summary-name">${escapeHtml(s.standard_name)}</p>
                <div class="indicator-progress-bar">
                    <div class="indicator-progress-fill" style="width:${pct}%"></div>
                </div>
                <p class="indicator-summary-counts">
                    <span class="badge badge-complete">${s.complete} complete</span>
                    <span class="badge badge-partial">${s.partial} partial</span>
                    <span class="badge badge-missing">${s.missing} missing</span>
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
        container.innerHTML = '<p class="section-desc">No indicators match the current filters.</p>';
        return;
    }

    container.innerHTML = numbers.map((num) => {
        const rows = byStandard[num];
        const standardName = rows[0].standard_name;
        return `
            <div class="dashboard-section section-collapsible">
                <button type="button" class="section-toggle" aria-expanded="true" data-toggle-standard="${num}">
                    <span class="section-title">Standard ${num} — ${escapeHtml(standardName)}</span>
                    <span class="toggle-icon">▼</span>
                </button>
                <div class="section-body">
                    <table class="data-table indicators-table">
                        <thead>
                            <tr>
                                <th>Indicator</th>
                                <th>Status</th>
                                <th>Responsible</th>
                                <th>Evidence link</th>
                                <th>Due date</th>
                                <th>Log</th>
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
}

function renderIndicatorRow(ind) {
    const logOpen = openLogPanels.has(ind.id);
    return `
        <tr data-indicator-id="${ind.id}">
            <td>${escapeHtml(ind.indicator_text)}</td>
            <td>
                <select class="indicator-status-select" data-field="status" data-id="${ind.id}">
                    <option value="missing" ${ind.status === 'missing' ? 'selected' : ''}>Missing</option>
                    <option value="partial" ${ind.status === 'partial' ? 'selected' : ''}>Partial</option>
                    <option value="complete" ${ind.status === 'complete' ? 'selected' : ''}>Complete</option>
                </select>
            </td>
            <td>
                <input type="text" class="indicator-inline-input" data-field="responsible_person" data-id="${ind.id}"
                       value="${escapeHtml(ind.responsible_person || '')}" placeholder="Unassigned">
            </td>
            <td>
                <input type="text" class="indicator-inline-input" data-field="evidence_link" data-id="${ind.id}"
                       value="${escapeHtml(ind.evidence_link || '')}" placeholder="Path or URL">
            </td>
            <td>
                <input type="date" class="indicator-inline-input" data-field="due_date" data-id="${ind.id}"
                       value="${escapeHtml(ind.due_date || '')}">
            </td>
            <td>
                <button type="button" class="btn-header btn-header-secondary indicator-log-toggle" data-id="${ind.id}">
                    Log (${(ind.closing_the_loop_log || []).length || ''})
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
                — Weakness: ${escapeHtml(e.weakness_identified)}
                ${e.action_taken ? `— Action: ${escapeHtml(e.action_taken)}` : ''}
                ${e.entry_status ? `<span class="badge badge-${escapeHtml(e.entry_status)}">${escapeHtml(e.entry_status)}</span>` : ''}
            </li>
        `).join('')
        : '<li class="section-desc">No closing-the-loop entries yet.</li>';

    panel.innerHTML = `
        <ul class="closing-loop-list">${entriesHtml}</ul>
        <div class="closing-loop-form">
            <input type="text" class="log-weakness-input" placeholder="Weakness identified">
            <input type="text" class="log-action-input" placeholder="Action taken (optional)">
            <input type="text" class="log-status-input" placeholder="Status note (optional)">
            <button type="button" class="btn-header btn-header-primary log-submit-btn" data-id="${indicatorId}">Add entry</button>
        </div>
    `;

    panel.querySelector('.log-submit-btn').addEventListener('click', async () => {
        const weakness = panel.querySelector('.log-weakness-input').value.trim();
        if (!weakness) {
            alert('Weakness identified is required.');
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

async function init() {
    await loadStandards();
    await Promise.all([loadSummary(), loadIndicators()]);
    initFilters();
    initAddIndicatorForm();
}

document.addEventListener('DOMContentLoaded', init);
