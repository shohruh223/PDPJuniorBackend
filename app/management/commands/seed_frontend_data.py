from datetime import date, datetime, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Count
from django.utils import timezone

from app.models import (
    Branch,
    CoinProduct,
    Course,
    GalleryPost,
    Lesson,
    Mentor,
    Module,
    MonthHero,
    Portfolio,
    Question,
    StudentPaymentHistory,
    StudentProfile,
)
from app.models.marks import StudentMark


COURSES = [
    ("Scratch", "Bolalar uchun blokli dasturlash, animatsiya va o‘yinlar yaratish bo‘yicha qiziqarli kurs.", "static/img/course-logos/scratch.webp"),
    ("Python", "Algoritmlar, mantiqiy fikrlash va dasturlash asoslarini amaliy loyihalar bilan o‘rganish.", "static/img/course-logos/python.webp"),
    ("Frontend", "HTML, CSS va JavaScript asoslari orqali zamonaviy web sahifalar yaratishni o‘rganing.", "static/img/course-logos/frontend.webp"),
    ("Robototexnika", "Robot yasash, sensorlar bilan ishlash va muhandislik fikrlashni rivojlantiruvchi kurs.", "static/img/course-logos/robot-twemoji.svg"),
]

PYTHON_CURRICULUM = [
    ("Python asoslari", ["Variable", "Ma'lumot turlari", "Input va Output", "Arifmetik operatorlar", "String bilan ishlash", "Boolean qiymatlar", "Taqqoslash operatorlari", "Type conversion", "Kommentariyalar", "Kod yozish qoidalari", "Mini kalkulyator", "Modul testi"]),
    ("Shart operatorlari", ["if operatori", "if va else", "elif operatori", "Ichma-ich shartlar", "Mantiqiy operatorlar", "Taqqoslash amaliyoti", "Login tekshiruvi", "Yosh kalkulyatori", "Baholash dasturi", "Mini viktorina", "Amaliy loyiha", "Modul testi"]),
    ("Telegram bot", ["Bot yaratish", "BotFather bilan ishlash", "Start komandasi", "Message handler", "Command handler", "Reply keyboard", "Inline keyboard", "Callback query", "Foydalanuvchi holati", "API bilan ulash", "Botni serverga joylash", "Modul testi"]),
    ("List va Tuple", ["List yaratish", "Elementlarga murojaat", "List metodlari", "Slicing", "Tuple", "List va Tuple farqi", "Nested list", "Ro‘yxatni saralash", "Qidirish", "Amaliy mashqlar", "Mini loyiha", "Modul testi"]),
    ("Looplar", ["for loop", "range funksiyasi", "while loop", "break operatori", "continue operatori", "Nested loop", "Ro‘yxat bilan loop", "String bilan loop", "Hisoblagichlar", "Pattern chizish", "Mini loyiha", "Modul testi"]),
    ("Dictionary va Set", ["Dictionary yaratish", "Key va value", "Dictionary metodlari", "Dictionary loop", "Nested dictionary", "Set yaratish", "Set metodlari", "Union va intersection", "Ma’lumot qidirish", "Kontaktlar dasturi", "Mini loyiha", "Modul testi"]),
    ("Funksiyalar", ["Funksiya yaratish", "Parametrlar", "return operatori", "Default parametr", "Keyword argument", "*args", "**kwargs", "Scope", "Lambda", "Rekursiya", "Mini loyiha", "Modul testi"]),
    ("Fayllar bilan ishlash", ["Fayl ochish", "Fayl o‘qish", "Faylga yozish", "with operatori", "Matn fayllari", "CSV fayllar", "JSON fayllar", "Papka bilan ishlash", "Xatolarni ushlash", "Log yozish", "Mini loyiha", "Modul testi"]),
    ("Exception handling", ["Xatolik turlari", "try va except", "else bloki", "finally bloki", "Bir nechta except", "raise operatori", "Custom exception", "Validatsiya", "Debug qilish", "Xavfsiz kalkulyator", "Mini loyiha", "Modul testi"]),
    ("OOP asoslari", ["Class va object", "Constructor", "Atributlar", "Metodlar", "Encapsulation", "Inheritance", "Polymorphism", "Class method", "Static method", "Magic method", "Mini loyiha", "Modul testi"]),
    ("API va ma’lumotlar", ["API nima", "HTTP metodlar", "GET so‘rovi", "POST so‘rovi", "JSON response", "Status kodlar", "Headers", "Authentication", "Weather API", "Telegram API", "Mini loyiha", "Modul testi"]),
    ("Yakuniy loyiha", ["Loyiha tanlash", "Texnik topshiriq", "Arxitektura", "Ma’lumotlar modeli", "Asosiy funksiyalar", "Interfeys", "Testlash", "Xatolarni tuzatish", "Deploy", "Taqdimot", "Loyihani himoya qilish", "Yakuniy test"]),
]

