// Program Report Page Logic

const apiUrlProgram = window.location.origin || '';

/** Escape untrusted text before inserting into innerHTML. */
function escapeHtmlPR(str) {
    const d = document.createElement('div');
    d.textContent = String(str ?? '');
    return d.innerHTML;
}

let programLastResult = null;
let programSummary = null;

function uploadProgramFile(file) {
  const form = new FormData();
  form.append('file', file);
  return fetch(`${apiUrlProgram}/upload-excel`, {
    method: 'POST',
    body: form,
  }).then(async (resp) => {
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({ detail: resp.statusText }));
      throw new Error(err.detail || `HTTP ${resp.status}`);
    }
    return resp.json();
  });
}

function setProgramLoading(loading) {
  const loadingEl = document.getElementById('program-loading');
  const zone = document.getElementById('program-upload-zone');
  const input = document.getElementById('programExcelInput');
  if (loading) {
    if (loadingEl) loadingEl.hidden = false;
    if (zone) zone.classList.add('uploading');
    if (input) input.disabled = true;
  } else {
    if (loadingEl) loadingEl.hidden = true;
    if (zone) zone.classList.remove('uploading');
    if (input) input.disabled = false;
  }
}

function buildProgramSummary(result) {
  const academic = (result && result.academic_analytics) || {};
  const kpis = (result && result.metadata && result.metadata.kpis) || {};
  const predictions = (result && result.predictions) || {};
  const courseRisk = (result && result.course_risk) || {};

  let totalStudents = 0;
  const coursesSet = new Set();
  let gpaWeighted = 0;
  let gpaCount = 0;
  let failWeighted = 0;
  let excWeighted = 0;

  const sheetReliability = [];

  Object.entries(academic).forEach(([sheet, data]) => {
    const allCourses = data.all_courses || [];

    if (allCourses.length) {
      // Wide-format: we have per-course aggregates, so use them directly
      allCourses.forEach((row) => {
        const total = row.total || row.enrollment || 0;
        const fr = row.failure_rate || 0;
        const er = row.excellence_rate || 0;
        const g = row.gpa_estimate || 0;
        if (total > 0) {
          totalStudents += total;
          gpaCount += total;
          failWeighted += (fr / 100) * total;
          excWeighted += (er / 100) * total;
          gpaWeighted += g * total;
        }
        if (row.course) {
          coursesSet.add(row.course);
        }
      });
    } else {
      // Fallback for long format / legacy: use top20 lists
      const enrollment = data.top20_enrollment || [];
      const failure = data.top20_failure_rate || [];
      const excellence = data.top20_excellence_rate || [];
      const gpaList = data.top20_gpa_per_course || [];

      enrollment.forEach((row) => {
        totalStudents += row.enrollment || 0;
        if (row.course) coursesSet.add(row.course);
      });

      failure.forEach((row) => {
        const total = row.total || 0;
        const rate = row.failure_rate || 0;
        failWeighted += (rate / 100) * total;
        gpaCount += total;
        if (row.course) coursesSet.add(row.course);
      });

      excellence.forEach((row) => {
        const total = row.total || 0;
        const rate = row.excellence_rate || 0;
        excWeighted += (rate / 100) * total;
        if (row.course) coursesSet.add(row.course);
      });

      gpaList.forEach((row) => {
        const total = row.total || 0;
        const g = row.gpa_estimate || 0;
        gpaWeighted += g * total;
      });
    }

    const sheetKpi = kpis[sheet];
    if (sheetKpi) {
      const rel = sheetKpi.composite_reliability_index ?? null;
      if (rel != null) sheetReliability.push(rel);
    }
  });

  const totalCourses = coursesSet.size;
  const overallFailureRate =
    gpaCount > 0 ? (failWeighted / gpaCount) * 100 : null;
  const overallExcellenceRate =
    gpaCount > 0 ? (excWeighted / gpaCount) * 100 : null;
  const avgGpa = gpaCount > 0 ? gpaWeighted / gpaCount : null;
  const qualityScore =
    sheetReliability.length > 0
      ? (sheetReliability.reduce((a, b) => a + b, 0) / sheetReliability.length) * 100
      : null;

  // GPA trend per sheet
  const gpaTrendLabels = [];
  const gpaTrendValues = [];
  const qualityTrendLabels = [];
  const qualityTrendValues = [];

  Object.keys(academic)
    .sort()
    .forEach((sheet) => {
      const data = academic[sheet];
      const gpaList = (data.all_courses && data.all_courses.length)
        ? data.all_courses
        : (data.top20_gpa_per_course || []);
      const sheetTotal = gpaList.reduce((acc, r) => acc + (r.total || r.enrollment || 0), 0);
      const sheetGpaWeighted = gpaList.reduce(
        (acc, r) => acc + (r.gpa_estimate || 0) * (r.total || r.enrollment || 0),
        0,
      );
      const sheetAvgGpa =
        sheetTotal > 0 ? sheetGpaWeighted / sheetTotal : null;
      gpaTrendLabels.push(sheet);
      gpaTrendValues.push(sheetAvgGpa);

      const sheetKpi = kpis[sheet];
      if (sheetKpi) {
        const rel = sheetKpi.composite_reliability_index ?? null;
        qualityTrendLabels.push(sheet);
        qualityTrendValues.push(rel != null ? rel * 100 : null);
      }
    });

  // Enrollment comparison: top courses across program
  const enrollmentAgg = {};
  Object.values(academic).forEach((data) => {
    const src = (data.all_courses && data.all_courses.length)
      ? data.all_courses
      : (data.top20_enrollment || []);
    src.forEach((row) => {
      const c = row.course;
      if (!c) return;
      enrollmentAgg[c] = (enrollmentAgg[c] || 0) + (row.enrollment || 0);
    });
  });
  const enrollmentSorted = Object.entries(enrollmentAgg)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 15);

  // Risk heatmap and high-risk courses
  const riskMatrix = [];
  const highRiskCourses = [];
  Object.entries(courseRisk).forEach(([sheet, data]) => {
    const cr = (data && data.course_risk) || {};
    Object.entries(cr).forEach(([course, risk]) => {
      riskMatrix.push({ sheet, course, risk: (risk || 0) * 100 });
      if (risk >= 0.6) {
        highRiskCourses.push({ course, risk: (risk || 0) * 100 });
      }
    });
  });
  highRiskCourses.sort((a, b) => b.risk - a.risk);

  // Stability index from reliability spread
  let stabilityIndex = null;
  let stabilityNote = '';
  if (sheetReliability.length > 1) {
    const meanRel =
      sheetReliability.reduce((a, b) => a + b, 0) / sheetReliability.length;
    const variance =
      sheetReliability.reduce(
        (acc, r) => acc + Math.pow(r - meanRel, 2),
        0,
      ) / sheetReliability.length;
    const std = Math.sqrt(variance);
    // Higher std => lower stability
    const raw = 1 - Math.min(std / 0.3, 1);
    stabilityIndex = Math.round(raw * 100);
    if (stabilityIndex >= 80) {
      stabilityNote = 'Data quality is stable across semesters/sheets.';
    } else if (stabilityIndex >= 55) {
      stabilityNote =
        'Moderate variation in data quality across semesters/sheets.';
    } else {
      stabilityNote =
        'Significant variation in data quality; investigate data collection processes.';
    }
  }

  // Overall risk level (from predictions)
  const riskValues = Object.values(predictions).map(
    (p) => p.risk_probability || 0,
  );
  const avgRiskProb =
    riskValues.length > 0
      ? riskValues.reduce((a, b) => a + b, 0) / riskValues.length
      : 0;

  // Predict next semester GPA: adjust by risk
  let predictedGpa = null;
  if (avgGpa != null) {
    const adj = 1 - Math.min(avgRiskProb * 0.3, 0.25);
    predictedGpa = avgGpa * adj;
  }

  return {
    totalStudents,
    totalCourses,
    avgGpa: avgGpa != null ? avgGpa.toFixed(2) : null,
    overallFailureRate:
      overallFailureRate != null ? overallFailureRate.toFixed(1) : null,
    overallExcellenceRate:
      overallExcellenceRate != null ? overallExcellenceRate.toFixed(1) : null,
    qualityScore: qualityScore != null ? qualityScore.toFixed(1) : null,
    gpaTrendLabels,
    gpaTrendValues,
    qualityTrendLabels,
    qualityTrendValues,
    enrollmentSorted,
    riskMatrix,
    highRiskCourses,
    stabilityIndex,
    stabilityNote,
    avgRiskProb,
    predictedGpa: predictedGpa != null ? predictedGpa.toFixed(2) : null,
    // raw aggregates for manual-denominator override
    _computedDenominator: gpaCount,
    _gpaWeightedSum: gpaWeighted,
    _failCount: failWeighted,
    _excellentCount: excWeighted,
    predictions,
    academic,
  };
}

function setText(id, value, suffix = '') {
  const el = document.getElementById(id);
  if (!el) return;
  el.textContent = value != null ? `${value}${suffix}` : '—';
}

function getProgramManualTotal() {
  const overrideInput = document.getElementById('progTotalStudentsOverride');
  if (!overrideInput) return null;
  if (overrideInput.value === '') return null;
  const v = parseInt(overrideInput.value, 10);
  if (Number.isNaN(v) || v < 0) return null;
  return v;
}

