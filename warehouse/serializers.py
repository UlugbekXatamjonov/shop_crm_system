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
  3. Warehouse serializers
  4. Stock serializers
  5. StockMovement serializers
"""

from rest_framework import serializers

from .models import (
    Category,
    MovementType,
    Product,
    ProductStatus,
    Stock,
    StockMovement,
    Warehouse,
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
        fields = ('name', 'description', 'status')

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

    def validate_name(self, value: str) -> str:
        """Bir do'kon ichida mahsulot nomi takrorlanmasligi kerak."""
        store = self.context.get('store')
        if store and Product.objects.filter(store=store, name=value).exists():
            raise serializers.ValidationError(
                "Bu nomli mahsulot ushbu do'konda allaqachon mavjud."
            )
        return value

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

    def validate_name(self, value: str) -> str:
        """Bir do'kon ichida mahsulot nomi takrorlanmasligi kerak."""
        qs = Product.objects.filter(
            store=self.instance.store, name=value
        ).exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError(
                "Bu nomli mahsulot ushbu do'konda allaqachon mavjud."
            )
        return value

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
# OMBOR SERIALIZERLARI
# ============================================================

class WarehouseListSerializer(serializers.ModelSerializer):
    """
    Omborlar ro'yxati uchun qisqa serializer.
    GET /api/v1/warehouse/warehouses/ da ishlatiladi.
    """
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    stock_count    = serializers.SerializerMethodField()

    class Meta:
        model  = Warehouse
        fields = ('id', 'name', 'status', 'status_display', 'stock_count')

    def get_stock_count(self, obj: Warehouse) -> int:
        return obj.stocks.filter(quantity__gt=0).count()


class WarehouseDetailSerializer(serializers.ModelSerializer):
    """
    Omborning to'liq ma'lumoti.
    GET /api/v1/warehouse/warehouses/{id}/ da ishlatiladi.
    """
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    store_name     = serializers.CharField(source='store.name', read_only=True)
    stock_count    = serializers.SerializerMethodField()

    class Meta:
        model  = Warehouse
        fields = (
            'id', 'name', 'address',
            'store_name', 'status', 'status_display',
            'stock_count', 'created_on',
        )

    def get_stock_count(self, obj: Warehouse) -> int:
        return obj.stocks.filter(quantity__gt=0).count()


class WarehouseCreateSerializer(serializers.ModelSerializer):
    """
    Yangi ombor yaratish.
    POST /api/v1/warehouse/warehouses/ da ishlatiladi.
    store maydoni view da avtomatik beriladi (perform_create).
    """

    class Meta:
        model  = Warehouse
        fields = ('name', 'address')

    def validate_name(self, value: str) -> str:
        """Bir do'kon ichida ombor nomi takrorlanmasligi kerak."""
        store = self.context.get('store')
        if store and Warehouse.objects.filter(store=store, name=value).exists():
            raise serializers.ValidationError(
                "Bu nomli ombor ushbu do'konda allaqachon mavjud."
            )
        return value


class WarehouseUpdateSerializer(serializers.ModelSerializer):
    """
    Ombor ma'lumotlarini yangilash.
    PATCH /api/v1/warehouse/warehouses/{id}/ da ishlatiladi.
    """

    class Meta:
        model  = Warehouse
        fields = ('name', 'address', 'status')

    def validate_name(self, value: str) -> str:
        qs = Warehouse.objects.filter(
            store=self.instance.store, name=value
        ).exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError(
                "Bu nomli ombor ushbu do'konda allaqachon mavjud."
            )
        return value


# ============================================================
# QOLDIQ SERIALIZERLARI
# ============================================================

class StockListSerializer(serializers.ModelSerializer):
    """
    Qoldiqlar ro'yxati uchun qisqa serializer.
    GET /api/v1/warehouse/stocks/ da ishlatiladi.
    Filial yoki ombor bo'yicha qoldiqni ko'rsatadi.
    """
    product_name   = serializers.CharField(source='product.name', read_only=True)
    product_unit   = serializers.CharField(source='product.get_unit_display', read_only=True)
    branch_name    = serializers.CharField(source='branch.name', read_only=True, default=None)
    warehouse_name = serializers.CharField(source='warehouse.name', read_only=True, default=None)
    location_type  = serializers.SerializerMethodField()

    class Meta:
        model  = Stock
        fields = (
            'id', 'product_name', 'product_unit',
            'branch_name', 'warehouse_name', 'location_type',
            'quantity', 'updated_on',
        )

    def get_location_type(self, obj: Stock) -> str:
        return 'branch' if obj.branch_id else 'warehouse'


