#!/usr/bin/env bash
# PDP Junior backend — bitta buyruqli deploy.
#
#   ./deploy.sh                   birinchi marta ham, yangilash ham: hammasini qiladi
#   ./deploy.sh init              faqat .env.prod yaratadi
#   ./deploy.sh status | logs [xizmat] | down | restart
#   ./deploy.sh backup            Postgres'dan siqilgan nusxa -> backups/
#   ./deploy.sh import FAYL.json  SQLite'dan eksport qilingan ma'lumotni yuklash
#                                 (DRY_RUN=1 bo'lsa faqat tekshiradi)
#   ./deploy.sh createsuperuser   admin foydalanuvchi yaratish
#   ./deploy.sh manage KOMANDA..  istalgan `manage.py` buyrug'i
#
# Muhit: DOMAIN=api.misol.uz ./deploy.sh   (.env.prod yo'q bo'lsa so'ramaydi)
#        SKIP_PULL=1 ./deploy.sh           (git pull qilmaslik)
set -euo pipefail
cd "$(dirname "$0")"

ENV_FILE=".env.prod"

die()  { echo "XATO: $*" >&2; exit 1; }
info() { echo "==> $*"; }

env_get() {  # env_get KALIT [default] — .env.prod dan qiymat o'qiydi
    local v
    v=$(grep -E "^$1=" "$ENV_FILE" 2>/dev/null | tail -1 | cut -d= -f2- || true)
    echo "${v:-${2:-}}"
}

need_docker() {
    command -v docker >/dev/null 2>&1 || die "Docker o'rnatilmagan. Ubuntu'da: curl -fsSL https://get.docker.com | sh"
    docker compose version >/dev/null 2>&1 || die "'docker compose' plagini topilmadi (Docker 20.10+ / Compose v2 kerak)."
}

dc() {
    local profiles=()
    if [ "$(env_get CELERY_ENABLED 0)" = "1" ]; then
        profiles=(--profile celery)
    fi
    docker compose --env-file "$ENV_FILE" ${profiles[@]+"${profiles[@]}"} "$@"
}

rand_hex() { openssl rand -hex "$1" 2>/dev/null || head -c "$1" /dev/urandom | od -An -tx1 | tr -d ' \n'; }

cmd_init() {
    if [ -f "$ENV_FILE" ]; then
        info "$ENV_FILE mavjud — o'zgartirilmadi."
        return
    fi
    local domain="${DOMAIN:-}"
    if [ -z "$domain" ]; then
        read -r -p "Domen (masalan api.misol.uz; lokal sinov uchun localhost): " domain
    fi
    [ -n "$domain" ] || die "Domen kerak."

    info "$ENV_FILE yaratilmoqda (sirlar tasodifiy generatsiya qilinadi)"
    umask 077
    cat > "$ENV_FILE" <<ENVEOF
# Avtomatik yaratildi: $(date -u +%FT%TZ). GITGA QO'SHMANG.
DOMAIN=$domain
SECRET_KEY=$(rand_hex 32)
POSTGRES_USER=pdpjunior
POSTGRES_DB=pdpjunior
# Faqat harf/raqam (URL ichida ishlatiladi).
POSTGRES_PASSWORD=$(rand_hex 24)
REDIS_PASSWORD=$(rand_hex 24)

# Frontend originlari (vergul bilan): https://pdp-junior-test.netlify.app
CORS_ALLOWED_ORIGINS=
# Cloudflare ham bo'lsa 2, faqat Caddy bo'lsa 1.
TRUSTED_PROXY_COUNT=1

# 1 = Celery worker/beat ishga tushadi (PDP sinxronizatsiyasi, Telegram).
CELERY_ENABLED=0

# --- Quyidagilarni kerak bo'lsa to'ldiring (.env.example ga qarang) ---
# USE_R2=1
# R2_ACCOUNT_ID=
# R2_ACCESS_KEY_ID=
# R2_SECRET_ACCESS_KEY=
# R2_BUCKET_NAME=
# R2_ENDPOINT=
# R2_PUBLIC_BASE_URL=
# TELEGRAM_BOT_TOKEN=
# TELEGRAM_SHOP_CHAT_ID=
# PDP_AUTH_BASE_URL=
# PDP_STUDENT_BASE_URL=
# ESKIZ_EMAIL=
# ESKIZ_PASSWORD=
ENVEOF
    chmod 600 "$ENV_FILE"
    info "Tayyor. R2/Telegram/PDP kalitlari kerak bo'lsa $ENV_FILE ni tahrirlab, ./deploy.sh ni qayta ishga tushiring."
}

