"""
============================================================
TRADE APP — Serializerlar
============================================================
Serializerlar:
  CustomerGroupListSerializer   — GET /customer-groups/
  CustomerGroupCreateSerializer — POST/PATCH /customer-groups/
  CustomerListSerializer        — GET /customers/
  CustomerDetailSerializer      — GET /customers/{id}/
  CustomerCreateSerializer      — POST /customers/
  CustomerUpdateSerializer      — PATCH /customers/{id}/
  SaleItemListSerializer        — SaleDetail ichida nested
  SaleItemInputSerializer       — SaleCreate uchun input
  SaleListSerializer            — GET /sales/
  SaleDetailSerializer          — GET /sales/{id}/  +  cancel/close javobida
  SaleCreateSerializer          — POST /sales/ uchun input validatsiya
"""

from decimal import Decimal

from rest_framework import serializers

from store.models import Branch

from warehouse.models import Product

from .models import (
    Customer,
    CustomerGroup,
    CustomerStatus,
    PaymentType,
    Sale,
    SaleItem,
    SaleStatus,
)


# ============================================================
# MIJOZ GURUHI SERIALIZERLARI
# ============================================================

class CustomerGroupListSerializer(serializers.ModelSerializer):
    """Mijoz guruhlari ro'yxati. GET /api/v1/customer-groups/"""

    class Meta:
        model  = CustomerGroup
        fields = ('id', 'name', 'discount', 'created_on')


class CustomerGroupCreateSerializer(serializers.ModelSerializer):
    """
    Mijoz guruhi yaratish/yangilash.
    POST/PATCH /api/v1/customer-groups/

    store — ViewSet da avtomatik (worker.store).
    """

    class Meta:
        model  = CustomerGroup
        fields = ('name', 'discount')
        extra_kwargs = {
            'name': {
                'error_messages': {
                    'required':   "Guruh nomi kiritilishi shart.",
                    'blank':      "Guruh nomi bo'sh bo'lishi mumkin emas.",
                    'max_length': "Guruh nomi 100 belgidan oshmasligi kerak.",
                }
            },
            'discount': {
                'required': False,
                'default': Decimal('0'),
                'error_messages': {
                    'invalid':    "To'g'ri chegirma foizi kiritilishi shart.",
                    'max_digits': "Chegirma foizi juda katta.",
                }
            },
        }

    def validate_name(self, value: str) -> str:
        request = self.context.get('request')
        worker  = getattr(request.user, 'worker', None) if request else None
        store   = worker.store if worker else None
        if store:
            qs = CustomerGroup.objects.filter(store=store, name=value)
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError(
                    "Bunday nomli Mijoz guruhi mavjud. Iltimos boshqa nom tanlang !"
                )
        return value

    def validate_discount(self, value: Decimal) -> Decimal:
        if value < 0 or value > 100:
            raise serializers.ValidationError(
                "Chegirma 0 dan 100 gacha bo'lishi kerak."
            )
        return value


# ============================================================
# MIJOZ SERIALIZERLARI
# ============================================================

class CustomerListSerializer(serializers.ModelSerializer):
    """Mijozlar ro'yxati. GET /api/v1/customers/"""
    group_name     = serializers.CharField(
        source='group.name', read_only=True, allow_null=True, default=None,
    )
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model  = Customer
        fields = (
            'id', 'name', 'phone', 'debt_balance',
            'group', 'group_name',
            'status', 'status_display',
            'created_on',
        )


class CustomerDebtSaleSerializer(serializers.ModelSerializer):
    """Mijozning nasiya sotuvlari — CustomerDetailSerializer ichida nested."""
    class Meta:
        model  = Sale
        fields = (
            'id', 'total_price', 'paid_amount', 'debt_amount',
            'status', 'created_on',
        )


class CustomerDetailSerializer(serializers.ModelSerializer):
    """Mijoz to'liq ma'lumoti. GET /api/v1/customers/{id}/"""
    group_name     = serializers.CharField(
        source='group.name', read_only=True, allow_null=True, default=None,
    )
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    debt_sales     = serializers.SerializerMethodField()

    class Meta:
        model  = Customer
        fields = (
            'id', 'name', 'phone', 'address', 'debt_balance',
            'group', 'group_name',
            'status', 'status_display',
            'created_on',
            'debt_sales',
        )

    def get_debt_sales(self, obj: Customer) -> list:
        """Mijozning barcha nasiya sotuvlari (yakunlangan, qarzi bor)."""
        sales = obj.sales.filter(
            payment_type=PaymentType.DEBT,
            debt_amount__gt=0,
            status=SaleStatus.COMPLETED,
        ).order_by('-created_on')
        return CustomerDebtSaleSerializer(sales, many=True).data


