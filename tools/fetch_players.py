"""Wikidata'dan mashhur futbolchilar va ularning klub tarixini olib, data/players_auto.json ga yozadi.

Ishlatish:
  python tools/fetch_players.py                 # ~150 ta futbolchi
  python tools/fetch_players.py --limit 300     # ko'proq
  python tools/fetch_players.py --uz            # O'zbekiston terma jamoasi futbolchilarini ham qo'shadi

Mashhurlik = Wikipedia maqolalari soni (sitelinks). Eng mashhur 1/3 — "oson", keyingisi — "o‘rtacha", qolgani — "qiyin".
Qo'lda yozilgan data/players.json har doim ustun turadi (bir xil id bo'lsa, qo'ldagisi olinadi).
Ma'lumot manbasi: Wikidata (CC0).
"""
import argparse, json, re, sys, time
from pathlib import Path
import requests

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "players_auto.json"
API = "https://query.wikidata.org/sparql"
HEADERS = {"User-Agent": "GeoIlmQuizBot/1.0 (https://github.com/; educational quiz generator)",
           "Accept": "application/sparql-results+json"}

# Yoshlar/dubl jamoalarini chiqarib tashlash
SKIP = re.compile(r"\b(B|C|II|III|U-?\d{2}|Under-\d{2}|Youth|Juvenil|Reserves?|Academy|Primavera|Jong|Castilla|Next Gen|Sub-\d{2})\b", re.I)
# Uzbekcha yozilishi (agar Wikidata'da uz yorlig'i bo'lmasa, inglizchasi qoladi)
UZ_NAME_FIX = {"Cristiano Ronaldo": "Krishtianu Ronaldu", "Kylian Mbappé": "Kilian Mbappe", "Erling Haaland": "Erling Xoland"}


def sparql(query: str, retries=5) -> list[dict]:
    """POST so'rov (uzun so'rovlar GET'da uziladi), sekinlashib qayta urinish."""
    for k in range(retries):
        try:
            r = requests.post(API, data={"query": query, "format": "json"}, headers=HEADERS, timeout=120)
            if r.status_code in (429, 500, 502, 503, 504):
                wait = int(r.headers.get("Retry-After", 0) or 0) or 15 * (k + 1)
                print(f"  server band ({r.status_code}), {wait} s kutamiz..."); time.sleep(wait); continue
            r.raise_for_status()
            return r.json()["results"]["bindings"]
        except (requests.RequestException, ValueError) as e:
            print(f"  so'rov xatosi ({k + 1}/{retries}): {e} — qayta urinish"); time.sleep(10 * (k + 1))
    raise RuntimeError("Wikidata javob bermadi")


def v(row, key, default=None):
    return row[key]["value"] if key in row else default


def qid(uri: str) -> str:
    return uri.rsplit("/", 1)[-1]


def top_players(limit: int, uz_only=False) -> list[dict]:
    extra = "?p wdt:P1532 wd:Q265 ." if uz_only else "FILTER(?links > 40)"
    q = f"""
    SELECT ?p ?pLabel ?pLabelUz ?links ?nat WHERE {{
      ?p wdt:P106 wd:Q937857 ; wikibase:sitelinks ?links ; wdt:P569 ?dob .
      FILTER(YEAR(?dob) >= 1978)
      {extra}
      OPTIONAL {{ ?p wdt:P1532 ?nc . ?nc wdt:P297 ?nat . }}
      OPTIONAL {{ ?p rdfs:label ?pLabelUz . FILTER(LANG(?pLabelUz) = "uz") }}
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
    }} ORDER BY DESC(?links) LIMIT {limit}"""
    seen, out = set(), []
    for r in sparql(q):
        pid = qid(v(r, "p"))
        if pid in seen:
            continue
        seen.add(pid)
        name = v(r, "pLabelUz") or v(r, "pLabel")
        if re.search(r"[А-Яа-яЁё]", name or ""):  # kirillcha bo'lsa — inglizchasini olamiz
            name = v(r, "pLabel")
        out.append({"qid": pid, "name": UZ_NAME_FIX.get(v(r, "pLabel"), name), "links": int(v(r, "links", 0)),
                    "nat": (v(r, "nat") or "").upper()})
    return out


_gb_cache: dict[str, str] = {}


def gb_part(club: str) -> str:
    """Britaniya klubi Angliya/Shotlandiya/Uelsdan qaysi biriga tegishli (kichik alohida so'rov, keshlanadi)."""
    if club not in _gb_cache:
        q = f"""SELECT ?nat WHERE {{
          VALUES (?region ?nat) {{ (wd:Q21 "ENG") (wd:Q22 "SCT") (wd:Q25 "WLS") }}
          wd:{club} wdt:P131+ ?region . }} LIMIT 1"""
        try:
            rows = sparql(q, retries=2)
            _gb_cache[club] = v(rows[0], "nat") if rows else "ENG"
        except RuntimeError:
            _gb_cache[club] = "ENG"
    return _gb_cache[club]


