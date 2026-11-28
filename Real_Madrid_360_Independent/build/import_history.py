"""Compile the historical first-team archive from public match records.

This is an explicit editorial command. Production builds use the reviewed snapshot.
"""
import argparse
import csv
import io
import json
import re
import unicodedata
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta
from pathlib import Path
from urllib.parse import parse_qs, quote, urlparse
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

from lxml import html
from history_leyenda import extract as extract_leyenda, same_opponent


ROOT = Path(__file__).resolve().parents[1]
BDF = "https://www.bdfutbol.com/en/"
RSSSF = "https://www.rsssf.org/"
CENTRO = RSSSF + "tabless/span-centrchamp.html"
FRIENDLIES = RSSSF + "tablesm/madrid-friend{}.html"
INTERNATIONAL = RSSSF + "miscellaneous/torre-madrid.html"
CORONATION = RSSSF + "tabless/spancup1902.html"
CLUB = "https://www.realmadrid.com"
CLUB_CALENDAR = CLUB + "/es-ES/futbol/primer-equipo/calendario"
LALIGA = "https://www.laliga.com"
LIGA_RESULTS = LALIGA + "/clubes/real-madrid/resultados"
CURLEY = "https://raw.githubusercontent.com/mrcreel/soccer_data/master/data-raw/"
FOOTBALL_DATA = "https://www.football-data.co.uk/"
WIKI = "https://en.wikipedia.org/wiki/"
WIKI_EARLY = WIKI + quote("1902–03_Madrid_FC_season")
WIKI_EARLY_ES = "https://es.wikipedia.org/wiki/" + quote("Anexo:Temporada_1903-04_del_Real_Madrid_Club_de_Fútbol", safe=":_")
RFEF_CORONATION = "https://rfef.es/es/noticias/la-copa-de-la-coronacion-donde-todo-comenzo"
CLUB_2026_FRIENDLIES = "https://as.com/futbol/primera/pretemporada-de-laliga-ea-sports-todos-los-amistosos-fechas-partidos-y-resultados-de-los-equipos-de-primera-f202607-n/"
CLASSIC_NOVEMBER = "https://www.laligaennumeros.es/2026/11/previa-14-primera.html?m=0"

REGIONAL_EDITIONS = {
    1913: (504, "regional"), 1914: (558, "regional"), 1915: (672, "regional"),
    1916: (673, "regional"), 1917: (572, "regional"), 1918: (564, "regional"),
    1919: (563, "regional"), 1920: (498, "regional"), 1921: (499, "regional"),
    1922: (483, "regional"), 1923: (562, "regional"), 1924: (526, "regional"),
    1925: (530, "regional"), 1926: (556, "regional"), 1927: (525, "regional"),
    1928: (529, "regional"), 1929: (481, "regional"), 1930: (484, "regional"),
    1931: (480, "regional-joint"), 1932: (473, "regional-joint"), 1933: (474, "regional-joint"),
    1934: (478, "regional-joint"), 1935: (477, "regional-joint"), 1939: (479, "regional"),
}
REGIONAL_CUPS = {1580: "centro-cup", 3060: "centro-cup", 475: "castilla-cup", 490: "castellana", 491: "castellana"}

