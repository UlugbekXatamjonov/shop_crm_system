"""
============================================================
WAREHOUSE APP — Serializerlar
============================================================
Har bir ViewSet action uchun alohida serializer:
  list     → ListSerializer    (qisqa, jadval uchun)
  retrieve → DetailSerializer  (to'liq ma'lumot)
  create   → CreateSerializer  (yangi obyekt yaratish)
  update   → UpdateSerializer  (ma'lumotlarni yangilash)

Tartib:
  1. Category serializers
  2. Product serializers
  3. Stock serializers
  4. StockMovement serializers
"""

from rest_framework import serializers

from .models import (
    Category,
    MovementType,
    Product,
    ProductStatus,
    Stock,
    StockMovement,
)


# ============================================================
# KATEGORIYA SERIALIZERLARI
# ============================================================

class CategoryListSerializer(serializers.ModelSerializer):
    """
    Kategoriyalar ro'yxati uchun qisqa serializer.
    GET /api/v1/warehouse/categories/ da ishlatiladi.
    """
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    product_count  = serializers.SerializerMethodField()

    class Meta:
        model  = Category
        fields = ('id', 'name', 'status', 'status_display', 'product_count')

    def get_product_count(self, obj: Category) -> int:
        return obj.products.filter(status=ProductStatus.ACTIVE).count()


class CategoryDetailSerializer(serializers.ModelSerializer):
    """
    Kategoriyaning to'liq ma'lumoti.
    GET /api/v1/warehouse/categories/{id}/ da ishlatiladi.
    """
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    store_name     = serializers.CharField(source='store.name', read_only=True)
    product_count  = serializers.SerializerMethodField()

    class Meta:
        model  = Category
        fields = (
            'id', 'name', 'description',
            'store_name', 'status', 'status_display',
            'product_count', 'created_on',
        )

    def get_product_count(self, obj: Category) -> int:
        return obj.products.filter(status=ProductStatus.ACTIVE).count()


class CategoryCreateSerializer(serializers.ModelSerializer):
    """
    Yangi kategoriya yaratish.
    POST /api/v1/warehouse/categories/ da ishlatiladi.
    store maydoni view da avtomatik beriladi (perform_create).
    """

    class Meta:
        model  = Category
        fields = ('name', 'description')

    def validate_name(self, value: str) -> str:
        """Bir do'kon ichida kategoriya nomi takrorlanmasligi kerak."""
        store = self.context.get('store')
        if store and Category.objects.filter(store=store, name=value).exists():
            raise serializers.ValidationError(
                "Bu nomli kategoriya ushbu do'konda allaqachon mavjud."
            )
        return value


class CategoryUpdateSerializer(serializers.ModelSerializer):
    """
    Kategoriya ma'lumotlarini yangilash.
    PATCH /api/v1/warehouse/categories/{id}/ da ishlatiladi.
    """

    class Meta:
        model  = Category
        fields = ('name', 'description')

    def validate_name(self, value: str) -> str:
        qs = Category.objects.filter(
            store=self.instance.store, name=value
        ).exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError(
                "Bu nomli kategoriya ushbu do'konda allaqachon mavjud."
            )
        return value


# ============================================================
# MAHSULOT SERIALIZERLARI
# ============================================================

