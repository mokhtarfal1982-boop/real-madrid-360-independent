#!/usr/bin/env python3
"""Real Madrid 360 feed tool. Builds, validates and plans deployments for the feed project
(Vercel project "real-madrid-360-news", served to the site under /feed/).

Commands
  flatten  TREE.json > current.json
           TREE.json: the exact JSON returned by list_deployment_files for the live deployment.
  unb64    B64.txt SHA OUT
           Decodes base64 copied from get_deployment_file_contents and checks it against the file's uid (sha1).
  sigcheck CURRENT.json LIGA_STANDINGS.txt UCL_STANDINGS.txt
           Prints SAME when today's date and the number of finished La Liga / UCL games match the live sig marker.
  rminfo   LIGA.txt UCL.txt
           Prints Real Madrid's latest finished match and next matches.
  matches  LIGA.txt UCL.txt [GOALS.txt] --updated ISO > matches.json
           LIGA/UCL lines: ID STATUS START_ISO HOME AWAY HS AS   (one Real Madrid match per line, '-' for no score)
           GOALS lines:    MATCH_ID home M,M,M away M,M          (use '-' for no goals)
  tables   LIGA_STANDINGS.txt UCL_STANDINGS.txt GOALS_STATE.json WINDOW.txt --updated ISO --state-out PATH
           [--fix FIX.txt] [--no-goals] > tables.json
           STANDINGS lines: RANK CODE W D L PTS
           GOALS_STATE.json: the live state/goals.json ({"teams": {CODE: [P, GF, GA]}, "counted": [match ids]})
           WINDOW lines: ID HOME AWAY HS AS   (every FINAL La Liga match in today's scores window, all teams)
           FIX lines:    ID HOME AWAY HS AS   (every FINAL La Liga match of the season for the teams the error named)
           --no-goals builds the tables without goals for/against and leaves the state untouched.
  sig      LIGA_STANDINGS.txt UCL_STANDINGS.txt LIGA.txt UCL.txt WORKDIR
           Writes the new change marker WORKDIR/sig/<signature>.txt.
  plan     CURRENT.json WORKDIR --updated ISO [--remove PATH ...]
           CURRENT.json: [{"file": "...", "sha": "..."}] from the live deployment (see flatten).
           Writes WORKDIR/index.json, validates every new file, prints uploads and the files array.
  b64      FILE    prints the file's size, sha1 and base64 for upload_file
"""
import base64, datetime as dt, hashlib, json, os, re, sys

KSA = dt.timezone(dt.timedelta(hours=3))
RM = 'RMA'
CODE = re.compile(r'^[A-Z0-9]{2,4}$')
MID = re.compile(r'^[0-9]{4,12}$')
ITEM = re.compile(r'^items/(\d{8})-(\d{4})-[a-z0-9-]{3,60}\.json$')
ABS = re.compile(r'^absences/[a-z0-9-]{2,40}\.json$')
NOTE = re.compile(r'^notes/(\d{4,12})\.json$')
SIG = re.compile(r'^sig/[A-Za-z0-9_-]{1,80}\.txt$')
FIXED = {'index.html', 'vercel.json'}
SMALL, LARGE = 1500, 6800
MAX_ITEMS = 12
CATS = {'official', 'reliable', 'rumor', 'analysis'}
ARABIC = re.compile(r'[؀-ۿ]')


def die(msg):
    print('ERROR: ' + msg, file=sys.stderr)
    sys.exit(1)


def now():
    return dt.datetime.now(dt.timezone.utc)


def parse_time(s, date_only_ok=False):
    if not isinstance(s, str):
        return None
    s = s.strip()
    if date_only_ok and re.fullmatch(r'\d{4}-\d{2}-\d{2}', s):
        s += 'T12:00:00+03:00'
    try:
        t = dt.datetime.fromisoformat(s.replace('Z', '+00:00'))
    except ValueError:
        return None
    return t if t.tzinfo else None


