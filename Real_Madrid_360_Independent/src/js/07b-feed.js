/* Live feed: news, fixtures, tables, absences and match notes published hourly to the feed project.
   Every file is validated here; anything invalid is ignored and the bundled snapshot stays on screen. */
(function (R) {
  'use strict';
  var D = R.D;
  var BASES = ['/feed/'];
  var CODE = /^[A-Z0-9]{2,4}$/, ID = /^[0-9]{4,12}$/, PATH = /^[a-z0-9][a-z0-9_\/.\-]{0,150}\.json$/;

  function int(v, max) { return typeof v === 'number' && isFinite(v) && v >= 0 && v <= max && Math.floor(v) === v; }
  function txt(v, max) {
    if (typeof v !== 'string') return null;
    var s = v.replace(/<[^>]*>/g, '').replace(/[\u0000-\u001F\u007F]/g, ' ').trim();
    return s && s.length <= max ? s : null;
  }
  function link(u) {
    if (typeof u !== 'string') return null;
    try { var x = new URL(u.trim()); return x.protocol === 'https:' && x.hostname.indexOf('.') > 0 ? x.href : null; } catch (e) { return null; }
  }
  function src(s) { if (!s || typeof s !== 'object') return null; var l = txt(s.label, 80), u = link(s.url); return l && u ? { label: l, url: u } : null; }
  function okPath(p) { return typeof p === 'string' && PATH.test(p) && p.indexOf('..') === -1; }
  function when(v) { var t = typeof v === 'string' ? Date.parse(v) : NaN; return isNaN(t) || t > R.now() + 2 * 3600 * 1000 ? null : t; }
  function idOf(v) { var s = typeof v === 'number' ? String(v) : v; return typeof s === 'string' && ID.test(s) ? s : null; }

  function cleanMatch(m) {
    if (!m || typeof m !== 'object') return null;
    var id = idOf(m.id), t = typeof m.d === 'string' ? Date.parse(m.d) : NaN;
    if (!id || (m.c !== 'liga' && m.c !== 'ucl') || isNaN(t)) return null;
    if (!CODE.test(m.h || '') || !CODE.test(m.a || '') || m.h === m.a || (m.h !== R.RM && m.a !== R.RM)) return null;
    var out = { id: id, c: m.c, d: m.d, h: m.h, a: m.a, tc: m.tc !== false };
    var hasH = m.hs !== undefined && m.hs !== null, hasA = m.as !== undefined && m.as !== null;
    if (hasH !== hasA) return null;
    if (hasH) {
      if (!int(m.hs, 20) || !int(m.as, 20) || t > R.now()) return null;
      out.hs = m.hs; out.as = m.as;
      var g = m.goals;
      if (g && Array.isArray(g.home) && Array.isArray(g.away) && g.home.length === m.hs && g.away.length === m.as &&
          g.home.concat(g.away).every(function (x) { return int(x, 130) && x >= 1; })) {
        out.goals = { home: g.home.slice(), away: g.away.slice() };
      }
    }
    return out;
  }
  function cleanMatches(j) {
    if (!j || j.schema !== 'rm360-matches/1' || !Array.isArray(j.matches) || j.matches.length < 1 || j.matches.length > 90) return null;
    var out = [], seen = {};
    for (var i = 0; i < j.matches.length; i++) {
      var m = cleanMatch(j.matches[i]);
      if (!m || seen[m.id]) return null;
      seen[m.id] = true; out.push(m);
    }
    return { list: out, t: when(j.updatedAt) };
  }
  function cleanRows(rows, kind) {
    var min = kind === 'liga' ? 18 : 30, max = kind === 'liga' ? 22 : 40;
    if (!Array.isArray(rows) || rows.length < min || rows.length > max) return null;
    var out = [], seen = {}, sw = 0, sl = 0, sd = 0, sgf = 0, sga = 0, withGoals = 0;
    for (var i = 0; i < rows.length; i++) {
      var r = rows[i];
      if (!r || !CODE.test(r.t || '') || seen[r.t]) return null;
      // UEFA may give the same official position to teams tied on all active ranking criteria.
      var prev = i > 0 ? rows[i - 1] : null;
      var tied = prev && r.r === prev.r && r.pts === prev.pts &&
        typeof r.gf === 'number' && typeof prev.gf === 'number' &&
        r.gf === prev.gf && (r.gf - r.ga) === (prev.gf - prev.ga);
      if (r.r !== i + 1 && !tied) return null;
      if (!int(r.p, 60) || !int(r.w, 60) || !int(r.d, 60) || !int(r.l, 60) || !int(r.pts, 200)) return null;
      if (r.w + r.d + r.l !== r.p || r.pts > 3 * r.w + r.d) return null;
      var row = { r: r.r, t: r.t, p: r.p, w: r.w, d: r.d, l: r.l, pts: r.pts };
      if (kind === 'liga' && int(r.gf, 300) && int(r.ga, 300)) { row.gf = r.gf; row.ga = r.ga; sgf += r.gf; sga += r.ga; withGoals++; }
      seen[r.t] = true; sw += r.w; sl += r.l; sd += r.d; out.push(row);
    }
    if (sw !== sl || sd % 2 !== 0) return null;
    if (kind === 'liga') {
      if (withGoals && withGoals !== out.length) return null;
      if (withGoals && sgf !== sga) return null;
    }
    return out;
  }
  function cleanTables(j) {
    if (!j || j.schema !== 'rm360-tables/1') return null;
    var liga = cleanRows(j.liga, 'liga'), ucl = cleanRows(j.ucl, 'ucl');
    return liga || ucl ? { liga: liga, ucl: ucl, t: when(j.updatedAt) } : null;
  }
  function cleanAbsence(a) {
    if (!a || typeof a !== 'object') return null;
    var name = txt(a.name, 40), status = txt(a.status, 90);
    if (!name || !status || (a.kind !== 'suspended' && a.kind !== 'injured')) return null;
    var out = { name: name, kind: a.kind, status: status }, detail = txt(a.detail, 220), s = src(a.source);
    if (detail) out.detail = detail;
    if (s) out.source = s;
    if (a.kind === 'suspended') {
      var ids = (Array.isArray(a.banFixtures) ? a.banFixtures : []).map(idOf).filter(Boolean).slice(0, 12);
      if (!ids.length) return null;
      out.banFixtures = ids;
    }
    return out;
  }
  function cleanNote(n) {
    if (!n || typeof n !== 'object') return null;
    var id = idOf(n.match);
    if (!id) return null;
    var notes = {}, round = txt(n.round, 30), venue = txt(n.venue, 60), s = src(n.source);
    if (round) notes.round = round;
    if (venue) notes.venue = venue;
    if (s && Array.isArray(n.opponentAbsences)) {
      var list = n.opponentAbsences.map(function (x) { return txt(x, 120); }).filter(Boolean).slice(0, 10);
      if (list.length) { notes.opponentAbsences = list; notes.source = s; }
    }
    return Object.keys(notes).length ? { id: id, notes: notes } : null;
  }

  function getAll(base, paths) {
    return Promise.all(paths.map(function (p) { return R.fetchJSON(base + p, 8000).catch(function () { return null; }); }));
  }
  function pathList(v, max) { return (Array.isArray(v) ? v : []).filter(okPath).slice(0, max); }
  function index() {
    return R.fetchJSON(BASES[0] + 'index.json', 6000).then(function (j) { return { j: j, base: BASES[0] }; })
      .catch(function () { return R.fetchJSON(BASES[1] + 'index.json', 6000).then(function (j) { return { j: j, base: BASES[1] }; }); });
  }

  R.loadFeed = function () {
    if (!window.fetch || !window.Promise) return;
    index().then(function (res) {
      var idx = res.j, base = res.base;
      if (!idx || idx.schema !== 'rm360-feed/1') throw new Error('bad index');
      var feedTime = when(idx.updatedAt);
      var newsPaths = pathList(idx.news, 100);
      var newsTask = getAll(base, newsPaths).then(function (list) {
        var items = R.validateNews(list.filter(Boolean));
        if (items.length) R.setNews(items, feedTime); else R.loadLegacyNews();
      });
      var dataTask = Promise.all([
        okPath(idx.matches) ? R.fetchJSON(base + idx.matches, 8000).catch(function () { return null; }) : null,
        okPath(idx.tables) ? R.fetchJSON(base + idx.tables, 8000).catch(function () { return null; }) : null,
        getAll(base, pathList(idx.absences, 15)),
        getAll(base, pathList(idx.notes, 6))
      ]).then(function (r) {
        var changed = false, m = cleanMatches(r[0]), tb = cleanTables(r[1]);
        if (m) { D.matches = m.list; changed = true; }
        var notes = r[3].map(cleanNote).filter(Boolean);
        if (m || notes.length) {
          var byId = {};
          notes.forEach(function (n) { byId[n.id] = n.notes; });
          D.matches.forEach(function (x) { if (byId[x.id]) x.notes = byId[x.id]; else if (m) delete x.notes; });
          changed = true;
        }
        if (tb) {
          if (tb.liga) D.liga = tb.liga;
          if (tb.ucl) D.ucl = tb.ucl;
          if (tb.t) D.tablesUpdatedAt = tb.t;
          changed = true;
        }
        if (Array.isArray(idx.absences)) {
          var abs = r[2].map(cleanAbsence).filter(Boolean)
            .sort(function (x, y) { return (x.kind === 'suspended' ? 0 : 1) - (y.kind === 'suspended' ? 0 : 1); });
          if (abs.length || r[2].length === 0) { D.absences = abs; D.absencesSource = null; changed = true; }
        }
        if (feedTime && feedTime > (Date.parse(D.updatedAt) || 0)) { D.updatedAt = new Date(feedTime).toISOString(); changed = true; }
        if (!changed) return;
        R.MATCHES = R.buildMatches(D.matches);
        [R.renderStamp, R.renderHero, R.renderLastResult, R.renderMiniTable, R.renderHomeAbsences, R.renderTeam,
          R.renderMatches, R.renderFullTable].forEach(R.safe);
      });
      return Promise.all([newsTask, dataTask]);
    }).catch(function () { R.loadLegacyNews(); });
  };
})(window.RM360);
