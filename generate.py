"""GeoIlm: savol tanlash, render, musiqa/ovoz qo'shish.

Formatlar (MODE):
  davlat     — "Bu qaysi davlat?"  (xaritada kontur)
  poytaxt    — "Poytaxti qaysi?"   (davlat ko'rsatiladi, poytaxt ochiladi)
  futbolchi  — "Bu qaysi futbolchi?" (klublar yo'li bo'yicha)
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
}
# Qo'lda ishga tushirishda (--mode berilmasa) soatga qarab; rejali ishda format workflow'dan keladi
SCHEDULE = {1: "davlat", 14: "futbolchi", 16: "poytaxt"}   # 06:20, 19:00, 21:00 Toshkent

STYLE = {  # xarita ko'rinishi: theme = notebook | clean | pastel | chalk
    "theme": os.getenv("GEOILM_THEME", "clean"),
    "globe": os.getenv("GEOILM_GLOBE", "1") == "1",
    "labels": os.getenv("GEOILM_LABELS", "0") == "1",
    "zoom": float(os.getenv("GEOILM_ZOOM", "0.6")),
}


def mode_for_now() -> str:
    h = dt.datetime.utcnow().hour
    return SCHEDULE.get(min(SCHEDULE, key=lambda k: abs(k - h)))


def _load(name):
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def _used() -> dict:
    return json.loads(USED.read_text(encoding="utf-8")) if USED.exists() else {}


def _key(mode, item_id):
    return item_id if mode == "davlat" else f"{mode}:{item_id}"


def pick_questions(mode="davlat", seed=None) -> list[dict]:
    rnd, used, today = random.Random(seed), _used(), dt.date.today()
    if mode == "davlat":
        db = {k: [{"id": c[0], "a2": c[1], "name": c[2]} for c in v] for k, v in _load("countries.json").items()}
    elif mode == "poytaxt":
        db = {k: [{"id": c[0], "a2": c[1], "name": c[2], "cap": c[3], "lat": c[4], "lon": c[5]} for c in v]
              for k, v in _load("capitals.json").items()}
    else:
        db = {k: v for k, v in _load("players.json").items() if not k.startswith("_")}
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
    for it in items:
        used[_key(mode, it["id"])] = dt.date.today().isoformat()
    USED.write_text(json.dumps(used, ensure_ascii=False, indent=1), encoding="utf-8")


def _run(cmd):
    print("$", " ".join(map(str, cmd)))
    subprocess.run(list(map(str, cmd)), check=True)


def _names() -> dict:
    return {c[0]: c[2] for f in ("countries.json", "capitals.json") for lvl in _load(f).values() for c in lvl}


def build_video(mode: str, items: list[dict], handle="@geoilm") -> Path:
    OUT.mkdir(exist_ok=True)
    cfg = MODES[mode]
    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M")
    quiz = {"title": cfg["title"], "handle": handle, "items": items, "style": STYLE, "names": _names(),
            "mode": "capital" if mode == "poytaxt" else mode}
    (GEN / "quiz.js").write_text("window.QUIZ=" + json.dumps(quiz, ensure_ascii=False) + ";", encoding="utf-8")

    silent, events, sfx = OUT / "silent.mp4", OUT / "events.json", OUT / "sfx.wav"
    _run(["node", GEN / "render.js", silent, events, cfg["page"]])

    # ovoz: quiz_generator/voice/<mode>.(mp3|m4a|ogg|wav) bo'lsa — har savol boshida qo'yiladi
    voice_wav = None
    for ext in ("mp3", "m4a", "ogg", "opus", "wav"):
        v = GEN / "voice" / f"{mode}.{ext}"
        if v.exists():
            voice_wav = OUT / "voice.wav"
            _run(["ffmpeg", "-y", "-loglevel", "error", "-i", v, "-ac", "1", "-ar", "44100", voice_wav])
            break

    sys.path.insert(0, str(GEN))
    from sfx import build as build_sfx
    duration = build_sfx(str(events), str(sfx), str(voice_wav) if voice_wav else None)

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
    for p in (silent, sfx, voice_wav):
        if p:
            Path(p).unlink(missing_ok=True)
    return final


def captions(mode: str, items: list[dict]) -> dict:
    n = len(items)
    base = "#geoilm #viktorina #quiz #bilim #oʻzbekiston"
    if mode == "futbolchi":
        head, tags, what = "⚽ Bu qaysi futbolchi? Klublaridan toping!", "#futbol #football #futbolchi " + base, "futbolchi"
        answers = "\n".join(f"{i+1}. {it['name']}" for i, it in enumerate(items))
    elif mode == "poytaxt":
        head, tags, what = "🏛 Poytaxti qaysi shahar?", "#geografiya #poytaxt " + base, "poytaxt"
        answers = "\n".join(f"{i+1}. {it['name']} — {it['cap']}" for i, it in enumerate(items))
    else:
        head, tags, what = "🌍 Bu qaysi davlat?", "#geografiya #buqaysidavlat " + base, "davlat"
        answers = "\n".join(f"{i+1}. {it['name']}" for i, it in enumerate(items))
    insta = f"{head} {n} ta savol — osondan qiyinga!\nNechtasini topdingiz? Izohda yozing 👇\n\nHar kuni yangi viktorina — obuna bo‘ling: @geoilm\n\n{tags}"
    title = {"davlat": "Bu qaysi davlat? 🌍", "poytaxt": "Poytaxti qaysi? 🏛", "futbolchi": "Bu qaysi futbolchi? ⚽"}[mode]
    yt_desc = f"{head}\n3 soniyada javob bering! Nechta {what}ni topdingiz? Izohda yozing 👇\n\nJavoblar:\n{answers}\n\n{tags} #shorts"
    return {"instagram": insta, "telegram": insta, "yt_title": f"{title} {n} ta savol #shorts"[:100], "yt_desc": yt_desc}


if __name__ == "__main__":
    m = sys.argv[1] if len(sys.argv) > 1 else "davlat"
    qs = pick_questions(m)
    print(json.dumps(qs, ensure_ascii=False, indent=1))
    print(build_video(m, qs))
