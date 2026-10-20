/* RM360 audio player. Only plays persisted audio; never calls the synthesis API from browsers. */
(function () {
  'use strict';
  var records = {}, player = new Audio(), active = null, timer = null;
  player.preload = 'none';
  var css = document.createElement('style');
  css.textContent = '.rm360-listen{display:inline-flex;align-items:center;gap:.4em;margin:.5em .4em;padding:.55em .85em;border:1px solid #9bb7d8;border-radius:999px;background:#142b46;color:#fff;font:inherit;font-size:.86em;cursor:pointer;min-height:40px}.rm360-listen:focus-visible{outline:3px solid #e7c46a}.rm360-listen[aria-pressed="true"]{background:#225f85}';
  document.head.appendChild(css);
  function attach() {
    Object.keys(records).forEach(function (title) {
      var heads = document.querySelectorAll('h1,h2,h3,h4');
      heads.forEach(function (h) {
        if (h.dataset.rm360Audio || h.textContent.trim() !== title) return;
        h.dataset.rm360Audio = '1';
        var btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'rm360-listen';
        btn.textContent = '▶ استماع';
        btn.setAttribute('aria-label', 'استماع إلى ' + title);
        btn.setAttribute('aria-pressed', 'false');
        var url = records[title];
        btn.addEventListener('click', function () {
          if (active === btn && !player.paused) { player.pause(); btn.textContent = '▶ متابعة'; btn.setAttribute('aria-pressed', 'false'); return; }
          if (active !== btn) {
            if (active) { active.textContent = '▶ استماع'; active.setAttribute('aria-pressed', 'false'); }
            player.src = url;
            active = btn;
          }
          player.play().then(function () { btn.textContent = '❚❚ إيقاف مؤقت'; btn.setAttribute('aria-pressed', 'true'); })
            .catch(function () { btn.textContent = 'تعذر التشغيل'; });
        });
        h.insertAdjacentElement('afterend', btn);
      });
    });
  }
  player.addEventListener('ended', function () {
    if (active) { active.textContent = '▶ إعادة الاستماع'; active.setAttribute('aria-pressed', 'false'); }
  });
  function schedule() { if (timer) return; timer = setTimeout(function () { timer = null; attach(); }, 200); }
  Promise.all([
    fetch('./audio/manifest.json').then(function (r) { return r.ok ? r.json() : {}; }).catch(function () { return {}; }),
    fetch('./feed/index.json').then(function (r) { return r.ok ? r.json() : {}; }).catch(function () { return {}; })
  ]).then(function (results) {
    var manifest = results[0], index = results[1];
    var paths = Array.isArray(index.news) ? index.news.slice(0, 150) : [];
    return Promise.all(paths.map(function (p) {
      if (!/^items\/[a-z0-9_.-]+\.json$/.test(p)) return null;
      return fetch('./feed/' + p).then(function (r) { return r.ok ? r.json() : null; }).catch(function () { return null; });
    })).then(function (articles) {
      articles.forEach(function (a) {
        if (!a || !a.id || !a.title || !manifest[a.id]) return;
        var f = manifest[a.id].file;
        if (typeof f === 'string' && /^[a-f0-9]{16}\.mp3$/.test(f)) records[a.title] = './audio/' + f;
      });
      attach();
      new MutationObserver(schedule).observe(document.getElementById('main') || document.body, {childList:true,subtree:true});
    });
  });
})();
