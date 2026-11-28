import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { categories, indexArchive, saudiDay, sourceLink, summarize, upcomingFixture } from '../site/history-data.mjs';

const directory = process.argv[2] || 'site';
const read = name => JSON.parse(readFileSync(`${directory}/feed/${name}.json`, 'utf8'));
const archive = read('history');
const platform = read('matches');
const club = read('history-fixtures');
assert.equal(archive.schema, 'rm360-history/2');
assert.equal(club.schema, 'rm360-history-fixtures/1');

const seen = new Set();
const officialDates = new Set();
for (const row of archive.matches) {
  const [day, opponent, side, scored, conceded, tournament, sources, details] = row;
  assert.match(day, /^\d{4}-\d{2}-\d{2}$/);
  assert.equal(new Date(day).toISOString().slice(0, 10), day);
  assert(day >= '1902-03-06' && day <= archive.checkedThrough);
  assert(opponent && opponent !== 'Real Madrid');
  assert(['H', 'A'].includes(side));
  assert([scored, conceded].every(goal => Number.isInteger(goal) && goal >= 0));
  const category = archive.competitions[tournament][0];
  assert(categories.includes(category));
  const key = `${day}|${category}|${opponent.toLocaleLowerCase('es')}`;
  assert(!seen.has(key), `Duplicate result: ${key}`);
  seen.add(key);
  if (category === 'official') {
    assert(!officialDates.has(day), `Multiple official first-team results on ${day}`);
    officialDates.add(day);
  }
  assert(sources.length > 0);
  for (const ref of sources) assert.match(sourceLink(archive, ref).url, /^https:\/\/.+/);
  if (details?.shootout) {
    assert.equal(details.shootout.length, 2);
    assert(details.shootout.every(goal => Number.isInteger(goal) && goal >= 0));
    assert.notEqual(...details.shootout);
  }
}

const index = indexArchive(archive);
assert.equal(index.size, 366);
assert.equal([...index.values()].reduce((sum, day) => sum + categories.reduce((count, category) => count + day[category].length, 0), 0), archive.matches.length);
assert(index.get('02-29').official.length > 0);
assert(!index.has('02-30'));
assert(!index.has('04-31'));
assert.equal(summarize([]).winPercentage, null);

const november = index.get('11-28').official.filter(row => row[0] < '2026-11-28');
assert.deepEqual(summarize(november), {
  played: 20, wins: 8, draws: 4, losses: 8, scored: 41, conceded: 32, winPercentage: 40,
});
assert(november.some(row => row[0] === '2000-11-28' && row[1] === 'Boca Juniors' && row[5] === 'intercontinental'));
assert(november.some(row => row[0] === '1984-11-28' && row[1] === 'RSC Anderlecht' && row[5] === 'uel'));
assert(november.some(row => row[0] === '1909-11-28' && row[5] === 'regional'));
assert(index.get('05-02').friendly.some(row => row[0] === '1902-05-02'));
assert(index.get('05-13').historical.some(row => row[0] === '1902-05-13' && row[5] === 'coronation'));
assert(index.get('06-26').official.some(row => row[0] === '2025-06-26' && row[1] === 'Red Bull Salzburg'));
assert(!index.get('06-27').official.some(row => row[0] === '2025-06-27' && row[1] === 'Red Bull Salzburg'));
assert(index.get('12-12').official.some(row => row[0] === '2004-12-12' && row[1] === 'Real Sociedad'));
assert(!index.get('01-05').official.some(row => row[0] === '2005-01-05' && row[1] === 'Real Sociedad'));
assert(index.get('11-24').official.some(row => row[0] === '2026-11-24' && row[1] === 'PSV' && row[3] === 5 && row[4] === 1));
const shootout = index.get('01-12').official.find(row => row[0] === '2020-01-12');
assert.deepEqual(shootout[7].shootout, [4, 1]);
assert.equal(summarize([shootout]).draws, 1);
assert.equal(summarize([shootout]).scored, 0);

for (const match of club.matches) {
  assert.match(match.source, /^https:\/\/www\.realmadrid\.com\//);
  assert.equal(match.tc, true);
  assert(Number.isFinite(Date.parse(match.d)));
}
if (archive.checkedThrough === '2026-11-28') {
  const novemberDate = Date.parse('2026-11-28T09:00:00Z');
  const decemberDate = Date.parse('2026-11-29T09:00:00Z');
  assert.equal(upcomingFixture(platform, club, novemberDate).a, 'ALA');
  assert.equal(upcomingFixture({}, club, novemberDate).day, '2026-11-28');
  assert.equal(upcomingFixture(platform, club, decemberDate).day, '2026-12-02');
  assert.equal(upcomingFixture(platform, club, decemberDate).h, 'RSO');
}
assert.equal(saudiDay(Date.parse('2026-11-28T21:15:00Z')), '2026-11-29');
assert.equal(upcomingFixture({}, {}, 0), null);
assert.equal(upcomingFixture({ matches: [{ c: 'liga', h: 'RMA', a: 'BAR', d: '2026-12-22T20:00:00Z', tc: false }] }, {}, 0), null);
assert.equal(upcomingFixture({ matches: [{ c: 'liga', h: 'RMA', a: 'BAR', d: '2026-12-22T20:00:00Z', hs: 1, as: 0 }] }, {}, 0), null);

console.log(`History archive validated: ${seen.size} sourced matches and ${index.size} calendar days.`);
