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
  2. SubCategory serializers
  3. Currency serializers
  4. ExchangeRate serializers
  5. Product serializers
  6. Warehouse serializers
  7. Stock serializers         (branch|warehouse)
  8. StockMovement serializers (branch|warehouse, unit_cost)
  9. Transfer serializers      (guruhlab ko'chirish)
  10. StockBatch serializers   (FIFO partiyalar)
  11. WastageRecord serializers (B7 — isrof)
  12. StockAudit serializers    (B8 — inventarizatsiya)
"""

from rest_framework import serializers

from store.models import Branch

from .models import (
    AuditStatus,
    Category,
    Currency,
    ExchangeRate,
    MovementType,
    Product,
    Stock,
    StockAudit,
    StockAuditItem,
    StockBatch,
    StockMovement,
    SubCategory,
    Transfer,
    TransferItem,
    TransferStatus,
    Warehouse,
    WastageReason,
    WastageRecord,
)


# ============================================================
# KATEGORIYA SERIALIZERLARI
# ============================================================

class CategoryListSerializer(serializers.ModelSerializer):
    status_display    = serializers.CharField(source='get_status_display', read_only=True)
    product_count     = serializers.SerializerMethodField()
    subcategory_count = serializers.SerializerMethodField()

    class Meta:
        model  = Category
        fields = ('id', 'name', 'status', 'status_display', 'product_count', 'subcategory_count')

    def get_product_count(self, obj):
        return obj.products.count()

    def get_subcategory_count(self, obj):
        return obj.subcategories.count()


class CategoryDetailSerializer(serializers.ModelSerializer):
    status_display    = serializers.CharField(source='get_status_display', read_only=True)
    store_name        = serializers.CharField(source='store.name', read_only=True)
    product_count     = serializers.SerializerMethodField()
    subcategory_count = serializers.SerializerMethodField()

    class Meta:
        model  = Category
        fields = (
            'id', 'name', 'description',
            'store_name', 'status', 'status_display',
            'product_count', 'subcategory_count', 'created_on',
        )

    def get_product_count(self, obj):
        return obj.products.count()

    def get_subcategory_count(self, obj):
        return obj.subcategories.count()


class CategoryCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Category
        fields = ('name', 'description')
        extra_kwargs = {
            'name': {
                'error_messages': {
                    'required'  : "Kategoriya nomi kiritilishi shart.",
                    'blank'     : "Kategoriya nomi bo'sh bo'lishi mumkin emas.",
                    'max_length': "Kategoriya nomi 200 belgidan oshmasligi kerak.",
                }
            },
        }

    def validate_name(self, value):
        store = self.context.get('store')
        if store and Category.objects.filter(store=store, name=value).exists():
            raise serializers.ValidationError(
                "Bunday nomli Kategoriya mavjud. Iltimos boshqa nom tanlang !"
            )
        return value


class CategoryUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Category
        fields = ('name', 'description', 'status')
        extra_kwargs = {
            'name': {
                'error_messages': {
                    'blank'     : "Kategoriya nomi bo'sh bo'lishi mumkin emas.",
                    'max_length': "Kategoriya nomi 200 belgidan oshmasligi kerak.",
                }
            },
            'status': {
                'error_messages': {
                    'invalid_choice': "'{input}' noto'g'ri holat. Mavjud: active, inactive.",
                }
            },
        }

    def validate_name(self, value):
        qs = Category.objects.filter(
            store=self.instance.store, name=value
        ).exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError(
                "Bunday nomli Kategoriya mavjud. Iltimos boshqa nom tanlang !"
            )
        return value


# ============================================================
# SUBKATEGORIYA SERIALIZERLARI
# ============================================================

class SubCategoryListSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    category_name  = serializers.CharField(source='category.name', read_only=True)
    product_count  = serializers.SerializerMethodField()

    class Meta:
        model  = SubCategory
        fields = (
            'id', 'name', 'category_id', 'category_name',
            'status', 'status_display', 'product_count',
        )

    def get_product_count(self, obj):
        return obj.products.count()


class SubCategoryDetailSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    category_id    = serializers.IntegerField(source='category.id', read_only=True)
    category_name  = serializers.CharField(source='category.name', read_only=True)
    store_name     = serializers.CharField(source='store.name', read_only=True)
    product_count  = serializers.SerializerMethodField()

    class Meta:
        model  = SubCategory
        fields = (
            'id', 'name', 'description',
            'category_id', 'category_name',
            'store_name', 'status', 'status_display',
            'product_count', 'created_on',
        )

    def get_product_count(self, obj):
        return obj.products.count()


class SubCategoryCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model  = SubCategory
        fields = ('name', 'description', 'category')
        extra_kwargs = {
            'name': {
                'error_messages': {
                    'required'  : "Subkategoriya nomi kiritilishi shart.",
                    'blank'     : "Subkategoriya nomi bo'sh bo'lishi mumkin emas.",
                    'max_length': "Subkategoriya nomi 200 belgidan oshmasligi kerak.",
                }
            },
            'category': {
                'error_messages': {
                    'required'      : "Kategoriya tanlanishi shart.",
                    'does_not_exist': "Bunday kategoriya topilmadi.",
                    'incorrect_type': "Kategoriya ID butun son bo'lishi kerak.",
                }
            },
        }

    def validate_category(self, value):
        store = self.context.get('store')
        if store and value.store != store:
            raise serializers.ValidationError(
                "Ushbu kategoriya sizning do'koningizga tegishli emas."
            )
        return value

    def validate(self, data):
        store = self.context.get('store')
        if store:
            if SubCategory.objects.filter(
                store=store,
                category=data.get('category'),
                name=data.get('name'),
            ).exists():
                raise serializers.ValidationError(
                    "Bunday nomli SubKategoriya mavjud. Iltimos boshqa nom tanlang !"
                )
        return data


class SubCategoryUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model  = SubCategory
        fields = ('name', 'description', 'category', 'status')
        extra_kwargs = {
            'name': {
                'error_messages': {
                    'blank'     : "Subkategoriya nomi bo'sh bo'lishi mumkin emas.",
                    'max_length': "Subkategoriya nomi 200 belgidan oshmasligi kerak.",
                }
            },
            'category': {
                'error_messages': {
                    'does_not_exist': "Bunday kategoriya topilmadi.",
                    'incorrect_type': "Kategoriya ID butun son bo'lishi kerak.",
                }
            },
            'status': {
                'error_messages': {
                    'invalid_choice': "'{input}' noto'g'ri holat. Mavjud: active, inactive.",
                }
            },
        }

    def validate_category(self, value):
        if value and value.store != self.instance.store:
            raise serializers.ValidationError(
                "Ushbu kategoriya sizning do'koningizga tegishli emas."
            )
        return value

    def validate(self, data):
        category = data.get('category', self.instance.category)
        name     = data.get('name', self.instance.name)
        qs = SubCategory.objects.filter(
            store=self.instance.store,
            category=category,
            name=name,
        ).exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError(
                "Bunday nomli SubKategoriya mavjud. Iltimos boshqa nom tanlang !"
            )
        return data


# ============================================================
# VALYUTA SERIALIZERLARI
# ============================================================

class CurrencyListSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Currency
        fields = ('id', 'code', 'name', 'symbol', 'is_base')


class CurrencyDetailSerializer(serializers.ModelSerializer):
    latest_rate = serializers.SerializerMethodField()

    class Meta:
        model  = Currency
        fields = ('id', 'code', 'name', 'symbol', 'is_base', 'latest_rate')

    def get_latest_rate(self, obj):
        if obj.is_base:
            return {'rate': '1.0000', 'date': None}
        latest = obj.rates.order_by('-date').first()
        if latest:
            return {'rate': str(latest.rate), 'date': str(latest.date)}
        return None


class CurrencyCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Currency
        fields = ('code', 'name', 'symbol', 'is_base')
        extra_kwargs = {
            'code'  : {'error_messages': {'required': "Valyuta kodi kiritilishi shart.", 'blank': "Valyuta kodi bo'sh bo'lishi mumkin emas.", 'max_length': "Valyuta kodi 3 belgidan oshmasligi kerak.", 'unique': "Bu valyuta kodi allaqachon mavjud."}},
            'name'  : {'error_messages': {'required': "Valyuta nomi kiritilishi shart.", 'blank': "Valyuta nomi bo'sh bo'lishi mumkin emas."}},
            'symbol': {'error_messages': {'required': "Valyuta belgisi kiritilishi shart.", 'blank': "Valyuta belgisi bo'sh bo'lishi mumkin emas."}},
        }

    def validate_code(self, value):
        return value.upper().strip()

    def validate_is_base(self, value):
        if value and Currency.objects.filter(is_base=True).exists():
            raise serializers.ValidationError(
                "Asosiy valyuta allaqachon mavjud. Faqat bitta asosiy valyuta bo'lishi mumkin."
            )
        return value


# ============================================================
# VALYUTA KURSI SERIALIZERLARI
# ============================================================

class ExchangeRateListSerializer(serializers.ModelSerializer):
    currency_code   = serializers.CharField(source='currency.code', read_only=True)
    currency_symbol = serializers.CharField(source='currency.symbol', read_only=True)

    class Meta:
        model  = ExchangeRate
        fields = ('id', 'currency_code', 'currency_symbol', 'rate', 'date')


class ExchangeRateDetailSerializer(serializers.ModelSerializer):
    currency_id     = serializers.IntegerField(source='currency.id', read_only=True)
    currency_code   = serializers.CharField(source='currency.code', read_only=True)
    currency_name   = serializers.CharField(source='currency.name', read_only=True)
    currency_symbol = serializers.CharField(source='currency.symbol', read_only=True)

    class Meta:
        model  = ExchangeRate
        fields = (
            'id',
            'currency_id', 'currency_code', 'currency_name', 'currency_symbol',
            'rate', 'date', 'created_on',
        )


class ExchangeRateCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model  = ExchangeRate
        fields = ('currency', 'rate', 'date')
        extra_kwargs = {
            'currency': {'error_messages': {'required': "Valyuta tanlanishi shart.", 'does_not_exist': "Bunday valyuta topilmadi.", 'incorrect_type': "Valyuta ID butun son bo'lishi kerak."}},
            'rate'    : {'error_messages': {'required': "Kurs kiritilishi shart.", 'invalid': "To'g'ri raqam kiritilishi shart.", 'max_digits': "Raqam juda katta."}},
            'date'    : {'error_messages': {'required': "Sana kiritilishi shart.", 'invalid': "Sana formati noto'g'ri. To'g'ri format: YYYY-MM-DD."}},
        }

    def validate(self, data):
        currency = data.get('currency')
        date     = data.get('date')
        if currency and date:
            if ExchangeRate.objects.filter(currency=currency, date=date).exists():
                raise serializers.ValidationError(
                    f"{currency.code} uchun {date} sanasida kurs allaqachon mavjud."
                )
        return data


# ============================================================
# MAHSULOT SERIALIZERLARI
# ============================================================

class ProductListSerializer(serializers.ModelSerializer):
    category_name    = serializers.CharField(source='category.name', read_only=True)
    subcategory_name = serializers.CharField(source='subcategory.name', read_only=True)
    unit_display     = serializers.CharField(source='get_unit_display', read_only=True)
    status_display   = serializers.CharField(source='get_status_display', read_only=True)
    currency_code    = serializers.CharField(source='price_currency.code', read_only=True)

    class Meta:
        model  = Product
        fields = (
            'id', 'name',
            'category_name', 'subcategory_name',
            'unit', 'unit_display',
            'sale_price', 'currency_code',
            'barcode', 'status', 'status_display',
        )


class ProductDetailSerializer(serializers.ModelSerializer):
    category_id      = serializers.IntegerField(source='category.id', read_only=True)
    category_name    = serializers.CharField(source='category.name', read_only=True)
    subcategory_id   = serializers.IntegerField(source='subcategory.id', read_only=True)
    subcategory_name = serializers.CharField(source='subcategory.name', read_only=True)
    unit_display     = serializers.CharField(source='get_unit_display', read_only=True)
    status_display   = serializers.CharField(source='get_status_display', read_only=True)
    currency_id      = serializers.IntegerField(source='price_currency.id', read_only=True)
    currency_code    = serializers.CharField(source='price_currency.code', read_only=True)
    currency_symbol  = serializers.CharField(source='price_currency.symbol', read_only=True)
    store_name       = serializers.CharField(source='store.name', read_only=True)
    stock_total      = serializers.SerializerMethodField()
    barcode_image_url = serializers.SerializerMethodField()

    class Meta:
        model  = Product
        fields = (
            'id', 'name',
            'category_id', 'category_name',
            'subcategory_id', 'subcategory_name',
            'unit', 'unit_display',
            'purchase_price', 'sale_price',
            'currency_id', 'currency_code', 'currency_symbol',
            'barcode', 'barcode_image_url', 'image',
            'store_name', 'status', 'status_display',
            'stock_total', 'created_on',
        )

    def get_stock_total(self, obj):
        from django.db.models import Sum
        result = obj.stocks.aggregate(total=Sum('quantity'))
        return result['total'] or 0

    def get_barcode_image_url(self, obj):
        if not obj.barcode:
            return None
        request = self.context.get('request')
        url = f'/api/v1/warehouse/products/{obj.id}/barcode/'
        if request:
            return request.build_absolute_uri(url)
        return url


class ProductCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Product
        fields = (
            'name', 'category', 'subcategory',
            'unit', 'purchase_price', 'sale_price',
            'price_currency', 'barcode', 'image',
        )
        extra_kwargs = {
            'name': {
                'error_messages': {
                    'required'  : "Mahsulot nomi kiritilishi shart.",
                    'blank'     : "Mahsulot nomi bo'sh bo'lishi mumkin emas.",
                    'max_length': "Mahsulot nomi 300 belgidan oshmasligi kerak.",
                }
            },
        }

    def validate_category(self, value):
        store = self.context.get('store')
        if store and value and value.store != store:
            raise serializers.ValidationError(
                "Ushbu kategoriya sizning do'koningizga tegishli emas."
            )
        return value

    def validate_subcategory(self, value):
        store = self.context.get('store')
        if store and value and value.store != store:
            raise serializers.ValidationError(
                "Ushbu subkategoriya sizning do'koningizga tegishli emas."
            )
        return value

    def validate_barcode(self, value):
        if not value:
            return value
        store = self.context.get('store')
        if store and Product.objects.filter(store=store, barcode=value).exists():
            raise serializers.ValidationError(
                "Bu shtrix-kod sizning do'koningizda allaqachon mavjud."
            )
        return value

    def validate(self, data):
        store    = self.context.get('store')
        name     = data.get('name')
        category = data.get('category')
        subcategory = data.get('subcategory')
        if store and name and Product.objects.filter(store=store, name=name).exists():
            raise serializers.ValidationError(
                "Bunday nomli Mahsulot mavjud. Iltimos boshqa nom tanlang !"
            )
        if category and subcategory and subcategory.category != category:
            raise serializers.ValidationError(
                "Subkategoriya tanlangan kategoriyaga tegishli emas."
            )
        return data


class ProductUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Product
        fields = (
            'name', 'category', 'subcategory',
            'unit', 'purchase_price', 'sale_price',
            'price_currency', 'barcode', 'image', 'status',
        )
        extra_kwargs = {
            'name': {
                'error_messages': {
                    'blank'     : "Mahsulot nomi bo'sh bo'lishi mumkin emas.",
                    'max_length': "Mahsulot nomi 300 belgidan oshmasligi kerak.",
                }
            },
        }

    def validate_category(self, value):
        if value and value.store != self.instance.store:
            raise serializers.ValidationError(
                "Ushbu kategoriya sizning do'koningizga tegishli emas."
            )
        return value

    def validate_subcategory(self, value):
        if value and value.store != self.instance.store:
            raise serializers.ValidationError(
                "Ushbu subkategoriya sizning do'koningizga tegishli emas."
            )
        return value

    def validate_barcode(self, value):
        if not value:
            return value
        qs = Product.objects.filter(
            store=self.instance.store, barcode=value
        ).exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError(
                "Bu shtrix-kod sizning do'koningizda allaqachon mavjud."
            )
        return value

    def validate(self, data):
        name = data.get('name')
        if name:
            qs = Product.objects.filter(
                store=self.instance.store, name=name
            ).exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError(
                    "Bunday nomli Mahsulot mavjud. Iltimos boshqa nom tanlang !"
                )
        category    = data.get('category', self.instance.category)
        subcategory = data.get('subcategory', self.instance.subcategory)
        if category and subcategory and subcategory.category != category:
            raise serializers.ValidationError(
                "Subkategoriya tanlangan kategoriyaga tegishli emas."
            )
        return data


# ============================================================
# OMBOR (WAREHOUSE) SERIALIZERLARI
# ============================================================

class WarehouseListSerializer(serializers.ModelSerializer):
    stock_count = serializers.SerializerMethodField()

    class Meta:
        model  = Warehouse
        fields = ('id', 'name', 'address', 'status', 'stock_count')

    def get_stock_count(self, obj):
        return obj.stocks.count()


class WarehouseDetailSerializer(serializers.ModelSerializer):
    store_name  = serializers.CharField(source='store.name', read_only=True)
    stock_count = serializers.SerializerMethodField()

    class Meta:
        model  = Warehouse
        fields = (
            'id', 'name', 'address',
            'store_name', 'status',
            'stock_count', 'created_on',
        )

    def get_stock_count(self, obj):
        return obj.stocks.count()


class WarehouseCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Warehouse
        fields = ('name', 'address', 'status')
        extra_kwargs = {
            'name': {
                'error_messages': {
                    'required'  : "Ombor nomi kiritilishi shart.",
                    'blank'     : "Ombor nomi bo'sh bo'lishi mumkin emas.",
                    'max_length': "Ombor nomi 200 belgidan oshmasligi kerak.",
                }
            },
        }

    def validate_name(self, value):
        store = self.context.get('store')
        if store:
            existing = Warehouse.objects.filter(store=store, name=value).first()
            if existing:
                raise serializers.ValidationError(
                    "Bunday nomli Ombor mavjud. Iltimos boshqa nom tanlang !"
                )
        return value


class WarehouseUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Warehouse
        fields = ('name', 'address', 'status')
        extra_kwargs = {
            'name': {
                'error_messages': {
                    'blank'     : "Ombor nomi bo'sh bo'lishi mumkin emas.",
                    'max_length': "Ombor nomi 200 belgidan oshmasligi kerak.",
                }
            },
        }

    def validate_name(self, value):
        qs = Warehouse.objects.filter(
            store=self.instance.store, name=value
        ).exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError(
                "Bunday nomli Ombor mavjud. Iltimos boshqa nom tanlang !"
            )
        return value


# ============================================================
# OMBOR QOLDIG'I SERIALIZERLARI
# ============================================================

class StockListSerializer(serializers.ModelSerializer):
    product_id    = serializers.IntegerField(source='product.id', read_only=True)
    product_name  = serializers.CharField(source='product.name', read_only=True)
    product_unit  = serializers.CharField(source='product.get_unit_display', read_only=True)
    location_type = serializers.SerializerMethodField()
    location_name = serializers.SerializerMethodField()

    class Meta:
        model  = Stock
        fields = (
            'id', 'product_id', 'product_name', 'product_unit',
            'location_type', 'location_name',
            'quantity', 'updated_on',
        )

    def get_location_type(self, obj):
        return 'branch' if obj.branch_id else 'warehouse'

    def get_location_name(self, obj):
        if obj.branch_id:
            return obj.branch.name
        return obj.warehouse.name if obj.warehouse_id else None


class StockDetailSerializer(serializers.ModelSerializer):
    product_id    = serializers.IntegerField(source='product.id', read_only=True)
    product_name  = serializers.CharField(source='product.name', read_only=True)
    product_unit  = serializers.CharField(source='product.get_unit_display', read_only=True)
    branch_id     = serializers.IntegerField(source='branch.id', read_only=True)
    branch_name   = serializers.CharField(source='branch.name', read_only=True)
    warehouse_id  = serializers.IntegerField(source='warehouse.id', read_only=True)
    warehouse_name = serializers.CharField(source='warehouse.name', read_only=True)
    location_type = serializers.SerializerMethodField()

    class Meta:
        model  = Stock
        fields = (
            'id',
            'product_id', 'product_name', 'product_unit',
            'location_type',
            'branch_id', 'branch_name',
            'warehouse_id', 'warehouse_name',
            'quantity', 'updated_on',
        )

    def get_location_type(self, obj):
        return 'branch' if obj.branch_id else 'warehouse'


class StockLocationSerializer(serializers.Serializer):
    """by-product endpointi uchun — bitta joylashuv."""
    stock_id      = serializers.IntegerField()
    location_type = serializers.CharField()
    location_id   = serializers.IntegerField()
    location_name = serializers.CharField()
    quantity      = serializers.DecimalField(max_digits=14, decimal_places=3)
    updated_on    = serializers.CharField()


class StockByProductSerializer(serializers.Serializer):
    """
    GET /api/v1/warehouse/stocks/by-product/
    Har bir mahsulot — bitta obyekt, joylashuvlar nested 'locations' da.
    """
    product_id     = serializers.IntegerField()
    product_name   = serializers.CharField()
    product_unit   = serializers.CharField()
    total_quantity = serializers.DecimalField(max_digits=14, decimal_places=3)
    locations      = StockLocationSerializer(many=True)


class StockCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Stock
        fields = ('product', 'branch', 'warehouse', 'quantity')
        extra_kwargs = {
            'product': {
                'error_messages': {
                    'required'      : "Mahsulot tanlanishi shart.",
                    'does_not_exist': "Bunday mahsulot topilmadi.",
                    'incorrect_type': "Mahsulot ID butun son bo'lishi kerak.",
                }
            },
            'quantity': {
                'error_messages': {
                    'required': "Miqdor kiritilishi shart.",
                    'invalid' : "To'g'ri raqam kiritilishi shart.",
                }
            },
        }

    def validate_product(self, value):
        store = self.context.get('store')
        if store and value.store != store:
            raise serializers.ValidationError(
                "Bu mahsulot sizning do'koningizga tegishli emas."
            )
        return value

    def validate_branch(self, value):
        store = self.context.get('store')
        if store and value and value.store != store:
            raise serializers.ValidationError(
                "Bu filial sizning do'koningizga tegishli emas."
            )
        return value

    def validate_warehouse(self, value):
        store = self.context.get('store')
        if store and value and value.store != store:
            raise serializers.ValidationError(
                "Bu ombor sizning do'koningizga tegishli emas."
            )
        return value

    def validate(self, data):
        branch    = data.get('branch')
        warehouse = data.get('warehouse')
        # branch XOR warehouse — aynan bittasi to'ldirilishi shart
        if branch and warehouse:
            raise serializers.ValidationError(
                "Filial va ombor bir vaqtda ko'rsatilishi mumkin emas. Faqat bittasini tanlang."
            )
        if not branch and not warehouse:
            raise serializers.ValidationError(
                "Filial yoki ombor ko'rsatilishi shart."
            )
        product  = data.get('product')
        quantity = data.get('quantity', 0)
        if quantity < 0:
            raise serializers.ValidationError(
                "Qoldiq manfiy bo'lishi mumkin emas."
            )
        # Takrorlanishni tekshirish
        if product and branch:
            if Stock.objects.filter(product=product, branch=branch).exists():
                raise serializers.ValidationError(
                    "Bu mahsulot uchun ushbu filialda qoldiq allaqachon mavjud."
                )
        if product and warehouse:
            if Stock.objects.filter(product=product, warehouse=warehouse).exists():
                raise serializers.ValidationError(
                    "Bu mahsulot uchun ushbu omborда qoldiq allaqachon mavjud."
                )
        return data


class StockUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Stock
        fields = ('quantity',)
        extra_kwargs = {
            'quantity': {
                'error_messages': {
                    'required': "Miqdor kiritilishi shart.",
                    'invalid' : "To'g'ri raqam kiritilishi shart.",
                }
            },
        }

    def validate_quantity(self, value):
        if value < 0:
            raise serializers.ValidationError(
                "Qoldiq manfiy bo'lishi mumkin emas."
            )
        return value


# ============================================================
# KIRIM/CHIQIM HARAKATI SERIALIZERLARI
# ============================================================

class MovementListSerializer(serializers.ModelSerializer):
    product_name        = serializers.CharField(source='product.name', read_only=True)
    product_unit        = serializers.CharField(source='product.get_unit_display', read_only=True)
    movement_type_display = serializers.CharField(source='get_movement_type_display', read_only=True)
    worker_name         = serializers.SerializerMethodField()
    location_type       = serializers.SerializerMethodField()
    location_name       = serializers.SerializerMethodField()

    class Meta:
        model  = StockMovement
        fields = (
            'id', 'product_name', 'product_unit',
            'location_type', 'location_name',
            'movement_type', 'movement_type_display',
            'quantity', 'unit_cost', 'worker_name', 'created_on',
        )

    def get_worker_name(self, obj):
        if obj.worker_id:
            return obj.worker.user.get_full_name() or obj.worker.user.username
        return None

    def get_location_type(self, obj):
        return 'branch' if obj.branch_id else 'warehouse'

    def get_location_name(self, obj):
        if obj.branch_id:
            return obj.branch.name
        return obj.warehouse.name if obj.warehouse_id else None


class MovementDetailSerializer(serializers.ModelSerializer):
    product_id            = serializers.IntegerField(source='product.id', read_only=True)
    product_name          = serializers.CharField(source='product.name', read_only=True)
    product_unit          = serializers.CharField(source='product.get_unit_display', read_only=True)
    movement_type_display = serializers.CharField(source='get_movement_type_display', read_only=True)
    branch_id             = serializers.IntegerField(source='branch.id', read_only=True)
    branch_name           = serializers.CharField(source='branch.name', read_only=True)
    warehouse_id          = serializers.IntegerField(source='warehouse.id', read_only=True)
    warehouse_name        = serializers.CharField(source='warehouse.name', read_only=True)
    worker_name           = serializers.SerializerMethodField()
    location_type         = serializers.SerializerMethodField()

    class Meta:
        model  = StockMovement
        fields = (
            'id',
            'product_id', 'product_name', 'product_unit',
            'location_type',
            'branch_id', 'branch_name',
            'warehouse_id', 'warehouse_name',
            'movement_type', 'movement_type_display',
            'quantity', 'unit_cost', 'note',
            'worker_name', 'created_on',
        )

    def get_worker_name(self, obj):
        if obj.worker_id:
            return obj.worker.user.get_full_name() or obj.worker.user.username
        return None

    def get_location_type(self, obj):
        return 'branch' if obj.branch_id else 'warehouse'


class MovementCreateSerializer(serializers.ModelSerializer):
    # unit_cost: IN harakatda xarid narxi. OUT da e'tiborsiz (FIFO dan hisoblanadi).
    unit_cost = serializers.DecimalField(
        max_digits=15,
        decimal_places=2,
        required=False,
        allow_null=True,
        help_text="Kirim narxi (IN uchun). Chiqimda avtomatik hisoblanadi.",
    )

    class Meta:
        model  = StockMovement
        fields = ('product', 'branch', 'warehouse', 'movement_type', 'quantity', 'unit_cost', 'note')
        extra_kwargs = {
            'product': {
                'error_messages': {
                    'required'      : "Mahsulot tanlanishi shart.",
                    'does_not_exist': "Bunday mahsulot topilmadi.",
                    'incorrect_type': "Mahsulot ID butun son bo'lishi kerak.",
                }
            },
            'movement_type': {
                'error_messages': {
                    'required': "Harakat turi (kirim/chiqim) kiritilishi shart.",
                    'invalid_choice': "Harakat turi noto'g'ri. Faqat 'in' yoki 'out' bo'lishi mumkin.",
                }
            },
            'quantity': {
                'error_messages': {
                    'required': "Miqdor kiritilishi shart.",
                    'invalid' : "To'g'ri raqam kiritilishi shart.",
                }
            },
        }

    def validate_product(self, value):
        store = self.context.get('store')
        if store and value.store != store:
            raise serializers.ValidationError(
                "Bu mahsulot sizning do'koningizga tegishli emas."
            )
        return value

    def validate_branch(self, value):
        store = self.context.get('store')
        if store and value and value.store != store:
            raise serializers.ValidationError(
                "Bu filial sizning do'koningizga tegishli emas."
            )
        return value

    def validate_warehouse(self, value):
        store = self.context.get('store')
        if store and value and value.store != store:
            raise serializers.ValidationError(
                "Bu ombor sizning do'koningizga tegishli emas."
            )
        return value

    def validate_quantity(self, value):
        if value <= 0:
            raise serializers.ValidationError(
                "Miqdor 0 dan katta bo'lishi shart."
            )
        return value

    def validate(self, data):
        branch        = data.get('branch')
        warehouse     = data.get('warehouse')
        movement_type = data.get('movement_type')
        product       = data.get('product')
        quantity      = data.get('quantity', 0)

        # branch XOR warehouse
        if branch and warehouse:
            raise serializers.ValidationError(
                "Filial va ombor bir vaqtda ko'rsatilishi mumkin emas. Faqat bittasini tanlang."
            )
        if not branch and not warehouse:
            raise serializers.ValidationError(
                "Filial yoki ombor ko'rsatilishi shart."
            )

        # Chiqim uchun qoldiq yetarliligini tekshirish
        if movement_type == MovementType.OUT and product:
            stock_qs = Stock.objects.filter(product=product)
            if branch:
                stock_qs = stock_qs.filter(branch=branch)
            else:
                stock_qs = stock_qs.filter(warehouse=warehouse)
            stock = stock_qs.first()
            current_qty = stock.quantity if stock else 0
            if current_qty < quantity:
                location_name = branch.name if branch else warehouse.name
                raise serializers.ValidationError(
                    f"Qoldiq yetarli emas. '{location_name}' da '{product.name}' "
                    f"qoldig'i: {current_qty}, so'ralgan: {quantity}."
                )
        return data


# ============================================================
# TRANSFER SERIALIZERLARI
# ============================================================

class TransferItemReadSerializer(serializers.ModelSerializer):
    """Transfer satri — o'qish uchun (list/detail ichida nested)."""
    product_id   = serializers.IntegerField(source='product.id', read_only=True)
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_unit = serializers.CharField(source='product.get_unit_display', read_only=True)

    class Meta:
        model  = TransferItem
        fields = ('id', 'product_id', 'product_name', 'product_unit', 'quantity', 'note')


class TransferItemWriteSerializer(serializers.Serializer):
    """
    Transfer satri — yozish uchun (create da items[] ichida).

    MUHIM: Bu serializer TransferCreateSerializer ichida nested (many=True)
    ishlatiladi. DRF da nested serializer __init__ paytida context hali
    bind bo'lmagan bo'ladi — shuning uchun queryset=all() + validate_product
    usuli ishlatiladi (context faqat validation paytida mavjud).
    """
    product  = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all(),
        error_messages={
            'does_not_exist': "Mahsulot topilmadi (ID: {pk_value}).",
            'incorrect_type': "Mahsulot ID butun son bo'lishi kerak.",
            'required'      : "Mahsulot ID kiritilishi shart.",
            'null'          : "Mahsulot bo'sh bo'lishi mumkin emas.",
        }
    )
    quantity = serializers.DecimalField(
        max_digits=14,
        decimal_places=3,
        error_messages={
            'required': "Miqdor kiritilishi shart.",
            'invalid' : "Miqdor raqam bo'lishi kerak.",
        }
    )
    note     = serializers.CharField(required=False, allow_blank=True, default='')

    def validate_product(self, value):
        """Do'kon tegishliligi tekshiruvi — context validation paytida mavjud."""
        store = self.context.get('store')
        if store and value.store_id != store.id:
            raise serializers.ValidationError(
                f"Mahsulot topilmadi (ID: {value.pk}). Faqat o'z do'konidagi mahsulotlarni tanlang."
            )
        return value

    def validate_quantity(self, value):
        if value <= 0:
            raise serializers.ValidationError(
                "Miqdor 0 dan katta bo'lishi shart."
            )
        return value


