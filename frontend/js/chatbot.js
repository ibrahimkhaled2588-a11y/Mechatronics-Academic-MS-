/**
 * Academic Analytics Chatbot — self-contained widget.
 * Injects its own CSS so it works on every page with no external dependency.
 */
(function () {
  'use strict';

  /* ── Inject styles ─────────────────────────────────────────────────── */
  var CSS = [
    '#cb-toggle{',
      'position:fixed;bottom:24px;right:24px;z-index:2147483647;',
      'width:56px;height:56px;border-radius:50%;',
      'background:linear-gradient(135deg,#0f172a 0%,#1e40af 100%);',
      'color:#fff;border:none;cursor:pointer;',
      'display:flex;align-items:center;justify-content:center;',
      'box-shadow:0 4px 20px rgba(15,23,42,.4);',
      'transition:transform .2s,box-shadow .2s;',
      'font-size:22px;line-height:1;padding:0;',
    '}',
    '#cb-toggle:hover{transform:scale(1.08);box-shadow:0 6px 28px rgba(15,23,42,.5);}',
    '#cb-toggle.cb-active{background:linear-gradient(135deg,#1e40af 0%,#0ea5e9 100%);}',

    '#cb-window{',
      'position:fixed;bottom:90px;right:24px;z-index:2147483646;',
      'width:370px;max-width:calc(100vw - 32px);',
      'height:560px;max-height:calc(100vh - 110px);',
      'background:#fff;border-radius:18px;',
      'box-shadow:0 16px 56px rgba(15,23,42,.25),0 2px 8px rgba(15,23,42,.12);',
      'display:flex;flex-direction:column;overflow:hidden;',
      'transform:scale(.9) translateY(16px);opacity:0;pointer-events:none;',
      'transition:transform .25s cubic-bezier(.34,1.56,.64,1),opacity .2s;',
      'font-family:"Plus Jakarta Sans",system-ui,sans-serif;',
    '}',
    '#cb-window.cb-open{transform:scale(1) translateY(0);opacity:1;pointer-events:all;}',

    '#cb-header{',
      'display:flex;align-items:center;justify-content:space-between;',
      'padding:14px 16px;flex-shrink:0;',
      'background:linear-gradient(135deg,#0f172a 0%,#1e40af 100%);color:#fff;',
    '}',
    '.cb-header-left{display:flex;align-items:center;gap:10px;}',
    '.cb-avatar{',
      'width:38px;height:38px;background:rgba(255,255,255,.18);border-radius:50%;',
      'display:flex;align-items:center;justify-content:center;font-size:18px;flex-shrink:0;',
    '}',
    '.cb-title{font-weight:700;font-size:15px;line-height:1.2;}',
    '.cb-sub{font-size:11px;opacity:.72;margin-top:1px;}',
    '#cb-close{',
      'background:none;border:none;color:#fff;cursor:pointer;',
      'font-size:16px;opacity:.75;padding:4px 6px;border-radius:6px;line-height:1;',
    '}',
    '#cb-close:hover{opacity:1;background:rgba(255,255,255,.18);}',

    '#cb-messages{',
      'flex:1;overflow-y:auto;padding:14px 12px;',
      'display:flex;flex-direction:column;gap:10px;background:#f8fafc;',
      'scroll-behavior:smooth;',
    '}',
    '.cb-row{display:flex;align-items:flex-end;gap:7px;}',
    '.cb-user{justify-content:flex-end;}',
    '.cb-bot{justify-content:flex-start;}',
    '.cb-bot-avatar{',
      'width:28px;height:28px;background:#dbeafe;border-radius:50%;flex-shrink:0;',
      'display:flex;align-items:center;justify-content:center;font-size:14px;',
    '}',
    '.cb-bubble{',
      'max-width:82%;padding:10px 13px;border-radius:16px;',
      'font-size:13.5px;line-height:1.6;word-break:break-word;',
    '}',
    '.cb-user .cb-bubble{',
      'background:linear-gradient(135deg,#1e40af,#0ea5e9);color:#fff;',
      'border-bottom-right-radius:4px;',
    '}',
    '.cb-bot .cb-bubble{',
      'background:#fff;color:#1e293b;',
      'border:1px solid #e2e8f0;border-bottom-left-radius:4px;',
      'box-shadow:0 1px 4px rgba(15,23,42,.07);',
    '}',
    '.cb-bot .cb-bubble strong{color:#1e40af;}',
    '.cb-bot .cb-bubble em{color:#64748b;font-style:italic;}',
    '.cb-indent{padding-left:14px;color:#475569;font-size:13px;}',

    '.cb-typing{display:flex;gap:5px;align-items:center;padding:3px 0;}',
    '.cb-typing span{',
      'width:7px;height:7px;background:#94a3b8;border-radius:50%;',
      'animation:cbBounce 1.2s infinite ease-in-out;',
    '}',
    '.cb-typing span:nth-child(2){animation-delay:.2s;}',
    '.cb-typing span:nth-child(3){animation-delay:.4s;}',
    '@keyframes cbBounce{0%,80%,100%{transform:translateY(0)}40%{transform:translateY(-7px)}}',

    '#cb-quick{',
      'display:flex;flex-wrap:wrap;gap:6px;padding:8px 12px 4px;',
      'background:#f8fafc;flex-shrink:0;',
    '}',
    '.cb-chip{',
      'background:#e0e7ff;color:#1e40af;border:none;border-radius:20px;',
      'padding:4px 11px;font-size:12px;cursor:pointer;',
      'transition:background .15s;white-space:nowrap;',
      'font-family:inherit;',
    '}',
    '.cb-chip:hover{background:#c7d2fe;}',

    '#cb-input-row{',
      'display:flex;gap:8px;padding:10px 12px;',
      'border-top:1px solid #e2e8f0;background:#fff;flex-shrink:0;',
    '}',
    '#cb-input{',
      'flex:1;border:1.5px solid #cbd5e1;border-radius:22px;',
      'padding:9px 14px;font-size:13.5px;outline:none;',
      'background:#f8fafc;color:#1e293b;font-family:inherit;',
      'transition:border-color .15s;',
    '}',
    '#cb-input:focus{border-color:#1e40af;background:#fff;}',
    '#cb-send{',
      'width:40px;height:40px;border-radius:50%;flex-shrink:0;',
      'background:linear-gradient(135deg,#1e40af,#0ea5e9);color:#fff;',
      'border:none;cursor:pointer;',
      'display:flex;align-items:center;justify-content:center;',
      'transition:opacity .15s,transform .15s;',
    '}',
    '#cb-send:hover{opacity:.88;transform:scale(1.07);}',
    '#cb-send:disabled{opacity:.4;cursor:not-allowed;transform:none;}',
    '@media(max-width:480px){',
      '#cb-window{width:calc(100vw - 24px);right:12px;bottom:80px;}',
      '#cb-toggle{right:12px;bottom:12px;}',
    '}',
  ].join('');

  function injectStyles() {
    if (document.getElementById('cb-styles')) return;
    var style = document.createElement('style');
    style.id = 'cb-styles';
    style.textContent = CSS;
    document.head.appendChild(style);
  }

  /* ── Helpers ──────────────────────────────────────────────────────── */
  var QUICK_QS = [
    'What is the overall GPA?',
    'Which courses have the highest failure rate?',
    'Show me high-risk courses',
    'What is the data quality score?',
    'What does the trend forecast say?',
    'What is the cohort retention rate?',
    'Show me all alerts',
    'What actions are recommended?',
    'Which courses have the best excellence rate?',
    'What is the dropout risk?',
  ];

  function getContext() {
    return window.programLastResult
        || window.courseLastResult
        || window._dashboardLastResult
        || null;
  }

  function renderMd(raw) {
    var lines = (raw || '').split('\n');
    var html = lines.map(function (line) {
      var s = line
        .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
      s = s.replace(/\*\*([^*\n]+)\*\*/g, '<strong>$1</strong>');
      s = s.replace(/_([^_\n]+)_/g, '<em>$1</em>');
      if (/^\s+(→|•)/.test(line)) {
        return '<div class="cb-indent">' + s.trim() + '</div>';
      }
      return s;
    });
    var div = document.createElement('div');
    div.innerHTML = html.join('<br>');
    return div;
  }

  /* ── Build DOM ────────────────────────────────────────────────────── */
  function buildWidget() {
    var btn = document.createElement('button');
    btn.id   = 'cb-toggle';
    btn.type = 'button';
    btn.title = 'Academic Assistant';
    btn.innerHTML = '💬';

    var win = document.createElement('div');
    win.id = 'cb-window';
    win.innerHTML = [
      '<div id="cb-header">',
        '<div class="cb-header-left">',
          '<div class="cb-avatar">🎓</div>',
          '<div>',
            '<div class="cb-title">Academic Assistant</div>',
            '<div class="cb-sub">Academic Reports &middot; Department Analytics</div>',
          '</div>',
        '</div>',
        '<button id="cb-close" type="button">✕</button>',
      '</div>',
      '<div id="cb-messages"></div>',
      '<div id="cb-quick"></div>',
      '<div id="cb-input-row">',
        '<input id="cb-input" type="text" placeholder="Ask about the report…" autocomplete="off" maxlength="300"/>',
        '<button id="cb-send" type="button">',
          '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" ',
          'stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" style="pointer-events:none">',
          '<line x1="22" y1="2" x2="11" y2="13"/>',
          '<polygon points="22 2 15 22 11 13 2 9 22 2"/>',
          '</svg>',
        '</button>',
      '</div>',
    ].join('');

    document.body.appendChild(btn);
    document.body.appendChild(win);
    return { btn: btn, win: win };
  }

  /* ── Message rendering ────────────────────────────────────────────── */
  function addMsg(el, role, text) {
    var row    = document.createElement('div');
    row.className = 'cb-row cb-' + role;
    if (role === 'bot') {
      var av = document.createElement('div');
      av.className = 'cb-bot-avatar';
      av.textContent = '🎓';
      row.appendChild(av);
    }
    var bubble = document.createElement('div');
    bubble.className = 'cb-bubble';
    if (role === 'bot') bubble.appendChild(renderMd(text));
    else bubble.textContent = text || '';
    row.appendChild(bubble);
    el.appendChild(row);
    el.scrollTop = el.scrollHeight;
    return row;
  }

  function addTyping(el) {
    var row = document.createElement('div');
    row.className = 'cb-row cb-bot';
    var av = document.createElement('div');
    av.className = 'cb-bot-avatar';
    av.textContent = '🎓';
    var bubble = document.createElement('div');
    bubble.className = 'cb-bubble';
    bubble.innerHTML = '<div class="cb-typing"><span></span><span></span><span></span></div>';
    row.appendChild(av);
    row.appendChild(bubble);
    el.appendChild(row);
    el.scrollTop = el.scrollHeight;
    return row;
  }

  function showChips(quickEl, onSelect) {
    quickEl.innerHTML = '';
    QUICK_QS.forEach(function (q) {
      var chip = document.createElement('button');
      chip.className = 'cb-chip';
      chip.type = 'button';
      chip.textContent = q;
      chip.addEventListener('click', function (e) {
        e.stopPropagation();
        onSelect(q);
      });
      quickEl.appendChild(chip);
    });
  }

  /* ── Main ─────────────────────────────────────────────────────────── */
  function init() {
    injectStyles();
    var els  = buildWidget();
    var btn  = els.btn;
    var win  = els.win;
    var msgEl   = document.getElementById('cb-messages');
    var quickEl = document.getElementById('cb-quick');
    var inputEl = document.getElementById('cb-input');
    var sendEl  = document.getElementById('cb-send');
    var closeEl = document.getElementById('cb-close');

    var isOpen = false;
    var busy   = false;

    function openChat() {
      isOpen = true;
      win.classList.add('cb-open');
      btn.classList.add('cb-active');
      setTimeout(function () { inputEl.focus(); }, 230);
      if (!msgEl.children.length) greet();
    }
    function closeChat() {
      isOpen = false;
      win.classList.remove('cb-open');
      btn.classList.remove('cb-active');
    }

    function greet() {
      var ctx = getContext();
      if (ctx) {
        addMsg(msgEl, 'bot',
          'Hello! Analysis data is loaded.\n\n' +
          'Ask me anything about the report — GPA, failure rates, risk courses, ' +
          'data quality, forecasts, cohort intelligence, recommendations, and more.');
        showChips(quickEl, ask);
      } else {
        addMsg(msgEl, 'bot',
          'Hello! I\'m your Academic Analytics Assistant.\n\n' +
          'Please upload your Excel file on this page first. Once the analysis runs, ' +
          'I can answer questions about:\n' +
          '• GPA and failure rates\n• High-risk courses\n• Data quality\n' +
          '• Trend forecasts\n• Cohort retention\n• Recommendations');
      }
    }

    function ask(question) {
      question = (question || '').trim();
      if (busy || !question) return;
      busy = true;
      inputEl.value = '';
      quickEl.innerHTML = '';
      sendEl.disabled = true;
      addMsg(msgEl, 'user', question);
      var typingRow = addTyping(msgEl);
      var ctx = getContext();

      fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: question, context: ctx }),
      })
      .then(function (res) {
        if (!res.ok) throw new Error('HTTP ' + res.status);
        return res.json();
      })
      .then(function (data) {
        typingRow.remove();
        addMsg(msgEl, 'bot', data.answer || 'Sorry, no answer returned.');
      })
      .catch(function (err) {
        typingRow.remove();
        addMsg(msgEl, 'bot',
          'Could not reach the server. Please make sure the backend is running.');
        console.error('[chatbot]', err);
      })
      .finally(function () {
        busy = false;
        sendEl.disabled = false;
        if (getContext()) showChips(quickEl, ask);
        inputEl.focus();
      });
    }

    /* Events */
    btn.addEventListener('click', function (e) {
      e.stopPropagation();
      isOpen ? closeChat() : openChat();
    });
    closeEl.addEventListener('click', function (e) {
      e.stopPropagation();
      closeChat();
    });
    sendEl.addEventListener('click', function (e) {
      e.stopPropagation();
      ask(inputEl.value);
    });
    inputEl.addEventListener('keydown', function (e) {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        ask(inputEl.value);
      }
    });
    document.addEventListener('click', function (e) {
      if (isOpen && !win.contains(e.target) && !btn.contains(e.target)) closeChat();
    });
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && isOpen) closeChat();
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