COMPETITIONS = {
    "liga": ("official", "الدوري الإسباني"),
    "copa": ("official", "كأس إسبانيا «كأس الملك»"),
    "ucl": ("official", "كأس أوروبا / دوري أبطال أوروبا"),
    "uel": ("official", "كأس الاتحاد الأوروبي / الدوري الأوروبي"),
    "supercopa": ("official", "كأس السوبر الإسباني"),
    "cup-winners": ("official", "كأس الكؤوس الأوروبية"),
    "league-cup": ("official", "كأس الدوري الإسباني"),
    "club-world-cup": ("official", "كأس العالم للأندية"),
    "uefa-supercup": ("official", "كأس السوبر الأوروبي"),
    "intercontinental": ("official", "كأس إنتركونتيننتال «1960–2004»"),
    "fifa-intercontinental": ("official", "كأس القارات للأندية «فيفا»"),
    "latin": ("official", "الكأس اللاتينية"),
    "ibero": ("official", "كأس إيبيرو أميريكانا"),
    "eva-duarte": ("official", "كأس إيفا دوارتي"),
    "regional": ("official", "بطولة مدريد الإقليمية «كامبيوناتو سنترو»"),
    "regional-joint": ("official", "البطولة الإقليمية المشتركة"),
    "centro-cup": ("official", "كأس اتحاد المنطقة الوسطى"),
    "castilla-cup": ("official", "كأس قشتالة"),
    "castellana": ("official", "كأس رئيس الاتحاد القشتالي"),
    "jose-del-valle": ("official", "كأس خوسيه لويس ديل فايي"),
    "minimalista": ("historical", "الدوري التمهيدي «ليغا مينيماليستا»"),
    "coronation": ("historical", "كأس التتويج «كونكورسو مدريد»"),
    "gran-pena": ("historical", "كأس غران بينيا"),
    "void-regional": ("historical", "مباراة إقليمية أُلغي اعتمادها"),
    "friendly": ("friendly", "مباراة ودية"),
    "friendly-tournament": ("friendly", "بطولة ودية"),
    "bernabeu": ("friendly", "كأس سانتياغو برنابيو"),
    "icc": ("friendly", "كأس الأبطال الدولية الودية"),
    "small-world-cup": ("friendly", "كأس العالم المصغرة الودية"),
    "teresa-herrera": ("friendly", "كأس تيريسا هيريرا"),
    "audi": ("friendly", "كأس أودي الودية"),
    "bandas": ("friendly", "بطولة كونكورسو دي بانداس الودية"),
    "codorniu": ("friendly", "كأس كودورنيو الودية"),
    "arzuaga": ("friendly", "كأس رودريغيز أرثواغا الودية"),
}
BDF_CODES = dict(zip(
    ("1a", "COP", "CHA", "UEF", "SUP", "REC", "CLI", "MUN", "SCE", "INT", "FIF", "LAT", "IBE", "EVA", "MAX"),
    ("liga", "copa", "ucl", "uel", "supercopa", "cup-winners", "league-cup", "club-world-cup",
     "uefa-supercup", "intercontinental", "club-world-cup", "latin", "ibero", "eva-duarte", "minimalista"),
))
LIGA_CODES = {
    "primera-division": "liga", "champions-league": "ucl", "copa-del-rey": "copa",
    "supercopa-de-espana": "supercopa", "supercopa-espana": "supercopa",
}
SOURCES = {
    "bdf": ("BDFutbol", BDF + "p/p.php?id={id}"),
    "bdf-special": ("BDFutbol", BDF + "p/partido.html?{id}"),
    "bdf-regional": ("BDFutbol · الأرشيف الإقليمي", BDF + "c/{id}"),
    "centro": ("RSSSF · بطولات المنطقة الوسطى", CENTRO + "#{id}"),
    "rsssf-international": ("Raúl Torre / RSSSF", INTERNATIONAL),
    "rsssf-friendly": ("Raúl Torre / RSSSF", FRIENDLIES.format("{id}")),
    "rsssf-cup-finals": ("RSSSF · نهائيات كأس إسبانيا", RSSSF + "tabless/spancuphist.html"),
    "rsssf-teresa": ("RSSSF · كأس تيريسا هيريرا", RSSSF + "tablest/teresa-herrera.html#77"),
    "rsssf-coronation": ("RSSSF · كأس التتويج", CORONATION),
    "rfef-coronation": ("الاتحاد الإسباني", RFEF_CORONATION),
    "curley-liga": ("James Curley · سجل الدوري", "https://github.com/mrcreel/soccer_data/blob/master/data-raw/spain.csv"),
    "curley-ucl": ("James Curley · سجل كأس أوروبا", "https://github.com/mrcreel/soccer_data/blob/master/data-raw/champs.csv"),
    "football-data": ("Football-Data.co.uk", FOOTBALL_DATA + "mmz4281/{id}/SP1.csv"),
    "laliga": ("رابطة الدوري الإسباني", LALIGA + "/partido/{id}"),
    "laliga-en-numeros": ("La Liga en números", CLASSIC_NOVEMBER),
    "uefa": ("الاتحاد الأوروبي", "https://www.uefa.com/uefachampionsleague/match/{id}/"),
    "uefa-europa": ("الاتحاد الأوروبي", "https://www.uefa.com/uefaeuropaleague/match/{id}/matchinfo/"),
    "club": ("ريال مدريد", "{id}"),
    "season": ("أرشيف الموسم", WIKI + "{id}"),
    "early": ("أرشيف الموسم التاريخي", WIKI_EARLY),
    "early-es": ("أرشيف الموسم التاريخي", WIKI_EARLY_ES),
    "leyenda": ("Leyenda Blanca · الأرشيف", "{id}"),
    "as-preseason": ("AS · وديات 2026", CLUB_2026_FRIENDLIES),
    "source": ("مرجع المباراة", "{id}"),
}
CREDITS = [
    ("BDFutbol", BDF + "p/e2.html"),
    ("Raúl Torre / RSSSF · المباريات الدولية الودية", FRIENDLIES.format("")),
    ("RSSSF · بطولات المنطقة الوسطى", CENTRO),
    ("Leyenda Blanca · أرشيف المواسم", "https://web.archive.org/web/20190819152048/http://leyendablanca.galeon.com/tempo04.htm"),
    ("ريال مدريد · التقويم الرسمي", CLUB_CALENDAR),
    ("رابطة الدوري الإسباني · النتائج", LIGA_RESULTS),
    ("الاتحاد الأوروبي · أرشيف ريال مدريد", "https://www.uefa.com/uefachampionsleague/history/clubs/50051--real-madrid/"),
    ("James Curley · Soccer Data", "https://github.com/mrcreel/soccer_data"),
    ("Football-Data.co.uk", FOOTBALL_DATA + "spainm.php"),
]
COVERAGE = [
    "يشمل الأرشيف البطولات الإسبانية والأوروبية والعالمية المعروفة، وما توفر من بطولات مدريد الإقليمية. لكل مباراة مدرجة مرجع يتيح مراجعتها.",
    "ما زالت نتائج بعض مباريات بطولة مدريد في 1903–1904 وأدوار من كؤوس قشتالة الإقليمية غير متاحة، ومنها دور المجموعات في كأس خوسيه لويس ديل فايي 1944–1945.",
    "سجل الوديات جزئي. الأرشيف الدولي أغزر من الوديات المحلية القديمة، وبعض المباريات التدريبية المغلقة تفتقر إلى نتائج منشورة.",
    "تظهر كأس التتويج لعام 1902 والدوري التمهيدي لعام 1927 في «مسابقات تاريخية أخرى». تُستبعد المباريات التي لم تُلعب والسجلات التي يتعذر إثبات تاريخها أو نتيجتها.",
]
SCORE = re.compile(r"(\d{1,2})\s*[-:–—]\s*(\d{1,2})")
EARLY_REGIONAL = re.compile(r"^(\d{1,2}-\d{1,2}-\d{4})\s+(.+?)\s+[-–—\x96]\s+(.+?)\s{2,}(.*)$")
TEAM = "Real Madrid"
SPAIN_TZ = ZoneInfo("Europe/Madrid")

