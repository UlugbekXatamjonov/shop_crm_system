"""
============================================================
AUDIT MIXIN — ViewSet'lar uchun log yozish yordamchisi
============================================================

Ishlatish:
    class MyViewSet(AuditMixin, viewsets.ModelViewSet):
        ...
        def perform_create(self, serializer):
            instance = serializer.save(store=worker.store)
            self._audit_log(AuditLog.Action.CREATE, instance)

        def perform_update(self, serializer):
            instance = serializer.save()
            self._audit_log(AuditLog.Action.UPDATE, instance)

        def perform_destroy(self, instance):
            self._audit_log(AuditLog.Action.DELETE, instance)
            instance.delete()

Tavsif avtomatik shakllanadi:
    CREATE → "Mahsulot yaratildi: 'Coca-Cola 0.5L'"
    UPDATE → "Mahsulot yangilandi: 'Coca-Cola 0.5L'"
    DELETE → "Mahsulot o'chirildi: 'Coca-Cola 0.5L'"

Maxsus tavsif kerak bo'lsa — description parametrini bering:
    self._audit_log(AuditLog.Action.CREATE, instance,
                    description="Kirim: 'Coca-Cola' × 10 (Filial 1)")
"""

from accaunt.models import AuditLog


# Amal → o'zbek fe'li
_ACTION_VERB = {
    AuditLog.Action.CREATE: 'yaratildi',
    AuditLog.Action.UPDATE: 'yangilandi',
    AuditLog.Action.DELETE: "o'chirildi",
    AuditLog.Action.ASSIGN: 'tayinlandi',
}


class AuditMixin:
    """
    ViewSet'larga `_audit_log()` yordamchi metodini qo'shadigan mixin.

    Bu mixin perform_create/update/destroy ni o'zgartirmaydi —
    faqat `_audit_log()` metodini taqdim etadi.
    ViewSet o'zi perform_* metodlarida `self._audit_log(...)` chaqiradi.
    """

    def _audit_log(
        self,
        action: str,
        obj,
        description: str = '',
        extra_data: dict = None,
    ) -> None:
        """
        AuditLog yozuvi yaratadi.

        Parametrlar:
            action      — AuditLog.Action.CREATE / UPDATE / DELETE / ASSIGN
            obj         — log yoziladigan model obyekti
            description — ixtiyoriy; bo'sh bo'lsa avtomatik shakllanadi
            extra_data  — ixtiyoriy JSON (eski/yangi qiymatlar va h.k.)

        Avtomatik tavsif formati:
            "{Model verbose_name} {fe'l}: '{obj}'"
        Misol:
            "Mahsulot yaratildi: 'Coca-Cola 0.5L'"
            "Xodim o'chirildi: 'Alisher Karimov (Sotuvchi)'"
        """
        if not description:
            verb        = _ACTION_VERB.get(action, action)
            model_label = obj._meta.verbose_name.capitalize()
            description = f"{model_label} {verb}: '{obj}'"

        AuditLog.objects.create(
            actor       = self.request.user,
            action      = action,
            target_model= obj.__class__.__name__,
            target_id   = obj.pk,
            description = description,
            extra_data  = extra_data,
        )
