const apiUrl = window.location.origin || '';

// keep references to Chart.js instances for academic analytics so we can destroy them on re-render
let academicCharts = [];

/** Escape untrusted text before inserting into innerHTML. */
function escapeHtml(str) {
    const d = document.createElement('div');
    d.textContent = String(str ?? '');
    return d.innerHTML;
}

async function uploadFile(files) {
    const fileList = (Array.isArray(files) ? files : [files]).filter(Boolean);
    const form = new FormData();
    let endpoint;
    if (fileList.length > 1) {
        // Bulk mode: merge sheets across all files
        fileList.forEach((f) => form.append('files', f));
        endpoint = `${apiUrl}/upload-excel-bulk`;
    } else {
        form.append('file', fileList[0]);
        endpoint = `${apiUrl}/upload-excel`;
    }
    const resp = await fetch(endpoint, { method: 'POST', body: form });
    if (!resp.ok) {
        const err = await resp.json().catch(() => ({ detail: resp.statusText }));
        throw new Error(err.detail || `HTTP ${resp.status}`);
    }
    return resp.json();
}

/** Update the upload zone hint to show selected file names. */
function _showUploadHint(files) {
    const hint = document.getElementById('uploadHint');
    if (!hint) return;
    if (!files || !files.length) {
        hint.textContent = 'Select up to 10 Excel workbooks — sheets with matching names are merged automatically';
        return;
    }
    if (files.length === 1) {
        hint.textContent = `Selected: ${files[0].name}`;
    } else {
        hint.textContent = `Selected ${files.length} files: ${files.map((f) => f.name).join(', ')}`;
    }
}

function setLoading(loading) {
    const excelInput = document.getElementById('excelInput');
    const loadingPlaceholder = document.getElementById('loading-placeholder');
    if (loading) {
        if (loadingPlaceholder) {
            loadingPlaceholder.hidden = false;
        }
        if (excelInput) {
            excelInput.disabled = true;
        }
    } else {
        if (loadingPlaceholder) {
            loadingPlaceholder.hidden = true;
        }
        if (excelInput) {
            excelInput.disabled = false;
        }
    }
}

function renderKpiCards(kpis, predictions, alerts, alertsDetailed) {
    const kpiContainer = document.getElementById('kpi-cards');
    const alertsContainer = document.getElementById('alerts-container');
    if (!kpiContainer) return;

    kpiContainer.innerHTML = '';
    if (alertsContainer) alertsContainer.innerHTML = '';

    // Severity-colored alerts (use detailed if available, plain strings as fallback)
    const detailed = Array.isArray(alertsDetailed) && alertsDetailed.length ? alertsDetailed : null;
    const plain = Array.isArray(alerts) && alerts.length ? alerts : null;

    if (detailed || plain) {
        const alertsEl = document.createElement('div');
        alertsEl.className = 'alerts-box';
        const h3 = document.createElement('h3');
        h3.textContent = 'System Alerts';
        alertsEl.appendChild(h3);
        const ul = document.createElement('ul');

        if (detailed) {
            detailed.forEach((a) => {
                const li = document.createElement('li');
                li.className = `alert-item alert-${a.severity || 'info'}`;
                const badge = document.createElement('span');
                badge.className = `alert-badge alert-badge-${a.severity || 'info'}`;
                badge.textContent = (a.severity || 'info').toUpperCase();
                li.appendChild(badge);
                const msg = document.createElement('span');
                msg.textContent = a.message;
                li.appendChild(msg);
                ul.appendChild(li);
            });
        } else {
            plain.forEach((a) => {
                const li = document.createElement('li');
                li.textContent = a;
                ul.appendChild(li);
            });
        }
        alertsEl.appendChild(ul);
        if (alertsContainer) alertsContainer.appendChild(alertsEl);
    }

    const labelMap = {
        missing_ratio: ['Missing Ratio', true],
        duplicate_rate: ['Duplicate Rate', true],
        precision_score: ['Precision Score', false],
        consistency_index: ['Consistency Index', false],
        anomaly_density: ['Anomaly Density', true],
        anomaly_density_iqr: ['Anomaly (IQR)', true],
        completeness: ['Completeness', false],
        uniqueness: ['Uniqueness', false],
        data_drift_score: ['Data Drift (PSI)', false],
        composite_reliability_index: ['Reliability Index', false],
    };

    Object.entries(kpis).forEach(([sheet, vals]) => {
        const pred = (predictions && predictions[sheet]) || {};
        const card = document.createElement('div');
        card.className = 'kpi-card';

        const h3 = document.createElement('h3');
        h3.textContent = sheet;
        card.appendChild(h3);

        Object.entries(vals).forEach(([k, v]) => {
            if (typeof v !== 'number' || !labelMap[k]) return;
            const [label, isPercent] = labelMap[k];
            const display = isPercent ? `${(v * 100).toFixed(2)}%` : v.toFixed(3);
            const p = document.createElement('p');
            p.innerHTML = `<span>${label}:</span> ${escapeHtml(display)}`;
            card.appendChild(p);
        });

        const predScore = pred.predicted_quality_score != null ? `${(pred.predicted_quality_score * 100).toFixed(1)}%` : '—';
        const riskProb  = pred.risk_probability  != null ? `${(pred.risk_probability * 100).toFixed(1)}%` : '—';
        const outlook   = pred.outlook || '';

        card.insertAdjacentHTML('beforeend',
            `<p class="pred"><span>Predicted Quality:</span> ${escapeHtml(predScore)}</p>` +
            `<p class="pred"><span>Risk Probability:</span> ${escapeHtml(riskProb)}</p>`);
        if (outlook) {
            const op = document.createElement('p');
            op.className = 'prediction-note';
            op.textContent = outlook;
            card.appendChild(op);
        }
        kpiContainer.appendChild(card);
    });
}