class StockDetailSerializer(serializers.ModelSerializer):
    """
    Qoldiqning to'liq ma'lumoti.
    GET /api/v1/warehouse/stocks/{id}/ da ishlatiladi.
    """
    product_id     = serializers.IntegerField(source='product.id', read_only=True)
    product_name   = serializers.CharField(source='product.name', read_only=True)
    product_unit   = serializers.CharField(source='product.get_unit_display', read_only=True)
    branch_id      = serializers.IntegerField(source='branch.id', read_only=True, default=None)
    branch_name    = serializers.CharField(source='branch.name', read_only=True, default=None)
    warehouse_id   = serializers.IntegerField(source='warehouse.id', read_only=True, default=None)
    warehouse_name = serializers.CharField(source='warehouse.name', read_only=True, default=None)
    location_type  = serializers.SerializerMethodField()

    class Meta:
        model  = Stock
        fields = (
            'id',
            'product_id', 'product_name', 'product_unit',
            'branch_id', 'branch_name',
            'warehouse_id', 'warehouse_name',
            'location_type', 'quantity', 'updated_on',
        )

    def get_location_type(self, obj: Stock) -> str:
        return 'branch' if obj.branch_id else 'warehouse'


class StockCreateSerializer(serializers.ModelSerializer):
    """
    Qoldiqni qo'lda qo'shish (boshlang'ich inventarizatsiya).
    POST /api/v1/warehouse/stocks/ da ishlatiladi.
    branch yoki warehouse dan biri berilishi kerak.
    """

    class Meta:
        model  = Stock
        fields = ('product', 'branch', 'warehouse', 'quantity')

    def validate(self, data: dict) -> dict:
        branch    = data.get('branch')
        warehouse = data.get('warehouse')
        store     = self.context.get('store')

        # branch yoki warehouse dan biri bo'lishi kerak
        if not branch and not warehouse:
            raise serializers.ValidationError(
                "Filial yoki ombor ko'rsatilishi kerak."
            )
        if branch and warehouse:
            raise serializers.ValidationError(
                "Faqat filial yoki ombor ko'rsatilishi kerak, ikkalasi emas."
            )

        if store:
            if data['product'].store != store:
                raise serializers.ValidationError({
                    'product': "Bu mahsulot sizning do'koningizga tegishli emas."
                })
            if branch and branch.store != store:
                raise serializers.ValidationError({
                    'branch': "Bu filial sizning do'koningizga tegishli emas."
                })
            if warehouse and warehouse.store != store:
                raise serializers.ValidationError({
                    'warehouse': "Bu ombor sizning do'koningizga tegishli emas."
                })

        # Takroriy yozuv tekshiruvi
        if branch and Stock.objects.filter(product=data['product'], branch=branch).exists():
            raise serializers.ValidationError(
                "Bu mahsulot uchun ushbu filialda qoldiq yozuvi allaqachon mavjud."
            )
        if warehouse and Stock.objects.filter(product=data['product'], warehouse=warehouse).exists():
            raise serializers.ValidationError(
                "Bu mahsulot uchun ushbu omborда qoldiq yozuvi allaqachon mavjud."
            )
        return data


class StockUpdateSerializer(serializers.ModelSerializer):
    """
    Qoldiqni yangilash (faqat miqdor).
    PATCH /api/v1/warehouse/stocks/{id}/ da ishlatiladi.
    """

    class Meta:
        model  = Stock
        fields = ('quantity',)


# ============================================================
# HARAKAT (KIRIM/CHIQIM/KO'CHIRISH) SERIALIZERLARI
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
    movement_type_display = serializers.CharField(
        source='get_movement_type_display', read_only=True
    )
    from_name             = serializers.SerializerMethodField()
    to_name               = serializers.SerializerMethodField()
    worker_name           = serializers.SerializerMethodField()

    class Meta:
        model  = StockMovement
        fields = (
            'id', 'product_name', 'product_unit',
            'movement_type', 'movement_type_display',
            'from_name', 'to_name',
            'quantity', 'worker_name', 'created_on',
        )

    def get_from_name(self, obj: StockMovement) -> str | None:
        loc = obj.from_branch or obj.from_warehouse
        return loc.name if loc else None

    def get_to_name(self, obj: StockMovement) -> str | None:
        loc = obj.to_branch or obj.to_warehouse
        return loc.name if loc else None

    def get_worker_name(self, obj: StockMovement) -> str | None:
        return str(obj.worker.user) if obj.worker else None


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
    movement_type_display = serializers.CharField(
        source='get_movement_type_display', read_only=True
    )
    from_branch_id        = serializers.IntegerField(
        source='from_branch.id', read_only=True, default=None
    )
    from_branch_name      = serializers.CharField(
        source='from_branch.name', read_only=True, default=None
    )
    from_warehouse_id     = serializers.IntegerField(
        source='from_warehouse.id', read_only=True, default=None
    )
    from_warehouse_name   = serializers.CharField(
        source='from_warehouse.name', read_only=True, default=None
    )
    to_branch_id          = serializers.IntegerField(
        source='to_branch.id', read_only=True, default=None
    )
    to_branch_name        = serializers.CharField(
        source='to_branch.name', read_only=True, default=None
    )
    to_warehouse_id       = serializers.IntegerField(
        source='to_warehouse.id', read_only=True, default=None
    )
    to_warehouse_name     = serializers.CharField(
        source='to_warehouse.name', read_only=True, default=None
    )
    worker_name           = serializers.SerializerMethodField()

    class Meta:
        model  = StockMovement
        fields = (
            'id',
            'product_id', 'product_name', 'product_unit',
            'movement_type', 'movement_type_display',
            'from_branch_id', 'from_branch_name',
            'from_warehouse_id', 'from_warehouse_name',
            'to_branch_id', 'to_branch_name',
            'to_warehouse_id', 'to_warehouse_name',
            'quantity', 'note',
            'worker_name', 'created_on',
        )

    def get_worker_name(self, obj: StockMovement) -> str | None:
        return str(obj.worker.user) if obj.worker else None