ALIASES = {}


def fold(text):
    text = unicodedata.normalize("NFKD", text.casefold())
    return re.sub(r"[^a-z0-9]+", " ", text.encode("ascii", "ignore").decode()).strip()


def register_club(canonical, *names):
    for name in (canonical, *names):
        ALIASES[fold(name)] = canonical


def club_name(name):
    name = re.sub(r"\s+\([A-Z]{2,4}\)$", "", name).strip()
    return ALIASES.get(fold(name), name.title() if name.isupper() else name)


register_club(TEAM, "Madrid", "Madrid FC", "Madrid CF", "Madrid F. C.", "Real Madrid F.C.",
              "Real Madrid CF", "Real Madrid FC", "REAL MADRIC CF", "Madrid-Moderno", "Madrid Moderno", "Madrid-Moderno F. C.")
register_club("Atlético de Madrid", "Atletico Madrid", "Athletic Madrid", "Athletic de Madrid",
              "Athletic Club de Madrid", "Atlético Aviación", "Ath. Aviación", "Atlético-Aviación",
              "Atlético de Madrid (Athletic Club)", "Club Atlético de Madrid", "Athletic Club (Sucursal Madrid)")
register_club("Athletic Club", "Athletic Bilbao", "Athletic de Bilbao", "Athletic Club de Bilbao", "Atletico Bilbao", "Ath Club de Bilbao")
register_club("Espanyol", "Espanyol Barcelona", "RCD Español", "Club Español de Football", "Club Español",
              "Club Espanyol de Football de Barcelona", "Español de Barcelona", "RCD Espanyol", "RCD Espanyol de Barcelona")
