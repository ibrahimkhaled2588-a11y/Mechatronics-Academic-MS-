// Course Report Page Logic

const apiUrlCourse = window.location.origin || '';

/** Escape untrusted text before inserting into innerHTML. */
function escapeHtmlCR(str) {
    const d = document.createElement('div');
    d.textContent = String(str ?? '');
    return d.innerHTML;
}

let courseLastResult = null;
let courseIndex = null;
let courseGpaChart = null;
let courseFailureChart = null;
let courseGradeChart = null;

/** Upload one file → /upload-excel, two or more → /upload-excel-bulk. */
function uploadCourseFile(files) {
  const fileList = Array.isArray(files) ? files : [files];
  const form = new FormData();
  let endpoint;
  if (fileList.length > 1) {
    fileList.forEach((f) => form.append('files', f));
    endpoint = `${apiUrlCourse}/upload-excel-bulk`;
  } else {
    form.append('file', fileList[0]);
    endpoint = `${apiUrlCourse}/upload-excel`;
  }
  return fetch(endpoint, { method: 'POST', body: form }).then(async (resp) => {
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({ detail: resp.statusText }));
      throw new Error(err.detail || `HTTP ${resp.status}`);
    }
    return resp.json();
  });
}

function _showCourseUploadHint(files) {
  const hint = document.getElementById('courseUploadHint');
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

function setCourseLoading(loading) {
  const loadingEl = document.getElementById('course-loading');
  const zone = document.getElementById('course-upload-zone');
  const input = document.getElementById('courseExcelInput');
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

function buildCourseIndex(result) {
  const academic = (result && result.academic_analytics) || {};
  const courseRisk = (result && result.course_risk) || {};
  const coursePlans = (result && result.course_plans) || {};
  const kpis = (result && result.metadata && result.metadata.kpis) || {};
  const sheetTitles = (result && result.metadata && result.metadata.sheet_titles) || {};

  const index = {};

  Object.entries(academic).forEach(([sheet, data]) => {
    const allCourses = data.all_courses || [];
    const enroll = allCourses.length ? allCourses : (data.top20_enrollment || []);
    const excellence = allCourses.length ? allCourses : (data.top20_excellence_rate || []);
    const failure = allCourses.length ? allCourses : (data.top20_failure_rate || []);
    const gpa = allCourses.length ? allCourses : (data.top20_gpa_per_course || []);

    function ensureCourse(course) {
      if (!index[course]) {
        index[course] = {
          name: course, courseCode: null, courseTitle: null, instructor: null,
          academicYear: null, semester: null, programTitle: null, facultyHint: sheet,
          sheets: {},
        };
      }
      if (!index[course].sheets[sheet]) {
        index[course].sheets[sheet] = {
          sheet,
          enrollment: null,
          excellenceRate: null,
          excellenceCiLo: null,
          excellenceCiHi: null,
          failureRate: null,
          failureCiLo: null,
          failureCiHi: null,
          passRate: null,
          passCiLo: null,
          passCiHi: null,
          gpa: null,
          gpaVariance: null,
          volatility: null,
          gradeDistribution: null,
          abnormalSpike: false,
          total: null,
          riskScore: null,
          quality: null,
          recommendations: [],
        };
      }
      return index[course].sheets[sheet];
    }

    enroll.forEach((row) => {
      const c = row.course;
      if (!c) return;
      const entry = ensureCourse(c);
      if (row.enrollment != null) entry.enrollment = row.enrollment;
      if (row.total != null && entry.total == null) entry.total = row.total;
    });

    excellence.forEach((row) => {
      const c = row.course;
      if (!c) return;
      const entry = ensureCourse(c);
      if (row.excellence_rate != null) entry.excellenceRate = row.excellence_rate;
      if (row.total != null) entry.total = row.total;
    });

    failure.forEach((row) => {
      const c = row.course;
      if (!c) return;
      const entry = ensureCourse(c);
      if (row.failure_rate != null) entry.failureRate = row.failure_rate;
      if (row.failure_rate_ci_lower != null) entry.failureCiLo = row.failure_rate_ci_lower;
      if (row.failure_rate_ci_upper != null) entry.failureCiHi = row.failure_rate_ci_upper;
      if (row.total != null) entry.total = row.total;
    });

    gpa.forEach((row) => {
      const c = row.course;
      if (!c) return;
      const entry = ensureCourse(c);
      if (row.gpa_estimate != null) entry.gpa = row.gpa_estimate;
      if (row.volatility_index != null) entry.volatility = row.volatility_index;
      if (row.gpa_variance != null) entry.gpaVariance = row.gpa_variance;
      if (row.total != null && entry.total == null) entry.total = row.total;
    });

    // Pick up grade_distribution and CI values from all_courses (richer source)
    allCourses.forEach((row) => {
      const c = row.course;
      if (!c) return;
      const entry = ensureCourse(c);
      if (row.course_code) entry.courseCode = row.course_code;
      if (row.course_title) entry.courseTitle = row.course_title;
      if (row.instructor) entry.instructor = row.instructor;
      if (row.grade_distribution) entry.gradeDistribution = row.grade_distribution;
      if (row.excellence_ci_lower != null) entry.excellenceCiLo = row.excellence_ci_lower;
      if (row.excellence_ci_upper != null) entry.excellenceCiHi = row.excellence_ci_upper;
      if (row.pass_rate != null) entry.passRate = row.pass_rate;
      if (row.pass_rate_ci_lower != null) entry.passCiLo = row.pass_rate_ci_lower;
      if (row.pass_rate_ci_upper != null) entry.passCiHi = row.pass_rate_ci_upper;
      if (row.failure_rate_ci_lower != null && entry.failureCiLo == null) entry.failureCiLo = row.failure_rate_ci_lower;
      if (row.failure_rate_ci_upper != null && entry.failureCiHi == null) entry.failureCiHi = row.failure_rate_ci_upper;
      if (row.volatility_index != null && entry.volatility == null) entry.volatility = row.volatility_index;
      if (row.abnormal_spike != null) entry.abnormalSpike = row.abnormal_spike;
    });

    const sheetRisk = (courseRisk[sheet] && courseRisk[sheet].course_risk) || {};
    Object.entries(sheetRisk).forEach(([courseName, risk]) => {
      const entry = ensureCourse(courseName);
      entry.riskScore = (risk || 0) * 100;
    });

    const plans = coursePlans[sheet] || [];
    plans.forEach((p) => {
      const entry = ensureCourse(p.course);
      const recs = p.action_plan || [];
      entry.recommendations = entry.recommendations.concat(recs);
    });

    const titleMeta = sheetTitles[sheet] || null;
    if (titleMeta) {
      Object.values(index).forEach((courseEntry) => {
        if (courseEntry.sheets[sheet]) {
          courseEntry.sheets[sheet].titleMeta = titleMeta;
        }
        if (!courseEntry.academicYear && titleMeta.academic_year) courseEntry.academicYear = titleMeta.academic_year;
        if (!courseEntry.semester && titleMeta.semester) courseEntry.semester = titleMeta.semester;
        if (!courseEntry.programTitle && titleMeta.program_title) courseEntry.programTitle = titleMeta.program_title;
      });
    }

    const sheetKpi = kpis[sheet];
    if (sheetKpi) {
      const missingPct = sheetKpi.missing_ratio ?? null;
      const dupPct = sheetKpi.duplicate_rate ?? null;
      const rel = sheetKpi.composite_reliability_index ?? null;
      const driftScore = sheetKpi.data_drift_score ?? 0;
      const driftStatus =
        driftScore > 0.2 ? 'Significant drift' : driftScore > 0.05 ? 'Mild drift' : 'Stable';
      Object.values(index).forEach((courseEntry) => {
        if (courseEntry.sheets[sheet]) {
          courseEntry.sheets[sheet].quality = {
            missingPct,
            dupPct,
            reliability: rel != null ? rel * 100 : null,
            driftScore,
            driftStatus,
          };
        }
      });
    }
  });

  return index;
}

function populateCourseDropdown(index) {
  const select = document.getElementById('courseSelect');
  if (!select) return;
  select.innerHTML = '<option value="" disabled selected>Select a course...</option>';
  const courses = Object.keys(index).sort((a, b) => a.localeCompare(b));
  courses.forEach((course) => {
    const opt = document.createElement('option');
    opt.value = course;
    opt.textContent = course;
    select.appendChild(opt);
  });
}

function aggregateCourseMetrics(courseEntry) {
  const sheets = Object.values(courseEntry.sheets || {});
  if (!sheets.length) return null;

  let totalEnroll = 0;
  let totalForRates = 0;
  let excellenceSum = 0;
  let failureSum = 0;
  let passSum = 0;
  let gpaWeighted = 0;
  let riskMax = 0;
  let qualityRef = null;
  let gradeDistRef = null;
  let failureCiLo = null, failureCiHi = null;
  let excellenceCiLo = null, excellenceCiHi = null;
  let passCiLo = null, passCiHi = null;
  let volatilityMax = null;

  sheets.forEach((s) => {
    const total = s.total != null ? s.total : s.enrollment;
    if (s.enrollment != null) {
      totalEnroll += s.enrollment;
    } else if (total != null) {
      totalEnroll += total;
    }
    if (total != null && total > 0) {
      totalForRates += total;
      if (s.excellenceRate != null) excellenceSum += (s.excellenceRate / 100) * total;
      if (s.failureRate != null) failureSum += (s.failureRate / 100) * total;
      if (s.passRate != null) passSum += (s.passRate / 100) * total;
      if (s.gpa != null) gpaWeighted += s.gpa * total;
    }
    if (s.riskScore != null) riskMax = Math.max(riskMax, s.riskScore);
    if (!qualityRef && s.quality) qualityRef = s.quality;
    if (!gradeDistRef && s.gradeDistribution) gradeDistRef = s.gradeDistribution;
    if (s.failureCiLo != null) failureCiLo = s.failureCiLo;
    if (s.failureCiHi != null) failureCiHi = s.failureCiHi;
    if (s.excellenceCiLo != null) excellenceCiLo = s.excellenceCiLo;
    if (s.excellenceCiHi != null) excellenceCiHi = s.excellenceCiHi;
    if (s.passCiLo != null) passCiLo = s.passCiLo;
    if (s.passCiHi != null) passCiHi = s.passCiHi;
    if (s.volatility != null) volatilityMax = volatilityMax == null ? s.volatility : Math.max(volatilityMax, s.volatility);
  });

  const excellenceRate = totalForRates ? (excellenceSum / totalForRates) * 100 : null;
  const failureRate = totalForRates ? (failureSum / totalForRates) * 100 : null;
  const passRate = totalForRates ? (passSum / totalForRates) * 100 : null;
  const gpa = totalForRates ? gpaWeighted / totalForRates : null;

  return {
    enrollment: totalEnroll || null,
    excellenceRate: excellenceRate != null ? excellenceRate.toFixed(1) : null,
    excellenceCiLo,
    excellenceCiHi,
    failureRate: failureRate != null ? failureRate.toFixed(1) : null,
    failureCiLo,
    failureCiHi,
    passRate: passRate != null ? passRate.toFixed(1) : null,
    passCiLo,
    passCiHi,
    gpa: gpa != null ? gpa.toFixed(2) : null,
    volatility: volatilityMax,
    riskScore: riskMax ? riskMax.toFixed(1) : null,
    quality: qualityRef,
    gradeDistribution: gradeDistRef,
    sheets,
  };
}

function renderCourseKpis(metrics) {
  const setText = (id, value, suffix = '') => {
    const el = document.getElementById(id);
    if (!el) return;
    el.textContent = value != null ? `${value}${suffix}` : '—';
  };

  setText('kpiEnrollment', metrics.enrollment, '');
  setText('kpiGpa', metrics.gpa, '');
  setText('kpiRisk', metrics.riskScore, ' %');

  // Excellence with CI
  const excEl = document.getElementById('kpiExcellence');
  if (excEl) {
    if (metrics.excellenceRate != null) {
      let txt = `${metrics.excellenceRate} %`;
      if (metrics.excellenceCiLo != null && metrics.excellenceCiHi != null) {
        txt += ` [${metrics.excellenceCiLo.toFixed(1)}%–${metrics.excellenceCiHi.toFixed(1)}%]`;
      }
      excEl.textContent = txt;
    } else {
      excEl.textContent = '—';
    }
  }

  // Failure with CI
  const failEl = document.getElementById('kpiFailure');
  if (failEl) {
    if (metrics.failureRate != null) {
      let txt = `${metrics.failureRate} %`;
      if (metrics.failureCiLo != null && metrics.failureCiHi != null) {
        txt += ` [${metrics.failureCiLo.toFixed(1)}%–${metrics.failureCiHi.toFixed(1)}%]`;
      }
      failEl.textContent = txt;
    } else {
      failEl.textContent = '—';
    }
  }

  // Pass rate (may not have a dedicated element, set if present)
  const passEl = document.getElementById('kpiPassRate');
  if (passEl) {
    if (metrics.passRate != null) {
      let txt = `${metrics.passRate} %`;
      if (metrics.passCiLo != null && metrics.passCiHi != null) {
        txt += ` [${metrics.passCiLo.toFixed(1)}%–${metrics.passCiHi.toFixed(1)}%]`;
      }
      passEl.textContent = txt;
    } else {
      passEl.textContent = '—';
    }
  }

  // Volatility index
  const volEl = document.getElementById('kpiVolatility');
  if (volEl) {
    volEl.textContent = metrics.volatility != null ? metrics.volatility.toFixed(3) : '—';
  }

  const riskLevelEl = document.getElementById('kpiRiskLevel');
  if (riskLevelEl) {
    const risk = metrics.riskScore != null ? parseFloat(metrics.riskScore) : null;
    let label = 'Insufficient data';
    if (risk != null) {
      if (risk >= 70) label = 'High predicted risk';
      else if (risk >= 40) label = 'Moderate predicted risk';
      else label = 'Low predicted risk';
    }
    riskLevelEl.textContent = label;
  }
}

function renderCourseQuality(metrics) {
  const q = metrics.quality || {};
  const setText = (id, value, suffix = '') => {
    const el = document.getElementById(id);
    if (!el) return;
    el.textContent = value != null ? `${value}${suffix}` : '—';
  };

  setText('qualityMissing', q.missingPct != null ? q.missingPct.toFixed(2) : null, ' %');
  setText('qualityDuplicate', q.dupPct != null ? q.dupPct.toFixed(2) : null, ' %');
  setText('qualityReliability', q.reliability != null ? q.reliability.toFixed(1) : null, ' / 100');

  const driftStatusEl = document.getElementById('qualityDriftStatus');
  const driftScoreEl = document.getElementById('qualityDriftScore');
  if (driftStatusEl) driftStatusEl.textContent = q.driftStatus || 'Not evaluated';
  if (driftScoreEl) {
    driftScoreEl.textContent =
      q.driftScore != null ? `Drift score: ${q.driftScore.toFixed(3)}` : '';
  }
}

function renderCourseGradeDistribution(metrics) {
  const ctxEl = document.getElementById('courseGradeDistributionChart');
  if (!ctxEl || typeof Chart === 'undefined') return;
  if (courseGradeChart) {
    courseGradeChart.destroy();
    courseGradeChart = null;
  }
  const exc = metrics.excellenceRate != null ? parseFloat(metrics.excellenceRate) : null;
  const fail = metrics.failureRate != null ? parseFloat(metrics.failureRate) : null;
  if (exc == null && fail == null) return;
  const exVal = exc != null ? exc : 0;
  const failVal = fail != null ? fail : 0;
  let other = 100 - exVal - failVal;
  if (other < 0) other = 0;

  const data = {
    labels: ['Excellence', 'Pass', 'Failure'],
    datasets: [
      {
        data: [exVal, other, failVal],
        backgroundColor: ['#0ea5e9', '#e5e7eb', '#dc2626'],
      },
    ],
  };

  courseGradeChart = new Chart(ctxEl.getContext('2d'), {
    type: 'doughnut',
    data,
    options: {
      responsive: true,
      plugins: {
        legend: { position: 'bottom' },
      },
      cutout: '55%',
    },
  });
}

function renderCourseGradeBreakdown(metrics) {
  const container = document.getElementById('courseGradeBreakdownTable');
  if (!container) return;
  container.innerHTML = '';
  const dist = metrics.gradeDistribution;
  if (!dist || typeof dist !== 'object' || !Object.keys(dist).length) return;

  const GRADE_ORDER = ['A+', 'A', 'A-', 'B+', 'B', 'B-', 'C+', 'C', 'C-', 'D+', 'D', 'F'];
  const table = document.createElement('table');
  table.className = 'data-table';
  const thead = document.createElement('thead');
  const hRow = document.createElement('tr');
  ['Grade', '%'].forEach((h) => {
    const th = document.createElement('th');
    th.textContent = h;
    hRow.appendChild(th);
  });
  thead.appendChild(hRow);
  table.appendChild(thead);
  const tbody = document.createElement('tbody');
  const grades = GRADE_ORDER.filter((g) => dist[g] != null);
  if (!grades.length) {
    Object.keys(dist).forEach((g) => grades.push(g));
  }
  grades.forEach((g) => {
    const tr = document.createElement('tr');
    const pct = dist[g];
    if (g === 'F') tr.style.color = '#dc2626';
    else if (g === 'A+' || g === 'A' || g === 'A-') tr.style.color = '#16a34a';
    const tdG = document.createElement('td');
    tdG.textContent = g;
    const tdP = document.createElement('td');
    tdP.textContent = pct != null ? `${(+pct).toFixed(1)}%` : '—';
    tr.appendChild(tdG);
    tr.appendChild(tdP);
    tbody.appendChild(tr);
  });
  table.appendChild(tbody);
  container.appendChild(table);
}

function renderCourseTrends(courseName, metrics) {
  const ctxGpa = document.getElementById('courseGpaTrendChart');
  const ctxFail = document.getElementById('courseFailureTrendChart');
  if (courseGpaChart) courseGpaChart.destroy();
  if (courseFailureChart) courseFailureChart.destroy();

  if (!metrics.sheets || !metrics.sheets.length || typeof Chart === 'undefined') return;

  const sortedSheets = [...metrics.sheets].sort((a, b) => a.sheet.localeCompare(b.sheet));
  const labels = sortedSheets.map((s) => s.sheet);
  const gpaValues = sortedSheets.map((s) => (s.gpa != null ? s.gpa : null));
  const failValues = sortedSheets.map((s) => (s.failureRate != null ? s.failureRate : null));

  if (ctxGpa) {
    courseGpaChart = new Chart(ctxGpa.getContext('2d'), {
      type: 'line',
      data: {
        labels,
        datasets: [
          {
            label: 'Estimated GPA',
            data: gpaValues,
            borderColor: '#0ea5e9',
            backgroundColor: 'rgba(14, 165, 233, 0.15)',
            tension: 0.3,
            fill: true,
          },
        ],
      },
      options: {
        responsive: true,
        scales: {
          y: { beginAtZero: true, max: 4.0 },
        },
      },
    });
  }

  if (ctxFail) {
    courseFailureChart = new Chart(ctxFail.getContext('2d'), {
      type: 'line',
      data: {
        labels,
        datasets: [
          {
            label: 'Failure Rate %',
            data: failValues,
            borderColor: '#dc2626',
            backgroundColor: 'rgba(220, 38, 38, 0.15)',
            tension: 0.3,
            fill: true,
          },
        ],
      },
      options: {
        responsive: true,
        scales: {
          y: { beginAtZero: true, max: 100 },
        },
      },
    });
  }
}

function renderCourseRecommendations(courseEntry) {
  const container = document.getElementById('courseRecommendations');
  if (!container) return;
  container.innerHTML = '';

  const allRecs = new Set();
  Object.values(courseEntry.sheets || {}).forEach((s) => {
    (s.recommendations || []).forEach((r) => allRecs.add(r));
  });

  const recs = Array.from(allRecs);
  if (!recs.length) {
    const p = document.createElement('p');
    p.textContent = 'No specific recommendations generated. Maintain current course practices and continue monitoring.';
    container.appendChild(p);
    return;
  }

  const list = document.createElement('ul');
  list.className = 'plan-actions';
  recs.forEach((r) => {
    const li = document.createElement('li');
    li.textContent = r;
    list.appendChild(li);
  });

  const wrapper = document.createElement('div');
  wrapper.className = 'plan-card';
  const title = document.createElement('div');
  title.className = 'plan-course';
  title.textContent = courseEntry.name;
  wrapper.appendChild(title);
  wrapper.appendChild(list);
  container.appendChild(wrapper);
}

function findCourseKeyInStats(statsObj, courseName) {
  if (!statsObj || !courseName) return null;
  const exact = statsObj[courseName];
  if (exact !== undefined) return courseName;
  const normalized = String(courseName).trim().toLowerCase();
  for (const key of Object.keys(statsObj)) {
    if (String(key).trim().toLowerCase() === normalized) return key;
  }
  return null;
}

function renderCourseDeepStats(courseName, courseStatistics) {
  const container = document.getElementById('courseDeepStatsContainer');
  if (!container) return;
  container.innerHTML = '';
  if (!courseStatistics || typeof courseStatistics !== 'object') return;

  let deep = null;
  let fairness = null;
  let risk = null;
  for (const sheet of Object.keys(courseStatistics)) {
    const s = courseStatistics[sheet];
    const gdd = s && s.grade_distribution_deep;
    const key = gdd ? findCourseKeyInStats(gdd, courseName) : null;
    if (key) {
      deep = gdd[key];
      fairness = (s.fairness_indicators && s.fairness_indicators[key]) || (s.fairness_indicators && s.fairness_indicators[courseName]) || null;
      risk = (s.risk_modeling && s.risk_modeling[key]) || (s.risk_modeling && s.risk_modeling[courseName]) || null;
      break;
    }
  }
  if (!deep && !fairness && !risk) return;

  function card(title, items) {
    const el = document.createElement('div');
    el.className = 'kpi-card advanced-stat-card';
    let html = '<h3>' + escapeHtmlCR(title) + '</h3>';
    items.forEach(function (it) {
      html += '<p><span>' + escapeHtmlCR(it.label) + '</span> ' + (it.value != null ? escapeHtmlCR(it.value) : '—') + '</p>';
    });
    el.innerHTML = html;
    container.appendChild(el);
  }
  if (deep) {
    card('Grade Distribution Deep Metrics', [
      { label: 'MAD', value: deep.median_absolute_deviation != null ? deep.median_absolute_deviation.toFixed(3) : null },
      { label: 'Trimmed mean (5%)', value: deep.trimmed_mean_5 != null ? deep.trimmed_mean_5.toFixed(2) : null },
      { label: 'Trimmed mean (10%)', value: deep.trimmed_mean_10 != null ? deep.trimmed_mean_10.toFixed(2) : null },
      { label: 'Mode frequency %', value: deep.mode_frequency_pct != null ? deep.mode_frequency_pct.toFixed(1) + '%' : null },
      { label: 'Concentration ratio', value: deep.grade_concentration_ratio != null ? deep.grade_concentration_ratio.toFixed(3) : null },
      { label: 'Inequality (Gini)', value: deep.inequality_index_gini != null ? deep.inequality_index_gini.toFixed(3) : null },
    ]);
  }
  if (fairness) {
    card('Fairness Indicators', [
      { label: 'Grade inflation index', value: fairness.grade_inflation_index != null ? fairness.grade_inflation_index.toFixed(3) : null },
      { label: 'Grade deflation index', value: fairness.grade_deflation_index != null ? fairness.grade_deflation_index.toFixed(3) : null },
      { label: 'Z-score vs program', value: fairness.z_score_vs_program != null ? fairness.z_score_vs_program.toFixed(2) : null },
      { label: 'Difficulty index', value: fairness.difficulty_index != null ? fairness.difficulty_index.toFixed(3) : null },
    ]);
  }
  if (risk) {
    card('Risk Modeling', [
      { label: 'Probability passing', value: risk.probability_passing != null ? (risk.probability_passing * 100).toFixed(1) + '%' : null },
      { label: 'Hazard ratio (failure)', value: risk.hazard_ratio_failure != null ? risk.hazard_ratio_failure.toFixed(2) : null },
    ]);
  }
}

function onCourseSelected(courseName) {
  if (!courseIndex || !courseName) return;
  const entry = courseIndex[courseName];
  if (!entry) return;
  const metrics = aggregateCourseMetrics(entry);
  if (!metrics) return;
  selectedCourseName = courseName;

  const panels = document.getElementById('course-report-panels');
  if (panels) panels.hidden = false;

  renderCourseKpis(metrics);
  renderCourseQuality(metrics);
  renderCourseGradeDistribution(metrics);
  renderCourseGradeBreakdown(metrics);
  renderCourseTrends(courseName, metrics);
  renderCourseRecommendations(entry);
  const courseStatistics = (courseLastResult && courseLastResult.course_statistics) || {};
  renderCourseDeepStats(courseName, courseStatistics);
}

function exportCoursePdf() {
  const container = document.getElementById('course-results');
  if (!container) return;
  if (!courseLastResult) {
    alert('Please upload and analyze a file first.');
    return;
  }
  const btns = [
    document.getElementById('courseExportPdfBtn'),
    document.getElementById('courseExportPdfSecondaryBtn'),
  ].filter(Boolean);
  btns.forEach((b) => {
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
        'course-report-' + new Date().toISOString().slice(0, 10) + '.pdf';
      pdf.save(filename);
    } catch (err) {
      console.error(err);
      alert('An error occurred while exporting.');
    } finally {
      btns.forEach((b) => {
        b.disabled = false;
        b.textContent =
          b.id === 'courseExportPdfBtn' ? 'Download PDF' : 'Download Course PDF';
      });
    }
  }, 300);
}

function exportCourseExcel() {
  if (!courseIndex) {
    alert('Please upload and analyze a file first.');
    return;
  }
  const rows = [
    [
      'Course',
      'Total Enrollment',
      'Excellence Rate %',
      'Failure Rate %',
      'Estimated GPA',
      'Max Risk Score %',
    ],
  ];
  Object.values(courseIndex).forEach((entry) => {
    const metrics = aggregateCourseMetrics(entry);
    if (!metrics) return;
    rows.push([
      entry.name,
      metrics.enrollment ?? '',
      metrics.excellenceRate ?? '',
      metrics.failureRate ?? '',
      metrics.gpa ?? '',
      metrics.riskScore ?? '',
    ]);
  });
  const csv = rows.map((r) => r.join(',')).join('\n');
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = 'course-report-summary.csv';
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

let selectedCourseName = null;

function _getFormVal(id) {
  const el = document.getElementById(id);
  return el ? el.value.trim() : '';
}

/** Build the DOCX payload for one course: shared form fields + per-course auto-detected data. */
function buildCourseReportPayload(courseName, entry) {
  const metrics = entry && aggregateCourseMetrics(entry);
  if (!metrics) return null;

  const recommendations = [];
  Object.values(entry.sheets || {}).forEach((s) => {
    (s.recommendations || []).forEach((r) => {
      if (!recommendations.includes(r)) recommendations.push(r);
    });
  });

  return {
    course: courseName,
    course_title: entry.courseTitle || courseName,
    course_code: entry.courseCode || _getFormVal('crfCourseCode') || '',
    academic_year: entry.academicYear || _getFormVal('crfAcademicYear') || '',
    semester: entry.semester || _getFormVal('crfSemester') || '',
    department: _getFormVal('crfDepartment') || '',
    credit_hours: _getFormVal('crfCreditHours') || '',
    course_type: _getFormVal('crfCourseType') || '',
    level: _getFormVal('crfLevel') || '',
    program: entry.programTitle || _getFormVal('crfProgram') || '',
    faculty: _getFormVal('crfFaculty') || entry.facultyHint || '',
    university: _getFormVal('crfUniversity') || '',
    coordinator: entry.instructor || _getFormVal('crfCoordinator') || '',
    department_head: _getFormVal('crfDeptHead') || '',
    approval_date: _getFormVal('crfApprovalDate') || '',
    enrollment: metrics.enrollment,
    gpa: metrics.gpa,
    failure_rate: metrics.failureRate,
    excellence_rate: metrics.excellenceRate,
    risk_score: metrics.riskScore,
    grade_distribution: metrics.gradeDistribution,
    recommendations,
  };
}

function exportCourseDocx() {
  if (!courseIndex || !selectedCourseName) {
    alert('Please upload data and select a course first.');
    return;
  }
  const entry = courseIndex[selectedCourseName];
  const payload = entry && buildCourseReportPayload(selectedCourseName, entry);
  if (!payload) {
    alert('No metrics available for the selected course.');
    return;
  }

  const btn = document.getElementById('courseExportDocxBtn');
  if (btn) {
    btn.disabled = true;
    btn.textContent = 'Generating...';
  }

  fetch(`${apiUrlCourse}/export-course-docx`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
    .then(async (resp) => {
      if (!resp.ok) {
        const err = await resp.json().catch(() => ({ detail: resp.statusText }));
        throw new Error(err.detail || `HTTP ${resp.status}`);
      }
      return resp.blob();
    })
    .then((blob) => {
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `Course_Report_${selectedCourseName.replace(/[^a-z0-9_-]+/gi, '_')}.docx`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    })
    .catch((err) => {
      console.error(err);
      alert(err.message || 'Failed to generate the course report.');
    })
    .finally(() => {
      if (btn) {
        btn.disabled = false;
        btn.textContent = 'Generate Report for Selected Course (DOCX)';
      }
    });
}

function exportAllCourseDocx() {
  if (!courseIndex || !Object.keys(courseIndex).length) {
    alert('Please upload and analyze a file first.');
    return;
  }

  const courses = Object.entries(courseIndex)
    .map(([name, entry]) => buildCourseReportPayload(name, entry))
    .filter(Boolean);

  if (!courses.length) {
    alert('No course metrics available to export.');
    return;
  }

  const btn = document.getElementById('courseExportDocxAllBtn');
  if (btn) {
    btn.disabled = true;
    btn.textContent = `Generating ${courses.length} reports...`;
  }

  fetch(`${apiUrlCourse}/export-course-docx-bulk`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ courses }),
  })
    .then(async (resp) => {
      if (!resp.ok) {
        const err = await resp.json().catch(() => ({ detail: resp.statusText }));
        throw new Error(err.detail || `HTTP ${resp.status}`);
      }
      return resp.blob();
    })
    .then((blob) => {
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'Course_Reports.zip';
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    })
    .catch((err) => {
      console.error(err);
      alert(err.message || 'Failed to generate course reports.');
    })
    .finally(() => {
      if (btn) {
        btn.disabled = false;
        btn.textContent = 'Generate Reports for ALL Courses (ZIP)';
      }
    });
}

