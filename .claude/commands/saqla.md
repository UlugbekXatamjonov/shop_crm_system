# #saqla — Kunlik sessiyani yakunlash va saqlash buyrug'i

Sessiya oxirida quyidagi 4 ta ishni tartib bilan bajar:

## 1. Barcha qilingan ishlarni PROJECT_CONTEXT ga saqlа

`PROJECT_CONTEXT.md` faylini yangilа:
- Fayl boshiga bugungi sana bilan yangi SESSION bloki qo'sh (## 📅 DD.MM.YYYY SESSION — QILINGAN ISHLAR)
- Har bir qilingan ish uchun: nima qilindi, qaysi fayllar o'zgartirildi, qaysi endpoint lar qo'shildi
- "LOYIHA HOLATI" jadvalini yangilа — tugallangan bosqichlarni ✅ ga, boshlanganlarini o'zgartir
- Yangi model/serializer/endpoint lar bo'lsa tegishli app bo'limiga qo'sh
- Eski ma'lumotlar o'chirilmaydi — faqat yangilari qo'shiladi

## 2. Barcha o'zgarishlarni main branchga merge qil

Quyidagi tartibda bajar:
```bash
# 1. Hozirgi branch da uncommitted o'zgarish bo'lsa commit qil
git add <o'zgartirilgan fayllar>
git commit -m "feat(...): <qilingan ishlar qisqacha>"

# 2. main ga o'tib merge qil
git checkout main
git merge <hozirgi_branch> --no-ff -m "merge: <bosqich nomi> — <qisqacha izoh>"

# 3. Muvaffaqiyatli bo'lsa hozirgi branchga qayt
git checkout <hozirgi_branch>
```
⚠️ Merge konflikt bo'lsa — foydalanuvchiga xabar ber, o'zing hal qilma.

## 3. Barcha o'zgarishlarni GitHub ga yukla

```bash
# main branchni push qil
git push origin main

# Worktree branchini ham push qil (ixtiyoriy)
git push origin <hozirgi_branch>
```
⚠️ Push oldidan foydalanuvchidan tasdiqlash so'ra: "Main branchni GitHub ga yuklayman, rozimisiz?"

## 4. Bugungi qilingan ishlar haqida batafsil habar ber

Quyidagi formatda chiqar:

---
### 📋 Bugungi sessiya xulosasi (DD.MM.YYYY)

**Bajarilgan bosqichlar:**
- B? — [bosqich nomi]: [nima qilindi]

**O'zgartirilgan fayllar:**
- `app/fayl.py` — [nima o'zgartirildi]

**Yangi endpointlar:**
- `METHOD /api/v1/...` — [izoh]

**Yangi migration lar:**
- `app/migrations/XXXX_name.py`

**Keyingi sessiya uchun eslatma:**
- [qolgan ishlar, muammolar, diqqat qilish kerak bo'lgan joylar]
---
