# 500+ foydalanuvchi uchun ishga tushirish qo'llanmasi

Bu hujjat backendni bir vaqtda 500 va undan ortiq o'quvchi test yechadigan
holatga tayyorlash bo'yicha. Har bir bo'lim **nima uchun** kerakligini ham
tushuntiradi — sozlamani ko'r-ko'rona ko'chirmang.

---

## 1. Majburiy muhit o'zgaruvchilari

Ular bo'lmasa server ishga tushmaydi yoki noto'g'ri ishlaydi.

```bash
SECRET_KEY=<uzun tasodifiy satr>
DEBUG=0
ALLOWED_HOSTS=api.pdp.uz,pdp-junior.onrender.com
DATABASE_URL=postgres://...
REDIS_URL=redis://...
CELERY_ENABLED=1
```

**Nega `DEBUG=0` shunchalik muhim.** `DEBUG=True` holatida Django har bir SQL
so'rovni `connection.queries` ro'yxatiga qo'shadi va uni **hech qachon
tozalamaydi**. Uzoq ishlaydigan gunicorn worker sekin-asta xotirani
to'ldiradi va oxir-oqibat OOM bilan o'ladi. Bundan tashqari har bir 500 xatosi
tashrifchiga R2 kalitlari va DATABASE_URL bilan to'liq traceback ko'rsatadi.

**Nega `REDIS_URL` majburiy.** Redis bo'lmasa kesh `LocMemCache` ga tushadi —
u har bir gunicorn worker'ining shaxsiy xotirasida. Oqibatlari:

* modul qulfi keshi workerlar aro yangilanmaydi (modul goh ochiq, goh yopiq);
* rate limiting worker boshiga alohida hisoblanadi, ya'ni amalda ishlamaydi;
* ommaviy endpointlar keshi 3-4 marta takrorlanadi.

---

## 2. Jarayonlar

`Procfile` to'rtta jarayon turini e'lon qiladi:

| Jarayon | Buyruq | Vazifasi |
|---------|--------|----------|
| `web` | gunicorn | HTTP so'rovlar |
| `worker` | celery -Q pdp-junior | PDP sinxronizatsiyasi, Telegram xabarlari |
| `maintenance` | celery -Q pdp-junior-maintenance | Uzoq tozalash vazifalari |
| `beat` | celery beat | Jadval bo'yicha ishga tushirish |

`worker` va `beat` **majburiy**: ularsiz PDP ma'lumotlari yangilanmaydi va
tashqi so'rovlar yana web so'rovini bloklashga qaytadi (`PDP_SYNC_ASYNC`
o'z-o'zidan sinxron rejimga tushadi).

`maintenance` alohida navbatda, chunki uning vazifalari daqiqalab davom
etishi mumkin va tez sinxronizatsiya vazifalarini kutdirib qo'ymasligi kerak.

---

## 3. Parallellikni hisoblash

Django sinxron ishlaydi: bitta thread bir vaqtda bitta so'rovni bajaradi.

```
parallel so'rovlar = GUNICORN_WORKERS × GUNICORN_THREADS
```

Standart: `3 × 8 = 24`.

**Baza ulanishlari.** Har bir thread o'ziga baza ulanishi olishi mumkin
(`DB_CONN_MAX_AGE=120` bilan ular qayta ishlatiladi). Kerakli minimal
`max_connections`:

```
web (24) + celery worker (4) + maintenance (1) + beat (1) + zaxira (10) ≈ 40
```

Render Starter Postgres'da limit past bo'lishi mumkin — `SHOW max_connections;`
bilan tekshiring. Yetmasa `GUNICORN_THREADS` ni kamaytiring yoki
`DB_CONN_MAX_AGE=0` qo'ying (har so'rovda yangi ulanish: sekinroq, lekin
ulanish yig'ilmaydi).

**Instansiya qo'shish.** Ikkinchi web instansiya qo'shsangiz ulanishlar ham
ikki barobar bo'ladi. Bu holda PgBouncer (transaction pooling) qo'yish
kerak bo'ladi.

---

## 4. Yuk sinovi

Loyihada tayyor asboblar bor.

