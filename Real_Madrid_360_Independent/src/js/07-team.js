/* Team view: season record, form and absences. */
(function (R) {
  'use strict';
  var el = R.el, add = R.add, clear = R.clear, $ = R.$, D = R.D;
  var RES = { w: 'ف', d: 'ت', l: 'خ' }, RES_FULL = { w: 'فوز', d: 'تعادل', l: 'خسارة' };

  function recCard(title, stats) {
    var c = el('div', 'rec'), line = el('div', 'line');
    add(c, el('h3', null, title));
    stats.forEach(function (s) { var st = el('div', 'stat'); add(st, el('span', 'v', s[0]), el('span', 'l', s[1])); add(line, st); });
    add(c, line);
    return c;
  }
  function absenceList(ul, compact) {
    (D.absences || []).forEach(function (a) {
      var status = a.status;
      if (a.kind === 'suspended') {
        var bp = R.banProgress(a);
        if (!bp.left.length) return;
        var served = bp.total - bp.left.length, comps = {};
        R.banList(a).forEach(function (id) { var m = R.findMatch(id); if (m) comps[m.c] = true; });
        var ligaOnly = comps.liga && !comps.ucl, uclOnly = comps.ucl && !comps.liga;
        status = 'موقوف' + (ligaOnly ? ' في الدوري' : uclOnly ? ' في دوري الأبطال' : '') + '، ' +
          (served > 0 ? 'قضى ' + served + ' من ' + bp.total + ' مباريات' : 'يغيب عن ' + bp.total + ' مباريات');
        if (!compact) {
          var names = bp.left.map(function (id) { var m = R.findMatch(id); return m ? R.teamName(m.opp) : ''; }).filter(Boolean);
          status += '. المتبقي: ' + names.join('، ') + '.' + (ligaOnly ? ' متاح في دوري الأبطال.' : '');
        }
      } else if (!compact && a.detail) {
        status = a.status + '. ' + a.detail;
      }
      var li = el('li');
      add(li, el('span', 'who', a.name), el('span', 'kind ' + a.kind, a.kind === 'suspended' ? 'موقوف' : 'مصاب'), el('span', 'st', status));
      if (!compact && a.source) { var sl = R.sourceLine(a.source); sl.className = 'source-line st-src'; add(li, sl); }
      add(ul, li);
    });
  }

  R.renderHomeAbsences = function () { absenceList(clear($('home-absences')), true); };
  R.renderTeam = function () {
    $('coach-line').textContent = 'المدرب: ' + (D.coach || '');
    var grid = el('div', 'records');
    var lr = (D.liga || []).filter(function (r) { return r.t === R.RM; })[0];
    if (lr) add(grid, recCard('الدوري الإسباني، المركز ' + lr.r, [[lr.p, 'مباريات'], [lr.w, 'فوز'], [lr.d, 'تعادل'], [lr.l, 'خسارة'], [lr.gf, 'له'], [lr.ga, 'عليه'], [lr.pts, 'نقطة']]));
    var ur = (D.ucl || []).filter(function (r) { return r.t === R.RM; })[0];
    if (ur) {
      var gf = 0, ga = 0;
      R.MATCHES.forEach(function (m) { if (m.c === 'ucl' && m.played) { gf += m.rmG; ga += m.opG; } });
      add(grid, recCard('دوري أبطال أوروبا، المركز ' + ur.r + ' من 36', [[ur.p, 'مباريات'], [ur.w, 'فوز'], [ur.d, 'تعادل'], [ur.l, 'خسارة'], [gf, 'له'], [ga, 'عليه'], [ur.pts, 'نقاط']]));
    }
    add(clear($('record')), grid);

    var fs = clear($('form-strip'));
    R.MATCHES.filter(function (m) { return m.c === 'liga' && m.played; }).slice(-6).forEach(function (m) {
      var li = el('li');
      li.setAttribute('aria-label', RES_FULL[m.r] + ' ' + m.rmG + '–' + m.opG + ' أمام ' + R.teamName(m.opp) + '، ' + R.fmtDate(m.t, { noDay: true }));
      li.title = li.getAttribute('aria-label');
      add(li, el('span', 'res ' + m.r, RES[m.r]), el('span', 'opp', m.opp));
      add(fs, li);
    });

    absenceList(clear($('team-absences')), false);
    var src = clear($('abs-source'));
    if (D.absencesSource) { var sl = R.sourceLine(D.absencesSource); while (sl.firstChild) src.appendChild(sl.firstChild); }
  };
})(window.RM360);
