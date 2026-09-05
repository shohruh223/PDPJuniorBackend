"""Gunicorn konfiguratsiyasi — 500+ bir vaqtdagi foydalanuvchi uchun.

Django sinxron freymvork: bitta worker thread bir vaqtda bitta so'rovni
bajaradi. Shuning uchun "qotib qolmaslik" ikki narsaga bog'liq:

  1. Yetarli miqdorda parallel ishlov beruvchi (worker x thread).
  2. Hech bir so'rov uzoq bloklanmasligi (tashqi API, sekin SQL).

Bu fayl birinchisini beradi; ikkinchisi kod tomonda hal qilingan
(tashqi sinxronizatsiya Celery'ga ko'chirildi, statement_timeout qo'yildi).

VAJ: har bir thread o'ziga baza ulanishi olishi mumkin. Kerakli ulanishlar:
    workers x threads (+ celery worker'lari)
Postgres'ning max_connections shundan katta bo'lishi shart.
Standart 3 x 8 = 24 ulanish — Render Starter uchun ham xavfsiz.
"""

import multiprocessing
import os


def _int(name, default):
    try:
        return int(os.getenv(name, "") or default)
    except (TypeError, ValueError):
        return default


bind = f"0.0.0.0:{os.getenv('PORT', '8000')}"

# gthread: sinxron kod uchun eng mos worker turi. Thread'lar tarmoq va
# baza kutish vaqtini bir-birining ustiga qo'yadi.
worker_class = "gthread"

_cpu = multiprocessing.cpu_count()
workers = _int("GUNICORN_WORKERS", min(4, max(2, _cpu)))
threads = _int("GUNICORN_THREADS", 8)

# Bitta so'rov shu vaqtdan oshsa worker qayta ishga tushiriladi.
timeout = _int("GUNICORN_TIMEOUT", 45)
graceful_timeout = _int("GUNICORN_GRACEFUL_TIMEOUT", 30)

# Keep-alive: frontend ketma-ket so'rov yuborganda TLS qayta ochilmaydi.
keepalive = _int("GUNICORN_KEEPALIVE", 15)

# Worker'larni davriy yangilash — xotira gigienasi uchun.
#
# DIQQAT: har bir qayta ishga tushish o'sha worker'dagi ochiq keep-alive
# ulanishlarni uzadi. Yuk sinovida 2000 qiymati 8500 so'rovda 5 marta
# qayta ishga tushishga va mijozda ~0.06% ulanish xatosiga olib keldi.
# DEBUG=0 bo'lgani uchun Django endi SQL so'rovlarni xotirada
# to'plamaydi, ya'ni tez-tez yangilashga ehtiyoj yo'q.
# 0 qiymati bu mexanizmni butunlay o'chiradi.
max_requests = _int("GUNICORN_MAX_REQUESTS", 10000)
max_requests_jitter = _int("GUNICORN_MAX_REQUESTS_JITTER", 1000)

# Navbat: barcha thread'lar band bo'lsa so'rovlar shu yerda kutadi.
backlog = _int("GUNICORN_BACKLOG", 1024)

# Konteynerda /tmp tmpfs bo'lmasligi mumkin — heartbeat fayli sekin diskda
# bo'lsa worker'lar sababsiz o'ldiriladi.
worker_tmp_dir = os.getenv("GUNICORN_WORKER_TMP_DIR", "/dev/shm")
if not os.path.isdir(worker_tmp_dir):
    worker_tmp_dir = None

accesslog = os.getenv("GUNICORN_ACCESS_LOG", "-")
errorlog = "-"
loglevel = os.getenv("GUNICORN_LOG_LEVEL", "info")
# Javob vaqtini (D = mikrosoniya) logga chiqaramiz — sekin endpointni
# topish uchun.
access_log_format = '%(h)s "%(r)s" %(s)s %(b)s %(D)sus "%(a)s"'

preload_app = os.getenv("GUNICORN_PRELOAD", "1") == "1"
forwarded_allow_ips = os.getenv("FORWARDED_ALLOW_IPS", "*")
