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
            'discount': {'required': False, 'default': Decimal('0')},
        }

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


class CustomerDetailSerializer(serializers.ModelSerializer):
    """Mijoz to'liq ma'lumoti. GET /api/v1/customers/{id}/"""
    group_name     = serializers.CharField(
        source='group.name', read_only=True, allow_null=True, default=None,
    )
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model  = Customer
        fields = (
            'id', 'name', 'phone', 'address', 'debt_balance',
            'group', 'group_name',
            'status', 'status_display',
            'created_on',
        )


class CustomerCreateSerializer(serializers.ModelSerializer):
    """
    Mijoz yaratish. POST /api/v1/customers/
    store — ViewSet da avtomatik (worker.store).
    """

    class Meta:
        model  = Customer
        fields = ('name', 'phone', 'address', 'group')
        extra_kwargs = {
            'phone':   {'required': False, 'allow_blank': True},
            'address': {'required': False, 'allow_blank': True},
            'group':   {'required': False, 'allow_null': True},
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
            'name':    {'required': False},
            'phone':   {'required': False, 'allow_blank': True},
            'address': {'required': False, 'allow_blank': True},
            'group':   {'required': False, 'allow_null': True},
            'status':  {'required': False},
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
    )
    quantity   = serializers.DecimalField(
        max_digits=10,
        decimal_places=3,
        min_value=Decimal('0.001'),
    )
    unit_price = serializers.DecimalField(
        max_digits=15,
        decimal_places=2,
        min_value=Decimal('0'),
        required=False,
        allow_null=True,
        default=None,
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
        except Exception:
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
        except Exception:
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
    )
    customer        = serializers.PrimaryKeyRelatedField(
        queryset=Customer.objects.filter(status=CustomerStatus.ACTIVE),
        required=False,
        allow_null=True,
        default=None,
    )
    payment_type    = serializers.ChoiceField(choices=PaymentType.choices)
    discount_amount = serializers.DecimalField(
        max_digits=15,
        decimal_places=2,
        min_value=Decimal('0'),
        required=False,
        default=Decimal('0'),
    )
    paid_amount     = serializers.DecimalField(
        max_digits=15,
        decimal_places=2,
        min_value=Decimal('0'),
    )
    note            = serializers.CharField(
        required=False,
        allow_blank=True,
        default='',
    )
    items           = SaleItemInputSerializer(many=True)

    def validate_items(self, value: list) -> list:
        if not value:
            raise serializers.ValidationError(
                "Kamida bitta mahsulot bo'lishi shart."
            )
        return value