class TransferListSerializer(serializers.ModelSerializer):
    """Transfer ro'yxati — qisqa ko'rinish."""
    from_location_type = serializers.SerializerMethodField()
    from_location_name = serializers.SerializerMethodField()
    to_location_type   = serializers.SerializerMethodField()
    to_location_name   = serializers.SerializerMethodField()
    status_display     = serializers.CharField(source='get_status_display', read_only=True)
    item_count         = serializers.SerializerMethodField()
    worker_name        = serializers.SerializerMethodField()

    class Meta:
        model  = Transfer
        fields = (
            'id',
            'from_location_type', 'from_location_name',
            'to_location_type',   'to_location_name',
            'status', 'status_display',
            'item_count', 'worker_name', 'created_on',
        )

    def get_from_location_type(self, obj):
        return 'branch' if obj.from_branch_id else 'warehouse'

    def get_from_location_name(self, obj):
        if obj.from_branch_id:
            return obj.from_branch.name
        return obj.from_warehouse.name if obj.from_warehouse_id else None

    def get_to_location_type(self, obj):
        return 'branch' if obj.to_branch_id else 'warehouse'

    def get_to_location_name(self, obj):
        if obj.to_branch_id:
            return obj.to_branch.name
        return obj.to_warehouse.name if obj.to_warehouse_id else None

    def get_item_count(self, obj):
        return obj.items.count()

    def get_worker_name(self, obj):
        if obj.worker_id:
            return obj.worker.user.get_full_name() or obj.worker.user.username
        return None


