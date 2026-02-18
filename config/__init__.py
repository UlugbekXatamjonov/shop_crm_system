# Celery ilovasini Django bilan integratsiya qilish
# Bu import Django ishga tushganda Celery ham avtomatik yuklanishini ta'minlaydi
from .celery import app as celery_app

__all__ = ('celery_app',)
