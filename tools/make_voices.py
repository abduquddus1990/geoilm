"""BITTA BUYRUQ bilan ovoz kutubxonasini yasash (Kaggle'ning bepul GPU'sida, avtomatik).

  python tools/make_voices.py --ref C:\\Users\\Surface\\Downloads\\ovoz.m4a

Nima qiladi:
  1) data/voice_lines.json ni yangilaydi va faqat HALI YO'Q iboralarni ajratadi
  2) ovozingni (m4a/mp3/ogg/wav) reference.wav ga aylantiradi
  3) Kaggle'ga yuklaydi, GPU'da Navoiy TTS'ni ishga tushiradi
  4) tugashini kutadi (20–40 daqiqa), natijani quiz_generator/voice/lines/ ga ochadi

Bir martalik sozlash: README → "Kaggle sozlash" bo'limi (kaggle.json).
Keyingi safarlarda (yangi futbolchi/davlat qo'shilsa) --ref shart emas — avvalgi ovoz ishlatiladi.
"""
import argparse, json, shutil, subprocess, sys, time, zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import voice_lines  # noqa: E402

LINES_DIR = ROOT / "quiz_generator" / "voice" / "lines"
REF_SAVED = ROOT / "quiz_generator" / "voice" / "reference.wav"
WORK = ROOT / "out" / "kaggle"
KAGGLE_JSON = Path.home() / ".kaggle" / "kaggle.json"
KAGGLE_TOKEN = Path.home() / ".kaggle" / "access_token"   # yangi turdagi token (KGAT_...)

try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
except ImportError:
    pass


def run(cmd, check=True, capture=False):
    print("$", " ".join(map(str, cmd)))
    r = subprocess.run(list(map(str, cmd)), check=False, text=True, capture_output=capture, encoding="utf-8", errors="replace")
    if check and r.returncode != 0:
        if capture:
            print(r.stdout, r.stderr)
        raise SystemExit(f"Buyruq xato bilan tugadi: {cmd[0]} {cmd[1] if len(cmd) > 1 else ''}")
    return r