class TransferDetailSerializer(serializers.ModelSerializer):
    """Transfer tafsilotlari — to'liq ma'lumot + nested items."""
    from_location_type = serializers.SerializerMethodField()
    from_location_name = serializers.SerializerMethodField()
    from_branch_id     = serializers.IntegerField(source='from_branch.id', read_only=True)
    from_warehouse_id  = serializers.IntegerField(source='from_warehouse.id', read_only=True)
    to_location_type   = serializers.SerializerMethodField()
    to_location_name   = serializers.SerializerMethodField()
    to_branch_id       = serializers.IntegerField(source='to_branch.id', read_only=True)
    to_warehouse_id    = serializers.IntegerField(source='to_warehouse.id', read_only=True)
    status_display     = serializers.CharField(source='get_status_display', read_only=True)
    worker_name        = serializers.SerializerMethodField()
    store_name         = serializers.CharField(source='store.name', read_only=True)
    items              = TransferItemReadSerializer(many=True, read_only=True)

    class Meta:
        model  = Transfer
        fields = (
            'id',
            'from_location_type', 'from_location_name',
            'from_branch_id',     'from_warehouse_id',
            'to_location_type',   'to_location_name',
            'to_branch_id',       'to_warehouse_id',
            'store_name',
            'status', 'status_display',
            'note', 'confirmed_at',
            'worker_name', 'created_on',
            'items',
        )

    def get_from_location_type(self, obj):
        return 'branch' if obj.from_branch_id else 'warehouse'

    def get_from_location_name(self, obj):
        if obj.from_branch_id:
            return obj.from_branch.name
        return obj.from_warehouse.name if obj.from_warehouse_id else None

    def get_to_location_type(self, obj):
        return 'branch' if obj.to_branch_id else 'warehouse'

    def get_to_location_name(self, obj):
        if obj.to_branch_id:
            return obj.to_branch.name
        return obj.to_warehouse.name if obj.to_warehouse_id else None

    def get_worker_name(self, obj):
        if obj.worker_id:
            return obj.worker.user.get_full_name() or obj.worker.user.username
        return None