class CustomerCreateSerializer(serializers.ModelSerializer):
    """
    Mijoz yaratish. POST /api/v1/customers/
    store — ViewSet da avtomatik (worker.store).
    """

    class Meta:
        model  = Customer
        fields = ('name', 'phone', 'address', 'group')
        extra_kwargs = {
            'name': {
                'error_messages': {
                    'required':   "Mijoz nomi kiritilishi shart.",
                    'blank':      "Mijoz nomi bo'sh bo'lishi mumkin emas.",
                    'max_length': "Mijoz nomi 200 belgidan oshmasligi kerak.",
                }
            },
            'phone':   {'required': False, 'allow_blank': True},
            'address': {'required': False, 'allow_blank': True},
            'group': {
                'required':   False,
                'allow_null': True,
                'error_messages': {
                    'does_not_exist': "Bunday mijoz guruhi topilmadi.",
                    'incorrect_type': "Guruh ID butun son bo'lishi kerak.",
                }
            },
        }


class CustomerUpdateSerializer(serializers.ModelSerializer):
    """
    Mijoz yangilash. PATCH /api/v1/customers/{id}/
    status ham o'zgartirish mumkin (active|inactive).
    """

    class Meta:
        model  = Customer
        fields = ('name', 'phone', 'address', 'group', 'status')
        extra_kwargs = {
            'name': {
                'required': False,
                'error_messages': {
                    'blank':      "Mijoz nomi bo'sh bo'lishi mumkin emas.",
                    'max_length': "Mijoz nomi 200 belgidan oshmasligi kerak.",
                }
            },
            'phone':   {'required': False, 'allow_blank': True},
            'address': {'required': False, 'allow_blank': True},
            'group': {
                'required':   False,
                'allow_null': True,
                'error_messages': {
                    'does_not_exist': "Bunday mijoz guruhi topilmadi.",
                    'incorrect_type': "Guruh ID butun son bo'lishi kerak.",
                }
            },
            'status': {
                'required': False,
                'error_messages': {
                    'invalid_choice': "'{input}' noto'g'ri holat. Mavjud: active, inactive.",
                }
            },
        }


# ============================================================
# SOTUV SERIALIZERLARI
# ============================================================

class SaleItemListSerializer(serializers.ModelSerializer):
    """
    Sotuv elementlari (SaleDetail ichida nested ko'rsatish).
    Read-only.
    """
    product_name = serializers.CharField(source='product.name', read_only=True)
    unit         = serializers.CharField(source='product.get_unit_display', read_only=True)

    class Meta:
        model  = SaleItem
        fields = (
            'id', 'product', 'product_name', 'unit',
            'quantity', 'unit_price', 'total_price',
        )


class SaleItemInputSerializer(serializers.Serializer):
    """
    Sotuv yaratishda har bir mahsulot uchun input.
    SaleCreateSerializer.items da ishlatiladi.

    unit_price berilmasa → product.sale_price ishlatiladi (views.py da).
    """
    product    = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.filter(status='active'),
        error_messages={
            'required':       "Mahsulot tanlanishi shart.",
            'does_not_exist': "Bunday mahsulot topilmadi yoki u faol emas.",
            'incorrect_type': "Mahsulot ID butun son bo'lishi kerak.",
        }
    )
    quantity   = serializers.DecimalField(
        max_digits=10,
        decimal_places=3,
        min_value=Decimal('0.001'),
        error_messages={
            'required':   "Miqdor kiritilishi shart.",
            'invalid':    "To'g'ri miqdor kiritilishi shart.",
            'min_value':  "Miqdor 0 dan katta bo'lishi kerak.",
            'max_digits': "Miqdor juda katta.",
        }
    )
    unit_price = serializers.DecimalField(
        max_digits=15,
        decimal_places=2,
        min_value=Decimal('0'),
        required=False,
        allow_null=True,
        default=None,
        error_messages={
            'invalid':   "To'g'ri narx kiritilishi shart.",
            'min_value': "Narx manfiy bo'lishi mumkin emas.",
        }
    )


class SaleListSerializer(serializers.ModelSerializer):
    """Sotuvlar ro'yxati. GET /api/v1/sales/"""
    branch_name          = serializers.CharField(source='branch.name', read_only=True)
    worker_name          = serializers.SerializerMethodField()
    customer_name        = serializers.SerializerMethodField()
    payment_type_display = serializers.CharField(
        source='get_payment_type_display', read_only=True,
    )
    status_display       = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model  = Sale
        fields = (
            'id', 'branch', 'branch_name',
            'worker_name', 'customer', 'customer_name',
            'payment_type', 'payment_type_display',
            'total_price', 'discount_amount', 'paid_amount', 'debt_amount',
            'status', 'status_display',
            'created_on',
        )

    def get_worker_name(self, obj: Sale) -> str | None:
        try:
            return str(obj.worker.user)
        except AttributeError:
            return None

    def get_customer_name(self, obj: Sale) -> str | None:
        return obj.customer.name if obj.customer else None


