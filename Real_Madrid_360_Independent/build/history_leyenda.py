"""Read dated first-team results from the friendly sections of Leyenda Blanca."""
import re
from datetime import date
from difflib import SequenceMatcher

FRIENDLIES_HEADING = re.compile(
    r"(?i)(?:\bPRETEMPORADA[\s,.]+(?:AMISTOSOS?[\s,]+TROFEOS\s+Y\s+HOMENAJES"
    r"|TROFEOS\s+Y\s+AMISTOSOS)|\bAMISTOSOS,\s+TROFEOS\s+Y\s+HOMENAJES)"
    r"\s*(?:\d{2,4}\s*[-/]\s*\d{2,4})?\s*:?"
)
OFFICIAL_HEADING = re.compile(
    r"(?im)^[ \t]*(?:CAMPEONATO\s+(?:NACIONAL|MANCOMUNADO|REGIONAL|CENTRO|DE\s+(?:LIGA|MADRID))"
    r"|COPA\s+(?:DE\s+S\.?\s*M|DEL\s+(?:REY|GENERAL|PRESIDENTE)|DE\s+(?:EUROPA|LA UEFA|LA LIGA|ESPAÑA)"
    r"|LATINA|IBEROAMERICANA|INTERCONTINENTAL|DE\s+LA\s+REPÚBLICA)"
    r"|LIGA NACIONAL|SUPERCOPA\s+(?:DE ESPAÑA|EUROPEA|DE EUROPA)|PRIMERA DIVISI[ÓO]N(?:\s*\d{4}|\s*:))"
)
MONTHS = "enero febrero marzo abril mayo junio julio agosto septiembre octubre noviembre diciembre".split()
DATE = re.compile(
    r"(?im)^[ \t]*(?P<day>\d{1,2})(?:[-/](?P<number>\d{1,2})[-/]|"
    r"(?:\s+de)?\s+(?P<month>" + "|".join([*MONTHS, "setiembre"]) + r")(?:\s+de)?\s*)"
    r"(?P<year>\d{4})(?=\s|\.|:|,|$)"
)
PAIR = re.compile(
    r"(?im)^[ \t]*([A-ZÁÉÍÓÚÜÑÇ0-9][^:\n]{0,68}?)\s*[-–—\x96]\s*([^:\n]{1,68}?)"
    r"[\s.]*(?<!\d)(\d{1,2})\s*[-–:\x96]\s*(\d{1,2})(?=\s|\(|[.,]|$)"
)
LOCATED_REAL = re.compile(r"\)\s*((?:REAL )?MADRID\b)", re.I)
TEAM = "Real Madrid"
NON_FIRST_TEAM = re.compile(r"(?i)\b(?:amateur|juvenil|veteranos|reservas|coppel|castilla)\b|\b[234]\s*[ºª°]")
FRIENDLY_EVENT = re.compile(
    r"\b(?:amistoso|trofeo|torneo|homenaje|aniv|aniversario|"
    r"international champions cup|copa pequena|pequena copa|copa audi|audi cup|"
    r"copa santiago|concurso de bandas|copa rodriguez arzuaga|copa j ruete|copa madrid|"
    r"fiestas de s lorenzo|gira)\b"
)


def extract(document, season, normalize, fold):
    for node in document.xpath("//script|//style"):
        node.drop_tree()
    for node in document.xpath("//br|//pre|//p|//td"):
        node.tail = "\n" + (node.tail or "")
    text = document.text_content().replace("\u00a0", " ")
    heading = FRIENDLIES_HEADING.search(text)
    if not heading:
        return

    section = text[heading.end():]
    end = OFFICIAL_HEADING.search(section)
    if end:
        section = section[:end.start()]

    dates = list(DATE.finditer(section))
    for i, marker in enumerate(dates):
        block = section[marker.end():dates[i + 1].start() if i + 1 < len(dates) else len(section)]
        sample = "\n".join(block.splitlines()[:13])
        sample = LOCATED_REAL.sub(r")\n\1", sample)
        for pair in PAIR.finditer(sample):
            home, away, hg, ag = pair.groups()
            home = normalize(home.strip(" ."))
            away = normalize(away.strip(" ."))
            if (home == TEAM) == (away == TEAM) or NON_FIRST_TEAM.search(home + " " + away):
                continue
            event = sample[:pair.start()]
            if "amistoso?" in event.lower() or not FRIENDLY_EVENT.search(fold(event)):
                continue
            year = int(marker["year"])
            if year not in (season - 1, season):
                continue
            month = marker["month"]
            number = int(marker["number"]) if marker["number"] else MONTHS.index(month.lower().replace("setiembre", "septiembre")) + 1
            try:
                day = date(year, number, int(marker["day"])).isoformat()
            except ValueError:
                continue
            yield day, home, away, [int(hg), int(ag)], fold(event)
            break


def same_opponent(a, b, fold):
    a, b = fold(a), fold(b)
    if a == b:
        return True
    qualifiers = {"fc", "cf", "cd", "ac", "sc", "sl", "as", "rc", "fk", "rcd", "club", "real", "de", "ud", "ad", "sd"}
    first = [term for term in a.split() if term not in qualifiers]
    second = [term for term in b.split() if term not in qualifiers]
    if not first or not second:
        return False
    return first == second or SequenceMatcher(None, " ".join(first), " ".join(second)).ratio() >= .84