class TransferCreateSerializer(serializers.Serializer):
    """
    Yangi transfer yaratish.

    items[] — bir nechta mahsulot bir vaqtda jo'natiladi.
    Tasdiqlash (confirm) alohida action orqali.

    Tekshiruvlar:
      - from_branch XOR from_warehouse (manbaa)
      - to_branch   XOR to_warehouse   (manzil)
      - from != to  (o'ziga o'zi jo'natib bo'lmaydi)
      - items bo'sh bo'lmasligi
      - har bir mahsulot do'konga tegishli
      - bir transfer ichida bir xil mahsulot takrorlanmasligi
    """
    from_branch    = serializers.PrimaryKeyRelatedField(
        queryset=Branch.objects.all(),
        required=False,
        allow_null=True,
        default=None,
        error_messages={
            'does_not_exist': "Filial topilmadi (ID: {pk_value}).",
            'incorrect_type': "Filial ID butun son bo'lishi kerak.",
        }
    )
    from_warehouse = serializers.PrimaryKeyRelatedField(
        queryset=Warehouse.objects.all(),
        required=False,
        allow_null=True,
        default=None,
        error_messages={
            'does_not_exist': "Ombor topilmadi (ID: {pk_value}).",
            'incorrect_type': "Ombor ID butun son bo'lishi kerak.",
        }
    )
    to_branch      = serializers.PrimaryKeyRelatedField(
        queryset=Branch.objects.all(),
        required=False,
        allow_null=True,
        default=None,
        error_messages={
            'does_not_exist': "Filial topilmadi (ID: {pk_value}).",
            'incorrect_type': "Filial ID butun son bo'lishi kerak.",
        }
    )
    to_warehouse   = serializers.PrimaryKeyRelatedField(
        queryset=Warehouse.objects.all(),
        required=False,
        allow_null=True,
        default=None,
        error_messages={
            'does_not_exist': "Ombor topilmadi (ID: {pk_value}).",
            'incorrect_type': "Ombor ID butun son bo'lishi kerak.",
        }
    )
    note  = serializers.CharField(required=False, allow_blank=True, default='')
    items = TransferItemWriteSerializer(many=True)

    def validate_from_branch(self, value):
        store = self.context.get('store')
        if value and store and value.store_id != store.id:
            raise serializers.ValidationError(
                f'"{value.name}" Filiali sizning do\'koningizga tegishli emas.'
            )
        return value

    def validate_from_warehouse(self, value):
        store = self.context.get('store')
        if value and store and value.store_id != store.id:
            raise serializers.ValidationError(
                f'"{value.name}" Ombori sizning do\'koningizga tegishli emas.'
            )
        return value

    def validate_to_branch(self, value):
        store = self.context.get('store')
        if value and store and value.store_id != store.id:
            raise serializers.ValidationError(
                f'"{value.name}" Filiali sizning do\'koningizga tegishli emas.'
            )
        return value

    def validate_to_warehouse(self, value):
        store = self.context.get('store')
        if value and store and value.store_id != store.id:
            raise serializers.ValidationError(
                f'"{value.name}" Ombori sizning do\'koningizga tegishli emas.'
            )
        return value

    def validate_items(self, value):
        if not value:
            raise serializers.ValidationError(
                "Kamida bitta mahsulot kiritilishi shart."
            )
        # Takroriy mahsulot tekshiruvi
        product_ids = [item['product'].id for item in value]
        if len(product_ids) != len(set(product_ids)):
            raise serializers.ValidationError(
                "Bir transfer ichida bir xil mahsulot ikki marta kiritilishi mumkin emas."
            )
        return value

    def validate(self, data):
        from_branch    = data.get('from_branch')
        from_warehouse = data.get('from_warehouse')
        to_branch      = data.get('to_branch')
        to_warehouse   = data.get('to_warehouse')

        # Manbaa: from_branch XOR from_warehouse
        if from_branch and from_warehouse:
            raise serializers.ValidationError(
                "Manbaa uchun filial va ombor bir vaqtda ko'rsatilishi mumkin emas."
            )
        if not from_branch and not from_warehouse:
            raise serializers.ValidationError(
                "Manbaa (from_branch yoki from_warehouse) ko'rsatilishi shart."
            )

        # Manzil: to_branch XOR to_warehouse
        if to_branch and to_warehouse:
            raise serializers.ValidationError(
                "Manzil uchun filial va ombor bir vaqtda ko'rsatilishi mumkin emas."
            )
        if not to_branch and not to_warehouse:
            raise serializers.ValidationError(
                "Manzil (to_branch yoki to_warehouse) ko'rsatilishi shart."
            )

        # O'ziga o'zi jo'natib bo'lmaydi
        if from_branch and to_branch and from_branch == to_branch:
            raise serializers.ValidationError(
                "Manbaa va manzil bir xil filial bo'lishi mumkin emas."
            )
        if from_warehouse and to_warehouse and from_warehouse == to_warehouse:
            raise serializers.ValidationError(
                "Manbaa va manzil bir xil ombor bo'lishi mumkin emas."
            )

        return data

    def create(self, validated_data):
        items_data = validated_data.pop('items')
        store      = self.context['store']
        worker     = self.context.get('worker')
        transfer   = Transfer.objects.create(store=store, worker=worker, **validated_data)
        for item in items_data:
            TransferItem.objects.create(transfer=transfer, **item)
        return transfer