function deriveProgramKpis(summary) {
  const manualTotal = getProgramManualTotal();

  // لو مفيش رقم يدوي، نرجّع القيم الجاهزة من الملخّص كما هي
  if (manualTotal == null) {
    return {
      totalStudents: summary.totalStudents,
      avgGpa: summary.avgGpa,
      overallFailureRate: summary.overallFailureRate,
      overallExcellenceRate: summary.overallExcellenceRate,
      predictedGpa: summary.predictedGpa,
    };
  }

  const displayTotalStudents = manualTotal;
  const denom = manualTotal || 0;

  // الـ GPA لا يتغيّر مع الرقم اليدوي، نستخدم المتوسط المحسوب من الداتا كما هو
  let avgGpaNum =
    summary.avgGpa != null ? parseFloat(summary.avgGpa) : null;
  if (avgGpaNum != null) {
    // GPA must be within [0, 4]
    avgGpaNum = Math.min(4, Math.max(0, avgGpaNum));
  }

  let failureRateNum =
    denom > 0 ? ((summary._failCount || 0) / denom) * 100 : null;
  if (failureRateNum != null) {
    // percentage [0, 100]
    failureRateNum = Math.min(100, Math.max(0, failureRateNum));
  }

  let excellenceRateNum =
    denom > 0 ? ((summary._excellentCount || 0) / denom) * 100 : null;
  if (excellenceRateNum != null) {
    excellenceRateNum = Math.min(100, Math.max(0, excellenceRateNum));
  }

  const adj = 1 - Math.min((summary.avgRiskProb || 0) * 0.3, 0.25);
  let predictedGpaNum =
    avgGpaNum != null ? avgGpaNum * adj : null;
  if (predictedGpaNum != null) {
    predictedGpaNum = Math.min(4, Math.max(0, predictedGpaNum));
  }

  return {
    totalStudents: displayTotalStudents,
    avgGpa: avgGpaNum != null ? avgGpaNum.toFixed(2) : null,
    overallFailureRate: failureRateNum != null ? failureRateNum.toFixed(1) : null,
    overallExcellenceRate: excellenceRateNum != null ? excellenceRateNum.toFixed(1) : null,
    predictedGpa: predictedGpaNum != null ? predictedGpaNum.toFixed(2) : null,
  };
}

function renderProgramKpis(summary) {
  const derived = deriveProgramKpis(summary);
  setText('progTotalStudents', derived.totalStudents);
  setText('progTotalCourses', summary.totalCourses);
  setText('progAvgGpa', derived.avgGpa);
  setText('progFailureRate', derived.overallFailureRate, ' %');
  setText('progExcellenceRate', derived.overallExcellenceRate, ' %');
  setText('progQualityScore', summary.qualityScore, ' / 100');
}

let progGpaTrendChart = null;
let progEnrollmentChart = null;
let progQualityTrendChart = null;

