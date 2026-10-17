/* News: validation of the feed, rendering, ticker and update stamp. */
(function (R) {
  'use strict';
  var el = R.el, add = R.add, clear = R.clear, $ = R.$, D = R.D, state = R.state;

  function cleanText(v, max) {
    if (typeof v !== 'string') return '';
    var s = v.replace(/<[^>]*>/g, '').replace(/[\u0000-\u0008\u000B\u000C\u000E-\u001F\u007F]/g, '').trim();
    if (max && s.length > max) s = s.slice(0, max - 1).trim() + '…';
    return s;
  }
  function validUrl(u) {
    if (typeof u !== 'string') return '';
    try { var x = new URL(u.trim()); return (x.protocol === 'https:' && x.hostname.indexOf('.') > 0) ? x.href : ''; } catch (e) { return ''; }
  }
  function parseNewsDate(v) {
    if (typeof v !== 'string') return null;
    var s = v.trim(), dateOnly = /^\d{4}-\d{2}-\d{2}$/.test(s);
    var t = Date.parse(dateOnly ? s + 'T12:00:00+03:00' : s);
    if (isNaN(t) || t > R.now() + 2 * 3600 * 1000) return null;
    return { t: t, dateOnly: dateOnly };
  }
  function validateItems(items) {
    if (!Array.isArray(items)) return [];
    var seen = {}, out = [];
    items.slice(0, 60).forEach(function (it) {
      if (!it || typeof it !== 'object') return;
      var raw = String(it.category || '').trim();
      var cat = R.CAT_ALIASES[raw.toLowerCase()] || R.CAT_ALIASES[raw];
      var title = cleanText(it.title, 160), source = cleanText(it.source, 60), url = validUrl(it.url);
      var dt = parseNewsDate(it.date || it.publishedAt);
      if (!cat || title.length < 6 || source.length < 2 || !url || !dt || seen[title]) return;
      seen[title] = true;
      out.push({ cat: cat, title: title, summary: cleanText(it.summary, 420), body: cleanText(it.body, 4000),
                 source: source, url: url, t: dt.t, dateOnly: dt.dateOnly });
    });
    out.sort(function (a, b) { return b.t - a.t; });
    return out.slice(0, 40);
  }
  function fetchJSON(url, ms) {
    return new Promise(function (resolve, reject) {
      var done = false;
      var timer = setTimeout(function () { if (!done) { done = true; reject(new Error('timeout')); } }, ms);
      fetch(url, { cache: 'no-cache', credentials: 'omit' })
        .then(function (r) { if (!r.ok) throw new Error('HTTP ' + r.status); return r.json(); })
        .then(function (j) { if (!done) { done = true; clearTimeout(timer); resolve(j); } })
        .catch(function (e) { if (!done) { done = true; clearTimeout(timer); reject(e); } });
    });
  }
  R.validateNews = validateItems;
  R.fetchJSON = fetchJSON;
  R.parseNewsDate = parseNewsDate;
  R.setNews = function (items, updatedAt) {
    state.news = items; state.newsFromFeed = true; state.newsUpdatedAt = updatedAt || items[0].t;
    renderAll();
  };
  /* Verified news bundled with the site, shown until the live feed arrives. */
  R.loadNews = function () {
    state.news = validateItems(D.newsFallback || []);
    renderAll();
  };
  /* Older single-file feed, used only when the feed index is unavailable. */
  R.loadLegacyNews = function () {
    if (!window.fetch) return;
    (function attempt(i) {
      if (i >= R.NEWS_URLS.length) return;
      fetchJSON(R.NEWS_URLS[i], 6000).then(function (j) {
        var items = validateItems(j && j.items);
        if (!items.length) throw new Error('empty feed');
        var up = parseNewsDate(j.updatedAt);
        R.setNews(items, up ? up.t : null);
      }).catch(function () { attempt(i + 1); });
    })(0);
  };

  function link(text, href) { var a = el('a', null, text); a.href = href; a.target = '_blank'; a.rel = 'noopener noreferrer'; return a; }
  function newsItem(n, withBody) {
    var li = el('li'), art = el('article', 'news-item'), top = el('div', 'top'), h3 = el('h3'), src = el('p', 'src');
    add(top, el('span', 'tag ' + n.cat, R.CATS[n.cat]), el('span', 'when', R.relTime(n.t, n.dateOnly)));
    add(h3, link(n.title, n.url));
    add(art, top, h3);
    if (n.summary) add(art, el('p', 'sum', n.summary));
    if (withBody && n.body) {
      var det = el('details'); add(det, el('summary', null, 'التفاصيل'), el('p', null, n.body)); add(art, det);
    }
    src.appendChild(document.createTextNode('المصدر: '));
    add(src, link(n.source, n.url));
    add(art, src);
    add(li, art);
    return li;
  }
  R.renderHomeNews = function () {
    var ol = clear($('home-news')), list = state.news.slice(0, 4);
    if (!list.length) { add(ol, el('li', 'empty', 'لا توجد أخبار حاليًا.')); return; }
    list.forEach(function (n) { add(ol, newsItem(n, false)); });
  };
  R.renderNewsView = function () {
    var ol = clear($('news-list'));
    var list = state.news.filter(function (n) { return state.newsCat === 'all' || n.cat === state.newsCat; });
    if (!list.length) add(ol, el('li', 'empty', 'لا توجد أخبار في هذا التصنيف حاليًا.'));
    list.forEach(function (n) { add(ol, newsItem(n, true)); });
    var stamp = $('news-stamp');
    if (stamp) stamp.textContent = state.newsUpdatedAt ? 'آخر تحديث للأخبار: ' + R.fmtDate(state.newsUpdatedAt, { noDay: true }) + '، ' + R.fmtTime(state.newsUpdatedAt) : 'أخبار موثقة بمصادرها';
  };
  function renderTicker() {
    var bar = $('ticker'), track = clear($('ticker-track')), list = state.news.slice(0, 6);
    if (!list.length) { bar.hidden = true; return; }
    for (var copy = 0; copy < 2; copy++) {
      list.forEach(function (n) {
        var a = el('a', null, n.title); a.href = '#/news';
        if (copy === 1) { a.setAttribute('aria-hidden', 'true'); a.tabIndex = -1; }
        add(track, a);
      });
    }
    bar.hidden = false;
    requestAnimationFrame(function () { track.style.setProperty('--dur', Math.max(24, Math.round(track.scrollWidth / 2 / 55)) + 's'); });
  }
  R.renderStamp = function () {
    var dt = Date.parse(D.updatedAt), t = dt;
    if (state.newsUpdatedAt && state.newsUpdatedAt > t) t = state.newsUpdatedAt;
    if (!isNaN(t)) $('stamp').textContent = 'محدّث ' + R.fmtTime(t);
    var ts = $('table-stamp'), tt = D.tablesUpdatedAt || dt;
    if (ts && !isNaN(tt)) ts.textContent = 'حتى ' + R.fmtDate(tt, { noDay: true }) + '، ' + R.fmtTime(tt) + ' بتوقيت السعودية';
  };
  function renderAll() { R.safe(renderTicker); R.safe(R.renderHomeNews); R.safe(R.renderNewsView); R.safe(R.renderStamp); }
})(window.RM360);
