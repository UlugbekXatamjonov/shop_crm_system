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
  6. Stock serializers
  7. StockMovement serializers
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
)


# ============================================================
# KATEGORIYA SERIALIZERLARI
# ============================================================

class CategoryListSerializer(serializers.ModelSerializer):
    """
    Kategoriyalar ro'yxati uchun qisqa serializer.
    GET /api/v1/warehouse/categories/ da ishlatiladi.
    """
    status_display    = serializers.CharField(source='get_status_display', read_only=True)
    product_count     = serializers.SerializerMethodField()
    subcategory_count = serializers.SerializerMethodField()

    class Meta:
        model  = Category
        fields = ('id', 'name', 'status', 'status_display', 'product_count', 'subcategory_count')

    def get_product_count(self, obj: Category) -> int:
        return obj.products.filter(status=ProductStatus.ACTIVE).count()

    def get_subcategory_count(self, obj: Category) -> int:
        return obj.subcategories.filter(status=ProductStatus.ACTIVE).count()


class CategoryDetailSerializer(serializers.ModelSerializer):
    """
    Kategoriyaning to'liq ma'lumoti.
    GET /api/v1/warehouse/categories/{id}/ da ishlatiladi.
    """
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

    def get_product_count(self, obj: Category) -> int:
        return obj.products.filter(status=ProductStatus.ACTIVE).count()

    def get_subcategory_count(self, obj: Category) -> int:
        return obj.subcategories.filter(status=ProductStatus.ACTIVE).count()


class CategoryCreateSerializer(serializers.ModelSerializer):
    """
    Yangi kategoriya yaratish.
    POST /api/v1/warehouse/categories/ da ishlatiladi.
    store maydoni view da avtomatik beriladi (perform_create).
    """

    class Meta:
        model  = Category
        fields = ('name', 'description')
        extra_kwargs = {
            'name': {
                'error_messages': {
                    'required':   "Kategoriya nomi kiritilishi shart.",
                    'blank':      "Kategoriya nomi bo'sh bo'lishi mumkin emas.",
                    'max_length': "Kategoriya nomi 200 belgidan oshmasligi kerak.",
                }
            },
        }

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
        extra_kwargs = {
            'name': {
                'error_messages': {
                    'blank':      "Kategoriya nomi bo'sh bo'lishi mumkin emas.",
                    'max_length': "Kategoriya nomi 200 belgidan oshmasligi kerak.",
                }
            },
        }

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
# SUBKATEGORIYA SERIALIZERLARI (BOSQICH 1.1)
# ============================================================

class SubCategoryListSerializer(serializers.ModelSerializer):
    """
    Subkategoriyalar ro'yxati uchun qisqa serializer.
    GET /api/v1/warehouse/subcategories/ da ishlatiladi.
    """
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    category_name  = serializers.CharField(source='category.name', read_only=True)
    product_count  = serializers.SerializerMethodField()

    class Meta:
        model  = SubCategory
        fields = (
            'id', 'name', 'category_id', 'category_name',
            'status', 'status_display', 'product_count',
        )

    def get_product_count(self, obj: SubCategory) -> int:
        return obj.products.filter(status=ProductStatus.ACTIVE).count()


class SubCategoryDetailSerializer(serializers.ModelSerializer):
    """
    Subkategoriyaning to'liq ma'lumoti.
    GET /api/v1/warehouse/subcategories/{id}/ da ishlatiladi.
    """
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

    def get_product_count(self, obj: SubCategory) -> int:
        return obj.products.filter(status=ProductStatus.ACTIVE).count()