```bash
# 1) Sun'iy ma'lumot (FAQAT staging bazasida!)
python manage.py seed_load_test --students 500 --modules 8 --lessons 6 --questions 10 --yes

# 2) Tokenlar
python manage.py shell -c "
from app.models.auth import User
from rest_framework_simplejwt.tokens import RefreshToken
import json
users = User.objects.filter(phone_number__startswith='+99870000')
open('scripts/tokens.json','w').write(json.dumps(
    [str(RefreshToken.for_user(u).access_token) for u in users]))
"

# 3) Yuk sinovi
pip install httpx
python scripts/loadtest.py --base https://<sizning-domen> \
    --tokens scripts/tokens.json --users 500 --concurrency 120

# 4) Tozalash
python manage.py seed_load_test --cleanup
```

Sinov paytida `THROTTLE_ENABLED=0` qo'ying, aks holda rate limiting
natijalarni buzadi.

### O'lchangan natija (2 CPU li konteyner, Postgres + Redis)

500 virtual o'quvchi, har biri to'liq yo'lni bosib o'tdi (dashboard →
darslar → test boshlash → 10 ta javob → natija → reyting), jami 8 500 so'rov:

| Endpoint | Oldin p50 | Keyin p50 | Oldin p95 | Keyin p95 |
|----------|----------:|----------:|----------:|----------:|
| dashboard | 2 212 ms | **386 ms** | 6 108 ms | **599 ms** |
| tests/lessons | 2 150 ms | **389 ms** | 6 423 ms | **638 ms** |
| tests/start | 2 871 ms | **485 ms** | 6 789 ms | **744 ms** |
| tests/answer | 3 189 ms | **510 ms** | 7 031 ms | **754 ms** |
| tests/result | 3 697 ms | **520 ms** | 6 949 ms | **756 ms** |
| ranking | 3 670 ms | **391 ms** | 7 431 ms | **612 ms** |
| ranking/me | 6 092 ms | **412 ms** | 10 487 ms | **623 ms** |

Umumiy vaqt 326 s → **74 s**, o'rtacha 26 RPS → **114 RPS**.

