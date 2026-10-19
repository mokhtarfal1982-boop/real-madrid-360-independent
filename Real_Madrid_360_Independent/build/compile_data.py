"""Compile verified Real Madrid 360 data (SportRadar via sports data tool, 17 Oct 2026)
into site/data.js, and cross-check the La Liga table against computed results."""
import json, sys, os
from collections import defaultdict
from datetime import datetime, timezone

from datetime import timedelta
UPDATED_AT = (datetime.now(timezone(timedelta(hours=3)))).replace(second=0, microsecond=0).isoformat()

# ---------- La Liga: every final match played so far (79) ----------
LIGA_FINALS = [
    (72478494,"2026-08-22T19:30","ESP","RMA",1,2),(72478460,"2026-08-26T19:00","RMA","RSO",4,1),
    (72478520,"2026-08-30T15:00","RMA","MCF",4,0),(72478530,"2026-09-04T19:00","RBB","RMA",1,0),
    (72478558,"2026-09-12T19:00","RMA","RVC",4,1),(72478574,"2026-09-15T19:30","ELC","RMA",2,3),
    (72478588,"2026-09-20T14:15","ATM","RMA",2,1),(72478622,"2026-10-10T19:00","RMA","VIL",1,0),
    (72478492,"2026-08-23T19:30","ELC","BAR",0,5),(72478456,"2026-08-27T19:00","BAR","ATH",2,0),
    (72478512,"2026-08-31T19:30","BAR","RVC",5,2),(72478542,"2026-09-06T14:15","VCF","BAR",0,5),
    (72478552,"2026-09-13T14:15","LEV","BAR",2,4),(72478576,"2026-09-16T19:30","BAR","RAC",7,2),
    (72478600,"2026-09-19T19:00","SEV","BAR",1,3),(72478612,"2026-10-10T16:30","BAR","GET",3,0),
    (72478448,"2026-08-19T19:00","ATM","MCF",2,0),(72478488,"2026-08-23T15:00","ATM","VIL",2,2),
    (72478524,"2026-08-29T19:30","SEV","ATM",1,3),(72478528,"2026-09-05T14:15","ATH","ATM",3,0),
    (72478560,"2026-09-13T19:00","RSO","ATM",0,3),(72478568,"2026-09-16T17:00","ATM","OSA",4,0),
    (72478606,"2026-10-10T14:15","ALA","ATM",1,2),
    (72478490,"2026-08-21T19:00","RBB","RSO",1,0),(72478464,"2026-08-25T19:00","VCF","RBB",0,1),
    (72478514,"2026-08-29T15:00","LEV","RBB",5,2),(72478564,"2026-09-14T19:00","VIL","RBB",1,2),
    (72478570,"2026-09-17T17:00","RBB","GET",1,0),(72478592,"2026-09-20T16:30","DEP","RBB",1,1),
    (72478608,"2026-10-11T16:30","RBB","OSA",5,2),
    (72478462,"2026-08-15T19:30","SEV","RVC",2,1),(72478486,"2026-08-22T15:00","ATH","SEV",1,3),
    (72478534,"2026-09-06T19:00","ESP","SEV",1,1),(72478562,"2026-09-11T19:00","SEV","VCF",1,0),
    (72478572,"2026-09-16T17:00","DEP","SEV",0,1),(72478614,"2026-10-12T19:00","LEV","SEV",3,3),
    (72478522,"2026-08-29T17:00","RSO","ESP",2,1),(72478584,"2026-09-03T19:00","RSO","RCC",0,0),
    (72478532,"2026-09-07T19:30","ELC","RSO",2,3),(72478602,"2026-09-20T19:00","VCF","RSO",2,3),
    (72478624,"2026-10-11T14:15","RSO","DEP",3,2),
    (72478446,"2026-08-15T17:30","ALA","GET",3,0),(72478502,"2026-08-20T19:00","RVC","ALA",1,1),
    (72478506,"2026-08-28T19:30","ALA","VIL",1,0),(72478526,"2026-09-06T16:30","ALA","OSA",5,2),
    (72478556,"2026-09-12T12:00","RAC","ALA",2,1),(72478566,"2026-09-15T18:00","ALA","VCF",0,1),
    (72478586,"2026-09-19T14:15","ATH","ALA",0,0),
    (72478452,"2026-08-17T19:00","DEP","ELC",1,1),(72478498,"2026-08-24T19:30","MCF","DEP",1,1),
    (72478510,"2026-08-30T17:30","DEP","VCF",3,1),(72478544,"2026-09-05T19:00","VIL","DEP",2,3),
    (72478550,"2026-09-13T16:30","GET","DEP",1,1),(72478630,"2026-10-16T19:00","DEP","LEV",1,1),
    (72478504,"2026-08-22T17:30","VCF","RCC",0,0),(73706190,"2026-08-27T18:30","RCC","OSA",1,2),
    (72478508,"2026-08-30T19:30","RCC","ATH",0,2),(72478536,"2026-09-07T17:00","GET","RCC",1,1),
    (72478548,"2026-09-13T12:00","RCC","MCF",1,1),(72478590,"2026-09-19T16:30","RCC","RAC",5,0),
    (72478610,"2026-10-11T12:00","ELC","RCC",0,0),
    (72478546,"2026-09-12T16:30","ATH","ELC",1,1),
    (72478458,"2026-08-16T15:00","RAC","VIL",2,2),(72478580,"2026-09-17T19:30","MCF","VIL",1,3),
    (72478604,"2026-09-20T16:30","VIL","LEV",3,1),
    (72478454,"2026-08-16T17:00","ESP","LEV",3,0),(72478554,"2026-09-12T14:15","OSA","ESP",0,2),
    (72478582,"2026-09-15T17:00","RVC","ESP",2,1),(72478594,"2026-09-18T19:00","ESP","ELC",1,3),
    (72478616,"2026-10-09T19:00","MCF","ESP",1,1),
    (72478540,"2026-09-05T16:30","RVC","RAC",3,2),(72478598,"2026-09-19T12:00","OSA","RVC",1,1),
    (72478496,"2026-08-23T17:30","GET","RAC",1,0),(72478516,"2026-08-31T17:30","OSA","GET",1,0),
    (72478596,"2026-09-20T12:00","GET","MCF",1,0),
    (72478518,"2026-08-28T17:00","RAC","ELC",3,2),(72478618,"2026-10-11T19:00","RAC","VCF",2,2),
    (72478500,"2026-08-24T17:30","OSA","LEV",0,0),
    (72478538,"2026-09-06T16:30","MCF","LEV",0,0),
    (72478640,"2026-10-18T19:00","RMA","SEV",4,1),
]

