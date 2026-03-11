"""
============================================================
TRADE APP — View'lar
============================================================
ViewSet'lar:
  CustomerGroupViewSet — Mijoz guruhlari CRUD
  CustomerViewSet      — Mijozlar CRUD (soft delete)
  SaleViewSet          — Sotuvlar (create + cancel, list, retrieve)
  SaleReturnViewSet    — Qaytarishlar (create, confirm, cancel, list, retrieve)

Sale yaratish (POST /sales/) — @transaction.atomic:
  1. StoreSettings validatsiya (allow_cash/card/debt, allow_discount, shift_enabled)
  2. Branch + customer store validatsiya
  3. StockMovement(OUT) yaratish + Stock yangilash (select_for_update + F())
  4. Sale + SaleItem saqlash
  5. Customer.debt_balance yangilash (nasiya bo'lsa)
  6. AuditLog yozish

Sale bekor qilish (PATCH /sales/{id}/cancel/) — @transaction.atomic:
  1. Faqat 'completed' savdoni bekor qilish mumkin
  2. Har bir SaleItem uchun StockMovement(IN) + Stock yangilash
  3. Customer.debt_balance kamaytirish (nasiya bo'lsa)
  4. sale.status = 'cancelled'
  5. AuditLog yozish

SaleReturn yaratish (POST /sale-returns/) — pending holat:
  1. sale_return_enabled tekshiruvi (StoreSettings)
  2. Branch + customer + sale store validatsiya
  3. SaleReturn + SaleReturnItem saqlash (status=pending)
  4. AuditLog yozish

SaleReturn tasdiqlash (PATCH /sale-returns/{id}/confirm/) — @transaction.atomic:
  1. Faqat 'pending' qaytarish tasdiqlanadi
  2. Har bir SaleReturnItem uchun StockMovement(IN) + Stock yangilash
  3. SaleReturn.status = 'confirmed'
  4. AuditLog yozish
"""

from decimal import Decimal

from django.db import transaction
from django.db.models import F, Q, Sum, Count
from django.utils import timezone

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accaunt.models import AuditLog
from accaunt.permissions import CanAccess, IsManagerOrAbove

from config.cache_utils import get_store_settings

from store.models import Smena, SmenaStatus

from warehouse.models import MovementType, Stock, StockMovement
from warehouse.utils import fifo_deduct

from .models import (
    Customer,
    CustomerGroup,
    CustomerStatus,
    PaymentType,
    Sale,
    SaleItem,
    SaleReturn,
    SaleReturnItem,
    SaleReturnStatus,
    SaleStatus,
)
from .serializers import (
    CustomerCreateSerializer,
    CustomerDetailSerializer,
    CustomerGroupCreateSerializer,
    CustomerGroupListSerializer,
    CustomerListSerializer,
    CustomerUpdateSerializer,
    SaleCreateSerializer,
    SaleDetailSerializer,
    SaleListSerializer,
    SaleReturnCreateSerializer,
    SaleReturnDetailSerializer,
    SaleReturnListSerializer,
)


# ============================================================
# MIJOZ GURUHI VIEWSET
# ============================================================