Eslatma: eski kod bu sinovda tashqi PDP API'ga umuman murojaat qilmagan
(sinov profillarida token yo'q). Real productionda eski kod har bir
dashboard va to'lov so'rovida `adminapi.pdp.uz` ni kutardi, ya'ni haqiqiy
farq bundan ham katta.

---

## 5. Kesh strategiyasi

| Nima | TTL | Sozlama | Qachon tozalanadi |
|------|-----|---------|-------------------|
| Katalog, filial, mentor, portfolio | 5 daq | `CACHE_TTL_PUBLIC` | Admin panelda o'zgarganda (signal) |
| Reyting | 2 daq | `CACHE_TTL_RANKING` | TTL + beat oldindan to'ldiradi |
| Oy qahramonlari | 5 daq | `CACHE_TTL_HEROES` | MonthHero o'zgarganda |
| Galereya | 5 daq | `CACHE_TTL_GALLERY` | Post o'zgarganda |
| Modul qulfi | 15 daq | `CACHE_TTL_PROGRESS` | Test yakunlanganda + dars/savol o'zgarganda |

Kesh qatlami "stampede" dan himoyalangan: TTL tugagan lahzada faqat bitta
so'rov qayta hisoblaydi, qolganlari eskirgan (lekin to'g'ri) javobni oladi.

**Redis yiqilsa nima bo'ladi.** Sayt ishlashda davom etadi:
`IGNORE_EXCEPTIONS=True` tufayli kesh o'qishlari `None` qaytaradi, rate
limiting esa so'rovni o'tkazib yuboradi (fail-open). Faqat sekinroq bo'ladi.

---

## 6. Tashqi PDP API

Bu backend `adminapi.pdp.uz` ustidagi qobiq. Uning sekinligi bizning
javob vaqtimizga **ta'sir qilmasligi** kerak.

* Dashboard, to'lovlar va invoyslar **har doim bazadan** o'qiladi.
* Yangilash `PDP_SYNC_MIN_INTERVAL` (5 daq) dan tez-tez bo'lmaydi.
* Yangilash Celery vazifasi sifatida bajariladi (`PDP_SYNC_ASYNC=1`).
* Bitta o'quvchi uchun bir vaqtda faqat bitta tashqi so'rov ketadi.
* Mijoz `?refresh=1` bilan majburiy yangilashni so'ray oladi (throttle bilan).

Agar PDP javob bermasa, javobda `sync_warning` maydoni paydo bo'ladi,
lekin ma'lumot baribir ko'rsatiladi.

---

## 7. Kuzatuv

```bash
curl https://<domen>/health        # liveness — bazaga tegmaydi
curl https://<domen>/health/ready  # readiness — baza + kesh
```

Platformaning health check'ini `/health` ga qo'ying (yuk ostida ham
darhol javob beradi), monitoring uchun `/health/ready` dan foydalaning.

Gunicorn access log har so'rovning bajarilish vaqtini mikrosoniyada
yozadi (`%(D)sus`) — sekin endpointni shundan topasiz.

Sekin SQL so'rovlarni ko'rish uchun **vaqtincha**:

```bash
SQL_LOG_LEVEL=DEBUG
```

---

## 8. Rate limiting

| Scope | Standart | Nimani himoya qiladi |
|-------|----------|----------------------|
| `sms` | 4/min | SMS balansi (IP + telefon raqami bo'yicha) |
| `auth` | 10/min | Parol brute-force |
| `password` | 6/min | Tashqi API'ga parol oracle |
| `test_write` | 180/min | Test yozuvlari |
| `shop_write` | 20/min | Do'kon buyurtmalari |
| `sync` | 20/min | Majburiy PDP sinxronizatsiyasi |
| `anon` / `user` | 90 / 600 min | Umumiy shift |

**500 o'quvchi uchun yetarlimi?** Ha. Bir o'quvchi 10 savollik testni ~10
daqiqada yechadi, ya'ni daqiqasiga ~1-2 yozuv so'rovi. 180/min chegarasi
faqat avtomatlashtirilgan hujumni ushlaydi.

Yuk sinovi paytida `THROTTLE_ENABLED=0`.

---

## 9. Deploy oldidan tekshiruv ro'yxati

- [ ] `SECRET_KEY` yangi va sir (eski kalit git tarixida bo'lgan)
- [ ] `DEBUG=0`, `ALLOWED_HOSTS` to'ldirilgan
- [ ] `REDIS_URL` qo'shilgan, `CELERY_ENABLED=1`
- [ ] `worker` va `beat` jarayonlari ishga tushirilgan
- [ ] Postgres `max_connections` yetarli (yuqoridagi hisob)
- [ ] `python manage.py migrate` (yangi `0014` migratsiyasi bor)
- [ ] `python manage.py test app` — 42 test o'tadi
- [ ] `/health/ready` `"status": "ready"` qaytaradi
- [ ] `db.sqlite3` git tarixidan olib tashlangan va tokenlar almashtirilgan
- [ ] Frontend `pdp_token` ni ishlatmasligi tekshirilgan → `EXPOSE_PDP_TOKEN=0`

---

## 10. Nima o'zgarmadi (frontend uchun)

Javob shakllari **saqlangan**. Aniqrog'i:

* Paginatsiya `?page=` yoki `?limit=` yuborilmasa yoqilmaydi — javob
  avvalgidek to'liq ro'yxat (lekin maksimal 500 yozuv).
* `pdp_token` login javobida hozircha bor (`EXPOSE_PDP_TOKEN=1`).
* Barcha URL'lar, jumladan eski compat aliaslar, ishlashda davom etadi.

Yangi qo'shilganlar (ixtiyoriy):

* `?page=2&limit=50` → javobga `meta` bloki qo'shiladi.
* `?refresh=1` → dashboard/to'lov endpointlarida majburiy sinxronizatsiya.
* `GET /health`, `GET /health/ready`.
* `POST /auth/logout` — `{"refresh_token": "..."}`.
* Dashboard javobida `coins.spent_coin` maydoni.

**Bitta ko'rinadigan o'zgarish.** Reytingda ma'lumot yo'q bo'lsa endi
haqiqiy bo'sh qiymat qaytadi (`monthlyPoints: 0`, `streak: 0`,
`course: ""`, `level: ""`). Ilgari ular "taxmin qilib" to'ldirilardi:
hech qachon test topshirmagan o'quvchi ham oylik ball va seriya bilan
ko'rinardi. Eski ko'rinishni `RANKING_ESTIMATE_MISSING=1` bilan
qaytarish mumkin, lekin o'sha raqamlar haqiqiy emas.
