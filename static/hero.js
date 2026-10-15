/* Overview hero: a replay of one stored read. Fields fill in as the scan box moves over the masked page,
   the paper's identities turn green one by one, and the field the paper cannot settle turns red. It ends on a red
   card: a field the model read right and the first capture mis-keyed, with the certified count. Loops. */
(function () {
  var el = document.getElementById('loopData'); if (!el) return;
  var D = JSON.parse(el.textContent);
  var frame = document.getElementById('rFrame'), scan = document.getElementById('rScan'),
      tiles = document.getElementById('rTiles'), ids = document.getElementById('rIds'),
      verdict = document.getElementById('rVerdict'), stage = document.getElementById('rStage'),
      receipt = document.getElementById('rReceipt');
  function showReceipt(on) { if (!receipt) return; receipt.classList.toggle('on', on); receipt.setAttribute('aria-hidden', on ? 'false' : 'true'); }
  var SHORT = {SOBRANTES: 'Unused', VOTARON: 'Voters', REPRESENTANTES: 'Reps', PERSONAS_Y_REP: 'Sec 5',
               SACADOS: 'Sec 7', NO_REGISTRADAS: 'Unreg.', NULOS: 'Null', TOTAL: 'TOTAL'};
  function short(c) { return SHORT[c] || ('Opt ' + c.slice(3)); }
  function esc(s) { return String(s == null ? '–' : s).replace(/[&<>"]/g, function (c) { return {'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;'}[c]; }); }

  var reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var run = 0;

  function build() {
    tiles.innerHTML = ''; ids.innerHTML = '';
    frame.querySelectorAll('.bx').forEach(function (b) { b.remove(); });
    D.fields.forEach(function (f) {
      var t = document.createElement('div'); t.className = 'ft'; t.id = 'ft-' + f.code; t.title = f.name;
      t.innerHTML = '<span class="k">' + esc(short(f.code)) + '</span><span class="v"><span class="sk"></span></span>';
      tiles.appendChild(t);
    });
    D.identities.forEach(function (i, k) {
      var d = document.createElement('div'); d.id = 'id-' + k;
      d.innerHTML = '<i>·</i><span>' + esc(i.name) + '</span><b></b>'; ids.appendChild(d);
    });
    verdict.className = 'vbar'; verdict.textContent = 'Waiting for the read';
    scan.style.opacity = 0; showReceipt(false);
  }
  function place(node, box) { node.style.left = box[0] + '%'; node.style.top = box[1] + '%'; node.style.width = box[2] + '%'; node.style.height = box[3] + '%'; }
  function showField(f) {
    var t = document.getElementById('ft-' + f.code);
    var prev = tiles.querySelector('.cur'); if (prev) prev.classList.remove('cur');
    t.className = 'ft cur ' + (f.ok ? 'ok' : 'bad');
    t.querySelector('.v').innerHTML = f.ok ? esc(f.n) : esc(f.n) + '<span style="font-weight:500">≠' + esc(f.w) + '</span>';
    if (!f.ok) t.title = f.name + ': ' + f.msg;
    var b = document.createElement('div'); b.className = 'bx ' + (f.ok ? 'ok' : 'bad'); place(b, f.box); frame.insertBefore(b, scan);
    place(scan, f.box); scan.style.opacity = 1;
  }
  function showIdent(i, k) {
    var d = document.getElementById('id-' + k);
    d.className = i.ok ? 'ok' : (i.ok === false ? 'bad' : '');
    d.querySelector('i').textContent = i.ok ? '✓' : (i.ok === false ? '✕' : '–');
    d.querySelector('b').textContent = i.count ? (i.lhs + ' of ' + i.rhs) : (i.lhs + (i.ok ? ' = ' : ' ≠ ') + i.rhs);
  }
  function finish() {
    var prev = tiles.querySelector('.cur'); if (prev) prev.classList.remove('cur');
    scan.style.opacity = 0;
    verdict.className = 'vbar ' + (D.accepted ? 'ok' : 'bad');
    verdict.textContent = D.accepted ? D.line : D.line.replace(/^Routed: /, 'Routed to a person: ');
    stage.textContent = D.accepted ? 'Accepted: nobody keys it' : 'Routed: 1 field to a person';
  }
  function wait(ms, my) { return new Promise(function (res, rej) { setTimeout(function () { my === run ? res() : rej(); }, ms); }); }

  function play() {
    var my = ++run; build(); stage.textContent = 'Reading on AMD';
    var p = wait(700, my);
    D.fields.forEach(function (f) { p = p.then(function () { showField(f); return wait(f.ok ? 230 : 900, my); }); });
    p = p.then(function () { stage.textContent = "Checking the paper's arithmetic"; return wait(350, my); });
    D.identities.forEach(function (i, k) { p = p.then(function () { showIdent(i, k); return wait(420, my); }); });
    // end on the receipt: a field the model read right and the first capture mis-keyed, certified by comparison
    p.then(function () { finish(); return wait(2600, my); })
     .then(function () { stage.textContent = 'A keying error the model found'; showReceipt(true); return wait(9000, my); })
     .then(play).catch(function () {});
  }
  function still() { build(); D.fields.forEach(showField); D.identities.forEach(showIdent); finish(); if (receipt) stage.textContent = 'A keying error the model found'; showReceipt(true); }

  if (reduce) { still(); return; }
  // play only while visible; restart from the top when it scrolls back into view
  if ('IntersectionObserver' in window) {
    var on = false;
    new IntersectionObserver(function (es) {
      es.forEach(function (e) { if (e.isIntersecting && !on) { on = true; play(); } else if (!e.isIntersecting && on) { on = false; run++; still(); } });
    }, {threshold: 0.2}).observe(document.getElementById('reader'));
  } else play();
})();
