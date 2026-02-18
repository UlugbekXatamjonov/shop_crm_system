from django.apps import AppConfig


class ExpenseConfig(AppConfig):
    """Xarajatlar ilovasi konfiguratsiyasi"""
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'expense'
    verbose_name = 'Xarajatlar'
