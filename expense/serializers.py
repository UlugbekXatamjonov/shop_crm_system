"""
============================================================
EXPENSE APP — Serializerlar
============================================================
Serializerlar:
  ExpenseCategoryListSerializer   — GET /expense-categories/
  ExpenseCategoryDetailSerializer — GET /expense-categories/{id}/
  ExpenseCategoryCreateSerializer — POST /expense-categories/
  ExpenseCategoryUpdateSerializer — PATCH /expense-categories/{id}/
  ExpenseListSerializer           — GET /expenses/
  ExpenseDetailSerializer         — GET /expenses/{id}/
  ExpenseCreateSerializer         — POST /expenses/
  ExpenseUpdateSerializer         — PATCH /expenses/{id}/
"""

from rest_framework import serializers

from store.models import Branch

from .models import Expense, ExpenseCategory


# ============================================================
# XARAJAT KATEGORIYASI SERIALIZERLARI
# ============================================================

class ExpenseCategoryListSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    expense_count  = serializers.SerializerMethodField()

    class Meta:
        model  = ExpenseCategory
        fields = ('id', 'name', 'status', 'status_display', 'expense_count')

    def get_expense_count(self, obj):
        return obj.expenses.count()


class ExpenseCategoryDetailSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    store_name     = serializers.CharField(source='store.name', read_only=True)
    expense_count  = serializers.SerializerMethodField()

    class Meta:
        model  = ExpenseCategory
        fields = (
            'id', 'name', 'store_name',
            'status', 'status_display',
            'expense_count', 'created_on',
        )

    def get_expense_count(self, obj):
        return obj.expenses.count()


class ExpenseCategoryCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model  = ExpenseCategory
        fields = ('name',)
        extra_kwargs = {
            'name': {
                'error_messages': {
                    'required':   "Kategoriya nomi kiritilishi shart.",
                    'blank':      "Kategoriya nomi bo'sh bo'lishi mumkin emas.",
                    'max_length': "Kategoriya nomi 200 belgidan oshmasligi kerak.",
                }
            },
        }

    def validate_name(self, value):
        store = self.context.get('store')
        if store and ExpenseCategory.objects.filter(store=store, name=value).exists():
            raise serializers.ValidationError(
                "Bunday nomli Xarajat kategoriyasi mavjud. Iltimos boshqa nom tanlang !"
            )
        return value


class ExpenseCategoryUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model  = ExpenseCategory
        fields = ('name', 'status')
        extra_kwargs = {
            'name': {
                'required': False,
                'error_messages': {
                    'blank':      "Kategoriya nomi bo'sh bo'lishi mumkin emas.",
                    'max_length': "Kategoriya nomi 200 belgidan oshmasligi kerak.",
                }
            },
            'status': {'required': False},
        }

    def validate_name(self, value):
        store    = self.context.get('store')
        instance = self.instance
        qs = ExpenseCategory.objects.filter(store=store, name=value)
        if instance:
            qs = qs.exclude(pk=instance.pk)
        if qs.exists():
            raise serializers.ValidationError(
                "Bunday nomli Xarajat kategoriyasi mavjud. Iltimos boshqa nom tanlang !"
            )
        return value


# ============================================================
# XARAJAT SERIALIZERLARI
# ============================================================

class ExpenseListSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    branch_name   = serializers.CharField(source='branch.name',   read_only=True)
    worker_name   = serializers.SerializerMethodField()

    class Meta:
        model  = Expense
        fields = (
            'id', 'category_name', 'branch_name', 'worker_name',
            'amount', 'date', 'created_on',
        )

    def get_worker_name(self, obj):
        user = obj.worker.user
        full_name = f"{user.first_name} {user.last_name}".strip()
        return full_name or user.username


class ExpenseDetailSerializer(serializers.ModelSerializer):
    category_id   = serializers.IntegerField(source='category.id',   read_only=True)
    category_name = serializers.CharField(source='category.name',    read_only=True)
    branch_id     = serializers.IntegerField(source='branch.id',     read_only=True)
    branch_name   = serializers.CharField(source='branch.name',      read_only=True)
    worker_id     = serializers.IntegerField(source='worker.id',     read_only=True)
    worker_name   = serializers.SerializerMethodField()
    smena_id      = serializers.IntegerField(source='smena.id',      read_only=True, allow_null=True)

    class Meta:
        model  = Expense
        fields = (
            'id',
            'category_id', 'category_name',
            'branch_id', 'branch_name',
            'worker_id', 'worker_name',
            'smena_id',
            'amount', 'description', 'date',
            'receipt_image', 'created_on',
        )

    def get_worker_name(self, obj):
        user = obj.worker.user
        full_name = f"{user.first_name} {user.last_name}".strip()
        return full_name or user.username


class ExpenseCreateSerializer(serializers.ModelSerializer):
    branch = serializers.PrimaryKeyRelatedField(
        queryset=Branch.objects.all(),
        required=False,
        allow_null=True,
    )

    class Meta:
        model  = Expense
        fields = ('category', 'branch', 'amount', 'description', 'date', 'receipt_image')
        extra_kwargs = {
            'category': {
                'error_messages': {
                    'required':       "Kategoriya kiritilishi shart.",
                    'does_not_exist': "Bunday kategoriya topilmadi.",
                }
            },
            'amount': {
                'error_messages': {
                    'required': "Summa kiritilishi shart.",
                    'invalid':  "To'g'ri summa kiritilishi shart.",
                }
            },
            'date': {
                'error_messages': {
                    'required': "Sana kiritilishi shart.",
                    'invalid':  "To'g'ri sana kiritilishi shart (YYYY-MM-DD).",
                }
            },
            'description':   {'required': False},
            'receipt_image': {'required': False},
        }

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Summa musbat bo'lishi shart.")
        return value

    def validate(self, data):
        request  = self.context.get('request')
        worker   = getattr(request.user, 'worker', None)
        store    = getattr(worker, 'store', None)

        # Category store validatsiya
        category = data.get('category')
        if category and category.store_id != store.id:
            raise serializers.ValidationError(
                {'category': "Bu kategoriya sizning do'koningizga tegishli emas."}
            )
        if category and category.status == 'inactive':
            raise serializers.ValidationError(
                {'category': "Bu kategoriya nofaol."}
            )

        # Branch validatsiya
        branch = data.get('branch')
        if branch is None:
            branch = getattr(worker, 'branch', None)
        if branch is None:
            raise serializers.ValidationError(
                {'branch': "Filial ko'rsatilishi shart."}
            )
        if branch.store_id != store.id:
            raise serializers.ValidationError(
                {'branch': "Bu filial sizning do'koningizga tegishli emas."}
            )
        data['branch'] = branch

        return data


class ExpenseUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Expense
        fields = ('category', 'amount', 'description', 'date', 'receipt_image')
        extra_kwargs = {
            'category':      {'required': False},
            'amount':        {'required': False},
            'description':   {'required': False},
            'date':          {'required': False},
            'receipt_image': {'required': False},
        }

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Summa musbat bo'lishi shart.")
        return value

    def validate_category(self, value):
        request = self.context.get('request')
        worker  = getattr(request.user, 'worker', None)
        store   = getattr(worker, 'store', None)
        if value.store_id != store.id:
            raise serializers.ValidationError(
                "Bu kategoriya sizning do'koningizga tegishli emas."
            )
        if value.status == 'inactive':
            raise serializers.ValidationError("Bu kategoriya nofaol.")
        return value
