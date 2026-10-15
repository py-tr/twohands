(function () {
  var clave = document.getElementById('live') && document.getElementById('live').dataset.clave;

  // crops: click "crop" to open the field's crop from the masked page under its row
  var table = document.getElementById('ftable');
  if (table) table.addEventListener('click', function (e) {
    var b = e.target.closest('[data-crop]'); if (!b) return;
    var tr = b.closest('tr'), next = tr.nextElementSibling;
    if (next && next.classList.contains('croprow')) { next.remove(); b.textContent = 'crop'; return; }
    var row = document.createElement('tr'); row.className = 'croprow';
    var td = document.createElement('td'); td.colSpan = tr.children.length;
    var img = new Image(); img.alt = 'crop'; img.src = '/crop/' + clave + '/' + b.dataset.crop + '.jpg';
    td.appendChild(img); row.appendChild(td); tr.after(row); b.textContent = 'hide';
  });

  // live read over server-sent events
  var btn = document.getElementById('liveBtn'); if (!btn) return;
  var timer = document.getElementById('timer'), stages = document.getElementById('stages'),
      tiles = document.getElementById('tiles'), idents = document.getElementById('liveIdents'), msg = document.getElementById('liveMsg');
  var t0 = 0, tick = null;

  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"]/g, function (c) { return {'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;'}[c]; }); }
  function stage(t, text) { var li = document.createElement('li'); li.innerHTML = '<span class="t">' + (t != null ? Number(t).toFixed(1) + 's' : '') + '</span><span>' + esc(text) + '</span>'; stages.appendChild(li); }
  function say(kind, text) { msg.innerHTML = '<div class="msg ' + kind + '">' + text + '</div>'; }
  function setTimer(s) { timer.textContent = s.toFixed(1) + ' s'; }

  function buildTiles() {
    tiles.innerHTML = ''; tiles.hidden = false;
    document.querySelectorAll('#ftable tbody tr[data-key]').forEach(function (tr) {
      var k = tr.dataset.key, d = document.createElement('div');
      d.className = 'tile'; d.id = 'tile-' + k; d.innerHTML = '<div class="k">' + esc(tr.dataset.name) + '</div><div class="v">·</div>';
      tiles.appendChild(d);
    });
  }

  btn.addEventListener('click', function () {
    btn.disabled = true; stages.innerHTML = ''; idents.innerHTML = ''; msg.innerHTML = '';
    buildTiles(); t0 = performance.now(); timer.hidden = false;
    tick = setInterval(function () { setTimer((performance.now() - t0) / 1000); }, 100);
    stage(0, 'Checking the shared budget and the endpoint');
    fetch('/api/live/' + encodeURIComponent(clave), {method: 'POST'}).then(function (r) {
      return r.json().then(function (j) { return {ok: r.ok, j: j}; });
    }).then(function (res) {
      if (!res.ok) { stop(); tiles.hidden = true; say('warn', esc(res.j.message || 'The live read is not available right now.') + ' The measured result above stays valid.'); return; }
      var es = new EventSource('/api/live/events/' + res.j.job);
      es.onmessage = function (m) {
        var ev = JSON.parse(m.data);
        if (ev.type === 'stage') stage(ev.t, ev.msg);
        else if (ev.type === 'field') {
          var d = document.getElementById('tile-' + ev.code); if (!d) return;
          var bad = ev.status !== 'ok';
          d.className = 'tile in ' + (bad ? 'bad' : 'ok');
          d.innerHTML = '<div class="k">' + esc(ev.name) + '</div><div class="v">' + (ev.n == null ? '—' : esc(ev.n)) +
            ' <span>' + (ev.w == null ? '' : 'words ' + esc(ev.w)) + '</span></div>' + (bad ? '<div class="tiny" style="color:var(--bad)">' + esc(ev.msg) + '</div>' : '');
        } else if (ev.type === 'identity') {
          var ok = ev.ok, cls = ok ? 'ok' : (ok === null ? 'na' : 'bad');
          idents.insertAdjacentHTML('beforeend', '<div class="ident ' + cls + '"><span class="st ' + cls + '">' + (ok ? '✓' : (ok === null ? '–' : '✕')) +
            '</span><span class="nm">' + esc(ev.name) + '</span><span class="eq">' + (ok === null ? 'not checkable' : esc(ev.lhs) + (ok ? ' = ' : ' ≠ ') + esc(ev.rhs)) + '</span></div>');
        } else if (ev.type === 'verdict') {
          say(ev.accepted ? 'ok' : 'warn', '<b>' + esc(ev.line) + '</b><br><span class="small">Live read by ' + esc(ev.model) + ' in ' + esc(ev.secs) + ' s, cost $' + Number(ev.cost || 0).toFixed(6) + '. Saved as this form\'s latest live read.</span>');
        } else if (ev.type === 'error') {
          say('warn', esc(ev.msg));
        } else if (ev.type === 'done') { es.close(); stop(); }
      };
      es.onerror = function () { es.close(); stop(); };
    }).catch(function () { stop(); say('warn', 'Could not reach the server.'); });
  });

  function stop() { if (tick) clearInterval(tick); tick = null; setTimer((performance.now() - t0) / 1000); btn.disabled = false; }
})();
