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

  var live = document.getElementById('live');
  if (live && window.LiveJob) window.LiveJob(live);
})();
