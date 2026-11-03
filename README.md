# GeoIlm — "Bu qaysi davlat?" avtomat video zavodi

Kuniga 3 marta (09:00 / 14:00 / 20:00, Toshkent vaqti) avtomatik:

1. 10 ta davlat tanlanadi: 3 ta oson, 4 ta o‘rtacha, 3 ta qiyin. Bir davlat 14 kun ichida takrorlanmaydi.
2. Daftar uslubidagi 1080×1920 video render qilinadi (taymer, effektlar, ixtiyoriy fon musiqasi).
3. Video **YouTube Shorts**, **Instagram Reels (@geoilm)** va **Telegram** kanaliga joylanadi.
4. Telegram'dagi admin chatingga hisobot keladi: ✅ yoki ❌ va havolalar.

```
geoilm-auto/
├─ run_quiz.py            ← asosiy skript (hammasini boshqaradi)
├─ generate.py            ← savol tanlash + video yig'ish
├─ get_youtube_token.py   ← YouTube kalitini olish (bir marta)
├─ publishers/            ← youtube.py · instagram.py · telegram.py
├─ quiz_generator/        ← xarita animatsiyasi (HTML + Playwright render)
│  └─ music/              ← fon musiqalari (.mp3) shu yerga
├─ data/countries.json    ← davlatlar bazasi (qo'shish/o'zgartirish mumkin)
├─ data/used.json         ← ishlatilgan davlatlar (avtomatik)
└─ .github/workflows/geoilm.yml ← jadval (GitHub Actions)
```

---

## 1-qadam. Kompyuterni tayyorlash (Windows)

PowerShell'ni oching va quyidagilarni o'rnating:

```powershell
winget install Python.Python.3.11
winget install OpenJS.NodeJS.LTS
winget install Gyan.FFmpeg
winget install Git.Git
winget install Microsoft.VisualStudioCode
```

O'rnatgandan keyin kompyuterni qayta yoqing (PATH yangilanishi uchun).

