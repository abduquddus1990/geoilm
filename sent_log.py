"""Kunlik yuborilganlar jurnali (data/sent.json): har format kuniga bir martadan ortiq yuborilmasligi uchun.

  python sent_log.py check <format>   # GITHUB_OUTPUT uchun "skip=true|false" chiqaradi
"""
import json, sys, datetime as dt
from pathlib import Path

LOG = Path(__file__).parent / "data" / "sent.json"


def today() -> str:
    return (dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=5)).date().isoformat()   # Toshkent sanasi


def _load() -> dict:
    return json.loads(LOG.read_text(encoding="utf-8")) if LOG.exists() else {}


def was_sent(mode: str) -> bool:
    return mode in _load().get(today(), [])


def record(mode: str) -> None:
    d = _load()
    d[today()] = sorted(set(d.get(today(), [])) | {mode})
    LOG.write_text(json.dumps({k: d[k] for k in sorted(d)[-14:]}, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__" and len(sys.argv) == 3 and sys.argv[1] == "check":
    print("skip=" + ("true" if was_sent(sys.argv[2]) else "false"))