# ============================================================
# STOCKBATCH SERIALIZERLARI (FIFO PARTIYALAR)
# ============================================================

class StockBatchSerializer(serializers.ModelSerializer):
    """
    FIFO partiya — o'qish uchun (read-only).

    GET /api/v1/warehouse/batches/           — ro'yxat (?product=<id>)
    GET /api/v1/warehouse/batches/{id}/      — tafsilotlar
    """
    product_name   = serializers.CharField(source='product.name',              read_only=True)
    product_unit   = serializers.CharField(source='product.get_unit_display',  read_only=True)
    branch_name    = serializers.CharField(source='branch.name',               read_only=True)
    warehouse_name = serializers.CharField(source='warehouse.name',            read_only=True)
    location_type  = serializers.SerializerMethodField()
    location_name  = serializers.SerializerMethodField()
    is_empty       = serializers.SerializerMethodField()

    class Meta:
        model  = StockBatch
        fields = (
            'id', 'batch_code',
            'product', 'product_name', 'product_unit',
            'location_type', 'location_name',
            'branch_name', 'warehouse_name',
            'unit_cost',
            'qty_received', 'qty_left',
            'is_empty',
            'movement', 'received_at',
        )

    def get_location_type(self, obj):
        return 'branch' if obj.branch_id else 'warehouse'

    def get_location_name(self, obj):
        if obj.branch_id:
            return obj.branch.name
        return obj.warehouse.name if obj.warehouse_id else None

    def get_is_empty(self, obj):
        """qty_left == 0 bo'lsa — partiya tamom."""
        return obj.qty_left == 0