BRANCHES = [
    ("Chilonzor", "Chilonzor, Toshkent", "static/img/branches/chilonzor.svg", "Toshkent · Chilonzor", "41.2696960", "69.1912750"),
    ("Yashnobod", "Yashnobod, Toshkent", "static/img/branches/yashnobod.svg", "Toshkent · Yashnobod", "41.2869790", "69.3479230"),
    ("Xadra", "Xadra, Toshkent", "static/img/branches/xadra.svg", "Toshkent · Xadra", "41.3237820", "69.2421410"),
    ("Sergeli", "Sergeli, Toshkent", "static/img/branches/sergeli.svg", "Toshkent · Sergeli", "41.2342190", "69.2155510"),
    ("Keles", "Keles, Toshkent viloyati", "static/img/branches/keles.svg", "Toshkent viloyati · Keles", "41.3934770", "69.2064620"),
    ("Yunusobod", "Yunusobod, Toshkent", "", "Toshkent · Yunusobod", None, None),
    ("Mirzo Ulug‘bek", "Mirzo Ulug‘bek, Toshkent", "", "Toshkent · Mirzo Ulug‘bek", None, None),
    ("Samarqand", "Samarqand shahri", "", "Samarqand", None, None),
    ("Andijon", "Andijon shahri", "", "Andijon", None, None),
    ("Farg‘ona", "Farg‘ona shahri", "", "Farg‘ona", None, None),
]

HOME_MENTORS = [
    ("Abror Abdusaidov", "Scratch", "Scratch dasturlashni o‘yinlar, animatsiyalar va qiziqarli topshiriqlar orqali o‘rgatadi.", "static/img/mentor/mentor-1.webp"),
    ("Asilbek Mamadaliyev", "Robototexnika", "Robototexnika yo‘nalishida texnik ijodkorlik va amaliy loyiha ko‘nikmalarini rivojlantiradi.", "static/img/mentor/mentor-2.webp"),
    ("Oybek Xalimov", "Python", "Python asoslarini mantiqiy fikrlash, masalalar va mini-loyihalar orqali tushunarli o‘rgatadi.", "static/img/mentor/mentor-3.webp"),
    ("Abdurahmon Maxamedov", "Frontend", "HTML, CSS va web sahifa yaratishni kreativ amaliy loyihalar orqali tushuntiradi.", "static/img/mentor/mentor-4.webp"),
    ("Jahongir Abdurahimov", "Frontend", "HTML, CSS va web sahifa yaratishni kreativ amaliy loyihalar orqali tushuntiradi.", "static/img/mentor/mentor-5.webp"),
    ("Saydullo Keldiyorov", "Python", "Python asoslarini mantiqiy fikrlash, masalalar va mini-loyihalar orqali tushunarli o‘rgatadi.", "static/img/mentor/mentor-6.webp"),
    ("Shohruh Abdurahmonov", "Frontend", "HTML, CSS va web sahifa yaratishni kreativ amaliy loyihalar orqali tushuntiradi.", "static/img/mentor/mentor-7.webp"),
    ("Asadbek Erkinov", "Frontend", "HTML, CSS va web sahifa yaratishni kreativ amaliy loyihalar orqali tushuntiradi.", "static/img/mentor/mentor-8.webp"),
    ("Bahodir Isroilov", "Robototexnika", "Robototexnika yo‘nalishida texnik ijodkorlik va amaliy loyiha ko‘nikmalarini rivojlantiradi.", "static/img/mentor/mentor-9.webp"),
    ("Shohruh Abdurahmonov (Python)", "Python", "Python asoslarini mantiqiy fikrlash, masalalar va mini-loyihalar orqali tushunarli o‘rgatadi.", "static/img/mentor/mentor-10.webp"),
]

