// Build Real Madrid 360 into dist/: minify, pack into files small enough for the
// Vercel connector upload limit, and write an upload manifest (sha1, size, base64).
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const NM = process.argv[2];                     // node_modules with terser, csso, html-minifier-terser
const ROOT = path.resolve(__dirname, '..');
const DIST = path.join(ROOT, 'dist');
const LIMIT = 6800;                             // bytes per uploaded file
const { minify } = require(path.join(NM, 'terser'));
const csso = require(path.join(NM, 'csso'));
const htmlmin = require(path.join(NM, 'html-minifier-terser'));

const bytes = s => Buffer.byteLength(s, 'utf8');
function pack(pieces, prefix, ext, sep) {
  const out = []; let cur = '';
  for (const p of pieces) {
    if (bytes(p) > LIMIT) throw new Error(`${prefix}: piece of ${bytes(p)} bytes exceeds limit`);
    if (cur && bytes(cur) + bytes(sep) + bytes(p) > LIMIT) { out.push(cur); cur = ''; }
    cur = cur ? cur + sep + p : p;
  }
  if (cur) out.push(cur);
  return out.map((body, i) => ({ name: `${prefix}${i + 1}.${ext}`, body }));
}
function splitCss(css) {
  // split at top-level rule boundaries only
  const parts = []; let depth = 0, start = 0;
  for (let i = 0; i < css.length; i++) {
    if (css[i] === '{') depth++;
    else if (css[i] === '}') { depth--; if (depth === 0) { parts.push(css.slice(start, i + 1)); start = i + 1; } }
  }
  if (start < css.length && css.slice(start).trim()) parts.push(css.slice(start));
  return parts;
}

(async () => {
  fs.rmSync(path.join(DIST, 'a'), { recursive: true, force: true });
  fs.mkdirSync(path.join(DIST, 'a'), { recursive: true });

  // JavaScript modules, in order
  const jsDir = path.join(ROOT, 'src', 'js');
  const mods = fs.readdirSync(jsDir).filter(f => f.endsWith('.js')).sort();
  const minified = [];
  for (const f of mods) {
    const r = await minify(fs.readFileSync(path.join(jsDir, f), 'utf8'), { compress: { passes: 2 }, mangle: true, format: { comments: false, ascii_only: false } });
    minified.push(r.code);
  }
  const jsFiles = pack(minified, 'a/app', 'js', '\n');

  // CSS
  const css = csso.minify(fs.readFileSync(path.join(ROOT, 'site', 'app.css'), 'utf8'), { restructure: false }).css;
  const cssFiles = pack(splitCss(css), 'a/style', 'css', '');

  // data files (written by compile_data.py into dist/)
  const dataFiles = ['data-1.js', 'data-2.js', 'data-3.js'];

  // HTML
  const tags = cssFiles.map(f => `<link rel="stylesheet" href="/${f.name}">`)
    .concat(dataFiles.map(f => `<script src="/${f}" defer></script>`))
    .concat(jsFiles.map(f => `<script src="/${f.name}" defer></script>`)).join('\n');
  let html = fs.readFileSync(path.join(ROOT, 'src', 'index.html'), 'utf8').replace('<!--ASSETS-->', tags);
  html = await htmlmin.minify(html, { collapseWhitespace: true, conservativeCollapse: true, removeComments: true, minifyCSS: false, minifyJS: false, keepClosingSlash: true });

  for (const f of jsFiles.concat(cssFiles)) fs.writeFileSync(path.join(DIST, f.name), f.body);
  fs.writeFileSync(path.join(DIST, 'index.html'), html);
  for (const f of ['manifest.webmanifest', 'icon.svg', 'robots.txt', 'icon-192.png', 'apple-touch-icon.png', 'og.png']) {
    fs.copyFileSync(path.join(ROOT, 'site', f), path.join(DIST, f));
  }
  fs.copyFileSync(path.join(ROOT, 'src', 'icons.svg'), path.join(DIST, 'icons.svg'));
  fs.cpSync(path.join(ROOT, 'site', 'feed'), path.join(DIST, 'feed'), {recursive: true});

  // upload manifest
  const list = [];
  (function walk(dir) {
    for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
      const p = path.join(dir, e.name);
      if (e.isDirectory()) walk(p);
      else if (e.name !== 'upload.json') {
        const buf = fs.readFileSync(p);
        list.push({ file: path.relative(DIST, p), size: buf.length, sha: crypto.createHash('sha1').update(buf).digest('hex') });
      }
    }
  })(DIST);
  list.sort((a, b) => a.file.localeCompare(b.file));
  fs.writeFileSync(path.join(DIST, 'upload.json'), JSON.stringify(list, null, 1));
  for (const f of list) console.log(String(f.size).padStart(6), f.size > LIMIT ? 'TOO BIG' : '      ', f.sha, f.file);
})().catch(e => { console.error(e); process.exit(1); });
