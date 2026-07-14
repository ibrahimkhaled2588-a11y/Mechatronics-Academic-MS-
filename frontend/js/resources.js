const apiUrl = window.location.origin || '';

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

// --- Equipment ---

async function loadEquipment() {
    const rows = await fetchJson(`${apiUrl}/api/resources/equipment`);
    document.getElementById('equipment-tbody').innerHTML = rows.map((e) => `
        <tr class="${e.status !== 'operational' ? 'high-risk' : ''}">
            <td>${escapeHtml(e.name)}</td>
            <td>${escapeHtml(e.category || '')}</td>
            <td>${escapeHtml(e.location || '')}</td>
            <td>
                <select class="eq-status-select" data-id="${e.id}">
                    <option value="operational" ${e.status === 'operational' ? 'selected' : ''}>Operational</option>
                    <option value="needs_repair" ${e.status === 'needs_repair' ? 'selected' : ''}>Needs Repair</option>
                    <option value="out_of_service" ${e.status === 'out_of_service' ? 'selected' : ''}>Out of Service</option>
                </select>
            </td>
            <td>${escapeHtml(e.next_maintenance_date || '')}</td>
            <td><button type="button" class="btn-header btn-header-secondary delete-eq-btn" data-id="${e.id}">Delete</button></td>
        </tr>
    `).join('') || '<tr><td colspan="6" class="section-desc">No equipment recorded yet.</td></tr>';

    document.querySelectorAll('.eq-status-select').forEach((sel) => {
        sel.addEventListener('change', async () => {
            await fetchJson(`${apiUrl}/api/resources/equipment/${sel.dataset.id}`, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ status: sel.value }),
            });
            await refreshAll();
        });
    });
    document.querySelectorAll('.delete-eq-btn').forEach((btn) => {
        btn.addEventListener('click', async () => {
            await fetchJson(`${apiUrl}/api/resources/equipment/${btn.dataset.id}`, { method: 'DELETE' });
            await refreshAll();
        });
    });
}

function initEquipmentForm() {
    document.getElementById('add-eq-btn').addEventListener('click', async () => {
        const name = document.getElementById('new-eq-name').value.trim();
        const category = document.getElementById('new-eq-category').value.trim();
        const location = document.getElementById('new-eq-location').value.trim();
        const status = document.getElementById('new-eq-status').value;
        const date = document.getElementById('new-eq-date').value;
        if (!name) {
            alert('Equipment name is required.');
            return;
        }
        try {
            await fetchJson(`${apiUrl}/api/resources/equipment`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    name, category: category || null, location: location || null,
                    status, next_maintenance_date: date || null,
                }),
            });
            document.getElementById('new-eq-name').value = '';
            document.getElementById('new-eq-category').value = '';
            document.getElementById('new-eq-location').value = '';
            document.getElementById('new-eq-date').value = '';
            await refreshAll();
        } catch (err) {
            alert(`Could not add equipment: ${err.message}`);
        }
    });
}

// --- Library ---

async function loadLibrary() {
    const rows = await fetchJson(`${apiUrl}/api/resources/library`);
    document.getElementById('library-tbody').innerHTML = rows.map((h) => `
        <tr>
            <td>${escapeHtml(h.title)}</td>
            <td>${escapeHtml(h.subject_area || '')}</td>
            <td>${h.count}</td>
            <td><button type="button" class="btn-header btn-header-secondary delete-lib-btn" data-id="${h.id}">Delete</button></td>
        </tr>
    `).join('') || '<tr><td colspan="4" class="section-desc">No library holdings recorded yet.</td></tr>';

    document.querySelectorAll('.delete-lib-btn').forEach((btn) => {
        btn.addEventListener('click', async () => {
            await fetchJson(`${apiUrl}/api/resources/library/${btn.dataset.id}`, { method: 'DELETE' });
            await refreshAll();
        });
    });
}

function initLibraryForm() {
    document.getElementById('add-lib-btn').addEventListener('click', async () => {
        const title = document.getElementById('new-lib-title').value.trim();
        const subject = document.getElementById('new-lib-subject').value.trim();
        const count = Number(document.getElementById('new-lib-count').value);
        if (!title || !document.getElementById('new-lib-count').value) {
            alert('Title and count are required.');
            return;
        }
        try {
            await fetchJson(`${apiUrl}/api/resources/library`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ title, subject_area: subject || null, count }),
            });
            document.getElementById('new-lib-title').value = '';
            document.getElementById('new-lib-subject').value = '';
            document.getElementById('new-lib-count').value = '';
            await refreshAll();
        } catch (err) {
            alert(`Could not add library holding: ${err.message}`);
        }
    });
}

// --- Budget ---