def careers(qids: list[str]) -> dict:
    """Bir nechta futbolchining klublari (milliy terma jamoalarsiz)."""
    values = " ".join(f"wd:{q}" for q in qids)
    q = f"""
    SELECT ?p ?club ?clubLabel ?start ?end ?cc WHERE {{
      VALUES ?p {{ {values} }}
      ?p p:P54 ?st . ?st ps:P54 ?club .
      ?club wdt:P31 wd:Q476028 .
      FILTER NOT EXISTS {{ ?club wdt:P31 wd:Q6979593 }}
      OPTIONAL {{ ?st pq:P580 ?start }}
      OPTIONAL {{ ?st pq:P582 ?end }}
      OPTIONAL {{ ?club wdt:P17 ?country . ?country wdt:P297 ?cc . }}
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
    }}"""
    res: dict[str, list] = {}
    for r in sparql(q):
        label = v(r, "clubLabel", "")
        if not label or SKIP.search(label) or re.match(r"^Q\d+$", label):
            continue
        start = (v(r, "start") or "")[:4]
        if not start.isdigit():
            continue
        end = (v(r, "end") or "")[:4]
        cc = (v(r, "cc") or "").upper()
        if cc == "GB":
            cc = gb_part(qid(v(r, "club")))
        if not cc:
            continue
        res.setdefault(qid(v(r, "p")), []).append((int(start), int(end) if end.isdigit() else None, cc, clean(label)))
    return res


def clean(name: str) -> str:
    n = re.sub(r"\s+(F\.?C\.?|C\.?F\.?|A\.?F\.?C\.?|S\.?C\.?|CP|FK|SK)$", "", name.strip())
    n = re.sub(r"^(FC|FK|F\.C\.|AC|AS|SS|SSC|RC|CA|SL|SC)\s+(?=\S{4,})", "", n)
    return {"Inter Milan": "Inter", "Internazionale": "Inter", "Milan": "Milan"}.get(n, n)


def tidy(clubs: list[tuple]) -> list[list]:
    """Yil bo'yicha tartiblash, ketma-ket bir xil klubni birlashtirish, oxirgi 10 tasini qoldirish."""
    merged = []
    for s, e, cc, name in sorted(set(clubs), key=lambda c: (c[0], c[1] or 9999)):
        if merged and merged[-1][3] == name:
            ps, pe, _, _ = merged[-1]
            merged[-1] = (ps, None if (pe is None or e is None) else max(pe, e), cc, name)
        else:
            merged.append((s, e, cc, name))
    merged = merged[-10:]
    out = []
    for k, (s, e, cc, name) in enumerate(merged):
        yrs = f"{s}–{e}" if e and e != s else (f"{s}–" if k == len(merged) - 1 and not e else str(s))
        out.append([cc, name, yrs])
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=150)
    ap.add_argument("--uz", action="store_true", help="O'zbekiston terma jamoasi futbolchilarini qo'shish")
    a = ap.parse_args()

    print("Mashhur futbolchilar olinmoqda...")
    players = top_players(a.limit)
    if a.uz:
        players += [p for p in top_players(60, uz_only=True) if p["qid"] not in {x["qid"] for x in players}]
    print(f"  {len(players)} ta futbolchi")

    result = []
    for i in range(0, len(players), 8):
        chunk = players[i:i + 8]
        print(f"  klublar: {i + 1}–{i + len(chunk)}")
        try:
            car = careers([p["qid"] for p in chunk])
        except RuntimeError:
            print("  bu guruh o'tkazib yuborildi (Wikidata javob bermadi)")
            continue
        for p in chunk:
            clubs = tidy(car.get(p["qid"], []))
            if len(clubs) >= 3 and p["nat"]:  # kamida 3 ta klub — aks holda viktorina juda oson/qiyin
                result.append({"id": "wd_" + p["qid"], "name": p["name"], "nat": p["nat"], "clubs": clubs, "links": p["links"]})
        time.sleep(2)

    result.sort(key=lambda p: -p["links"])
    n = len(result)
    levels = {"oson": result[: n // 3], "o‘rtacha": result[n // 3: 2 * n // 3], "qiyin": result[2 * n // 3:]}
    for lst in levels.values():
        for p in lst:
            p.pop("links", None)
    levels["_izoh"] = "Wikidata (CC0) dan avtomatik olingan. Xato topsangiz, to'g'ri variantni data/players.json ga qo'lda yozing."
    OUT.write_text(json.dumps(levels, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Tayyor: {OUT}  (jami {n} ta: {', '.join(f'{k}={len(v)}' for k, v in levels.items() if not k.startswith('_'))})")


if __name__ == "__main__":
    sys.exit(main())
