import { calendarKey, categories, indexArchive, monthLengths, months, saudiDay, sourceLink, summarize, upcomingFixture } from './history-data.mjs';

const byId = id => document.getElementById(id);
const month = byId('month');
const day = byId('day');
const rows = byId('rows');
const stats = byId('stats');
const nextButton = byId('next');
const dateURL = new URL(location.href);
const labels = { official: 'الرسمية', friendly: 'الودية', historical: 'المسابقات التاريخية الأخرى' };

function element(tag, text, className) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function link(label, url) {
  const node = element('a', label);
  node.href = url;
  node.target = '_blank';
  node.rel = 'noopener noreferrer';
  return node;
}

async function readJSON(path) {
  const response = await fetch(`./feed/${path}`);
  if (!response.ok) throw new Error(`${path} ${response.status}`);
  return response.json();
}

function dateLabel(key) {
  const [monthNumber, dayNumber] = key.split('-').map(Number);
  return `${dayNumber} ${months[monthNumber - 1]}`;
}

function matchCard(archive, match) {
  const [date, opponent, , scored, conceded, competition, references, details] = match;
  const card = element('article', undefined, 'archive-match');
  card.dataset.date = date;
  const meta = element('p', undefined, 'archive-match-meta');
  const time = element('time', `${dateLabel(date.slice(5))} ${date.slice(0, 4)}`);
  time.dateTime = date;
  meta.append(time, ' · ', archive.competitions[competition][1]);

  const title = element('h3');
  const score = element('bdi', `${scored}–${conceded}`);
  score.dir = 'ltr';
  score.dataset.result = scored > conceded ? 'win' : scored === conceded ? 'draw' : 'loss';
  const rival = element('bdi', archive.opponents[opponent] || opponent);
  title.append('ريال مدريد ', score, ' ', rival);
  card.append(meta, title);
  if (details?.shootout) {
    const shootout = element('p', 'ركلات الترجيح ', 'archive-match-note');
    const penaltyScore = element('bdi', details.shootout.join('–'));
    penaltyScore.dir = 'ltr';
    shootout.append(penaltyScore);
    card.append(shootout);
  }
  if (details?.note) card.append(element('p', details.note, 'archive-match-note'));

  const sources = element('p', undefined, 'archive-sources');
  for (const reference of references) {
    const source = sourceLink(archive, reference);
    sources.append(link(source.label, source.url));
  }
  card.append(sources);
  return card;
}

function updateDays(preferredDay) {
  const length = monthLengths[Number(month.value) - 1];
  const selected = Math.min(preferredDay, length);
  day.replaceChildren(...Array.from({ length }, (_, index) => new Option(index + 1, index + 1)));
  day.value = selected;
}