function renderMergedCourses(mergedCourses) {
    const container = document.getElementById('merged-courses-container');
    if (!container) return;
    container.innerHTML = '';
    const rows = Array.isArray(mergedCourses) ? mergedCourses : [];
    if (!rows.length) {
        container.innerHTML = '<p class="section-desc">No merged-course statistics available yet.</p>';
        return;
    }
    const table = document.createElement('table');
    table.className = 'data-table merged-courses-table';
    table.innerHTML = `
      <caption>Merged by course name across all uploaded sheets</caption>
      <thead>
        <tr>
          <th>#</th>
          <th>Course</th>
          <th>Occurrences</th>
          <th>Sheets</th>
          <th>Total Students</th>
          <th>Excellence %</th>
          <th>Failure %</th>
          <th>GPA</th>
        </tr>
      </thead>
      <tbody></tbody>
    `;
    const tbody = table.querySelector('tbody');
    rows.forEach((r, i) => {
        const tr = document.createElement('tr');
        const cells = [
            String(i + 1),
            r.course ?? '—',
            String(r.occurrences ?? 0),
            String(r.sheet_count ?? 0),
            String(r.total_students ?? 0),
            r.excellence_rate != null ? `${Number(r.excellence_rate).toFixed(2)}%` : '—',
            r.failure_rate != null ? `${Number(r.failure_rate).toFixed(2)}%` : '—',
            r.gpa_estimate != null ? Number(r.gpa_estimate).toFixed(3) : '—',
        ];
        cells.forEach((text) => {
            const td = document.createElement('td');
            td.textContent = text;  // textContent prevents XSS from course names
            tr.appendChild(td);
        });
        tbody.appendChild(tr);
    });
    container.appendChild(table);
}

// Global analysis result — read by the chatbot widget
window._dashboardLastResult = null;

/** Shared render pipeline called after any upload (single or multi-file). */
async function _runUpload(files) {
    setLoading(true);
    try {
        const result = await uploadFile(files);
        window._dashboardLastResult = result;
        renderKpiCards(result.metadata?.kpis || {}, result.predictions, result.alerts, result.alerts_detailed);
        renderMergedCourses(result.quality_dashboard_merged_courses || []);
        renderAdvancedStats(result);
        renderAcademicAnalytics(result);
        renderPredictive(result);
        renderForecast(result);
        renderCoursePlans(result);
        openAllSections();
    } catch (err) {
        const alertsContainer = document.getElementById('alerts-container');
        if (alertsContainer) {
            const errDiv = document.createElement('div');
            errDiv.className = 'error-msg';
            errDiv.textContent = 'خطأ: ' + (err.message || 'فشل الاتصال بالخادم.');
            alertsContainer.replaceChildren(errDiv);
        }
    } finally {
        setLoading(false);
    }
}