def kaggle(*args, check=True, capture=True):
    exe = shutil.which("kaggle")
    base = [exe] if exe else [sys.executable, "-m", "kaggle.cli"]
    return run([*base, *args], check=check, capture=capture)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ref", help="o'z ovozing yozuvi (6–12 s): m4a, mp3, ogg yoki wav")
    ap.add_argument("--emotion", default="happy", help="javoblar uslubi: happy | warm | calm | surprised")
    ap.add_argument("--speed", type=float, default=1.05)
    ap.add_argument("--all", action="store_true", help="bor fayllarni ham qaytadan o'qitish")
    a = ap.parse_args()

    # 0) Tekshiruvlar
    import os
    has_token = KAGGLE_JSON.exists() or KAGGLE_TOKEN.exists() or os.getenv("KAGGLE_API_TOKEN")
    if not has_token:
        raise SystemExit(f"Kaggle tokeni topilmadi: {KAGGLE_TOKEN}\nREADME → 'Kaggle sozlash' bo'limini bajaring.")
    user = os.getenv("KAGGLE_USERNAME") or (json.loads(KAGGLE_JSON.read_text()).get("username") if KAGGLE_JSON.exists() else None)
    if not user:
        raise SystemExit("Kaggle foydalanuvchi nomi yo'q. .env fayliga qo'shing:  KAGGLE_USERNAME=sizning_nomingiz\n"
                         "(nomni kaggle.com → profil sahifasi manzilidan ko'rasiz: kaggle.com/<nom>)")
    if shutil.which("ffmpeg") is None:
        raise SystemExit("ffmpeg topilmadi. O'rnating: winget install Gyan.FFmpeg")

    # 1) Iboralar
    lines = voice_lines.build()
    (ROOT / "data" / "voice_lines.json").write_text(json.dumps(lines, ensure_ascii=False, indent=1), encoding="utf-8")
    todo = lines if a.all else {k: t for k, t in lines.items() if not (LINES_DIR / f"{k}.wav").exists()}
    print(f"Jami {len(lines)} ta ibora, o'qitiladi: {len(todo)} ta")
    if not todo:
        print("Hammasi tayyor — o'qitish shart emas ✅"); return

    # 2) Ovoz namunasi
    REF_SAVED.parent.mkdir(parents=True, exist_ok=True)
    if a.ref:
        run(["ffmpeg", "-y", "-loglevel", "error", "-i", a.ref, "-ac", "1", "-ar", "24000", "-t", "15", REF_SAVED])
    if not REF_SAVED.exists():
        raise SystemExit("Ovoz namunasi yo'q. Birinchi marta --ref bilan ishga tushiring, masalan:\n"
                         "  python tools/make_voices.py --ref C:\\Users\\Surface\\Downloads\\ovoz.m4a")

    # 3) Kaggle dataset (kirish fayllari)
    shutil.rmtree(WORK, ignore_errors=True)
    ds, kd = WORK / "dataset", WORK / "kernel"
    ds.mkdir(parents=True); kd.mkdir(parents=True)
    shutil.copy(REF_SAVED, ds / "reference.wav")
    (ds / "voice_lines.json").write_text(json.dumps(todo, ensure_ascii=False, indent=1), encoding="utf-8")
    (ds / "settings.json").write_text(json.dumps({"emotion": a.emotion, "emotion_title": "happy", "speed": a.speed}))
    ds_slug = f"{user}/geoilm-voice-input"
    (ds / "dataset-metadata.json").write_text(json.dumps(
        {"title": "geoilm-voice-input", "id": ds_slug, "licenses": [{"name": "CC0-1.0"}]}))
    exists = kaggle("datasets", "status", ds_slug, check=False).returncode == 0
    if exists:
        kaggle("datasets", "version", "-p", ds, "-m", time.strftime("%Y-%m-%d %H:%M"), "--dir-mode", "zip")
    else:
        kaggle("datasets", "create", "-p", ds, "--dir-mode", "zip")
    print("Dataset tayyorlanmoqda...")
    for _ in range(40):
        st = kaggle("datasets", "status", ds_slug, check=False).stdout.strip().lower()
        if "ready" in st:
            break
        time.sleep(10)
    time.sleep(20)  # yangi versiya kernel'ga ko'rinishi uchun

    # 4) Kernel (GPU skript)
    k_slug = f"{user}/geoilm-tts"
    shutil.copy(ROOT / "tools" / "kaggle_tts.py", kd / "kaggle_tts.py")
    (kd / "kernel-metadata.json").write_text(json.dumps({
        "id": k_slug, "title": "geoilm-tts", "code_file": "kaggle_tts.py", "language": "python",
        "kernel_type": "script", "is_private": True, "enable_gpu": True, "enable_internet": True,
        "machine_shape": "NvidiaTeslaT4", "dataset_sources": [ds_slug], "competition_sources": [], "kernel_sources": []}))
    kaggle("kernels", "push", "-p", kd)

    # 5) Kutish
    print("Kaggle GPU'da ishlayapti (20–40 daqiqa). Bu oynani yopmang...")
    t0 = time.time()
    while True:
        time.sleep(60)
        st = kaggle("kernels", "status", k_slug, check=False).stdout.lower()
        print(f"  {int((time.time() - t0) / 60)} daq: {st.strip()[-60:]}")
        if "complete" in st:
            break
        if "error" in st or "cancel" in st:
            out = WORK / "log"; out.mkdir(exist_ok=True)
            kaggle("kernels", "output", k_slug, "-p", out, check=False)
            raise SystemExit(f"Kaggle'da xato. Log: {out}  (yoki kaggle.com → Code → geoilm-tts → Logs)")
        if time.time() - t0 > 3 * 3600:
            raise SystemExit("3 soatdan oshdi — kaggle.com → Code → geoilm-tts sahifasini tekshiring")

    # 6) Natija
    out = WORK / "result"; out.mkdir(exist_ok=True)
    kaggle("kernels", "output", k_slug, "-p", out)
    LINES_DIR.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out / "voice_lines.zip") as z:
        z.extractall(LINES_DIR)
    rep = json.loads((out / "report.json").read_text(encoding="utf-8"))
    print(f"\n✅ Tayyor: {rep['ok']} ta ovoz → {LINES_DIR}")
    if rep["suspicious"]:
        print("⚠ Tinglab tekshiring (juda uzun chiqdi):", *[f"  {k} — {t}" for k, t, _ in rep["suspicious"]], sep="\n")
    if rep["failed"]:
        print("❌ O'qitilmadi:", *[f"  {k} — {t}" for k, t, _ in rep["failed"]], sep="\n")


if __name__ == "__main__":
    main()
