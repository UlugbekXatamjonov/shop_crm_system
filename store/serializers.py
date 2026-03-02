"""
============================================================
STORE APP — Serializerlar
============================================================
Har bir ViewSet action uchun alohida serializer:
  list    → ListSerializer    (qisqa, jadval uchun)
  retrieve → DetailSerializer (to'liq ma'lumot)
  create  → CreateSerializer  (yangi obyekt yaratish)
  update  → UpdateSerializer  (ma'lumotlarni yangilash)

Tartib: Branch serializers birinchi (StoreDetailSerializer
        ular ga murojaat qiladi).
"""

from rest_framework import serializers

from .models import Branch, Store, StoreStatus


def _worker_short(worker) -> dict:
    """Hodimning qisqa ma'lumoti: id va to'liq ismi."""
    return {'id': worker.id, 'full_name': str(worker.user)}


# ============================================================
# FILIAL SERIALIZERLARI
# ============================================================

class BranchListSerializer(serializers.ModelSerializer):
    """
    Filiallar ro'yxati uchun qisqa serializer.
    GET /api/v1/branches/ da ishlatiladi.
    """
    status_display = serializers.CharField(
        source='get_status_display',
        read_only=True
    )
    store_id = serializers.IntegerField(
        source='store.id',
        read_only=True
    )
    store_name = serializers.CharField(
        source='store.name',
        read_only=True
    )

    class Meta:
        model  = Branch
        fields = ('id', 'name', 'store_id', 'store_name', 'phone', 'status', 'status_display')


class BranchDetailSerializer(serializers.ModelSerializer):
    """
    Filialning to'liq ma'lumoti.
    GET /api/v1/branches/{id}/ da ishlatiladi.
    """
    status_display = serializers.CharField(
        source='get_status_display',
        read_only=True
    )
    store_name = serializers.CharField(
        source='store.name',
        read_only=True
    )
    store_id = serializers.IntegerField(
        source='store.id',
        read_only=True
    )
    workers = serializers.SerializerMethodField()

    class Meta:
        model  = Branch
        fields = (
            'id', 'name', 'address', 'phone',
            'store_id', 'store_name',
            'status', 'status_display',
            'created_on', 'workers',
        )

    def get_workers(self, obj: Branch) -> list:
        """Shu filialdagi barcha xodimlar (id + to'liq ismi)."""
        return [
            _worker_short(w)
            for w in obj.workers.select_related('user').order_by('user__first_name')
        ]


class BranchCreateSerializer(serializers.ModelSerializer):
    """
    Yangi filial yaratish.
    POST /api/v1/branches/ da ishlatiladi.
    store maydoni view da avtomatik beriladi (perform_create).
    """

    class Meta:
        model  = Branch
        fields = ('name', 'address', 'phone')

    def validate_name(self, value: str) -> str:
        """Bir do'kon ichida filial nomi takrorlanmasligi kerak."""
        store = self.context.get('store')
        if store and Branch.objects.filter(store=store, name=value).exists():
            raise serializers.ValidationError(
                "Bu nomli filial ushbu do'konda allaqachon mavjud."
            )
        return value


class BranchUpdateSerializer(serializers.ModelSerializer):
    """
    Filial ma'lumotlarini yangilash.
    PATCH /api/v1/branches/{id}/ da ishlatiladi.
    """

    class Meta:
        model  = Branch
        fields = ('name', 'address', 'phone', 'status')

    def validate_name(self, value: str) -> str:
        """Bir do'kon ichida filial nomi takrorlanmasligi kerak."""
        qs = Branch.objects.filter(
            store=self.instance.store, name=value
        ).exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError(
                "Bu nomli filial ushbu do'konda allaqachon mavjud."
            )
        return value


# ============================================================
# DO'KON SERIALIZERLARI
# ============================================================

class StoreListSerializer(serializers.ModelSerializer):
    """
    Do'konlar ro'yxati uchun qisqa serializer.
    GET /api/v1/stores/ da ishlatiladi.
    """
    status_display = serializers.CharField(
        source='get_status_display',
        read_only=True
    )
    branch_count = serializers.SerializerMethodField()

    class Meta:
        model  = Store
        fields = ('id', 'name', 'phone', 'status', 'status_display', 'branch_count')

    def get_branch_count(self, obj: Store) -> int:
        return obj.branches.filter(status=StoreStatus.ACTIVE).count()


class StoreDetailSerializer(serializers.ModelSerializer):
    """
    Do'konning to'liq ma'lumoti.
    GET /api/v1/stores/{id}/ da ishlatiladi.
    """
    status_display = serializers.CharField(
        source='get_status_display',
        read_only=True
    )
    branches = serializers.SerializerMethodField()
    workers  = serializers.SerializerMethodField()

    class Meta:
        model  = Store
        fields = (
            'id', 'name', 'address', 'phone',
            'status', 'status_display',
            'created_on', 'branches', 'workers',
        )

    def get_branches(self, obj: Store) -> list:
        qs = obj.branches.filter(status=StoreStatus.ACTIVE).order_by('name')
        return BranchListSerializer(qs, many=True).data

    def get_workers(self, obj: Store) -> list:
        """Do'konga tegishli barcha xodimlar (id + to'liq ismi)."""
        return [
            _worker_short(w)
            for w in obj.workers.select_related('user').order_by('user__first_name')
        ]


class StoreCreateSerializer(serializers.ModelSerializer):
    """
    Yangi do'kon yaratish.
    POST /api/v1/stores/ da ishlatiladi.
    Faqat owner yarata oladi.
    Store.name global unique emas — har bir owner o'z nomini erkin tanlaydi.
    """

    class Meta:
        model  = Store
        fields = ('name', 'address', 'phone')


class StoreUpdateSerializer(serializers.ModelSerializer):
    """
    Do'kon ma'lumotlarini yangilash.
    PATCH /api/v1/stores/{id}/ da ishlatiladi.
    """

    class Meta:
        model  = Store
        fields = ('name', 'address', 'phone', 'status')