def https(u):
    return isinstance(u, str) and re.fullmatch(r'https://[A-Za-z0-9.-]+\.[A-Za-z]{2,}(/\S*)?', u.strip()) is not None


def text(v, lo, hi):
    return isinstance(v, str) and lo <= len(v.strip()) <= hi and '<' not in v


def source_ok(s):
    return isinstance(s, dict) and text(s.get('label'), 2, 80) and https(s.get('url'))


def dump(obj):
    return json.dumps(obj, ensure_ascii=False, separators=(',', ':')) + '\n'


# ---------- validators: return a list of problems ----------
def check_item(path, o):
    p = []
    m = ITEM.match(path)
    if not m:
        p.append('bad item path (items/YYYYMMDD-HHMM-slug.json)')
    if o.get('id') != os.path.basename(path)[:-5]:
        p.append('id must equal the file name without .json')
    if o.get('category') not in CATS:
        p.append('category must be one of ' + ', '.join(sorted(CATS)))
    if not text(o.get('title'), 6, 160) or not ARABIC.search(o.get('title', '')):
        p.append('title must be Arabic, 6-160 chars, no HTML')
    if not text(o.get('summary'), 20, 420) or not ARABIC.search(o.get('summary', '')):
        p.append('summary must be Arabic, 20-420 chars, no HTML')
    if 'body' in o and not text(o.get('body'), 1, 4000):
        p.append('body must be 1-4000 chars')
    if not text(o.get('source'), 2, 60):
        p.append('source must be 2-60 chars')
    if not https(o.get('url')):
        p.append('url must be an https link')
    t = parse_time(o.get('date'), True)
    if not t:
        p.append('date must be ISO 8601 with offset, or YYYY-MM-DD')
    elif t > now() + dt.timedelta(hours=1):
        p.append('date is in the future')
    extra = set(o) - {'id', 'category', 'title', 'summary', 'body', 'source', 'url', 'date'}
    if extra:
        p.append('unknown fields: ' + ', '.join(sorted(extra)))
    return p


def check_absence(o):
    p = []
    if not text(o.get('name'), 2, 40):
        p.append('name 2-40 chars')
    if o.get('kind') not in ('injured', 'suspended'):
        p.append('kind must be injured or suspended')
    if not text(o.get('status'), 2, 90):
        p.append('status 2-90 chars')
    if 'detail' in o and not text(o.get('detail'), 1, 220):
        p.append('detail 1-220 chars')
    if not source_ok(o.get('source')):
        p.append('source {label, https url} required')
    if o.get('kind') == 'suspended':
        b = o.get('banFixtures')
        if not isinstance(b, list) or not b or not all(isinstance(x, str) and MID.match(x) for x in b):
            p.append('suspended needs banFixtures: list of match ids (digits, no prefix)')
    extra = set(o) - {'name', 'kind', 'status', 'detail', 'source', 'banFixtures'}
    if extra:
        p.append('unknown fields: ' + ', '.join(sorted(extra)))
    return p


def check_note(path, o):
    p = []
    m = NOTE.match(path)
    if not m or o.get('match') != m.group(1):
        p.append('notes/<matchId>.json must contain the same "match" id')
    if 'round' in o and not text(o.get('round'), 2, 30):
        p.append('round 2-30 chars')
    if 'venue' in o and not text(o.get('venue'), 2, 60):
        p.append('venue 2-60 chars')
    if 'opponentAbsences' in o:
        oa = o.get('opponentAbsences')
        if not isinstance(oa, list) or not all(text(x, 2, 120) for x in oa) or len(oa) > 10:
            p.append('opponentAbsences: up to 10 strings, 2-120 chars')
        if not source_ok(o.get('source')):
            p.append('opponentAbsences need a source {label, https url}')
    extra = set(o) - {'match', 'round', 'venue', 'opponentAbsences', 'source'}
    if extra:
        p.append('unknown fields: ' + ', '.join(sorted(extra)))
    return p


