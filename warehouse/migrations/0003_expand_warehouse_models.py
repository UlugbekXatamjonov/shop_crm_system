# Eski dizayn (Warehouse modeli, from_branch/to_branch) bekor qilindi.
# Loyiha soddalashtirildi — StockMovement da oddiy branch FK qoldi.
# Bu migration zanjir davomiyligini saqlash uchun saqlanadi.

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('warehouse', '0002_alter_product_unique_together'),
    ]

    operations = [
        # Intentionally empty — design was reverted to simple branch FK
    ]
