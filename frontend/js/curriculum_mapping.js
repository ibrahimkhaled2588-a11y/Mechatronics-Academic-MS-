const apiUrl = window.location.origin || '';

let ilos = [];
let courses = [];
let matrix = {};

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

// --- ILOs ---

async function loadIlos() {
    ilos = await fetchJson(`${apiUrl}/api/curriculum/ilos`);
    renderIlos();
}

function renderIlos() {
    document.getElementById('ilos-tbody').innerHTML = ilos.map((ilo) => `
        <tr>
            <td>${escapeHtml(ilo.ilo_code || '')}</td>
            <td>${escapeHtml(ilo.ilo_text)}</td>
            <td><button type="button" class="btn-header btn-header-secondary delete-ilo-btn" data-id="${ilo.id}">${t('common.delete')}</button></td>
        </tr>
    `).join('') || `<tr><td colspan="3" class="section-desc">${t('curr.noIlos')}</td></tr>`;

    document.querySelectorAll('.delete-ilo-btn').forEach((btn) => {
        btn.addEventListener('click', async () => {
            if (!confirm('Delete this ILO? Its mappings will also be removed.')) return;
            await fetchJson(`${apiUrl}/api/curriculum/ilos/${btn.dataset.id}`, { method: 'DELETE' });
            await refreshAll();
        });
    });
}

// --- Courses ---

async function loadCourses() {
    courses = await fetchJson(`${apiUrl}/api/curriculum/courses`);
    renderCourses();
}

function renderCourses() {
    document.getElementById('courses-tbody').innerHTML = courses.map((c) => `
        <tr>
            <td>${escapeHtml(c.course_name)}</td>
            <td>${escapeHtml(c.source)}</td>
            <td><button type="button" class="btn-header btn-header-secondary delete-course-btn" data-id="${c.id}">${t('common.delete')}</button></td>
        </tr>
    `).join('') || `<tr><td colspan="3" class="section-desc">${t('curr.noCourses')}</td></tr>`;

    document.querySelectorAll('.delete-course-btn').forEach((btn) => {
        btn.addEventListener('click', async () => {
            if (!confirm('Delete this course? Its mappings will also be removed.')) return;
            await fetchJson(`${apiUrl}/api/curriculum/courses/${btn.dataset.id}`, { method: 'DELETE' });
            await refreshAll();
        });
    });
}

// --- Matrix ---

async function loadMatrix() {
    const data = await fetchJson(`${apiUrl}/api/curriculum/matrix`);
    matrix = data.matrix;
    renderMatrix();
}

function renderMatrix() {
    const table = document.getElementById('matrix-table');
    if (!ilos.length || !courses.length) {
        table.innerHTML = `<tr><td class="section-desc">${t('curr.buildMatrixHint')}</td></tr>`;
        return;
    }
    const headerCells = ilos.map((i) => `<th>${escapeHtml(i.ilo_code || ('ILO' + i.id))}</th>`).join('');
    const rows = courses.map((c) => {
        const cells = ilos.map((i) => {
            const mapped = !!(matrix[c.id] && matrix[c.id][i.id]);
            return `<td class="matrix-cell"><input type="checkbox" data-course-id="${c.id}" data-ilo-id="${i.id}" ${mapped ? 'checked' : ''}></td>`;
        }).join('');
        return `<tr><th class="matrix-row-label">${escapeHtml(c.course_name)}</th>${cells}</tr>`;
    }).join('');

    table.innerHTML = `<thead><tr><th>${t('curr.courseVsIlo')}</th>${headerCells}</tr></thead><tbody>${rows}</tbody>`;

    table.querySelectorAll('input[type="checkbox"]').forEach((cb) => {
        cb.addEventListener('change', async () => {
            try {
                await fetchJson(`${apiUrl}/api/curriculum/matrix`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        course_id: Number(cb.dataset.courseId),
                        ilo_id: Number(cb.dataset.iloId),
                        mapped: cb.checked,
                    }),
                });
                await loadFindings();
            } catch (err) {
                alert(`Could not save mapping: ${err.message}`);
                cb.checked = !cb.checked;
            }
        });
    });
}

// --- Findings ---