register_club("Club Español de Madrid", "Español Madrid", "Español de Madrid", "Español FC", "Club Español FC")
register_club("Barcelona", "FC Barcelona", "CF Barcelona")
register_club("Celta de Vigo", "Celta", "RC Celta", "Real Club Celta de Vigo")
register_club("Deportivo de La Coruña", "Deportivo", "Deportivo La Coruna", "Deportivo de A Coruña", "RC Deportivo")
register_club("Racing de Santander", "Racing Santander", "Real Racing Club de Santander", "R. Racing Club")
register_club("Racing de Madrid", "Racing Madrid", "Racing Club de Madrid", "Racing Madrid CF")
register_club("Gimnástica Española", "Gimnástica", "RS Gimnástica", "S. Gimnástica", "Sociedad Gimnástica Española", "RS Gimnástica Madrid")
register_club("Nacional de Madrid", "CD Nacional", "Nacional Madrid")
register_club("Real Valladolid", "Valladolid", "Valladolid CD")
register_club("Real Zaragoza", "Zaragoza", "Zaragoza CF")
register_club("Alavés", "Deportivo Alavés")
register_club("Sevilla", "Sevilla FC")
register_club("Betis", "Betis Balompié", "Real Betis", "Real Betis Balompié")
register_club("Unión Sporting", "Unión SC", "Unión Sporting Club")
register_club("Internacional de Madrid (1902)", "Internacional FC", "Internacional")
register_club("New Foot-Ball Club", "New FC", "New F. C.", "New Foot-Ball de Madrid")
register_club("AS Roma", "Roma")
register_club("Inter", "Internazionale", "Inter de Milan", "Inter Milan", "FC Internazionale Milano")
register_club("Milan", "AC Milan", "AC Milano")
register_club("PSG", "Paris Saint-Germain", "Paris Saint Germain")
register_club("Bayern München", "Bayern Munich", "Bayern Munchen", "FC Bayern München", "Bayern de Munich")
register_club("Stade de Reims", "Reims", "Stade Reims")
register_club("PSV", "PSV Eindhoven")
register_club("SL Benfica", "Benfica", "SP Benfica")
register_club("Tottenham Hotspur", "Tottenham")
register_club("FC Porto", "Porto", "FC Oporto", "Oporto")
register_club("Rangers", "Rangers FC", "Glasgow Rangers")
register_club("FC Schalke 04", "Schalke 04", "Schalke")
register_club("Red Bull Salzburg", "RB Salzburg", "Salzburg", "FC Salzburg", "Red Bull Salzburgo")
register_club("Fiorentina", "AC Fiorentina")
register_club("Moncloa FC", "Moncloa F. C.")
register_club("Moderno FC", "Moderno F. C.", "Modern FC")
register_club("LASK", "LASK Linz")
register_club("Shakhtar Donetsk", "Shakhtar", "FC Shakhtar Donetsk")
register_club("Elche", "Elche CF")
register_club("Hércules", "Hercules CF", "Hercules Alicante", "Hércules Alicante C.F.")
register_club("Fuenlabrada", "CF Fuenlabrada")
register_club("Royal Antwerp", "Antwerp", "Antwerpen")
register_club("Club América", "América", "America (MEX)")
register_club("LA Galaxy", "L.A. GALAXY", "Los Angeles Galaxy")
register_club("RSC Anderlecht", "Anderlecht")
register_club("VfL Borussia Mönchengladbach", "Borussia M'gladbach", "Borussia Mönchengladbach", "Borussia M.G.")
register_club("Sporting de Gijón", "Sporting Gijon")
register_club("Gimnástico de Tarragona", "Gimnastic", "Nastic", "Gimnàstic de Tarragona")
register_club("Real Unión", "Real Unión de Irún", "Real Unión Club de Irún")
register_club("Real Oviedo", "Oviedo")
register_club("Valencia", "Valencia CF", "Valencia FC")
register_club("Rayo Vallecano", "Rayo")
register_club("Málaga", "Malaga CF")
register_club("Sabadell", "CE Sabadell")
register_club("Talavera de la Reina", "Talavera CF")
register_club("AD Ferroviaria", "Ferroviaria")
register_club("Imperio FC", "Imperio")
register_club("Club Vizcaya", "Bizcaya", "Club Vizcaya de Bilbao")
register_club("Villarreal", "Villarreal CF")
register_club("AEK", "AEK Atenas", "AEK Athens")
register_club("Coalición Matritense", "Combinado Madrileño")
register_club("Millonarios", "CD Millonarios")
register_club("Os Belenenses", "CF Os Belenenses", "Belenenses")
register_club("Peñarol", "CA Peñarol")
register_club("Girona", "Gerona", "Girona CF")
register_club("Vasco da Gama", "CR Vasco de Gama", "CR Vasco Gama", "CR Vasco da Gama")
register_club("Fortuna Düsseldorf", "Fortuna Dusseldorf", "FC Düsseldorf")
register_club("FC Köln", "Köln", "1 FK Köln", "1 FK Colonia", "1. FC Köln")
register_club("Newcastle United", "Newcastle")
register_club("Racing Club de Avellaneda", "Racing Club", "Racing de Avellaneda", "Racing Buenos Aires")
register_club("Boca Juniors", "CA Boca Juniors")
register_club("Sporting CP", "Sporting de Lisboa")
register_club("Vasas", "Vasas SC", "SC Vasas Budapest", "Budapesti Vasas")
register_club("Zürich", "FC Zürich", "FC Zurich")
register_club("Clube Internacional de Foot-Ball", "Internacional Lisboa", "Sp. Internacional")
register_club("Sampdoria", "Sampdoria UC", "UC Sampdoria")
register_club("Civil Service", "Civil Service London")
register_club("Montriond Sport", "FC Montriond")
register_club("Vie au Grand Air du Médoc", "V.A.G Air Medoc")
register_club("Spartak Moscow", "Spartak de Moscú", "Spartak Moscú")
register_club("Steaua București", "Steaua de Bucarest", "Steaua Bucaresti")
register_club("Dukla Praha", "Dukla de Praga")
register_club("Real Murcia", "Murcia", "Real Murcia CF")
register_club("Iberia SC", "Iberia", "Iberia CD")
register_club("Castilla FC", "Castilla")
register_club("CD Logroño", "Logroño")
register_club("AD Tranviaria", "Tranviaria")
register_club("Imperio FC", "Imperio de Madrid")
register_club("UD Salamanca", "Salamanca")
register_club("Atlético de Madrid", "Athletic Aviación")
register_club("Botafogo", "Botafogo FR", "Botafofo FR")
register_club("São Paulo", "São Paulo FC", "FC São Paulo FC")


class Sources:
    def __init__(self, directory, refresh=False):
        self.directory = directory
        self.refresh = refresh
        directory.mkdir(parents=True, exist_ok=True)

    def get(self, name, url):
        path = self.directory / (name + ".html")
        if self.refresh or not path.exists():
            request = Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; RM360 historical match research)"})
            with urlopen(request, timeout=25) as response:
                path.write_bytes(response.read())
        return path.read_bytes()

    def document(self, name, url):
        return html.fromstring(self.get(name, url))


def clean(node):
    return " ".join(node.text_content().split())


def iso_day(slash_date):
    return datetime.strptime(slash_date, "%d/%m/%Y").date().isoformat()


def parse_score(value):
    if match := SCORE.search(value):
        return [int(goal) for goal in match.groups()]
    return None


def calendar_date(text, default_year=None):
    match = re.search(r"(\d{1,2})(?: de)? ([A-Za-z]+)(?: de)?(?: (\d{4}))?", text)
    if match is None:
        raise ValueError(text)
    day, month, year = match.groups()
    months = "jan feb mar apr may jun jul aug sep oct nov dec".split()
    translated = {"ene": "jan", "abr": "apr", "ago": "aug", "dic": "dec"}
    month = month[:3].lower()
    return date(int(year or default_year), months.index(translated.get(month, month)) + 1, int(day)).isoformat()