function renderProgramCharts(summary) {
  if (typeof Chart === 'undefined') return;

  const ctxGpa = document.getElementById('progGpaTrendChart');
  const ctxEnroll = document.getElementById('progEnrollmentChart');
  const ctxQual = document.getElementById('progQualityTrendChart');

  if (progGpaTrendChart) progGpaTrendChart.destroy();
  if (progEnrollmentChart) progEnrollmentChart.destroy();
  if (progQualityTrendChart) progQualityTrendChart.destroy();

  if (ctxGpa) {
    progGpaTrendChart = new Chart(ctxGpa.getContext('2d'), {
      type: 'line',
      data: {
        labels: summary.gpaTrendLabels,
        datasets: [
          {
            label: 'Average GPA',
            data: summary.gpaTrendValues,
            borderColor: '#0ea5e9',
            backgroundColor: 'rgba(14, 165, 233, 0.15)',
            tension: 0.3,
            fill: true,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          y: { beginAtZero: true, max: 4.0 },
          x: { grid: { display: false } },
        },
        plugins: {
          legend: { position: 'bottom', labels: { boxWidth: 14, boxHeight: 14 } },
        },
      },
    });
  }

  if (ctxEnroll) {
    const labels = summary.enrollmentSorted.map(([course]) => course);
    const values = summary.enrollmentSorted.map(([, val]) => val);
    // dynamically size horizontal bar chart: 36px per bar, min 300px
    const enrollContainer = ctxEnroll.closest('.chart-container') || ctxEnroll.parentElement;
    if (enrollContainer) enrollContainer.style.height = Math.max(300, labels.length * 36) + 'px';
    progEnrollmentChart = new Chart(ctxEnroll.getContext('2d'), {
      type: 'bar',
      data: {
        labels,
        datasets: [
          {
            label: 'Enrollment',
            data: values,
            backgroundColor: '#0369a1dd',
            borderColor: '#0369a1',
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
            ticks: { font: { size: 10 } },
          },
          y: {
            grid: { display: false },
            ticks: { font: { size: 9 }, autoSkip: false },
          },
        },
        plugins: {
          legend: { display: false },
        },
      },
    });
  }

  if (ctxQual) {
    progQualityTrendChart = new Chart(ctxQual.getContext('2d'), {
      type: 'line',
      data: {
        labels: summary.qualityTrendLabels,
        datasets: [
          {
            label: 'Reliability Index',
            data: summary.qualityTrendValues,
            borderColor: '#22c55e',
            backgroundColor: 'rgba(34, 197, 94, 0.15)',
            tension: 0.3,
            fill: true,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          y: { beginAtZero: true, max: 100 },
          x: { grid: { display: false } },
        },
        plugins: {
          legend: { position: 'bottom', labels: { boxWidth: 14, boxHeight: 14 } },
        },
      },
    });
  }
}

function renderProgramRiskAnalysis(summary) {
  const topRiskUl = document.getElementById('progTopRiskCourses');
  const incFailUl = document.getElementById('progIncreasingFailureCourses');
  const gpaDeclineUl = document.getElementById('progGpaDeclineCourses');
  const volUl = document.getElementById('progVolatilityCourses');

  if (topRiskUl) {
    topRiskUl.innerHTML = '';
    summary.highRiskCourses.slice(0, 10).forEach((item) => {
      const li = document.createElement('li');
      li.textContent = `${item.course}: ${item.risk.toFixed(1)}% predicted risk`;
      topRiskUl.appendChild(li);
    });
    if (!topRiskUl.children.length) {
      const li = document.createElement('li');
      li.textContent = 'No high-risk courses detected above the configured threshold.';
      topRiskUl.appendChild(li);
    }
  }

  // Increasing failure trend & GPA decline based on sheet-level lists
  const academic = summary.academic;
  const failureByCourseSheet = {};
  const gpaByCourseSheet = {};

  Object.entries(academic).forEach(([sheet, data]) => {
    (data.top20_failure_rate || []).forEach((row) => {
      const c = row.course;
      if (!c) return;
      if (!failureByCourseSheet[c]) failureByCourseSheet[c] = {};
      failureByCourseSheet[c][sheet] = row.failure_rate || 0;
    });
    (data.top20_gpa_per_course || []).forEach((row) => {
      const c = row.course;
      if (!c) return;
      if (!gpaByCourseSheet[c]) gpaByCourseSheet[c] = {};
      gpaByCourseSheet[c][sheet] = row.gpa_estimate || 0;
    });
  });

  const incrFailureCourses = [];
  Object.entries(failureByCourseSheet).forEach(([course, perSheet]) => {
    const entries = Object.entries(perSheet).sort((a, b) =>
      a[0].localeCompare(b[0]),
    );
    if (entries.length < 2) return;
    const first = entries[0][1];
    const last = entries[entries.length - 1][1];
    if (last > first + 5) {
      incrFailureCourses.push({
        course,
        from: first,
        to: last,
      });
    }
  });
  incrFailureCourses.sort((a, b) => b.to - b.from - (a.to - a.from));

  if (incFailUl) {
    incFailUl.innerHTML = '';
    incrFailureCourses.slice(0, 8).forEach((item) => {
      const li = document.createElement('li');
      li.textContent = `${item.course}: failure rate increased from ${item.from.toFixed(
        1,
      )}% to ${item.to.toFixed(1)}%.`;
      incFailUl.appendChild(li);
    });
    if (!incFailUl.children.length) {
      const li = document.createElement('li');
      li.textContent =
        'No courses with a pronounced increase in failure rate were detected.';
      incFailUl.appendChild(li);
    }
  }

  const gpaDeclineCourses = [];
  Object.entries(gpaByCourseSheet).forEach(([course, perSheet]) => {
    const entries = Object.entries(perSheet).sort((a, b) =>
      a[0].localeCompare(b[0]),
    );
    if (entries.length < 2) return;
    const first = entries[0][1];
    const last = entries[entries.length - 1][1];
    if (last + 0.2 < first) {
      gpaDeclineCourses.push({ course, from: first, to: last });
    }
  });
  gpaDeclineCourses.sort((a, b) => a.to - b.to);

  if (gpaDeclineUl) {
    gpaDeclineUl.innerHTML = '';
    gpaDeclineCourses.slice(0, 8).forEach((item) => {
      const li = document.createElement('li');
      li.textContent = `${item.course}: GPA decreased from ${item.from.toFixed(
        2,
      )} to ${item.to.toFixed(2)}.`;
      gpaDeclineUl.appendChild(li);
    });
    if (!gpaDeclineUl.children.length) {
      const li = document.createElement('li');
      li.textContent =
        'No clear GPA decline patterns were detected at the course level.';
      gpaDeclineUl.appendChild(li);
    }
  }

  // Volatility ranking from GPA variance
  const volAgg = [];
  Object.values(academic).forEach((data) => {
    (data.top20_gpa_per_course || []).forEach((row) => {
      if (row.volatility_index != null) {
        volAgg.push({
          course: row.course,
          volatility: row.volatility_index,
        });
      }
    });
  });
  volAgg.sort((a, b) => b.volatility - a.volatility);

  if (volUl) {
    volUl.innerHTML = '';
    volAgg.slice(0, 8).forEach((item) => {
      const li = document.createElement('li');
      li.textContent = `${item.course}: volatility index ${item.volatility.toFixed(
        3,
      )}.`;
      volUl.appendChild(li);
    });
    if (!volUl.children.length) {
      const li = document.createElement('li');
      li.textContent =
        'No volatility information was available for the current dataset.';
      volUl.appendChild(li);
    }
  }
}

function renderRiskHeatmap(summary) {
  const container = document.getElementById('progRiskHeatmap');
  if (!container) return;
  container.innerHTML = '';

  if (!summary.riskMatrix.length) {
    container.textContent =
      'Risk heatmap is not available because course-level risk scores were not computed.';
    return;
  }

  const sheets = Array.from(
    new Set(summary.riskMatrix.map((r) => r.sheet)),
  ).sort();
  const courses = Array.from(
    new Set(summary.riskMatrix.map((r) => r.course)),
  ).sort();

  const table = document.createElement('table');
  table.className = 'heatmap-table';

  const thead = document.createElement('thead');
  const headRow = document.createElement('tr');
  headRow.appendChild(document.createElement('th'));
  sheets.forEach((s) => {
    const th = document.createElement('th');
    th.textContent = s;
    headRow.appendChild(th);
  });
  thead.appendChild(headRow);
  table.appendChild(thead);

  const tbody = document.createElement('tbody');
  courses.forEach((course) => {
    const tr = document.createElement('tr');
    const th = document.createElement('th');
    th.textContent = course;
    tr.appendChild(th);
    sheets.forEach((sheet) => {
      const td = document.createElement('td');
      const rec = summary.riskMatrix.find(
        (r) => r.course === course && r.sheet === sheet,
      );
      const risk = rec ? rec.risk : null;
      if (risk != null) {
        td.textContent = risk.toFixed(0);
        const intensity = Math.min(risk / 100, 1);
        const r = 248;
        const g = Math.round(250 - intensity * 120);
        const b = Math.round(252 - intensity * 160);
        td.style.backgroundColor = `rgb(${r},${g},${b})`;
      } else {
        td.textContent = '—';
      }
      tr.appendChild(td);
    });
    tbody.appendChild(tr);
  });
  table.appendChild(tbody);
  container.appendChild(table);
}

function renderPredictiveSection(summary) {
  const derived = deriveProgramKpis(summary);
  setText('progPredictedGpa', derived.predictedGpa);
  const gpaNote = document.getElementById('progPredictedGpaNote');
  if (gpaNote) {
    if (derived.predictedGpa == null) {
      gpaNote.textContent =
        'Predicted GPA could not be estimated from the current dataset.';
    } else if (summary.avgRiskProb >= 0.6) {
      gpaNote.textContent =
        'Prediction assumes a conservative scenario due to elevated program-wide risk.';
    } else if (summary.avgRiskProb >= 0.3) {
      gpaNote.textContent =
        'Prediction assumes moderate stability with some risk-sensitive courses.';
    } else {
      gpaNote.textContent =
        'Prediction assumes stable program conditions with generally good reliability.';
    }
  }

  const highRiskList = document.getElementById(
    'progPredictedHighRiskCourses',
  );
  if (highRiskList) {
    highRiskList.innerHTML = '';
    summary.highRiskCourses.slice(0, 8).forEach((item) => {
      const li = document.createElement('li');
      li.textContent = `${item.course}: ${item.risk.toFixed(
        1,
      )}% predicted risk.`;
      highRiskList.appendChild(li);
    });
    if (!highRiskList.children.length) {
      const li = document.createElement('li');
      li.textContent =
        'No courses exceed the high-risk prediction threshold in the current dataset.';
      highRiskList.appendChild(li);
    }
  }

  setText('progStabilityIndex', summary.stabilityIndex);
  const stabilityNoteEl = document.getElementById('progStabilityNote');
  if (stabilityNoteEl) {
    stabilityNoteEl.textContent =
      summary.stabilityNote ||
      'Stability index requires at least two sheets with reliability metrics.';
  }
}

function renderExecutiveSummary(summary) {
  const container = document.getElementById('progExecutiveSummary');
  if (!container) return;
  container.innerHTML = '';

  const derived = deriveProgramKpis(summary);

  const p1 = document.createElement('p');
  p1.textContent = `The uploaded dataset describes a program with approximately ${derived.totalStudents.toLocaleString()} student-course registrations distributed across ${summary.totalCourses} distinct courses. The current average grade point average (GPA) is ${
    derived.avgGpa ?? 'N/A'
  }, with an overall failure rate of ${
    derived.overallFailureRate ?? 'N/A'
  }% and an excellence rate of ${
    derived.overallExcellenceRate ?? 'N/A'
  }%.`;

  const p2 = document.createElement('p');
  p2.textContent = `From a data quality perspective, the composite reliability score is ${
    summary.qualityScore ?? 'N/A'
  } out of 100, indicating ${
    summary.qualityScore != null && parseFloat(summary.qualityScore) >= 80
      ? 'a strong and consistent reporting process.'
      : summary.qualityScore != null &&
        parseFloat(summary.qualityScore) >= 60
      ? 'an acceptable but improvable level of robustness.'
      : 'areas of concern that warrant closer review of data collection and validation procedures.'
  }`;

  const p3 = document.createElement('p');
  const riskPct = summary.avgRiskProb != null ? (summary.avgRiskProb * 100).toFixed(1) : '0.0';
  p3.textContent = `Predictive indicators estimate a next-semester GPA of ${
    derived.predictedGpa ?? 'N/A'
  }, under a program-wide risk level of approximately ${riskPct}%. High-risk courses identified in the analysis should be prioritised for targeted pedagogical interventions, curriculum refinement, and enhanced academic advising to safeguard student success.`;

  const p4 = document.createElement('p');
  p4.textContent =
    'It is recommended that the program monitoring committee reviews courses with increasing failure trends and declining GPA profiles, integrates these findings into periodic quality assurance meetings, and documents follow-up actions within the formal program improvement plan.';

  [p1, p2, p3, p4].forEach((p) => container.appendChild(p));
}

function renderProgramStrategicStats(programStatistics) {
  const container = document.getElementById('progStrategicStatsContainer');
  if (!container) return;
  container.innerHTML = '';
  if (!programStatistics || typeof programStatistics !== 'object') return;

  function card(title, items) {
    const el = document.createElement('div');
    el.className = 'kpi-card advanced-stat-card';
    let html = '<h3>' + escapeHtmlPR(title) + '</h3>';
    items.forEach(function (it) {
      html += '<p><span>' + escapeHtmlPR(it.label) + '</span> ' + (it.value != null ? escapeHtmlPR(it.value) : '—') + '</p>';
    });
    el.innerHTML = html;
    container.appendChild(el);
  }

  const ineq = programStatistics.inequality_balance || {};
  if (Object.keys(ineq).length) {
    const vd = ineq.variance_decomposition || {};
    card('Inequality & Balance', [
      { label: 'GPA Gini inequality', value: ineq.gpa_inequality_index != null ? ineq.gpa_inequality_index.toFixed(3) : null },
      { label: 'Difficulty dispersion', value: ineq.course_difficulty_dispersion != null ? ineq.course_difficulty_dispersion.toFixed(2) : null },
      { label: 'Academic equity score', value: ineq.academic_equity_score != null ? ineq.academic_equity_score.toFixed(3) : null },
      { label: 'Between-course variance', value: vd.between_course_variance != null ? vd.between_course_variance.toFixed(4) : null },
      { label: 'Within-course variance', value: vd.within_course_variance != null ? vd.within_course_variance.toFixed(4) : null },
    ]);
  }
  const long = programStatistics.longitudinal_growth || {};
  if (Object.keys(long).length) {
    card('Longitudinal Growth', [
      { label: 'CAGR GPA (per sheet)', value: long.cagr_gpa != null ? (long.cagr_gpa * 100).toFixed(2) + '%' : null },
      { label: 'Failure trend acceleration', value: long.failure_trend_acceleration != null ? long.failure_trend_acceleration.toFixed(3) : null },
      { label: 'Growth rate (excellence)', value: long.growth_rate_excellence != null ? (long.growth_rate_excellence * 100).toFixed(1) + '%' : null },
      { label: 'Program momentum score', value: long.program_momentum_score != null ? long.program_momentum_score.toFixed(3) : null },
    ]);
  }
  const ci = programStatistics.cohort_intelligence || {};
  if (ci.cohort_retention_rate != null || ci.dropout_risk_probability != null) {
    card('Cohort Intelligence', [
      { label: 'Estimated retention rate', value: ci.cohort_retention_rate != null ? (ci.cohort_retention_rate * 100).toFixed(1) + '%' : null },
      { label: 'Dropout risk probability', value: ci.dropout_risk_probability != null ? (ci.dropout_risk_probability * 100).toFixed(1) + '%' : null },
      { label: 'Academic recovery rate', value: ci.academic_recovery_rate != null ? (ci.academic_recovery_rate * 100).toFixed(1) + '%' : null },
    ]);
  }
  const mc = programStatistics.monte_carlo_simulation || {};
  if (Object.keys(mc).length) {
    card('Monte Carlo (1,000 runs)', [
      { label: 'Simulated mean final GPA', value: mc.simulated_mean_final_gpa != null ? mc.simulated_mean_final_gpa.toFixed(2) : null },
      { label: '5th percentile GPA', value: mc.percentile_5 != null ? mc.percentile_5.toFixed(2) : null },
      { label: '95th percentile GPA', value: mc.percentile_95 != null ? mc.percentile_95.toFixed(2) : null },
      { label: 'P(GPA < 2.0)', value: mc.p_below_2 != null ? (mc.p_below_2 * 100).toFixed(1) + '%' : null },
      { label: 'P(GPA >= 3.0)', value: mc.p_above_3 != null ? (mc.p_above_3 * 100).toFixed(1) + '%' : null },
      { label: 'Stress 95th % failure', value: mc.stress_test && mc.stress_test.stress_percentile_95 != null ? mc.stress_test.stress_percentile_95.toFixed(1) + '%' : null },
    ]);
  }
  const bench = programStatistics.benchmarking || {};
  if (Object.keys(bench).length) {
    card('Benchmarking', [
      { label: 'Program mean GPA', value: bench.program_mean_gpa != null ? bench.program_mean_gpa.toFixed(2) : null },
      { label: 'Z-score vs historical', value: bench.z_score_vs_historical != null ? bench.z_score_vs_historical.toFixed(2) : null },
    ]);
  }
}

function renderExecutiveCertificates(crossModule) {
  const container = document.getElementById('progExecutiveCertificates');
  if (!container) return;
  container.innerHTML = '';
  if (!crossModule || typeof crossModule !== 'object') return;

  function _esc(s) { const d = document.createElement('div'); d.textContent = String(s ?? ''); return d.innerHTML; }

  const inner = document.createElement('div');
  inner.className = 'executive-certificates-inner';

  // Bayesian quality posterior
  const bq = crossModule.bayesian_quality || {};
  if (bq.posterior_mean != null) {
    const p = document.createElement('p');
    p.className = 'certificate-line';
    const std = bq.posterior_std != null ? ` ± ${bq.posterior_std.toFixed(3)}` : '';
    p.innerHTML = '<strong>Bayesian quality posterior:</strong> ' +
      _esc((bq.posterior_mean * 100).toFixed(1)) + '% (reliability)' + _esc(std ? ` (std ${(bq.posterior_std * 100).toFixed(1)}%)` : '');
    inner.appendChild(p);
  }

  if (crossModule.risk_confidence_statement) {
    const p = document.createElement('p');
    p.className = 'certificate-line';
    p.innerHTML = '<strong>Risk confidence:</strong> ' + _esc(crossModule.risk_confidence_statement);
    inner.appendChild(p);
  }
  if (crossModule.institutional_stability_certificate_score != null) {
    const p = document.createElement('p');
    p.className = 'certificate-line';
    p.innerHTML = '<strong>Institutional stability certificate score:</strong> ' +
      _esc(crossModule.institutional_stability_certificate_score.toFixed(1)) + ' / 100';
    inner.appendChild(p);
  }
  if (crossModule.accreditation_readiness_probability != null) {
    const p = document.createElement('p');
    p.className = 'certificate-line';
    p.innerHTML = '<strong>Accreditation readiness probability:</strong> ' +
      _esc((crossModule.accreditation_readiness_probability * 100).toFixed(1)) + '%';
    inner.appendChild(p);
  }
  if (inner.children.length) {
    container.appendChild(inner);
  }
}

function renderProgramTrendForecast(result) {
  if (typeof renderQaForecast === 'function') {
    renderQaForecast('progTrendForecastContainer', result && result.trend_forecast);
  }
}

function exportProgramPdfFull() {
  if (!programLastResult) {
    alert('Please upload and analyze a file first.');
    return;
  }
  const container = document.getElementById('program-results');
  if (!container) return;

  const buttons = [
    document.getElementById('programExportPdfBtn'),
    document.getElementById('progExportPdfFullBtn'),
  ].filter(Boolean);
  buttons.forEach((b) => {
    b.disabled = true;
    b.textContent = 'Exporting...';
  });

  setTimeout(async () => {
    try {
      if (typeof html2canvas === 'undefined') throw new Error('html2canvas_not_loaded');
      const jspdfGlobal = window.jspdf || window.jsPDF;
      if (!jspdfGlobal) throw new Error('jspdf_not_loaded');

      const canvas = await html2canvas(container, {
        scale: 2,
        useCORS: true,
        backgroundColor: '#ffffff',
      });
      const JsPDFCtor = jspdfGlobal.jsPDF || jspdfGlobal;
      const pdf = new JsPDFCtor('p', 'mm', 'a4');
      const imgWidth = 210;
      const pageHeight = 297;
      const imgHeight = (canvas.height * imgWidth) / canvas.width;
      const src = canvas.toDataURL('image/png');
      const totalPages = Math.ceil(imgHeight / pageHeight) || 1;
      for (let p = 0; p < totalPages; p++) {
        if (p > 0) pdf.addPage();
        pdf.addImage(src, 'PNG', 0, -p * pageHeight, imgWidth, imgHeight);
      }
      const filename =
        'program-report-' + new Date().toISOString().slice(0, 10) + '.pdf';
      pdf.save(filename);
    } catch (err) {
      console.error(err);
      alert('An error occurred while exporting.');
    } finally {
      buttons.forEach((b) => {
        b.disabled = false;
        b.textContent =
          b.id === 'progExportPdfFullBtn'
            ? 'Full PDF Program Report'
            : 'Full PDF Report';
      });
    }
  }, 300);
}

function exportProgramPdfSummaryOnly() {
  if (!programLastResult || !programSummary) {
    alert('Please upload and analyze a file first.');
    return;
  }
  const summaryEl = document.getElementById('progExecutiveSummary');
  if (!summaryEl) return;

  try {
    const jspdfGlobal = window.jspdf || window.jsPDF;
    if (!jspdfGlobal) throw new Error('jspdf_not_loaded');
    const JsPDFCtor = jspdfGlobal.jsPDF || jspdfGlobal;
    const pdf = new JsPDFCtor('p', 'mm', 'a4');

    const lines = pdf.splitTextToSize(summaryEl.innerText, 180);
    pdf.text(lines, 15, 20);
    const filename =
      'program-executive-summary-' + new Date().toISOString().slice(0, 10) + '.pdf';
    pdf.save(filename);
  } catch (err) {
    console.error(err);
    alert('An error occurred while exporting the executive summary.');
  }
}

function exportProgramExcel() {
  if (!programSummary) {
    alert('Please upload and analyze a file first.');
    return;
  }
  const derived = deriveProgramKpis(programSummary);
  const rows = [
    ['Metric', 'Value'],
    ['Total Students', derived.totalStudents],
    ['Total Courses', programSummary.totalCourses],
    ['Average GPA', derived.avgGpa],
    ['Overall Failure Rate %', derived.overallFailureRate],
    ['Overall Excellence Rate %', derived.overallExcellenceRate],
    ['Overall Data Quality Score', programSummary.qualityScore],
    ['Stability Index', programSummary.stabilityIndex],
  ];
  rows.push([]);
  rows.push(['High-Risk Courses', 'Predicted Risk %']);
  programSummary.highRiskCourses.slice(0, 20).forEach((c) => {
    rows.push([c.course, c.risk.toFixed(1)]);
  });
  const csv = rows.map((r) => r.join(',')).join('\n');
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = 'program-analytics-summary.csv';
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

async function exportProgramDocx() {
  if (!programLastResult) {
    alert('Please upload and analyze a file first.');
    return;
  }
  const btn = document.getElementById('progExportDocxBtn');
  if (btn) { btn.disabled = true; btn.textContent = 'Generating…'; }

  const manualTotal = getProgramManualTotal();
  const payload = { analysis: programLastResult };
  if (manualTotal != null) payload.manual_total_students = manualTotal;

  try {
    const resp = await fetch(`${apiUrlProgram}/export-program-docx`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({ detail: resp.statusText }));
      throw new Error(err.detail || `HTTP ${resp.status}`);
    }
    const blob = await resp.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'Program_Report_2024_2025.docx';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  } catch (err) {
    console.error(err);
    alert('DOCX export failed: ' + err.message);
  } finally {
    if (btn) { btn.disabled = false; btn.textContent = '📄 Export DOCX Report'; }
  }
}

function renderProgramExplicitSections(res) {
  const ps = res.program_statistics || {};
  const cm = res.cross_module_executive || {};

  function setEl(id, val, suffix) {
    const el = document.getElementById(id);
    if (!el) return;
    el.textContent = val != null ? `${val}${suffix || ''}` : '—';
  }

  // ── Cohort Intelligence ──
  const ci = ps.cohort_intelligence || {};
  setEl('progCohortRetention', ci.cohort_retention_rate != null ? (ci.cohort_retention_rate * 100).toFixed(1) : null, ' %');
  setEl('progDropoutRisk', ci.dropout_risk_probability != null ? (ci.dropout_risk_probability * 100).toFixed(1) : null, ' %');
  setEl('progRecoveryRate', ci.academic_recovery_rate != null ? (ci.academic_recovery_rate * 100).toFixed(1) : null, ' %');

  // ── Variance Decomposition ──
  const ineq = ps.inequality_balance || {};
  const vd = ineq.variance_decomposition || {};
  setEl('progBetweenVar', vd.between_course_variance != null ? vd.between_course_variance.toFixed(4) : null);
  setEl('progWithinVar', vd.within_course_variance != null ? vd.within_course_variance.toFixed(4) : null);
  setEl('progGiniIndex', ineq.gpa_inequality_index != null ? ineq.gpa_inequality_index.toFixed(3) : null);
  setEl('progEquityScore', ineq.academic_equity_score != null ? ineq.academic_equity_score.toFixed(3) : null);

  // ── Bayesian Quality ──
  const bq = cm.bayesian_quality || {};
  setEl('progBayesianMean', bq.posterior_mean != null ? (bq.posterior_mean * 100).toFixed(1) : null, ' %');
  setEl('progBayesianStd', bq.posterior_std != null ? (bq.posterior_std * 100).toFixed(1) : null, ' %');
  setEl('progAccreditationReadiness', cm.accreditation_readiness_probability != null ? (cm.accreditation_readiness_probability * 100).toFixed(1) : null, ' %');
  setEl('progStabilityCert', cm.institutional_stability_certificate_score != null ? cm.institutional_stability_certificate_score.toFixed(1) : null, ' / 100');

  // ── Monte Carlo ──
  const mc = ps.monte_carlo_simulation || {};
  setEl('progMcMeanGpa', mc.simulated_mean_final_gpa != null ? mc.simulated_mean_final_gpa.toFixed(2) : null);
  setEl('progMcP5', mc.percentile_5 != null ? mc.percentile_5.toFixed(2) : null);
  setEl('progMcP95', mc.percentile_95 != null ? mc.percentile_95.toFixed(2) : null);
  setEl('progMcPBelow2', mc.p_below_2 != null ? (mc.p_below_2 * 100).toFixed(1) : null, ' %');
  setEl('progMcPAbove3', mc.p_above_3 != null ? (mc.p_above_3 * 100).toFixed(1) : null, ' %');
  const stressVal = mc.stress_test && mc.stress_test.stress_percentile_95 != null ? mc.stress_test.stress_percentile_95 : (mc.stress_test && mc.stress_test.worst_case_overall_failure_pct != null ? mc.stress_test.worst_case_overall_failure_pct : null);
  setEl('progMcStressFailure', stressVal != null ? (+stressVal).toFixed(1) : null, ' %');

  // ── Trend Forecast ──
  const fc = res.trend_forecast;
  const noteEl = document.getElementById('progFcNote');
  if (!fc || !fc.available) {
    setEl('progFcGpa', null);
    setEl('progFcFailure', null);
    setEl('progFcExcellence', null);
    if (noteEl) noteEl.textContent = fc?.reason || 'Trend forecast requires 2 or more uploaded sheets.';
  } else {
    if (noteEl) noteEl.textContent = `Based on ${fc.sheet_count} sheets — R² shown in parentheses.`;

    function setFcKpi(valId, trendId, fcData, unit) {
      if (!fcData) return;
      const next = fcData.predicted_next && fcData.predicted_next.length ? fcData.predicted_next[0] : null;
      const r2 = fcData.r_squared != null ? ` (R²=${(+fcData.r_squared).toFixed(2)})` : '';
      setEl(valId, next != null ? `${(+next).toFixed(2)} ${unit}` : null);
      const tEl = document.getElementById(trendId);
      if (tEl) {
        const dir = fcData.trend_direction || 'stable';
        tEl.textContent = `Trend: ${dir}${r2}`;
        tEl.style.color = dir === 'improving' ? '#16a34a' : dir === 'declining' || dir === 'worsening' ? '#dc2626' : '#64748b';
      }
    }
    setFcKpi('progFcGpa', 'progFcGpaTrend', fc.gpa_forecast, '/ 4.00');
    setFcKpi('progFcFailure', 'progFcFailureTrend', fc.failure_rate_forecast, '%');
    setFcKpi('progFcExcellence', 'progFcExcellenceTrend', fc.excellence_rate_forecast, '%');
  }

  // ── Longitudinal Growth ──
  const long = ps.longitudinal_growth || {};
  setEl('progCagrGpa', long.cagr_gpa != null ? (long.cagr_gpa * 100).toFixed(2) : null, ' %');
  setEl('progGrowthExcellence', long.growth_rate_excellence != null ? (long.growth_rate_excellence * 100).toFixed(1) : null, ' %');
  setEl('progFailAcceleration', long.failure_trend_acceleration != null ? long.failure_trend_acceleration.toFixed(3) : null);
  setEl('progMomentum', long.program_momentum_score != null ? long.program_momentum_score.toFixed(2) : null);
}

function handleAnalysisResult(res) {
  programLastResult = res;
  window.programLastResult = res;
  programSummary = buildProgramSummary(res);
  renderProgramKpis(programSummary);
  renderProgramCharts(programSummary);
  renderProgramRiskAnalysis(programSummary);
  renderRiskHeatmap(programSummary);
  renderPredictiveSection(programSummary);
  renderProgramExplicitSections(res);
  renderProgramStrategicStats(res.program_statistics || {});
  renderExecutiveCertificates(res.cross_module_executive || {});
  renderProgramTrendForecast(res);
  renderExecutiveSummary(programSummary);
  renderAnalyticsReport(res, programSummary);
}

function uploadProgramMultiFiles(formData) {
  return fetch(`${apiUrlProgram}/upload-excel-multi`, {
    method: 'POST',
    body: formData,
  }).then(async (resp) => {
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({ detail: resp.statusText }));
      throw new Error(err.detail || `HTTP ${resp.status}`);
    }
    return resp.json();
  });
}

