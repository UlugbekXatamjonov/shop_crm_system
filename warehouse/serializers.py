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
