/* Last result card with a goal timeline. */
(function (R) {
  'use strict';
  var el = R.el, add = R.add, clear = R.clear, $ = R.$;

  function timeline(m) {
    var wrap = el('div'), tl = el('div', 'timeline');
    tl.setAttribute('role', 'img');
    tl.setAttribute('aria-label', 'تسلسل الأهداف بالدقيقة. أهداف ' + R.teamName(m.h) + ': ' + (m.goals.home.join('، ') || 'لا يوجد') +
      '. أهداف ' + R.teamName(m.a) + ': ' + (m.goals.away.join('، ') || 'لا يوجد') + '.');
    add(tl, el('span', 'axis'));
    var half = el('span', 'half'); half.style.right = (45 / 95 * 100) + '%'; add(tl, half);
    function place(list, pos, isRm) {
      var prev = -99, prevAlt = false;
      list.slice().sort(function (a, b) { return a - b; }).forEach(function (min) {
        var alt = (min - prev) < 8 && !prevAlt;
        var g = el('span', 'goal ' + pos + (isRm ? ' rm' : ' opp') + (alt ? ' alt' : ''));
        g.style.right = (Math.min(min, 95) / 95 * 100) + '%';
        var lbl = el('b', null, min + "'"); lbl.setAttribute('dir', 'ltr');
        add(g, el('i'), lbl);
        add(tl, g);
        prevAlt = alt; prev = min;
      });
    }
    place(m.goals.home, 'top', m.h === R.RM);
    place(m.goals.away, 'bottom', m.a === R.RM);
    add(wrap, tl);
    var lg = el('p', 'tl-legend');
    add(lg, el('span', 'rm', 'ريال مدريد'), el('span', 'opp', R.teamName(m.opp)));
    add(wrap, lg);
    return wrap;
  }

  function comebackStory(m) {
    var ev = [];
    m.goals.home.forEach(function (x) { ev.push({ t: x, side: m.h }); });
    m.goals.away.forEach(function (x) { ev.push({ t: x, side: m.a }); });
    ev.sort(function (a, b) { return a.t - b.t; });
    var rm = 0, op = 0, worst = 0, worstAt = -1, worstScore = null;
    ev.forEach(function (e, i) {
      if (e.side === R.RM) rm++; else op++;
      if (op - rm > worst) { worst = op - rm; worstAt = i; worstScore = [rm, op]; }
    });
    if (m.r !== 'w' || worst < 2) return '';
    var after = ev.slice(worstAt + 1).filter(function (e) { return e.side === R.RM; });
    if (!after.length) return '';
    var first = after[0].t, last = after[after.length - 1].t;
    var span = first === last ? 'في الدقيقة ' + first : 'بين الدقيقتين ' + first + ' و' + last;
    return 'قلب ريال مدريد تأخره ' + worstScore[0] + '–' + worstScore[1] + ' إلى فوز ' + m.rmG + '–' + m.opG + ' ' + R.goalsWord(after.length) + ' ' + span + '.';
  }

  R.renderLastResult = function () {
    var box = clear($('last-result')), m = R.lastResult();
    if (!m) { box.hidden = true; return; }
    box.hidden = false;
    var head = el('div', 'block-head'), h2 = el('h2', null, 'آخر نتيجة'), more = el('a', 'more', 'كل النتائج');
    h2.id = 'h-last';
    more.href = '#/matches?results';
    add(head, h2, more);
    add(box, head);

    var card = el('article', 'result-card'), meta = el('p', 'result-meta');
    add(meta, el('span', null, R.compLine(m)), el('span', null, R.fmtDate(m.t)));
    add(card, meta);

    var row = el('div', 'score-row');
    var hs = el('div', 'side'); add(hs, R.badge(m.h, true), el('span', 'tname', R.teamName(m.h)));
    var as = el('div', 'side away'); add(as, R.badge(m.a, true), el('span', 'tname', R.teamName(m.a)));
    var sc = el('div', 'bigscore');
    sc.setAttribute('aria-label', 'النتيجة ' + R.teamName(m.h) + ' ' + m.hs + '، ' + R.teamName(m.a) + ' ' + m.as);
    add(sc, el('span', m.hs >= m.as ? 'win' : 'lose', m.hs), el('span', 'dash', '–'), el('span', m.as >= m.hs ? 'win' : 'lose', m.as));
    add(row, hs, sc, as);
    add(card, row);

    if (m.goals && (m.goals.home.length || m.goals.away.length)) {
      add(card, timeline(m));
      var story = comebackStory(m);
      if (story) add(card, el('p', 'story', story));
    }
    add(box, card);
  };
})(window.RM360);