function initMultiUpload() {
  // Tracks the selected File object per slot
  const multiSlots = {
    'sem1_old': null, 'sem1_new': null,
    'sem1_old_4': null, 'sem1_new_4': null,
    'sem2_old_4': null, 'sem2_new_4': null,
  };

  // Mode tab switching
  document.querySelectorAll('.upload-mode-tab').forEach((tab) => {
    tab.addEventListener('click', () => {
      document.querySelectorAll('.upload-mode-tab').forEach((t) => t.classList.remove('is-active'));
      tab.classList.add('is-active');
      const mode = tab.dataset.mode;
      ['single', 'multi2', 'multi4'].forEach((p) => {
        const panel = document.getElementById(`panel-${p}`);
        if (panel) panel.hidden = (p !== mode);
      });
    });
  });

  // Wire up a slot zone: file input + drag-drop + name display + state tracking
  function setupSlot(slotKey, zoneId, inputId, nameId) {
    const zone = document.getElementById(zoneId);
    const inp = document.getElementById(inputId);
    const nameEl = document.getElementById(nameId);
    if (!zone || !inp) return;

    function setFile(file) {
      if (!file || !file.name.toLowerCase().endsWith('.xlsx')) {
        alert('Please select an .xlsx file.');
        return;
      }
      multiSlots[slotKey] = file;
      zone.classList.add('has-file');
      if (nameEl) nameEl.textContent = file.name;
      updateAnalyzeBtns();
    }

    inp.addEventListener('change', (e) => {
      const f = e.target.files && e.target.files[0];
      if (f) setFile(f);
    });
    zone.addEventListener('dragover', (e) => { e.preventDefault(); zone.classList.add('drag-over'); });
    zone.addEventListener('dragleave', () => zone.classList.remove('drag-over'));
    zone.addEventListener('drop', (e) => {
      e.preventDefault();
      zone.classList.remove('drag-over');
      const f = e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files[0];
      if (f) setFile(f);
    });
  }

  // 2-file panel slots
  setupSlot('sem1_old',   'zone-sem1-old',   'input-sem1-old',   'fname-sem1-old');
  setupSlot('sem1_new',   'zone-sem1-new',   'input-sem1-new',   'fname-sem1-new');
  // 4-file panel slots
  setupSlot('sem1_old_4', 'zone-sem1-old-4', 'input-sem1-old-4', 'fname-sem1-old-4');
  setupSlot('sem1_new_4', 'zone-sem1-new-4', 'input-sem1-new-4', 'fname-sem1-new-4');
  setupSlot('sem2_old_4', 'zone-sem2-old-4', 'input-sem2-old-4', 'fname-sem2-old-4');
  setupSlot('sem2_new_4', 'zone-sem2-new-4', 'input-sem2-new-4', 'fname-sem2-new-4');

  function updateAnalyzeBtns() {
    const btn2 = document.getElementById('progMulti2AnalyzeBtn');
    const btn4 = document.getElementById('progMulti4AnalyzeBtn');
    if (btn2) btn2.disabled = !(multiSlots.sem1_old && multiSlots.sem1_new);
    if (btn4) btn4.disabled = !(
      multiSlots.sem1_old_4 && multiSlots.sem1_new_4 &&
      multiSlots.sem2_old_4 && multiSlots.sem2_new_4
    );
  }

  async function doMultiAnalyze(slots, btn) {
    const form = new FormData();
    for (const [field, file] of Object.entries(slots)) {
      if (file) form.append(field, file);
    }
    if (btn) { btn.disabled = true; btn.textContent = 'Analyzing…'; }
    setProgramLoading(true);
    try {
      const res = await uploadProgramMultiFiles(form);
      handleAnalysisResult(res);
    } catch (err) {
      console.error(err);
      alert(err?.message || 'Error while analyzing files.');
    } finally {
      setProgramLoading(false);
      if (btn) {
        btn.disabled = false;
        btn.textContent = btn.id === 'progMulti2AnalyzeBtn'
          ? 'Analyze — 1 Semester'
          : 'Analyze — 2 Semesters';
      }
    }
  }

  const btn2 = document.getElementById('progMulti2AnalyzeBtn');
  if (btn2) {
    btn2.addEventListener('click', () => doMultiAnalyze(
      { sem1_old: multiSlots.sem1_old, sem1_new: multiSlots.sem1_new },
      btn2,
    ));
  }

  const btn4 = document.getElementById('progMulti4AnalyzeBtn');
  if (btn4) {
    btn4.addEventListener('click', () => doMultiAnalyze(
      {
        sem1_old: multiSlots.sem1_old_4, sem1_new: multiSlots.sem1_new_4,
        sem2_old: multiSlots.sem2_old_4, sem2_new: multiSlots.sem2_new_4,
      },
      btn4,
    ));
  }
}

