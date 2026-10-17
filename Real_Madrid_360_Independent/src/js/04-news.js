/* News: validation, internal article pages, ticker and update stamp. */
(function (R) {
  'use strict';
  var el = R.el, add = R.add, clear = R.clear, $ = R.$, D = R.D, state = R.state;

  function ensureArticleView() {
    if (!document.querySelector('link[data-rm360-article-css]')) {
      var css = document.createElement('link'); css.rel = 'stylesheet'; css.href = './article.css'; css.setAttribute('data-rm360-article-css', '1');
      document.head.appendChild(css);
    }
    if (!$('view-article')) {
      var main = $('main'), section = el('section', 'view'), detail = el('div');
      if (!main) return;
      section.id = 'view-article'; section.setAttribute('data-view', 'article'); section.hidden = true; section.setAttribute('aria-live', 'polite');
      detail.id = 'article-detail'; add(section, detail); add(main, section);
    }
  }
  ensureArticleView();
  (function alignTaxonomyLabels() {
    var reliable = document.querySelector('#news-filters [data-cat="reliable"]');
    var rumor = document.querySelector('#news-filters [data-cat="rumor"]');
    var legend = $('news-legend');
    if (reliable) reliable.textContent = 'تقرير صحفي موثوق';
    if (rumor) rumor.textContent = 'غير مؤكد';
    if (legend) legend.textContent = 'درجة التأكد: رسمي، تقرير صحفي موثوق، أو غير مؤكد. ويظهر التحليل والتوقع كنوع محتوى مستقل عن درجة التأكد.';
  })();

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
    return { t: t, dateOnly: dateOnly, raw: s };
  }
  function hashId(s) {
    var h = 2166136261, i;
    for (i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h += (h << 1) + (h << 4) + (h << 7) + (h << 8) + (h << 24); }
    return 'n-' + (h >>> 0).toString(36);
  }
  function cleanSource(s) {
    if (typeof s === 'string') {
      var n = cleanText(s, 100);
      return n ? { label: n, url: '' } : null;
    }
    if (!s || typeof s !== 'object') return null;
    var label = cleanText(s.label || s.name || s.source || '', 100);
    var url = validUrl(s.url || s.link || '');
    return label ? { label: label, url: url } : null;
  }
  function sourceList(it, primaryLabel, primaryUrl) {
    var out = [], seen = {};
    function push(s) {
      var x = cleanSource(s);
      if (!x) return;
      var key = x.url || x.label;
      if (seen[key]) return;
      seen[key] = true;
      out.push(x);
    }
    if (Array.isArray(it.sources)) it.sources.slice(0, 12).forEach(push);
    if (primaryLabel) push({ label: primaryLabel, url: primaryUrl });
    return out;
  }
  function cleanBody(v) {
    var out = [];
    if (typeof v === 'string') {
      v.split(/\n\s*\n/).forEach(function (p) { p = cleanText(p, 5000); if (p) out.push(p); });
    } else if (Array.isArray(v)) {
      v.slice(0, 30).forEach(function (p) { p = cleanText(p, 5000); if (p) out.push(p); });
    }
    return out.slice(0, 24);
  }
  function cleanSections(v) {
    if (!Array.isArray(v)) return [];
    var out = [];
    v.slice(0, 14).forEach(function (s) {
      if (!s || typeof s !== 'object') return;
      var title = cleanText(s.title || s.heading || '', 120);
      if (!title) return;
      var body = cleanBody(s.body || s.text || s.paragraphs || []);
      var items = [];
      if (Array.isArray(s.items)) {
        s.items.slice(0, 20).forEach(function (x) { x = cleanText(String(x), 700); if (x) items.push(x); });
      }
      if (body.length || items.length) out.push({ title: title, body: body, items: items });
    });
    return out;
  }
  function contentType(it, cat) {
    var raw = cleanText(it.contentType || it.content_type || it.type || '', 30).toLowerCase();
    if (raw === 'analysis' || raw === 'تحليل' || cat === 'analysis') return 'analysis';
    if (raw === 'prediction' || raw === 'expected' || raw === 'توقع') return 'prediction';
    return 'news';
  }
  function certainty(it, cat, type) {
    var raw = cleanText(it.certainty || it.status || '', 40).toLowerCase();
    if (raw === 'official' || raw === 'رسمي') return 'official';
    if (raw === 'reliable' || raw === 'trusted' || raw === 'موثوق' || raw === 'تقرير صحفي موثوق') return 'reliable';
    if (raw === 'unconfirmed' || raw === 'rumor' || raw === 'rumour' || raw === 'غير مؤكد' || raw === 'شائعة') return 'unconfirmed';
    if (cat === 'official') return 'official';
    if (cat === 'reliable') return 'reliable';
    if (cat === 'rumor') return 'unconfirmed';
    if (type === 'analysis' || type === 'prediction') return null;
    return 'unconfirmed';
  }
  function typeLabel(t) {
    return t === 'analysis' ? 'تحليل' : t === 'prediction' ? 'توقع' : 'خبر';
  }
  function certaintyLabel(c) {
    return c === 'official' ? 'رسمي' : c === 'reliable' ? 'تقرير صحفي موثوق' : c === 'unconfirmed' ? 'غير مؤكد' : 'لا تنطبق';
  }
  function certaintyClass(c) {
    return c === 'official' ? 'official' : c === 'reliable' ? 'reliable' : c === 'unconfirmed' ? 'rumor' : 'analysis';
  }
  function defaultVerification(c, type) {
    if (c === 'official') return 'يدعمه مصدر أصلي مختص مذكور في قسم المصادر.';
    if (c === 'reliable') return 'منشور لدى مصدر صحفي معتبر، من دون إعلان رسمي مطابق حتى وقت التحديث.';
    if (c === 'unconfirmed') return 'لم يتوافر تأكيد كافٍ من مصدر أصلي مختص حتى وقت التحديث.';
    if (type === 'analysis') return 'هذه مادة تحليلية؛ وسم التأكد يخص الادعاءات الخبرية داخلها لا الرأي التحليلي نفسه.';
    if (type === 'prediction') return 'هذه مادة توقعية وليست إعلانًا رسميًا، ويجب عدم قراءتها كتشكيلة أو قرار مؤكد.';
    return 'لم تتوافر درجة تأكد مستقلة لهذه المادة.';
  }
  function validateItems(items) {
    if (!Array.isArray(items)) return [];
    var seen = {}, out = [];
    items.slice(0, 60).forEach(function (it) {
      if (!it || typeof it !== 'object') return;
      var raw = String(it.category || '').trim();
      var cat = R.CAT_ALIASES[raw.toLowerCase()] || R.CAT_ALIASES[raw] || 'reliable';
      var title = cleanText(it.title, 180);
      var primary = cleanSource(it.source);
      var source = primary ? primary.label : cleanText(it.source, 100);
      var url = validUrl(it.url || (primary && primary.url) || '');
      var published = parseNewsDate(it.publishedAt || it.timestamp_utc || it.date);
      if (!title || title.length < 6 || !source || source.length < 2 || !url || !published || seen[title]) return;
      seen[title] = true;
      var type = contentType(it, cat), cert = certainty(it, cat, type);
      var updated = parseNewsDate(it.updatedAt || it.updated_at_utc || it.verifiedAt || '');
      var event = parseNewsDate(it.eventAt || it.event_at_utc || '');
      var id = cleanText(it.id, 140) || hashId(title + '|' + published.t);
      out.push({
        id: id, cat: cat, title: title, summary: cleanText(it.summary, 900), body: cleanBody(it.body),
        sections: cleanSections(it.sections), source: source, url: url, sources: sourceList(it, source, url),
        image: validUrl(it.image || ''), t: published.t, dateOnly: published.dateOnly, publishedAt: published.t,
        updatedAt: updated ? updated.t : published.t, eventAt: event ? event.t : null, contentType: type,
        certainty: cert, verificationNote: cleanText(it.verificationNote || it.verification_note || '', 700) || defaultVerification(cert, type),
        tags: Array.isArray(it.tags) ? it.tags.slice(0, 12).map(function (x) { return cleanText(String(x), 60); }).filter(Boolean) : []
      });
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
    state.news = items; state.newsFromFeed = true; state.newsUpdatedAt = updatedAt || (items[0] && items[0].t) || null;
    renderAll();
  };
  R.loadNews = function () { state.news = validateItems(D.newsFallback || []); renderAll(); };
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

  function internalHref(n) { return '#/article/' + encodeURIComponent(n.id); }
  function badge(text, cls) { return el('span', 'tag ' + cls, text); }
  function newsItem(n) {
    var li = el('li'), art = el('article', 'news-item'), top = el('div', 'top'), h3 = el('h3');
    add(top, badge(typeLabel(n.contentType), n.contentType === 'news' ? 'content-news' : 'analysis'));
    add(top, badge(certaintyLabel(n.certainty), certaintyClass(n.certainty)));
    add(top, el('span', 'when', R.relTime(n.t, n.dateOnly)));
    var titleLink = el('a', 'news-internal', n.title); titleLink.href = internalHref(n); add(h3, titleLink);
    if (n.image) {
      var imgLink = el('a', 'news-image-link'); imgLink.href = internalHref(n);
      var img = el('img', 'news-image'); img.src = n.image; img.alt = ''; img.loading = 'lazy'; add(imgLink, img); add(art, imgLink);
    }
    add(art, top, h3);
    if (n.summary) add(art, el('p', 'sum', n.summary));
    add(art, el('p', 'verification-note', certaintyLabel(n.certainty) + ': ' + n.verificationNote));
    var actions = el('div', 'news-actions');
    var more = el('a', 'read-more', 'اقرأ المزيد داخل المنصة'); more.href = internalHref(n); add(actions, more); add(art, actions);
    add(li, art);
    return li;
  }
  R.findNews = function (id) {
    for (var i = 0; i < state.news.length; i++) if (state.news[i].id === id) return state.news[i];
    return null;
  };
  function timeLine(label, ms) {
    if (!ms) return null;
    return el('div', 'article-meta-item', label + ': ' + R.fmtDate(ms, { noDay: false, year: true }) + '، ' + R.fmtTime(ms) + ' بتوقيت السعودية');
  }
  function renderSection(parent, title, paragraphs, items) {
    if ((!paragraphs || !paragraphs.length) && (!items || !items.length)) return;
    var sec = el('section', 'article-section'), h = el('h2', null, title); add(sec, h);
    (paragraphs || []).forEach(function (p) { add(sec, el('p', null, p)); });
    if (items && items.length) {
      var ul = el('ul', 'article-points'); items.forEach(function (x) { add(ul, el('li', null, x)); }); add(sec, ul);
    }
    add(parent, sec);
  }
  R.renderArticle = function (id) {
    var wrap = clear($('article-detail'));
    if (!wrap) return;
    var n = R.findNews(id);
    if (!n) {
      add(wrap, el('p', 'empty', state.newsFromFeed ? 'لم يعد هذا الخبر متاحًا في التغذية الحالية.' : 'جارٍ تحميل الخبر من التغذية الحالية…'));
      var back0 = el('a', 'article-back', 'العودة إلى الأخبار'); back0.href = '#/news'; add(wrap, back0);
      return;
    }
    var article = el('article', 'article-page');
    var back = el('a', 'article-back', '← العودة إلى الأخبار'); back.href = '#/news'; add(article, back);
    var badges = el('div', 'article-badges');
    add(badges, badge(typeLabel(n.contentType), n.contentType === 'news' ? 'content-news' : 'analysis'));
    add(badges, badge(certaintyLabel(n.certainty), certaintyClass(n.certainty)));
    add(article, badges, el('h1', 'article-title', n.title));
    if (n.summary) add(article, el('p', 'article-lead', n.summary));
    if (n.image) { var figure = el('figure', 'article-figure'), image = el('img'); image.src = n.image; image.alt = ''; add(figure, image); add(article, figure); }
    var meta = el('div', 'article-meta');
    add(meta, timeLine('تاريخ النشر', n.publishedAt));
    if (n.updatedAt && n.updatedAt !== n.publishedAt) add(meta, timeLine('آخر تحديث', n.updatedAt));
    if (n.eventAt) add(meta, timeLine('وقت الحدث', n.eventAt));
    add(meta, el('div', 'article-meta-item', 'نوع المحتوى: ' + typeLabel(n.contentType)));
    add(meta, el('div', 'article-meta-item', 'درجة التأكد: ' + certaintyLabel(n.certainty)));
    add(article, meta);
    var verify = el('aside', 'verification-box');
    add(verify, el('strong', null, 'سبب التصنيف: '), document.createTextNode(n.verificationNote));
    add(article, verify);
    renderSection(article, 'تفاصيل الخبر', n.body, []);
    n.sections.forEach(function (s) { renderSection(article, s.title, s.body, s.items); });
    if (!n.body.length && !n.sections.length) {
      renderSection(article, 'تفاصيل الخبر', ['المعلومات المتاحة حاليًا تقتصر على الخلاصة المنشورة أعلاه. لم تضف المنصة تفاصيل غير متحقق منها لاستكمال الخبر.'], []);
    }
    var srcSec = el('section', 'article-section sources-section'), sh = el('h2', null, 'المصادر'); add(srcSec, sh);
    if (n.sources.length) {
      var ul = el('ul', 'source-list');
      n.sources.forEach(function (s) {
        var li = el('li');
        if (s.url) {
          var a = el('a', null, s.label); a.href = s.url; a.target = '_blank'; a.rel = 'noopener noreferrer'; add(li, a);
        } else add(li, document.createTextNode(s.label));
        add(ul, li);
      });
      add(srcSec, ul, el('p', 'source-help', 'فتح المصادر اختياري ويكون في علامة تبويب جديدة.'));
    } else add(srcSec, el('p', null, 'لم تتوافر روابط مصادر إضافية قابلة للتحقق في بيانات الخبر الحالية.'));
    add(article, srcSec);
    add(wrap, article);
    document.title = n.title + ' | ريال مدريد 360';
  };
  R.renderHomeNews = function () {
    var ol = clear($('home-news')), list = state.news.slice(0, 4);
    if (!list.length) { add(ol, el('li', 'empty', 'لا توجد أخبار حاليًا.')); return; }
    list.forEach(function (n) { add(ol, newsItem(n)); });
  };
  R.renderNewsView = function () {
    var ol = clear($('news-list'));
    var list = state.news.filter(function (n) {
      if (state.newsCat === 'all') return true;
      if (state.newsCat === 'analysis') return n.contentType === 'analysis';
      return n.cat === state.newsCat;
    });
    if (!list.length) add(ol, el('li', 'empty', 'لا توجد أخبار في هذا التصنيف حاليًا.'));
    list.forEach(function (n) { add(ol, newsItem(n)); });
    var stamp = $('news-stamp');
    if (stamp) stamp.textContent = state.newsUpdatedAt ? 'آخر تحديث للأخبار: ' + R.fmtDate(state.newsUpdatedAt, { noDay: true }) + '، ' + R.fmtTime(state.newsUpdatedAt) + ' بتوقيت السعودية' : 'أخبار موثقة بمصادرها';
  };
  function renderTicker() {
    var bar = $('ticker'), track = clear($('ticker-track')), list = state.news.slice(0, 6);
    if (!list.length) { bar.hidden = true; return; }
    for (var copy = 0; copy < 2; copy++) {
      list.forEach(function (n) {
        var a = el('a', null, n.title); a.href = internalHref(n);
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
  function rerenderOpenArticle() {
    var m = (location.hash || '').match(/^#\/article\/(.+)$/);
    if (!m) return;
    try { R.renderArticle(decodeURIComponent(m[1].split('?')[0])); } catch (e) { R.renderArticle(m[1]); }
  }
  function renderAll() { R.safe(renderTicker); R.safe(R.renderHomeNews); R.safe(R.renderNewsView); R.safe(R.renderStamp); R.safe(rerenderOpenArticle); }
})(window.RM360);