# SportRadar La Liga standings (rank order), W/D/L/Pts
LIGA_STANDINGS = [
    ("BAR",8,0,0,24),("RMA",7,0,2,21),("ATM",6,1,1,19),("RBB",6,1,1,19),("SEV",4,2,3,14),
    ("RSO",4,1,3,13),("ALA",3,2,3,11),("DEP",2,5,2,11),("RCC",1,5,2,8),("ATH",2,2,2,8),
    ("VIL",2,2,4,8),("ESP",2,2,4,8),("RVC",2,2,3,8),("GET",2,2,4,8),("RAC",2,2,4,8),
    ("OSA",2,2,4,8),("LEV",1,4,3,7),("ELC",1,3,4,6),("VCF",1,2,5,5),("MCF",0,4,4,4),
]

# SportRadar UEFA Champions League league-phase standings (rank order)
UCL_STANDINGS = [
    ("PSG",2,0,0,6),("BAR",2,0,0,6),("AVL",2,0,0,6),("VFB",2,0,0,6),("LFC",2,0,0,6),
    ("SPO",2,0,0,6),("ARS",2,0,0,6),("RMA",2,0,0,6),("RBB",2,0,0,6),("BMU",1,1,0,4),
    ("SHA",1,1,0,4),("COM",1,0,1,3),("MUN",1,0,1,3),("VIL",1,0,1,3),("ATM",1,0,1,3),
    ("BRU",1,0,1,3),("MCI",1,0,1,3),("BVB",1,0,1,3),("RCL",1,0,1,3),("AEK",1,0,1,3),
    ("RBL",1,0,1,3),("SBH",1,0,1,3),("FEY",1,0,1,3),("BOG",1,0,1,3),("ROM",0,1,1,1),
    ("PSV",0,1,1,1),("VIK",0,1,1,1),("FEN",0,1,1,1),("INT",0,0,2,0),("FCP",0,0,2,0),
    ("SLA",0,0,2,0),("NAP",0,0,2,0),("ASK",0,0,2,0),("LIL",0,0,2,0),("GAL",0,0,2,0),
    ("SLO",0,0,2,0),
]

