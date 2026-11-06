"""GeoIlm: savol tanlash, render, musiqa/ovoz qo'shish.

Formatlar (MODE):
  davlat     — "Bu qaysi davlat?"  (xaritada kontur)
  poytaxt    — "Poytaxti qaysi?"   (davlat ko'rsatiladi, poytaxt ochiladi)
  futbolchi  — "Bu qaysi futbolchi?" (klublar yo'li bo'yicha)
  viloyat    — "Bu qaysi viloyat?" (O'zbekiston viloyatlari)
"""
import json, os, random, subprocess, sys, datetime as dt
from pathlib import Path

ROOT = Path(__file__).parent
GEN = ROOT / "quiz_generator"
DATA = ROOT / "data"
OUT = ROOT / "out"
USED = DATA / "used.json"
REPEAT_DAYS = 14

MODES = {
    "davlat":    {"title": "Bu qaysi davlat?",    "page": "index.html",  "plan": {"oson": 3, "o‘rtacha": 4, "qiyin": 3}},
    "poytaxt":   {"title": "Poytaxti qaysi?",     "page": "index.html",  "plan": {"oson": 3, "o‘rtacha": 4, "qiyin": 3}},
    "futbolchi": {"title": "Bu qaysi futbolchi?", "page": "player.html", "plan": {"oson": 2, "o‘rtacha": 2, "qiyin": 2}},
    "viloyat":   {"title": "Bu qaysi viloyat?",   "page": "index.html",  "plan": {"oson": 3, "o‘rtacha": 4, "qiyin": 3}},
    "globus":    {"title": "Bu qaysi davlat?",    "page": "globe.html",  "plan": {"oson": 3, "o‘rtacha": 4, "qiyin": 3}},
    "globus_poytaxt": {"title": "Poytaxti qaysi?", "page": "globe.html", "plan": {"oson": 3, "o‘rtacha": 4, "qiyin": 3}},
    "tuman":     {"title": "Bu qaysi tuman?",     "page": "index.html",  "plan": {"qiyin": 8}},
}
# Avtomatik jadval: kuniga 3 ta slot, TOSHKENT vaqti bilan (06:20, 19:00, 21:00). Formatlar navbat bilan
# almashadi, shuning uchun har kuni boshqacha kombinatsiya chiqadi.
SLOT_HOURS_TASHKENT = [6, 19, 21]
ROTATION = ["globus", "futbolchi", "globus_poytaxt", "davlat", "tuman", "viloyat", "poytaxt"]

STYLE = {  # xarita ko'rinishi: theme = notebook | clean | pastel | chalk
    "theme": os.getenv("GEOILM_THEME", "clean"),
    "globe": os.getenv("GEOILM_GLOBE", "1") == "1",
    "labels": os.getenv("GEOILM_LABELS", "0") == "1",
    "zoom": float(os.getenv("GEOILM_ZOOM", "0.6")),
}


def mode_for_now(slot: int | None = None) -> str:
    """Toshkent vaqti (UTC+5) bo'yicha: slot = 0 (06:20), 1 (19:00), 2 (21:00). Bermasa — hozirgi soatga eng yaqini."""
    now = dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=5)
    if slot is None:
        slot = min(range(len(SLOT_HOURS_TASHKENT)), key=lambda i: abs(SLOT_HOURS_TASHKENT[i] - now.hour))
    rot = [m for m in ROTATION if m != "tuman" or (DATA / "uz_districts.geojson").exists()]
    n, base = len(rot), now.date().toordinal() * len(SLOT_HOURS_TASHKENT)
    shift = base // n if n % 3 == 0 else 0   # n 3 ga bo'linsa kombinatsiyalar 2 kunda takrorlanardi
    return rot[(base + shift + slot) % n]


def _players() -> dict:
    """Qo'lda yozilgan players.json + Wikidata'dan olingan players_auto.json (qo'ldagi ustun)."""
    db = {k: v for k, v in _load("players.json").items() if not k.startswith("_")}
    auto = DATA / "players_auto.json"
    if auto.exists():
        known = {p["id"] for lvl in db.values() for p in lvl}
        for lvl, lst in json.loads(auto.read_text(encoding="utf-8")).items():
            if lvl.startswith("_"):
                continue
            db.setdefault(lvl, []).extend(p for p in lst if p["id"] not in known)
    return db