RANKING_STUDENTS = [
    ("Malika", "Karimova", "Python", "Chilonzor", "malika.svg", 4960, 940, 18, "P-12"),
    ("Jasur", "Abduqodirov", "Frontend", "Yunusobod", "jasur.svg", 4815, 1010, 21, "F-10"),
    ("Farzona", "Usmonova", "Robototexnika", "Sergeli", "farzona.svg", 4720, 875, 15, "R-9"),
    ("Bekzod", "Mirzayev", "Python", "Mirzo Ulug‘bek", "bekzod.svg", 4580, 1085, 24, "P-11"),
    ("Nilufar", "Xolmatova", "Scratch", "Xadra", "nilufar.svg", 4455, 820, 13, "S-8"),
    ("Omadbek", "Yoqubov", "Frontend", "Yashnobod", "omadbek.svg", 4380, 790, 12, "F-9"),
    ("Ziyoda", "Qodirova", "Python", "Samarqand", "farzona.svg", 4265, 965, 19, "P-10"),
    ("Muhammadali", "Hamidov", "Robototexnika", "Andijon", "jasur.svg", 4190, 735, 10, "R-8"),
    ("Sevinch", "Tursunova", "Frontend", "Chilonzor", "malika.svg", 4075, 920, 17, "F-8"),
    ("Imron", "Akbarov", "Scratch", "Keles", "bekzod.svg", 3985, 680, 9, "S-7"),
    ("Sabrina", "Nematova", "Python", "Yunusobod", "nilufar.svg", 3910, 845, 14, "P-9"),
    ("Abdulloh", "Ismoilov", "Frontend", "Sergeli", "omadbek.svg", 3825, 770, 11, "F-7"),
    ("Madina", "Omonova", "Robototexnika", "Farg‘ona", "malika.svg", 3740, 895, 16, "R-7"),
    ("Yusufbek", "Sobirov", "Scratch", "Mirzo Ulug‘bek", "jasur.svg", 3680, 610, 8, "S-6"),
    ("Aziza", "Erkinova", "Python", "Yashnobod", "farzona.svg", 3590, 715, 10, "P-8"),
    ("Temurbek", "Soliyev", "Frontend", "Xadra", "bekzod.svg", 3515, 660, 7, "F-6"),
    ("Mubina", "Xasanova", "Scratch", "Samarqand", "nilufar.svg", 3440, 805, 13, "S-6"),
    ("Ibrohim", "Murodov", "Robototexnika", "Chilonzor", "omadbek.svg", 3375, 750, 12, "R-6"),
    ("Asal", "Zokirova", "Frontend", "Andijon", "malika.svg", 3290, 880, 15, "F-6"),
    ("Samandar", "Aliyev", "Python", "Keles", "jasur.svg", 3180, 590, 6, "P-7"),
    ("Muslima", "Raxmatova", "Scratch", "Yunusobod", "farzona.svg", 3095, 700, 9, "S-5"),
    ("Diyorbek", "Mahmudov", "Robototexnika", "Sergeli", "bekzod.svg", 3010, 640, 8, "R-5"),
    ("Rayona", "Saidova", "Python", "Farg‘ona", "nilufar.svg", 2945, 825, 12, "P-6"),
    ("Kamron", "Ortiqov", "Frontend", "Mirzo Ulug‘bek", "omadbek.svg", 2860, 545, 5, "F-5"),
]

