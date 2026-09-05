#!/usr/bin/env python3
"""`.po` fayllarni `.mo` ga aylantiradi (gettext o'rnatilmagan bo'lsa ham).

Django tarjimalarni ishga tushishda `.mo` (binar) fayldan o'qiydi.
Odatda ular `manage.py compilemessages` orqali yasaladi, lekin u
tizimda `msgfmt` (GNU gettext) borligini talab qiladi. Serverda yoki
CI'da gettext bo'lmasligi mumkin, shuning uchun bu skript MO formatini
o'zi yozadi — tashqi bog'liqlik yo'q.

Ishlatish:
    python scripts/compile_messages.py            # locale/ ichidagi hammasi
    python scripts/compile_messages.py locale/uz  # faqat bittasi

MO formati: https://www.gnu.org/software/gettext/manual/html_node/MO-Files.html
"""

import array
import os
import re
import struct
import sys

MAGIC = 0x950412DE


def parse_po(text):
    """`.po` matnidan {msgid: msgstr} lug'atini yig'adi."""
    entries = {}
    msgid = msgstr = None
    target = None
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("msgid_plural"):
            # Ko'plik shakllari bu yerda ishlatilmaydi — o'tkazib yuboramiz.
            target = None
            continue
        if line.startswith("msgid "):
            if msgid is not None and msgstr is not None:
                entries[msgid] = msgstr
            msgid = _unquote(line[len("msgid "):])
            msgstr = None
            target = "id"
            continue
        if line.startswith("msgstr "):
            msgstr = _unquote(line[len("msgstr "):])
            target = "str"
            continue
        if line.startswith('"') and target:
            piece = _unquote(line)
            if target == "id":
                msgid += piece
            else:
                msgstr += piece
    if msgid is not None and msgstr is not None:
        entries[msgid] = msgstr
    # Tarjimasi bo'sh bo'lganlar MO ga tushmaydi (aks holda ular
    # asl inglizcha matnni "bo'sh satr" bilan almashtirib qo'yadi).
    return {k: v for k, v in entries.items() if v or k == ""}


_ESCAPES = {"n": "\n", "t": "\t", "r": "\r", '"': '"', "\\": "\\"}


def _unquote(chunk):
    chunk = chunk.strip()
    if not (chunk.startswith('"') and chunk.endswith('"')):
        raise ValueError(f"Noto‘g‘ri satr: {chunk!r}")
    body = chunk[1:-1]
    out = []
    i = 0
    while i < len(body):
        ch = body[i]
        if ch == "\\" and i + 1 < len(body):
            out.append(_ESCAPES.get(body[i + 1], body[i + 1]))
            i += 2
        else:
            out.append(ch)
            i += 1
    return "".join(out)


def write_mo(entries, path):
    keys = sorted(entries)
    offsets, ids, strs = [], b"", b""
    for key in keys:
        eid = key.encode("utf-8")
        estr = entries[key].encode("utf-8")
        offsets.append((len(ids), len(eid), len(strs), len(estr)))
        ids += eid + b"\0"
        strs += estr + b"\0"

    keystart = 7 * 4 + 16 * len(keys)
    valuestart = keystart + len(ids)
    koffsets, voffsets = [], []
    for o1, l1, o2, l2 in offsets:
        koffsets += [l1, o1 + keystart]
        voffsets += [l2, o2 + valuestart]

    output = struct.pack(
        "Iiiiiii", MAGIC, 0, len(keys), 7 * 4, 7 * 4 + len(keys) * 8, 0, 0
    )
    output += array.array("i", koffsets + voffsets).tobytes()
    output += ids + strs
    with open(path, "wb") as fh:
        fh.write(output)
    return len(keys)


def main(argv):
    roots = argv[1:] or ["locale"]
    total = 0
    for root in roots:
        for dirpath, _dirs, files in os.walk(root):
            for name in files:
                if not name.endswith(".po"):
                    continue
                po_path = os.path.join(dirpath, name)
                mo_path = po_path[:-3] + ".mo"
                with open(po_path, encoding="utf-8") as fh:
                    entries = parse_po(fh.read())
                count = write_mo(entries, mo_path)
                total += 1
                print(f"{po_path} -> {mo_path}  ({count} ta satr)")
    if not total:
        print("`.po` fayl topilmadi.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