def _load(name):
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def _used() -> dict:
    return json.loads(USED.read_text(encoding="utf-8")) if USED.exists() else {}


def _key(mode, item_id):
    return item_id if mode in ("davlat", "globus") else f"{mode}:{item_id}"


DISTRICTS = DATA / "uz_districts.geojson"


def _region_names() -> dict:
    return {iso: name for k, v in _load("regions.json").items() if not k.startswith("_") for iso, name in v}


def pick_district_region(seed=None, region=None) -> str:
    """Tuman formati uchun viloyat: eng uzoq vaqt ishlatilmagani (yoki --region bilan berilgani)."""
    if region:
        return region
    used = _used()
    feats = json.loads(DISTRICTS.read_text(encoding="utf-8"))["features"]
    counts = {}
    for f in feats:
        counts[f["properties"]["region"]] = counts.get(f["properties"]["region"], 0) + 1
    regs = [r for r, n in counts.items() if n >= 5]
    random.Random(seed).shuffle(regs)
    return min(regs, key=lambda r: used.get(f"tuman_region:{r}", "0000-00-00"))


def pick_questions(mode="davlat", seed=None, region=None) -> list[dict]:
    rnd, used, today = random.Random(seed), _used(), dt.date.today()
    if mode == "tuman":
        if not DISTRICTS.exists():
            raise SystemExit("Tumanlar ma'lumoti yo'q. Avval:  python tools/fetch_districts.py")
        reg = pick_district_region(seed, region)
        feats = [f for f in json.loads(DISTRICTS.read_text(encoding="utf-8"))["features"] if f["properties"]["region"] == reg]
        pool = [{"id": f["properties"]["id"], "a2": "UZ", "name": f["properties"]["name"], "level": "qiyin", "region": reg} for f in feats]
        pool.sort(key=lambda c: used.get(_key(mode, c["id"]), "0000-00-00"))
        return rnd.sample(pool[:max(8, len(pool) // 2 + 4)], min(8, len(pool)))
    if mode in ("davlat", "globus"):
        db = {k: [{"id": c[0], "a2": c[1], "name": c[2]} for c in v] for k, v in _load("countries.json").items()}
    elif mode in ("poytaxt", "globus_poytaxt"):
        db ={k: [{"id": c[0], "a2": c[1], "name": c[2], "cap": c[3], "lat": c[4], "lon": c[5]} for c in v]
              for k, v in _load("capitals.json").items()}
    elif mode == "viloyat":
        db = {k: [{"id": c[0], "a2": "UZ", "name": c[1]} for c in v]
              for k, v in _load("regions.json").items() if not k.startswith("_")}
    else:
        db = _players()
    items = []
    for level, count in MODES[mode]["plan"].items():
        pool = db[level]
        fresh = [c for c in pool if _key(mode, c["id"]) not in used
                 or (today - dt.date.fromisoformat(used[_key(mode, c["id"])])).days >= REPEAT_DAYS]
        if len(fresh) < count:
            fresh = sorted(pool, key=lambda c: used.get(_key(mode, c["id"]), "0000-00-00"))[:max(count, len(pool))]
        for c in rnd.sample(fresh, min(count, len(fresh))):
            items.append({**c, "level": level})
    return items


def mark_used(mode: str, items: list[dict]) -> None:
    used = _used()
    if mode == "tuman" and items:
        used[f"tuman_region:{items[0]['region']}"] = dt.date.today().isoformat()
    for it in items:
        used[_key(mode, it["id"])] = dt.date.today().isoformat()
    USED.write_text(json.dumps(used, ensure_ascii=False, indent=1), encoding="utf-8")


def _run(cmd):
    print("$", " ".join(map(str, cmd)))
    subprocess.run(list(map(str, cmd)), check=True)


def _names() -> dict:
    return {c[0]: c[2] for lvl in _load("countries.json").values() for c in lvl}


def build_video(mode: str, items: list[dict], handle="@geoilm") -> Path:
    OUT.mkdir(exist_ok=True)
    cfg = MODES[mode]
    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M")
    style = dict(STYLE, globe=False, labels=False) if mode in ("viloyat", "tuman") else STYLE
    quiz = {"title": cfg["title"], "handle": handle, "items": items, "style": style, "names": _names(),
            "mode": {"poytaxt": "capital", "globus_poytaxt": "capital", "viloyat": "region"}.get(mode, mode)}
    if mode == "viloyat":
        quiz["regions"] = json.loads((DATA / "uz_regions.geojson").read_text(encoding="utf-8"))
    if mode == "tuman":
        reg = items[0]["region"]
        quiz["mode"] = "district"
        quiz["regions"] = {"type": "FeatureCollection", "features": [
            f for f in json.loads(DISTRICTS.read_text(encoding="utf-8"))["features"] if f["properties"]["region"] == reg]}
        quiz["area"] = next(f for f in json.loads((DATA / "uz_regions.geojson").read_text(encoding="utf-8"))["features"]
                            if f["properties"]["shapeISO"] == reg)
        quiz["subtitle"] = _region_names().get(reg, "")
    (GEN / "quiz.js").write_text("window.QUIZ=" + json.dumps(quiz, ensure_ascii=False) + ";", encoding="utf-8")

    silent, events, sfx = OUT / "silent.mp4", OUT / "events.json", OUT / "sfx.wav"
    _run(["node", GEN / "render.js", silent, events, cfg["page"]])

    # ovoz: 1) voice/<mode>.mp3 — o'zing yozgan savol ovozi; 2) voice/lines/*.wav — Navoiy TTS kutubxonasi
    vtmp = OUT / "vtmp"; vtmp.mkdir(exist_ok=True)

    def to_wav(src, name):
        dst = vtmp / f"{name}.wav"
        _run(["ffmpeg", "-y", "-loglevel", "error", "-i", src, "-ac", "1", "-ar", "44100", dst])
        return str(dst)

    lines = GEN / "voice" / "lines"
    title_src = next((GEN / "voice" / f"{mode}.{e}" for e in ("mp3", "m4a", "ogg", "opus", "wav")
                      if (GEN / "voice" / f"{mode}.{e}").exists()), None) or \
        (lines / f"title_{mode}.wav" if (lines / f"title_{mode}.wav").exists() else None)
    voice_wav = to_wav(title_src, "title") if title_src else None
    answers = []
    for i, it in enumerate(items):
        vmode = {"globus": "davlat", "globus_poytaxt": "poytaxt"}.get(mode, mode)
        f = lines / f"ans_{vmode}_{it['id']}.wav"
        answers.append(to_wav(f, f"ans{i}") if f.exists() else None)
    outro_wav = to_wav(lines / "outro.wav", "outro") if (lines / "outro.wav").exists() else None
    tts_used = any(answers) or bool(outro_wav) or (title_src is not None and title_src.parent == lines)
    print(f"Ovoz: savol={'bor' if voice_wav else 'yo‘q'}, javoblar={sum(1 for a in answers if a)}/{len(items)}, yakun={'bor' if outro_wav else 'yo‘q'}")
    (OUT / "tts_used.flag").write_text("1" if tts_used else "0")

    sys.path.insert(0, str(GEN))
    from sfx import build as build_sfx
    duration = build_sfx(str(events), str(sfx), voice_wav, answers, outro_wav)

    final = OUT / f"geoilm_{mode}_{stamp}.mp4"
    # fon musiqasi: avval music/<mode>/ yoki music/ dagi o'z treklaring, bo'lmasa — original trek generatsiya qilinadi
    own = [p for d in (GEN / "music" / mode, GEN / "music") if d.exists()
           for p in sorted(d.glob("*")) if p.suffix.lower() in {".mp3", ".wav", ".m4a", ".ogg"}]
    if own:
        track, vol = random.choice(own), 0.14
        print("Musiqa (o'zingniki):", track.name)
    else:
        from music import generate as gen_music
        track, vol = OUT / "music.wav", 0.20
        gen_music("sport" if mode == "futbolchi" else "geo", duration + 1, str(track), random.randrange(10**6))
        print("Musiqa: original generatsiya")
    filt = (f"[2:a]volume={vol},afade=t=in:d=1,afade=t=out:st={max(0, duration - 2):.2f}:d=2[m];"
            f"[1:a][m]amix=inputs=2:duration=first:normalize=0[a]")
    _run(["ffmpeg", "-y", "-loglevel", "error", "-i", silent, "-i", sfx, "-stream_loop", "-1", "-i", track,
          "-filter_complex", filt, "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
          "-t", f"{duration:.2f}", "-movflags", "+faststart", final])
    if not own:
        Path(track).unlink(missing_ok=True)
    import shutil
    shutil.rmtree(vtmp, ignore_errors=True)
    for p in (silent, sfx):
        Path(p).unlink(missing_ok=True)
    return final


def captions(mode: str, items: list[dict]) -> dict:
    n = len(items)
    base = "#geoilm #viktorina #quiz #bilim #oʻzbekiston"
    if mode == "futbolchi":
        head, tags, what = "⚽ Bu qaysi futbolchi? Klublaridan toping!", "#futbol #football #futbolchi " + base, "futbolchi"
        answers = "\n".join(f"{i+1}. {it['name']}" for i, it in enumerate(items))
    elif mode == "tuman":
        rname = _region_names().get(items[0]["region"], "") if items else ""
        head, tags, what = f"🇺🇿 {rname}: bu qaysi tuman?", "#oʻzbekiston #tumanlar #geografiya " + base, "tuman"
        answers = "\n".join(f"{i+1}. {it['name']}" for i, it in enumerate(items))
    elif mode == "viloyat":
        head, tags, what = "🇺🇿 Bu qaysi viloyat?", "#oʻzbekiston #viloyatlar #geografiya " + base, "viloyat"
        answers = "\n".join(f"{i+1}. {it['name']}" for i, it in enumerate(items))
    elif mode in ("poytaxt", "globus_poytaxt"):
        head, tags, what = "🏛 Poytaxti qaysi shahar?", "#geografiya #poytaxt " + base, "poytaxt"
        answers = "\n".join(f"{i+1}. {it['name']} — {it['cap']}" for i, it in enumerate(items))
    else:  # davlat, globus
        head, tags, what = "🌍 Bu qaysi davlat?", "#geografiya #buqaysidavlat " + base, "davlat"
        answers = "\n".join(f"{i+1}. {it['name']}" for i, it in enumerate(items))
    insta = f"{head} {n} ta savol — osondan qiyinga!\nNechtasini topdingiz? Izohda yozing 👇\n\nHar kuni yangi viktorina — obuna bo‘ling: @geoilm\n\n{tags}"
    title = {"davlat": "Bu qaysi davlat? 🌍", "poytaxt": "Poytaxti qaysi? 🏛", "futbolchi": "Bu qaysi futbolchi? ⚽",
             "viloyat": "Bu qaysi viloyat? 🇺🇿", "tuman": "Bu qaysi tuman? 🇺🇿", "globus": "Globusdan toping: bu qaysi davlat? 🌍",
             "globus_poytaxt": "Poytaxti qaysi? 🌍🏛"}[mode]
    credit = {"viloyat": "\n\nXarita: geoBoundaries, © OpenStreetMap hissadorlari (ODbL)",
              "tuman": "\n\nXarita: © OpenStreetMap hissadorlari (ODbL)"}.get(mode, "")
    flag = OUT / "tts_used.flag"
    if flag.exists() and flag.read_text() == "1":
        credit += "\nOvoz: Navoiy TTS (sun’iy intellekt)"
    yt_desc = f"{head}\n3 soniyada javob bering! Nechta {what}ni topdingiz? Izohda yozing 👇\n\nJavoblar:\n{answers}{credit}\n\n{tags} #shorts"
    if credit:
        insta += credit
    return {"instagram": insta, "telegram": insta, "yt_title": f"{title} {n} ta savol #shorts"[:100], "yt_desc": yt_desc}


if __name__ == "__main__":
    m = sys.argv[1] if len(sys.argv) > 1 else "davlat"
    qs = pick_questions(m)
    print(json.dumps(qs, ensure_ascii=False, indent=1))
    print(build_video(m, qs))