class Archive:
    def __init__(self, through):
        self.through = through
        self.matches = {}
        self.audit = defaultdict(list)

    def add(self, day, home, away, score, competition, sources, details=None):
        if not "1902-03-06" <= day <= self.through:
            return None
        date.fromisoformat(day)
        home, away = club_name(home), club_name(away)
        if (home == TEAM) == (away == TEAM):
            raise ValueError((day, home, away, competition))
        at_home = home == TEAM
        rival = away if at_home else home
        goals = score if at_home else score[::-1]
        category = COMPETITIONS[competition][0]
        key = day, category, fold(rival)
        if record := self.matches.get(key):
            if record[3:5] != goals:
                self.audit["sameDayScoreConflicts"].append([record[:6], [day, rival, "H" if at_home else "A", *goals, competition], sources])
                return record
            for ref in sources:
                if ref not in record[6]:
                    record[6].append(ref)
            if details:
                if len(record) == 7:
                    record.append({})
                record[7].update(details)
            return record

        record = [day, rival, "H" if at_home else "A", *goals, competition, list(sources)]
        if details:
            record.append(details)
        self.matches[key] = record
        return record

    def candidates(self, competition):
        return [row for row in self.matches.values() if row[5] == competition]

    def corroborate(self, day, home, away, score, competition, ref, *, tolerant=False):
        """Compare historical sources without allowing an unchecked conflict to add a match."""
        home, away = club_name(home), club_name(away)
        at_home = home == TEAM
        rival = away if at_home else home
        goals = score if at_home else score[::-1]
        category = COMPETITIONS[competition][0]
        row = self.matches.get((day, category, fold(rival)))
        if row is None and tolerant:
            # The CSV uses modern club names in seasons with historical names.
            candidates = [r for r in self.candidates(competition)
                          if r[0] == day and r[2] == ("H" if at_home else "A") and r[3:5] == goals]
            if len(candidates) == 1:
                row = candidates[0]
        if row is None or row[3:5] != goals or row[5] != competition:
            self.audit["crossCheckDifferences"].append([ref[0], day, rival, *goals, competition, row[:6] if row else None])
            return None
        if ref not in row[6]:
            row[6].append(ref)
        return row

    def rows(self):
        return sorted(self.matches.values(), key=lambda row: (row[0], row[5], fold(row[1])))


def import_bdf(archive, sources):
    doc = sources.document("bdf", BDF + "p/e2.html")
    script = next(s for s in doc.xpath("//script/text()") if re.search(r"\bP=\[\[", s))
    rows, _ = json.JSONDecoder().raw_decode(re.split(r"\bP=", script, maxsplit=1)[1])
    if len(rows) < 4400:
        raise ValueError(f"Incomplete BDFutbol download: {len(rows)} matches")
    for _, code, _, raw_date, side, home, hg, ag, match_id, away, *_ in rows:
        day = iso_day(raw_date)
        if (club_name(home) == TEAM) != bool(side):
            raise ValueError((match_id, home, away, side))
        # In the 1903 Copa semifinal the opponent was Espanyol of Barcelona.
        if away == "Español" or home == "Español":
            home = "Espanyol" if home == "Español" else home
            away = "Espanyol" if away == "Español" else away
        competition = "fifa-intercontinental" if code == "MUN" and day >= "2024-01-01" else BDF_CODES[code]
        refs = [["bdf-special" if "&l=" in str(match_id) else "bdf", match_id]]
        if competition == "liga" and day.endswith("-11-28") and day < "2026-11-28":
            refs.append(["laliga-en-numeros"])
        archive.add(day, home, away, [hg, ag], competition, refs)


def import_rsssf_regional(archive, sources):
    doc = sources.document("centro", CENTRO)
    corrections = {
        "25-03-1991": "25-03-1911",
        "16-11-1914": "16-11-1924",
        "04-12-1917": "04-12-1927",
    }
    for header in doc.xpath("//h4[a/@name]"):
        anchor = header.find("a").get("name")
        pre = header.getnext()
        if pre is None or pre.tag != "pre":
            continue
        competition = "regional-joint" if anchor in ("32", "33", "34", "35", "36") else "regional"
        if anchor in ("41c", "44c"):
            competition = "castellana"
        for line in pre.text_content().splitlines():
            if line.startswith("COPA FEDERACIÓN CENTRO"):
                competition = "centro-cup"
            elif line.startswith("COPA CASTILLA"):
                competition = "castilla-cup"
            match = EARLY_REGIONAL.match(line.strip())
            if not match:
                continue
            raw_date, home, away, raw_score = match.groups()
            if TEAM not in (club_name(home), club_name(away)):
                continue
            if re.search(r"\b(segundos|terceros)\b", raw_score):
                continue
            score = parse_score(raw_score)
            if not score or competition == "castilla-cup":
                archive.audit["regionalSourceIssues"].append([anchor, line.strip()])
                continue
            # These two typos also occur as valid years in other seasons.
            if anchor in ("11", "25", "28"):
                raw_date = corrections.get(raw_date, raw_date)
            details = None
            if (anchor, raw_date) == ("05", "02-04-1905"):
                details = {"note": "انتهت المباراة بعد انسحاب مونكلوا والنتيجة 2–0."}
            elif (anchor, raw_date) == ("07", "02-12-1906"):
                archive.add(iso_day(raw_date.replace("-", "/")), home, away, score, "void-regional",
                            [["centro", anchor]], {"note": "أُلغي اعتماد المباراة لاحقًا بقرار الاتحاد الإقليمي."})
                continue
            elif (anchor, raw_date) == ("08", "22-03-1908"):
                details = {"note": "انسحب إسبانيول مدريد بين الشوطين والنتيجة 3–0."}
            archive.add(iso_day(raw_date.replace("-", "/")), home, away, score, competition, [["centro", anchor]], details)