# Real Madrid fixtures and results, all competitions. t = time confirmed by the competition.
RM_MATCHES = [
    # La Liga, played
    ("72478494","liga","2026-08-22T19:30","ESP","RMA",1,2,True),
    ("72478460","liga","2026-08-26T19:00","RMA","RSO",4,1,True),
    ("72478520","liga","2026-08-30T15:00","RMA","MCF",4,0,True),
    ("72478530","liga","2026-09-04T19:00","RBB","RMA",1,0,True),
    ("72478558","liga","2026-09-12T19:00","RMA","RVC",4,1,True),
    ("72478574","liga","2026-09-15T19:30","ELC","RMA",2,3,True),
    ("72478588","liga","2026-09-20T14:15","ATM","RMA",2,1,True),
    ("72478622","liga","2026-10-10T19:00","RMA","VIL",1,0,True),
    # Champions League, played
    ("74165878","ucl","2026-09-08T19:00","RMA","INT",2,1,True),
    ("74165926","ucl","2026-10-14T19:00","ROM","RMA",3,4,True),
    # La Liga: confirmed result of Sevilla match
    ("72478640","liga","2026-10-18T19:00","RMA","SEV",4,1,True),
    # Upcoming (times from SportRadar; later La Liga dates are placeholders until set)
    ("74165970","ucl","2026-10-21T19:00","RMA","RBL",None,None,True),
    ("72478654","liga","2026-10-25T20:00","BAR","RMA",None,None,True),
    ("72478680","liga","2026-11-01T15:15","RAC","RMA",None,None,True),
    ("74165996","ucl","2026-11-04T17:45","AEK","RMA",None,None,True),
    ("72478702","liga","2026-11-07T20:00","VCF","RMA",None,None,True),
    ("72478722","liga","2026-11-22T19:00","RMA","RCC",None,None,False),
    ("74166028","ucl","2026-11-24T20:00","RMA","PSV",None,None,True),
    ("72478740","liga","2026-11-29T19:00","RMA","ALA",None,None,False),
    ("72478748","liga","2026-12-06T19:00","ATH","RMA",None,None,False),
    ("74166072","ucl","2026-12-09T20:00","ARS","RMA",None,None,True),
    ("72478780","liga","2026-12-13T19:00","RMA","OSA",None,None,False),
    ("72478792","liga","2026-12-20T19:00","DEP","RMA",None,None,False),
    ("72478820","liga","2027-01-03T19:00","RMA","GET",None,None,False),
    ("74166100","ucl","2027-01-19T20:00","RMA","ASK",None,None,True),
    ("74166136","ucl","2027-01-27T20:00","SHA","RMA",None,None,True),
]

# Goal minutes for the last result (SportRadar key events)
LAST_RESULT_EVENTS = {
    "74165926": {"home": [20, 51, 57], "away": [25, 83, 85, 90]},
}

ABSENCES = [
    {"name": "فينيسيوس جونيور", "kind": "suspended",
     "status": "موقوف 4 مباريات في الدوري",
     "detail": "طُرد أمام فياريال في 10 أكتوبر، ورُفض الاستئناف. يغيب عن إشبيلية وبرشلونة وراسينغ سانتاندير وفالنسيا، ومتاح في دوري الأبطال.",
     "ligaBanFixtures": ["72478640", "72478654", "72478680", "72478702"]},
    {"name": "إيدير ميليتاو", "kind": "injured", "status": "إصابة عضلية",
     "detail": "عودته متوقعة قبل نهاية أكتوبر."},
    {"name": "رودريغو", "kind": "injured", "status": "إصابة في الركبة",
     "detail": "موعد عودته غير معروف."},
    {"name": "فيرلاند ميندي", "kind": "injured", "status": "مصاب",
     "detail": "قد يغيب حتى أواخر 2026."},
    {"name": "راؤول أسينسيو", "kind": "injured", "status": "كسر إجهادي في الساق",
     "detail": "خضع لجراحة، وغيابه يقارب 3 أشهر."},
]
ABSENCES_SOURCE = {"label": "Sports Mole، 15 و16 أكتوبر 2026",
                   "url": "https://www.sportsmole.co.uk/football/real-madrid/injury-news/injuries-and-suspensions/vinicius-militao-rodrygo-updates-real-madrid-injury-suspension-news-vs-sevilla_606939.html"}

