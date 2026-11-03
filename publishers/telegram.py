"""Telegram: videoni kanalga yuborish va admin'ga hisobot."""
import os, requests

API = "https://api.telegram.org/bot{token}/{method}"


def send_video(path: str, caption: str, chat_id: str | None = None) -> dict:
    token, chat_id = os.environ["TG_BOT_TOKEN"], chat_id or os.environ["TG_CHAT_ID"]
    with open(path, "rb") as f:
        r = requests.post(API.format(token=token, method="sendVideo"),
                          data={"chat_id": chat_id, "caption": caption[:1024], "supports_streaming": "true",
                                "width": 1080, "height": 1920},
                          files={"video": f}, timeout=300)
    r.raise_for_status()
    return r.json()


def notify(text: str) -> None:
    """Admin chatiga qisqa xabar (TG_ADMIN_CHAT_ID bo'lmasa — jim o'tadi)."""
    token, chat = os.getenv("TG_BOT_TOKEN"), os.getenv("TG_ADMIN_CHAT_ID")
    if token and chat:
        try:
            requests.post(API.format(token=token, method="sendMessage"),
                          data={"chat_id": chat, "text": text[:4000]}, timeout=30)
        except requests.RequestException:
            pass


def _esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def send_manual(path: str, cap: dict, chat_ids: list[str]) -> None:
    """Qo'lda joylash uchun: videoni va nusxa olinadigan matnlarni (YouTube sarlavha/tavsif, Instagram) yuboradi."""
    token = os.environ["TG_BOT_TOKEN"]
    for chat in chat_ids:
        with open(path, "rb") as f:
            r = requests.post(API.format(token=token, method="sendVideo"),
                              data={"chat_id": chat, "caption": "🌍 GeoIlm — tayyor video. Matnlar pastda 👇 (bosib nusxa oling)",
                                    "supports_streaming": "true", "width": 1080, "height": 1920},
                              files={"video": f}, timeout=600)
        r.raise_for_status()
        for label, text in (("▶️ YouTube sarlavha", cap["yt_title"]), ("▶️ YouTube tavsif", cap["yt_desc"]),
                            ("📸 Instagram matni", cap["instagram"])):
            requests.post(API.format(token=token, method="sendMessage"), timeout=30, data={
                "chat_id": chat, "parse_mode": "HTML",
                "text": f"<b>{label}</b>\n<pre>{_esc(text)}</pre>"[:4096]}).raise_for_status()