class SaleDetailSerializer(serializers.ModelSerializer):
    """
    Sotuv to'liq ma'lumoti + elementlar.
    GET /api/v1/sales/{id}/  va  cancel action javobida ishlatiladi.
    """
    branch_name          = serializers.CharField(source='branch.name', read_only=True)
    worker_name          = serializers.SerializerMethodField()
    customer_name        = serializers.SerializerMethodField()
    smena_id             = serializers.PrimaryKeyRelatedField(
        source='smena', read_only=True,
    )
    payment_type_display = serializers.CharField(
        source='get_payment_type_display', read_only=True,
    )
    status_display       = serializers.CharField(source='get_status_display', read_only=True)
    items                = SaleItemListSerializer(many=True, read_only=True)

    class Meta:
        model  = Sale
        fields = (
            'id', 'branch', 'branch_name',
            'worker', 'worker_name',
            'customer', 'customer_name',
            'smena_id',
            'payment_type', 'payment_type_display',
            'total_price', 'discount_amount', 'paid_amount', 'debt_amount',
            'status', 'status_display',
            'note', 'created_on',
            'items',
        )

    def get_worker_name(self, obj: Sale) -> str | None:
        try:
            return str(obj.worker.user)
        except AttributeError:
            return None

    def get_customer_name(self, obj: Sale) -> str | None:
        return obj.customer.name if obj.customer else None


class SaleCreateSerializer(serializers.Serializer):
    """
    Sotuv yaratish uchun input serializer.
    POST /api/v1/sales/

    ⚠️ Bu serializer Serializer (ModelSerializer emas) chunki:
       - items write-only, model maydoni emas
       - total_price, debt_amount, store, worker, smena — views.py da hisoblanadi/to'ldiriladi

    Validatsiya:
      - items: kamida 1 ta mahsulot bo'lishi shart
      - discount_amount: 0 dan katta bo'lmagan chegirma foizi
      - paid_amount: to'lov turi va qoidalarga mos bo'lishi shart (views.py da)

    Business logika views.py SaleViewSet.create() da:
      1. Settings validatsiya (allow_cash, allow_card, allow_debt, allow_discount)
      2. shift_enabled → ochiq smena tekshirish
      3. Stock qoldig'i tekshirish (select_for_update)
      4. Sale + SaleItem yaratish
      5. StockMovement(OUT) + Stock yangilash
      6. Customer.debt_balance yangilash
    """
    branch          = serializers.PrimaryKeyRelatedField(
        queryset=Branch.objects.all(),
        error_messages={
            'required':       "Filial tanlanishi shart.",
            'does_not_exist': "Bunday filial topilmadi.",
            'incorrect_type': "Filial ID butun son bo'lishi kerak.",
        }
    )
    customer        = serializers.PrimaryKeyRelatedField(
        queryset=Customer.objects.filter(status=CustomerStatus.ACTIVE),
        required=False,
        allow_null=True,
        default=None,
        error_messages={
            'does_not_exist': "Bunday mijoz topilmadi yoki u faol emas.",
            'incorrect_type': "Mijoz ID butun son bo'lishi kerak.",
        }
    )
    payment_type    = serializers.ChoiceField(
        choices=PaymentType.choices,
        error_messages={
            'required':       "To'lov turi tanlanishi shart.",
            'invalid_choice': "'{input}' noto'g'ri to'lov turi.",
        }
    )
    discount_amount = serializers.DecimalField(
        max_digits=15,
        decimal_places=2,
        min_value=Decimal('0'),
        required=False,
        default=Decimal('0'),
        error_messages={
            'invalid':   "To'g'ri chegirma miqdori kiritilishi shart.",
            'min_value': "Chegirma manfiy bo'lishi mumkin emas.",
        }
    )
    paid_amount     = serializers.DecimalField(
        max_digits=15,
        decimal_places=2,
        min_value=Decimal('0'),
        error_messages={
            'required':  "To'lov miqdori kiritilishi shart.",
            'invalid':   "To'g'ri to'lov miqdori kiritilishi shart.",
            'min_value': "To'lov miqdori manfiy bo'lishi mumkin emas.",
        }
    )
    note            = serializers.CharField(
        required=False,
        allow_blank=True,
        default='',
        error_messages={
            'max_length': "Izoh 500 belgidan oshmasligi kerak.",
        }
    )
    items           = SaleItemInputSerializer(
        many=True,
        error_messages={
            'required':   "Kamida bitta mahsulot bo'lishi shart.",
            'not_a_list': "Mahsulotlar ro'yxat ko'rinishida bo'lishi kerak.",
            'empty':      "Kamida bitta mahsulot bo'lishi shart.",
        }
    )

    def validate_items(self, value: list) -> list:
        if not value:
            raise serializers.ValidationError(
                "Kamida bitta mahsulot bo'lishi shart."
            )
        return value
