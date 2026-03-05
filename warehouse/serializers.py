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
  6. Warehouse serializers   <- YANGI
  7. Stock serializers       <- YANGILANDI (branch|warehouse)
  8. StockMovement serializers <- YANGILANDI (branch|warehouse)
"""

from rest_framework import serializers

from .models import (
    Category,
    Currency,
    ExchangeRate,
    MovementType,
    Product,
    ProductStatus,
    Stock,
    StockMovement,
    SubCategory,
    Warehouse,
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
        return obj.products.filter(status=ProductStatus.ACTIVE).count()

    def get_subcategory_count(self, obj):
        return obj.subcategories.filter(status=ProductStatus.ACTIVE).count()


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
        return obj.products.filter(status=ProductStatus.ACTIVE).count()

    def get_subcategory_count(self, obj):
        return obj.subcategories.filter(status=ProductStatus.ACTIVE).count()


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
                "Bu nomli kategoriya ushbu do'konda allaqachon mavjud."
            )
        return value


class CategoryUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Category
        fields = ('name', 'description')
        extra_kwargs = {
            'name': {
                'error_messages': {
                    'blank'     : "Kategoriya nomi bo'sh bo'lishi mumkin emas.",
                    'max_length': "Kategoriya nomi 200 belgidan oshmasligi kerak.",
                }
            },
        }

    def validate_name(self, value):
        qs = Category.objects.filter(
            store=self.instance.store, name=value
        ).exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError(
                "Bu nomli kategoriya ushbu do'konda allaqachon mavjud."
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
        return obj.products.filter(status=ProductStatus.ACTIVE).count()


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
        return obj.products.filter(status=ProductStatus.ACTIVE).count()


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
                    "Bu kategoriyada bunday nomli subkategoriya allaqachon mavjud."
                )
        return data


class SubCategoryUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model  = SubCategory
        fields = ('name', 'description', 'category')
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
                "Bu kategoriyada bunday nomli subkategoriya allaqachon mavjud."
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
            return {'rate': '1.0000', 'date': None, 'source': 'Base'}
        latest = obj.rates.order_by('-date').first()
        if latest:
            return {'rate': str(latest.rate), 'date': str(latest.date), 'source': latest.source}
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
        fields = ('id', 'currency_code', 'currency_symbol', 'rate', 'date', 'source')


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
            'rate', 'date', 'source', 'created_on',
        )


class ExchangeRateCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model  = ExchangeRate
        fields = ('currency', 'rate', 'date', 'source')
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

    class Meta:
        model  = Product
        fields = (
            'id', 'name',
            'category_id', 'category_name',
            'subcategory_id', 'subcategory_name',
            'unit', 'unit_display',
            'purchase_price', 'sale_price',
            'currency_id', 'currency_code', 'currency_symbol',
            'barcode', 'image',
            'store_name', 'status', 'status_display',
            'stock_total', 'created_on',
        )

    def get_stock_total(self, obj):
        from django.db.models import Sum
        result = obj.stocks.aggregate(total=Sum('quantity'))
        return result['total'] or 0


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
                "Bu nomli mahsulot do'koningizda allaqachon mavjud."
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
                    "Bu nomli mahsulot do'koningizda allaqachon mavjud."
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
        fields = ('id', 'name', 'address', 'is_active', 'stock_count')

    def get_stock_count(self, obj):
        return obj.stocks.count()


class WarehouseDetailSerializer(serializers.ModelSerializer):
    store_name  = serializers.CharField(source='store.name', read_only=True)
    stock_count = serializers.SerializerMethodField()

    class Meta:
        model  = Warehouse
        fields = (
            'id', 'name', 'address',
            'store_name', 'is_active',
            'stock_count', 'created_on',
        )

    def get_stock_count(self, obj):
        return obj.stocks.count()


class WarehouseCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Warehouse
        fields = ('name', 'address')
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
        if store and Warehouse.objects.filter(store=store, name=value).exists():
            raise serializers.ValidationError(
                "Bu nomli ombor do'koningizda allaqachon mavjud."
            )
        return value


class WarehouseUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Warehouse
        fields = ('name', 'address', 'is_active')
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
                "Bu nomli ombor do'koningizda allaqachon mavjud."
            )
        return value


# ============================================================
# OMBOR QOLDIG'I SERIALIZERLARI
# ============================================================

class StockListSerializer(serializers.ModelSerializer):
    product_name  = serializers.CharField(source='product.name', read_only=True)
    product_unit  = serializers.CharField(source='product.get_unit_display', read_only=True)
    location_type = serializers.SerializerMethodField()
    location_name = serializers.SerializerMethodField()

    class Meta:
        model  = Stock
        fields = (
            'id', 'product_name', 'product_unit',
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
            'quantity', 'worker_name', 'created_on',
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
            'quantity', 'note',
            'worker_name', 'created_on',
        )

    def get_worker_name(self, obj):
        if obj.worker_id:
            return obj.worker.user.get_full_name() or obj.worker.user.username
        return None

    def get_location_type(self, obj):
        return 'branch' if obj.branch_id else 'warehouse'


class MovementCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model  = StockMovement
        fields = ('product', 'branch', 'warehouse', 'movement_type', 'quantity', 'note')
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