function initProgramPage() {
  const input = document.getElementById('programExcelInput');
  const zone = document.getElementById('program-upload-zone');
  const fullPdfTopBtn = document.getElementById('programExportPdfBtn');
  const fullPdfBtn = document.getElementById('progExportPdfFullBtn');
  const summaryPdfBtn = document.getElementById('progExportPdfSummaryBtn');
  const excelBtn = document.getElementById('progExportExcelBtn');
  const docxBtn = document.getElementById('progExportDocxBtn');
  const totalOverrideInput = document.getElementById('progTotalStudentsOverride');

  initMultiUpload();

  const handleFile = (file) => {
    if (!file || !file.name.toLowerCase().endsWith('.xlsx')) return;
    setProgramLoading(true);
    uploadProgramFile(file)
      .then((res) => {
        handleAnalysisResult(res);
      })
      .catch((err) => {
        console.error(err);
        const msg = err?.message || err?.detail || 'Error while analyzing Excel file.';
        alert(msg);
      })
      .finally(() => setProgramLoading(false));
  };

  if (input) {
    input.addEventListener('change', (e) => {
      const file = e.target.files && e.target.files[0];
      handleFile(file);
    });
  }

  if (totalOverrideInput) {
    totalOverrideInput.addEventListener('input', () => {
      if (programSummary) {
        renderProgramKpis(programSummary);
        renderPredictiveSection(programSummary);
        renderExecutiveSummary(programSummary);
      }
    });
  }

  if (zone) {
    zone.addEventListener('dragover', (e) => {
      e.preventDefault();
      zone.classList.add('drag-over');
    });
    zone.addEventListener('dragleave', () => zone.classList.remove('drag-over'));
    zone.addEventListener('drop', (e) => {
      e.preventDefault();
      zone.classList.remove('drag-over');
      const file = e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files[0];
      handleFile(file);
    });
  }

  if (fullPdfTopBtn) {
    fullPdfTopBtn.addEventListener('click', exportProgramPdfFull);
  }
  if (fullPdfBtn) {
    fullPdfBtn.addEventListener('click', exportProgramPdfFull);
  }
  if (summaryPdfBtn) {
    summaryPdfBtn.addEventListener('click', exportProgramPdfSummaryOnly);
  }
  if (excelBtn) {
    excelBtn.addEventListener('click', exportProgramExcel);
  }
  if (docxBtn) {
    docxBtn.addEventListener('click', exportProgramDocx);
  }
}

