#!/usr/bin/env python3
"""Seed the feed project from the verified snapshot in dist/data-*.js and news/news.json."""
import datetime as dt, json, os, re, shutil, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIST = os.path.join(ROOT, 'dist')
WORK = os.path.join(ROOT, 'feed', 'work')


def read(name):
    return open(os.path.join(DIST, name), encoding='utf-8').read()


def grab(src, key, opener):
    i = src.index(key + '=') + len(key) + 1
    assert src[i] == opener
    depth, j, in_str, esc = 0, i, False, False
    while True:
        ch = src[j]
        if in_str:
            if esc: esc = False
            elif ch == '\\': esc = True
            elif ch == '"': in_str = False
        elif ch == '"': in_str = True
        elif ch in '[{': depth += 1
        elif ch in ']}':
            depth -= 1
            if depth == 0:
                return json.loads(src[i:j + 1])
        j += 1


def dump(obj):
    return json.dumps(obj, ensure_ascii=False, separators=(',', ':')) + '\n'


def write(rel, obj):
    path = os.path.join(WORK, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    data = obj if isinstance(obj, str) else dump(obj)
    open(path, 'w', encoding='utf-8').write(data)


def main():
    updated = sys.argv[1]
    d1 = grab(read('data-1.js'), 'window.RM360_DATA', '{')
    d2 = read('data-2.js'); d3 = read('data-3.js')
    liga, ucl = grab(d2, 'd.liga', '['), grab(d2, 'd.ucl', '[')
    absences, abs_src = grab(d3, 'd.absences', '['), grab(d3, 'd.absencesSource', '{')
    news = json.load(open(os.path.join(ROOT, 'news', 'news.json'), encoding='utf-8'))['items']
    shutil.rmtree(WORK, ignore_errors=True)

    slugs = {'2026-10-16-tebas': 'club-demands-tebas-resignation', '2026-10-16-vini-appeal': 'vinicius-appeal-rejected',
             '2026-10-16-rm-team-news': 'real-madrid-injuries-before-sevilla', '2026-10-16-sevilla-absences': 'sevilla-absences-bernabeu',
             '2026-10-10-mourinho-presser': 'mourinho-press-conference-boycott'}
    for it in news:
        nid = it['date'].replace('-', '') + '-1200-' + slugs[it['id']]
        item = dict(it); item['id'] = nid
        write('items/%s.json' % nid, item)

    names = {'فينيسيوس جونيور': 'vinicius-junior', 'إيدير ميليتاو': 'eder-militao', 'رودريغو': 'rodrygo',
             'فيرلاند ميندي': 'ferland-mendy', 'راؤول أسينسيو': 'raul-asencio'}
    for a in absences:
        o = {'name': a['name'], 'kind': a['kind'], 'status': a['status']}
        if a.get('detail'): o['detail'] = a['detail']
        if a.get('ligaBanFixtures'): o['banFixtures'] = a['ligaBanFixtures']
        o['source'] = {'label': 'Sports Mole', 'url': abs_src['url']}
        write('absences/%s.json' % names[a['name']], o)

    matches = []
    for m in d1['matches']:
        if m.get('notes'):
            n = m['notes']; note = {'match': m['id']}
            for k in ('round', 'venue', 'opponentAbsences', 'source'):
                if n.get(k): note[k] = n[k]
            if 'source' in note: note['source'] = {'label': 'Sports Mole', 'url': note['source']['url']}
            write('notes/%s.json' % m['id'], note)
        matches.append({k: v for k, v in m.items() if k != 'notes'})
    write('matches.json', {'schema': 'rm360-matches/1', 'updatedAt': updated, 'matches': matches})
    write('tables.json', {'schema': 'rm360-tables/1', 'updatedAt': updated, 'liga': liga, 'ucl': ucl})

    played = [m for m in matches if 'hs' in m]
    last = played[-1]
    liga_games = sum(r['p'] for r in liga) // 2
    ucl_games = sum(r['p'] for r in ucl) // 2
    day = dt.datetime.fromisoformat(updated).strftime('%Y%m%d')
    write('sig/%s_L%d_U%d_R%s-%d-%d.txt' % (day, liga_games, ucl_games, last['id'], last['hs'], last['as']), 'ok\n')
    for root, _, files in os.walk(WORK):
        for f in sorted(files):
            p = os.path.join(root, f)
            print('%6d %s' % (os.path.getsize(p), os.path.relpath(p, WORK)))


if __name__ == '__main__':
    main()