# ============================================================
# ISROF (WASTAGE) SERIALIZERLARI  B7
# ============================================================

class WastageRecordListSerializer(serializers.ModelSerializer):
    """Isrof ro'yxati uchun qisqa serializer."""
    product_name   = serializers.CharField(source='product.name',             read_only=True)
    product_unit   = serializers.CharField(source='product.get_unit_display', read_only=True)
    reason_display = serializers.CharField(source='get_reason_display',       read_only=True)
    worker_name    = serializers.SerializerMethodField()
    location_type  = serializers.SerializerMethodField()
    location_name  = serializers.SerializerMethodField()

    class Meta:
        model  = WastageRecord
        fields = (
            'id', 'product', 'product_name', 'product_unit',
            'location_type', 'location_name',
            'reason', 'reason_display',
            'quantity', 'date', 'worker_name', 'created_on',
        )

    def get_worker_name(self, obj):
        if obj.worker_id:
            return obj.worker.user.get_full_name() or obj.worker.user.username
        return None

    def get_location_type(self, obj):
        return 'branch' if obj.branch_id else 'warehouse'

    def get_location_name(self, obj):
        if obj.branch_id:
            return obj.branch.name
        return obj.warehouse.name if obj.warehouse_id else None


class WastageRecordDetailSerializer(serializers.ModelSerializer):
    """Isrof tafsiloti uchun to'liq serializer."""
    product_name   = serializers.CharField(source='product.name',             read_only=True)
    product_unit   = serializers.CharField(source='product.get_unit_display', read_only=True)
    reason_display = serializers.CharField(source='get_reason_display',       read_only=True)
    branch_name    = serializers.CharField(source='branch.name',              read_only=True)
    warehouse_name = serializers.CharField(source='warehouse.name',           read_only=True)
    worker_name    = serializers.SerializerMethodField()
    location_type  = serializers.SerializerMethodField()

    class Meta:
        model  = WastageRecord
        fields = (
            'id',
            'product', 'product_name', 'product_unit',
            'location_type',
            'branch', 'branch_name',
            'warehouse', 'warehouse_name',
            'reason', 'reason_display',
            'quantity', 'note', 'date',
            'worker_name', 'created_on',
        )

    def get_worker_name(self, obj):
        if obj.worker_id:
            return obj.worker.user.get_full_name() or obj.worker.user.username
        return None

    def get_location_type(self, obj):
        return 'branch' if obj.branch_id else 'warehouse'