def check_matches(o):
    p = []
    if o.get('schema') != 'rm360-matches/1' or not parse_time(o.get('updatedAt')):
        p.append('schema rm360-matches/1 and updatedAt required')
    ms = o.get('matches')
    if not isinstance(ms, list) or not 1 <= len(ms) <= 90:
        return p + ['matches must be a list of 1-90']
    seen = set()
    for m in ms:
        tag = str(m.get('id'))
        if not (isinstance(m.get('id'), str) and MID.match(m['id'])) or m['id'] in seen:
            p.append(tag + ': bad or duplicate id')
        seen.add(m.get('id'))
        if m.get('c') not in ('liga', 'ucl'):
            p.append(tag + ': c must be liga or ucl')
        t = parse_time(m.get('d'))
        if not t:
            p.append(tag + ': d must be ISO time')
        if not (CODE.match(str(m.get('h'))) and CODE.match(str(m.get('a')))) or RM not in (m.get('h'), m.get('a')):
            p.append(tag + ': h/a must be codes and include RMA')
        played = 'hs' in m or 'as' in m
        if played:
            if not all(isinstance(m.get(k), int) and 0 <= m[k] <= 20 for k in ('hs', 'as')):
                p.append(tag + ': hs/as must both be integers')
            elif t and t > now():
                p.append(tag + ': a final score cannot be in the future')
            g = m.get('goals')
            if g is not None:
                if not (isinstance(g, dict) and len(g.get('home', [])) == m.get('hs') and len(g.get('away', [])) == m.get('as')):
                    p.append(tag + ': goals must list one minute per goal')
        elif 'goals' in m:
            p.append(tag + ': goals only for played matches')
        if not isinstance(m.get('tc'), bool):
            p.append(tag + ': tc must be true or false')
    return p


def check_rows(rows, kind):
    p = []
    lo, hi = (18, 22) if kind == 'liga' else (30, 40)
    if not isinstance(rows, list) or not lo <= len(rows) <= hi:
        return [kind + ': wrong number of rows']
    sw = sl = sd = sgf = sga = 0
    seen = set()
    for i, r in enumerate(rows):
        if r.get('r') != i + 1 or not CODE.match(str(r.get('t'))) or r.get('t') in seen:
            p.append(kind + ' row %d: rank/team problem' % (i + 1))
        seen.add(r.get('t'))
        if r.get('w', 0) + r.get('d', 0) + r.get('l', 0) != r.get('p') or r.get('pts', 0) > 3 * r.get('w', 0) + r.get('d', 0):
            p.append(kind + ' row %d: p/w/d/l/pts inconsistent' % (i + 1))
        sw += r.get('w', 0); sl += r.get('l', 0); sd += r.get('d', 0)
        if kind == 'liga':
            sgf += r.get('gf', 0); sga += r.get('ga', 0)
    if sw != sl or sd % 2:
        p.append(kind + ': league-wide wins/losses/draws do not balance')
    if kind == 'liga' and sgf != sga:
        p.append('liga: goals for and against do not balance')
    return p


def check_tables(o):
    if o.get('schema') != 'rm360-tables/1' or not parse_time(o.get('updatedAt')):
        return ['schema rm360-tables/1 and updatedAt required']
    return check_rows(o.get('liga'), 'liga') + (check_rows(o.get('ucl'), 'ucl') if 'ucl' in o else [])


def check_goals_state(o):
    t, c = o.get('teams'), o.get('counted')
    if not isinstance(t, dict) or not 18 <= len(t) <= 22:
        return ['teams must map 18-22 club codes to [P, GF, GA]']
    for k, v in t.items():
        if not CODE.match(k) or not (isinstance(v, list) and len(v) == 3 and all(isinstance(x, int) and x >= 0 for x in v)):
            return ['bad goals entry for ' + str(k)]
    if sum(v[1] for v in t.values()) != sum(v[2] for v in t.values()) or sum(v[0] for v in t.values()) % 2:
        return ['goals state does not balance']
    if not isinstance(c, list) or not all(isinstance(x, str) and MID.match(x) for x in c):
        return ['counted must be a list of match ids']
    return []