SHOP_PRODUCTS = [
    ("Maktab xaltasi", "academy", 500, 5, "🎒", "linear-gradient(135deg,#ff2fd5,#7c3aed)"),
    ("Maktab krujkasi", "academy", 200, 12, "☕", "linear-gradient(135deg,#fbbf24,#f97316)"),
    ("Maktab futbolkasi", "academy", 350, 8, "👕", "linear-gradient(135deg,#22c55e,#14b8a6)"),
    ("Premium qalam seti", "academy", 150, 20, "✏️", "linear-gradient(135deg,#7c3aed,#4f46e5)"),
    ("iPhone 15", "gadget", 15000, 2, "📱", "linear-gradient(135deg,#374151,#111827)"),
    ("AirPods Pro", "gadget", 5000, 3, "🎧", "linear-gradient(135deg,#4b5563,#1f2937)"),
    ("iPad mini", "gadget", 12000, 1, "💻", "linear-gradient(135deg,#1d4ed8,#2563eb)"),
    ("Frontend olimpiada kitobi", "book", 400, 15, "📗", "linear-gradient(135deg,#f0fdf4,#dcfce7)"),
    ("Scratch darsligi", "book", 350, 10, "📘", "linear-gradient(135deg,#eff6ff,#dbeafe)"),
    ("50% chegirma kuponi", "special", 200, 1, "🎁", "linear-gradient(135deg,#ff2fd5,#f97316)"),
    ("Olimpiada ro‘yxati", "special", 1000, 5, "🏆", "linear-gradient(135deg,#7c3aed,#4f46e5)"),
]

PORTFOLIOS = [
    ("Memory Quest", "static/img/portfolio/demo-1.webp", "Rangli kartalarni juftlash, vaqt va natijani hisoblashga asoslangan interaktiv Scratch o‘yini.", "Muhammadali Sagdiyev", "Scratch", "2026"),
    ("MegaMark Store", "static/img/portfolio/demo-2.webp", "Mahsulot qidiruvi, bannerlar va qulay katalogga ega zamonaviy elektron savdo sahifasi.", "Hamidulla Mamadalimov", "Frontend", "2026"),
    ("Night Market", "static/img/portfolio/demo-3.webp", "Qorong‘i mavzu, yorqin aksentlar va moslashuvchan kartalar bilan yaratilgan e-commerce loyiha.", "Shaxriyor Zayniddinov", "UI / Web", "2025"),
    ("Eco Tracker", "static/img/portfolio/eco-tracker.svg", "Kunlik ekologik odatlarni belgilash va natijalarni sodda diagrammada ko‘rsatadigan dashboard.", "Madina Rustamova", "JavaScript", "2026"),
    ("Robot Lab", "static/img/portfolio/robot-lab.svg", "Robot sensori, motor holati va topshiriqlar ketma-ketligini boshqarish uchun yaratilgan panel.", "Azizbek Karimov", "Robototexnika", "2025"),
    ("Space Explorer", "static/img/portfolio/space-explorer.svg", "Sayyoralar haqida ma’lumot, missiyalar va animatsion kosmik xaritani birlashtirgan loyiha.", "Nilufar Sobirova", "Scratch", "2026"),
    ("Study Planner", "static/img/portfolio/study-planner.svg", "Dars jadvali, vazifalar ustuvorligi va haftalik progressni kuzatishga mo‘ljallangan ilova.", "Jasur Abdullayev", "Python / Web", "2025"),
    ("Art Gallery", "static/img/portfolio/art-gallery.svg", "O‘quvchi rasmlarini turkumlash, ko‘rish va sevimlilarga saqlash imkonini beruvchi kreativ galereya.", "Farzona Ismoilova", "Frontend", "2026"),
]

