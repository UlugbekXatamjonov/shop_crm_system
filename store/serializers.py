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

StoreSettings serializerlari (BOSQICH 2):
  StoreSettingsSerializer       — GET (to'liq, 10 guruh)
  StoreSettingsUpdateSerializer — PATCH (validatsiya bilan)
"""

from rest_framework import serializers

from .models import Branch, Smena, SmenaStatus, Store, StoreSettings, StoreStatus


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
    store_name    = serializers.CharField(
        source='store.name',
        read_only=True
    )
    workers_count = serializers.SerializerMethodField()

    class Meta:
        model  = Branch
        fields = (
            'id', 'name', 'address', 'store_name',
            'phone', 'status', 'status_display',
            'workers_count',
        )

    def get_workers_count(self, obj: Branch) -> int:
        """Shu filialdagi faol xodimlar soni."""
        return obj.workers.count()


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
        extra_kwargs = {
            'name': {
                'error_messages': {
                    'required':   "Filial nomi kiritilishi shart.",
                    'blank':      "Filial nomi bo'sh bo'lishi mumkin emas.",
                    'max_length': "Filial nomi 200 belgidan oshmasligi kerak.",
                }
            },
        }

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
        extra_kwargs = {
            'name': {
                'error_messages': {
                    'blank':      "Filial nomi bo'sh bo'lishi mumkin emas.",
                    'max_length': "Filial nomi 200 belgidan oshmasligi kerak.",
                }
            },
            'status': {
                'error_messages': {
                    'invalid_choice': "'{input}' noto'g'ri holat. Mavjud: active, inactive.",
                }
            },
        }

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
    settings (do'kon sozlamalari) va open_smenas (ochiq smenalar) ham qaytariladi.
    """
    status_display = serializers.CharField(
        source='get_status_display',
        read_only=True
    )
    branches    = serializers.SerializerMethodField()
    workers     = serializers.SerializerMethodField()
    settings    = serializers.SerializerMethodField()
    open_smenas = serializers.SerializerMethodField()

    class Meta:
        model  = Store
        fields = (
            'id', 'name', 'address', 'phone',
            'status', 'status_display',
            'created_on', 'branches', 'workers',
            'settings', 'open_smenas',
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

    def get_settings(self, obj: Store) -> dict | None:
        """Do'kon sozlamalari (StoreSettings)."""
        if hasattr(obj, 'settings'):
            return StoreSettingsSerializer(obj.settings).data
        return None

    def get_open_smenas(self, obj: Store) -> list:
        """Hozirda ochiq smenalar ro'yxati."""
        qs = obj.smenas.filter(status=SmenaStatus.OPEN).select_related(
            'branch', 'worker_open__user',
        )
        return SmenaListSerializer(qs, many=True).data


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
        extra_kwargs = {
            'name': {
                'error_messages': {
                    'required':   "Do'kon nomi kiritilishi shart.",
                    'blank':      "Do'kon nomi bo'sh bo'lishi mumkin emas.",
                    'max_length': "Do'kon nomi 200 belgidan oshmasligi kerak.",
                }
            },
        }


class StoreUpdateSerializer(serializers.ModelSerializer):
    """
    Do'kon ma'lumotlarini yangilash.
    PATCH /api/v1/stores/{id}/ da ishlatiladi.
    """

    class Meta:
        model  = Store
        fields = ('name', 'address', 'phone', 'status')
        extra_kwargs = {
            'name': {
                'error_messages': {
                    'blank':      "Do'kon nomi bo'sh bo'lishi mumkin emas.",
                    'max_length': "Do'kon nomi 200 belgidan oshmasligi kerak.",
                }
            },
            'status': {
                'error_messages': {
                    'invalid_choice': "'{input}' noto'g'ri holat. Mavjud: active, inactive.",
                }
            },
        }


# ============================================================
# DO'KON SOZLAMALARI SERIALIZERLARI — BOSQICH 2
# ============================================================

class StoreSettingsSerializer(serializers.ModelSerializer):
    """
    Do'kon sozlamalarining to'liq ko'rinishi.
    GET /api/v1/settings/ da ishlatiladi.

    store va id faqat o'qish uchun — o'zgartirib bo'lmaydi.
    """
    store_name = serializers.CharField(
        source='store.name',
        read_only=True
    )

    class Meta:
        model  = StoreSettings
        fields = (
            'id', 'store', 'store_name',
            # Guruh 1 — Modul flaglari
            'subcategory_enabled', 'sale_return_enabled',
            'wastage_enabled', 'stock_audit_enabled',
            'kpi_enabled', 'price_list_enabled',
            # Guruh 2 — Valyuta
            'default_currency', 'show_usd_price', 'show_rub_price',
            # Guruh 3 — To'lov
            'allow_cash', 'allow_card', 'allow_debt',
            # Guruh 4 — Chegirma
            'allow_discount', 'max_discount_percent',
            # Guruh 5 — Chek
            'receipt_header', 'receipt_footer',
            'show_store_logo', 'show_worker_name',
            # Guruh 6 — Ombor
            'low_stock_enabled', 'low_stock_threshold',
            # Guruh 7 — Smena
            'shift_enabled', 'shifts_per_day', 'require_cash_count',
            # Guruh 8 — Telegram
            'telegram_enabled', 'telegram_chat_id',
            # Guruh 9 — Soliq/OFD
            'tax_enabled', 'tax_percent', 'ofd_enabled',
            'ofd_token', 'ofd_device_id',
            # Guruh 10 — Yetkazib beruvchi
            'supplier_credit_enabled',
        )
        read_only_fields = ('id', 'store', 'store_name')


class StoreSettingsUpdateSerializer(serializers.ModelSerializer):
    """
    Do'kon sozlamalarini yangilash.
    PATCH /api/v1/settings/{id}/ da ishlatiladi.
    Barcha maydonlar ixtiyoriy (partial=True).

    Validatsiyalar:
      - max_discount_percent: 0–100 oralig'ida bo'lishi shart
      - tax_percent: 0–100 oralig'ida bo'lishi shart
      - shifts_per_day: faqat 1, 2 yoki 3 qabul qilinadi
      - telegram_chat_id: telegram_enabled=True bo'lsa majburiy
      - allow_cash + allow_card: ikkalasi ham False bo'lmasligi shart
    """

    class Meta:
        model  = StoreSettings
        fields = (
            # Guruh 1 — Modul flaglari
            'subcategory_enabled', 'sale_return_enabled',
            'wastage_enabled', 'stock_audit_enabled',
            'kpi_enabled', 'price_list_enabled',
            # Guruh 2 — Valyuta
            'default_currency', 'show_usd_price', 'show_rub_price',
            # Guruh 3 — To'lov
            'allow_cash', 'allow_card', 'allow_debt',
            # Guruh 4 — Chegirma
            'allow_discount', 'max_discount_percent',
            # Guruh 5 — Chek
            'receipt_header', 'receipt_footer',
            'show_store_logo', 'show_worker_name',
            # Guruh 6 — Ombor
            'low_stock_enabled', 'low_stock_threshold',
            # Guruh 7 — Smena
            'shift_enabled', 'shifts_per_day', 'require_cash_count',
            # Guruh 8 — Telegram
            'telegram_enabled', 'telegram_chat_id',
            # Guruh 9 — Soliq/OFD
            'tax_enabled', 'tax_percent', 'ofd_enabled',
            'ofd_token', 'ofd_device_id',
            # Guruh 10 — Yetkazib beruvchi
            'supplier_credit_enabled',
        )

    def validate_max_discount_percent(self, value):
        """Chegirma foizi 0 dan 100 gacha bo'lishi shart."""
        if value < 0 or value > 100:
            raise serializers.ValidationError(
                "Chegirma foizi 0 dan 100 gacha bo'lishi shart."
            )
        return value

    def validate_tax_percent(self, value):
        """Soliq foizi 0 dan 100 gacha bo'lishi shart."""
        if value < 0 or value > 100:
            raise serializers.ValidationError(
                "Soliq foizi 0 dan 100 gacha bo'lishi shart."
            )
        return value

    def validate_shifts_per_day(self, value):
        """Smena soni faqat 1, 2 yoki 3 bo'lishi mumkin."""
        if value not in (1, 2, 3):
            raise serializers.ValidationError(
                "Kunlik smena soni 1, 2 yoki 3 bo'lishi shart."
            )
        return value

    def validate(self, attrs):
        """Bir necha maydon bir vaqtda tekshiriladigan validatsiyalar."""

        # Telegram: enabled bo'lsa chat_id majburiy
        telegram_enabled = attrs.get(
            'telegram_enabled',
            self.instance.telegram_enabled if self.instance else False
        )
        telegram_chat_id = attrs.get(
            'telegram_chat_id',
            self.instance.telegram_chat_id if self.instance else None
        )
        if telegram_enabled and not telegram_chat_id:
            raise serializers.ValidationError({
                'telegram_chat_id': "Telegram yoqilgan bo'lsa, chat ID kiritilishi shart."
            })

        # To'lov: naqd ham, karta ham o'chirilmasligi kerak
        allow_cash = attrs.get(
            'allow_cash',
            self.instance.allow_cash if self.instance else True
        )
        allow_card = attrs.get(
            'allow_card',
            self.instance.allow_card if self.instance else True
        )
        if not allow_cash and not allow_card:
            raise serializers.ValidationError({
                'allow_cash': "Naqd va karta to'lov ikkalasi ham o'chirilishi mumkin emas."
            })

        return attrs


# ============================================================
# SMENA SERIALIZERLARI — BOSQICH 3
# ============================================================

class SmenaListSerializer(serializers.ModelSerializer):
    """
    Smenalar ro'yxati uchun qisqa serializer.
    GET /api/v1/shifts/ da ishlatiladi.
    """
    branch_name      = serializers.CharField(source='branch.name', read_only=True)
    status_display   = serializers.CharField(source='get_status_display', read_only=True)
    worker_open_name = serializers.SerializerMethodField()

    class Meta:
        model  = Smena
        fields = (
            'id', 'branch', 'branch_name',
            'status', 'status_display',
            'start_time', 'end_time',
            'worker_open_name',
        )

    def get_worker_open_name(self, obj: Smena) -> str:
        return str(obj.worker_open.user) if obj.worker_open else None


class SmenaDetailSerializer(serializers.ModelSerializer):
    """
    Smenaning to'liq ma'lumoti.
    GET /api/v1/shifts/{id}/ va close/x-report action da ishlatiladi.
    """
    branch_name       = serializers.CharField(source='branch.name', read_only=True)
    store_name        = serializers.CharField(source='store.name',  read_only=True)
    status_display    = serializers.CharField(source='get_status_display', read_only=True)
    worker_open_name  = serializers.SerializerMethodField()
    worker_close_name = serializers.SerializerMethodField()

    class Meta:
        model  = Smena
        fields = (
            'id',
            'branch', 'branch_name',
            'store',  'store_name',
            'status', 'status_display',
            'worker_open',  'worker_open_name',
            'worker_close', 'worker_close_name',
            'start_time', 'end_time',
            'cash_start', 'cash_end',
            'note',
        )

    def get_worker_open_name(self, obj: Smena) -> str | None:
        return str(obj.worker_open.user) if obj.worker_open else None

    def get_worker_close_name(self, obj: Smena) -> str | None:
        return str(obj.worker_close.user) if obj.worker_close else None


class SmenaOpenSerializer(serializers.ModelSerializer):
    """
    Smena ochish uchun serializer.
    POST /api/v1/shifts/ da ishlatiladi.

    Maydonlar:
      branch     — Qaysi filialda smena ochilmoqda (majburiy)
      cash_start — Boshlang'ich naqd miqdori (ixtiyoriy, default=0)
                   require_cash_count=True bo'lsa views.py da majburiy tekshiriladi
      note       — Izoh (ixtiyoriy)

    store, worker_open, status — views.py perform_create da avtomatik to'ldiriladi.
    """

    class Meta:
        model  = Smena
        fields = ('branch', 'cash_start', 'note')
        extra_kwargs = {
            'branch': {
                'error_messages': {
                    'required':        "Filial tanlanishi shart.",
                    'does_not_exist':  "Bunday filial topilmadi.",
                    'incorrect_type':  "Filial ID butun son bo'lishi kerak.",
                }
            },
            'cash_start': {
                'required': False,
                'error_messages': {
                    'invalid': "To'g'ri pul miqdori kiritilishi shart.",
                }
            },
            'note': {'required': False},
        }


class SmenaCloseSerializer(serializers.ModelSerializer):
    """
    Smena yopish uchun serializer.
    PATCH /api/v1/shifts/{id}/close/ da ishlatiladi.

    Maydonlar:
      cash_end — Yakuniy naqd miqdori (ixtiyoriy)
                 require_cash_count=True bo'lsa views.py da majburiy tekshiriladi
      note     — Izoh (ixtiyoriy, yangilanadi)

    worker_close, end_time, status — views.py close action da avtomatik to'ldiriladi.
    """

    class Meta:
        model  = Smena
        fields = ('cash_end', 'note')
        extra_kwargs = {
            'cash_end': {'required': False},
            'note':     {'required': False},
        }