async function initialize() {
  const fixtureSnapshots = Promise.all([
    readJSON('matches.json').catch(() => ({})),
    readJSON('history-fixtures.json').catch(() => ({})),
  ]);
  const archive = await readJSON('history.json');
  if (archive.schema !== 'rm360-history/2') throw new Error('Unsupported archive version');
  const index = indexArchive(archive);
  const counts = Object.fromEntries(categories.map(category => [category, 0]));
  for (const records of index.values()) {
    for (const category of categories) counts[category] += records[category].length;
  }
  byId('coverage-counts').textContent = `دُقّقت التغطية حتى ${dateLabel(archive.checkedThrough.slice(5))} ${archive.checkedThrough.slice(0, 4)}. ` +
    `${counts.official.toLocaleString('en')} مباراة رسمية، ${counts.friendly.toLocaleString('en')} ودية، و${counts.historical.toLocaleString('en')} في مسابقات تاريخية أخرى.`;
  byId('coverage-notes').replaceChildren(...archive.coverage.map(note => element('li', note)));
  byId('coverage-links').replaceChildren(...archive.credits.map(([label, url]) => link(label, url)));
  byId('coverage').hidden = false;

  let selectedCategory = dateURL.searchParams.get('type');
  if (!categories.includes(selectedCategory)) selectedCategory = 'official';
  byId('category').querySelector(`[value="${selectedCategory}"]`).checked = true;
  let manuallySelected = index.has(dateURL.searchParams.get('day'));
  const todaysKey = saudiDay(Date.now()).slice(5);
  let fixture = null;

  function render() {
    const key = calendarKey(month.value, day.value);
    const matches = index.get(key)[selectedCategory];
    const totals = summarize(matches);
    byId('selected-date').textContent = `${dateLabel(key)} · ${labels[selectedCategory]}`;
    const values = [
      ['played', 'المباريات', totals.played], ['wins', 'فوز', totals.wins],
      ['draws', 'تعادل', totals.draws], ['losses', 'خسارة', totals.losses],
      ['scored', 'أهداف له', totals.scored], ['conceded', 'أهداف عليه', totals.conceded],
      ['winPercentage', 'نسبة الفوز', totals.winPercentage === null ? '—' : `${totals.winPercentage.toFixed(1)}%`],
    ];
    stats.replaceChildren(...values.map(([id, label, value]) => {
      const metric = element('div');
      metric.dataset.metric = id;
      metric.append(element('dt', label), element('dd', value));
      return metric;
    }));
    rows.replaceChildren(...(matches.length ? matches.map(match => matchCard(archive, match)) : [
      element('p', 'لا توجد مباريات موثقة ضمن هذا النوع في التاريخ المختار.'),
    ]));
    if (manuallySelected || selectedCategory !== 'official') {
      dateURL.searchParams.set('day', key);
      if (selectedCategory === 'official') dateURL.searchParams.delete('type');
      else dateURL.searchParams.set('type', selectedCategory);
      history.replaceState(null, '', dateURL);
    }
  }

  function selectDate(key) {
    const [monthNumber, dayNumber] = key.split('-').map(Number);
    month.value = monthNumber;
    updateDays(dayNumber);
    render();
  }

  month.replaceChildren(...months.map((name, index) => new Option(name, index + 1)));
  month.addEventListener('change', () => {
    manuallySelected = true;
    updateDays(Number(day.value));
    render();
  });
  day.addEventListener('change', () => {
    manuallySelected = true;
    render();
  });
  byId('category').addEventListener('change', event => {
    selectedCategory = event.target.value;
    manuallySelected = true;
    render();
  });
  byId('today').addEventListener('click', () => {
    manuallySelected = true;
    selectDate(saudiDay(Date.now()).slice(5));
  });
  nextButton.addEventListener('click', () => {
    manuallySelected = true;
    selectDate(fixture.day.slice(5));
  });
  selectDate(manuallySelected ? dateURL.searchParams.get('day') : todaysKey);
  rows.setAttribute('aria-busy', 'false');
  byId('calendar').disabled = false;
  byId('category').disabled = false;

  fixture = upcomingFixture(...await fixtureSnapshots);
  const fixtureText = byId('fixture');
  if (!fixture) {
    fixtureText.textContent = 'لا يتوفر موعد مؤكد للمباراة المقبلة في الجدول الحالي.';
    return;
  }
  const opponent = fixture.h === 'RMA' ? fixture.a : fixture.h;
  const opponentName = window.RM360_TEAMS?.[opponent]?.[0] || fixture.opponent || opponent;
  const kickoff = new Intl.DateTimeFormat('en-GB', { timeZone: 'Asia/Riyadh', timeStyle: 'short' }).format(fixture.timestamp);
  fixtureText.append(`المباراة المقبلة أمام ${opponentName} · ${dateLabel(fixture.day.slice(5))} · ${kickoff} بتوقيت السعودية`);
  if (fixture.source) fixtureText.append(' · ', link('الموعد الرسمي', fixture.source));
  nextButton.disabled = false;
  if (!manuallySelected) selectDate(fixture.day.slice(5));
}

initialize().catch(error => {
  console.error('RM360 history', error);
  rows.setAttribute('aria-busy', 'false');
  rows.textContent = 'تعذر تحميل أرشيف المباريات. أعد تحميل الصفحة للمحاولة مرة أخرى.';
});
