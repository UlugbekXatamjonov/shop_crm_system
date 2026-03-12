# #start — Kunlik sessiya boshlash buyrug'i

Har yangi chat/session boshida quyidagi 5 ta ishni bajar:

## 1. PROJECT_CONTEXT o'qi
`.claude/worktrees/compassionate-swanson/PROJECT_CONTEXT.md` faylini o'qi (yoki mavjud worktree/main dagi `PROJECT_CONTEXT.md`).
Asosiy ma'lumotlar: loyiha holati, qoidalar, arxitektura, tugallangan/qolgan bosqichlar.

## 2. Kodni ko'zdan kechir
Oxirgi commit larni ko'r: `git log --oneline -10`
Yangi o'zgartirilgan fayllarni tekshir: `git show HEAD --stat`
Asosiy app fayllarini skanla: models, views, serializers, migrations.

## 3. Muammo va konfliktlarni aniqlа
- `python manage.py check --settings=config.settings.local` — Django system check
- `python manage.py showmigrations --settings=config.settings.local` — qo'llanilmagan migration lar
- Import xatolari, o'zaro konfliktlar, qoidabuzarliklar (is_active o'rniga status ishlatilganmi? va h.k.)
- `project_problems.txt` faylini tekshir

## 4. Kecha bajarilgan ishlar haqida habar ber
Oxirgi sessiyadan (bugungi sanadan oldingi) git commitlarni tahlil qil:
`git log --oneline --since="yesterday"` yoki `git log --oneline -5`
Har bir commit uchun: nima qilindi, qaysi fayllar, qaysi bosqich (B7, B8...).

## 5. Keyingi qilish kerak bo'lgan ishlar
PROJECT_CONTEXT dagi "LOYIHA HOLATI" jadvalidan ❌ Boshlanmagan bosqichlarni sanab ber.
Ustuvorlik tartibida: qaysi bosqich birinchi, nima uchun, qanday boshlash kerak.

---
**Eslatma:** Barcha natijani o'zbek tilida chiqar. Aniq, qisqa, tuzilgan formatda.
