/**
 * QA Forecast Decisions renderer — shared by dashboard and program report.
 * Renders forecast data as senior-QA-style action decisions directly on the page.
 */

(function (global) {
  'use strict';

  /* ── QA decision tables ─────────────────────────────────────────────── */

  function qaGpa(value, direction) {
    if (direction === 'declining' || direction === 'worsening') {
      if (value < 2.0) return { status: 'CRITICAL', level: 'critical',
        action: 'Immediate escalation required. Forecasted GPA falls below the minimum academic threshold. Convene an emergency academic committee review and suspend non-critical curriculum changes until root cause is identified.' };
      if (value < 2.5) return { status: 'HIGH RISK', level: 'danger',
        action: 'Trigger departmental intervention plan. Assign academic advisors to at-risk cohorts, review grading consistency across courses, and schedule mid-semester progress checks.' };
      return { status: 'WATCH', level: 'warning',
        action: 'Place program on QA monitoring watch-list. Issue formal notification to department head. Review teaching effectiveness scores and cross-reference with failure rate trend.' };
    }
    if (direction === 'stable') {
      if (value >= 3.0) return { status: 'ACCEPTABLE', level: 'pass',
        action: 'No immediate action required. Maintain current instructional approach. Schedule routine semester-end review to confirm stability.' };
      return { status: 'BORDERLINE', level: 'warning',
        action: 'No escalation yet, but marginal performance must be tracked. Issue a precautionary advisory and increase monitoring frequency to bi-weekly.' };
    }
    if (value >= 3.0) return { status: 'STRONG', level: 'pass',
      action: 'Program performing above benchmark. Document current practices as best-practice templates for other programs. No corrective action needed.' };
    return { status: 'IMPROVING', level: 'pass',
      action: 'Positive trajectory confirmed. Reinforce support structures currently in place. Conduct a contributing-factors audit to sustain the improvement.' };
  }

  function qaFailure(value, direction) {
    if (direction === 'worsening' || direction === 'increasing') {
      if (value > 50) return { status: 'CRITICAL', level: 'critical',
        action: 'Failure rate exceeds 50% — program integrity at risk. Immediate halt on new enrolments to affected courses pending a full academic audit. Escalate to accreditation compliance officer.' };
      if (value > 35) return { status: 'HIGH RISK', level: 'danger',
        action: 'Failure rate trending into red zone. Mandate supplementary teaching sessions, review assessment design for unintended difficulty bias, and implement early-warning student identification protocol.' };
      if (value > 20) return { status: 'ELEVATED', level: 'warning',
        action: 'Failure rate rising beyond acceptable band. Issue a formal quality alert. Require course coordinators to submit a remediation plan within 14 days.' };
      return { status: 'WATCH', level: 'warning',
        action: 'Mild upward trend detected. Log in QA register and schedule a targeted course review at the end of the current semester.' };
    }
    if (direction === 'stable') {
      if (value <= 15) return { status: 'ACCEPTABLE', level: 'pass',
        action: 'Failure rate stable within target range. Continue standard monitoring protocol.' };
      return { status: 'BORDERLINE', level: 'warning',
        action: 'Failure rate stable but above preferred ceiling. Maintain heightened monitoring. Include in next department quality report.' };
    }
    if (value <= 10) return { status: 'EXCELLENT', level: 'pass',
      action: 'Failure rate at healthy levels and improving. Validate against grade inflation risk — confirm assessment rigour is maintained.' };
    return { status: 'IMPROVING', level: 'pass',
      action: 'Failure rate declining — intervention measures are working. Document effective practices and continue current support strategy.' };
  }

  function qaExcellence(value, direction) {
    if (direction === 'declining' || direction === 'worsening') {
      if (value < 5) return { status: 'CRITICAL', level: 'critical',
        action: 'Excellence rate approaching near-zero. Investigate whether assessment design suppresses high achievement. Review honours criteria and challenge provisions for advanced students.' };
      if (value < 10) return { status: 'CONCERN', level: 'danger',
        action: 'Excellence pipeline is thinning. Introduce enrichment tracks or challenge assignments. Alert student services to proactively engage high-potential students.' };
      return { status: 'WATCH', level: 'warning',
        action: 'Declining excellence trend logged. Issue advisory to teaching staff. Review curriculum stretch goals and top-performer support mechanisms.' };
    }
    if (direction === 'stable') {
      if (value >= 20) return { status: 'STRONG', level: 'pass',
        action: 'Excellence rate stable at a high level. No action required. Document academic culture factors supporting this outcome.' };
      return { status: 'ACCEPTABLE', level: 'pass',
        action: 'Excellence rate stable within typical range. No action required at this time.' };
    }
    if (value >= 20) return { status: 'EXCELLENT', level: 'pass',
      action: 'Excellence rate high and improving. Program producing strong academic outcomes. Consider nominating for institutional recognition.' };
    return { status: 'IMPROVING', level: 'pass',
      action: 'Excellence rate trending upward. Reinforce practices driving this and share teaching approach as a model for underperforming programs.' };
  }

  /* ── Verdict ─────────────────────────────────────────────────────────── */
  function verdict(badCount, total) {
    if (badCount === 0) return {
      level: 'pass',
      text: 'QA VERDICT: PASS',
      sub: 'All forecast indicators are within acceptable bounds. Continue standard monitoring.'
    };
    if (badCount === 1) return {
      level: 'warning',
      text: 'QA VERDICT: CONDITIONAL PASS',
      sub: 'One indicator requires attention. Act on the flagged item before the next review cycle.'
    };
    if (badCount === 2) return {
      level: 'danger',
      text: 'QA VERDICT: REQUIRES INTERVENTION',
      sub: 'Multiple indicators are off-track. Escalate to department head and initiate a formal QA review within 30 days.'
    };
    return {
      level: 'critical',
      text: 'QA VERDICT: PROGRAM UNDER REVIEW',
      sub: 'All forecast indicators signal deterioration. Convene an emergency academic board session. Immediate corrective action plan required.'
    };
  }

  /* ── CSS (injected once) ─────────────────────────────────────────────── */
  var CSS = [
    '.qa-fc-wrap{display:flex;flex-direction:column;gap:16px;margin-top:8px;}',
    '.qa-fc-card{border-radius:12px;overflow:hidden;box-shadow:0 2px 10px rgba(15,23,42,.09);}',
    '.qa-fc-header{display:flex;align-items:center;justify-content:space-between;padding:14px 18px;gap:10px;}',
    '.qa-fc-header-left{display:flex;align-items:center;gap:12px;}',
    '.qa-fc-icon{font-size:22px;flex-shrink:0;line-height:1;}',
    '.qa-fc-metric{font-size:15px;font-weight:700;color:#fff;}',
    '.qa-fc-value{font-size:13px;color:rgba(255,255,255,.85);margin-top:2px;}',
    '.qa-fc-badge{font-size:11px;font-weight:700;letter-spacing:.5px;padding:4px 10px;border-radius:20px;',
      'background:rgba(255,255,255,.2);color:#fff;white-space:nowrap;}',
    '.qa-fc-body{padding:14px 18px;background:#fff;}',
    '.qa-fc-action{font-size:14px;line-height:1.7;color:#1e293b;}',
    '.qa-fc-action::before{content:"→ ";font-weight:700;margin-right:2px;}',
    '.qa-fc-meta{display:flex;gap:16px;margin-top:10px;padding-top:10px;border-top:1px solid #f1f5f9;}',
    '.qa-fc-meta span{font-size:12px;color:#64748b;}',
    '.qa-fc-meta strong{color:#1e293b;}',

    '.qa-fc-verdict{border-radius:12px;padding:16px 20px;display:flex;align-items:flex-start;gap:14px;}',
    '.qa-fc-verdict-icon{font-size:26px;flex-shrink:0;line-height:1;margin-top:2px;}',
    '.qa-fc-verdict-title{font-size:15px;font-weight:800;letter-spacing:.3px;}',
    '.qa-fc-verdict-sub{font-size:13px;margin-top:4px;line-height:1.6;}',

    /* level colours */
    '.qa-lv-critical .qa-fc-header{background:linear-gradient(135deg,#7f1d1d,#dc2626);}',
    '.qa-lv-danger   .qa-fc-header{background:linear-gradient(135deg,#92400e,#ea580c);}',
    '.qa-lv-warning  .qa-fc-header{background:linear-gradient(135deg,#78350f,#d97706);}',
    '.qa-lv-pass     .qa-fc-header{background:linear-gradient(135deg,#14532d,#16a34a);}',

    '.qa-lv-critical.qa-fc-verdict{background:#fef2f2;border:1.5px solid #fca5a5;}',
    '.qa-lv-critical .qa-fc-verdict-title{color:#991b1b;}',
    '.qa-lv-critical .qa-fc-verdict-sub{color:#7f1d1d;}',

    '.qa-lv-danger.qa-fc-verdict{background:#fff7ed;border:1.5px solid #fed7aa;}',
    '.qa-lv-danger .qa-fc-verdict-title{color:#9a3412;}',
    '.qa-lv-danger .qa-fc-verdict-sub{color:#7c2d12;}',

    '.qa-lv-warning.qa-fc-verdict{background:#fffbeb;border:1.5px solid #fde68a;}',
    '.qa-lv-warning .qa-fc-verdict-title{color:#92400e;}',
    '.qa-lv-warning .qa-fc-verdict-sub{color:#78350f;}',

    '.qa-lv-pass.qa-fc-verdict{background:#f0fdf4;border:1.5px solid #86efac;}',
    '.qa-lv-pass .qa-fc-verdict-title{color:#15803d;}',
    '.qa-lv-pass .qa-fc-verdict-sub{color:#14532d;}',

    '.qa-fc-unavail{padding:18px;text-align:center;color:#94a3b8;font-size:14px;',
      'background:#f8fafc;border-radius:12px;border:1.5px dashed #e2e8f0;}',
  ].join('');

  function injectCss() {
    if (document.getElementById('qa-fc-styles')) return;
    var s = document.createElement('style');
    s.id = 'qa-fc-styles';
    s.textContent = CSS;
    document.head.appendChild(s);
  }

  /* ── Icon map ────────────────────────────────────────────────────────── */
  var ICONS = { critical: '🚨', danger: '🔴', warning: '⚠️', pass: '✅' };
  var VERDICT_ICONS = { critical: '🚨', danger: '🔴', warning: '🟠', pass: '✅' };

  function esc(s) {
    return String(s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;')
      .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  /* ── Build one indicator card ────────────────────────────────────────── */
  function buildCard(metricLabel, valueStr, data, qa) {
    var dir  = (data && data.trend_direction) || 'stable';
    var r2   = (data && data.r_squared   != null) ? data.r_squared.toFixed(3)   : null;
    var slope= (data && data.slope       != null) ? data.slope.toFixed(4)        : null;
    var icon = ICONS[qa.level] || '➡️';

    var dirArrow = dir === 'improving' ? '↑' : (dir === 'declining' || dir === 'worsening') ? '↓' : '→';

    var card = document.createElement('div');
    card.className = 'qa-fc-card qa-lv-' + qa.level;

    var metaHtml = '';
    if (r2)    metaHtml += '<span>Fit quality: <strong>R²=' + esc(r2) + '</strong></span>';
    if (slope) metaHtml += '<span>Slope / period: <strong>' + esc((parseFloat(slope) > 0 ? '+' : '') + slope) + '</strong></span>';
    metaHtml += '<span>Trend: <strong>' + esc(dirArrow + ' ' + dir) + '</strong></span>';

    card.innerHTML =
      '<div class="qa-fc-header">' +
        '<div class="qa-fc-header-left">' +
          '<div class="qa-fc-icon">' + icon + '</div>' +
          '<div>' +
            '<div class="qa-fc-metric">' + esc(metricLabel) + '</div>' +
            '<div class="qa-fc-value">Forecast: <strong>' + esc(valueStr) + '</strong></div>' +
          '</div>' +
        '</div>' +
        '<div class="qa-fc-badge">' + esc(qa.status) + '</div>' +
      '</div>' +
      '<div class="qa-fc-body">' +
        '<div class="qa-fc-action">' + esc(qa.action) + '</div>' +
        (metaHtml ? '<div class="qa-fc-meta">' + metaHtml + '</div>' : '') +
      '</div>';

    return card;
  }

  /* ── Main render function (called by page JS) ───────────────────────── */
  function renderQaForecast(containerId, fc) {
    injectCss();
    var container = document.getElementById(containerId);
    if (!container) return;
    container.innerHTML = '';

    if (!fc || !fc.available) {
      var reason = (fc && fc.reason) || 'Upload data from 2 or more semesters to enable trend forecasting.';
      container.innerHTML =
        '<div class="qa-fc-unavail">' +
        '📊 Trend forecast not available — ' + esc(reason) + '</div>';
      return;
    }

    var wrap = document.createElement('div');
    wrap.className = 'qa-fc-wrap';

    var badCount = 0;
    var totalCount = 0;

    var indicators = [
      {
        key: 'gpa_forecast',
        label: 'GPA Trend',
        unit: '/ 4.00',
        fn: qaGpa,
        fmt: function(v) { return v.toFixed(2) + ' / 4.00'; },
      },
      {
        key: 'failure_rate_forecast',
        label: 'Failure Rate',
        unit: '%',
        fn: qaFailure,
        fmt: function(v) { return v.toFixed(1) + '%'; },
      },
      {
        key: 'excellence_rate_forecast',
        label: 'Excellence Rate',
        unit: '%',
        fn: qaExcellence,
        fmt: function(v) { return v.toFixed(1) + '%'; },
      },
    ];

    indicators.forEach(function(ind) {
      var data = fc[ind.key];
      if (!data) return;
      var nv = data.predicted_next && data.predicted_next.length ? data.predicted_next[0] : null;
      if (nv == null) return;
      totalCount++;
      var qa = ind.fn(nv, data.trend_direction || 'stable');
      if (['critical','danger','warning'].indexOf(qa.level) !== -1 && qa.status !== 'ACCEPTABLE' && qa.status !== 'BORDERLINE') {
        // Only flag non-pass items as bad for the verdict
      }
      if (['CRITICAL','HIGH RISK','ELEVATED','WATCH','BORDERLINE','CONCERN','WATCH'].indexOf(qa.status) !== -1) {
        badCount++;
      }
      wrap.appendChild(buildCard(ind.label, ind.fmt(nv), data, qa));
    });

    /* Verdict */
    if (totalCount > 0) {
      var v = verdict(badCount, totalCount);
      var vDiv = document.createElement('div');
      vDiv.className = 'qa-fc-verdict qa-lv-' + v.level;
      vDiv.innerHTML =
        '<div class="qa-fc-verdict-icon">' + (VERDICT_ICONS[v.level] || '✅') + '</div>' +
        '<div>' +
          '<div class="qa-fc-verdict-title">' + esc(v.text) + '</div>' +
          '<div class="qa-fc-verdict-sub">' + esc(v.sub) + '</div>' +
        '</div>';
      wrap.appendChild(vDiv);
    }

    container.appendChild(wrap);
  }

  /* Export */
  global.renderQaForecast = renderQaForecast;

})(window);