def check_file(path, data):
    size = len(data)
    if path in FIXED or SIG.match(path):
        return [] if size <= SMALL else ['too large']
    try:
        o = json.loads(data.decode('utf-8'))
    except Exception as e:
        return ['not valid UTF-8 JSON: %s' % e]
    if not isinstance(o, dict):
        return ['top level must be an object']
    if path.startswith('items/'):
        p = check_item(path, o); limit = SMALL
    elif path.startswith('absences/'):
        p = ([] if ABS.match(path) else ['bad absences path']) + check_absence(o); limit = SMALL
    elif path.startswith('notes/'):
        p = check_note(path, o); limit = SMALL
    elif path == 'matches.json':
        p = check_matches(o); limit = LARGE
    elif path == 'tables.json':
        p = check_tables(o); limit = LARGE
    elif path == 'state/goals.json':
        p = check_goals_state(o); limit = SMALL
    elif path == 'index.json':
        p = [] if o.get('schema') == 'rm360-feed/1' else ['bad index schema']; limit = LARGE
    else:
        return ['unexpected path']
    if size > limit:
        p.append('file is %d bytes; limit is %d' % (size, limit))
    return p


# ---------- builders ----------
def tc_rule(comp, start, ref):
    if comp == 'ucl':
        return True
    days = (start - ref).total_seconds() / 86400
    if days <= 14:
        return True
    return days <= 35 and not (start.astimezone(dt.timezone.utc).strftime('%H:%M') == '19:00')


