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
    var img = new Image(); img.alt = 'crop'; img.src = (window.TH_BASE || '/') + 'crop/' + clave + '/' + b.dataset.crop + '.jpg';
    td.appendChild(img); row.appendChild(td); tr.after(row); b.textContent = 'hide';
  });

  // receipts: "Verify this receipt" runs the same checks as python -m twohands.verify_receipt, server side
  Array.prototype.forEach.call(document.querySelectorAll('[data-receipt-box]'), function (box) {
    var b = box.querySelector('[data-verify]'), ul = box.querySelector('[data-checks]');
    if (!b) return;
    b.addEventListener('click', function () {
      b.disabled = true; ul.hidden = false; ul.innerHTML = '<li class="muted">Checking the receipt…</li>';
      fetch(box.dataset.check).then(function (r) { if (!r.ok) throw 0; return r.json(); }).then(function (j) {
        ul.innerHTML = j.checks.map(function (c) {
          return '<li><span class="' + (c.ok ? 'ok' : 'no') + '">' + (c.ok ? 'ok' : 'FAIL') + '</span><span>' + c.label + '</span><span class="h">' + c.hash + '</span></li>';
        }).join('') + '<li class="verified ' + (j.verified ? '' : 'no') + '">' + (j.verified ? 'VERIFIED' : 'NOT VERIFIED') +
          '</li><li class="tiny muted">Root ' + j.root.slice(0, 16) + '… of ' + j.n_leaves + ' receipts. It proves the record is unchanged, not that the reading is right.</li>';
        b.disabled = false;
      }).catch(function () { ul.innerHTML = '<li class="no">Could not check the receipt right now.</li>'; b.disabled = false; });
    });
  });

  var live = document.getElementById('live');
  if (live && window.LiveJob) window.LiveJob(live);
})();