GALLERY = [
    ("Tadbir", "🎪", "12.07.2026", "1.2K", "static/img/portfolio/robot-lab.svg", "Yozgi Robototexnika Festivali", "O‘quvchilar yaratgan robotlar, jamoaviy bellashuvlar va master-klasslar bir maydonda jamlandi."),
    ("Oy qahramonlari", "🏆", "05.07.2026", "980", "static/img/about/pdp-junior-team.webp", "Iyun oyining qahramonlari aniqlandi", "Faollik, intizom va loyihalardagi yuqori natijalari bilan ajralib turgan o‘quvchilar taqdirlandi."),
    ("Marosim", "🎓", "28.06.2026", "1.6K", "static/img/hero-rocket.svg", "Bitiruvchilar uchun unutilmas kun", "Yosh dasturchilar sertifikatlarini qabul qilib, ota-onalari va mentorlar bilan yutuqlarini nishonladilar."),
    ("Tanlov", "💡", "21.06.2026", "864", "static/img/course-logos/scratch.webp", "Scratch Game Jam g‘oliblari", "Bolalar 48 soat ichida o‘z o‘yinlarini yaratib, g‘oya, dizayn va dasturlash bo‘yicha bellashdilar."),
    ("Ochiq eshiklar", "🚪", "15.06.2026", "742", "static/img/site-previews/pdp-academy-preview.svg", "Ota-onalar uchun ochiq dars", "Ota-onalar dars jarayonini kuzatib, mentorlar bilan suhbatlashdi va farzandlarining loyihalarini ko‘rdi."),
    ("Oilaviy tadbir", "👨‍👩‍👧", "08.06.2026", "690", "static/img/portfolio/study-planner.svg", "Family IT Day: birgalikda loyiha", "Ota-onalar va bolalar bir jamoa bo‘lib mini-loyiha yaratdi va natijani taqdim etdi."),
    ("Klub yangiligi", "🌍", "01.06.2026", "615", "static/img/course-logos/frontend.webp", "English Coding Club ish boshladi", "Yangi klubda o‘quvchilar texnik ingliz tili va kodni tushuntirish ko‘nikmasini rivojlantiradi."),
]

MARK_STUDENTS = [
    ("Samira", "Alimova", "farzona.svg", True),
    ("Jahongir", "Toshmatov", "omadbek.svg", True),
    ("Nilufar", "Rashidova", "nilufar.svg", False),
    ("Bekzod", "Xasanov", "bekzod.svg", True),
    ("Zulfiya", "Mirzayeva", "malika.svg", False),
    ("Abror", "Yusupov", "jasur.svg", True),
    ("Madina", "Karimova", "farzona.svg", True),
    ("Sherzod", "Nazarov", "malika.svg", False),
]

VARIABLE_QUESTIONS = [
    ("Python'da o‘zgaruvchi yaratishning to‘g‘ri ko‘rinishi qaysi?", ['name = "Ali"', 'string name = "Ali"', 'var: name = Ali', 'name == "Ali"'], "A"),
    ("Quyidagi kod natijasi nima bo‘ladi? x = 7; print(x)", ["x", "7", "print", "Xatolik"], "B"),
    ("O‘zgaruvchi nomi qaysi belgi bilan boshlanishi mumkin?", ["Raqam", "Bo‘sh joy", "Harf yoki _", "- belgisi"], "C"),
    ("x = 5 dan keyin x = 9 yozilsa, x ning qiymati nima?", ["5", "9", "14", "Xatolik"], "B"),
]


def i18n(text):
    return {"uz": text, "ru": text, "en": text}


