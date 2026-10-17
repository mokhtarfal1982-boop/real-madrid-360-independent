/* Real Madrid 360 core: constants, helpers and the match model. Maintained by Claude. */
(function () {
  'use strict';
  var R = window.RM360 = {};
  var D = R.D = window.RM360_DATA;
  R.TEAMS = window.RM360_TEAMS || {};
  R.NEWS_URLS = ['/feed/news.json'];
  var KSA_OFFSET = 3 * 3600 * 1000;
  R.LIVE_WINDOW = 135 * 60 * 1000;
  R.RM = 'RMA';

  R.COMPS = { liga: 'الدوري الإسباني', ucl: 'دوري أبطال أوروبا' };
  R.DAYS = ['الأحد', 'الإثنين', 'الثلاثاء', 'الأربعاء', 'الخميس', 'الجمعة', 'السبت'];
  R.MONTHS = ['يناير', 'فبراير', 'مارس', 'أبريل', 'مايو', 'يونيو', 'يوليو', 'أغسطس', 'سبتمبر', 'أكتوبر', 'نوفمبر', 'ديسمبر'];
  R.CATS = { official: 'رسمي', reliable: 'موثوق', rumor: 'شائعة', analysis: 'تحليل' };
  R.CAT_ALIASES = {
    official: 'official', 'رسمي': 'official',
    reliable: 'reliable', trusted: 'reliable', 'موثوق': 'reliable',
    rumor: 'rumor', rumour: 'rumor', 'شائعة': 'rumor', 'شائعات': 'rumor',
    analysis: 'analysis', opinion: 'analysis', 'تحليل': 'analysis', 'تحليلات': 'analysis'
  };
  R.VIEW_TITLES = { home: 'ريال مدريد 360', matches: 'المباريات', news: 'الأخبار', table: 'الترتيب', team: 'الفريق' };
  R.state = { news: [], newsUpdatedAt: null, newsFromFeed: false, matchMode: 'upcoming', matchComp: 'all', newsCat: 'all', table: 'liga' };

  R.$ = function (id) { return document.getElementById(id); };
  R.el = function (tag, cls, text) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text !== undefined && text !== null) e.textContent = String(text);
    return e;
  };
  R.add = function (parent) { for (var i = 1; i < arguments.length; i++) { if (arguments[i]) parent.appendChild(arguments[i]); } return parent; };
  R.clear = function (node) { while (node && node.firstChild) node.removeChild(node.firstChild); return node; };
  var pad = R.pad = function (n) { return n < 10 ? '0' + n : String(n); };
  var now = R.now = function () { return Date.now(); };
  var ksa = R.ksa = function (ms) { return new Date(ms + KSA_OFFSET); };
  R.teamName = function (code, short) { var t = R.TEAMS && R.TEAMS[code]; return t ? t[short ? 1 : 0] : code; };
  R.safe = function (fn) { try { fn(); } catch (e) { if (window.console) console.error('[RM360]', e); } };

  var timeParts = R.timeParts = function (ms) {
    var k = ksa(ms), h = k.getUTCHours(), m = k.getUTCMinutes();
    return { hm: (h % 12 || 12) + ':' + pad(m), ap: h < 12 ? 'ص' : 'م' };
  };
  R.fmtTime = function (ms) { var p = timeParts(ms); return p.hm + ' ' + p.ap; };
  var fmtDate = R.fmtDate = function (ms, opts) {
    opts = opts || {};
    var k = ksa(ms), cur = ksa(now());
    var s = (opts.noDay ? '' : R.DAYS[k.getUTCDay()] + ' ') + k.getUTCDate() + ' ' + R.MONTHS[k.getUTCMonth()];
    if (opts.year || k.getUTCFullYear() !== cur.getUTCFullYear()) s += ' ' + k.getUTCFullYear();
    return s;
  };
  function arCount(n, forms) {
    if (n === 1) return forms[0];
    if (n === 2) return forms[1];
    if (n >= 3 && n <= 10) return n + ' ' + forms[2];
    return n + ' ' + forms[3];
  }
  R.relTime = function (ms, dateOnly) {
    if (dateOnly) return fmtDate(ms, { noDay: true });
    var min = Math.floor(Math.max(0, now() - ms) / 60000);
    if (min < 1) return 'الآن';
    if (min < 60) return 'قبل ' + arCount(min, ['دقيقة', 'دقيقتين', 'دقائق', 'دقيقة']);
    var h = Math.floor(min / 60);
    if (h < 24) return 'قبل ' + arCount(h, ['ساعة', 'ساعتين', 'ساعات', 'ساعة']);
    var d = Math.floor(h / 24);
    if (d < 7) return 'قبل ' + arCount(d, ['يوم', 'يومين', 'أيام', 'يومًا']);
    return fmtDate(ms, { noDay: true });
  };
  R.goalsWord = function (n) {
    var w = { 1: 'بهدف', 2: 'بهدفين', 3: 'بثلاثة أهداف', 4: 'بأربعة أهداف', 5: 'بخمسة أهداف' };
    return w[n] || ('ب' + n + ' أهداف');
  };

  /* Match model: every Real Madrid fixture and result, oldest first. */
  R.buildMatches = function (list) { return (list || []).map(function (m) {
    var played = typeof m.hs === 'number' && typeof m.as === 'number';
    var home = m.h === R.RM, r = null, rmG = null, opG = null;
    if (played) {
      rmG = home ? m.hs : m.as; opG = home ? m.as : m.hs;
      r = rmG > opG ? 'w' : rmG === opG ? 'd' : 'l';
    }
    return { id: m.id, c: m.c, t: Date.parse(m.d), h: m.h, a: m.a, hs: m.hs, as: m.as, tc: m.tc !== false, played: played,
             home: home, opp: home ? m.a : m.h, r: r, rmG: rmG, opG: opG, goals: m.goals || null, notes: m.notes || null };
  }).sort(function (a, b) { return a.t - b.t; }); };
  R.MATCHES = R.buildMatches(D && D.matches);
  R.findMatch = function (id) { for (var i = 0; i < R.MATCHES.length; i++) { if (R.MATCHES[i].id === id) return R.MATCHES[i]; } return null; };
  R.roundLabel = function (m) {
    if (m.notes && m.notes.round) return m.notes.round;
    if (m.c !== 'ucl') return '';
    var list = R.MATCHES.filter(function (x) { return x.c === 'ucl'; });
    return 'الجولة ' + (list.indexOf(m) + 1);
  };
  R.compLine = function (m) { var rl = R.roundLabel(m); return R.COMPS[m.c] + (rl ? '، ' + rl : ''); };
  R.isUpcoming = function (m) { return !m.played && m.t + R.LIVE_WINDOW > now(); };
  R.isLive = function (m) { return !m.played && m.t <= now() && m.t + R.LIVE_WINDOW > now(); };
  R.nextMatch = function () { for (var i = 0; i < R.MATCHES.length; i++) { if (R.isUpcoming(R.MATCHES[i])) return R.MATCHES[i]; } return null; };
  R.lastResult = function () { for (var i = R.MATCHES.length - 1; i >= 0; i--) { if (R.MATCHES[i].played) return R.MATCHES[i]; } return null; };
  R.venueOf = function (m) {
    if (m.notes && m.notes.venue) return m.notes.venue;
    return m.home ? 'سانتياغو برنابيو' : 'ملعب ' + R.teamName(m.opp);
  };
  R.badge = function (code, small) {
    var b = R.el('span', 'badge' + (code === R.RM ? ' rm' : '') + (small ? ' sm' : ''), code);
    b.setAttribute('aria-hidden', 'true');
    return b;
  };
  R.sourceLine = function (src) {
    var p = R.el('p', 'source-line');
    p.appendChild(document.createTextNode('المصدر: '));
    if (src.url && /^https:\/\//.test(src.url)) {
      var a = R.el('a', null, src.label); a.href = src.url; a.target = '_blank'; a.rel = 'noopener noreferrer';
      p.appendChild(a);
    } else {
      p.appendChild(document.createTextNode(src.label));
    }
    return p;
  };
})();