def import_bdf_regional(archive, sources, name, tournament_id, competition):
    doc = sources.document(name, BDF + f"c/temporada.html?id={tournament_id}")
    for tr in doc.xpath("//tr[td]"):
        cells = tr.xpath("./td")
        for index, cell in enumerate(cells):
            if not re.fullmatch(r"\d{2}/\d{2}/\d{4}", clean(cell)) or len(cells) < index + 4:
                continue
            if "Real Madrid" in [clean(c) for c in cells[index + 1:]] or "Madrid" in [clean(c) for c in cells[index + 1:]]:
                links = tr.xpath('.//a[starts-with(@href, "partido.html?")]/@href')
                scores = [clean(n) for n in tr.xpath('.//div[contains(@class,"resultat-gols")]')]
                if len(scores) != 2 or not all(g.isdigit() for g in scores) or not links:
                    continue
                # This works with both the matchday and tournament layouts.
                query = parse_qs(urlparse(links[0]).query)
                h, a = query["l"][0], query["v"][0]
                if TEAM not in (club_name(h), club_name(a)):
                    continue
                day = iso_day(clean(cell))
                score = [int(g) for g in scores]
                ref = ["bdf-regional", links[0]]
                if any(r[0] == day and fold(r[1]) == fold(club_name(a if club_name(h) == TEAM else h))
                       for r in archive.candidates(competition)):
                    archive.corroborate(day, h, a, score, competition, ref)
                else:
                    archive.add(day, h, a, score, competition, [ref])
                break


def import_corroboration_csv(archive, sources):
    for file, competition, ref in (("spain", "liga", "curley-liga"), ("champs", "ucl", "curley-ucl")):
        raw = sources.get(file, CURLEY + file + ".csv").decode("utf-8-sig")
        for row in csv.DictReader(io.StringIO(raw)):
            if TEAM not in (row["home"], row["visitor"]):
                continue
            if row.get("tier", "1") != "1" or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", row["Date"]):
                continue
            score = parse_score(row.get("tothgoal", "") + "-" + row.get("totvgoal", "")) or parse_score(row["FT"])
            if score:
                result = archive.corroborate(row["Date"], row["home"], row["visitor"], score, competition, [ref], tolerant=True)
                if result and (shootout := parse_score(row.get("pens", ""))):
                    if len(result) == 7:
                        result.append({})
                    result[7]["shootout"] = shootout if result[2] == "H" else shootout[::-1]

    through = date.fromisoformat(archive.through)
    first_year_of_season = through.year - (through.month < 7)
    for year in range(2016, first_year_of_season + 1):
        season = f"{year % 100:02}{(year + 1) % 100:02}"
        raw = sources.get(f"fd-{year}", f"{FOOTBALL_DATA}mmz4281/{season}/SP1.csv").decode("utf-8-sig", "replace")
        for row in csv.DictReader(io.StringIO(raw)):
            if TEAM not in (row.get("HomeTeam"), row.get("AwayTeam")) or not row.get("FTHG", "").isdigit():
                continue
            parts = row["Date"].split("/")
            day = iso_day("/".join((parts[0], parts[1], str(2000 + int(parts[2])) if len(parts[2]) == 2 else parts[2])))
            if day <= archive.through:
                archive.corroborate(day, row["HomeTeam"], row["AwayTeam"], [int(row["FTHG"]), int(row["FTAG"])],
                                    "liga", ["football-data", season], tolerant=True)


def import_recent_official(archive, sources):
    doc = sources.document("laliga-current", LIGA_RESULTS)
    results = json.loads(doc.xpath('//script[@id="__NEXT_DATA__"]/text()')[0])["props"]["pageProps"]["matches"]
    for match in results:
        competition = LIGA_CODES.get(match["competition"]["slug"])
        if competition is None or match["status"] != "FullTime" or match["home_score"] is None or match["away_score"] is None:
            continue
        played = datetime.fromisoformat(match["date"]).astimezone(SPAIN_TZ).date().isoformat()
        if played > archive.through:
            continue
        home, away = (club_name(match[x + "_team"]["nickname"]) for x in ("home", "away"))
        if TEAM not in (home, away):
            continue
        reference = ["laliga", match["slug"]]
        rival = away if home == TEAM else home
        score = [match["home_score"], match["away_score"]]
        if (played, "official", fold(rival)) in archive.matches:
            archive.corroborate(played, home, away, score, competition, reference)
        else:
            archive.add(played, home, away, score, competition, [reference])
        if match["slug"].endswith("real-madrid-psv-5"):
            archive.corroborate(played, home, away, score, competition, ["club", CLUB + "/es-ES/noticias/futbol/primer-equipo/cronicas/real-madrid-psv-24-11-2026"])