document.getElementById('excelInput').addEventListener('change', async (e) => {
    const files = Array.from(e.target.files || []).filter((f) => (f.name || '').toLowerCase().endsWith('.xlsx'));
    if (!files.length) return;
    _showUploadHint(files);
    await _runUpload(files);
});


// helper renderers for the collapsible sections
function renderAdvancedStats(result) {
    const container = document.getElementById('advanced-stats-container');
    if (!container) return;
    container.innerHTML = '';
    const stats = result.program_statistics || {};
    if (!stats || Object.keys(stats).length === 0) {
        container.innerHTML = '<p class="section-desc">Advanced statistics will appear here after you upload a workbook.</p>';
        return;
    }

    const makeCard = (title, items) => {
        const card = document.createElement('div');
        card.className = 'kpi-card advanced-stat-card';
        const cardH3 = document.createElement('h3');
        cardH3.textContent = title;
        card.appendChild(cardH3);
        items.forEach(({ label, value, suffix }) => {
            const display = value == null ? '—' : `${value}${suffix || ''}`;
            // label and display are hardcoded strings or formatted numbers — safe
            card.insertAdjacentHTML('beforeend', `<p><span>${escapeHtml(label)}</span> ${escapeHtml(display)}</p>`);
        });
        container.appendChild(card);
    };

    const ineq = stats.inequality_balance || {};
    if (Object.keys(ineq).length) {
        const vd = ineq.variance_decomposition || {};
        makeCard('Inequality & Balance', [
            { label: 'GPA Gini inequality', value: ineq.gpa_inequality_index != null ? ineq.gpa_inequality_index.toFixed(3) : null },
            { label: 'Course difficulty dispersion', value: ineq.course_difficulty_dispersion != null ? ineq.course_difficulty_dispersion.toFixed(2) : null },
            { label: 'Academic equity score', value: ineq.academic_equity_score != null ? ineq.academic_equity_score.toFixed(3) : null },
            { label: 'Between-course variance', value: vd.between_course_variance != null ? vd.between_course_variance.toFixed(4) : null },
            { label: 'Within-course variance', value: vd.within_course_variance != null ? vd.within_course_variance.toFixed(4) : null },
        ]);
    }

    const long = stats.longitudinal_growth || {};
    if (Object.keys(long).length) {
        makeCard('Longitudinal Growth', [
            { label: 'CAGR GPA (per sheet)', value: long.cagr_gpa != null ? (long.cagr_gpa * 100).toFixed(2) : null, suffix: '%' },
            { label: 'Growth rate (excellence)', value: long.growth_rate_excellence != null ? (long.growth_rate_excellence * 100).toFixed(1) : null, suffix: '%' },
            { label: 'Failure trend acceleration', value: long.failure_trend_acceleration != null ? long.failure_trend_acceleration.toFixed(3) : null },
            { label: 'Program momentum score', value: long.program_momentum_score != null ? long.program_momentum_score.toFixed(2) : null },
        ]);
    }

    const ci = stats.cohort_intelligence || {};
    if (ci.cohort_retention_rate != null || ci.dropout_risk_probability != null) {
        makeCard('Cohort Intelligence', [
            { label: 'Estimated retention rate', value: ci.cohort_retention_rate != null ? (ci.cohort_retention_rate * 100).toFixed(1) : null, suffix: '%' },
            { label: 'Dropout risk probability', value: ci.dropout_risk_probability != null ? (ci.dropout_risk_probability * 100).toFixed(1) : null, suffix: '%' },
            { label: 'Academic recovery rate', value: ci.academic_recovery_rate != null ? (ci.academic_recovery_rate * 100).toFixed(1) : null, suffix: '%' },
        ]);
    }

    const mc = stats.monte_carlo_simulation || {};
    if (Object.keys(mc).length) {
        makeCard('Monte Carlo Simulation (1,000 runs)', [
            { label: 'Simulated mean final GPA', value: mc.simulated_mean_final_gpa != null ? mc.simulated_mean_final_gpa.toFixed(2) : null },
            { label: 'GPA std dev (simulated)', value: mc.simulated_std_final_gpa != null ? mc.simulated_std_final_gpa.toFixed(3) : null },
            { label: '5th percentile GPA', value: mc.percentile_5 != null ? mc.percentile_5.toFixed(2) : null },
            { label: '95th percentile GPA', value: mc.percentile_95 != null ? mc.percentile_95.toFixed(2) : null },
            { label: 'P(GPA >= 3.0)', value: mc.p_above_3 != null ? (mc.p_above_3 * 100).toFixed(1) : null, suffix: '%' },
            { label: 'P(GPA < 2.0)', value: mc.p_below_2 != null ? (mc.p_below_2 * 100).toFixed(1) : null, suffix: '%' },
            { label: 'Stress worst-case failure', value: mc.stress_test && mc.stress_test.worst_case_overall_failure_pct != null ? mc.stress_test.worst_case_overall_failure_pct.toFixed(1) : null, suffix: '%' },
        ]);
    }

    const bench = stats.benchmarking || {};
    if (Object.keys(bench).length) {
        makeCard('Benchmarking', [
            { label: 'Program mean GPA', value: bench.program_mean_gpa != null ? bench.program_mean_gpa.toFixed(2) : null },
            { label: 'Program GPA std dev', value: bench.program_std_gpa != null ? bench.program_std_gpa.toFixed(2) : null },
            { label: 'Z-score vs historical', value: bench.z_score_vs_historical != null ? bench.z_score_vs_historical.toFixed(2) : null },
        ]);
    }
}

