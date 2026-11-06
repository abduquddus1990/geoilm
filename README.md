# GeoIlm — "Bu qaysi davlat?" avtomat video zavodi

Kuniga aniq 3 marta (06:20 / 19:00 / 21:00, Toshkent vaqti) avtomatik:

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

**Fon musiqasi avtomatik:** har video uchun `music.py` yangi original trek yasaydi. Davlat va poytaxt formatlariga yengil, qiziquvchan ohang, futbolchi formatiga energik ohang tushadi. Bu treklar 100% o'zimizniki, shuning uchun Content ID xavfi yo'q. O'z treklaringni ishlatmoqchi bo'lsang, ularni `music/` yoki `music/<format>/` papkasiga qo'y, shunda generatsiya o'rniga ular olinadi.

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

## Formatlar va jadval

| Slot (Toshkent vaqti) | Format |
|---|---|
| 06:20 · 19:00 · 21:00 | Har kuni navbat bilan: globus → futbolchi → globus_poytaxt (globusda poytaxt) → davlat (daftar xaritasi) → viloyat → poytaxt (daftar xaritasi) → tuman (tumanlar fayli bo'lsa) |

Kuniga 3 ta video chiqadi, navbat har kuni siljiydi, shuning uchun formatlar har kuni boshqacha tartibda tushadi. Barcha vaqtlar Toshkent bo'yicha (GitHub cron UTC da, ya'ni 01:20 / 14:00 / 16:00). Har slot uchun +1 soatlik zaxira bor; data/sent.json takror yuborishdan saqlaydi.

Qo'lda tanlash: `python run_quiz.py --mode poytaxt --no-publish`

`players.json` da 68 ta futbolchi bor (15 oson, 24 o‘rtacha, 29 qiyin; 80–90-yillar, 2000-yillar va hozirgi yulduzlar). Yangisini qo'shish: `{"id","name","nat","clubs":[[davlat_kodi,klub,yillar],...]}`, Angliya uchun `ENG`. Klublar yo'li 2–10 ta bo'lsin.

## 3D globus formati ("globus")

Kosmos fonida aylanuvchi globus har savolda keyingi davlatga uchib boradi va yaqinlashadi. Davlat yorqin rang bilan yonib, atrofida to'lqin tarqaladi. Davlatlar `data/countries.json` dan olinadi, kunlik navbatda birinchi turadi.

```powershell
python run_quiz.py --mode globus --only telegram
```

## Tumanlar formati ("Bu qaysi tuman?")

Bir martalik: tumanlarning hozirgi chegaralari OpenStreetMap'dan olinadi.

```powershell
pip install osm2geojson
python tools/fetch_districts.py
```

Natija `data/uz_districts.geojson` fayliga yoziladi, nomlar o'zbekcha lotin yozuvida bo'ladi. Shu fayl paydo bo'lgandan keyin "tuman" formati avtomatik navbatga qo'shiladi: har videoda bitta viloyat, 8 ta tuman. Viloyatni o'zing tanlashing ham mumkin:

```powershell
python run_quiz.py --mode tuman --region UZ-TK --only telegram    # Toshkent shahri tumanlari
python run_quiz.py --mode tuman --region UZ-SA --only telegram    # Samarqand viloyati
```

Viloyat kodlari: UZ-AN Andijon, UZ-BU Buxoro, UZ-FA Farg'ona, UZ-JI Jizzax, UZ-NG Namangan, UZ-NW Navoiy, UZ-QA Qashqadaryo, UZ-QR Qoraqalpog'iston, UZ-SA Samarqand, UZ-SI Sirdaryo, UZ-SU Surxondaryo, UZ-TK Toshkent shahri, UZ-TO Toshkent viloyati, UZ-XO Xorazm.

## Futbolchilar bazasi (Wikidata)

```powershell
python tools/fetch_players.py --limit 200 --uz
```

Bu buyruq Wikidata'dan ~150–200 ta mashhur futbolchi va ularning klub tarixini olib, `data/players_auto.json` faylini yasaydi. `--uz` qo'shilsa, O'zbekiston terma jamoasi futbolchilari ham kiradi. GitHub'da `players.yml` workflow buni har oyning 1-kuni o'zi bajaradi. Xato topsang, to'g'ri variantini `data/players.json`'ga qo'lda yoz, qo'ldagi ma'lumot ustun turadi.

## Manbalar va litsenziyalar

- Bayroqlar: [flag-icons](https://github.com/lipis/flag-icons) (MIT)
- Viloyat chegaralari: [geoBoundaries](https://www.geoboundaries.org), © OpenStreetMap hissadorlari (ODbL). Viloyat videolari izohiga manba avtomatik yoziladi.
- Futbolchilar: [Wikidata](https://www.wikidata.org) (CC0)

## VS Code tugmalari (eng oson yo'l)

`Ctrl + Shift + P` → **Tasks: Run Task** → ro'yxatdan tanlang:

| Vazifa | Qachon |
|---|---|
| GeoIlm: 1) Bir martalik o'rnatish | yangi fayllarni ko'chirgandan keyin |
| GeoIlm: 2) Futbolchilar bazasini yangilash | oyiga bir marta |
| GeoIlm: 3) Ovozlarni yasash (Kaggle GPU) | bir marta, ovoz yozuvingiz bilan |
| GeoIlm: 3b) Yangi iboralarga ovoz qo'shish | yangi davlat yoki futbolchi qo'shilganda |
| GeoIlm: 4) Video yasab botga yuborish | sinov yoki qo'lda yuborish |
| GeoIlm: 5) Faqat video yasash | ko'rib chiqish uchun, `out/` papkasida |