// ═══════════════════════════════════════════════════════════════════════
// PROGRAM ANALYTICS REPORT — renderAnalyticsReport()
// Generates all 7 sections from API result after file upload
// ═══════════════════════════════════════════════════════════════════════

function renderAnalyticsReport(result, summary) {
  const section = document.getElementById('prog-analytics-report');
  if (!section) return;

  const academic = (result && result.academic_analytics) || {};
  const kpis = (result && result.metadata && result.metadata.kpis) || {};
  const courseRisk = (result && result.course_risk) || {};
  const programStats = (result && result.program_statistics) || {};

  // ─── Build unified course list ───────────────────────────────────────
  const allCoursesMap = {}; // key = course name, val = {code?, name, enrolled, fail, failRate, gpa, excellence, sheet}
  Object.entries(academic).forEach(([sheet, data]) => {
    const src = (data.all_courses && data.all_courses.length)
      ? data.all_courses
      : (data.top20_gpa_per_course || []);
    src.forEach((row) => {
      const name = row.course || row.name || '';
      if (!name) return;
      if (!allCoursesMap[name]) {
        allCoursesMap[name] = {
          name,
          sheet,
          enrolled: row.total || row.enrollment || 0,
          failRate: row.failure_rate || 0,
          gpa: row.gpa_estimate || 0,
          excellence: row.excellence_rate || 0,
        };
      }
    });
  });
  const courseList = Object.values(allCoursesMap)
    .filter((c) => c.enrolled >= 3)
    .sort((a, b) => b.failRate - a.failRate);

  const derived = deriveProgramKpis(summary);

  // ────────────────────────────────────────────────────────────────────
  // SECTION 1 — Executive Dashboard
  // ────────────────────────────────────────────────────────────────────
  const execKpisEl = document.getElementById('ar-exec-kpis');
  if (execKpisEl) {
    const avgGpa = parseFloat(derived.avgGpa) || 0;
    const failRate = parseFloat(derived.overallFailureRate) || 0;
    const excRate = parseFloat(derived.overallExcellenceRate) || 0;
    const qs = parseFloat(summary.qualityScore) || 0;
    const coursesBelow2 = courseList.filter((c) => c.gpa < 2.0).length;
    const coursesHighFail = courseList.filter((c) => c.failRate > 20).length;

    const kpiItems = [
      { label: 'Total Enrollments', value: derived.totalStudents.toLocaleString(), cls: '' },
      { label: 'Total Courses', value: summary.totalCourses, cls: '' },
      { label: 'Avg GPA (Weighted)', value: derived.avgGpa + ' / 4.00', cls: avgGpa >= 3 ? 'ar-good' : avgGpa >= 2.5 ? 'ar-warn' : 'ar-bad' },
      { label: 'Failure Rate', value: (derived.overallFailureRate || '—') + '%', cls: failRate <= 10 ? 'ar-good' : failRate <= 20 ? 'ar-warn' : 'ar-bad' },
      { label: 'Excellence Rate', value: (derived.overallExcellenceRate || '—') + '%', cls: excRate >= 20 ? 'ar-good' : excRate >= 10 ? 'ar-warn' : 'ar-bad' },
      { label: 'Data Quality Score', value: (summary.qualityScore || '—') + '/100', cls: qs >= 80 ? 'ar-good' : qs >= 60 ? 'ar-warn' : 'ar-bad' },
      { label: 'Courses with GPA < 2.0', value: coursesBelow2 + ' courses', cls: coursesBelow2 === 0 ? 'ar-good' : coursesBelow2 <= 3 ? 'ar-warn' : 'ar-bad' },
      { label: 'Courses Failure > 20%', value: coursesHighFail + ' courses', cls: coursesHighFail === 0 ? 'ar-good' : coursesHighFail <= 3 ? 'ar-warn' : 'ar-bad' },
    ];
    execKpisEl.innerHTML = kpiItems.map((k) =>
      `<div class="ar-kpi-card ${k.cls}"><span class="ar-kpi-label">${k.label}</span><span class="ar-kpi-val">${k.value}</span></div>`
    ).join('');
  }

  const execInterpEl = document.getElementById('ar-exec-interpretation');
  if (execInterpEl) {
    const avgGpa = parseFloat(derived.avgGpa) || 0;
    const failRate = parseFloat(derived.overallFailureRate) || 0;
    const excRate = parseFloat(derived.overallExcellenceRate) || 0;
    let perf = avgGpa >= 3.0 ? 'strong' : avgGpa >= 2.5 ? 'moderate' : 'below-target';
    execInterpEl.innerHTML =
      `<p>The program demonstrates <strong>${perf} academic performance</strong> with a weighted average GPA of <strong>${derived.avgGpa ?? 'N/A'}/4.00</strong> and an overall failure rate of <strong>${derived.overallFailureRate ?? 'N/A'}%</strong>. ` +
      `Excellence rate stands at <strong>${derived.overallExcellenceRate ?? 'N/A'}%</strong> against a program target of ≥20%. ` +
      (failRate > 10
        ? `The failure rate exceeds the 10% institutional threshold, indicating that academic support and curriculum review are warranted in underperforming courses.`
        : `The failure rate remains within acceptable bounds; continued monitoring is recommended to maintain this standard.`) +
      `</p>`;
  }

  // ────────────────────────────────────────────────────────────────────
  // SECTION 2 — Risk Analysis
  // ────────────────────────────────────────────────────────────────────

  // High-risk table
  const highRiskTableEl = document.getElementById('ar-high-risk-table');
  if (highRiskTableEl) {
    const topRisk = courseList.filter((c) => c.failRate > 10).slice(0, 15);
    if (topRisk.length) {
      let html = `<table class="ar-table"><thead><tr>
        <th>#</th><th>Course</th><th>Enrolled</th><th>Fail%</th><th>GPA</th><th>Excellence%</th><th>Risk</th>
      </tr></thead><tbody>`;
      topRisk.forEach((c, i) => {
        const risk = c.failRate >= 30 ? '🔴 CRITICAL' : c.failRate >= 20 ? '🟠 HIGH' : '🟡 MODERATE';
        const badGpa = c.gpa < 2.0 ? ' style="color:#c0392b;font-weight:700"' : '';
        html += `<tr>
          <td>${i + 1}</td>
          <td>${c.name}</td>
          <td>${c.enrolled}</td>
          <td style="font-weight:600;color:${c.failRate >= 30 ? '#c0392b' : c.failRate >= 20 ? '#e67e22' : '#f39c12'}">${c.failRate.toFixed(1)}%</td>
          <td${badGpa}>${c.gpa.toFixed(2)}</td>
          <td>${c.excellence.toFixed(1)}%</td>
          <td>${risk}</td>
        </tr>`;
      });
      html += '</tbody></table>';
      highRiskTableEl.innerHTML = html;
    } else {
      highRiskTableEl.innerHTML = '<p class="ar-note ar-good-note">✅ No courses exceed the 10% failure rate threshold. No abnormal risk patterns detected.</p>';
    }
  }

  // Increasing failure trend — look across sheets
  const incrFailEl = document.getElementById('ar-incr-fail-list');
  if (incrFailEl) {
    incrFailEl.innerHTML = '';
    // Build per-sheet failure rates per course
    const bySheet = {};
    Object.entries(academic).forEach(([sheet, data]) => {
      const src = (data.all_courses && data.all_courses.length) ? data.all_courses : (data.top20_failure_rate || []);
      src.forEach((row) => {
        const name = row.course || row.name || '';
        if (!name) return;
        if (!bySheet[name]) bySheet[name] = {};
        bySheet[name][sheet] = row.failure_rate || 0;
      });
    });
    const trends = [];
    Object.entries(bySheet).forEach(([course, sheetRates]) => {
      const entries = Object.entries(sheetRates).sort((a, b) => a[0].localeCompare(b[0]));
      if (entries.length < 2) return;
      const first = entries[0][1];
      const last = entries[entries.length - 1][1];
      if (last > first + 5) trends.push({ course, from: first, to: last, delta: last - first });
    });
    trends.sort((a, b) => b.delta - a.delta);
    if (trends.length) {
      trends.slice(0, 8).forEach((t) => {
        const li = document.createElement('li');
        li.innerHTML = `<strong>${escapeHtmlPR(t.course)}</strong>: failure rate rose from ${escapeHtmlPR(t.from.toFixed(1))}% → <span style="color:#c0392b;font-weight:700">${escapeHtmlPR(t.to.toFixed(1))}%</span> (+${escapeHtmlPR(t.delta.toFixed(1))} pp)`;
        incrFailEl.appendChild(li);
      });
    } else {
      incrFailEl.innerHTML = '<li>No courses with a pronounced failure rate increase were detected across available sheets.</li>';
    }
  }

  // GPA decline / low GPA detection
  const gpaDeclineEl = document.getElementById('ar-gpa-decline-list');
  if (gpaDeclineEl) {
    gpaDeclineEl.innerHTML = '';
    // Courses with GPA < 2.0
    const lowGpa = courseList.filter((c) => c.gpa < 2.0 && c.enrolled >= 5).sort((a, b) => a.gpa - b.gpa);
    // Courses with GPA decline across sheets
    const gpaBySheet = {};
    Object.entries(academic).forEach(([sheet, data]) => {
      const src = (data.all_courses && data.all_courses.length) ? data.all_courses : (data.top20_gpa_per_course || []);
      src.forEach((row) => {
        const name = row.course || row.name || '';
        if (!name) return;
        if (!gpaBySheet[name]) gpaBySheet[name] = {};
        gpaBySheet[name][sheet] = row.gpa_estimate || 0;
      });
    });
    const declines = [];
    Object.entries(gpaBySheet).forEach(([course, sheetGpas]) => {
      const entries = Object.entries(sheetGpas).sort((a, b) => a[0].localeCompare(b[0]));
      if (entries.length < 2) return;
      const first = entries[0][1];
      const last = entries[entries.length - 1][1];
      if (last + 0.2 < first) declines.push({ course, from: first, to: last });
    });

    if (lowGpa.length || declines.length) {
      lowGpa.slice(0, 6).forEach((c) => {
        const li = document.createElement('li');
        li.innerHTML = `<strong>${escapeHtmlPR(c.name)}</strong>: GPA <span style="color:#c0392b;font-weight:700">${escapeHtmlPR(c.gpa.toFixed(2))}</span>/4.00 — critically low (enrolled: ${escapeHtmlPR(c.enrolled)})`;
        gpaDeclineEl.appendChild(li);
      });
      declines.slice(0, 4).forEach((d) => {
        const li = document.createElement('li');
        li.innerHTML = `<strong>${escapeHtmlPR(d.course)}</strong>: GPA declined from ${escapeHtmlPR(d.from.toFixed(2))} → <span style="color:#c0392b;font-weight:700">${escapeHtmlPR(d.to.toFixed(2))}</span>`;
        gpaDeclineEl.appendChild(li);
      });
    } else {
      gpaDeclineEl.innerHTML = '<li>✅ No significant GPA decline patterns detected. All courses maintain acceptable GPA levels.</li>';
    }
  }

  // ────────────────────────────────────────────────────────────────────
  // SECTION 3 — Visual Analytics Summaries
  // ────────────────────────────────────────────────────────────────────
  const visualEl = document.getElementById('ar-visual-analytics');
  if (visualEl) {
    const avgGpa = parseFloat(derived.avgGpa) || 0;
    const failRate = parseFloat(derived.overallFailureRate) || 0;
    const excRate = parseFloat(derived.overallExcellenceRate) || 0;
    const qs = parseFloat(summary.qualityScore) || 0;

    // GPA distribution buckets
    const buckets = [0, 0, 0, 0, 0, 0]; // <1.5, 1.5-2.0, 2.0-2.5, 2.5-3.0, 3.0-3.5, >=3.5
    courseList.forEach((c) => {
      if (c.gpa >= 3.5) buckets[5]++;
      else if (c.gpa >= 3.0) buckets[4]++;
      else if (c.gpa >= 2.5) buckets[3]++;
      else if (c.gpa >= 2.0) buckets[2]++;
      else if (c.gpa >= 1.5) buckets[1]++;
      else buckets[0]++;
    });
    const total = courseList.length || 1;

    // Top enrolled courses
    const topEnrolled = [...courseList].sort((a, b) => b.enrolled - a.enrolled).slice(0, 5);
    const maxEnroll = topEnrolled[0] ? topEnrolled[0].enrolled : 1;

    const analyticsCards = [
      {
        title: '📈 GPA Distribution',
        note: `Average GPA is ${derived.avgGpa ?? 'N/A'}/4.00. ${buckets[0] + buckets[1]} courses (${(((buckets[0] + buckets[1]) / total) * 100).toFixed(0)}%) fall below 2.00 — indicating a structural challenge in foundational courses.`,
        content: ['≥3.50', '3.0–3.49', '2.5–2.99', '2.0–2.49', '1.5–1.99', '<1.50'].map((label, i) => {
          const idx = 5 - i;
          const pct = ((buckets[idx] / total) * 100).toFixed(0);
          const color = idx >= 4 ? '#27ae60' : idx === 3 ? '#2ecc71' : idx === 2 ? '#f39c12' : idx === 1 ? '#e67e22' : '#c0392b';
          return `<div class="ar-bar-row"><span class="ar-bar-label">${label}</span><div class="ar-bar-track"><div class="ar-bar-fill" style="width:${pct}%;background:${color}"></div></div><span class="ar-bar-count">${buckets[idx]}</span></div>`;
        }).join(''),
      },
      {
        title: '🎓 Top Enrolled Courses',
        note: 'High-enrollment courses have the greatest student impact. Risk in these courses must be prioritized.',
        content: topEnrolled.map((c) => {
          const pct = ((c.enrolled / maxEnroll) * 100).toFixed(0);
          const color = c.failRate >= 30 ? '#c0392b' : c.failRate >= 15 ? '#e67e22' : '#27ae60';
          return `<div class="ar-bar-row"><span class="ar-bar-label" style="max-width:140px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title="${c.name}">${c.name}</span><div class="ar-bar-track"><div class="ar-bar-fill" style="width:${pct}%;background:${color}"></div></div><span class="ar-bar-count">${c.enrolled}</span></div>`;
        }).join(''),
      },
      {
        title: '📊 Quality Score',
        note: `Data Quality Score: ${summary.qualityScore ?? 'N/A'}/100. ${qs >= 80 ? 'Reporting processes are strong and consistent.' : qs >= 60 ? 'Quality is acceptable but further improvement is needed.' : 'Data quality requires urgent attention — review collection and validation.'}`,
        content: `<div class="ar-gauge-wrap"><div class="ar-gauge-bar" style="width:${Math.min(qs, 100)}%;background:${qs >= 80 ? '#27ae60' : qs >= 60 ? '#f39c12' : '#c0392b'}"></div></div><p class="ar-gauge-label">${summary.qualityScore ?? '—'} / 100</p>
        <div class="ar-bar-row" style="margin-top:8px"><span class="ar-bar-label">Failure Rate</span><div class="ar-bar-track"><div class="ar-bar-fill" style="width:${Math.min(failRate, 100)}%;background:#e74c3c"></div></div><span class="ar-bar-count">${failRate.toFixed(1)}%</span></div>
        <div class="ar-bar-row"><span class="ar-bar-label">Excellence Rate</span><div class="ar-bar-track"><div class="ar-bar-fill" style="width:${Math.min(excRate, 100)}%;background:#27ae60"></div></div><span class="ar-bar-count">${excRate.toFixed(1)}%</span></div>`,
      },
      {
        title: '🔒 Academic Performance Stability',
        note: `Stability Index: ${summary.stabilityIndex ?? 'N/A'}/100. ${summary.stabilityNote || 'Based on cross-sheet reliability variance.'}`,
        content: (() => {
          const si = summary.stabilityIndex ?? 0;
          const stableHigh = courseList.filter((c) => c.gpa >= 3.0 && c.failRate < 10).length;
          const stableLow = courseList.filter((c) => c.gpa < 2.0).length;
          const monitor = courseList.filter((c) => c.gpa >= 2.0 && c.gpa < 3.0 && c.failRate >= 10).length;
          return `<div class="ar-stability-grid">
            <div class="ar-stab-card ar-good"><span class="ar-stab-num">${stableHigh}</span><span>Stable High</span><small>GPA ≥3.0, Fail &lt;10%</small></div>
            <div class="ar-stab-card ar-warn"><span class="ar-stab-num">${monitor}</span><span>Monitor</span><small>GPA 2.0–3.0, Fail ≥10%</small></div>
            <div class="ar-stab-card ar-bad"><span class="ar-stab-num">${stableLow}</span><span>At Risk</span><small>GPA &lt;2.0</small></div>
          </div><div class="ar-gauge-wrap" style="margin-top:10px"><div class="ar-gauge-bar" style="width:${Math.min(si, 100)}%;background:${si >= 70 ? '#27ae60' : si >= 45 ? '#f39c12' : '#e74c3c'}"></div></div><p class="ar-gauge-label">Stability ${si}/100</p>`;
        })(),
      },
    ];

    visualEl.innerHTML = analyticsCards.map((card) =>
      `<div class="ar-analytics-card">
        <h4 class="ar-analytics-card-title">${card.title}</h4>
        <div class="ar-analytics-card-body">${card.content}</div>
        <p class="ar-analytics-note">${card.note}</p>
      </div>`
    ).join('');
  }

  // ────────────────────────────────────────────────────────────────────
  // SECTION 4 — Volatility Analysis
  // ────────────────────────────────────────────────────────────────────
  const volTableEl = document.getElementById('ar-volatility-table');
  if (volTableEl) {
    // Compute Volatility Index: combination of gpa spread and failure rate
    const volCourses = courseList.map((c) => {
      // VI approximated from: risk probability (from courseRisk) + normalized failure rate deviation
      let riPct = 0;
      Object.values(courseRisk).forEach((data) => {
        const cr = (data && data.course_risk) || {};
        if (cr[c.name] != null) riPct = (cr[c.name] || 0) * 100;
      });
      const vi = (c.failRate / 100 * 0.6 + (4 - c.gpa) / 4 * 0.4).toFixed(3);
      const viFloat = parseFloat(vi);
      const level = viFloat >= 0.6 ? '🔴 Very High' : viFloat >= 0.45 ? '🟠 High' : viFloat >= 0.3 ? '🟡 Moderate' : '🟢 Low';
      return { ...c, vi: viFloat, level };
    });
    volCourses.sort((a, b) => b.vi - a.vi);

    const top = volCourses.slice(0, 18);
    if (top.length) {
      let html = `<table class="ar-table"><thead><tr>
        <th>#</th><th>Course</th><th>Enrolled</th><th>GPA</th><th>Fail%</th><th>Volatility Index</th><th>Level</th>
      </tr></thead><tbody>`;
      top.forEach((c, i) => {
        html += `<tr>
          <td>${i + 1}</td>
          <td>${c.name}</td>
          <td>${c.enrolled}</td>
          <td>${c.gpa.toFixed(2)}</td>
          <td>${c.failRate.toFixed(1)}%</td>
          <td><strong>${c.vi.toFixed(3)}</strong></td>
          <td>${c.level}</td>
        </tr>`;
      });
      html += '</tbody></table>';
      volTableEl.innerHTML = html;
    } else {
      volTableEl.innerHTML = '<p class="ar-note">No course data available for volatility ranking.</p>';
    }
  }

  // ────────────────────────────────────────────────────────────────────
  // SECTION 5 — Risk Heatmap Matrix
  // ────────────────────────────────────────────────────────────────────
  const heatmapEl = document.getElementById('ar-heatmap-quadrants');
  if (heatmapEl) {
    const q1 = courseList.filter((c) => c.gpa < 2.0 && c.failRate >= 20);  // Critical
    const q2 = courseList.filter((c) => c.gpa < 2.0 && c.failRate < 20);   // Performance Gap
    const q3 = courseList.filter((c) => c.gpa >= 2.0 && c.gpa < 3.0 && c.failRate >= 10); // Monitor
    const q4 = courseList.filter((c) => c.gpa >= 3.0 && c.failRate < 10);  // Stable High

    const quadrants = [
      { cls: 'ar-q-critical', label: '🔴 Q1 — Critical Risk', sub: 'Low GPA + High Failure Rate', courses: q1 },
      { cls: 'ar-q-gap',      label: '🟠 Q2 — Performance Gap', sub: 'Low GPA + Low Failure Rate', courses: q2 },
      { cls: 'ar-q-monitor',  label: '🟡 Q3 — Monitor',         sub: 'Moderate GPA + Elevated Failure', courses: q3 },
      { cls: 'ar-q-stable',   label: '🟢 Q4 — Stable / High',   sub: 'GPA ≥ 3.0 + Failure < 10%', courses: q4 },
    ];

    heatmapEl.innerHTML = quadrants.map((q) =>
      `<div class="ar-quadrant ${q.cls}">
        <div class="ar-q-header">
          <span class="ar-q-title">${q.label}</span>
          <span class="ar-q-count">${q.courses.length} courses</span>
        </div>
        <p class="ar-q-sub">${q.sub}</p>
        <ul class="ar-q-list">${q.courses.slice(0, 8).map((c) =>
          `<li>${c.name} <span class="ar-q-meta">GPA ${c.gpa.toFixed(2)} · ${c.failRate.toFixed(1)}%</span></li>`
        ).join('')}${q.courses.length > 8 ? `<li class="ar-q-more">+${q.courses.length - 8} more…</li>` : ''}</ul>
      </div>`
    ).join('');

    const summaryEl = document.getElementById('ar-heatmap-summary');
    if (summaryEl) {
      const total = courseList.length || 1;
      summaryEl.textContent =
        `Risk distribution: ${q1.length} critical (${((q1.length/total)*100).toFixed(0)}%) · ` +
        `${q2.length} performance-gap (${((q2.length/total)*100).toFixed(0)}%) · ` +
        `${q3.length} monitor (${((q3.length/total)*100).toFixed(0)}%) · ` +
        `${q4.length} stable/high-performing (${((q4.length/total)*100).toFixed(0)}%). ` +
        (q1.length >= 5
          ? 'The high proportion of critical-risk courses indicates systemic challenges that require immediate program-level intervention.'
          : q1.length > 0
          ? 'A small number of critical-risk courses are identified; targeted support is recommended.'
          : 'No critical-risk courses detected. The program maintains an acceptable risk distribution.');
    }
  }

  // ────────────────────────────────────────────────────────────────────
  // SECTION 6 — Program Insights
  // ────────────────────────────────────────────────────────────────────
  const insightsEl = document.getElementById('ar-insights');
  if (insightsEl) {
    const topPerformers = [...courseList].filter((c) => c.gpa >= 3.3 && c.failRate < 5).sort((a, b) => b.gpa - a.gpa).slice(0, 5);
    const weakCourses = [...courseList].filter((c) => c.gpa < 2.0 || c.failRate > 20).sort((a, b) => a.gpa - b.gpa).slice(0, 6);
    const missingData = Object.values(kpis).some((k) => k && k.composite_reliability_index < 0.8);

    const insights = [
      {
        cls: 'ar-insight-strength',
        title: '✅ Academic Strengths',
        items: topPerformers.length
          ? topPerformers.map((c) => `<strong>${c.name}</strong> — GPA ${c.gpa.toFixed(2)}, Failure ${c.failRate.toFixed(1)}%`)
          : ['No clearly high-performing courses identified (GPA ≥ 3.3, Failure < 5%).'],
      },
      {
        cls: 'ar-insight-weak',
        title: '⚠️ Weak Courses Requiring Intervention',
        items: weakCourses.length
          ? weakCourses.map((c) => `<strong>${c.name}</strong> — GPA ${c.gpa.toFixed(2)}, Failure ${c.failRate.toFixed(1)}%, Enrolled ${c.enrolled}`)
          : ['All courses are within acceptable performance ranges.'],
      },
      {
        cls: 'ar-insight-improve',
        title: '🔧 Curriculum Improvement Areas',
        items: [
          courseList.filter((c) => c.failRate > 15 && c.enrolled >= 20).length > 0
            ? `High-enrollment, high-failure courses (${courseList.filter((c) => c.failRate > 15 && c.enrolled >= 20).length} courses) — review teaching methods and exam design.`
            : null,
          courseList.filter((c) => c.gpa < 2.0).length > 2
            ? `${courseList.filter((c) => c.gpa < 2.0).length} courses with GPA < 2.0 — prerequisite sequencing and content alignment need review.`
            : null,
          courseList.filter((c) => c.excellence < 5 && c.gpa >= 2.5).length > 3
            ? `Several courses with acceptable GPA but near-zero excellence rates — grade ceiling effect or limited challenge may be present.`
            : null,
          'Courses with enrollment < 5 students should be excluded from performance benchmarking.',
        ].filter(Boolean),
      },
      {
        cls: 'ar-insight-data',
        title: '📋 Data Quality Observations',
        items: [
          `Overall Data Quality Score: ${summary.qualityScore ?? 'N/A'}/100`,
          missingData ? 'Some sheets have composite reliability below 80% — data collection procedures should be reviewed.' : 'Data reliability is within acceptable range across uploaded sheets.',
          courseList.filter((c) => c.enrolled < 10).length > 0
            ? `${courseList.filter((c) => c.enrolled < 10).length} courses with fewer than 10 students produce statistically unreliable metrics.`
            : null,
          Object.keys(academic).length === 1
            ? 'Only one sheet was detected; longitudinal trend analysis requires at least two sheets.'
            : `${Object.keys(academic).length} sheets detected — cross-sheet trend analysis is available.`,
        ].filter(Boolean),
      },
    ];

    insightsEl.innerHTML = insights.map((ins) =>
      `<div class="ar-insight-card ${ins.cls}">
        <h4 class="ar-insight-title">${ins.title}</h4>
        <ul>${ins.items.map((it) => `<li>${it}</li>`).join('')}</ul>
      </div>`
    ).join('');
  }

  // ────────────────────────────────────────────────────────────────────
  // SECTION 7 — Recommended Actions
  // ────────────────────────────────────────────────────────────────────
  const recsEl = document.getElementById('ar-recommendations');
  if (recsEl) {
    const failRate = parseFloat(derived.overallFailureRate) || 0;
    const avgGpa = parseFloat(derived.avgGpa) || 0;
    const criticalCount = courseList.filter((c) => c.gpa < 2.0 && c.failRate >= 20).length;
    const topHighRisk = courseList.filter((c) => c.failRate > 20).slice(0, 3);

    const recs = [];

    if (criticalCount > 0) {
      recs.push({
        priority: '🔴 URGENT',
        cls: 'ar-rec-urgent',
        title: 'Academic Support for Critical Courses',
        body: `Deploy supplementary tutoring and peer-learning sessions for ${topHighRisk.map((c) => c.name).join(', ')}. These courses have failure rates above 20% and require immediate pedagogical attention.`,
      });
    }

    if (failRate > 10) {
      recs.push({
        priority: '🔴 URGENT',
        cls: 'ar-rec-urgent',
        title: 'Early-Warning System for At-Risk Students',
        body: 'Implement an academic early-alert mechanism by Week 4 of each semester. Identify students enrolled in multiple high-risk courses simultaneously and connect them with academic advising before withdrawal deadlines.',
      });
    }

    recs.push({
      priority: '🟠 HIGH',
      cls: 'ar-rec-high',
      title: 'Curriculum & Prerequisite Review',
      body: 'Convene a curriculum committee to audit prerequisite chains in underperforming course clusters. Introduce formal co-requisites or bridging modules where foundational gaps exist (particularly in physics, mechanics, and electronics streams where applicable).',
    });

    recs.push({
      priority: '🟠 HIGH',
      cls: 'ar-rec-high',
      title: 'Teaching Method Improvement',
      body: 'Courses with failure rates that worsened between terms should undergo pedagogical review. Evaluate exam design, learning outcome alignment, and consider evidence-based approaches such as problem-based learning or flipped classroom models.',
    });

    if (avgGpa < 3.0) {
      recs.push({
        priority: '🟡 MEDIUM',
        cls: 'ar-rec-medium',
        title: 'Faculty Monitoring & Best Practice Sharing',
        body: `Document pedagogical approaches from the program's highest-performing courses (GPA ≥ 3.3, Failure < 5%). Conduct structured peer observation for instructors of persistently underperforming courses, and incorporate findings into annual teaching reviews.`,
      });
    }

    recs.push({
      priority: '🟡 MEDIUM',
      cls: 'ar-rec-medium',
      title: 'Student Cohort Tracking System',
      body: 'Transition from course-level to student-level analytics. A longitudinal student database will enable dropout risk prediction, retention interventions, and accurate program-level GPA tracking across semesters.',
    });

    recs.push({
      priority: '🟢 LOW',
      cls: 'ar-rec-low',
      title: 'Data Quality Improvement',
      body: 'Ensure all course records include instructor attribution, section enrollments, and complete grade distributions. Set a data quality target of ≥90/100. Establish a three-term historical GPA baseline to enable statistically valid trend analysis.',
    });

    recsEl.innerHTML = recs.map((r) =>
      `<div class="ar-rec-card ${r.cls}">
        <div class="ar-rec-header">
          <span class="ar-rec-priority">${r.priority}</span>
          <span class="ar-rec-title">${r.title}</span>
        </div>
        <p class="ar-rec-body">${r.body}</p>
      </div>`
    ).join('');
  }

  // Show the section (in case it was hidden)
  section.hidden = false;
}

document.addEventListener('DOMContentLoaded', initProgramPage);