class WastageRecordCreateSerializer(serializers.ModelSerializer):
    """Isrof yaratish uchun serializer. Yaratilganda StockMovement(OUT) avtomatik."""

    class Meta:
        model  = WastageRecord
        fields = ('product', 'branch', 'warehouse', 'quantity', 'reason', 'note', 'date')
        extra_kwargs = {
            'product': {
                'error_messages': {
                    'required'      : "Mahsulot tanlanishi shart.",
                    'does_not_exist': "Bunday mahsulot topilmadi.",
                    'incorrect_type': "Mahsulot ID butun son bo'lishi kerak.",
                }
            },
            'quantity': {
                'error_messages': {
                    'required': "Miqdor kiritilishi shart.",
                    'invalid' : "To'g'ri raqam kiritilishi shart.",
                }
            },
            'date': {
                'error_messages': {
                    'required': "Sana kiritilishi shart.",
                    'invalid' : "To'g'ri sana formatini kiriting (YYYY-MM-DD).",
                }
            },
        }

    def validate_product(self, value):
        store = self.context.get('store')
        if store and value.store != store:
            raise serializers.ValidationError(
                "Bu mahsulot sizning do'koningizga tegishli emas."
            )
        return value

    def validate_branch(self, value):
        store = self.context.get('store')
        if store and value and value.store != store:
            raise serializers.ValidationError(
                "Bu filial sizning do'koningizga tegishli emas."
            )
        return value

    def validate_warehouse(self, value):
        store = self.context.get('store')
        if store and value and value.store != store:
            raise serializers.ValidationError(
                "Bu ombor sizning do'koningizga tegishli emas."
            )
        return value

    def validate_quantity(self, value):
        if value <= 0:
            raise serializers.ValidationError(
                "Miqdor 0 dan katta bo'lishi shart."
            )
        return value

    def validate(self, data):
        branch    = data.get('branch')
        warehouse = data.get('warehouse')

        # branch XOR warehouse
        if branch and warehouse:
            raise serializers.ValidationError(
                "Filial va ombor bir vaqtda ko'rsatilishi mumkin emas. Faqat bittasini tanlang."
            )
        if not branch and not warehouse:
            raise serializers.ValidationError(
                "Filial yoki ombor ko'rsatilishi shart."
            )

        # Qoldiq yetarliligini tekshirish
        product  = data.get('product')
        quantity = data.get('quantity', 0)
        if product:
            stock_qs = Stock.objects.filter(product=product)
            if branch:
                stock_qs = stock_qs.filter(branch=branch)
            else:
                stock_qs = stock_qs.filter(warehouse=warehouse)
            stock       = stock_qs.first()
            current_qty = stock.quantity if stock else 0
            if current_qty < quantity:
                location_name = branch.name if branch else warehouse.name
                raise serializers.ValidationError(
                    f"Qoldiq yetarli emas: '{location_name}' da '{product.name}' "
                    f"uchun {current_qty} dona bor, {quantity} so'ralmoqda."
                )

        return data