class SubCategoryCreateSerializer(serializers.ModelSerializer):
    """
    Yangi subkategoriya yaratish.
    POST /api/v1/warehouse/subcategories/ da ishlatiladi.
    store maydoni view da avtomatik beriladi.
    """

    class Meta:
        model  = SubCategory
        fields = ('name', 'description', 'category')
        extra_kwargs = {
            'name': {
                'error_messages': {
                    'required':   "Subkategoriya nomi kiritilishi shart.",
                    'blank':      "Subkategoriya nomi bo'sh bo'lishi mumkin emas.",
                    'max_length': "Subkategoriya nomi 200 belgidan oshmasligi kerak.",
                }
            },
            'category': {
                'error_messages': {
                    'required':       "Kategoriya tanlanishi shart.",
                    'does_not_exist': "Bunday kategoriya topilmadi.",
                    'incorrect_type': "Kategoriya ID butun son bo'lishi kerak.",
                }
            },
        }

    def validate_category(self, value: Category) -> Category:
        """Kategoriya xuddi shu do'konga tegishli bo'lishi kerak."""
        store = self.context.get('store')
        if store and value.store != store:
            raise serializers.ValidationError(
                "Ushbu kategoriya sizning do'koningizga tegishli emas."
            )
        return value

    def validate(self, data: dict) -> dict:
        """Do'kon ichida bir kategoriyada bir xil nom bo'lmasin."""
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
    """
    Subkategoriya ma'lumotlarini yangilash.
    PATCH /api/v1/warehouse/subcategories/{id}/ da ishlatiladi.
    """

    class Meta:
        model  = SubCategory
        fields = ('name', 'description', 'category')
        extra_kwargs = {
            'name': {
                'error_messages': {
                    'blank':      "Subkategoriya nomi bo'sh bo'lishi mumkin emas.",
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

    def validate_category(self, value: Category) -> Category:
        if value and value.store != self.instance.store:
            raise serializers.ValidationError(
                "Ushbu kategoriya sizning do'koningizga tegishli emas."
            )
        return value

    def validate(self, data: dict) -> dict:
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
# VALYUTA SERIALIZERLARI (BOSQICH 1.3)
# ============================================================

class CurrencyListSerializer(serializers.ModelSerializer):
    """
    Valyutalar ro'yxati.
    GET /api/v1/warehouse/currencies/ da ishlatiladi.
    """
    class Meta:
        model  = Currency
        fields = ('id', 'code', 'name', 'symbol', 'is_base')


class CurrencyDetailSerializer(serializers.ModelSerializer):
    """
    Valyuta to'liq ma'lumoti.
    """
    latest_rate = serializers.SerializerMethodField()

    class Meta:
        model  = Currency
        fields = ('id', 'code', 'name', 'symbol', 'is_base', 'latest_rate')

    def get_latest_rate(self, obj: Currency) -> dict | None:
        """Eng oxirgi mavjud kurs."""
        if obj.is_base:
            return {'rate': '1.0000', 'date': None, 'source': 'Base'}
        latest = obj.rates.order_by('-date').first()
        if latest:
            return {
                'rate':   str(latest.rate),
                'date':   str(latest.date),
                'source': latest.source,
            }
        return None


class CurrencyCreateSerializer(serializers.ModelSerializer):
    """
    Yangi valyuta qo'shish (admin/manager).
    POST /api/v1/warehouse/currencies/ da ishlatiladi.
    """
    class Meta:
        model  = Currency
        fields = ('code', 'name', 'symbol', 'is_base')
        extra_kwargs = {
            'code': {
                'error_messages': {
                    'required':   "Valyuta kodi kiritilishi shart.",
                    'blank':      "Valyuta kodi bo'sh bo'lishi mumkin emas.",
                    'max_length': "Valyuta kodi 3 belgidan oshmasligi kerak.",
                    'unique':     "Bu valyuta kodi allaqachon mavjud.",
                }
            },
            'name': {
                'error_messages': {
                    'required':   "Valyuta nomi kiritilishi shart.",
                    'blank':      "Valyuta nomi bo'sh bo'lishi mumkin emas.",
                }
            },
            'symbol': {
                'error_messages': {
                    'required':   "Valyuta belgisi kiritilishi shart.",
                    'blank':      "Valyuta belgisi bo'sh bo'lishi mumkin emas.",
                }
            },
        }

    def validate_code(self, value: str) -> str:
        return value.upper().strip()

    def validate_is_base(self, value: bool) -> bool:
        if value and Currency.objects.filter(is_base=True).exists():
            raise serializers.ValidationError(
                "Asosiy valyuta allaqachon mavjud. Faqat bitta asosiy valyuta bo'lishi mumkin."
            )
        return value


# ============================================================
# VALYUTA KURSI SERIALIZERLARI (BOSQICH 1.3)
# ============================================================

class ExchangeRateListSerializer(serializers.ModelSerializer):
    """
    Valyuta kurslari ro'yxati.
    GET /api/v1/warehouse/exchange-rates/ da ishlatiladi.
    """
    currency_code   = serializers.CharField(source='currency.code', read_only=True)
    currency_symbol = serializers.CharField(source='currency.symbol', read_only=True)

    class Meta:
        model  = ExchangeRate
        fields = ('id', 'currency_code', 'currency_symbol', 'rate', 'date', 'source')


class ExchangeRateDetailSerializer(serializers.ModelSerializer):
    """
    Valyuta kursi to'liq ma'lumoti.
    """
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
    """
    Qo'lda valyuta kursi kiritish (manager).
    POST /api/v1/warehouse/exchange-rates/ da ishlatiladi.
    CBU task avtomatik yangilaydi, bu faqat qo'lda kiritish uchun.
    """
    class Meta:
        model  = ExchangeRate
        fields = ('currency', 'rate', 'date', 'source')
        extra_kwargs = {
            'currency': {
                'error_messages': {
                    'required':       "Valyuta tanlanishi shart.",
                    'does_not_exist': "Bunday valyuta topilmadi.",
                    'incorrect_type': "Valyuta ID butun son bo'lishi kerak.",
                }
            },
            'rate': {
                'error_messages': {
                    'required': "Kurs kiritilishi shart.",
                    'invalid':  "To'g'ri raqam kiritilishi shart.",
                    'max_digits': "Raqam juda katta.",
                }
            },
            'date': {
                'error_messages': {
                    'required': "Sana kiritilishi shart.",
                    'invalid':  "Sana formati noto'g'ri. To'g'ri format: YYYY-MM-DD.",
                }
            },
        }

    def validate(self, data: dict) -> dict:
        currency = data.get('currency')
        date     = data.get('date')
        if currency and date:
            if ExchangeRate.objects.filter(currency=currency, date=date).exists():
                raise serializers.ValidationError(
                    f"{currency.code} uchun {date} sanasida kurs allaqachon mavjud. "
                    "Yangilash uchun PATCH ishlatil."
                )
        return data


# ============================================================
# MAHSULOT SERIALIZERLARI
# ============================================================

class ProductListSerializer(serializers.ModelSerializer):
    """
    Mahsulotlar ro'yxati uchun qisqa serializer.
    GET /api/v1/warehouse/products/ da ishlatiladi.
    """
    category_name    = serializers.CharField(
        source='category.name', read_only=True, default=None
    )
    subcategory_name = serializers.CharField(
        source='subcategory.name', read_only=True, default=None
    )
    unit_display     = serializers.CharField(source='get_unit_display', read_only=True)
    status_display   = serializers.CharField(source='get_status_display', read_only=True)
    currency_code    = serializers.CharField(
        source='price_currency.code', read_only=True, default='UZS'
    )

    class Meta:
        model  = Product
        fields = (
            'id', 'name',
            'category_name', 'subcategory_name',
            'unit', 'unit_display',
            'sale_price', 'currency_code',
            'barcode', 'image',
            'status', 'status_display',
        )


class ProductDetailSerializer(serializers.ModelSerializer):
    """
    Mahsulotning to'liq ma'lumoti.
    GET /api/v1/warehouse/products/{id}/ da ishlatiladi.
    """
    category_id      = serializers.IntegerField(
        source='category.id', read_only=True, default=None
    )
    category_name    = serializers.CharField(
        source='category.name', read_only=True, default=None
    )
    subcategory_id   = serializers.IntegerField(
        source='subcategory.id', read_only=True, default=None
    )
    subcategory_name = serializers.CharField(
        source='subcategory.name', read_only=True, default=None
    )
    unit_display     = serializers.CharField(source='get_unit_display', read_only=True)
    status_display   = serializers.CharField(source='get_status_display', read_only=True)
    store_name       = serializers.CharField(source='store.name', read_only=True)
    currency_code    = serializers.CharField(
        source='price_currency.code', read_only=True, default='UZS'
    )
    currency_symbol  = serializers.CharField(
        source='price_currency.symbol', read_only=True, default='so\'m'
    )

    class Meta:
        model  = Product
        fields = (
            'id', 'name',
            'category_id', 'category_name',
            'subcategory_id', 'subcategory_name',
            'unit', 'unit_display',
            'purchase_price', 'sale_price',
            'currency_code', 'currency_symbol',
            'barcode', 'image', 'store_name',
            'status', 'status_display',
            'created_on',
        )


class ProductCreateSerializer(serializers.ModelSerializer):
    """
    Yangi mahsulot yaratish.
    POST /api/v1/warehouse/products/ da ishlatiladi.
    store maydoni view da avtomatik beriladi (perform_create).
    barcode bo'sh bo'lsa perform_create da avtomatik EAN-13 generatsiya qilinadi.
    """

    class Meta:
        model  = Product
        fields = (
            'name', 'category', 'subcategory',
            'unit', 'purchase_price', 'sale_price', 'price_currency',
            'barcode', 'image',
        )
        extra_kwargs = {
            'name': {
                'error_messages': {
                    'required':   "Mahsulot nomi kiritilishi shart.",
                    'blank':      "Mahsulot nomi bo'sh bo'lishi mumkin emas.",
                    'max_length': "Mahsulot nomi 300 belgidan oshmasligi kerak.",
                }
            },
            'category': {
                'error_messages': {
                    'does_not_exist': "Bunday kategoriya topilmadi.",
                    'incorrect_type': "Kategoriya ID butun son bo'lishi kerak.",
                }
            },
            'subcategory': {
                'error_messages': {
                    'does_not_exist': "Bunday subkategoriya topilmadi.",
                    'incorrect_type': "Subkategoriya ID butun son bo'lishi kerak.",
                }
            },
            'unit': {
                'error_messages': {
                    'invalid_choice': "'{input}' noto'g'ri o'lchov birligi.",
                }
            },
            'purchase_price': {
                'error_messages': {
                    'invalid':  "To'g'ri xarid narxi kiritilishi shart.",
                    'max_digits': "Xarid narxi juda katta.",
                }
            },
            'sale_price': {
                'error_messages': {
                    'invalid':    "To'g'ri sotuv narxi kiritilishi shart.",
                    'max_digits': "Sotuv narxi juda katta.",
                }
            },
            'price_currency': {
                'error_messages': {
                    'does_not_exist': "Bunday valyuta topilmadi.",
                    'incorrect_type': "Valyuta ID butun son bo'lishi kerak.",
                }
            },
        }

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

    def validate_subcategory(self, value: SubCategory | None) -> SubCategory | None:
        """Subkategoriya xuddi shu do'konga tegishli bo'lishi kerak."""
        if not value:
            return None
        store = self.context.get('store')
        if store and value.store != store:
            raise serializers.ValidationError(
                "Ushbu subkategoriya sizning do'koningizga tegishli emas."
            )
        return value

    def validate_barcode(self, value: str | None) -> str | None:
        """Shtrix-kod do'kon ichida unikal bo'lishi kerak. Bo'sh bo'lsa — auto-generate."""
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
            'name', 'category', 'subcategory',
            'unit', 'purchase_price', 'sale_price', 'price_currency',
            'barcode', 'image', 'status',
        )
        extra_kwargs = {
            'name': {
                'error_messages': {
                    'blank':      "Mahsulot nomi bo'sh bo'lishi mumkin emas.",
                    'max_length': "Mahsulot nomi 300 belgidan oshmasligi kerak.",
                }
            },
            'unit': {
                'error_messages': {
                    'invalid_choice': "'{input}' noto'g'ri o'lchov birligi.",
                }
            },
            'status': {
                'error_messages': {
                    'invalid_choice': "'{input}' noto'g'ri holat. Mavjud: active, inactive.",
                }
            },
            'purchase_price': {
                'error_messages': {
                    'invalid': "To'g'ri xarid narxi kiritilishi shart.",
                }
            },
            'sale_price': {
                'error_messages': {
                    'invalid': "To'g'ri sotuv narxi kiritilishi shart.",
                }
            },
        }

    def validate_name(self, value: str) -> str:
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

    def validate_subcategory(self, value: SubCategory | None) -> SubCategory | None:
        if not value:
            return None
        if value.store != self.instance.store:
            raise serializers.ValidationError(
                "Ushbu subkategoriya sizning do'koningizga tegishli emas."
            )
        return value

    def validate_barcode(self, value: str | None) -> str | None:
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
        extra_kwargs = {
            'product': {
                'error_messages': {
                    'required':       "Mahsulot tanlanishi shart.",
                    'does_not_exist': "Bunday mahsulot topilmadi.",
                    'incorrect_type': "Mahsulot ID butun son bo'lishi kerak.",
                }
            },
            'branch': {
                'error_messages': {
                    'required':       "Filial tanlanishi shart.",
                    'does_not_exist': "Bunday filial topilmadi.",
                    'incorrect_type': "Filial ID butun son bo'lishi kerak.",
                }
            },
            'quantity': {
                'error_messages': {
                    'required': "Miqdor kiritilishi shart.",
                    'invalid':  "To'g'ri miqdor kiritilishi shart.",
                }
            },
        }

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
        extra_kwargs = {
            'quantity': {
                'error_messages': {
                    'required': "Miqdor kiritilishi shart.",
                    'invalid':  "To'g'ri miqdor kiritilishi shart.",
                }
            },
        }


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
        extra_kwargs = {
            'product': {
                'error_messages': {
                    'required':       "Mahsulot tanlanishi shart.",
                    'does_not_exist': "Bunday mahsulot topilmadi.",
                    'incorrect_type': "Mahsulot ID butun son bo'lishi kerak.",
                }
            },
            'branch': {
                'error_messages': {
                    'required':       "Filial tanlanishi shart.",
                    'does_not_exist': "Bunday filial topilmadi.",
                    'incorrect_type': "Filial ID butun son bo'lishi kerak.",
                }
            },
            'movement_type': {
                'error_messages': {
                    'required':       "Harakat turi tanlanishi shart.",
                    'invalid_choice': "'{input}' noto'g'ri harakat turi. Mavjud: IN (kirim), OUT (chiqim).",
                }
            },
            'quantity': {
                'error_messages': {
                    'required': "Miqdor kiritilishi shart.",
                    'invalid':  "To'g'ri miqdor kiritilishi shart.",
                }
            },
            'note': {
                'error_messages': {
                    'max_length': "Izoh 500 belgidan oshmasligi kerak.",
                }
            },
        }

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