VS Code kengaytmalari (`Ctrl+Shift+X`): **Python**, **GitHub Actions**, **Claude Code** (ixtiyoriy, kodni o'zgartirishda yordam beradi).

## 2-qadam. Loyihani ochish

1. ZIP'ni oching, masalan `C:\Users\Surface\Desktop\geoilm-auto` papkasiga.
2. VS Code: `File → Open Folder` → shu papkani tanlang.
3. Terminalni oching (`Ctrl + ~`) va ishga tushiring:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
npm install --prefix quiz_generator
npx --prefix quiz_generator playwright install chromium
```

## 3-qadam. Birinchi sinov (joylamasdan)

```powershell
python run_quiz.py --no-publish
```

7–10 daqiqadan keyin `out\geoilm_YYYYMMDD_HHMM.mp4` paydo bo'ladi. Uni ko'rib chiqing.

Fon musiqasi uchun `quiz_generator\music\` papkasiga 3–6 ta **mualliflik huquqidan xoli** `.mp3` qo'ying (YouTube Audio Library, Pixabay Music). Har video tasodifiy birini oladi. Papka bo'sh bo'lsa, video faqat effekt tovushlari bilan chiqadi.

## 4-qadam. Kalitlar (`.env`)

`.env.example` faylidan nusxa olib, nomini `.env` qiling va quyidagilarni to'ldiring.

**Telegram**

- `TG_BOT_TOKEN` — Zanjir botingning tokeni (@BotFather).
- `TG_CHAT_ID` — kanal (`@username` yoki `-100...`). Bot kanalga **admin** qilib qo'shilgan bo'lishi shart.
- `TG_ADMIN_CHAT_ID` — o'zingning Telegram ID raqaming, hisobot shu yerga keladi (@userinfobot'dan bilib olasan).

**YouTube**

1. [console.cloud.google.com](https://console.cloud.google.com) → yangi loyiha → **YouTube Data API v3**'ni yoqing.
2. `OAuth consent screen` → External → o'zingni **Test user** qilib qo'shing → keyin **Publish app** (aks holda token 7 kunda o'ladi).
3. `Credentials → Create OAuth client ID → Desktop app` → JSON'ni yuklab oling va `client_secret.json` nomi bilan loyiha papkasiga qo'ying.
4. Quyidagini ishga tushiring, brauzerda kanal akkauntini tanlang:

```powershell
python get_youtube_token.py
```

Chiqqan uchta qiymatni (`YT_CLIENT_ID`, `YT_CLIENT_SECRET`, `YT_REFRESH_TOKEN`) `.env`'ga yozing.

**Instagram (@geoilm)**

1. Akkaunt **Business** turida bo'lsin.
2. [developers.facebook.com](https://developers.facebook.com) → App → **Instagram API with Instagram Login** → `instagram_business_basic` va `instagram_business_content_publish` ruxsatlari.
3. Generate token → **long-lived token** (60 kun) → `IG_TOKEN`. User ID → `IG_USER_ID`.
4. Agar Facebook Login yo'li bilan ulagan bo'lsang: `IG_GRAPH_HOST=graph.facebook.com`.

⚠️ Instagram tokeni 60 kunda eskiradi. Uni har 50 kunda yangilab, GitHub Secret'ni almashtirish kerak.

## 5-qadam. Qo'lda to'liq sinov

```powershell
python run_quiz.py --only telegram      # avval faqat Telegram
python run_quiz.py --only youtube
python run_quiz.py --only instagram
```

Har biri ishlasa, tayyor.

## 6-qadam. GitHub'da avtomat jadval

1. GitHub'da yangi **private** repo oching, masalan `geoilm-auto`. Yoki papkani Zanjir-loyiha ichiga qo'yib, workflow faylini uning `.github/workflows/` papkasiga ko'chiring.
2. VS Code'da: `Source Control` (chapdagi 3-ikonka) → **Initialize Repository** → hamma faylni Commit → **Publish Branch** → private.
3. Repoda: `Settings → Secrets and variables → Actions → New repository secret`. `.env` dagi har bir qatorni alohida secret qilib qo'shing: `TG_BOT_TOKEN`, `TG_CHAT_ID`, `TG_ADMIN_CHAT_ID`, `YT_CLIENT_ID`, `YT_CLIENT_SECRET`, `YT_REFRESH_TOKEN`, `IG_TOKEN`, `IG_USER_ID`.
4. `Actions → GeoIlm quiz → Run workflow` bilan birinchi marta qo'lda ishga tushirib tekshiring.
5. Shundan keyin kuniga 3 marta o'zi ishlaydi. Kompyuter o'chiq bo'lsa ham ishlayveradi.

`.env` va `client_secret.json` hech qachon GitHub'ga chiqmaydi, ular `.gitignore`'da turibdi.

---

## Sozlash

| Nima | Qayerda |
|---|---|
| Vaqt jadvali | `.github/workflows/geoilm.yml` → `cron` (UTC: Toshkent − 5 soat) |
| Savollar soni / nisbati | `generate.py` → `PLAN = {"oson": 3, "o‘rtacha": 4, "qiyin": 3}` |
| Takrorlanmaslik muddati | `generate.py` → `REPEAT_DAYS = 14` |
| Yangi davlat qo'shish | `data/countries.json` → `["ISO raqam kodi", "ISO 2 harf", "O'zbekcha nom"]` |
| Matnlar, heshteglar | `generate.py` → `captions()` |
| Musiqa ovozi | `generate.py` → `volume=0.16` |

## Muammolar

- **`ffmpeg` topilmadi** — FFmpeg o'rnatilgandan keyin VS Code'ni qayta oching.
- **YouTube `invalid_grant`** — refresh token o'lgan (ilova "Testing" holatida qolgan). App'ni Publish qilib, tokenni qayta oling.
- **Instagram `OAuthException 190`** — token eskirgan, yangisini oling.
- **Instagram `status_code: ERROR`** — video formati. Bu loyiha 1080×1920 H.264 + AAC chiqaradi, odatda muammo bo'lmaydi; boshqa sabab bo'lsa, xabardagi matnga qarang.
- **Kvota** — YouTube kuniga ~6 ta yuklashga ruxsat beradi. 3 ta bemalol sig'adi.
