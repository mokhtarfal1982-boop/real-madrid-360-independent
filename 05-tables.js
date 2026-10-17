/* League tables. */
(function (R) {
  'use strict';
  var el = R.el, add = R.add, clear = R.clear, $ = R.$, D = R.D;
  var TITLES = { 'ف': 'فاز', 'ت': 'تعادل', 'خ': 'خسر', '±': 'فارق الأهداف', 'ن': 'النقاط', '#': 'المركز' };

  function zoneClass(kind, r) {
    if (kind === 'liga') return r <= 4 ? 'z-ucl' : r >= 18 ? 'z-rel' : '';
    return r <= 8 ? 'z-top8' : r <= 24 ? 'z-po' : 'z-out';
  }
  function standingsTable(rows, kind, mini) {
    var wrap = el('div', 'table-wrap' + (mini ? ' mini' : '')), table = el('table', 'standings');
    add(table, el('caption', 'sr-only', kind === 'liga' ? 'ترتيب الدوري الإسباني' : 'ترتيب مرحلة الدوري في دوري أبطال أوروبا'));
    var cols = mini ? [['#'], ['النادي', 'club'], ['لعب'], ['±'], ['ن']]
      : kind === 'liga' ? [['#'], ['النادي', 'club'], ['لعب'], ['ف'], ['ت'], ['خ'], ['له', 'wide-only'], ['عليه', 'wide-only'], ['±'], ['ن']]
        : [['#'], ['النادي', 'club'], ['لعب'], ['ف'], ['ت'], ['خ'], ['ن']];
    var thead = el('thead'), hr = el('tr');
    cols.forEach(function (c) {
      var th = el('th', c[1], c[0]); th.scope = 'col';
      if (TITLES[c[0]]) { th.title = TITLES[c[0]]; th.setAttribute('aria-label', TITLES[c[0]]); }
      add(hr, th);
    });
    add(thead, hr); add(table, thead);
    var tb = el('tbody');
    rows.forEach(function (r) {
      var tr = el('tr', zoneClass(kind, r.r) + (r.t === R.RM ? ' rm' : ''));
      var gd = typeof r.gf === 'number' ? r.gf - r.ga : null;
      var cells = { '#': r.r, 'لعب': r.p, 'ف': r.w, 'ت': r.d, 'خ': r.l, 'له': r.gf, 'عليه': r.ga, '±': gd === null ? '' : (gd > 0 ? '+' + gd : String(gd)), 'ن': r.pts };
      cols.forEach(function (c) {
        if (c[1] === 'club') {
          var td = el('td', 'club'), inn = el('span', 'in');
          add(inn, R.badge(r.t, true), el('span', null, R.teamName(r.t, true)));
          add(td, inn); add(tr, td);
          return;
        }
        var cls = ((c[0] === '#' ? 'pos' : c[0] === 'ن' ? 'pts' : '') + (c[1] ? ' ' + c[1] : '')).trim();
        var td2 = el('td', cls, cells[c[0]]);
        if (c[0] === '±') td2.setAttribute('dir', 'ltr');
        add(tr, td2);
      });
      add(tb, tr);
    });
    add(table, tb);
    add(wrap, table);
    return wrap;
  }

  R.renderMiniTable = function () {
    var box = clear($('mini-table')), rows = D.liga || [], idx = -1;
    rows.forEach(function (r, i) { if (r.t === R.RM) idx = i; });
    var pick = idx >= 6 ? rows.slice(0, 3).concat(rows.slice(idx - 1, idx + 2)) : rows.slice(0, 6);
    add(box, standingsTable(pick, 'liga', true));
  };
  R.renderFullTable = function () {
    var box = clear($('full-table')), kind = R.state.table;
    var rows = kind === 'liga' ? (D.liga || []) : (D.ucl || []);
    add(box, standingsTable(rows, kind, false));
    var z = el('p', 'zones');
    if (kind === 'liga') {
      add(z, el('span', 'ucl', 'المراكز 1 إلى 4: دوري أبطال أوروبا'), el('span', 'rel', 'المراكز 18 إلى 20: الهبوط'));
    } else {
      add(z, el('span', 'ucl', 'المراكز 1 إلى 8: التأهل المباشر إلى دور الـ16'), el('span', 'po', 'المراكز 9 إلى 24: الملحق'), el('span', 'rel', 'المراكز 25 إلى 36: الخروج'));
    }
    add(box, z);
    var uneven = rows.some(function (r) { return rows.length && r.p !== rows[0].p; });
    if (kind === 'liga' && uneven) add(box, el('p', 'table-note', 'يختلف عدد المباريات بين بعض الأندية بسبب مباريات مؤجلة.'));
    add(box, el('p', 'table-note', 'المصدر: SportRadar.'));
  };
})(window.RM360);