# ============================================================
# INVENTARIZATSIYA (STOCK AUDIT) SERIALIZERLARI  B8
# ============================================================

class StockAuditItemSerializer(serializers.ModelSerializer):
    """Inventarizatsiya satri — nested ko'rinish."""
    product_name = serializers.CharField(source='product.name',             read_only=True)
    product_unit = serializers.CharField(source='product.get_unit_display', read_only=True)
    difference   = serializers.SerializerMethodField()

    class Meta:
        model  = StockAuditItem
        fields = (
            'id', 'product', 'product_name', 'product_unit',
            'expected_qty', 'actual_qty', 'difference',
        )

    def get_difference(self, obj):
        """actual_qty - expected_qty. Musbat = oshiqcha, manfiy = kamomad."""
        return obj.actual_qty - obj.expected_qty


class StockAuditListSerializer(serializers.ModelSerializer):
    """Inventarizatsiya ro'yxati uchun qisqa serializer."""
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    worker_name    = serializers.SerializerMethodField()
    location_type  = serializers.SerializerMethodField()
    location_name  = serializers.SerializerMethodField()
    items_count    = serializers.SerializerMethodField()

    class Meta:
        model  = StockAudit
        fields = (
            'id', 'status', 'status_display',
            'location_type', 'location_name',
            'items_count', 'worker_name',
            'created_on', 'confirmed_on',
        )

    def get_worker_name(self, obj):
        if obj.worker_id:
            return obj.worker.user.get_full_name() or obj.worker.user.username
        return None

    def get_location_type(self, obj):
        return 'branch' if obj.branch_id else 'warehouse'

    def get_location_name(self, obj):
        if obj.branch_id:
            return obj.branch.name
        return obj.warehouse.name if obj.warehouse_id else None

    def get_items_count(self, obj):
        return obj.items.count()


class StockAuditDetailSerializer(serializers.ModelSerializer):
    """Inventarizatsiya tafsiloti — nested StockAuditItem'lar bilan."""
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    branch_name    = serializers.CharField(source='branch.name',        read_only=True)
    warehouse_name = serializers.CharField(source='warehouse.name',     read_only=True)
    worker_name    = serializers.SerializerMethodField()
    location_type  = serializers.SerializerMethodField()
    items          = StockAuditItemSerializer(many=True, read_only=True)

    class Meta:
        model  = StockAudit
        fields = (
            'id', 'status', 'status_display',
            'location_type',
            'branch', 'branch_name',
            'warehouse', 'warehouse_name',
            'note', 'worker_name',
            'created_on', 'confirmed_on',
            'items',
        )

    def get_worker_name(self, obj):
        if obj.worker_id:
            return obj.worker.user.get_full_name() or obj.worker.user.username
        return None

    def get_location_type(self, obj):
        return 'branch' if obj.branch_id else 'warehouse'


class StockAuditCreateSerializer(serializers.ModelSerializer):
    """
    Inventarizatsiya yaratish.
    Yaratilganda tanlangan joy (branch | warehouse) dagi barcha mahsulotlar
    uchun StockAuditItem'lar avtomatik yaratiladi.
    expected_qty = joriy Stock.quantity.
    actual_qty   = expected_qty (xodim keyinroq PATCH bilan o'zgartiradi).
    """

    class Meta:
        model  = StockAudit
        fields = ('branch', 'warehouse', 'note')
        extra_kwargs = {
            'branch': {
                'error_messages': {
                    'does_not_exist': "Bunday filial topilmadi.",
                    'incorrect_type': "Filial ID butun son bo'lishi kerak.",
                }
            },
            'warehouse': {
                'error_messages': {
                    'does_not_exist': "Bunday ombor topilmadi.",
                    'incorrect_type': "Ombor ID butun son bo'lishi kerak.",
                }
            },
        }

    def validate_branch(self, value):
        store = self.context.get('store')
        if store and value and value.store != store:
            raise serializers.ValidationError(
                "Bu filial sizning do'koningizga tegishli emas."
            )
        return value

    def validate_warehouse(self, value):
        store = self.context.get('store')
        if store and value and value.store != store:
            raise serializers.ValidationError(
                "Bu ombor sizning do'koningizga tegishli emas."
            )
        return value

    def validate(self, data):
        branch    = data.get('branch')
        warehouse = data.get('warehouse')

        # branch XOR warehouse
        if branch and warehouse:
            raise serializers.ValidationError(
                "Filial va ombor bir vaqtda ko'rsatilishi mumkin emas. Faqat bittasini tanlang."
            )
        if not branch and not warehouse:
            raise serializers.ValidationError(
                "Filial yoki ombor ko'rsatilishi shart."
            )

        # Mavjud DRAFT auditni tekshirish (UniqueConstraint bilan bir xil, lekin tushunarliroq xato)
        if branch and StockAudit.objects.filter(branch=branch, status=AuditStatus.DRAFT).exists():
            raise serializers.ValidationError(
                f"'{branch.name}' filialida allaqachon faol (draft) inventarizatsiya mavjud."
            )
        if warehouse and StockAudit.objects.filter(warehouse=warehouse, status=AuditStatus.DRAFT).exists():
            raise serializers.ValidationError(
                f"'{warehouse.name}' omborida allaqachon faol (draft) inventarizatsiya mavjud."
            )

        return data


class StockAuditItemUpdateSerializer(serializers.ModelSerializer):
    """
    Inventarizatsiya satri yangilash — faqat actual_qty.
    Faqat DRAFT holatdagi inventarizatsiya satrini yangilash mumkin.
    """

    class Meta:
        model  = StockAuditItem
        fields = ('actual_qty',)
        extra_kwargs = {
            'actual_qty': {
                'error_messages': {
                    'required': "Haqiqiy miqdor kiritilishi shart.",
                    'invalid' : "To'g'ri raqam kiritilishi shart.",
                }
            }
        }

    def validate_actual_qty(self, value):
        if value < 0:
            raise serializers.ValidationError(
                "Miqdor manfiy bo'lishi mumkin emas."
            )
        return value

    def validate(self, data):
        # Auditning draft holatini tekshirish
        if self.instance and self.instance.audit.status != AuditStatus.DRAFT:
            raise serializers.ValidationError(
                "Faqat 'draft' inventarizatsiya satrini yangilash mumkin."
            )
        return data
