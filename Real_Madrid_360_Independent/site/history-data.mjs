export const months = [
  'يناير', 'فبراير', 'مارس', 'أبريل', 'مايو', 'يونيو',
  'يوليو', 'أغسطس', 'سبتمبر', 'أكتوبر', 'نوفمبر', 'ديسمبر',
];

export const monthLengths = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
export const categories = ['official', 'friendly', 'historical'];

const pad = number => String(number).padStart(2, '0');

export function calendarKey(month, day) {
  return `${pad(month)}-${pad(day)}`;
}

export function indexArchive(archive) {
  const index = new Map();
  for (const [month, length] of monthLengths.entries()) {
    for (let day = 1; day <= length; day++) {
      index.set(calendarKey(month + 1, day), { official: [], friendly: [], historical: [] });
    }
  }
  for (const match of archive.matches) {
    const category = archive.competitions[match[5]][0];
    index.get(match[0].slice(5))[category].push(match);
  }
  for (const day of index.values()) {
    for (const matches of Object.values(day)) matches.sort((a, b) => b[0].localeCompare(a[0]));
  }
  return index;
}

export function summarize(matches) {
  const totals = { played: matches.length, wins: 0, draws: 0, losses: 0, scored: 0, conceded: 0 };
  for (const [, , , scored, conceded] of matches) {
    totals.scored += scored;
    totals.conceded += conceded;
    if (scored > conceded) totals.wins++;
    else if (scored < conceded) totals.losses++;
    else totals.draws++;
  }
  return { ...totals, winPercentage: totals.played ? 100 * totals.wins / totals.played : null };
}

const saudiDate = new Intl.DateTimeFormat('en-CA', {
  timeZone: 'Asia/Riyadh', year: 'numeric', month: '2-digit', day: '2-digit',
});

export function saudiDay(timestamp) {
  const parts = Object.fromEntries(saudiDate.formatToParts(timestamp).map(part => [part.type, part.value]));
  return `${parts.year}-${parts.month}-${parts.day}`;
}

export function upcomingFixture(platform, club, now = Date.now()) {
  const fixtures = new Map();
  // The source is the authority for a fixture when its snapshot is the newer of the two.
  const snapshotTime = snapshot => Date.parse(snapshot.updatedAt) || 0;
  const snapshots = [platform, club].sort((a, b) => snapshotTime(a) - snapshotTime(b));
  for (const snapshot of snapshots) {
    for (const match of snapshot.matches || []) {
      if ((match.h === 'RMA') === (match.a === 'RMA')) continue;
      const timestamp = Date.parse(match.d);
      if (!Number.isFinite(timestamp)) continue;
      const prefix = `${match.c}/${match.h}/${match.a}/`;
      const day = saudiDay(timestamp);
      const key = prefix + day;
      const played = Number.isInteger(match.hs) && Number.isInteger(match.as);
      // A league opponent can be hosted only once per season, even after a reschedule.
      const season = Number(day.slice(0, 4)) - (Number(day.slice(5, 7)) < 7 ? 1 : 0);
      const identity = match.c === 'liga' ? prefix + season : key;
      const known = fixtures.get(identity);
      if (played || !known?.played && match.tc !== false) {
        fixtures.set(identity, { ...known, ...match, timestamp, day, played });
      }
    }
  }
  return [...fixtures.values()]
    .filter(match => !match.played && match.timestamp > now)
    .sort((a, b) => a.timestamp - b.timestamp)[0] ?? null;
}

export function sourceLink(archive, [key, locator]) {
  const [label, template] = archive.sources[key];
  const linkTarget = key === 'leyenda' && typeof locator === 'number' ? archive.historicalSnapshots[locator] : locator;
  const url = template.replace('{id}', () => String(linkTarget ?? ''));
  if (new URL(url).protocol !== 'https:') throw new Error(`Invalid history source ${key}`);
  return { label, url };
}