/** Render the high-success-rate table above the course selector. */
function renderSuccessCourses(index, threshold) {
  threshold = threshold != null ? threshold : 60;
  const section = document.getElementById('success-overview-section');
  const container = document.getElementById('successCoursesContainer');
  const desc = document.getElementById('successOverviewDesc');
  if (!container || !section) return;

  container.innerHTML = '';

  // Collect courses above the threshold
  const passing = [];
  Object.entries(index).forEach(([name, entry]) => {
    const metrics = aggregateCourseMetrics(entry);
    if (!metrics) return;
    const failRate = metrics.failureRate != null ? parseFloat(metrics.failureRate) : null;
    if (failRate == null) return;
    const successRate = 100 - failRate;
    if (successRate >= threshold) {
      passing.push({ name, metrics, successRate });
    }
  });

  const total = Object.keys(index).length;
  section.hidden = false;

  if (desc) {
    desc.textContent = `${passing.length} of ${total} detected courses have a success rate ≥ ${threshold}%.`;
  }

  if (!passing.length) {
    const p = document.createElement('p');
    p.className = 'section-desc';
    p.textContent = `No courses found with a success rate ≥ ${threshold}%. Try lowering the threshold.`;
    container.appendChild(p);
    return;
  }

  // Sort best first
  passing.sort((a, b) => b.successRate - a.successRate);

  const table = document.createElement('table');
  table.className = 'data-table';

  // Header
  const thead = document.createElement('thead');
  const headerRow = document.createElement('tr');
  ['#', 'Course', 'Success %', 'Excellence %', 'Failure %', 'GPA', 'Enrollment'].forEach((label) => {
    const th = document.createElement('th');
    th.textContent = label;
    if (label === '#') th.className = 'row-num';
    headerRow.appendChild(th);
  });
  thead.appendChild(headerRow);
  table.appendChild(thead);

  // Body
  const tbody = document.createElement('tbody');
  passing.forEach((item, i) => {
    const tr = document.createElement('tr');
    if (item.successRate >= 90) tr.className = 'success-tier-high';
    else if (item.successRate >= 75) tr.className = 'success-tier-mid';
    const cells = [
      { text: String(i + 1), cls: 'row-num' },
      { text: item.name },
      { text: item.successRate.toFixed(1) + '%' },
      { text: item.metrics.excellenceRate != null ? item.metrics.excellenceRate + '%' : '—' },
      { text: item.metrics.failureRate != null ? item.metrics.failureRate + '%' : '—' },
      { text: item.metrics.gpa ?? '—' },
      { text: item.metrics.enrollment != null ? String(item.metrics.enrollment) : '—' },
    ];
    cells.forEach(({ text, cls }) => {
      const td = document.createElement('td');
      td.textContent = text;  // textContent prevents XSS
      if (cls) td.className = cls;
      tr.appendChild(td);
    });
    tbody.appendChild(tr);
  });
  table.appendChild(tbody);
  container.appendChild(table);
}