def import_rsssf_friendly(archive, sources):
    for portion in ("0239", "4059", "6079", "8000", "0105", "0914"):
        doc = sources.document(f"friend-{portion}", FRIENDLIES.format(portion))
        for tr in doc.xpath("//table//tr")[1:]:
            raw_date, event, _, home, away, raw_score = [clean(n) for n in tr.xpath("./td")]
            if raw_date == "03/0371907":
                raw_date = "03/03/1907"
            score = parse_score(raw_score)
            if score is None:
                raise ValueError((raw_date, home, away, raw_score))
            event_key = fold(event)
            competition = "friendly"
            for pattern, code in (("bernab", "bernabeu"), ("teresa herrera", "teresa-herrera"),
                                  ("champions cup", "icc"), ("copa del mundo", "small-world-cup")):
                if pattern in event_key:
                    competition = code
                    break
            else:
                if re.search(r"trophy|cup|torneo|trofeo|tournament|pokal", event_key):
                    competition = "friendly-tournament"
            archive.add(iso_day(raw_date), home, away, score, competition, [["rsssf-friendly", portion]])


def import_season_friendlies(archive, sources, season, early=False):
    if season == 1902:
        url, section, ref = WIKI_EARLY, "Friendlies", ["early"]
    elif season == 1903:
        url, section, ref = WIKI_EARLY_ES, "Torneos_amistosos", ["early-es"]
    else:
        name = quote(f"{season}–{(season + 1) % 100:02}_Real_Madrid_CF_season")
        url, section, ref = WIKI + name, "Pre-season_and_friendlies", ["season", name + "#Pre-season_and_friendlies"]
    doc = sources.document(f"wiki-{season}", url)
    for table in doc.xpath(f'//section[@aria-labelledby="{section}"]//table[contains(@class,"vevent")]'):
        row = table.xpath(".//tr[td]")[0]
        cells = [clean(n) for n in row.xpath("./td")]
        if len(cells) < 4 or not (score := parse_score(cells[2])):
            continue
        raw_date, home, raw_score, away = cells[:4]
        day = calendar_date(raw_date, default_year=season)
        references = [ref]
        if early:
            links = table.xpath('.//a[contains(@href,"leyendablanca.galeon.com")]/@href')
            if links:
                references.append(["leyenda", links[0]])
        else:
            links = table.xpath('.//a[@class="external text"]/@href')
            if links and links[0].startswith(CLUB + "/en-US/football/games/"):
                references.append(["club", links[0]])
        second_score = SCORE.findall(raw_score)[1:]
        details = None
        if second_score and re.search(r"\bp(?:en)?\b", raw_score):
            penalties = [int(number) for number in second_score[0]]
            details = {"shootout": penalties if club_name(home) == TEAM else penalties[::-1]}
        event_key = fold(raw_date)
        competition = "friendly"
        if "bandas" in event_key:
            competition = "bandas"
        elif "codorniu" in event_key:
            competition = "codorniu"
        elif "san lorenzo" in event_key:
            competition = "friendly-tournament"
        archive.add(day, home, away, score, competition, references, details)


def import_leyenda(archive, sources, snapshots):
    by_date = defaultdict(list)
    for row in archive.matches.values():
        by_date[row[0]].append(row)

    def get_snapshot(entry):
        season, url = entry
        return int(season), url, sources.document(f"leyenda-late-{season}", url)

    with ThreadPoolExecutor(max_workers=6) as pool:
        for season, url, document in pool.map(get_snapshot, snapshots.items()):
            for day, home, away, score, event in extract_leyenda(document, season, club_name, fold):
                if not "1902-03-06" <= day <= archive.through:
                    continue
                at_home = home == TEAM
                rival = away if at_home else home
                goals = score if at_home else score[::-1]
                ref = ["leyenda", season]
                if known := next((r for r in by_date[day] if same_opponent(rival, r[1], fold)), None):
                    if known[3:5] == goals and ref not in known[6]:
                        known[6].append(ref)
                    elif known[3:5] != goals:
                        archive.audit["leyendaConflicts"].append([day, rival, goals, known[:6], url])
                    continue

                # Several archival editions name the same visitor differently. Preserve
                # one result and record the competing name when the score and date agree.
                same_result = [r for r in by_date[day] if r[3:5] == goals and
                               any(reference[0] in ("rsssf-friendly", "early", "early-es", "season") for reference in r[6])]
                if len(same_result) == 1:
                    archive.audit["leyendaOpponentDifferences"].append([day, rival, same_result[0][:6], url])
                    continue

                following_day = date.fromisoformat(day)
                nearby = [r for delta in (-2, -1, 1, 2) for r in by_date[(following_day + timedelta(days=delta)).isoformat()]
                          if r[3:5] == goals and same_opponent(rival, r[1], fold)
                          and any(reference[0] != "leyenda" for reference in r[6])]
                if nearby:
                    archive.audit["leyendaDateDifferences"].append([day, rival, goals, nearby[0][:6], url])
                    continue

                # The event ends before the venue description. The Bernabéu stadium
                # also hosted ordinary friendlies and other tournaments.
                event = event.split(" en ", 1)[0]
                competition = "friendly-tournament"
                for phrase, code in (("trofeo santiago bernabeu", "bernabeu"), ("teresa herrera", "teresa-herrera"),
                                     ("international champions cup", "icc"), ("copa audi", "audi"),
                                     ("copa del mundo", "small-world-cup"), ("copa rodriguez arzuaga", "arzuaga")):
                    if phrase in event:
                        competition = code
                        break
                else:
                    if not re.search(r"\b(?:trofeo|torneo|copa|concurso)\b", event):
                        competition = "friendly"
                row = archive.add(day, home, away, score, competition, [ref])
                if row:
                    by_date[day].append(row)


