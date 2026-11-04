"""GeoIlm avtomat: savol tanlash → video → YouTube / Instagram / Telegram.

Misollar:
  python run_quiz.py                     # hammasi
  python run_quiz.py --no-publish        # faqat video yasash (sinov)
  python run_quiz.py --only telegram     # faqat Telegram'ga
"""
import argparse, os, sys, traceback
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from generate import pick_questions, build_video, captions, mark_used, mode_for_now, MODES
from publishers import telegram
import sent_log

PLATFORMS = ["youtube", "instagram", "telegram"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-publish", action="store_true")
    ap.add_argument("--only", default=",".join(PLATFORMS), help="youtube,instagram,telegram")
    ap.add_argument("--manual", action="store_true",
                    help="avto-joylamasdan, videoni va matnlarni TG_MANUAL_CHAT_IDS ga yuborish (qo'lda joylash uchun)")
    ap.add_argument("--mode", choices=list(MODES), help="davlat | poytaxt | futbolchi (bo'sh bo'lsa — soatga qarab)")
    ap.add_argument("--keep", action="store_true", help="videoni joylagandan keyin o'chirmaslik")
    args = ap.parse_args()

    mode = args.mode or mode_for_now()
    print("Format:", mode)
    items = pick_questions(mode)
    print("Savollar:", ", ".join(f"{i['name']} ({i['level']})" for i in items))
    video = build_video(mode, items)
    print("Video:", video)
    if args.no_publish:
        return 0

    cap = captions(mode, items)
    if args.manual:
        chats = [c.strip() for c in os.environ["TG_MANUAL_CHAT_IDS"].split(",") if c.strip()]
        telegram.send_manual(str(video), cap, chats)
        mark_used(mode, items)
        sent_log.record(mode)
        print("Botga yuborildi:", ", ".join(chats))
        if not args.keep:
            Path(video).unlink(missing_ok=True)
        return 0
    results, ok = [], 0
    targets = [p.strip() for p in args.only.split(",") if p.strip()]
    for p in targets:
        try:
            if p == "youtube":
                from publishers import youtube
                link = youtube.upload(str(video), cap["yt_title"], cap["yt_desc"])
            elif p == "instagram":
                from publishers import instagram
                link = instagram.upload_reel(str(video), cap["instagram"])
            elif p == "telegram":
                telegram.send_video(str(video), cap["telegram"])
                link = "yuborildi"
            else:
                continue
            ok += 1
            results.append(f"✅ {p}: {link}")
        except Exception as e:
            traceback.print_exc()
            results.append(f"❌ {p}: {type(e).__name__}: {e}")

    if ok:
        mark_used(mode, items)        # kamida bitta platformaga chiqqan bo'lsa — davlatlar "ishlatilgan"
    report = f"GeoIlm hisobot ({mode})\n" + "\n".join(results)
    print(report)
    telegram.notify(report)
    if not args.keep and ok == len(targets):
        Path(video).unlink(missing_ok=True)
    return 0 if ok == len(targets) else 1


if __name__ == "__main__":
    sys.exit(main())