class Command(BaseCommand):
    help = "Frontend ZIP ichidagi statik domain ma'lumotlarini database'ga yozadi."

    @transaction.atomic
    def handle(self, *args, **options):
        courses = self.seed_courses()
        branches = self.seed_branches()
        self.seed_mentors(branches)
        profiles = self.seed_students(courses, branches)
        self.seed_heroes(profiles)
        self.seed_shop()
        self.seed_portfolios()
        self.seed_gallery()
        self.seed_marks_and_dashboard(courses, branches)
        self.assign_unbranched_students(branches)
        self.seed_group_classmates()
        self.stdout.write(self.style.SUCCESS("Frontend statik ma'lumotlari database'ga muvaffaqiyatli yozildi."))

    def seed_courses(self):
        result = {}
        for order, (name, description, image_url) in enumerate(COURSES, 1):
            course, _ = Course.objects.update_or_create(
                name=name,
                defaults={
                    "description": description,
                    "image_url": image_url,
                    "sort_order": order,
                    "is_active": True,
                },
            )
            result[name] = course

        python = result["Python"]
        for module_order, (module_name, lessons) in enumerate(PYTHON_CURRICULUM, 1):
            module, _ = Module.objects.update_or_create(
                course=python,
                order=module_order,
                defaults={"name": module_name},
            )
            for lesson_order, lesson_name in enumerate(lessons, 1):
                lesson, _ = Lesson.objects.update_or_create(
                    module=module,
                    order=lesson_order,
                    defaults={"course": python, "name": lesson_name},
                )
                if module_order == 1 and lesson_order == 1:
                    for text, answers, correct in VARIABLE_QUESTIONS:
                        options = {
                            key: i18n(answer)
                            for key, answer in zip(("A", "B", "C", "D"), answers)
                        }
                        Question.objects.update_or_create(
                            lesson=lesson,
                            text=i18n(text),
                            defaults={"options": options, "correct_option": correct, "images": {}},
                        )
        return result

    def seed_branches(self):
        result = {}
        for name, address, image, district, lat, lng in BRANCHES:
            map_url = (
                f"https://www.google.com/maps?q={lat},{lng}&ll={lat},{lng}&z=16"
                if lat and lng
                else "https://www.google.com/maps/search/?api=1&query=PDP+Junior"
            )
            branch, _ = Branch.objects.update_or_create(
                name=name,
                defaults={
                    "address": address,
                    "phone": "+998 78 777-74-77",
                    "hours": "09:00–18:00",
                    "image_url": image,
                    "district": district,
                    "latitude": Decimal(lat) if lat else None,
                    "longitude": Decimal(lng) if lng else None,
                    "map_url": map_url,
                    "is_opened": Branch.OPENED,
                    "is_active": True,
                    "album": [],
                },
            )
            result[name] = branch
        return result

    def seed_mentors(self, branches):
        home_branch = branches["Chilonzor"]
        for index, (name, role, bio, avatar) in enumerate(HOME_MENTORS):
            Mentor.objects.update_or_create(
                name=name,
                defaults={
                    "role": role,
                    "bio": bio,
                    "branch": home_branch,
                    "exp": "3+ yil",
                    "students_count": "50+",
                    "working_period_start": date(2023, 1, 1) + timedelta(days=index),
                    "avatar": {"url": avatar},
                    "is_active": True,
                },
            )

    def seed_students(self, courses, branches):
        User = get_user_model()
        profiles = {}
        for index, (first, last, course_name, branch_name, avatar, total, monthly, streak, level) in enumerate(RANKING_STUDENTS, 1):
            phone = f"+99890{index:07d}"
            user, created = User.objects.get_or_create(
                phone_number=phone,
                defaults={"first_name": first, "last_name": last, "role": User.RoleChoices.STUDENT},
            )
            if created:
                user.set_unusable_password()
            user.first_name = first
            user.last_name = last
            user.role = User.RoleChoices.STUDENT
            user.is_active = True
            user.save()
            profile, _ = StudentProfile.objects.update_or_create(
                user=user,
                defaults={
                    "group_name": level,
                    "course": courses[course_name],
                    "branch": branches[branch_name],
                    "api_score": max(0, total - monthly),
                    "local_test_score": monthly,
                    "api_coin": 500,
                    "test_coin": 0,
                    "attendance_average_percent": min(100, streak * 4),
                    "streak_days": streak,
                    "avatar_url": f"static/img/avatars/{avatar}",
                },
            )
            profiles[f"{first} {last}"] = profile
        return profiles

    def seed_heroes(self, profiles):
        month_names = {
            date(2026, 8, 1): [
                ("Malika Karimova", 940), ("Jasur Abduqodirov", 1010),
                ("Farzona Usmonova", 875), ("Bekzod Mirzayev", 1085),
                ("Nilufar Xolmatova", 820), ("Omadbek Yoqubov", 790),
            ],
            date(2026, 7, 1): [
                ("Ziyoda Qodirova", 965), ("Sevinch Tursunova", 920),
                ("Muhammadali Hamidov", 890), ("Imron Akbarov", 780),
                ("Madina Omonova", 865), ("Sabrina Nematova", 845),
                ("Mubina Xasanova", 805),
            ],
            date(2026, 6, 1): [
                ("Asal Zokirova", 880), ("Rayona Saidova", 825),
                ("Mubina Xasanova", 805), ("Ibrohim Murodov", 750),
                ("Abdulloh Ismoilov", 770), ("Aziza Erkinova", 715),
            ],
        }
        for period, heroes in month_names.items():
            for name, points in heroes:
                MonthHero.objects.update_or_create(
                    student_profile=profiles[name],
                    period=period,
                    defaults={"points": points, "is_active": True},
                )

        generated_students = [
            (f"{first} {last}", seed)
            for (first, last, *_), seed in zip(
                RANKING_STUDENTS[:18],
                [11, 17, 23, 29, 31, 37, 41, 43, 47, 53, 59, 61, 67, 71, 73, 79, 83, 89],
            )
        ]
        for month_number in range(1, 13):
            if month_number in (6, 7, 8):
                continue
            period = date(2026, month_number, 1)
            for index, (name, seed) in enumerate(generated_students):
                points = 650 + ((month_number * 97 + index * 83 + seed * 41) % 431)
                MonthHero.objects.update_or_create(
                    student_profile=profiles[name],
                    period=period,
                    defaults={"points": points, "is_active": True},
                )

    def seed_shop(self):
        for name, category, price, stock, emoji, gradient in SHOP_PRODUCTS:
            CoinProduct.objects.update_or_create(
                name=name,
                defaults={
                    "description": f"{name} — PDP Junior coin do‘koni mahsuloti.",
                    "category": category,
                    "price": price,
                    "stock": stock,
                    "emoji": emoji,
                    "bg_gradient": gradient,
                    "is_active": True,
                },
            )

    def seed_portfolios(self):
        for name, image, desc, student, category, year in PORTFOLIOS:
            Portfolio.objects.update_or_create(
                name=name,
                defaults={
                    "url": "https://pdp.uz/gallery.html",
                    "image": {"url": image},
                    "desc": desc,
                    "student": student,
                    "category": category,
                    "year": year,
                    "is_active": True,
                },
            )

    def seed_gallery(self):
        for order, (category, icon, shown_date, views, image, title, description) in enumerate(GALLERY, 1):
            GalleryPost.objects.update_or_create(
                title=i18n(title),
                defaults={
                    "category": i18n(category),
                    "icon": icon,
                    "date": shown_date,
                    "views_display": views,
                    "cover_image": image,
                    "cover_contain": image.endswith(".svg"),
                    "cover_bg": "linear-gradient(135deg,#dffcff,#dffaf1)",
                    "description": i18n(description),
                    "media": [{"type": "image", "src": image, "contain": image.endswith(".svg")}],
                    "sort_order": order,
                    "is_active": True,
                },
            )

    def seed_marks_and_dashboard(self, courses, branches):
        User = get_user_model()
        python = courses["Python"]
        group = "P-9"
        rows = list(MARK_STUDENTS) + [
            ("Toxir", "Toirov", "student-custom.webp", True),
        ]
        mark_profiles = []
        for index, (first, last, avatar, verified) in enumerate(rows, 1):
            phone = "+998914530919" if first == "Toxir" else f"+99891{index:07d}"
            user, created = User.objects.get_or_create(
                phone_number=phone,
                defaults={"first_name": first, "last_name": last, "role": User.RoleChoices.STUDENT},
            )
            if created:
                user.set_unusable_password()
            user.first_name = first
            user.last_name = last
            user.role = User.RoleChoices.STUDENT
            user.is_active = True
            user.save()
            profile, _ = StudentProfile.objects.update_or_create(
                user=user,
                defaults={
                    "group_name": group,
                    "course": python,
                    "branch": branches["Chilonzor"],
                    "api_score": 0,
                    "local_test_score": 0,
                    "api_coin": 194 if first == "Toxir" else 0,
                    "test_coin": 0,
                    "attendance_average_percent": 100 if first == "Toxir" else 86,
                    "avatar_url": f"static/img/avatars/{avatar}",
                },
            )
            mark_profiles.append((profile, verified))

        start = date(2026, 5, 1)
        attendance = ["present", "present", "present", "absent", "present", "present", "present"]
        grades = [5, 4, 5, None, 5, 4, 5]
        for profile, verified in mark_profiles:
            for offset in range(7):
                grade = grades[offset]
                if profile.user.first_name == "Toxir" and offset in (1, 3):
                    grade = 5 if offset == 1 else None
                StudentMark.objects.update_or_create(
                    student_profile=profile,
                    course=python,
                    record_date=start + timedelta(days=offset),
                    defaults={
                        "attendance": "present" if profile.user.first_name == "Toxir" else attendance[offset],
                        "grade": grade,
                        "verified": verified,
                    },
                )

        toxir = next(profile for profile, _ in mark_profiles if profile.user.first_name == "Toxir")
        StudentPaymentHistory.objects.update_or_create(
            student_profile=toxir,
            external_id="frontend-demo-payment-1",
            defaults={
                "invoice_number": "PDP-2026-001",
                "amount": Decimal("750000.00"),
                "aim": "Python kursi uchun to‘lov",
                "group_name": group,
                "payment_type": "Karta",
                "date": timezone.make_aware(datetime(2026, 5, 5, 10, 0)),
                "created_date": timezone.make_aware(datetime(2026, 5, 5, 10, 0)),
                "cashier": "Online",
                "canceled": False,
                "raw_data": {"source": "frontend-static-seed"},
            },
        )

    def assign_unbranched_students(self, branches):
        StudentProfile.objects.filter(branch__isnull=True).update(
            branch=branches["Chilonzor"]
        )

    def seed_group_classmates(self):
        User = get_user_model()
        first_names = [
            "Azizbek", "Dilshod", "Jamshid", "Sardor", "Ulugbek",
            "Nodira", "Lola", "Gulnora", "Dilnoza", "Shahzoda",
        ]
        last_names = [
            "Rahimov", "Tursunov", "Ergashev", "Sattorov", "Ganiyev",
            "Saidova", "Nazarova", "Qodirova", "Karimova", "Aliyeva",
        ]
        avatars = [
            "malika.svg", "jasur.svg", "farzona.svg", "bekzod.svg",
            "nilufar.svg", "omadbek.svg",
        ]
        target_size = 10
        groups = list(
            StudentProfile.objects.exclude(branch__isnull=True)
            .exclude(group_name="")
            .values("branch_id", "group_name")
            .annotate(student_count=Count("id"))
            .order_by("branch_id", "group_name")
        )
        phone_index = 1
        for group in groups:
            sample = (
                StudentProfile.objects.filter(
                    branch_id=group["branch_id"],
                    group_name=group["group_name"],
                )
                .exclude(course__isnull=True)
                .first()
                or StudentProfile.objects.filter(
                    branch_id=group["branch_id"],
                    group_name=group["group_name"],
                ).first()
            )
            course_id = sample.course_id if sample else None
            needed = max(0, target_size - group["student_count"])
            for offset in range(needed):
                while User.objects.filter(phone_number=f"+99888{phone_index:07d}").exists():
                    phone_index += 1
                phone = f"+99888{phone_index:07d}"
                first = first_names[offset % len(first_names)]
                last = last_names[(offset + phone_index) % len(last_names)]
                user, created = User.objects.get_or_create(
                    phone_number=phone,
                    defaults={
                        "first_name": first,
                        "last_name": last,
                        "role": User.RoleChoices.STUDENT,
                    },
                )
                if created:
                    user.set_unusable_password()
                user.first_name = first
                user.last_name = last
                user.role = User.RoleChoices.STUDENT
                user.is_active = True
                user.save()
                StudentProfile.objects.update_or_create(
                    user=user,
                    defaults={
                        "group_name": group["group_name"],
                        "course_id": course_id,
                        "branch_id": group["branch_id"],
                        "api_score": 120 + ((phone_index * 17) % 380),
                        "local_test_score": 40 + ((phone_index * 11) % 160),
                        "api_coin": 80 + ((phone_index * 13) % 220),
                        "test_coin": 0,
                        "attendance_average_percent": 72 + ((phone_index * 7) % 25),
                        "streak_days": 3 + (phone_index % 12),
                        "avatar_url": f"static/img/avatars/{avatars[offset % len(avatars)]}",
                    },
                )
                phone_index += 1