def import_manual(archive, reviewed):
    for day, home, away, score, competition, refs, *optional in reviewed["add"]:
        archive.add(day, home, away, score, competition, refs, optional[0] if optional else None)
    for entry in reviewed["correct"]:
        old_date, category, opponent = entry["match"]
        key = old_date, category, fold(club_name(opponent))
        row = archive.matches.pop(key)
        new_date = entry.get("date", old_date)
        score = entry.get("score", row[3:5])
        refs = entry.get("replaceSources", row[6]) + entry.get("sources", [])
        opponent = entry.get("opponent", row[1])
        home, away = (TEAM, opponent) if row[2] == "H" else (opponent, TEAM)
        archive.add(new_date, home, away, score if row[2] == "H" else score[::-1], entry.get("competition", row[5]),
                    refs, entry.get("details", row[7] if len(row) > 7 else None))


def import_fixture_snapshot(sources, through):
    doc = sources.document("club-calendar", CLUB_CALENDAR)
    state = json.loads(doc.xpath('//script[@id="ng-state"]/text()')[0])
    records = next(item for item in state.values() if isinstance(item, dict) and "diaryV2" in item.get("u", ""))
    teams = {
        "Real Madrid": "RMA", "Alavés": "ALA", "Real Sociedad": "RSO", "Athletic Club": "ATH",
        "Arsenal": "ARS", "Osasuna": "OSA", "LASK": "LASK", "Shakhtar Donetsk": "SHA",
    }
    competitions = {"la-liga": "liga", "champions-league": "ucl", "supercopa-de-espana": "supercopa",
                    "copa-del-rey": "copa"}
    fixtures = []
    for match in records["b"]["data"]["matchList"]["items"]:
        competition = competitions.get(match["competition"]["slug"])
        if not competition or match["status"] != "pre_match" or not match["isScheduled"] or not match["dateTime"]:
            continue
        home, away = (match[side + "Team"]["name"] for side in ("home", "away"))
        if TEAM not in (home, away):
            continue
        fixtures.append({
            "id": match["optaId"], "c": competition, "d": match["dateTime"], "tc": True,
            "h": teams.get(home, home), "a": teams.get(away, away),
            "opponent": away if home == TEAM else home,
            "source": CLUB_CALENDAR,
        })
    fixtures.sort(key=lambda match: match["d"])
    captured = re.search(r"fromDate=([^%]+)", records["u"])
    return {"schema": "rm360-history-fixtures/1", "updatedAt": captured[1] if captured else through + "T00:00:00Z", "matches": fixtures}


def write_archive(output, archive, reviewed, snapshots):
    # One match per line keeps diffs and reviews useful without repeating the column names.
    data = {
        "schema": "rm360-history/2", "checkedThrough": archive.through,
        "competitions": COMPETITIONS, "sources": SOURCES, "opponents": reviewed["opponents"],
        "coverage": COVERAGE, "credits": CREDITS, "historicalSnapshots": snapshots,
    }
    with (output / "history.json").open("w", encoding="utf-8") as file:
        file.write(json.dumps(data, ensure_ascii=False, indent=2).removesuffix("\n}"))
        file.write(',\n  "matches": [\n')
        file.write(",\n".join("    " + json.dumps(row, ensure_ascii=False, separators=(",", ":")) for row in archive.rows()))
        file.write("\n  ]\n}\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--through", type=date.fromisoformat, required=True)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=ROOT / "site" / "feed")
    parser.add_argument("--audit", type=Path, help="Write comparison diagnostics")
    parser.add_argument("--refresh", action="store_true", help="Re-download all cached inputs")
    args = parser.parse_args()

    archive = Archive(args.through.isoformat())
    sources = Sources(args.cache, args.refresh)
    reviewed = json.loads((ROOT / "build" / "history-reviewed.json").read_text(encoding="utf-8"))
    snapshots = json.loads((ROOT / "build" / "history-leyenda-snapshots.json").read_text())
    import_bdf(archive, sources)
    import_rsssf_regional(archive, sources)
    for year, (tournament, competition) in REGIONAL_EDITIONS.items():
        import_bdf_regional(archive, sources, f"regional-{year}", tournament, competition)
    for tournament, competition in REGIONAL_CUPS.items():
        import_bdf_regional(archive, sources, f"regional-cup-{tournament}", tournament, competition)
    import_corroboration_csv(archive, sources)
    import_recent_official(archive, sources)
    import_rsssf_friendly(archive, sources)
    for year in (1902, 1903, *range(2014, 2026)):
        import_season_friendlies(archive, sources, year, early=year < 1904)
    import_manual(archive, reviewed)
    import_leyenda(archive, sources, snapshots)
    for item in reviewed.get("exclude", []):
        day, category, rival = item["match"]
        archive.matches.pop((day, category, fold(club_name(rival))), None)
    args.output.mkdir(parents=True, exist_ok=True)
    write_archive(args.output, archive, reviewed, snapshots)
    fixture = import_fixture_snapshot(sources, archive.through)
    (args.output / "history-fixtures.json").write_text(json.dumps(fixture, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.audit:
        args.audit.write_text(json.dumps(archive.audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{len(archive.matches)} matches", dict(Counter(row[5] for row in archive.rows())))
    print("Review diagnostics:", {name: len(rows) for name, rows in archive.audit.items()})


if __name__ == "__main__":
    main()
