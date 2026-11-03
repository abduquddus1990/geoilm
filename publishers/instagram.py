"""Instagram: Reels joylash (Graph API, resumable upload — videoni tashqi hostingga qo'yish shart emas)."""
import os, time, requests

HOST = os.getenv("IG_GRAPH_HOST", "graph.instagram.com")   # Facebook Login bo'lsa: graph.facebook.com
VER = os.getenv("IG_API_VERSION", "v23.0")


def _api(path):
    return f"https://{HOST}/{VER}/{path}"


def upload_reel(path: str, caption: str) -> str:
    token, user = os.environ["IG_TOKEN"], os.environ["IG_USER_ID"]

    # 1) konteyner yaratish
    r = requests.post(_api(f"{user}/media"), data={
        "media_type": "REELS", "upload_type": "resumable", "caption": caption,
        "share_to_feed": "true", "access_token": token}, timeout=60)
    r.raise_for_status()
    cid = r.json()["id"]
    upload_uri = r.json().get("uri") or f"https://rupload.facebook.com/ig-api-upload/{VER}/{cid}"

    # 2) faylni to'g'ridan-to'g'ri yuklash
    size = os.path.getsize(path)
    with open(path, "rb") as f:
        u = requests.post(upload_uri, data=f, timeout=600, headers={
            "Authorization": f"OAuth {token}", "offset": "0", "file_size": str(size)})
    u.raise_for_status()

    # 3) Instagram videoni qayta ishlashini kutish
    for _ in range(60):  # ~10 daqiqagacha
        s = requests.get(_api(cid), params={"fields": "status_code,status", "access_token": token}, timeout=30).json()
        code = s.get("status_code")
        if code == "FINISHED":
            break
        if code in ("ERROR", "EXPIRED"):
            raise RuntimeError(f"Instagram qayta ishlash xatosi: {s}")
        time.sleep(10)
    else:
        raise TimeoutError("Instagram videoni 10 daqiqada tayyorlamadi")

    # 4) e'lon qilish
    p = requests.post(_api(f"{user}/media_publish"), data={"creation_id": cid, "access_token": token}, timeout=60)
    p.raise_for_status()
    media_id = p.json()["id"]
    link = requests.get(_api(media_id), params={"fields": "permalink", "access_token": token}, timeout=30).json()
    return link.get("permalink", media_id)
