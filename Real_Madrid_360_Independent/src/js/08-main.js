/* Router, controls and start-up. */
(function (R) {
  'use strict';
  var $ = R.$, state = R.state;
  var ROUTES = { '': 'home', home: 'home', matches: 'matches', news: 'news', table: 'table', team: 'team', article: 'article' };
  function each(sel, fn) { document.querySelectorAll(sel).forEach(fn); }
  function routeInfo() {
    var raw = (location.hash || '').replace(/^#\/?/, '');
    var q = raw.split('?'), path = q[0], parts = path.split('/');
    if (parts[0] === 'article' && parts[1]) {
      var id = parts.slice(1).join('/');
      try { id = decodeURIComponent(id); } catch (e) {}
      return { view: 'article', id: id, query: q[1] || '' };
    }
    return { view: ROUTES[parts[0]] || 'home', id: '', query: q[1] || '' };
  }
  function show(first) {
    var info = routeInfo(), view = info.view;
    if (view === 'matches' && info.query === 'results') state.matchMode = 'results';
    each('.view', function (v) { v.hidden = v.getAttribute('data-view') !== view; });
    each('[data-route]', function (a) {
      var route = a.getAttribute('data-route');
      if (route === view || (view === 'article' && route === 'news')) a.setAttribute('aria-current', 'page'); else a.removeAttribute('aria-current');
    });
    if (view === 'article') {
      document.title = 'خبر | ريال مدريد 360';
      R.safe(function () { R.renderArticle(info.id); });
    } else document.title = view === 'home' ? 'ريال مدريد 360' : R.VIEW_TITLES[view] + ' | ريال مدريد 360';
    if (view === 'matches') { R.syncMatchControls(); R.safe(R.renderMatches); }
    if (view === 'news') R.safe(R.renderNewsView);
    if (view === 'table') R.safe(R.renderFullTable);
    if (!first) {
      window.scrollTo(0, 0);
      var main = $('main'); if (main && main.focus) main.focus({ preventScroll: true });
    }
  }
  function bind() {
    each('#view-matches [data-mode]', function (b) {
      b.addEventListener('click', function () { state.matchMode = b.getAttribute('data-mode'); R.syncMatchControls(); R.safe(R.renderMatches); });
    });
    each('#view-matches [data-comp]', function (b) {
      b.addEventListener('click', function () { state.matchComp = b.getAttribute('data-comp'); R.syncMatchControls(); R.safe(R.renderMatches); });
    });
    each('#news-filters [data-cat]', function (b) {
      b.addEventListener('click', function () {
        state.newsCat = b.getAttribute('data-cat');
        each('#news-filters [data-cat]', function (x) { x.setAttribute('aria-pressed', String(x === b)); });
        R.safe(R.renderNewsView);
      });
    });
    each('#view-table [data-table]', function (b) {
      b.addEventListener('click', function () {
        state.table = b.getAttribute('data-table');
        each('#view-table [data-table]', function (x) { x.setAttribute('aria-selected', String(x === b)); });
        R.safe(R.renderFullTable);
      });
    });
    window.addEventListener('hashchange', function () { show(false); });
    var tick = $('ticker');
    document.addEventListener('visibilitychange', function () {
      if (tick) tick.classList.toggle('paused', document.hidden);
      if (!document.hidden) { R.safe(R.renderHero); R.safe(R.renderHomeNews); }
    });
    if (tick) {
      tick.addEventListener('touchstart', function () { tick.classList.add('paused'); }, { passive: true });
      tick.addEventListener('touchend', function () { setTimeout(function () { tick.classList.remove('paused'); }, 1200); }, { passive: true });
    }
  }
  function init() {
    if (!R.D || !Array.isArray(R.D.matches)) {
      var main = R.clear($('main'));
      main.appendChild(R.el('p', 'empty', 'تعذّر تحميل بيانات المنصة. أعد تحميل الصفحة بعد قليل.'));
      return;
    }
    bind();
    [R.renderStamp, R.renderHero, R.renderLastResult, R.renderMiniTable, R.renderHomeAbsences, R.renderTeam].forEach(R.safe);
    show(true);
    R.loadNews();
    R.loadFeed();
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init); else init();
})(window.RM360);
