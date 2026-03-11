"""
============================================================
EXPENSE APP — Xarajatlar API URL'lari
============================================================
Prefix: /api/v1/

Router avtomatik quyidagi URL'larni yaratadi:

  GET    /api/v1/expense-categories/         — xarajat kategoriyalari ro'yxati (?status=active|inactive)
  POST   /api/v1/expense-categories/         — yangi kategoriya (IsManagerOrAbove)
  GET    /api/v1/expense-categories/{id}/    — kategoriya tafsilotlari
  PATCH  /api/v1/expense-categories/{id}/    — kategoriya yangilash (IsManagerOrAbove)
  DELETE /api/v1/expense-categories/{id}/    — kategoriya nofaol qilish (IsManagerOrAbove, soft)

  GET    /api/v1/expenses/                   — xarajatlar ro'yxati (?branch=id, ?category=id, ?smena=id, ?date=YYYY-MM-DD)
  POST   /api/v1/expenses/                   — yangi xarajat (CanAccess('xarajatlar'))
  GET    /api/v1/expenses/{id}/              — xarajat tafsilotlari
  PATCH  /api/v1/expenses/{id}/              — xarajat yangilash (IsManagerOrAbove)
  DELETE /api/v1/expenses/{id}/              — xarajat o'chirish (IsManagerOrAbove, hard)
"""

from rest_framework.routers import DefaultRouter

from .views import ExpenseCategoryViewSet, ExpenseViewSet

router = DefaultRouter()
router.register(r'expense-categories', ExpenseCategoryViewSet, basename='expense-category')
router.register(r'expenses',           ExpenseViewSet,          basename='expense')

urlpatterns = router.urls