async function loadBudget() {
    const rows = await fetchJson(`${apiUrl}/api/resources/budget`);
    document.getElementById('budget-tbody').innerHTML = rows.map((b) => `
        <tr>
            <td>${escapeHtml(b.fiscal_year)}</td>
            <td>${escapeHtml(b.category)}</td>
            <td>${b.amount}</td>
            <td>${escapeHtml(b.notes || '')}</td>
            <td><button type="button" class="btn-header btn-header-secondary delete-budget-btn" data-id="${b.id}">Delete</button></td>
        </tr>
    `).join('') || '<tr><td colspan="5" class="section-desc">No budget entries recorded yet.</td></tr>';

    document.querySelectorAll('.delete-budget-btn').forEach((btn) => {
        btn.addEventListener('click', async () => {
            await fetchJson(`${apiUrl}/api/resources/budget/${btn.dataset.id}`, { method: 'DELETE' });
            await refreshAll();
        });
    });
}

function initBudgetForm() {
    document.getElementById('add-budget-btn').addEventListener('click', async () => {
        const year = document.getElementById('new-budget-year').value.trim();
        const category = document.getElementById('new-budget-category').value.trim();
        const amount = Number(document.getElementById('new-budget-amount').value);
        const notes = document.getElementById('new-budget-notes').value.trim();
        if (!year || !category || !document.getElementById('new-budget-amount').value) {
            alert('Fiscal year, category, and amount are required.');
            return;
        }
        try {
            await fetchJson(`${apiUrl}/api/resources/budget`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ fiscal_year: year, category, amount, notes: notes || null }),
            });
            document.getElementById('new-budget-year').value = '';
            document.getElementById('new-budget-category').value = '';
            document.getElementById('new-budget-amount').value = '';
            document.getElementById('new-budget-notes').value = '';
            await refreshAll();
        } catch (err) {
            alert(`Could not add budget entry: ${err.message}`);
        }
    });
}

// --- Dashboard KPIs + maintenance-due ---

async function loadDashboard() {
    const summary = await fetchJson(`${apiUrl}/api/resources/dashboard`);

    document.getElementById('kpi-grid').innerHTML = `
        <div class="indicator-summary-card">
            <h3>${summary.total_equipment}</h3>
            <p class="indicator-summary-name">Equipment items</p>
        </div>
        <div class="indicator-summary-card">
            <h3>${summary.needs_repair_count + summary.out_of_service_count}</h3>
            <p class="indicator-summary-name">Needing repair / out of service</p>
        </div>
        <div class="indicator-summary-card">
            <h3>${summary.maintenance_due_count}</h3>
            <p class="indicator-summary-name">Maintenance due (30 days)</p>
        </div>
        <div class="indicator-summary-card">
            <h3>${summary.total_library_items}</h3>
            <p class="indicator-summary-name">Library items (${summary.total_library_titles} titles)</p>
        </div>
        <div class="indicator-summary-card">
            <h3>${summary.total_budget_amount}</h3>
            <p class="indicator-summary-name">Total budget recorded</p>
        </div>
    `;

    document.getElementById('maintenance-tbody').innerHTML = summary.maintenance_due.map((e) => `
        <tr class="${e.overdue ? 'high-risk' : ''}">
            <td>${escapeHtml(e.name)}</td>
            <td>${escapeHtml(e.location || '')}</td>
            <td>${escapeHtml(e.next_maintenance_date)}</td>
            <td>${e.overdue ? '<span class="badge badge-missing">overdue</span>' : '<span class="badge badge-partial">due soon</span>'}</td>
        </tr>
    `).join('') || '<tr><td colspan="4" class="section-desc">Nothing due for maintenance in the next 30 days.</td></tr>';
}

// --- Standard 6 indicators integration ---

async function loadStandard6Indicators() {
    const rows = await fetchJson(`${apiUrl}/api/indicators?standard_number=6`);
    const container = document.getElementById('std6-indicators-container');
    container.innerHTML = rows.map((ind) => `
        <div class="indicator-summary-card">
            <p>${escapeHtml(ind.indicator_text)}</p>
            <p class="indicator-summary-name">Status: <span class="badge badge-${ind.status}">${ind.status}</span></p>
            <button type="button" class="btn-header btn-header-primary mark-complete-btn" data-id="${ind.id}">
                Mark complete + note this dashboard as evidence
            </button>
        </div>
    `).join('') || '<p class="section-desc">No Standard 6 indicators found.</p>';

    container.querySelectorAll('.mark-complete-btn').forEach((btn) => {
        btn.addEventListener('click', async () => {
            try {
                await fetchJson(`${apiUrl}/api/indicators/${btn.dataset.id}`, {
                    method: 'PATCH',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ status: 'complete', evidence_link: '/resources.html' }),
                });
                await loadStandard6Indicators();
            } catch (err) {
                alert(`Could not update indicator: ${err.message}`);
            }
        });
    });
}

async function refreshAll() {
    await Promise.all([loadEquipment(), loadLibrary(), loadBudget(), loadDashboard(), loadStandard6Indicators()]);
}

async function init() {
    initSectionToggles();
    initEquipmentForm();
    initLibraryForm();
    initBudgetForm();
    await refreshAll();
}

document.addEventListener('DOMContentLoaded', init);
