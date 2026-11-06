"""Videolarda kerak bo'ladigan barcha ovozli iboralar ro'yxatini yasaydi: data/voice_lines.json

Har bir ibora bir marta (Google Colab'da, bepul GPU bilan) Navoiy TTS orqali o'qitiladi va
quiz_generator/voice/lines/<kalit>.wav bo'lib saqlanadi. Keyin video yasashda GPU kerak emas —
tayyor fayllar shunchaki ulanadi.

  python tools/voice_lines.py            # ro'yxatni yangilash + qaysilari hali o'qitilmaganini ko'rsatish
"""
import json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import generate as g  # noqa: E402

LINES_DIR = ROOT / "quiz_generator" / "voice" / "lines"
OUT = ROOT / "data" / "voice_lines.json"


def build() -> dict:
    lines = {
        "title_davlat": "Bu qaysi davlat?",
        "title_poytaxt": "Poytaxti qaysi?",
        "title_globus": "Bu qaysi davlat?",
        "title_globus_poytaxt": "Poytaxti qaysi?",
        "title_futbolchi": "Bu qaysi futbolchi?",
        "title_viloyat": "Bu qaysi viloyat?",
        "title_tuman": "Bu qaysi tuman?",
        "outro": "Nechtasini topdingiz? Izohda yozing!",
    }
    for lvl in g._load("countries.json").values():
        for cid, _, name in lvl:
            lines[f"ans_davlat_{cid}"] = f"{name}!"
    for lvl in g._load("capitals.json").values():
        for c in lvl:
            lines[f"ans_poytaxt_{c[0]}"] = f"{c[3]}!"
    for k, lvl in g._load("regions.json").items():
        if not k.startswith("_"):
            for rid, name in lvl:
                lines[f"ans_viloyat_{rid}"] = f"{name}!"
    for lvl in g._players().values():
        for p in lvl:
            lines[f"ans_futbolchi_{p['id']}"] = f"{p['name']}!"
    dist = ROOT / "data" / "uz_districts.geojson"
    if dist.exists():
        for f in json.loads(dist.read_text(encoding="utf-8"))["features"]:
            lines[f"ans_tuman_{f['properties']['id']}"] = f"{f['properties']['name']}!"
    return lines


if __name__ == "__main__":
    lines = build()
    OUT.write_text(json.dumps(lines, ensure_ascii=False, indent=1), encoding="utf-8")
    missing = [k for k in lines if not (LINES_DIR / f"{k}.wav").exists()]
    print(f"Jami iboralar: {len(lines)}  |  hali o'qitilmagan: {len(missing)}")
    print(f"Ro'yxat: {OUT}")
