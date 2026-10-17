/* Fixtures and results list. */
(function (R) {
  'use strict';
  var el = R.el, add = R.add, clear = R.clear, $ = R.$, state = R.state;
  var RES = { w: 'ف', d: 'ت', l: 'خ' }, RES_FULL = { w: 'فوز', d: 'تعادل', l: 'خسارة' };

  function matchRow(m, mode) {
    var row = el('article', 'match-row'), date = el('div', 'mdate'), k = R.ksa(m.t);
    add(date, el('span', 'd', k.getUTCDate()), el('span', 'wd', R.DAYS[k.getUTCDay()]));
    add(row, date);
    var teams = el('div', 'teams');
    [[m.h, m.hs], [m.a, m.as]].forEach(function (p) {
      var tr = el('div', 'trow' + (p[0] === R.RM ? ' rm' : ''));
      add(tr, R.badge(p[0], true), el('span', 'nm', R.teamName(p[0])));
      if (m.played) add(tr, el('span', 'sc', p[1]));
      add(teams, tr);
    });
    add(row, teams);
    var side = el('div', 'mside');
    if (m.played) {
      var res = el('span', 'res ' + m.r, RES[m.r]);
      res.setAttribute('aria-label', RES_FULL[m.r]); res.title = RES_FULL[m.r];
      add(side, res);
    } else if (mode === 'results') {
      add(side, el('span', 'res p', 'بانتظار النتيجة'));
    } else if (m.tc) {
      var tp = R.timeParts(m.t), t = el('span', 't');
      t.appendChild(document.createTextNode(tp.hm));
      add(t, el('small', null, tp.ap));
      add(side, t);
      if (R.isLive(m)) {
        add(side, el('span', 'pill live', 'جارية'));
      } else {
        var b = el('button', 'ics'); b.type = 'button';
        b.setAttribute('aria-label', 'أضف مباراة ' + R.teamName(m.h) + ' و' + R.teamName(m.a) + ' إلى التقويم');
        add(b, R.calIcon(), el('span', null, 'تقويم'));
        b.addEventListener('click', function () { R.downloadICS(m); });
        add(side, b);
      }
    } else {
      add(side, el('span', 'tbd', 'الموعد لم يُحدَّد'));
    }
    add(row, side);
    var comp = el('div', 'mcomp');
    add(comp, el('span', null, R.compLine(m)), el('span', null, m.home ? 'على أرضه' : 'خارج أرضه'));
    add(row, comp);
    return row;
  }

  R.renderMatches = function () {
    var box = clear($('match-list')), mode = state.matchMode, comp = state.matchComp;
    var list = R.MATCHES.filter(function (m) {
      if (comp !== 'all' && m.c !== comp) return false;
      return mode === 'upcoming' ? R.isUpcoming(m) : !R.isUpcoming(m);
    });
    if (mode === 'results') list = list.slice().reverse();
    if (!list.length) { add(box, el('p', 'empty', mode === 'upcoming' ? 'لا توجد مباريات قادمة في هذا التصنيف.' : 'لا توجد نتائج في هذا التصنيف.')); return; }
    var lastKey = '';
    list.forEach(function (m) {
      var k = R.ksa(m.t), key = k.getUTCFullYear() + '-' + k.getUTCMonth();
      if (key !== lastKey) { add(box, el('h2', 'month', R.MONTHS[k.getUTCMonth()] + ' ' + k.getUTCFullYear())); lastKey = key; }
      add(box, matchRow(m, mode));
    });
  };
  R.syncMatchControls = function () {
    document.querySelectorAll('#view-matches [data-mode]').forEach(function (b) { b.setAttribute('aria-selected', String(b.getAttribute('data-mode') === state.matchMode)); });
    document.querySelectorAll('#view-matches [data-comp]').forEach(function (b) { b.setAttribute('aria-pressed', String(b.getAttribute('data-comp') === state.matchComp)); });
  };
})(window.RM360);