function initCoursePage() {
  const input = document.getElementById('courseExcelInput');
  const zone = document.getElementById('course-upload-zone');
  const select = document.getElementById('courseSelect');
  const primaryPdfBtn = document.getElementById('courseExportPdfBtn');
  const secondaryPdfBtn = document.getElementById('courseExportPdfSecondaryBtn');
  const excelBtn = document.getElementById('courseExportExcelBtn');

  function _handleCourseUpload(files) {
    const fileList = Array.isArray(files) ? files : [files];
    const valid = fileList.filter((f) => f && f.name.toLowerCase().endsWith('.xlsx'));
    if (!valid.length) return;
    _showCourseUploadHint(valid);
    setCourseLoading(true);
    uploadCourseFile(valid)
      .then((res) => {
        courseLastResult = res;
        window.courseLastResult = res;
        courseIndex = buildCourseIndex(res);
        populateCourseDropdown(courseIndex);
        renderSuccessCourses(courseIndex, _getThreshold());
      })
      .catch((err) => {
        console.error(err);
        const msg = err?.message || err?.detail || 'Error while analyzing Excel file.';
        alert(msg);
      })
      .finally(() => setCourseLoading(false));
  }

  function _getThreshold() {
    const inp = document.getElementById('successThresholdInput');
    const val = inp ? parseFloat(inp.value) : 60;
    return isNaN(val) ? 60 : Math.max(0, Math.min(100, val));
  }

  if (input) {
    input.addEventListener('change', (e) => {
      const files = Array.from(e.target.files || []);
      _handleCourseUpload(files);
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
      const files = Array.from((e.dataTransfer && e.dataTransfer.files) || []);
      _handleCourseUpload(files);
    });
  }

  if (select) {
    select.addEventListener('change', (e) => {
      const value = e.target.value;
      if (value) onCourseSelected(value);
    });
  }

  const thresholdBtn = document.getElementById('successThresholdBtn');
  const thresholdInp = document.getElementById('successThresholdInput');
  function _applyThreshold() {
    if (!courseIndex) return;
    renderSuccessCourses(courseIndex, _getThreshold());
  }
  if (thresholdBtn) thresholdBtn.addEventListener('click', _applyThreshold);
  if (thresholdInp) thresholdInp.addEventListener('keydown', (e) => { if (e.key === 'Enter') _applyThreshold(); });

  const hookPdf = (btn) => {
    if (!btn) return;
    btn.addEventListener('click', exportCoursePdf);
  };
  hookPdf(primaryPdfBtn);
  hookPdf(secondaryPdfBtn);

  if (excelBtn) {
    excelBtn.addEventListener('click', exportCourseExcel);
  }

  const docxBtn = document.getElementById('courseExportDocxBtn');
  if (docxBtn) {
    docxBtn.addEventListener('click', exportCourseDocx);
  }

  const docxAllBtn = document.getElementById('courseExportDocxAllBtn');
  if (docxAllBtn) {
    docxAllBtn.addEventListener('click', exportAllCourseDocx);
  }
}

document.addEventListener('DOMContentLoaded', initCoursePage);