## Kaggle sozlash (bir marta, 5 daqiqa)

Ovozlar Kaggle'ning bepul GPU'sida (haftasiga 30 soat) avtomatik yasaladi.

1. [kaggle.com](https://www.kaggle.com) da ro'yxatdan o'ting (Google akkaunt bilan).
2. **Telefon raqamini tasdiqlang:** `Settings → Phone verification`. Busiz GPU va internet yoqilmaydi.
3. `Settings → API → Create Legacy API Key` → `kaggle.json` yuklab olinadi.
4. Faylni shu papkaga qo'ying: `C:\Users\Surface\.kaggle\kaggle.json` (`.kaggle` papkasi yo'q bo'lsa, yarating).
5. Run Task → **GeoIlm: 3) Ovozlarni yasash** → ovoz yozuvingiz yo'lini kiriting. 20–40 daqiqa kuting, qolgani avtomatik.

Kaggle ishlamasa, zaxira yo'l: quyidagi Colab usuli.

## Avtomatik o'zbekcha ovoz (Navoiy TTS)

Video har savolda "Bu qaysi davlat?" deydi, javob ochilganda nomini aytadi ("Italiya!"), oxirida esa "Nechtasini topdingiz? Izohda yozing!" deydi.

Navoiy TTS faqat NVIDIA GPU'da ishlaydi. Shuning uchun barcha iboralar **bir marta** bepul Google Colab'da o'qitilib, `.wav` fayl qilib saqlanadi. Video yasashda GPU kerak bo'lmaydi.

1. `python tools/voice_lines.py` — `data/voice_lines.json` yasaydi (barcha iboralar ro'yxati).
2. [colab.research.google.com](https://colab.research.google.com) → `File → Upload notebook` → `tools/navoiy_colab.ipynb` → `Runtime → Change runtime type → T4 GPU`.
3. Kataklarni yuqoridan pastga ishga tushir. 2-qadamda `reference.wav` (o'z ovozing, 6–12 soniya) va `voice_lines.json` ni yuklaysan.
4. Yuklab olingan `voice_lines.zip` ni `quiz_generator/voice/lines/` papkasiga och.

Shundan keyin har bir videoga ovoz o'zi qo'shiladi, izohga esa "Ovoz: Navoiy TTS (sun'iy intellekt)" yozuvi tushadi. Biror ibora uchun `.wav` bo'lmasa, o'sha joy ovozsiz o'tadi, xato bermaydi.

## O'z ovozing (ixtiyoriy, TTS o'rniga)

`quiz_generator/voice/` papkasiga fayllarni joylasang, ovoz har savol boshida avtomatik qo'yiladi:

- `davlat.mp3` — "Bu qaysi davlat?"
- `poytaxt.mp3` — "Poytaxti qaysi?"
- `futbolchi.mp3` — "Bu qaysi futbolchi?"

Format mp3, m4a, ogg yoki wav bo'lishi mumkin, 1–2 soniya, oldi va orqasida jimlik bo'lmasin.

## Sozlash

| Nima | Qayerda |
|---|---|
| Vaqt jadvali | `.github/workflows/geoilm.yml` → `cron` (UTC: Toshkent − 5 soat) |
| Savollar soni / nisbati | `generate.py` → `PLAN = {"oson": 3, "o‘rtacha": 4, "qiyin": 3}` |
| Takrorlanmaslik muddati | `generate.py` → `REPEAT_DAYS = 14` |
| Yangi davlat qo'shish | `data/countries.json` → `["ISO raqam kodi", "ISO 2 harf", "O'zbekcha nom"]` |
| Matnlar, heshteglar | `generate.py` → `captions()` |
| Musiqa ovozi | `generate.py` → `volume=0.16` |
| Ko'rinish (dizayn) | `generate.py` → `STYLE`: theme = `notebook` / `clean` / `pastel` / `chalk`, `globe`, `labels`, `zoom` (yoki GEOILM_THEME va boshqa env o'zgaruvchilar) |

## Muammolar

- **`ffmpeg` topilmadi** — FFmpeg o'rnatilgandan keyin VS Code'ni qayta oching.
- **YouTube `invalid_grant`** — refresh token o'lgan (ilova "Testing" holatida qolgan). App'ni Publish qilib, tokenni qayta oling.
- **Instagram `OAuthException 190`** — token eskirgan, yangisini oling.
- **Instagram `status_code: ERROR`** — video formati. Bu loyiha 1080×1920 H.264 + AAC chiqaradi, odatda muammo bo'lmaydi; boshqa sabab bo'lsa, xabardagi matnga qarang.
- **Kvota** — YouTube kuniga ~6 ta yuklashga ruxsat beradi. 3 ta bemalol sig'adi.