class MovementCreateSerializer(serializers.ModelSerializer):
    """
    Yangi harakat yaratish (kirim, chiqim, ko'chirish).
    POST /api/v1/warehouse/movements/ da ishlatiladi.

    Qoidalar:
      IN       — to_branch yoki to_warehouse berilishi kerak
      OUT      — from_branch yoki from_warehouse berilishi kerak
      TRANSFER — from_* va to_* ikkalasi ham berilishi kerak

    Yaratilganda:
      - Stock qoldig'i avtomatik yangilanadi (ViewSet.perform_create)
      - OUT/TRANSFER uchun yetarli qoldiq tekshiriladi
    """

    class Meta:
        model  = StockMovement
        fields = (
            'product',
            'movement_type',
            'quantity',
            'from_branch',
            'from_warehouse',
            'to_branch',
            'to_warehouse',
            'note',
        )

    def validate_quantity(self, value):
        if value <= 0:
            raise serializers.ValidationError("Miqdor 0 dan katta bo'lishi kerak.")
        return value

    def validate(self, data: dict) -> dict:
        store         = self.context.get('store')
        movement_type = data.get('movement_type')
        from_branch   = data.get('from_branch')
        from_wh       = data.get('from_warehouse')
        to_branch     = data.get('to_branch')
        to_wh         = data.get('to_warehouse')
        product       = data.get('product')

        # Multi-tenant: barcha FK lar bir do'konga tegishli bo'lishi kerak
        if store:
            if product and product.store != store:
                raise serializers.ValidationError({
                    'product': "Bu mahsulot sizning do'koningizga tegishli emas."
                })
            for loc, field in [(from_branch, 'from_branch'), (to_branch, 'to_branch')]:
                if loc and loc.store != store:
                    raise serializers.ValidationError({
                        field: "Bu filial sizning do'koningizga tegishli emas."
                    })
            for loc, field in [(from_wh, 'from_warehouse'), (to_wh, 'to_warehouse')]:
                if loc and loc.store != store:
                    raise serializers.ValidationError({
                        field: "Bu ombor sizning do'koningizga tegishli emas."
                    })

        # Harakat turiga qarab from/to tekshiruvi
        if movement_type == MovementType.IN:
            if not to_branch and not to_wh:
                raise serializers.ValidationError(
                    "Kirim uchun qayerga (to_branch yoki to_warehouse) ko'rsatilishi kerak."
                )
            if from_branch or from_wh:
                raise serializers.ValidationError(
                    "Kirimda 'from' joyi ko'rsatilmaydi."
                )

        elif movement_type == MovementType.OUT:
            if not from_branch and not from_wh:
                raise serializers.ValidationError(
                    "Chiqim uchun qayerdan (from_branch yoki from_warehouse) ko'rsatilishi kerak."
                )
            if to_branch or to_wh:
                raise serializers.ValidationError(
                    "Chiqimda 'to' joyi ko'rsatilmaydi."
                )

        elif movement_type == MovementType.TRANSFER:
            if not (from_branch or from_wh):
                raise serializers.ValidationError(
                    "Ko'chirishda qayerdan (from_branch yoki from_warehouse) ko'rsatilishi kerak."
                )
            if not (to_branch or to_wh):
                raise serializers.ValidationError(
                    "Ko'chirishda qayerga (to_branch yoki to_warehouse) ko'rsatilishi kerak."
                )
            # Bir joydan bir joyga bo'lmasligi kerak
            if from_branch and from_branch == to_branch:
                raise serializers.ValidationError(
                    "Ko'chirish bir filialdan o'sha filialga bo'lmaydi."
                )
            if from_wh and from_wh == to_wh:
                raise serializers.ValidationError(
                    "Ko'chirish bir ombordan o'sha omborga bo'lmaydi."
                )

        # Chiqim va ko'chirish uchun qoldiq tekshiruvi
        if movement_type in (MovementType.OUT, MovementType.TRANSFER):
            from_location_filter = {}
            if from_branch:
                from_location_filter['branch'] = from_branch
            elif from_wh:
                from_location_filter['warehouse'] = from_wh

            try:
                stock = Stock.objects.get(product=product, **from_location_filter)
                if stock.quantity < data['quantity']:
                    from_name = getattr(from_branch or from_wh, 'name', '?')
                    raise serializers.ValidationError({
                        'quantity': (
                            f"'{from_name}' da yetarli mahsulot yo'q. "
                            f"Mavjud: {stock.quantity} "
                            f"{product.get_unit_display()}"
                        )
                    })
            except Stock.DoesNotExist:
                from_name = getattr(from_branch or from_wh, 'name', '?')
                raise serializers.ValidationError({
                    'quantity': f"Bu mahsulot '{from_name}' da mavjud emas."
                })

        return data
