/* miluk.org /dictionary/ — search + story modes. Generated site; fold() mirrors the build. */
(function () {
  'use strict';
  var ROOT = document.body.getAttribute('data-root') || './';

  /* ---- fold: identical to the generator's ---- */
  var SUP = { 'ⁱ':'i','ᵘ':'u','ʷ':'w','ᵃ':'a','ᵉ':'e','ⁿ':'n','ʸ':'y','ʰ':'','ʻ':'' };
  var FOLD = { 'ɛ':'e','ə':'e','ɢ':'g','ƚ':'l','ł':'l','ɣ':'g','ʒ':'z','ʃ':'s','š':'s','ǯ':'j',
               'ŋ':'n','ɪ':'i','ʊ':'u','ð':'d','ɴ':'n','ʟ':'l','ᴍ':'m','ƛ':'tl' };
  function fold(s) {
    s = s.normalize('NFC').replace(/č/g, 'tc').replace(/ǯ/g, 'dj').replace(/ʒ/g, 'j');
    s = s.replace(/[ⁱᵘʷᵃᵉⁿʸʰʻ]/g, function (c) { return SUP[c] !== undefined ? SUP[c] : c; });
    s = s.normalize('NFD').replace(/[̀-ͯ]/g, '');
    s = s.toLowerCase().replace(/./g, function (c) { return FOLD[c] || c; });
    return s.replace(/[^a-z0-9]/g, '');
  }

  /* ---- search ---- */
  var q = document.getElementById('q');
  if (q) {
    var box = document.getElementById('results');
    var IDX = null, loading = false, waiting = [];
    function load(cb) {
      if (IDX) return cb();
      waiting.push(cb);
      if (loading) return;
      loading = true;
      fetch(ROOT + 'search-index.json').then(function (r) { return r.json(); })
        .then(function (j) {
          IDX = j;
          var w = waiting; waiting = [];
          w.forEach(function (f) { f(); });
        });
    }
    function esc(s) { return s.replace(/[&<>"]/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }
    function render(rows) {
      if (!rows.length) { box.innerHTML = '<div class="none">Nothing found.</div>'; }
      else {
        var h = '', grp = '';
        rows.slice(0, 40).forEach(function (r) {
          if (r.grp !== grp) { grp = r.grp; h += '<div class="rgroup">' + grp + '</div>'; }
          h += '<a href="' + r.href + '"><span class="mk">' + esc(r.hw) + '</span>' +
               (r.g ? '<span class="g">' + esc(r.g) + '</span>' : '') + '</a>';
        });
        box.innerHTML = h;
      }
      box.classList.add('open');
    }
    function search() {
      var raw = q.value.trim();
      if (!raw) { box.classList.remove('open'); return; }
      load(function () {
        var qf = fold(raw), ql = raw.toLowerCase(), rows = [];
        if (qf) {
          IDX.entries.forEach(function (e) {
            var hit = e.k.indexOf(qf) === 0 ? 0 :
                      e.k.indexOf(qf) > 0 ? 1 :
                      e.kk.some(function (k) { return k.indexOf(qf) >= 0; }) ? 2 : -1;
            if (hit >= 0) rows.push({ grp: 'Miluk', rank: hit, hw: e.h, g: e.g,
                                      href: ROOT + 'words/' + e.i + '.html' });
          });
        }
        IDX.entries.forEach(function (e) {
          if (e.g && e.g.toLowerCase().indexOf(ql) >= 0)
            rows.push({ grp: 'English', rank: e.g.toLowerCase().indexOf(ql) === 0 ? 0 : 1,
                        hw: e.h, g: e.g, href: ROOT + 'words/' + e.i + '.html' });
        });
        IDX.stories.forEach(function (s) {
          if (s.t.toLowerCase().indexOf(ql) >= 0)
            rows.push({ grp: 'Texts', rank: 1, hw: s.t, g: '',
                        href: ROOT + 'stories/' + s.i + '.html' });
        });
        var seen = {};
        rows = rows.filter(function (r) {
          var k = r.grp + r.href;
          if (seen[k]) return false; seen[k] = 1; return true;
        }).sort(function (a, b) {
          var g = { 'Miluk': 0, 'English': 1, 'Texts': 2 };
          return (g[a.grp] - g[b.grp]) || (a.rank - b.rank) || (a.hw > b.hw ? 1 : -1);
        });
        render(rows);
      });
    }
    q.addEventListener('input', search);
    q.addEventListener('focus', function () { load(function () {}); if (q.value.trim()) search(); });
    document.addEventListener('click', function (e) {
      if (!e.target.closest('.search-box')) box.classList.remove('open');
    });
  }

  /* ---- story reading modes ---- */
  var story = document.getElementById('story');
  if (story) {
    document.querySelectorAll('.modes button').forEach(function (b) {
      b.addEventListener('click', function () {
        document.querySelectorAll('.modes button').forEach(function (x) { x.classList.remove('on'); });
        b.classList.add('on');
        story.className = 'story mode-' + b.getAttribute('data-mode');
      });
    });
  }

  /* ---- story list filter ---- */
  var sf = document.getElementById('storyfilter');
  if (sf) {
    sf.addEventListener('input', function () {
      var v = sf.value.toLowerCase();
      document.querySelectorAll('.storylist li').forEach(function (li) {
        li.style.display = li.textContent.toLowerCase().indexOf(v) >= 0 ? '' : 'none';
      });
    });
  }
})();