def cmd_matches(args):
    files, updated = [], None
    i = 0
    while i < len(args):
        if args[i] == '--updated':
            updated = args[i + 1]; i += 2
        else:
            files.append(args[i]); i += 1
    if len(files) < 2 or not parse_time(updated):
        die('usage: matches LIGA.txt UCL.txt [GOALS.txt] --updated ISO')
    goals = {}
    if len(files) > 2:
        for line in open(files[2], encoding='utf-8'):
            f = line.split()
            if not f:
                continue
            if len(f) != 5 or f[1] != 'home' or f[3] != 'away':
                die('bad goals line: ' + line.strip())
            conv = lambda s: [] if s == '-' else [int(x) for x in s.split(',')]
            goals[f[0].split(':')[-1]] = {'home': conv(f[2]), 'away': conv(f[4])}
    ref = now()
    out = []
    for comp, fname in (('liga', files[0]), ('ucl', files[1])):
        for r in read_rm(fname):
            if r['status'] in DROP:
                continue
            m = {'id': r['id'], 'c': comp, 'd': r['t'].astimezone(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
                 'h': r['h'], 'a': r['a']}
            if r['status'] in FINAL:
                m['hs'], m['as'] = r['hs'], r['as']
                if r['id'] in goals:
                    m['goals'] = goals[r['id']]
                m['tc'] = True
            else:
                m['tc'] = False if r['status'] == 'postponed' else tc_rule(comp, r['t'], ref)
            out.append(m)
    out.sort(key=lambda m: m['d'])
    doc = {'schema': 'rm360-matches/1', 'updatedAt': updated, 'matches': out}
    probs = check_matches(doc)
    if probs:
        die('; '.join(probs))
    sys.stdout.write(dump(doc))


def read_rows(fname):
    rows = []
    if fname == '-':
        return rows
    for line in open(fname, encoding='utf-8'):
        f = line.split()
        if not f:
            continue
        if len(f) != 6:
            die('bad standings line (RANK CODE W D L PTS): ' + line.strip())
        try:
            r, code, w, d, l, pts = int(f[0]), f[1], int(f[2]), int(f[3]), int(f[4]), int(f[5])
        except ValueError:
            die('bad standings line (numbers expected): ' + line.strip())
        rows.append({'r': r, 't': code, 'w': w, 'd': d, 'l': l, 'pts': pts})
    rows.sort(key=lambda x: x['r'])
    return rows


def read_results(fname, what):
    out = []
    for line in open(fname, encoding='utf-8'):
        f = line.split()
        if not f:
            continue
        if len(f) != 5:
            die('bad %s line (ID HOME AWAY HS AS): %s' % (what, line.strip()))
        try:
            out.append((f[0].split(':')[-1], f[1], f[2], int(f[3]), int(f[4])))
        except ValueError:
            die('bad %s line (scores must be numbers): %s' % (what, line.strip()))
    return out


def games(rows, what):
    total = sum(r['w'] + r['d'] + r['l'] for r in rows)
    if total % 2:
        die(what + ' standings are inconsistent (odd number of team games)')
    return total // 2


def ksa_day():
    return now().astimezone(KSA).strftime('%Y%m%d')


def plain_rows(rows):
    return [{'r': r['r'], 't': r['t'], 'p': r['w'] + r['d'] + r['l'], 'w': r['w'], 'd': r['d'], 'l': r['l'], 'pts': r['pts']} for r in rows]


def cmd_tables(args):
    pos, opts, i = [], {}, 0
    while i < len(args):
        if args[i] in ('--updated', '--state-out', '--fix'):
            opts[args[i]] = args[i + 1]; i += 2
        elif args[i] == '--no-goals':
            opts['--no-goals'] = True; i += 1
        else:
            pos.append(args[i]); i += 1
    if len(pos) != 4 or not parse_time(opts.get('--updated')) or ('--no-goals' not in opts and not opts.get('--state-out')):
        die('usage: tables LIGA_STANDINGS.txt UCL_STANDINGS.txt GOALS_STATE.json WINDOW.txt --updated ISO --state-out PATH [--fix FIX.txt] [--no-goals]')
    updated = opts['--updated']
    liga, ucl = read_rows(pos[0]), read_rows(pos[1])

    def make_doc(liga_rows):
        d = {'schema': 'rm360-tables/1', 'updatedAt': updated, 'liga': liga_rows}
        if ucl:
            d['ucl'] = plain_rows(ucl)
        return d

    if '--no-goals' in opts:
        doc = make_doc(plain_rows(liga))
        probs = check_tables(doc)
        if probs:
            die('; '.join(probs))
        sys.stdout.write(dump(doc))
        return
    state = json.load(open(pos[2], encoding='utf-8'))
    teams = {k: list(v) for k, v in state.get('teams', {}).items()}
    counted = set(state.get('counted', []))
    codes = [r['t'] for r in liga]
    if set(teams) != set(codes):
        print('NOTE: the goals state has other teams than the standings (new season or renamed club); starting it from zero.',
              file=sys.stderr)
        teams, counted = {c: [0, 0, 0] for c in codes}, set()
    window = read_results(pos[3], 'window')
    for mid, h, a, hs, as_ in window:
        if mid in counted:
            continue
        for team, gf, ga in ((h, hs, as_), (a, as_, hs)):
            if team not in teams:
                die('team %s (window match %s) is not in the La Liga standings' % (team, mid))
            teams[team][0] += 1; teams[team][1] += gf; teams[team][2] += ga
        counted.add(mid)

    def disagree():
        return [r['t'] for r in liga if teams[r['t']][0] != r['w'] + r['d'] + r['l']]

    bad = disagree()
    if bad and opts.get('--fix'):
        fix = {}
        for mid, h, a, hs, as_ in read_results(opts['--fix'], 'fix'):
            fix[mid] = (h, a, hs, as_)
        for code in bad:
            mine = [g for g in fix.values() if code in (g[0], g[1])]
            if mine:
                teams[code] = [len(mine), sum(g[2] if g[0] == code else g[3] for g in mine),
                               sum(g[3] if g[0] == code else g[2] for g in mine)]
        bad = disagree()
    if bad:
        detail = '; '.join('%s: %d games counted, %d in the standings' % (c, teams[c][0], next(r['w'] + r['d'] + r['l'] for r in liga if r['t'] == c)) for c in bad)
        die('DISAGREE ' + ' '.join(bad) + ' -- goals state and standings disagree (' + detail + '). Follow the runbook: skip, --fix, or --no-goals.')
    doc = make_doc([{'r': r['r'], 't': r['t'], 'p': r['w'] + r['d'] + r['l'], 'w': r['w'], 'd': r['d'], 'l': r['l'],
                     'gf': teams[r['t']][1], 'ga': teams[r['t']][2], 'pts': r['pts']} for r in liga])
    probs = check_tables(doc)
    if probs:
        die('; '.join(probs))
    new_state = {'teams': {k: teams[k] for k in sorted(teams)}, 'counted': [w[0] for w in window if w[0] in counted]}
    data = dump(new_state).encode('utf-8')
    probs = check_file('state/goals.json', data)
    if probs:
        die('state: ' + '; '.join(probs))
    os.makedirs(os.path.dirname(opts['--state-out']) or '.', exist_ok=True)
    open(opts['--state-out'], 'wb').write(data)
    sys.stdout.write(dump(doc))


def sha1(data):
    return hashlib.sha1(data).hexdigest()


FINAL = ('final', 'closed', 'ended', 'complete', 'completed')
DROP = ('cancelled', 'canceled', 'abandoned')


def read_rm(fname):
    out = []
    if fname == '-':
        return out
    for line in open(fname, encoding='utf-8'):
        f = line.split()
        if not f:
            continue
        if len(f) != 7:
            die('bad match line (ID STATUS START HOME AWAY HS AS): ' + line.strip())
        t = parse_time(f[2])
        if not t:
            die('bad start time: ' + f[2])
        m = {'id': f[0].split(':')[-1], 'status': f[1].lower(), 't': t, 'h': f[3], 'a': f[4]}
        if m['status'] in FINAL:
            try:
                m['hs'], m['as'] = int(f[5]), int(f[6])
            except ValueError:
                die('a finished match needs both scores: ' + line.strip())
        out.append(m)
    return out


def latest_and_next(liga_file, ucl_file):
    ms = [m for m in read_rm(liga_file) + read_rm(ucl_file) if m['status'] not in DROP]
    ms.sort(key=lambda m: m['t'])
    done = [m for m in ms if m['status'] in FINAL]
    todo = [m for m in ms if m['status'] not in FINAL]
    return (done[-1] if done else None), todo


def load_current(path):
    current = {}
    for f in json.load(open(path, encoding='utf-8')):
        if not isinstance(f, dict) or not f.get('file') or not re.fullmatch(r'[0-9a-f]{40}', f.get('sha', '')):
            die('CURRENT.json entries need "file" and a 40-hex "sha"')
        current[f['file']] = f['sha']
    return current


def cmd_flatten(args):
    if len(args) != 1:
        die('usage: flatten TREE.json > current.json')
    tree = json.load(open(args[0], encoding='utf-8'))
    if isinstance(tree, dict):
        tree = tree.get('result', tree.get('files'))
    if not isinstance(tree, list):
        die('TREE.json must be the list_deployment_files result')
    out = []

    def walk(nodes, prefix):
        for n in nodes:
            if not isinstance(n, dict) or not n.get('name'):
                die('unexpected node in the tree')
            if n.get('type') == 'directory':
                walk(n.get('children') or [], prefix + n['name'] + '/')
            elif n.get('type') == 'file':
                out.append({'file': prefix + n['name'], 'sha': n.get('uid', '')})

    walk(tree, '')
    if out and all(f['file'].startswith('src/') for f in out):
        for f in out:
            f['file'] = f['file'][4:]
    for f in out:
        if not re.fullmatch(r'[0-9a-f]{40}', f['sha']):
            die('file %s has no 40-hex uid' % f['file'])
    for fx in FIXED:
        if fx not in {f['file'] for f in out}:
            die('the tree has no %s; is this the feed deployment?' % fx)
    print(json.dumps(sorted(out, key=lambda f: f['file']), separators=(',', ':')))


def cmd_unb64(args):
    if len(args) != 3:
        die('usage: unb64 B64.txt SHA OUT')
    raw = re.sub(r'\s+', '', open(args[0], encoding='ascii').read())
    try:
        data = base64.b64decode(raw, validate=True)
    except Exception:
        die('not valid base64: copy the "data" value again, exactly')
    if sha1(data) != args[1]:
        die('sha1 mismatch: the base64 was copied incorrectly or truncated; copy it again exactly')
    os.makedirs(os.path.dirname(args[2]) or '.', exist_ok=True)
    open(args[2], 'wb').write(data)
    print('ok %d bytes -> %s' % (len(data), args[2]))


def cmd_sigcheck(args):
    if len(args) != 3:
        die('usage: sigcheck CURRENT.json LIGA_STANDINGS.txt UCL_STANDINGS.txt')
    sigs = [k[4:-4] for k in load_current(args[0]) if SIG.match(k)]
    old = sigs[0] if sigs else 'none'
    core = '%s_L%d_U%d' % (ksa_day(), games(read_rows(args[1]), 'La Liga'), games(read_rows(args[2]), 'UCL'))
    print('%s (live marker: %s; now: %s)' % ('SAME' if old.startswith(core + '_R') else 'CHANGED', old, core))


def describe(m):
    when = m['t'].astimezone(KSA).strftime('%Y-%m-%d %H:%M KSA')
    score = ' %d-%d ' % (m['hs'], m['as']) if 'hs' in m else ' v '
    return '%s %s %s%s%s [%s]' % (m['id'], when, m['h'], score, m['a'], m['status'])


def cmd_rminfo(args):
    if len(args) != 2:
        die('usage: rminfo LIGA.txt UCL.txt')
    last, todo = latest_and_next(args[0], args[1])
    print('LATEST FINISHED: ' + (describe(last) if last else 'none'))
    for m in todo[:3]:
        print('NEXT: ' + describe(m))


def cmd_sig(args):
    if len(args) != 5:
        die('usage: sig LIGA_STANDINGS.txt UCL_STANDINGS.txt LIGA.txt UCL.txt WORKDIR')
    last, _ = latest_and_next(args[2], args[3])
    name = '%s_L%d_U%d_R%s' % (ksa_day(), games(read_rows(args[0]), 'La Liga'), games(read_rows(args[1]), 'UCL'),
                              '%s-%d-%d' % (last['id'], last['hs'], last['as']) if last else '0-0-0')
    path = os.path.join(args[4], 'sig', name + '.txt')
    os.makedirs(os.path.dirname(path), exist_ok=True)
    for old in os.listdir(os.path.dirname(path)):
        os.remove(os.path.join(os.path.dirname(path), old))
    open(path, 'w', encoding='utf-8').write('ok\n')
    print('wrote ' + path)


def cmd_plan(args):
    if len(args) < 4:
        die('usage: plan CURRENT.json WORKDIR --updated ISO [--remove PATH ...]')
    current_path, work = args[0], args[1].rstrip('/')
    updated, removes, i = None, [], 2
    while i < len(args):
        if args[i] == '--updated':
            updated = args[i + 1]; i += 2
        elif args[i] == '--remove':
            i += 1
            while i < len(args) and not args[i].startswith('--'):
                removes.append(args[i]); i += 1
        else:
            die('unknown argument ' + args[i])
    if not parse_time(updated):
        die('--updated must be an ISO time with offset')
    current = load_current(current_path)
    for fx in FIXED:
        if fx not in current:
            die('the live deployment must contain ' + fx)
    local = {}
    for root, _, names in os.walk(work):
        for n in names:
            full = os.path.join(root, n)
            rel = os.path.relpath(full, work).replace(os.sep, '/')
            if rel == 'index.json':
                continue
            local[rel] = open(full, 'rb').read()
    for rel in local:
        if rel in FIXED:
            die('do not change ' + rel)
    final = {k: v for k, v in current.items() if k not in removes and k not in ('index.json', 'news.json')}
    if any(SIG.match(r) for r in local):
        final = {k: v for k, v in final.items() if not SIG.match(k)}
    problems = []
    for rel, data in sorted(local.items()):
        pr = check_file(rel, data)
        if pr:
            problems.append(rel + ': ' + '; '.join(pr))
        final[rel] = sha1(data)
    if problems:
        die('fix these files before deploying:\n  ' + '\n  '.join(problems))
    items = sorted([k for k in final if ITEM.match(k)], reverse=True)
    for old in items[MAX_ITEMS:]:
        del final[old]
    items = items[:MAX_ITEMS]
    cutoff = (now() - dt.timedelta(days=10)).astimezone(KSA).strftime('%Y%m%d')
    items_kept = [k for k in items if ITEM.match(k).group(1) >= cutoff] or items[:3]
    for old in set(items) - set(items_kept):
        del final[old]
    index = {'schema': 'rm360-feed/1', 'updatedAt': updated, 'news': items_kept,
             'absences': sorted(k for k in final if ABS.match(k)),
             'notes': sorted(k for k in final if NOTE.match(k))}
    if 'matches.json' in final:
        index['matches'] = 'matches.json'
    if 'tables.json' in final:
        index['tables'] = 'tables.json'
    idx_data = dump(index).encode('utf-8')
    pr = check_file('index.json', idx_data)
    if pr:
        die('index.json: ' + '; '.join(pr))
    open(os.path.join(work, 'index.json'), 'wb').write(idx_data)
    final['index.json'] = sha1(idx_data)
    changed = [rel for rel in sorted(local) if rel in final and current.get(rel) != final[rel]]
    print('NEW OR CHANGED: ' + (', '.join(changed) if changed else 'nothing (index.json only)'))
    print('UPLOAD THESE FILES (python3 -I feedtool.py b64 %s/<path>, then upload_file):' % work)
    for rel in changed + ['index.json']:
        data = idx_data if rel == 'index.json' else local[rel]
        print('  %-48s size=%-5d sha=%s' % (rel, len(data), sha1(data)))
    gone = sorted(set(current) - set(final))
    print('REMOVED FROM THE FEED: ' + (', '.join(gone) if gone else 'nothing'))
    print('FILES ARRAY FOR create_deployment (target production):')
    print(json.dumps([{'file': k, 'sha': final[k]} for k in sorted(final)], separators=(',', ':')))


def cmd_b64(args):
    data = open(args[0], 'rb').read()
    print('size=%d sha=%s' % (len(data), sha1(data)))
    print(base64.b64encode(data).decode('ascii'))


if __name__ == '__main__':
    if len(sys.argv) < 2:
        die(__doc__)
    cmd = sys.argv[1]
    fn = {'flatten': cmd_flatten, 'unb64': cmd_unb64, 'sigcheck': cmd_sigcheck, 'rminfo': cmd_rminfo, 'matches': cmd_matches,
          'tables': cmd_tables, 'sig': cmd_sig, 'plan': cmd_plan, 'b64': cmd_b64}.get(cmd)
    if not fn:
        die(__doc__)
    fn(sys.argv[2:])