async function loadFindings() {
    const summary = await fetchJson(`${apiUrl}/api/curriculum/summary`);
    const container = document.getElementById('findings-container');
    const section = (title, items, textFn, emptyText) => `
        <div class="indicator-summary-card">
            <h3>${escapeHtml(title)}</h3>
            ${items.length
                ? `<ul class="closing-loop-list">${items.map((x) => `<li class="closing-loop-entry">${escapeHtml(textFn(x))}</li>`).join('')}</ul>`
                : `<p class="section-desc">${escapeHtml(emptyText)}</p>`}
        </div>
    `;
    container.innerHTML = [
        section(t('curr.findZero'), summary.zero_coverage_ilos, (i) => `${i.ilo_code || 'ILO' + i.id}: ${i.ilo_text}`, t('curr.findZeroEmpty')),
        section(t('curr.findLow'), summary.low_coverage_ilos, (i) => `${i.ilo_code || 'ILO' + i.id}: ${i.ilo_text}`, t('curr.findLowEmpty')),
        section(t('curr.findDup'), summary.heavy_duplication_ilos, (i) => `${i.ilo_code || 'ILO' + i.id}: ${i.ilo_text}`, t('curr.findDupEmpty')),
        section(t('curr.findUnmapped'), summary.courses_without_ilos, (c) => c.course_name, t('curr.findUnmappedEmpty')),
    ].join('');
}

// --- Standard 2 indicators integration ---

async function loadStandard2Indicators() {
    const container = document.getElementById('std2-indicators-container');
    let rows;
    try {
        rows = await fetchJson(`${apiUrl}/api/indicators?standard_number=2`);
    } catch (err) {
        container.innerHTML = `<p class="section-desc">Log in to see and update Standard 2 indicators here.</p>`;
        return;
    }
    container.innerHTML = rows.map((ind) => `
        <div class="indicator-summary-card">
            <p>${escapeHtml(ind.indicator_text)}</p>
            <p class="indicator-summary-name">${t('ind.statusLabel')} <span class="badge badge-${ind.status}">${t('status.' + ind.status)}</span></p>
            <button type="button" class="btn-header btn-header-primary mark-complete-btn" data-id="${ind.id}">
                ${t('curr.markCompleteExport')}
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
                        evidence_link: '/export-curriculum-map-docx',
                    }),
                });
                await loadStandard2Indicators();
            } catch (err) {
                alert(`Could not update indicator: ${err.message}`);
            }
        });
    });
}

// --- Add forms ---

function initAddForms() {
    document.getElementById('add-ilo-btn').addEventListener('click', async () => {
        const code = document.getElementById('new-ilo-code').value.trim();
        const text = document.getElementById('new-ilo-text').value.trim();
        if (!text) {
            alert('ILO text is required.');
            return;
        }
        try {
            await fetchJson(`${apiUrl}/api/curriculum/ilos`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ ilo_code: code || null, ilo_text: text }),
            });
            document.getElementById('new-ilo-code').value = '';
            document.getElementById('new-ilo-text').value = '';
            await refreshAll();
        } catch (err) {
            alert(`Could not add ILO: ${err.message}`);
        }
    });

    document.getElementById('add-course-btn').addEventListener('click', async () => {
        const name = document.getElementById('new-course-name').value.trim();
        if (!name) {
            alert('Course name is required.');
            return;
        }
        try {
            await fetchJson(`${apiUrl}/api/curriculum/courses`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ course_name: name }),
            });
            document.getElementById('new-course-name').value = '';
            await refreshAll();
        } catch (err) {
            alert(`Could not add course: ${err.message}`);
        }
    });

    document.getElementById('course-import-file').addEventListener('change', async (e) => {
        const file = e.target.files[0];
        if (!file) return;
        const form = new FormData();
        form.append('file', file);
        const summaryEl = document.getElementById('import-summary');
        summaryEl.textContent = 'Importing...';
        try {
            const result = await fetchJson(`${apiUrl}/api/curriculum/courses/import-excel`, {
                method: 'POST',
                body: form,
            });
            summaryEl.textContent = `Imported ${result.added.length} new course(s); ${result.merged_into_existing.length} matched existing courses and were skipped.`;
            await refreshAll();
        } catch (err) {
            summaryEl.textContent = `Import failed: ${err.message}`;
        } finally {
            e.target.value = '';
        }
    });
}

async function refreshAll() {
    await Promise.all([loadIlos(), loadCourses()]);
    await loadMatrix();
    await Promise.all([loadFindings(), loadStandard2Indicators()]);
}

async function init() {
    initSectionToggles();
    initAddForms();
    await refreshAll();
}

document.addEventListener('DOMContentLoaded', init);
document.addEventListener('i18n:applied', () => refreshAll());
