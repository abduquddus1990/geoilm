"""Viktorina savollarini tanlaydi, videoni render qiladi va musiqa/effektlarni qo'shadi."""
import json, random, subprocess, datetime as dt
from pathlib import Path

ROOT = Path(__file__).parent
GEN = ROOT / "quiz_generator"
DATA = ROOT / "data"
OUT = ROOT / "out"
USED = DATA / "used.json"
PLAN = {"oson": 3, "o‘rtacha": 4, "qiyin": 3}   # 10 ta savol, osondan qiyinga
REPEAT_DAYS = 14                                # davlat necha kun takrorlanmasin


def _load_used() -> dict:
    return json.loads(USED.read_text(encoding="utf-8")) if USED.exists() else {}


def pick_questions(seed=None) -> list[dict]:
    rnd = random.Random(seed)
    db = json.loads((DATA / "countries.json").read_text(encoding="utf-8"))
    used = _load_used()
    today = dt.date.today()
    items = []
    for level, count in PLAN.items():
        pool = db[level]
        fresh = [c for c in pool if c[0] not in used
                 or (today - dt.date.fromisoformat(used[c[0]])).days >= REPEAT_DAYS]
        if len(fresh) < count:  # hammasi yaqinda ishlatilgan bo'lsa — eng eskilaridan olamiz
            fresh = sorted(pool, key=lambda c: used.get(c[0], "0000-00-00"))[:max(count * 2, count)]
        for cid, a2, name in rnd.sample(fresh, count):
            items.append({"id": cid, "a2": a2, "name": name, "level": level})
    return items


def mark_used(items: list[dict]) -> None:
    used = _load_used()
    for it in items:
        used[it["id"]] = dt.date.today().isoformat()
    USED.write_text(json.dumps(used, ensure_ascii=False, indent=1), encoding="utf-8")


def _run(cmd, **kw):
    print("$", " ".join(map(str, cmd)))
    subprocess.run(cmd, check=True, **kw)


def build_video(items: list[dict], title="Bu qaysi davlat?", handle="@geoilm") -> Path:
    OUT.mkdir(exist_ok=True)
    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M")
    (GEN / "quiz.js").write_text("window.QUIZ=" + json.dumps(
        {"title": title, "handle": handle, "items": items}, ensure_ascii=False) + ";", encoding="utf-8")

    silent, events, sfx = OUT / "silent.mp4", OUT / "events.json", OUT / "sfx.wav"
    _run(["node", str(GEN / "render.js"), str(silent), str(events)])

    import sys; sys.path.insert(0, str(GEN))
    from sfx import build as build_sfx
    duration = build_sfx(str(events), str(sfx))

    final = OUT / f"geoilm_{stamp}.mp4"
    music = sorted(p for p in (GEN / "music").glob("*") if p.suffix.lower() in {".mp3", ".wav", ".m4a", ".ogg"})
    if music:
        track = random.choice(music)
        print("Musiqa:", track.name)
        fade_st = max(0, duration - 2)
        filt = (f"[2:a]volume=0.16,afade=t=in:d=1,afade=t=out:st={fade_st}:d=2[m];"
                f"[1:a][m]amix=inputs=2:duration=first:normalize=0[a]")
        _run(["ffmpeg", "-y", "-loglevel", "error", "-i", silent, "-i", sfx, "-stream_loop", "-1", "-i", track,
              "-filter_complex", filt, "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
              "-t", f"{duration:.2f}", "-movflags", "+faststart", final])
    else:
        _run(["ffmpeg", "-y", "-loglevel", "error", "-i", silent, "-i", sfx, "-map", "0:v", "-map", "1:a",
              "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", final])
    for p in (silent, sfx):
        p.unlink(missing_ok=True)
    return final


def captions(items: list[dict]) -> dict:
    n = len(items)
    tags = "#geografiya #viktorina #buqaysidavlat #quiz #geoilm #oʻzbekiston #bilim"
    insta = (f"🌍 Bu qaysi davlat? {n} ta savol — osondan qiyinga!\n"
             f"Nechtasini topding? Izohda yoz 👇\n\n"
             f"Har kuni yangi viktorina — obuna bo‘ling: @geoilm\n\n{tags}")
    yt_title = f"Bu qaysi davlat? 🌍 {n} ta savol | Geografiya viktorinasi #shorts"
    answers = "\n".join(f"{i+1}. {it['name']}" for i, it in enumerate(items))
    yt_desc = (f"Xaritada ko‘rsatilgan davlatni 3 soniyada top!\n"
               f"Nechtasini topding? Izohda yoz 👇\n\nJavoblar:\n{answers}\n\n{tags} #shorts")
    return {"instagram": insta, "telegram": insta, "yt_title": yt_title[:100], "yt_desc": yt_desc}


if __name__ == "__main__":
    qs = pick_questions()
    print(json.dumps(qs, ensure_ascii=False, indent=1))
    print(build_video(qs))
