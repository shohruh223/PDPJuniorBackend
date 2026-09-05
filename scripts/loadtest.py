"""Yuk sinovi: 500 o'quvchi bir vaqtda test yechadi.

Bu skript haqiqiy HTTP so'rovlar yuboradi, ya'ni gunicorn, baza va Redis
zanjiri to'liq sinovdan o'tadi.

Tayyorgarlik:

    python manage.py seed_load_test --students 500 --yes
    python manage.py shell -c "
    from app.models.auth import User
    from rest_framework_simplejwt.tokens import RefreshToken
    import json
    users = User.objects.filter(phone_number__startswith='+99870000')
    open('scripts/tokens.json','w').write(json.dumps(
        [str(RefreshToken.for_user(u).access_token) for u in users]))
    "

Ishga tushirish:

    python scripts/loadtest.py --base http://127.0.0.1:8000 \\
        --tokens scripts/tokens.json --users 500 --concurrency 120

Har bir virtual o'quvchi real yo'lni bosib o'tadi:
dashboard -> darslar ro'yxati -> test boshlash -> savollar -> javoblar ->
natija -> reyting.

Natijada har bir endpoint uchun p50/p95/p99 va xatolar soni chiqadi.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import random
import statistics
import sys
import time
from collections import defaultdict

try:
    import httpx
except ImportError:  # pragma: no cover
    print("httpx kerak:  pip install httpx", file=sys.stderr)
    raise SystemExit(1)


STATS: dict[str, list[float]] = defaultdict(list)
ERRORS: dict[str, int] = defaultdict(int)
STATUSES: dict[str, dict[int, int]] = defaultdict(lambda: defaultdict(int))


async def call(client, method, path, label, **kwargs):
    started = time.perf_counter()
    try:
        response = await client.request(method, path, **kwargs)
    except Exception as exc:
        ERRORS[f"{label}:{exc.__class__.__name__}"] += 1
        return None
    elapsed = (time.perf_counter() - started) * 1000
    STATS[label].append(elapsed)
    STATUSES[label][response.status_code] += 1
    if response.status_code >= 500:
        ERRORS[f"{label}:{response.status_code}"] += 1
    return response


def _node(payload, *keys):
    node = payload
    for key in keys:
        if not isinstance(node, dict):
            return None
        node = node.get(key)
    return node


async def student_journey(client, token, lessons_pool):
    headers = {"Authorization": f"Bearer {token}"}

    await call(client, "GET", "/api/student/dashboard", "dashboard", headers=headers)

    response = await call(client, "GET", "/api/student/tests/lessons", "tests/lessons", headers=headers)
    lesson_id = None
    if response is not None and response.status_code == 200:
        try:
            data = response.json()
            modules = _node(data, "data", "modules") or _node(data, "modules") or []
            candidates = [
                lesson["id"]
                for module in modules
                for lesson in (module.get("lessons") or [])
                if lesson.get("questions_count")
            ]
            if candidates:
                lesson_id = random.choice(candidates)
        except Exception:
            pass
    if lesson_id is None and lessons_pool:
        lesson_id = random.choice(lessons_pool)
    if lesson_id is None:
        return

    response = await call(
        client, "POST", "/api/student/tests/start/", "tests/start",
        headers=headers, json={"lesson_id": lesson_id},
    )
    if response is None or response.status_code not in (200, 201):
        return

    try:
        payload = response.json()
        session = _node(payload, "data", "session") or _node(payload, "session") or {}
        session_id = session.get("session_id")
        questions = _node(payload, "data", "questions") or payload.get("questions") or []
    except Exception:
        return
    if not session_id:
        return

    await call(client, "GET", f"/api/student/tests/during/{session_id}/", "tests/during", headers=headers)

    for item in questions:
        # DIQQAT: `/tests/start/` javobida element `id` — bu
        # TestSessionQuestion identifikatori, javob yuborishda esa
        # SAVOL identifikatori kerak (u `question.id` ichida).
        inner = item.get("question") or {}
        qid = inner.get("id") or item.get("question_id")
        if qid is None:
            continue
        await call(
            client, "POST", f"/api/student/tests/during/{session_id}/answer/", "tests/answer",
            headers=headers,
            json={"question_id": qid, "selected_option": random.choice("ABCD")},
        )
        # Haqiqiy o'quvchi savollar orasida o'ylaydi.
        await asyncio.sleep(random.uniform(0.05, 0.25))

    await call(
        client, "GET", f"/api/student/tests/sessions/{session_id}/result/", "tests/result",
        headers=headers,
    )
    await call(client, "GET", "/api/ranking", "ranking", headers=headers)
    await call(client, "GET", "/api/student/ranking/me", "ranking/me", headers=headers)
    # Ilgari bu ikkitasi har chaqiruvda tashqi PDP API'ni kutardi (15 s gacha)
    await call(client, "GET", "/api/student/payment-histories", "payments", headers=headers)
    await call(client, "GET", "/api/student/invoices", "invoices", headers=headers)


async def run(args):
    tokens = json.load(open(args.tokens, encoding="utf-8"))
    tokens = tokens[: args.users]
    if not tokens:
        print("Token topilmadi.", file=sys.stderr)
        return 1

    lessons_pool = json.load(open(args.lessons, encoding="utf-8")) if args.lessons else []

    limits = httpx.Limits(max_connections=args.concurrency + 20, max_keepalive_connections=args.concurrency)
    semaphore = asyncio.Semaphore(args.concurrency)

    async with httpx.AsyncClient(base_url=args.base, timeout=args.timeout, limits=limits) as client:
        async def guarded(token):
            async with semaphore:
                # Foydalanuvchilar bir vaqtda emas, sekin-asta kiradi.
                await asyncio.sleep(random.uniform(0, args.ramp))
                await student_journey(client, token, lessons_pool)

        started = time.perf_counter()
        await asyncio.gather(*(guarded(token) for token in tokens))
        total = time.perf_counter() - started

    report(total, len(tokens))
    return 0


def pct(values, p):
    if not values:
        return 0.0
    values = sorted(values)
    index = min(len(values) - 1, int(round(p / 100 * (len(values) - 1))))
    return values[index]


def report(total_seconds, users):
    total_requests = sum(len(v) for v in STATS.values())
    print()
    print(f"{'ENDPOINT':22s} {'SO‘ROV':>8s} {'p50':>8s} {'p95':>8s} {'p99':>8s} {'max':>8s}  KODLAR")
    print("-" * 92)
    for label in sorted(STATS):
        values = STATS[label]
        codes = ", ".join(f"{code}:{n}" for code, n in sorted(STATUSES[label].items()))
        print(
            f"{label:22s} {len(values):>8} "
            f"{pct(values, 50):>8.0f} {pct(values, 95):>8.0f} "
            f"{pct(values, 99):>8.0f} {max(values):>8.0f}  {codes}"
        )
    print("-" * 92)
    print(f"Virtual o‘quvchi : {users}")
    print(f"Jami so‘rov      : {total_requests}")
    print(f"Umumiy vaqt      : {total_seconds:.1f} s")
    print(f"O‘rtacha RPS     : {total_requests / total_seconds:.1f}")
    if ERRORS:
        print("\nXATOLAR:")
        for key, count in sorted(ERRORS.items()):
            print(f"  {key}: {count}")
    else:
        print("\nXato yo‘q (5xx va ulanish xatolari topilmadi).")


def main():
    parser = argparse.ArgumentParser(description="PDP Junior backend yuk sinovi")
    parser.add_argument("--base", default="http://127.0.0.1:8000")
    parser.add_argument("--tokens", default="scripts/tokens.json")
    parser.add_argument("--lessons", default="", help="Dars ID'lari ro'yxati (JSON)")
    parser.add_argument("--users", type=int, default=500)
    parser.add_argument("--concurrency", type=int, default=120)
    parser.add_argument("--ramp", type=float, default=10.0, help="Kirish oynasi (soniya)")
    parser.add_argument("--timeout", type=float, default=30.0)
    raise SystemExit(asyncio.run(run(parser.parse_args())))


if __name__ == "__main__":
    main()