function renderAcademicAnalytics(result) {
    const charts = document.getElementById('academic-charts');
    const tables = document.getElementById('academic-tables');
    if (charts) charts.innerHTML = '';
    if (tables) tables.innerHTML = '';
    // destroy old charts if any
    if (academicCharts && academicCharts.length) {
        academicCharts.forEach((ch) => {
            try {
                ch.destroy();
            } catch (e) {
                // ignore
            }
        });
        academicCharts = [];
    }

    const academic = result.academic_analytics || {};
    if (!Object.keys(academic).length) {
        if (tables) tables.innerHTML = '<p class="section-desc">Academic analytics will appear here after upload.</p>';
        return;
    }

    Object.entries(academic).forEach(([sheet, data]) => {
        const section = document.createElement('div');
        section.className = 'academic-table-section';

        const title = document.createElement('h4');
        title.textContent = sheet;
        section.appendChild(title);

        const makeTable = (captionText, rows, columns, highRiskKey) => {
            if (!rows || !rows.length) return;
            const wrapper = document.createElement('div');
            const table = document.createElement('table');
            table.className = 'data-table';

            const caption = document.createElement('caption');
            caption.textContent = captionText;
            table.appendChild(caption);

            const thead = document.createElement('thead');
            const headRow = document.createElement('tr');
            const numTh = document.createElement('th');
            numTh.textContent = '#';
            numTh.className = 'row-num';
            headRow.appendChild(numTh);
            columns.forEach((c) => {
                const th = document.createElement('th');
                th.textContent = c.label;
                headRow.appendChild(th);
            });
            thead.appendChild(headRow);
            table.appendChild(thead);

            const tbody = document.createElement('tbody');
            rows.forEach((row, idx) => {
                const tr = document.createElement('tr');
                if (highRiskKey && row[highRiskKey]) {
                    tr.classList.add('high-risk');
                }
                const numTd = document.createElement('td');
                numTd.textContent = String(idx + 1);
                numTd.className = 'row-num';
                tr.appendChild(numTd);
                columns.forEach((c) => {
                    const td = document.createElement('td');
                    let v = row[c.key];
                    if (typeof v === 'number') {
                        v = c.isPercent ? `${v.toFixed(1)}%` : v.toFixed(2).replace(/\.00$/, '');
                    }
                    td.textContent = v != null ? v : '—';
                    tr.appendChild(td);
                });
                tbody.appendChild(tr);
            });
            table.appendChild(tbody);
            wrapper.appendChild(table);
            section.appendChild(wrapper);
        };

        makeTable(
            'Top Courses by Enrollment',
            data.top20_enrollment || [],
            [
                { key: 'course', label: 'Course' },
                { key: 'enrollment', label: 'Enrollment' },
            ],
        );

        makeTable(
            'Top Courses by Excellence Rate',
            data.top20_excellence_rate || [],
            [
                { key: 'course', label: 'Course' },
                { key: 'excellence_rate', label: 'Excellence %', isPercent: true },
                { key: 'total', label: 'Students' },
            ],
        );

        makeTable(
            'Top Courses by Failure Rate',
            data.top20_failure_rate || [],
            [
                { key: 'course', label: 'Course' },
                { key: 'failure_rate', label: 'Failure %', isPercent: true },
                { key: 'total', label: 'Students' },
            ],
            'high_risk',
        );

        makeTable(
            'Top Courses by GPA',
            data.top20_gpa_per_course || [],
            [
                { key: 'course', label: 'Course' },
                { key: 'gpa_estimate', label: 'GPA' },
                { key: 'volatility_index', label: 'Volatility' },
                { key: 'total', label: 'Students' },
            ],
        );

        if (tables) tables.appendChild(section);
    });

    // charts per sheet (enrollment, excellence, failure, GPA)
    if (!charts || typeof Chart === 'undefined') {
        return;
    }

    Object.entries(academic).forEach(([sheet, data]) => {
        const topEnroll = data.top20_enrollment || [];
        const topExc = data.top20_excellence_rate || [];
        const topFail = data.top20_failure_rate || [];
        const topGpa = data.top20_gpa_per_course || [];
        if (!topEnroll.length && !topExc.length && !topFail.length && !topGpa.length) {
            return;
        }

        const sheetBlock = document.createElement('div');
        sheetBlock.className = 'chart-wrap sheet-chart-group';

        const heading = document.createElement('h4');
        heading.textContent = sheet;
        sheetBlock.appendChild(heading);

        const row = document.createElement('div');
        // use charts-large so each chart takes full available width (one per row)
        row.className = 'charts-row charts-large';

        const makeChartCard = (title, dotClass, wrapClass, labels, values, color) => {
            if (!labels.length || !values.length) return null;
            const wrap = document.createElement('div');
            wrap.className = `chart-wrap ${wrapClass}`;
            const h = document.createElement('h4');
            h.innerHTML = `<span class="chart-dot ${dotClass}"></span>${title}`;
            wrap.appendChild(h);
            const container = document.createElement('div');
            container.className = 'chart-container chart-container-sm';
            // dynamically size horizontal bar chart: 36px per bar, min 300px
            container.style.height = Math.max(300, labels.length * 36) + 'px';
            const canvas = document.createElement('canvas');
            container.appendChild(canvas);
            wrap.appendChild(container);

            const chart = new Chart(canvas.getContext('2d'), {
                type: 'bar',
                data: {
                    labels,
                    datasets: [
                        {
                            data: values,
                            backgroundColor: color,
                            borderColor: color,
                            borderWidth: 1,
                            borderRadius: 6,
                            borderSkipped: false,
                        },
                    ],
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    indexAxis: 'y',
                    scales: {
                        x: {
                            beginAtZero: true,
                            grid: { color: 'rgba(148, 163, 184, 0.25)' },
                            ticks: { font: { size: 9 } },
                        },
                        y: {
                            grid: { display: false },
                            ticks: { font: { size: 8 }, autoSkip: false },
                        },
                    },
                    plugins: {
                        legend: { display: false },
                    },
                },
            });
            academicCharts.push(chart);
            return wrap;
        };

        const enrollLabels = topEnroll.map((r) => r.course);
        const enrollVals = topEnroll.map((r) => r.enrollment || 0);
        const excLabels = topExc.map((r) => r.course);
        const excVals = topExc.map((r) => r.excellence_rate || 0);
        const failLabels = topFail.map((r) => r.course);
        const failVals = topFail.map((r) => r.failure_rate || 0);
        const gpaLabels = topGpa.map((r) => r.course);
        const gpaVals = topGpa.map((r) => r.gpa_estimate || 0);

        const c1 = makeChartCard('Enrollment (Top 20)', 'chart-dot-blue', 'chart-enrollment', enrollLabels, enrollVals, '#0369a1dd');
        const c2 = makeChartCard('Excellence Rate %', 'chart-dot-orange', 'chart-excellence', excLabels, excVals, '#f97316dd');
        const c3 = makeChartCard('Failure Rate %', 'chart-dot-red', 'chart-failure', failLabels, failVals, '#dc2626dd');
        const c4 = makeChartCard('GPA by Course', 'chart-dot-teal', 'chart-gpa', gpaLabels, gpaVals, '#0d9488dd');

        [c1, c2, c3, c4].forEach((card) => {
            if (card) row.appendChild(card);
        });

        if (row.children.length) {
            sheetBlock.appendChild(row);
            charts.appendChild(sheetBlock);
        }
    });
}

