# Serverga deploy qilish (Docker + PostgreSQL)

Bitta serverda ishga tushadi: **Caddy** (avtomatik HTTPS) → **Django/gunicorn** → **PostgreSQL** + **Redis**.
Celery (PDP sinxronizatsiyasi, Telegram) ixtiyoriy.

## Talablar

- Ubuntu 22.04/24.04 server, kamida 2 GB RAM (4 GB qulayroq), 20 GB disk.
- Domen nomi, uning A yozuvi server IP'siga yo'naltirilgan.
- 80 va 443 portlar ochiq (`ufw allow 22,80,443/tcp && ufw allow 443/udp`).
- Docker + Compose v2: `curl -fsSL https://get.docker.com | sh`

## Hetzner Cloud + GitHub orqali avtomatik deploy

Bu yo'l serverga qo'lda kirmasdan ishga tushiradi: server birinchi yoqilganda o'zi hamma narsani
o'rnatadi (`deploy/hetzner-cloud-init.yaml`), keyin `main` ga har push'da GitHub Actions testlarni
ishga tushiradi va muvaffaqiyatli bo'lsa serverni yangilaydi (`.github/workflows/ci-deploy.yml`).

### 0. Tayyorgarlik
1. Pull request'larni `main` ga birlashtiring (Docker fayllari `main` da bo'lishi shart).
2. O'z kompyuteringizda deploy kaliti yarating (parolsiz, faqat shu maqsad uchun):
   ```bash
   ssh-keygen -t ed25519 -N "" -C "pdpjunior-deploy" -f pdpjunior_deploy
   ```
   `pdpjunior_deploy.pub` ochiq kalit (serverga), `pdpjunior_deploy` maxfiy kalit (GitHub'ga).
   Maxfiy kalitni boshqa joyga qo'ymang va gitga qo'shmang.

### 1. Serverni yaratish (Hetzner Console)
1. Loyiha ochib, **Add Server** ni bosing.
2. Location: sizga yaqin (Helsinki yoki Falkenstein). Image: **Ubuntu 24.04**.
3. Type: shared vCPU, kamida **2 vCPU / 4 GB RAM**. IPv4 yoqilgan bo'lsin.
4. **SSH keys**: o'z shaxsiy kalitingizni qo'shing (admin kirish uchun).
5. **Cloud config** maydoniga `deploy/hetzner-cloud-init.yaml` mazmunini qo'ying, avval ichidagi
   ikki qiymatni o'zgartirib: `DOMAIN` (o'z domeningiz) va `DEPLOY_PUBKEY` (`pdpjunior_deploy.pub`
   ichidagi to'liq satr).
6. **Create & Buy now**.

### 2. DNS
Server yaratilgach Hetzner IP manzilni ko'rsatadi. Domeningizda shu IP'ga **A yozuvi** qo'shing
(`api.misol.uz -> 1.2.3.4`). Sertifikatni Caddy o'zi oladi; DNS kech yangilansa ham qayta urinadi.

### 3. Jarayonni kuzatish (5-8 daqiqa)
```bash
ssh root@SERVER_IP tail -f /var/log/pdpjunior-bootstrap.log
```
Oxirida `TAYYOR: https://DOMAIN/health` chiqadi. Keyin admin yarating:
```bash
ssh deploy@SERVER_IP "cd /opt/pdpjunior && ./deploy.sh createsuperuser"
```
(Interaktiv so'rov uchun `ssh -t` kerak bo'lishi mumkin.)

### 4. Avtomatik deploy (GitHub Secrets)
Repo -> **Settings -> Secrets and variables -> Actions -> New repository secret**:

| Secret | Qiymat |
|---|---|
| `DEPLOY_HOST` | Server IP yoki domen |
| `DEPLOY_SSH_KEY` | `pdpjunior_deploy` (maxfiy kalit) faylining TO'LIQ matni |
| `DEPLOY_KNOWN_HOSTS` | (ixtiyoriy, xavfsizroq) `ssh-keyscan SERVER_IP` natijasi |
| `DEPLOY_USER` | (ixtiyoriy) standart `deploy` |

Shundan so'ng `main` ga push qilsangiz: testlar (PostgreSQL) -> o'tsa -> server yangilanadi.
Pull request'larda faqat testlar ishlaydi, deploy hech qachon.

### 5. Sirlar va qo'shimcha sozlamalar
R2, Telegram, PDP kalitlarini **serverda** `/opt/pdpjunior/.env.prod` ga yozing (cloud-init yoki
GitHub'ga emas), keyin `./deploy.sh`. Hetzner'ning cloud config matni serverning metama'lumotida
saqlanadi, shuning uchun unga sir qo'ymang.

### Muhim
- Cloud-init faqat **birinchi** yoqilishda ishlaydi. Keyingi o'zgarishlar `deploy.sh` orqali.
- Zaxira nusxa Hetzner **Backups** (server narxining ~20%) yoki `./deploy.sh backup` + cron bilan.
- Hetzner Cloud Firewall ham qo'shsangiz bo'ladi (22, 80, 443); server ichidagi `ufw` allaqachon yoqilgan.

## Birinchi deploy (bitta buyruq)

```bash
git clone https://github.com/shohruh223/PDPJuniorBackend.git pdpjunior
cd pdpjunior
DOMAIN=api.misol.uz ./deploy.sh
```

`deploy.sh` o'zi: `.env.prod` yaratadi (SECRET_KEY, baza va Redis parollari tasodifiy generatsiya
qilinadi) → image yig'adi → xizmatlarni ko'taradi → migratsiyani bajaradi → `web` sog'lom
bo'lishini kutadi. Oxirida `https://api.misol.uz/health` ishlaydi.

Keyin admin yarating: `./deploy.sh createsuperuser`

## Keyingi yangilanishlar

```bash
./deploy.sh        # git pull + qayta yig'ish + yangilash + migratsiya
```

## Sozlamalar (`.env.prod`)

Fayl serverda qoladi va gitga tushmaydi. To'liq ro'yxat: `.env.prod.example`.

| O'zgaruvchi | Vazifasi |
|---|---|
| `CORS_ALLOWED_ORIGINS` | Frontend originlari, vergul bilan (`https://pdp-junior-test.netlify.app`) |
| `USE_R2=1` + `R2_*` | Media Cloudflare R2'da. Qo'yilmasa fayllar docker volume'da saqlanadi va Caddy beradi |
| `CELERY_ENABLED=1` | Worker, maintenance va beat xizmatlarini ham ishga tushiradi |
| `TELEGRAM_*`, `PDP_*`, `ESKIZ_*` | Tashqi servis kalitlari |
| `TRUSTED_PROXY_COUNT` | Faqat Caddy bo'lsa `1`. Oldida Cloudflare ham bo'lsa `2` (aks holda rate limit noto'g'ri IP'ni ko'radi) |

O'zgartirgach `./deploy.sh` ni qayta ishga tushiring.

## SQLite'dagi ma'lumotni Postgres'ga ko'chirish

Lokal kompyuterda (loyiha papkasida, `.venv` faol, `.env` da `DATABASE_URL` yo'q, ya'ni SQLite):

```bash
python manage.py export_db_json --preset full --mode combined -o data/exports/full.json
scp data/exports/full.json foydalanuvchi@server:~/pdpjunior/full.json
```

Serverda:

```bash
DRY_RUN=1 ./deploy.sh import full.json     # avval faqat tekshiradi, bazaga yozmaydi
./deploy.sh import full.json               # haqiqiy import
rm full.json                               # ichida shaxsiy ma'lumot va parol hashlari bor
```

Import tranzaksiya ichida bajariladi (xato bo'lsa hammasi bekor qilinadi) va oxirida Postgres
sequence'larini avtomatik tiklaydi, shuning uchun keyingi yangi yozuvlar "duplicate key" bermaydi.
Import qayta ishga tushirilsa mavjud yozuvlar yangilanadi.

Media fayllar JSON bilan ko'chmaydi. R2 ishlatilsa hech narsa qilish shart emas. Aks holda:
`docker compose --env-file .env.prod cp media/. web:/app/media`

## Kundalik buyruqlar

```bash
./deploy.sh status               # xizmatlar holati
./deploy.sh logs web             # log (Ctrl+C bilan chiqiladi)
./deploy.sh backup               # Postgres nusxasi -> backups/*.sql.gz
./deploy.sh manage shell         # manage.py buyruqlari
./deploy.sh restart | down
```

Zaxira nusxani avtomatik qilish uchun cron: `0 3 * * * cd ~/pdpjunior && ./deploy.sh backup`.
Nusxani serverdan tashqariga ham ko'chirib turing.

## Xavfsizlik eslatmalari

- Postgres va Redis tashqariga ochilmagan (faqat docker tarmog'i ichida).
- `.env.prod` ruxsati `600`; uni hech qachon gitga qo'shmang.
- Swagger productionda faqat admin uchun. Ochish: `.env.prod` ga `SWAGGER_PUBLIC=1`.
- `DEBUG=0` doim; productionda `REDIS_URL` bo'lmasa server ataylab ishga tushmaydi.

## Nosozliklarni topish

| Belgi | Sabab va yechim |
|---|---|
| `web sog'lom holatga kelmadi` | `./deploy.sh logs web`: odatda `.env.prod` dagi qiymat yoki migratsiya xatosi |
| Brauzerda sertifikat xatosi | Domen A yozuvi hali yangilanmagan yoki 80/443 yopiq. `./deploy.sh logs caddy` |
| Admin'da `CSRF verification failed` | `DOMAIN` noto'g'ri yozilgan; admin faqat `https://DOMAIN` dan ochilishi kerak |
| Hamma foydalanuvchi bir IP'dan ko'rinadi / rate limit juda tez ishlaydi | `TRUSTED_PROXY_COUNT` mos emas (yuqoriga qarang) |
| `DisallowedHost` | So'rov `ALLOWED_HOSTS` da yo'q domen bilan kelyapti; `EXTRA_ALLOWED_HOSTS=...` qo'shing |
