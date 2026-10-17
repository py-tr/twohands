// Home: forward the anchors of the sections that moved to /results, rotate the receipt card every ~8 s (paused on hover/focus), refresh the live strip every minute.
(function () {
  var moved = ['measured', 'conf52', 'c100chip', 'cost-of-problem', 'who-pays', 'reg', 'ine-buyer', 'offer-2027',
               'ine-metric', 'market-lines', 'buyer-benchmark', 'price-lines', 'market-size', 'next-markets', 'amd',
               'amd-models', 'modelline', 'readernow', 'any-form'];
  var h = (location.hash || '').slice(1);
  if (h && !document.getElementById(h) && moved.indexOf(h) >= 0) {
    var base = window.TH_BASE;   // the static mirror sets it; the live site serves /results
    location.replace((base ? base + 'results/' : '/results') + '#' + (h === 'amd' ? 'amd-models' : h));
    return;
  }
  var card = document.getElementById('rcard');
  if (card) {
    var slides = card.querySelectorAll('.rslide'), i = 0, hold = false;
    var show = function (k) {
      slides[i].hidden = true; slides[i].classList.remove('on');
      i = k % slides.length;
      var img = slides[i].querySelector('img');
      if (img && img.loading === 'lazy') img.loading = 'eager';
      slides[i].hidden = false; slides[i].classList.add('on');
    };
    card.addEventListener('mouseenter', function () { hold = true; });
    card.addEventListener('mouseleave', function () { hold = false; });
    card.addEventListener('focusin', function () { hold = true; });
    card.addEventListener('focusout', function () { hold = false; });
    if (slides.length > 1) setInterval(function () { if (!hold && !document.hidden) show(i + 1); }, 8000);
  }
  var strip = document.getElementById('strip');
  if (strip && strip.dataset.kind === 'live') {
    var fmt = function (x) { return (x || 0).toLocaleString('en-US'); };
    setInterval(function () {
      if (document.hidden) return;
      fetch('/api/live-strip').then(function (r) { return r.json(); }).then(function (j) {
        if (j.kind !== 'live') return;
        strip.querySelectorAll('[data-k]').forEach(function (el) { el.textContent = fmt(j[el.dataset.k]); });
        var m = document.getElementById('stripMeta');
        if (m && j.updated_min_ago !== null) {
          var t = m.innerHTML.replace(/updated (just now|\d+ min ago)/, 'updated ' + (j.updated_min_ago === 0 ? 'just now' : j.updated_min_ago + ' min ago'));
          m.innerHTML = t;
        }
      }).catch(function () {});
    }, 60000);
  }
})();