OPPONENT_NOTES = {
    "72478640": {
        "round": "الجولة 9",
        "venue": "سانتياغو برنابيو",
        "opponentAbsences": [
            "ماركاو (إصابة عضلية)", "جون غوريدي (إصابة في العضلة المقربة)",
            "ميغيل سييرا (إصابة في الكتف)", "إيساك روميرو (موقوف)"],
        "source": {"label": "Sports Mole، 16 أكتوبر 2026",
                   "url": "https://www.sportsmole.co.uk/football/real-madrid/race-for-the-la-liga-title/preview/real-madrid-vs-sevilla-prediction-team-news-lineups_607030.html"},
    }
}

NEWS_FALLBACK = [
    {"id": "2026-10-16-tebas", "category": "official",
     "title": "ريال مدريد يطالب رئيس رابطة الدوري خافيير تيباس بالاستقالة",
     "summary": "صدر بيان النادي بعد منشور لتيباس شبّه فيه أساليب النادي الإعلامية بأساليب دعاية غوبلز، ووصف النادي التشبيه بأنه غير مقبول وخطير للغاية.",
     "source": "ريال مدريد", "url": "https://www.realmadrid.com/en-US/news/club/announcements/comunicado-oficial-16-10-2026",
     "date": "2026-10-16"},
    {"id": "2026-10-16-vini-appeal", "category": "reliable",
     "title": "رفض استئناف ريال مدريد وتثبيت إيقاف فينيسيوس 4 مباريات",
     "summary": "رفضت لجنة الاستئناف في الاتحاد الإسباني الطعن، فيغيب فينيسيوس عن إشبيلية وبرشلونة وراسينغ وفالنسيا في الدوري، ويتجه النادي إلى المحكمة الإدارية للرياضة.",
     "source": "Yahoo Sports", "url": "https://sports.yahoo.com/articles/real-madrid-appeal-rejected-vinicius-131015686.html",
     "date": "2026-10-16"},
    {"id": "2026-10-16-rm-team-news", "category": "reliable",
     "title": "أربعة مصابين وموقوف في ريال مدريد قبل مواجهة إشبيلية",
     "summary": "يغيب ميليتاو ورودريغو وفيرلاند ميندي وراؤول أسينسيو للإصابة، إضافة إلى فينيسيوس الموقوف.",
     "source": "Sports Mole", "url": "https://www.sportsmole.co.uk/football/real-madrid/race-for-the-la-liga-title/preview/real-madrid-vs-sevilla-prediction-team-news-lineups_607030.html",
     "date": "2026-10-16"},
    {"id": "2026-10-16-sevilla-absences", "category": "reliable",
     "title": "إشبيلية يفتقد أربعة لاعبين قبل زيارة البرنابيو",
     "summary": "يغيب ماركاو وجون غوريدي وميغيل سييرا للإصابة، وإيساك روميرو للإيقاف بعد طرده أمام ليفانتي.",
     "source": "Sports Mole", "url": "https://www.sportsmole.co.uk/football/real-madrid/race-for-the-la-liga-title/preview/real-madrid-vs-sevilla-prediction-team-news-lineups_607030.html",
     "date": "2026-10-16"},
    {"id": "2026-10-10-mourinho-presser", "category": "reliable",
     "title": "مورينيو يقاطع المؤتمر الصحفي بعد مباراة فياريال",
     "summary": "قاطع المدرب المؤتمر الصحفي عقب الفوز على فياريال وسط جدل تحكيمي، وأعلن النادي دعمه لقراره.",
     "source": "Goal", "url": "https://www.goal.com/en-us/lists/real-madrid-completely-support-jose-mourinho-decision-boycott-villarreal-press-conference-refereeing-controversy/blt2dc4b219eacfbf55",
     "date": "2026-10-10"},
]