function renderPredictive(result) {
    const summary = document.getElementById('prediction-summary');
    const container = document.getElementById('predictive-cards');
    if (summary) summary.innerHTML = '';
    if (container) container.innerHTML = '';
    const preds = result.predictions || {};
    if (!Object.keys(preds).length) {
        if (summary) summary.textContent = 'Predictive risk indicators will appear here.';
        return;
    }

    // summary card: overall average risk & quality
    const values = Object.values(preds);
    const avgQuality =
        values.length > 0
            ? values.reduce((a, b) => a + ((b.predicted_quality_score || 0) * 100), 0) /
              values.length
            : null;
    const avgRisk =
        values.length > 0
            ? values.reduce((a, b) => a + (b.risk_probability || 0), 0) / values.length
            : null;
    if (summary) {
        const box = document.createElement('div');
        box.className = 'prediction-summary-box';
        const qualityText =
            avgQuality != null ? `${avgQuality.toFixed(1)} / 100` : '—';
        const riskPct =
            avgRisk != null ? `${(avgRisk * 100).toFixed(1)}%` : '—';
        box.innerHTML = `<h4>Program Outlook</h4>
            <p class="outlook">Average predicted data quality: <strong>${qualityText}</strong>, with overall risk probability around <strong>${riskPct}</strong>.</p>`;
        summary.appendChild(box);
    }

    Object.entries(preds).forEach(([sheet, p]) => {
        const card = document.createElement('div');
        card.className = 'kpi-card predictive-card';
        const q = p.predicted_quality_score != null ? (p.predicted_quality_score * 100).toFixed(1) + '%' : '—';
        const r = p.risk_probability != null ? (p.risk_probability * 100).toFixed(1) + '%' : '—';
        let outlook = p.outlook || null;
        if (!outlook) {
            if (p.risk_probability != null) {
                if (p.risk_probability >= 0.6) outlook = 'High risk';
                else if (p.risk_probability >= 0.35) outlook = 'Watch closely';
                else outlook = 'Stable';
            } else {
                outlook = 'Stable';
            }
        }
        const predH3 = document.createElement('h3');
        predH3.textContent = sheet;
        card.appendChild(predH3);
        const nextGpa = p.next_semester_gpa_estimate != null
            ? `<p><span>Next semester GPA est.</span> ${escapeHtml(p.next_semester_gpa_estimate.toFixed(2))}</p>`
            : '';
        card.insertAdjacentHTML('beforeend',
            `<p><span>Predicted quality score</span> ${escapeHtml(q)}</p>` +
            `<p><span>Risk probability</span> ${escapeHtml(r)}</p>` +
            nextGpa +
            `<p class="prediction-note">Outlook: ${escapeHtml(outlook)}</p>`);
        container?.appendChild(card);
    });
}