class CustomerGroupViewSet(viewsets.ModelViewSet):
    """
    Mijoz guruhlari.

    Endpointlar:
      GET    /api/v1/customer-groups/       — ro'yxat
      POST   /api/v1/customer-groups/       — yaratish (manager+)
      GET    /api/v1/customer-groups/{id}/  — detail
      PATCH  /api/v1/customer-groups/{id}/  — yangilash (manager+)
      DELETE /api/v1/customer-groups/{id}/  — o'chirish (manager+)
                                              (bog'liq mijozlar group=NULL bo'ladi)

    Multi-tenant: faqat o'z do'konining guruhlari.
    """
    http_method_names = ['get', 'post', 'patch', 'delete']

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return [IsAuthenticated()]
        return [IsAuthenticated(), IsManagerOrAbove()]

    def get_serializer_class(self):
        if self.action in ('create', 'update', 'partial_update'):
            return CustomerGroupCreateSerializer
        return CustomerGroupListSerializer

    def get_queryset(self):
        worker = getattr(self.request.user, 'worker', None)
        if not worker or not worker.store:
            return CustomerGroup.objects.none()
        return CustomerGroup.objects.filter(store=worker.store)

    def perform_create(self, serializer):
        worker   = self.request.user.worker
        instance = serializer.save(store=worker.store)
        AuditLog.objects.create(
            actor=self.request.user,
            action=AuditLog.Action.CREATE,
            target_model='CustomerGroup',
            target_id=instance.id,
            description=f"Mijoz guruhi yaratildi: '{instance.name}'",
        )

    def perform_update(self, serializer):
        instance = serializer.save()
        AuditLog.objects.create(
            actor=self.request.user,
            action=AuditLog.Action.UPDATE,
            target_model='CustomerGroup',
            target_id=instance.id,
            description=f"Mijoz guruhi yangilandi: '{instance.name}'",
        )

    def perform_destroy(self, instance: CustomerGroup):
        name = instance.name
        pk   = instance.id
        AuditLog.objects.create(
            actor=self.request.user,
            action=AuditLog.Action.DELETE,
            target_model='CustomerGroup',
            target_id=pk,
            description=f"Mijoz guruhi o'chirildi: '{name}'",
        )
        instance.delete()   # hard delete, Customer.group → NULL (SET_NULL)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(
            {
                'message': 'Mijoz guruhi muvaffaqiyatli yaratildi.',
                'data': CustomerGroupListSerializer(serializer.instance).data,
            },
            status=status.HTTP_201_CREATED,
        )

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        if not serializer.validated_data:
            return Response(
                {'message': "Yangilash uchun kamida bitta maydon yuborilishi kerak."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        self.perform_update(serializer)
        return Response(
            {
                'message': 'Mijoz guruhi muvaffaqiyatli yangilandi.',
                'data': CustomerGroupListSerializer(serializer.instance).data,
            },
            status=status.HTTP_200_OK,
        )

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(
            {'message': "Mijoz guruhi o'chirildi."},
            status=status.HTTP_200_OK,
        )


# ============================================================
# MIJOZ VIEWSET
# ============================================================

class CustomerViewSet(viewsets.ModelViewSet):
    """
    Mijozlar.

    Endpointlar:
      GET    /api/v1/customers/       — ro'yxat (?status, ?group, ?search)
      POST   /api/v1/customers/       — yaratish
      GET    /api/v1/customers/{id}/  — detail
      PATCH  /api/v1/customers/{id}/  — yangilash
      DELETE /api/v1/customers/{id}/  — soft delete (status='inactive')

    URL filterlar:
      ?status=active|inactive
      ?group=<id>
      ?search=<ism|telefon>

    Multi-tenant: faqat o'z do'konining mijozlari.
    """
    http_method_names = ['get', 'post', 'patch', 'delete']

    def get_permissions(self):
        if self.action == 'destroy':
            return [IsAuthenticated(), IsManagerOrAbove()]
        return [IsAuthenticated(), CanAccess('sotuv')]

    def get_serializer_class(self):
        if self.action == 'list':
            return CustomerListSerializer
        if self.action == 'create':
            return CustomerCreateSerializer
        if self.action in ('update', 'partial_update'):
            return CustomerUpdateSerializer
        return CustomerDetailSerializer

    def get_queryset(self):
        worker = getattr(self.request.user, 'worker', None)
        if not worker or not worker.store:
            return Customer.objects.none()

        qs = (
            Customer.objects
            .filter(store=worker.store)
            .select_related('group')
            .prefetch_related('sales')
        )

        # ?status=active|inactive
        status_param = self.request.query_params.get('status')
        if status_param in (CustomerStatus.ACTIVE, CustomerStatus.INACTIVE):
            qs = qs.filter(status=status_param)

        # ?group=<id>
        group_param = self.request.query_params.get('group')
        if group_param:
            qs = qs.filter(group_id=group_param)

        # ?search=<text>
        search_param = self.request.query_params.get('search')
        if search_param:
            qs = qs.filter(
                Q(name__icontains=search_param) |
                Q(phone__icontains=search_param)
            )

        return qs

    def perform_create(self, serializer):
        worker = self.request.user.worker

        # Guruh validatsiya: shu do'konning guruhimi?
        group = serializer.validated_data.get('group')
        if group and group.store_id != worker.store_id:
            raise ValidationError({
                'group': "Bu guruh sizning do'koningizga tegishli emas."
            })

        instance = serializer.save(store=worker.store)
        AuditLog.objects.create(
            actor=self.request.user,
            action=AuditLog.Action.CREATE,
            target_model='Customer',
            target_id=instance.id,
            description=f"Mijoz yaratildi: '{instance.name}'",
        )

    def perform_update(self, serializer):
        worker = self.request.user.worker
        group  = serializer.validated_data.get('group')
        if group and group.store_id != worker.store_id:
            raise ValidationError({
                'group': "Bu guruh sizning do'koningizga tegishli emas."
            })
        instance = serializer.save()
        AuditLog.objects.create(
            actor=self.request.user,
            action=AuditLog.Action.UPDATE,
            target_model='Customer',
            target_id=instance.id,
            description=f"Mijoz yangilandi: '{instance.name}'",
        )

    def perform_destroy(self, instance: Customer):
        """Hard delete — mijozni bazadan o'chiradi."""
        AuditLog.objects.create(
            actor=self.request.user,
            action=AuditLog.Action.DELETE,
            target_model='Customer',
            target_id=instance.id,
            description=f"Mijoz o'chirildi: '{instance.name}'",
        )
        instance.delete()

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(
            {
                'message': 'Mijoz muvaffaqiyatli yaratildi.',
                'data': CustomerDetailSerializer(serializer.instance).data,
            },
            status=status.HTTP_201_CREATED,
        )

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        if not serializer.validated_data:
            return Response(
                {'message': "Yangilash uchun kamida bitta maydon yuborilishi kerak."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        self.perform_update(serializer)
        return Response(
            {
                'message': 'Mijoz muvaffaqiyatli yangilandi.',
                'data': CustomerDetailSerializer(serializer.instance).data,
            },
            status=status.HTTP_200_OK,
        )

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(
            {'message': "Mijoz muvaffaqiyatli o'chirildi."},
            status=status.HTTP_200_OK,
        )


# ============================================================
# SOTUV VIEWSET
# ============================================================

class SaleViewSet(viewsets.ModelViewSet):
    """
    Sotuvlar.

    Endpointlar:
      GET   /api/v1/sales/                — ro'yxat (?date, ?branch, ?payment_type, ?status)
      POST  /api/v1/sales/                — sotuv yaratish (atomic transaction)
      GET   /api/v1/sales/{id}/           — to'liq ma'lumot
      PATCH /api/v1/sales/{id}/cancel/    — bekor qilish (manager+)

    Ruxsatlar:
      list/retrieve/create → IsAuthenticated + CanAccess('sotuv')
      cancel              → IsAuthenticated + IsManagerOrAbove

    Multi-tenant: faqat o'z do'konining sotuvlari.
    """
    http_method_names = ['get', 'post', 'patch']

    def get_permissions(self):
        if self.action == 'cancel':
            return [IsAuthenticated(), IsManagerOrAbove()]
        return [IsAuthenticated(), CanAccess('sotuv')]

    def get_serializer_class(self):
        if self.action == 'list':
            return SaleListSerializer
        if self.action == 'create':
            return SaleCreateSerializer
        return SaleDetailSerializer

    def get_queryset(self):
        worker = getattr(self.request.user, 'worker', None)
        if not worker or not worker.store:
            return Sale.objects.none()

        qs = (
            Sale.objects
            .filter(store=worker.store)
            .select_related('branch', 'worker__user', 'customer', 'smena')
        )

        # ?date=YYYY-MM-DD
        date_param = self.request.query_params.get('date')
        if date_param:
            qs = qs.filter(created_on__date=date_param)

        # ?branch=<id>
        branch_param = self.request.query_params.get('branch')
        if branch_param:
            qs = qs.filter(branch_id=branch_param)

        # ?payment_type=cash|card|mixed|debt
        pt_param = self.request.query_params.get('payment_type')
        if pt_param:
            qs = qs.filter(payment_type=pt_param)

        # ?status=completed|cancelled
        status_param = self.request.query_params.get('status')
        if status_param:
            qs = qs.filter(status=status_param)

        # ?customer=<id>
        customer_param = self.request.query_params.get('customer')
        if customer_param:
            qs = qs.filter(customer_id=customer_param)

        return qs

    # ----------------------------------------------------------
    # CREATE — sotuv yaratish (@transaction.atomic)
    # ----------------------------------------------------------

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        """
        Yangi sotuv yaratish.

        Jarayon:
          1. Serializer validatsiya
          2. StoreSettings tekshirish (to'lov, chegirma, smena)
          3. Stock qoldig'i tekshirish (select_for_update)
          4. Sale + SaleItem yaratish
          5. StockMovement(OUT) + Stock yangilash
          6. Customer.debt_balance yangilash (agar nasiya bo'lsa)
          7. AuditLog
        """
        serializer = SaleCreateSerializer(
            data=request.data,
            context=self.get_serializer_context(),
        )
        serializer.is_valid(raise_exception=True)
        data     = serializer.validated_data
        worker   = request.user.worker
        settings = get_store_settings(worker.store_id)   # QOIDA 3

        branch          = data['branch']
        customer        = data.get('customer')
        payment_type    = data['payment_type']
        discount_amount = data.get('discount_amount', Decimal('0'))
        paid_amount     = data['paid_amount']
        items_data      = data['items']
        note            = data.get('note', '')

        # --------------------------------------------------
        # 1. Branch do'konga tegishliligini tekshirish
        # --------------------------------------------------
        if branch.store_id != worker.store_id:
            raise ValidationError({
                'branch': "Bu filial sizning do'koningizga tegishli emas."
            })

        # --------------------------------------------------
        # 2. Mijoz do'konga tegishliligini tekshirish
        # --------------------------------------------------
        if customer and customer.store_id != worker.store_id:
            raise ValidationError({
                'customer': "Bu mijoz sizning do'koningizga tegishli emas."
            })

        # --------------------------------------------------
        # 3. To'lov turi validatsiya (settings)
        # --------------------------------------------------
        if payment_type == PaymentType.CASH and not settings.allow_cash:
            raise ValidationError({
                'payment_type': "Naqd to'lov bu do'konda o'chirilgan."
            })
        if payment_type == PaymentType.CARD and not settings.allow_card:
            raise ValidationError({
                'payment_type': "Karta to'lov bu do'konda o'chirilgan."
            })
        if payment_type == PaymentType.DEBT and not settings.allow_debt:
            raise ValidationError({
                'payment_type': "Nasiya bu do'konda o'chirilgan."
            })

        # --------------------------------------------------
        # 4. Smena tekshirish (agar shift_enabled=True)
        # --------------------------------------------------
        current_smena = None
        if settings.shift_enabled:
            current_smena = (
                Smena.objects
                .filter(branch=branch, status=SmenaStatus.OPEN)
                .first()
            )
            if not current_smena:
                raise ValidationError({
                    'branch': (
                        "Bu filialda ochiq smena yo'q. "
                        "Avval smena oching."
                    )
                })

        # --------------------------------------------------
        # 5. Jami narxni hisoblash
        # --------------------------------------------------
        total_price = Decimal('0')
        items_prepared = []
        for item_data in items_data:
            product    = item_data['product']
            quantity   = item_data['quantity']
            unit_price = item_data.get('unit_price') or product.sale_price
            item_total = quantity * unit_price
            total_price += item_total
            items_prepared.append({
                'product':    product,
                'quantity':   quantity,
                'unit_price': unit_price,
                'total_price': item_total,
            })

        # --------------------------------------------------
        # 6. Chegirma validatsiya
        # --------------------------------------------------
        if discount_amount > total_price:
            raise ValidationError({
                'discount_amount': "Chegirma jami narxdan ko'p bo'lishi mumkin emas."
            })
        if not settings.allow_discount and discount_amount > 0:
            raise ValidationError({
                'discount_amount': "Chegirma bu do'konda o'chirilgan."
            })
        if settings.allow_discount and settings.max_discount_percent > 0:
            max_allowed = total_price * settings.max_discount_percent / 100
            if discount_amount > max_allowed:
                raise ValidationError({
                    'discount_amount': (
                        f"Maksimal chegirma {settings.max_discount_percent}% "
                        f"({max_allowed:.2f} so'm) dan oshmasligi kerak."
                    )
                })

        net_price = total_price - discount_amount

        # --------------------------------------------------
        # 7. To'lov summasi validatsiya
        # --------------------------------------------------
        if payment_type in (PaymentType.CASH, PaymentType.CARD):
            if paid_amount != net_price:
                raise ValidationError({
                    'paid_amount': (
                        f"To'lov summasi jami narxga teng bo'lishi shart: "
                        f"{net_price:.2f} so'm."
                    )
                })
            debt_amount = Decimal('0')
        elif payment_type == PaymentType.MIXED:
            if paid_amount > net_price:
                raise ValidationError({
                    'paid_amount': "To'lov summasi jami narxdan ko'p bo'lishi mumkin emas."
                })
            debt_amount = Decimal('0')
        else:  # DEBT
            if paid_amount > net_price:
                raise ValidationError({
                    'paid_amount': "To'lov summasi jami narxdan ko'p bo'lishi mumkin emas."
                })
            debt_amount = net_price - paid_amount

        # --------------------------------------------------
        # 8. Mahsulotlar do'konga tegishliligini tekshirish
        # --------------------------------------------------
        for item_data in items_prepared:
            product = item_data['product']
            if product.store_id != worker.store_id:
                raise ValidationError({
                    'items': (
                        f"'{product.name}' mahsuloti "
                        "sizning do'koningizga tegishli emas."
                    )
                })

        # --------------------------------------------------
        # 9. Stock qoldig'ini tekshirish (select_for_update)
        # --------------------------------------------------
        locked_stocks = {}
        for item_data in items_prepared:
            product  = item_data['product']
            quantity = item_data['quantity']
            key      = product.id

            if key not in locked_stocks:
                stock, _ = Stock.objects.select_for_update().get_or_create(
                    product=product,
                    branch=branch,
                    defaults={'quantity': Decimal('0')},
                )
                locked_stocks[key] = stock

            stock = locked_stocks[key]
            if stock.quantity < quantity:
                raise ValidationError({
                    'items': (
                        f"'{product.name}' mahsulotidan yetarli qoldiq yo'q. "
                        f"Mavjud: {stock.quantity}, "
                        f"so'ralgan: {quantity}."
                    )
                })

        # --------------------------------------------------
        # 10. Sale yaratish
        # --------------------------------------------------
        sale = Sale.objects.create(
            branch          = branch,
            store           = worker.store,
            worker          = worker,
            customer        = customer,
            smena           = current_smena,
            payment_type    = payment_type,
            total_price     = total_price,
            discount_amount = discount_amount,
            paid_amount     = paid_amount,
            debt_amount     = debt_amount,
            status          = SaleStatus.COMPLETED,
            note            = note,
        )

        # --------------------------------------------------
        # 11. SaleItem + StockMovement(OUT) + Stock yangilash
        # --------------------------------------------------
        for item_data in items_prepared:
            product    = item_data['product']
            quantity   = item_data['quantity']

            # ── FIFO: manbaa partiyalardan yechib olish ──────────────
            loc_kwargs = {'branch': branch, 'warehouse': None}
            deductions, total_cost = fifo_deduct(product, loc_kwargs, quantity)
            avg_cost = (
                total_cost / quantity
                if quantity > 0
                else Decimal('0')
            )

            sale_item = SaleItem.objects.create(
                sale        = sale,
                product     = product,
                quantity    = quantity,
                unit_price  = item_data['unit_price'],
                total_price = item_data['total_price'],
                unit_cost   = avg_cost,
            )

            # StockMovement(OUT) — FIFO narxi bilan
            StockMovement.objects.create(
                product       = product,
                branch        = branch,
                movement_type = MovementType.OUT,
                quantity      = quantity,
                unit_cost     = avg_cost,
                worker        = worker,
                note          = f"Sotuv #{sale.id}",
            )

            # Stock yangilash — F() bilan race condition yo'q
            Stock.objects.filter(
                product=product,
                branch=branch,
            ).update(
                quantity   = F('quantity') - quantity,
                updated_on = timezone.now(),
            )

        # --------------------------------------------------
        # 12. Customer.debt_balance yangilash
        # --------------------------------------------------
        if customer and debt_amount > 0:
            Customer.objects.filter(pk=customer.pk).update(
                debt_balance=F('debt_balance') + debt_amount,
            )

        # --------------------------------------------------
        # 13. AuditLog
        # --------------------------------------------------
        AuditLog.objects.create(
            actor=request.user,
            action=AuditLog.Action.CREATE,
            target_model='Sale',
            target_id=sale.id,
            description=(
                f"Sotuv amalga oshirildi: #{sale.id}, "
                f"filial='{branch.name}', "
                f"jami={total_price:.2f}, "
                f"to'lov={payment_type}"
            ),
        )

        # SaleItem va boshqa related ma'lumotlar uchun qayta yuklash
        sale.refresh_from_db()
        return Response(
            {
                'message': 'Sotuv muvaffaqiyatli amalga oshirildi.',
                'data': SaleDetailSerializer(
                    sale,
                    context=self.get_serializer_context(),
                ).data,
            },
            status=status.HTTP_201_CREATED,
        )

    # ----------------------------------------------------------
    # CANCEL action — sotuv bekor qilish (@transaction.atomic)
    # ----------------------------------------------------------

    @action(methods=['patch'], detail=True, url_path='cancel')
    @transaction.atomic
    def cancel(self, request, pk=None):
        """
        Savdoni bekor qilish. Faqat manager+ uchun ruxsat.

        PATCH /api/v1/sales/{id}/cancel/

        Jarayon:
          1. Faqat 'completed' savdo bekor qilinadi
          2. Har bir SaleItem uchun StockMovement(IN) + Stock qaytarish
          3. Customer.debt_balance kamaytirish (agar nasiya bo'lsa)
          4. sale.status = 'cancelled'
          5. AuditLog
        """
        sale   = self.get_object()
        worker = request.user.worker

        if sale.status == SaleStatus.CANCELLED:
            raise ValidationError({'detail': "Sotuv allaqachon bekor qilingan."})

        # --------------------------------------------------
        # Stock qaytarish — har bir element uchun
        # --------------------------------------------------
        for item in sale.items.select_related('product').all():
            product  = item.product
            quantity = item.quantity

            # Qaytarish StockMovement(IN)
            StockMovement.objects.create(
                product       = product,
                branch        = sale.branch,
                movement_type = MovementType.IN,
                quantity      = quantity,
                worker        = worker,
                note          = f"Sotuv #{sale.id} bekor qilindi",
            )

            # Stock yangilash
            Stock.objects.select_for_update().get_or_create(
                product=product,
                branch=sale.branch,
                defaults={'quantity': Decimal('0')},
            )
            Stock.objects.filter(
                product=product,
                branch=sale.branch,
            ).update(
                quantity   = F('quantity') + quantity,
                updated_on = timezone.now(),
            )

        # --------------------------------------------------
        # Customer.debt_balance qaytarish (agar nasiya bo'lsa)
        # --------------------------------------------------
        if sale.customer and sale.debt_amount > 0:
            Customer.objects.filter(pk=sale.customer_id).update(
                debt_balance=F('debt_balance') - sale.debt_amount,
            )

        # --------------------------------------------------
        # Bekor qilish
        # --------------------------------------------------
        sale.status = SaleStatus.CANCELLED
        sale.save(update_fields=['status'])

        AuditLog.objects.create(
            actor=request.user,
            action=AuditLog.Action.UPDATE,
            target_model='Sale',
            target_id=sale.id,
            description=(
                f"Sotuv bekor qilindi: #{sale.id}, "
                f"filial='{sale.branch.name}'"
            ),
        )

        sale.refresh_from_db()
        return Response(
            {
                'message': 'Sotuv bekor qilindi.',
                'data': SaleDetailSerializer(
                    sale,
                    context=self.get_serializer_context(),
                ).data,
            },
            status=status.HTTP_200_OK,
        )


# ============================================================
# QAYTARISH VIEWSET (BOSQICH 5)
# ============================================================

class SaleReturnViewSet(viewsets.ModelViewSet):
    """
    Sotuv qaytarishlarini boshqarish.

    Endpointlar:
      GET    /api/v1/sale-returns/              — ro'yxat
      POST   /api/v1/sale-returns/              — yangi qaytarish (pending)
      GET    /api/v1/sale-returns/{id}/         — to'liq ma'lumot
      PATCH  /api/v1/sale-returns/{id}/confirm/ — tasdiqlash (manager+)
      PATCH  /api/v1/sale-returns/{id}/cancel/  — bekor qilish (manager+)
      [PUT, DELETE YO'Q — qaytarishlar o'chirilmaydi]
    """
    http_method_names = ['get', 'post', 'patch']

    def get_permissions(self):
        if self.action in ('confirm', 'cancel', 'destroy'):
            return [IsAuthenticated(), IsManagerOrAbove()]
        return [IsAuthenticated(), CanAccess('sotuv')]

    def get_queryset(self):
        worker = self.request.user.worker
        qs = SaleReturn.objects.filter(
            store=worker.store,
        ).select_related(
            'branch', 'worker__user', 'customer', 'sale', 'smena',
        ).prefetch_related('items__product')

        status_filter = self.request.query_params.get('status')
        if status_filter:
            qs = qs.filter(status=status_filter)

        branch_filter = self.request.query_params.get('branch')
        if branch_filter:
            qs = qs.filter(branch_id=branch_filter)

        smena_filter = self.request.query_params.get('smena')
        if smena_filter:
            qs = qs.filter(smena_id=smena_filter)

        return qs

    def get_serializer_class(self):
        if self.action == 'list':
            return SaleReturnListSerializer
        if self.action == 'create':
            return SaleReturnCreateSerializer
        return SaleReturnDetailSerializer

    # ----------------------------------------------------------
    # CREATE — yangi qaytarish (pending)
    # ----------------------------------------------------------

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        """
        POST /api/v1/sale-returns/ — yangi qaytarish yaratish.
        Holat: pending. Tasdiqlash uchun /confirm/ kerak.
        """
        worker   = request.user.worker
        settings = get_store_settings(worker.store_id)

        # StoreSettings: qaytarish yoqilganligini tekshirish
        if not settings.sale_return_enabled:
            raise ValidationError({
                'detail': "Qaytarish funksiyasi bu do'konda o'chirib qo'yilgan."
            })

        serializer = SaleReturnCreateSerializer(
            data=request.data,
            context={'request': request},
        )
        serializer.is_valid(raise_exception=True)
        data     = serializer.validated_data
        items    = data.pop('items')
        branch   = data['branch']
        customer = data.get('customer')
        sale_obj = data.get('sale')
        reason   = data.get('reason', '')

        # Ochiq smena (ixtiyoriy)
        current_smena = None
        if settings.shift_enabled:
            current_smena = Smena.objects.filter(
                branch=branch,
                status=SmenaStatus.OPEN,
            ).first()

        # Jami hisoblash
        total_amount = sum(
            item['quantity'] * item['unit_price']
            for item in items
        )

        # SaleReturn yaratish
        sale_return = SaleReturn.objects.create(
            sale         = sale_obj,
            branch       = branch,
            store        = worker.store,
            worker       = worker,
            customer     = customer,
            smena        = current_smena,
            reason       = reason,
            total_amount = total_amount,
            status       = SaleReturnStatus.PENDING,
        )

        # SaleReturnItem larni yaratish
        for item_data in items:
            product    = item_data['product']
            quantity   = item_data['quantity']
            unit_price = item_data['unit_price']
            SaleReturnItem.objects.create(
                sale_return = sale_return,
                product     = product,
                quantity    = quantity,
                unit_price  = unit_price,
                total_price = quantity * unit_price,
            )

        AuditLog.objects.create(
            actor=request.user,
            action=AuditLog.Action.CREATE,
            target_model='SaleReturn',
            target_id=sale_return.id,
            description=(
                f"Qaytarish yaratildi: #{sale_return.id}, "
                f"filial='{branch.name}', jami={total_amount}"
            ),
        )

        sale_return.refresh_from_db()
        return Response(
            {
                'message': 'Qaytarish muvaffaqiyatli yaratildi. Tasdiqlash kutilmoqda.',
                'data': SaleReturnDetailSerializer(
                    sale_return,
                    context=self.get_serializer_context(),
                ).data,
            },
            status=status.HTTP_201_CREATED,
        )

    # ----------------------------------------------------------
    # CONFIRM — tasdiqlash (@transaction.atomic)
    # ----------------------------------------------------------

    @action(methods=['patch'], detail=True, url_path='confirm')
    @transaction.atomic
    def confirm(self, request, pk=None):
        """
        PATCH /api/v1/sale-returns/{id}/confirm/
        Faqat manager+ tasdiqlaydi.

        Jarayon:
          1. Faqat 'pending' qaytarish tasdiqlanadi
          2. Har bir element uchun StockMovement(IN) + Stock yangilash
          3. SaleReturn.status = 'confirmed'
          4. AuditLog
        """
        sale_return = self.get_object()
        worker      = request.user.worker

        if sale_return.status != SaleReturnStatus.PENDING:
            raise ValidationError({
                'detail': (
                    "Faqat kutilayotgan qaytarishni tasdiqlash mumkin. "
                    f"Hozirgi holat: {sale_return.get_status_display()}."
                )
            })

        branch = sale_return.branch

        for item in sale_return.items.select_related('product').all():
            product  = item.product
            quantity = item.quantity

            # StockMovement(IN) — mahsulot omborga qaytdi
            StockMovement.objects.create(
                product       = product,
                branch        = branch,
                movement_type = MovementType.IN,
                quantity      = quantity,
                unit_cost     = item.unit_price,
                worker        = worker,
                note          = f"Qaytarish #{sale_return.id} tasdiqlandi",
            )

            # Stock yangilash
            Stock.objects.select_for_update().get_or_create(
                product=product,
                branch=branch,
                defaults={'quantity': Decimal('0')},
            )
            Stock.objects.filter(
                product=product,
                branch=branch,
            ).update(
                quantity   = F('quantity') + quantity,
                updated_on = timezone.now(),
            )

        sale_return.status = SaleReturnStatus.CONFIRMED
        sale_return.save(update_fields=['status'])

        AuditLog.objects.create(
            actor=request.user,
            action=AuditLog.Action.UPDATE,
            target_model='SaleReturn',
            target_id=sale_return.id,
            description=(
                f"Qaytarish tasdiqlandi: #{sale_return.id}, "
                f"filial='{branch.name}'"
            ),
        )

        sale_return.refresh_from_db()
        return Response(
            {
                'message': 'Qaytarish tasdiqlandi.',
                'data': SaleReturnDetailSerializer(
                    sale_return,
                    context=self.get_serializer_context(),
                ).data,
            },
            status=status.HTTP_200_OK,
        )

    # ----------------------------------------------------------
    # CANCEL — bekor qilish
    # ----------------------------------------------------------

    @action(methods=['patch'], detail=True, url_path='cancel')
    @transaction.atomic
    def cancel(self, request, pk=None):
        """
        PATCH /api/v1/sale-returns/{id}/cancel/
        Faqat manager+ bekor qiladi.
        Faqat 'pending' qaytarish bekor qilinadi.
        """
        sale_return = self.get_object()

        if sale_return.status != SaleReturnStatus.PENDING:
            raise ValidationError({
                'detail': (
                    "Faqat kutilayotgan qaytarishni bekor qilish mumkin. "
                    f"Hozirgi holat: {sale_return.get_status_display()}."
                )
            })

        sale_return.status = SaleReturnStatus.CANCELLED
        sale_return.save(update_fields=['status'])

        AuditLog.objects.create(
            actor=request.user,
            action=AuditLog.Action.UPDATE,
            target_model='SaleReturn',
            target_id=sale_return.id,
            description=f"Qaytarish bekor qilindi: #{sale_return.id}",
        )

        sale_return.refresh_from_db()
        return Response(
            {
                'message': 'Qaytarish bekor qilindi.',
                'data': SaleReturnDetailSerializer(
                    sale_return,
                    context=self.get_serializer_context(),
                ).data,
            },
            status=status.HTTP_200_OK,
        )