def compute_table(matches):
    t = defaultdict(lambda: {"p": 0, "w": 0, "d": 0, "l": 0, "gf": 0, "ga": 0, "pts": 0})
    for _id, _dt, h, a, hs, as_ in matches:
        for team, gf, ga in ((h, hs, as_), (a, as_, hs)):
            r = t[team]
            r["p"] += 1; r["gf"] += gf; r["ga"] += ga
            if gf > ga: r["w"] += 1; r["pts"] += 3
            elif gf == ga: r["d"] += 1; r["pts"] += 1
            else: r["l"] += 1
    return t


def main(out_path):
    ids = [m[0] for m in LIGA_FINALS]
    assert len(ids) == len(set(ids)) == 80, (len(ids), len(set(ids)))
    table = compute_table(LIGA_FINALS)
    errors = []
    for code, w, d, l, pts in LIGA_STANDINGS:
        r = table[code]
        if (r["w"], r["d"], r["l"], r["pts"]) != (w, d, l, pts):
            errors.append(f"{code}: computed {r['w']}/{r['d']}/{r['l']}/{r['pts']} vs SportRadar {w}/{d}/{l}/{pts}")
    if errors:
        print("TABLE MISMATCH:\n" + "\n".join(errors)); sys.exit(1)
    # RM results must be consistent with the league table row
    rm_liga = [m for m in RM_MATCHES if m[1] == "liga" and m[5] is not None]
    assert len(rm_liga) == table["RMA"]["p"]
    # UCL row check for Real Madrid
    rm_ucl = [m for m in RM_MATCHES if m[1] == "ucl" and m[5] is not None]
    w = sum(1 for m in rm_ucl if (m[5] - m[6]) * (1 if m[3] == "RMA" else -1) > 0)
    assert w == 2 and len(rm_ucl) == 2

    liga = []
    for rank, (code, w, d, l, pts) in enumerate(LIGA_STANDINGS, 1):
        r = table[code]
        liga.append({"r": rank, "t": code, "p": w + d + l, "w": w, "d": d, "l": l,
                     "gf": r["gf"], "ga": r["ga"], "pts": pts})
    ucl = [{"r": i, "t": c, "p": w + d + l, "w": w, "d": d, "l": l, "pts": p}
           for i, (c, w, d, l, p) in enumerate(UCL_STANDINGS, 1)]
    matches = []
    for mid, comp, dt, h, a, hs, as_, conf in RM_MATCHES:
        m = {"id": mid, "c": comp, "d": dt + ":00Z", "h": h, "a": a, "tc": conf}
        if hs is not None:
            m["hs"], m["as"] = hs, as_
        if mid in LAST_RESULT_EVENTS:
            m["goals"] = LAST_RESULT_EVENTS[mid]
        if mid in OPPONENT_NOTES:
            m["notes"] = OPPONENT_NOTES[mid]
        matches.append(m)
    meta = {"version": 1, "updatedAt": UPDATED_AT, "dataSource": "SportRadar", "coach": "جوزيه مورينيو", "matches": matches}
    j = lambda o: json.dumps(o, ensure_ascii=False, separators=(",", ":"))
    head = "/* Real Madrid 360 data. Maintained by Claude. Do not edit by hand. */\n"
    files = {
        "data-1.js": head + "window.RM360_DATA=" + j(meta) + ";\n",
        "data-2.js": head + "(function(d){d.liga=" + j(liga) + ";d.ucl=" + j(ucl) + ";})(window.RM360_DATA);\n",
        "data-3.js": head + "(function(d){d.absences=" + j(ABSENCES) + ";d.absencesSource=" + j(ABSENCES_SOURCE) + ";d.newsFallback=" + j(NEWS_FALLBACK) + ";})(window.RM360_DATA);\n",
    }
    os.makedirs(out_path, exist_ok=True)
    for name, body in files.items():
        with open(os.path.join(out_path, name), "w", encoding="utf-8") as f:
            f.write(body)
        print(name, len(body.encode()), "bytes")
    print("OK: table verified for 20 clubs")
    for row in liga:
        print(f"{row['r']:>2} {row['t']} P{row['p']} {row['w']}-{row['d']}-{row['l']} {row['gf']}:{row['ga']} {row['pts']}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "/home/claude/rm360/dist")