function renderForecast(result) {
    if (typeof renderQaForecast === 'function') {
        renderQaForecast('forecast-container', result && result.trend_forecast);
    }
}

function renderCoursePlans(result) {
    const container = document.getElementById('course-plans');
    if (!container) return;
    container.innerHTML = '';
    const plans = result.course_plans || {};
    if (Object.keys(plans).length === 0) {
        container.innerHTML = '<p class="section-desc">Course action plans will appear here.</p>';
        return;
    }

    Object.entries(plans).forEach(([sheet, arr]) => {
        const sect = document.createElement('div');
        sect.className = 'plan-sheet-section';
        const heading = document.createElement('h4');
        heading.textContent = sheet;
        sect.appendChild(heading);

        arr.forEach((p) => {
            const card = document.createElement('div');
            let riskClass = 'risk-low';
            if (p.risk_level === 'high') riskClass = 'risk-high';
            else if (p.risk_level === 'medium') riskClass = 'risk-medium';
            card.className = `plan-card ${riskClass}`;

            const courseTitle = document.createElement('div');
            courseTitle.className = 'plan-course';
            courseTitle.textContent = p.course;

            const meta = document.createElement('div');
            meta.className = 'plan-meta';
            const riskTxt =
                p.risk_percent != null ? `${p.risk_percent.toFixed(1)}% risk` : 'Risk score N/A';
            const failTxt =
                p.failure_rate != null ? `Failure: ${p.failure_rate.toFixed(1)}%` : '';
            const gpaTxt =
                p.gpa_estimate != null ? `GPA: ${p.gpa_estimate.toFixed(2)}` : '';
            const trendTxt = p.predicted_trend ? `Trend: ${p.predicted_trend}` : '';
            meta.textContent = [riskTxt, failTxt, gpaTxt, trendTxt].filter(Boolean).join(' · ');

            const list = document.createElement('ul');
            list.className = 'plan-actions';
            (p.action_plan || []).forEach((act) => {
                const li = document.createElement('li');
                li.textContent = act;
                list.appendChild(li);
            });

            card.appendChild(courseTitle);
            card.appendChild(meta);
            card.appendChild(list);
            sect.appendChild(card);
        });

        container.appendChild(sect);
    });
}