wait_healthy() {
    info "web sog'lom bo'lishi kutilmoqda (migratsiya ham shu vaqtda ishlaydi)..."
    local cid status
    for _ in $(seq 1 60); do
        cid=$(dc ps -q web 2>/dev/null || true)
        if [ -n "$cid" ]; then
            status=$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "$cid" 2>/dev/null || echo unknown)
            [ "$status" = "healthy" ] && return 0
            [ "$status" = "exited" ] && break
        fi
        sleep 3
    done
    echo "---- web logi (oxirgi 60 qator) ----" >&2
    dc logs --tail 60 web >&2 || true
    die "web sog'lom holatga kelmadi."
}

cmd_deploy() {
    need_docker
    cmd_init
    if [ -d .git ] && [ -z "${SKIP_PULL:-}" ]; then
        info "git pull"
        git pull --ff-only || die "git pull bajarilmadi (lokal o'zgarishlar bormi?). SKIP_PULL=1 bilan o'tkazib yuborish mumkin."
    fi
    info "image yig'ilmoqda"
    dc build
    info "xizmatlar ishga tushirilmoqda"
    dc up -d --remove-orphans
    wait_healthy
    info "Holat:"
    dc ps
    local domain
    domain=$(env_get DOMAIN)
    echo
    echo "Tayyor: https://$domain/health"
    echo "Admin yaratish:      ./deploy.sh createsuperuser"
    echo "Ma'lumot yuklash:    ./deploy.sh import data/exports/full.json"
}

cmd_backup() {
    need_docker
    mkdir -p backups
    local out="backups/pdpjunior_$(date +%F_%H%M%S).sql.gz"
    dc exec -T db pg_dump -U "$(env_get POSTGRES_USER pdpjunior)" "$(env_get POSTGRES_DB pdpjunior)" | gzip > "$out"
    info "Zaxira nusxa: $out ($(du -h "$out" | cut -f1))"
}

cmd_import() {
    need_docker
    local file="${1:-}"
    [ -n "$file" ] && [ -e "$file" ] || die "Foydalanish: ./deploy.sh import FAYL.json (yoki per-table papka)"
    info "$file konteynerga nusxalanmoqda"
    dc exec -T web rm -rf /tmp/import_data
    dc cp "$file" web:/tmp/import_data
    local extra=()
    [ -n "${DRY_RUN:-}" ] && extra=(--dry-run)
    dc exec -T web python manage.py import_db_json -i /tmp/import_data ${extra[@]+"${extra[@]}"}
}

case "${1:-deploy}" in
    deploy|up)         cmd_deploy ;;
    init)              cmd_init ;;
    status)            need_docker; dc ps ;;
    logs)              need_docker; shift; dc logs -f --tail 100 "$@" ;;
    down)              need_docker; dc down ;;
    restart)           need_docker; dc restart ;;
    backup)            cmd_backup ;;
    import)            shift; cmd_import "$@" ;;
    createsuperuser)   need_docker; dc exec web python manage.py createsuperuser ;;
    manage)            need_docker; shift; dc exec web python manage.py "$@" ;;
    -h|--help|help)    sed -n '2,16p' "$0" ;;
    *)                 die "Noma'lum buyruq: $1 (./deploy.sh help)" ;;
esac
