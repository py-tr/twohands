/* A live read on AMD as a visible queued job: place in the queue, stages, elapsed timer, then the fields as the
   gate checks them. If the AMD endpoint is busy (503 / timeout) or the allowance is used up, an honest banner says
   so and the last measured read of the same form is shown instead, with a retry button.
   Markup: <div data-live data-start="/api/live/X" data-fallback="X" data-fields='[{"code","name"}]'> ... */
window.LiveJob = function (root) {
  var $ = function (s) { return root.querySelector(s); };
  var btn = $('[data-live-btn]'), timer = $('[data-live-timer]'), steps = $('[data-live-steps]'),
      tiles = $('[data-live-tiles]'), ids = $('[data-live-ids]'), msg = $('[data-live-msg]');
  var fields = JSON.parse(root.dataset.fields || '[]');
  var t0 = 0, tick = null, es = null, current = null;
  var STEPS = [['queued', 'In the queue for the shared AMD endpoint'], ['prepare', 'Masked page and zoomed tiles prepared'],
               ['send', 'Reading on AMD (one request)'], ['answer', 'Gate checks every field'], ['verdict', 'Verdict']];

  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"]/g, function (c) { return {'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;'}[c]; }); }
  function fmt(s) { return s < 60 ? s.toFixed(1) + ' s' : Math.floor(s / 60) + ' min ' + Math.floor(s % 60) + ' s'; }
  function setTimer() { if (timer) timer.textContent = fmt((performance.now() - t0) / 1000); }

  function buildSteps() {
    steps.innerHTML = STEPS.map(function (s) { return '<li data-s="' + s[0] + '"><span class="ic"></span><span class="lb">' + s[1] + '</span><span class="tt"></span></li>'; }).join('');
    steps.hidden = false;
  }
  function step(name, state, note) {  // every step before `name` is done; `name` gets `state`
    var idx = STEPS.map(function (s) { return s[0]; }).indexOf(name);
    STEPS.forEach(function (s, i) {
      var li = steps.querySelector('[data-s="' + s[0] + '"]'); if (!li) return;
      if (i < idx) li.className = 'did';
      else if (i === idx) { li.className = state; if (note != null) li.querySelector('.tt').innerHTML = note; }
    });
    if (state === 'now') current = name;
  }
  function buildTiles(measured) {
    tiles.innerHTML = ''; tiles.hidden = false;
    fields.forEach(function (f) {
      var d = document.createElement('div');
      d.className = 'tile wait' + (measured ? ' measured' : ''); d.id = 'tile-' + f.code;
      d.innerHTML = '<div class="k">' + esc(f.name) + '</div><div class="v skel"></div>';
      tiles.appendChild(d);
    });
  }
  function field(ev, measured) {
    var d = root.querySelector('#tile-' + ev.code); if (!d) return;
    var bad = ev.status !== 'ok';
    d.className = 'tile in ' + (bad ? 'bad' : 'ok') + (measured ? ' measured' : '');
    d.innerHTML = '<div class="k">' + esc(ev.name) + '</div><div class="v">' + (ev.n == null ? '–' : esc(ev.n)) +
      ' <span>' + (ev.w == null ? '' : 'words ' + esc(ev.w)) + '</span></div>' + (bad ? '<div class="tiny" style="color:var(--bad)">' + esc(ev.msg) + '</div>' : '');
  }
  function ident(ev) {
    var ok = ev.ok, cls = ok ? 'ok' : (ok === null || ok === undefined ? 'na' : 'bad');
    ids.insertAdjacentHTML('beforeend', '<div class="ident ' + cls + '"><span class="st ' + cls + '">' + (ok ? '✓' : (cls === 'na' ? '–' : '✕')) +
      '</span><span class="nm">' + esc(ev.name) + '</span><span class="eq">' + (cls === 'na' ? 'not checkable' : esc(ev.lhs) + (ok ? ' = ' : ' ≠ ') + esc(ev.rhs)) + '</span></div>');
  }
  var ICON_ALERT = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M12 3l10 18H2z"/><path d="M12 10v5M12 18v.5"/></svg>';
  var ICON_OK = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round"><path d="M5 12l5 5 9-10"/></svg>';
  function banner(kind, html, retry) {
    msg.innerHTML = '<div class="banner ' + (kind === 'ok' ? 'ok' : '') + '" role="status">' + (kind === 'ok' ? ICON_OK : ICON_ALERT) +
      '<div class="grow">' + html + '</div>' + (retry ? '<button class="btn sm" data-retry>Retry</button>' : '') + '</div>';
    var r = msg.querySelector('[data-retry]'); if (r) r.addEventListener('click', start);
  }
  function fallback(clave, why) {
    if (!clave) return;
    fetch('/api/form/' + encodeURIComponent(clave)).then(function (r) { return r.ok ? r.json() : null; }).then(function (j) {
      if (!j) return;
      buildTiles(true); ids.innerHTML = '';
      j.verdict.fields.forEach(function (f) { field(f, true); });
      j.verdict.identities.forEach(ident);
      var cap = document.createElement('p'); cap.className = 'tiny'; cap.style.margin = '8px 0 0';
      cap.textContent = 'Showing the last measured read of this form (' + j.verdict.line + '). Dashed tiles = measured earlier, not live.';
      ids.appendChild(cap);
    });
  }
  function stop() { if (tick) clearInterval(tick); tick = null; if (t0) setTimer(); if (btn) btn.disabled = false; if (es) { es.close(); es = null; } }

  function attach(job, position) {
    if (btn) btn.disabled = true;
    buildSteps(); buildTiles(false); ids.innerHTML = ''; msg.innerHTML = '';
    t0 = performance.now(); if (timer) timer.hidden = false;
    if (tick) clearInterval(tick); tick = setInterval(setTimer, 100);
    step('queued', 'now', position ? '<span class="qpos">' + position + ' ahead</span>' : '<span class="qpos">next</span>');
    es = new EventSource('/api/live/events/' + job);
    es.onmessage = function (m) {
      var ev = JSON.parse(m.data);
      if (ev.type === 'queued' || (ev.type === 'tick' && ev.state === 'queued')) {
        step('queued', 'now', ev.position ? '<span class="qpos">' + ev.position + ' ahead</span>' : '<span class="qpos">next</span>');
      } else if (ev.type === 'stage') {
        if (ev.stage === 'prepare') { step('queued', 'did', ''); step('prepare', 'did', ''); }
        if (ev.stage === 'send') step('send', 'now', '');
        if (ev.stage === 'answer') { step('send', 'did', ev.secs != null ? esc(ev.secs) + ' s' : ''); step('answer', 'now', ''); }
      } else if (ev.type === 'field') field(ev, false);
      else if (ev.type === 'identity') ident(ev);
      else if (ev.type === 'verdict') {
        step('answer', 'did', ''); step('verdict', 'did', '');
        banner(ev.accepted ? 'ok' : 'warn', '<b>' + esc(ev.line) + '</b><br><span class="small">Read live by ' + esc(ev.model) + ' on AMD in ' + esc(ev.secs) +
          ' s, cost $' + Number(ev.cost || 0).toFixed(6) + '.</span>');
      } else if (ev.type === 'error') {
        step(current || 'send', 'fail', '');
        var busy = ev.code === 'endpoint_busy';
        banner('warn', busy ? esc(ev.msg).replace(/^(AMD endpoint busy)/, '<b>$1</b>') : '<b>Live read did not finish.</b> ' + esc(ev.msg), true);
        tiles.hidden = true;
        fallback(ev.fallback);
      } else if (ev.type === 'done') stop();
    };
    es.onerror = function () { stop(); };
  }

  function start() {
    if (btn) btn.disabled = true;
    msg.innerHTML = '';
    fetch(root.dataset.start, {method: 'POST'}).then(function (r) {
      return r.json().then(function (j) { return {ok: r.ok, j: j}; });
    }).then(function (res) {
      if (res.ok) { attach(res.j.job, res.j.position); return; }
      stop(); tiles.hidden = true; if (steps) steps.hidden = true;
      var code = res.j.refused, retry = code === 'endpoint' || code === 'busy';
      banner('warn', code === 'endpoint' ? esc(res.j.message).replace(/^(AMD endpoint busy)/, '<b>$1</b>') :
        '<b>' + (code === 'busy' ? 'Queue full.' : 'Live read not available.') + '</b> ' + esc(res.j.message), retry);
      if (code === 'endpoint' || code === 'budget') fallback(root.dataset.fallback);
    }).catch(function () { stop(); banner('warn', 'Could not reach the server.', true); });
  }

  if (btn) btn.addEventListener('click', start);
  return {start: start, attach: attach};
};