class ProductListSerializer(serializers.ModelSerializer):
    """
    Mahsulotlar ro'yxati uchun qisqa serializer.
    GET /api/v1/warehouse/products/ da ishlatiladi.
    """
    category_name  = serializers.CharField(
        source='category.name', read_only=True, default=None
    )
    unit_display   = serializers.CharField(source='get_unit_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model  = Product
        fields = (
            'id', 'name', 'category_name',
            'unit', 'unit_display',
            'sale_price', 'barcode',
            'status', 'status_display',
        )


class ProductDetailSerializer(serializers.ModelSerializer):
    """
    Mahsulotning to'liq ma'lumoti.
    GET /api/v1/warehouse/products/{id}/ da ishlatiladi.
    """
    category_id    = serializers.IntegerField(
        source='category.id', read_only=True, default=None
    )
    category_name  = serializers.CharField(
        source='category.name', read_only=True, default=None
    )
    unit_display   = serializers.CharField(source='get_unit_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    store_name     = serializers.CharField(source='store.name', read_only=True)

    class Meta:
        model  = Product
        fields = (
            'id', 'name',
            'category_id', 'category_name',
            'unit', 'unit_display',
            'purchase_price', 'sale_price',
            'barcode', 'store_name',
            'status', 'status_display',
            'created_on',
        )


class ProductCreateSerializer(serializers.ModelSerializer):
    """
    Yangi mahsulot yaratish.
    POST /api/v1/warehouse/products/ da ishlatiladi.
    store maydoni view da avtomatik beriladi (perform_create).
    """

    class Meta:
        model  = Product
        fields = ('name', 'category', 'unit', 'purchase_price', 'sale_price', 'barcode')

    def validate_category(self, value: Category) -> Category:
        """Kategoriya xuddi shu do'konga tegishli bo'lishi kerak."""
        store = self.context.get('store')
        if store and value.store != store:
            raise serializers.ValidationError(
                "Ushbu kategoriya sizning do'koningizga tegishli emas."
            )
        return value

    def validate_barcode(self, value: str):
        """Shtrix-kod do'kon ichida unikal bo'lishi kerak."""
        if not value:
            return None
        store = self.context.get('store')
        if store and Product.objects.filter(store=store, barcode=value).exists():
            raise serializers.ValidationError(
                "Bu shtrix-kodli mahsulot ushbu do'konda allaqachon mavjud."
            )
        return value


class ProductUpdateSerializer(serializers.ModelSerializer):
    """
    Mahsulot ma'lumotlarini yangilash.
    PATCH /api/v1/warehouse/products/{id}/ da ishlatiladi.
    """

    class Meta:
        model  = Product
        fields = (
            'name', 'category', 'unit',
            'purchase_price', 'sale_price',
            'barcode', 'status',
        )

    def validate_category(self, value: Category) -> Category:
        if value and value.store != self.instance.store:
            raise serializers.ValidationError(
                "Ushbu kategoriya sizning do'koningizga tegishli emas."
            )
        return value

    def validate_barcode(self, value: str):
        if not value:
            return None
        qs = Product.objects.filter(
            store=self.instance.store, barcode=value
        ).exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError(
                "Bu shtrix-kodli mahsulot ushbu do'konda allaqachon mavjud."
            )
        return value


# ============================================================
# OMBOR QOLDIG'I SERIALIZERLARI
# ============================================================

class StockListSerializer(serializers.ModelSerializer):
    """
    Ombor qoldiqlari ro'yxati uchun qisqa serializer.
    GET /api/v1/warehouse/stocks/ da ishlatiladi.
    """
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_unit = serializers.CharField(source='product.get_unit_display', read_only=True)
    branch_name  = serializers.CharField(source='branch.name', read_only=True)

    class Meta:
        model  = Stock
        fields = (
            'id', 'product_name', 'product_unit',
            'branch_name', 'quantity', 'updated_on',
        )


class StockDetailSerializer(serializers.ModelSerializer):
    """
    Ombor qoldig'ining to'liq ma'lumoti.
    GET /api/v1/warehouse/stocks/{id}/ da ishlatiladi.
    """
    product_id   = serializers.IntegerField(source='product.id', read_only=True)
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_unit = serializers.CharField(source='product.get_unit_display', read_only=True)
    branch_id    = serializers.IntegerField(source='branch.id', read_only=True)
    branch_name  = serializers.CharField(source='branch.name', read_only=True)

    class Meta:
        model  = Stock
        fields = (
            'id',
            'product_id', 'product_name', 'product_unit',
            'branch_id', 'branch_name',
            'quantity', 'updated_on',
        )


class StockCreateSerializer(serializers.ModelSerializer):
    """
    Ombor qoldig'ini qo'lda qo'shish.
    POST /api/v1/warehouse/stocks/ da ishlatiladi.
    Odatda StockMovement orqali avtomatik yaratiladi.
    """

    class Meta:
        model  = Stock
        fields = ('product', 'branch', 'quantity')

    def validate(self, data: dict) -> dict:
        store = self.context.get('store')
        if store:
            if data['product'].store != store:
                raise serializers.ValidationError({
                    'product': "Bu mahsulot sizning do'koningizga tegishli emas."
                })
            if data['branch'].store != store:
                raise serializers.ValidationError({
                    'branch': "Bu filial sizning do'koningizga tegishli emas."
                })
        if Stock.objects.filter(
            product=data['product'], branch=data['branch']
        ).exists():
            raise serializers.ValidationError(
                "Bu mahsulot uchun ushbu filialda qoldiq yozuvi allaqachon mavjud."
            )
        return data


class StockUpdateSerializer(serializers.ModelSerializer):
    """
    Ombor qoldig'ini yangilash (faqat miqdor).
    PATCH /api/v1/warehouse/stocks/{id}/ da ishlatiladi.
    """

    class Meta:
        model  = Stock
        fields = ('quantity',)


# ============================================================
# HARAKAT (KIRIM/CHIQIM) SERIALIZERLARI
# ============================================================

class MovementListSerializer(serializers.ModelSerializer):
    """
    Harakatlar ro'yxati uchun qisqa serializer.
    GET /api/v1/warehouse/movements/ da ishlatiladi.
    """
    product_name          = serializers.CharField(source='product.name', read_only=True)
    product_unit          = serializers.CharField(
        source='product.get_unit_display', read_only=True
    )
    branch_name           = serializers.CharField(source='branch.name', read_only=True)
    movement_type_display = serializers.CharField(
        source='get_movement_type_display', read_only=True
    )
    worker_name           = serializers.SerializerMethodField()

    class Meta:
        model  = StockMovement
        fields = (
            'id', 'product_name', 'product_unit', 'branch_name',
            'movement_type', 'movement_type_display',
            'quantity', 'worker_name', 'created_on',
        )

    def get_worker_name(self, obj: StockMovement) -> str | None:
        if obj.worker:
            return str(obj.worker.user)
        return None


class MovementDetailSerializer(serializers.ModelSerializer):
    """
    Harakatning to'liq ma'lumoti.
    GET /api/v1/warehouse/movements/{id}/ da ishlatiladi.
    """
    product_id            = serializers.IntegerField(source='product.id', read_only=True)
    product_name          = serializers.CharField(source='product.name', read_only=True)
    product_unit          = serializers.CharField(
        source='product.get_unit_display', read_only=True
    )
    branch_id             = serializers.IntegerField(source='branch.id', read_only=True)
    branch_name           = serializers.CharField(source='branch.name', read_only=True)
    movement_type_display = serializers.CharField(
        source='get_movement_type_display', read_only=True
    )
    worker_name           = serializers.SerializerMethodField()

    class Meta:
        model  = StockMovement
        fields = (
            'id',
            'product_id', 'product_name', 'product_unit',
            'branch_id', 'branch_name',
            'movement_type', 'movement_type_display',
            'quantity', 'note',
            'worker_name', 'created_on',
        )

    def get_worker_name(self, obj: StockMovement) -> str | None:
        if obj.worker:
            return str(obj.worker.user)
        return None


class MovementCreateSerializer(serializers.ModelSerializer):
    """
    Yangi kirim/chiqim harakati yaratish.
    POST /api/v1/warehouse/movements/ da ishlatiladi.

    Yaratilganda:
      - Stock qoldig'i avtomatik yangilanadi (ViewSet.perform_create)
      - Chiqim uchun yetarli qoldiq tekshiriladi
    """

    class Meta:
        model  = StockMovement
        fields = ('product', 'branch', 'movement_type', 'quantity', 'note')

    def validate_quantity(self, value):
        if value <= 0:
            raise serializers.ValidationError("Miqdor 0 dan katta bo'lishi kerak.")
        return value

    def validate(self, data: dict) -> dict:
        store = self.context.get('store')
        if store:
            if data['product'].store != store:
                raise serializers.ValidationError({
                    'product': "Bu mahsulot sizning do'koningizga tegishli emas."
                })
            if data['branch'].store != store:
                raise serializers.ValidationError({
                    'branch': "Bu filial sizning do'koningizga tegishli emas."
                })

        # Chiqim uchun yetarli qoldiq borligini tekshirish
        if data.get('movement_type') == MovementType.OUT:
            try:
                stock = Stock.objects.get(
                    product=data['product'],
                    branch=data['branch'],
                )
                if stock.quantity < data['quantity']:
                    raise serializers.ValidationError({
                        'quantity': (
                            f"Omborda yetarli mahsulot yo'q. "
                            f"Mavjud: {stock.quantity} "
                            f"{data['product'].get_unit_display()}"
                        )
                    })
            except Stock.DoesNotExist:
                raise serializers.ValidationError({
                    'quantity': "Bu mahsulot ushbu filial omborida mavjud emas."
                })
        return data
