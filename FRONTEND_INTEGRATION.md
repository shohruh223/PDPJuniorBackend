# PDP Junior Backend — Frontend integratsiya qo'llanmasi

## Portal endpointlar (yangi)

### Reyting — `ranking-page.js`
| Method | URL | Query |
|--------|-----|-------|
| GET | `/api/ranking` | `scope=all\|course\|branch`, `period=total\|month`, `context`, `q` |
| GET | `/api/student/ranking/me` | Auth kerak — shaxsiy o‘rin |

Javob: `{ data: { students: [{ id, name, course, branch, mentor, avatar, totalPoints, monthlyPoints, streak, level }] } }`

### Do‘kon — `shop.html`
| Method | URL |
|--------|-----|
| GET | `/api/student/shop` | Katalog + balance (`?category=academy`) |
| GET | `/api/student/shop/balance` |
| GET | `/api/student/shop/orders` |
| POST | `/api/student/shop/orders/create/` | `{ "product_id": "uuid" }` |
| GET | `/api/student/shop/products/{id}/` |

### Galereya — `gallery-page.js`
| Method | URL |
|--------|-----|
| GET | `/api/gallery` |
| GET | `/api/gallery/{post_id}/` |

Javob: `{ data: { items: [{ category, icon, date, views, image, title, description, media }] } }`

### Oy qahramonlari — `heroes-portal.js`
| Method | URL | Query |
|--------|-----|-------|
| GET | `/api/heroes` | `month=2026-08`, `view=all\|directions\|branches`, `q` |

Javob: `{ data: { months: [...], active_month: {...}, heroes: [...] } }`

### Modullar va darslar — `lessons-data.js`
| Method | URL |
|--------|-----|
| GET | `/api/student/modules` | `?course_id=` |
| GET | `/api/student/modules/{id}/` |
| GET | `/api/student/lessons` | `?module_id=` yoki `?course_id=` |
| GET | `/api/student/lessons/{id}/` |
| GET | `/api/student/lessons/{id}/questions` |
| GET | `/api/student/tests/lessons` | To‘liq modul+dars daraxti |

## Admin

- **GalleryPost** — galereya postlari (i18n JSON)
- **CoinProduct** — category, stock, emoji, bg_gradient
- **CoinOrder** — do‘kon buyurtmalari

## Migratsiya

```bash
python manage.py migrate
```

## Auth va boshqa endpointlar

Avvalgi auth, dashboard, profile endpointlari o‘zgarmagan. Batafsil oldingi bo‘limlarda.