// collapse/expand behaviour for dashboard sections
function initializeSectionToggles() {
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

function openAllSections() {
    document.querySelectorAll('.section-collapsible').forEach((sect) => {
        sect.classList.remove('collapsed');
        const btn = sect.querySelector('.section-toggle');
        if (btn) btn.setAttribute('aria-expanded', 'true');
    });
}

// initialize toggles right away
initializeSectionToggles();

// drag-and-drop for upload zone
(function () {
    const zone = document.getElementById('upload-zone');
    if (!zone) return;

    zone.addEventListener('dragover', (e) => { e.preventDefault(); zone.classList.add('drag-over'); });
    zone.addEventListener('dragleave', () => zone.classList.remove('drag-over'));
    zone.addEventListener('drop', (e) => {
        e.preventDefault();
        zone.classList.remove('drag-over');
        const files = Array.from(e.dataTransfer?.files || []).filter((f) => f.name.toLowerCase().endsWith('.xlsx'));
        if (!files.length) return;
        _showUploadHint(files);
        _runUpload(files);
    });
}());

// translation toggle on dashboard page
const dashTranslateBtn = document.getElementById('translateBtn');
if (dashTranslateBtn) {
    dashTranslateBtn.addEventListener('click', () => {
        const btn = dashTranslateBtn;
        if (btn.innerText === 'العربية') {
            document.getElementById('mainTitle').innerText = 'لوحة معلومات أداء أكاديمي';
            document.getElementById('uploadTitle').innerText = 'تحميل ملف إكسل';
            btn.innerText = 'English';
        } else {
            document.getElementById('mainTitle').innerText = 'Academic Performance Intelligence Dashboard';
            document.getElementById('uploadTitle').innerText = 'Upload Excel File';
            btn.innerText = 'العربية';
        }
    });
}
