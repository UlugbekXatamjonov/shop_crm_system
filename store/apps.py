from django.apps import AppConfig


class StoreConfig(AppConfig):
    """
    Do'kon, filial va sozlamalar ilovasi konfiguratsiyasi.

    ready() — signals.py ni import qilib signallarni ulaydi.
    ⚠️ QOIDA 1: create_store_settings signal shu yerda ishga tushadi.
    """
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'store'
    verbose_name = "Do'konlar"

    def ready(self) -> None:
        """Signal'larni ulash — Django ilovasi tayyor bo'lgandan keyin."""
        import store.signals  # noqa: F401
