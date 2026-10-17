/* Next match hero, countdown, calendar file and absences. */
(function (R) {
  'use strict';
  var el = R.el, add = R.add, clear = R.clear, $ = R.$, pad = R.pad, D = R.D;

  function icsEscape(s) { return String(s).replace(/\\/g, '\\\\').replace(/;/g, '\\;').replace(/,/g, '\\,').replace(/\n/g, '\\n'); }
  function icsStamp(ms) { var d = new Date(ms); return d.getUTCFullYear() + pad(d.getUTCMonth() + 1) + pad(d.getUTCDate()) + 'T' + pad(d.getUTCHours()) + pad(d.getUTCMinutes()) + '00Z'; }
  R.downloadICS = function (m) {
    var lines = [
      'BEGIN:VCALENDAR', 'VERSION:2.0', 'PRODID:-//Real Madrid 360//AR', 'CALSCALE:GREGORIAN', 'METHOD:PUBLISH',
      'BEGIN:VEVENT',
      'UID:rm360-' + m.id + '@real-madrid-360.vercel.app',
      'DTSTAMP:' + icsStamp(R.now()),
      'DTSTART:' + icsStamp(m.t),
      'DTEND:' + icsStamp(m.t + 2 * 3600 * 1000),
      'SUMMARY:' + icsEscape(R.teamName(m.h) + ' × ' + R.teamName(m.a)),
      'DESCRIPTION:' + icsEscape(R.compLine(m)),
      'LOCATION:' + icsEscape(R.venueOf(m)),
      'BEGIN:VALARM', 'TRIGGER:-PT30M', 'ACTION:DISPLAY', 'DESCRIPTION:' + icsEscape('تبدأ المباراة بعد 30 دقيقة'), 'END:VALARM',
      'END:VEVENT', 'END:VCALENDAR'
    ];
    var url = URL.createObjectURL(new Blob([lines.join('\r\n') + '\r\n'], { type: 'text/calendar;charset=utf-8' }));
    var a = document.createElement('a');
    a.href = url; a.download = 'rm360-' + m.id + '.ics';
    document.body.appendChild(a); a.click();
    setTimeout(function () { URL.revokeObjectURL(url); if (a.parentNode) a.parentNode.removeChild(a); }, 2000);
  };
  R.calIcon = function () {
    var s = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    s.setAttribute('viewBox', '0 0 24 24'); s.setAttribute('aria-hidden', 'true');
    s.innerHTML = '<rect x="3.5" y="5" width="17" height="15.5" rx="2"/><path d="M3.5 9.5h17M8 3v4M16 3v4M12 13v4M10 15h4"/>';
    return s;
  };

  R.banList = function (a) { return a.banFixtures || a.ligaBanFixtures || []; };
  R.absencesFor = function (m) {
    return (D.absences || []).filter(function (a) {
      if (a.kind === 'suspended') return m && R.banList(a).indexOf(m.id) !== -1;
      return true;
    });
  };
  R.banProgress = function (a) {
    var ids = R.banList(a);
    var left = ids.filter(function (id) { var m = R.findMatch(id); return m && R.isUpcoming(m); });
    return { total: ids.length, left: left };
  };

  var timer = null;
  function tick(m) {
    var diff = m.t - R.now();
    if (diff <= 0) return false;
    var mins = Math.floor(diff / 60000);
    var vals = { days: Math.floor(mins / 1440), hours: Math.floor((mins % 1440) / 60), mins: mins % 60 };
    Object.keys(vals).forEach(function (k) { var e = $('cd-' + k); if (e) e.textContent = pad(vals[k]); });
    return true;
  }
  function side(code) { var s = el('div', 'side'); add(s, R.badge(code), el('span', 'tname', R.teamName(code))); return s; }
  function row(k, v) { var p = el('p', 'row'); add(p, el('span', 'k', k), el('span', 'v2', v)); return p; }

  R.renderHero = function () {
    var hero = clear($('hero'));
    var m = R.nextMatch();
    if (!m) { add(hero, el('p', 'hero-status', 'لا توجد مباريات قادمة في البيانات الحالية.')); return; }
    var live = R.isLive(m);

    var top = el('div', 'hero-top'), comp = el('p');
    add(comp, el('span', 'comp', R.COMPS[m.c]));
    if (R.roundLabel(m)) comp.appendChild(document.createTextNode('، ' + R.roundLabel(m)));
    add(top, comp, el('span', 'pill' + (live ? ' live' : ''), live ? 'جارية الآن' : (m.home ? 'على أرضه' : 'خارج أرضه')));
    add(hero, top);

    var vs = el('div', 'versus'), kick = el('div', 'kick');
    if (m.tc) {
      var tp = R.timeParts(m.t), time = el('div', 'time');
      add(time, el('span', null, tp.hm), el('span', 'ampm', tp.ap));
      add(kick, time);
    } else {
      add(kick, el('div', 'time', '—'));
    }
    add(kick, el('div', 'date', R.fmtDate(m.t)));
    add(vs, side(m.h), kick, side(m.a));
    add(hero, vs);

    if (live) {
      add(hero, el('p', 'hero-status', 'المباراة جارية الآن. تُحدَّث النتيجة هنا بعد نهايتها.'));
    } else if (m.tc) {
      var cd = el('div', 'countdown');
      cd.setAttribute('role', 'timer'); cd.setAttribute('aria-label', 'الوقت المتبقي على انطلاق المباراة');
      ['days', 'hours', 'mins'].forEach(function (k, i) {
        if (i > 0) add(cd, el('span', 'cd-sep', ':'));
        var u = el('div', 'cd-unit'), v = el('span', 'v', '00');
        v.id = 'cd-' + k;
        add(u, v, el('span', 'l', ['يوم', 'ساعة', 'دقيقة'][i]));
        add(cd, u);
      });
      add(hero, cd);
      tick(m);
      if (timer) clearInterval(timer);
      timer = setInterval(function () { if (!tick(m)) { clearInterval(timer); R.renderHero(); } }, 30000);
    } else {
      add(hero, el('p', 'hero-status', 'لم يُحدَّد موعد الانطلاق بعد.'));
    }

    var info = el('div', 'hero-info');
    add(info, row('الملعب', R.venueOf(m)));
    if (m.tc) add(info, row('المنطقة الزمنية', 'توقيت السعودية'));
    var abs = R.absencesFor(m);
    if (abs.length) add(info, row('يغيب', abs.map(function (a) { return a.name + (a.kind === 'suspended' ? ' (موقوف)' : ''); }).join('، ')));
    add(hero, info);

    var notes = m.notes || {};
    if (notes.opponentAbsences && notes.opponentAbsences.length) {
      var det = el('details', 'more-info'), ul = el('ul');
      add(det, el('summary', null, 'غيابات ' + R.teamName(m.opp)));
      notes.opponentAbsences.forEach(function (x) { add(ul, el('li', null, x)); });
      add(det, ul);
      if (notes.source) add(det, R.sourceLine(notes.source));
      add(hero, det);
    }

    var actions = el('div', 'hero-actions');
    if (m.tc && !live) {
      var b = el('button', 'btn primary'); b.type = 'button';
      add(b, R.calIcon(), el('span', null, 'أضف إلى التقويم'));
      b.addEventListener('click', function () { R.downloadICS(m); });
      add(actions, b);
    }
    if (navigator.share) {
      var sh = el('button', 'btn', 'شارك الموعد'); sh.type = 'button';
      sh.addEventListener('click', function () {
        var txt = R.teamName(m.h) + ' × ' + R.teamName(m.a) + '، ' + R.fmtDate(m.t) + (m.tc ? '، ' + R.fmtTime(m.t) + ' بتوقيت السعودية' : '');
        navigator.share({ title: 'ريال مدريد 360', text: txt, url: location.origin + '/' }).catch(function () {});
      });
      add(actions, sh);
    }
    var all = el('a', 'btn', 'كل المباريات'); all.href = '#/matches';
    add(actions, all);
    add(hero, actions);
  };
})(window.RM360);
