from datetime import date, timedelta
from decimal import Decimal

from django.db.models import Count, Q, Sum
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from store.models import Store
from subscription.models import Subscription, SubscriptionPlan
from trade.models import Sale

from .models import AdminExpense, Coupon, CouponUsage, Referral, StoreReferralCode, SupportTicket, TicketReply
from .permissions import IsSuperAdmin
from .serializers import (
    AdminExpenseSerializer,
    AdminPlanSerializer,
    AdminSubscriptionDetailSerializer,
    AdminSubscriptionListSerializer,
    AdminWorkerListSerializer,
    ApplyCouponSerializer,
    ChangePlanSerializer,
    CouponCreateSerializer,
    CouponDetailSerializer,
    CouponListSerializer,
    CouponUsageSerializer,
    ExtendSubscriptionSerializer,
    GiveTrialSerializer,
    ReferralListSerializer,
    ReferralStatsSerializer,
    StoreDetailSerializer,
    StoreListSerializer,
    StoreReferralCodeSerializer,
    SupportTicketCreateSerializer,
    SupportTicketDetailSerializer,
    SupportTicketListSerializer,
    TicketReplyCreateSerializer,
    TicketStatusUpdateSerializer,
)


# ============================================================
# DASHBOARD
# ============================================================

class SuperAdminDashboardView(APIView):
    permission_classes = [IsSuperAdmin]

    def get(self, request):
        today = date.today()

        # Do'konlar statistikasi
        stores_total   = Store.objects.count()
        stores_active  = Store.objects.filter(status='active').count()
        stores_blocked = Store.objects.filter(status='inactive').count()
        new_today      = Store.objects.filter(created_on__date=today).count()

        # Obunalar holati
        subs = Subscription.objects.select_related('plan', 'store')
        trial_count   = subs.filter(status='trial').count()
        active_count  = subs.filter(status='active').count()
        expired_count = subs.filter(status='expired').count()

        # Trial muddati 7 kun va kamroq qolganlar
        expiring_soon = subs.filter(
            status__in=['trial', 'active'],
            end_date__lte=today + timedelta(days=7),
            end_date__gte=today,
        ).count()

        # MRR — faqat active obunalar
        mrr = Decimal('0')
        for sub in subs.filter(status='active'):
            if sub.is_yearly:
                mrr += sub.plan.price_yearly / 12
            else:
                mrr += sub.plan.price_monthly

        arr = mrr * 12

        # Shu oy admin xarajatlari
        month_start = today.replace(day=1)
        expenses_this_month = AdminExpense.objects.filter(
            date__gte=month_start
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

        net_profit = mrr - expenses_this_month

        return Response({
            'stores': {
                'total':         stores_total,
                'active':        stores_active,
                'blocked':       stores_blocked,
                'new_today':     new_today,
                'expiring_soon': expiring_soon,
            },
            'subscriptions': {
                'trial':   trial_count,
                'active':  active_count,
                'expired': expired_count,
            },
            'financials': {
                'mrr':                 float(mrr),
                'arr':                 float(arr),
                'expenses_this_month': float(expenses_this_month),
                'net_profit':          float(net_profit),
            },
        })


# ============================================================
# DO'KONLAR BOSHQARUVI
# ============================================================

class SuperAdminStoreViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsSuperAdmin]
    queryset = Store.objects.select_related('subscription__plan').order_by('-created_on')

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return StoreDetailSerializer
        return StoreListSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        status_filter = self.request.query_params.get('status')
        search        = self.request.query_params.get('search')
        plan_filter   = self.request.query_params.get('plan')

        if status_filter:
            qs = qs.filter(status=status_filter)
        if search:
            qs = qs.filter(Q(name__icontains=search) | Q(phone__icontains=search))
        if plan_filter:
            qs = qs.filter(subscription__plan__plan_type=plan_filter)
        return qs

    @action(detail=True, methods=['post'])
    def block(self, request, pk=None):
        store = self.get_object()
        if store.status == 'inactive':
            return Response({'detail': "Do'kon allaqachon bloklangan."}, status=400)
        store.status = 'inactive'
        store.save()
        return Response({'detail': f"'{store.name}' do'koni bloklandi."})

    @action(detail=True, methods=['post'])
    def unblock(self, request, pk=None):
        store = self.get_object()
        if store.status == 'active':
            return Response({'detail': "Do'kon allaqachon faol."}, status=400)
        store.status = 'active'
        store.save()
        return Response({'detail': f"'{store.name}' do'koni blokdan chiqarildi."})

    @action(detail=True, methods=['post'])
    def impersonate(self, request, pk=None):
        """Do'konning owner/manager xodimi nomidan JWT token yaratish."""
        store = self.get_object()
        owner_worker = store.workers.filter(
            role='owner', status='active'
        ).select_related('user').first()

        if not owner_worker:
            owner_worker = store.workers.filter(
                role='manager', status='active'
            ).select_related('user').first()

        if not owner_worker:
            return Response(
                {'detail': "Do'konda faol owner yoki manager topilmadi."},
                status=status.HTTP_404_NOT_FOUND
            )

        user = owner_worker.user
        refresh = RefreshToken.for_user(user)

        return Response({
            'store_id':    store.id,
            'store_name':  store.name,
            'worker_id':   owner_worker.id,
            'worker_role': owner_worker.role,
            'access':      str(refresh.access_token),
            'refresh':     str(refresh),
            'warning':     'Bu token superadmin impersonation uchun.',
        })


# ============================================================
# OBUNALAR BOSHQARUVI
# ============================================================

class SuperAdminSubscriptionViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsSuperAdmin]
    queryset = Subscription.objects.select_related('store', 'plan').order_by('-created_on')

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return AdminSubscriptionDetailSerializer
        return AdminSubscriptionListSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        status_filter = self.request.query_params.get('status')
        plan_filter   = self.request.query_params.get('plan')
        search        = self.request.query_params.get('search')
        if status_filter:
            qs = qs.filter(status=status_filter)
        if plan_filter:
            qs = qs.filter(plan__plan_type=plan_filter)
        if search:
            qs = qs.filter(store__name__icontains=search)
        return qs

    @action(detail=True, methods=['post'])
    def extend(self, request, pk=None):
        """Obuna muddatini uzaytirish."""
        subscription = self.get_object()
        serializer = ExtendSubscriptionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        days    = serializer.validated_data['days']
        note    = serializer.validated_data.get('note', '')
        old_end = subscription.end_date
        new_end = max(old_end, date.today()) + timedelta(days=days)

        subscription.end_date = new_end
        if subscription.status == 'expired':
            subscription.status = 'active'
            subscription.reset_notification_flags()
        subscription.save()

        return Response({
            'detail':  f"Obuna {days} kunga uzaytirildi.",
            'old_end': old_end.isoformat(),
            'new_end': new_end.isoformat(),
            'note':    note,
        })

    @action(detail=True, methods=['post'], url_path='change-plan')
    def change_plan(self, request, pk=None):
        """Tarif rejasini o'zgartirish."""
        subscription = self.get_object()
        serializer = ChangePlanSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        new_plan = SubscriptionPlan.objects.get(id=serializer.validated_data['plan_id'])
        old_plan = subscription.plan
        subscription.plan = new_plan
        subscription.save()

        return Response({
            'detail':   f"Tarif '{old_plan.name}' dan '{new_plan.name}' ga o'zgartirildi.",
            'store':    subscription.store.name,
            'new_plan': new_plan.name,
        })

    @action(detail=True, methods=['post'], url_path='give-trial')
    def give_trial(self, request, pk=None):
        """Qo'shimcha trial kunlar berish."""
        subscription = self.get_object()
        serializer = GiveTrialSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        days    = serializer.validated_data['days']
        note    = serializer.validated_data.get('note', '')
        old_end = subscription.end_date
        new_end = max(old_end, date.today()) + timedelta(days=days)

        subscription.end_date = new_end
        subscription.status   = 'trial'
        subscription.reset_notification_flags()
        subscription.save()

        return Response({
            'detail':  f"{days} kunlik trial berildi.",
            'old_end': old_end.isoformat(),
            'new_end': new_end.isoformat(),
            'note':    note,
        })


# ============================================================
# KUPONLAR
# ============================================================

class SuperAdminCouponViewSet(viewsets.ModelViewSet):
    permission_classes = [IsSuperAdmin]
    queryset = Coupon.objects.all().order_by('-created_on')

    def get_serializer_class(self):
        if self.action == 'list':
            return CouponListSerializer
        if self.action in ('create', 'update', 'partial_update'):
            return CouponCreateSerializer
        return CouponDetailSerializer

    @action(detail=True, methods=['get'])
    def usages(self, request, pk=None):
        coupon = self.get_object()
        usages = coupon.usages.select_related('store').order_by('-applied_at')
        serializer = CouponUsageSerializer(usages, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def deactivate(self, request, pk=None):
        coupon = self.get_object()
        coupon.is_active = False
        coupon.save()
        return Response({'detail': f"'{coupon.code}' kuponi o'chirildi."})

    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        coupon = self.get_object()
        coupon.is_active = True
        coupon.save()
        return Response({'detail': f"'{coupon.code}' kuponi yoqildi."})


class ApplyCouponView(APIView):
    """Do'kon egasi kupon qo'llaydi. POST /api/v1/subscriptions/apply-coupon/"""

    def post(self, request):
        serializer = ApplyCouponSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        code = serializer.validated_data['code'].upper().strip()
        try:
            coupon = Coupon.objects.get(code=code)
        except Coupon.DoesNotExist:
            return Response({'detail': "Kupon topilmadi."}, status=404)

        from accaunt.models import Worker
        worker = Worker.objects.filter(user=request.user, status='active').first()
        if not worker or not worker.store:
            return Response({'detail': "Do'kon topilmadi."}, status=404)

        store = worker.store
        can_use, reason = coupon.can_be_used_by(store)
        if not can_use:
            return Response({'detail': reason}, status=400)

        subscription = getattr(store, 'subscription', None)
        if not subscription:
            return Response({'detail': "Do'konning obunasi topilmadi."}, status=404)

        discount_value = Decimal('0')
        today = date.today()

        if coupon.type == 'free_days':
            days = int(coupon.value)
            old_end = subscription.end_date
            subscription.end_date = max(old_end, today) + timedelta(days=days)
            if subscription.status == 'expired':
                subscription.status = 'trial'
                subscription.reset_notification_flags()
            subscription.save()
            discount_value = coupon.value

        elif coupon.type == 'percent_off':
            plan_price = subscription.plan.price_monthly
            discount_value = plan_price * coupon.value / 100

        elif coupon.type == 'amount_off':
            discount_value = coupon.value

        CouponUsage.objects.create(coupon=coupon, store=store, discount_value=discount_value)
        Coupon.objects.filter(pk=coupon.pk).update(used_count=coupon.used_count + 1)

        return Response({
            'detail':         f"'{coupon.code}' kuponi muvaffaqiyatli qo'llandi.",
            'type':           coupon.type,
            'discount_value': float(discount_value),
            'new_end_date':   subscription.end_date.isoformat() if coupon.type == 'free_days' else None,
        })


# ============================================================
# MOLIYAVIY HISOBOT
# ============================================================

class SuperAdminFinancialView(APIView):
    permission_classes = [IsSuperAdmin]

    def get(self, request):
        today       = date.today()
        month_start = today.replace(day=1)
        subs        = Subscription.objects.select_related('plan')

        # Tariflar bo'yicha daromad
        plans_revenue = []
        total_mrr = Decimal('0')
        for plan in SubscriptionPlan.objects.all():
            count   = plan.subscriptions.filter(status='active').count()
            revenue = Decimal(str(plan.price_monthly)) * count
            total_mrr += revenue
            plans_revenue.append({
                'plan_name':       plan.name,
                'plan_type':       plan.plan_type,
                'price_monthly':   float(plan.price_monthly),
                'active_count':    count,
                'monthly_revenue': float(revenue),
            })

        trial_count   = subs.filter(status='trial').count()
        coupon_stores = CouponUsage.objects.values('store').distinct().count()

        coupon_loss = CouponUsage.objects.filter(
            applied_at__date__gte=month_start
        ).aggregate(total=Sum('discount_value'))['total'] or Decimal('0')

        expenses_this_month = AdminExpense.objects.filter(
            date__gte=month_start
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

        expenses_by_category = list(
            AdminExpense.objects.filter(date__gte=month_start)
            .values('category')
            .annotate(total=Sum('amount'))
            .order_by('-total')
        )

        arr        = total_mrr * 12
        net_profit = total_mrr - expenses_this_month

        return Response({
            'period': {
                'month': today.strftime('%Y-%m'),
                'today': today.isoformat(),
            },
            'revenue': {
                'mrr':               float(total_mrr),
                'arr':               float(arr),
                'by_plan':           plans_revenue,
                'trial_stores':      trial_count,
                'coupon_stores':     coupon_stores,
                'coupon_loss_month': float(coupon_loss),
            },
            'expenses': {
                'this_month':  float(expenses_this_month),
                'by_category': expenses_by_category,
            },
            'net_profit': float(net_profit),
        })


class SuperAdminFinancialExportView(APIView):
    permission_classes = [IsSuperAdmin]

    def get(self, request):
        import io
        import openpyxl
        from django.http import HttpResponse

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Moliyaviy hisobot"

        today       = date.today()
        month_start = today.replace(day=1)

        ws.append(['MOLIYAVIY HISOBOT', today.strftime('%B %Y')])
        ws.append([])

        ws.append(['DAROMAD'])
        ws.append(["Tarif", "Faol do'konlar", "Oylik daromad (UZS)"])
        for plan in SubscriptionPlan.objects.all():
            count   = plan.subscriptions.filter(status='active').count()
            revenue = float(plan.price_monthly) * count
            ws.append([plan.name, count, revenue])
        ws.append([])

        ws.append(['XARAJATLAR'])
        ws.append(['Nomi', 'Kategoriya', 'Summa (UZS)', 'Sana'])
        for exp in AdminExpense.objects.filter(date__gte=month_start).order_by('-date'):
            ws.append([exp.title, exp.get_category_display(), float(exp.amount), exp.date.isoformat()])

        buffer = io.BytesIO()
        wb.save(buffer)
        buffer.seek(0)
        filename = f"financial_{today.strftime('%Y_%m')}.xlsx"
        response = HttpResponse(
            buffer.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response


# ============================================================
# ADMIN XARAJATLARI
# ============================================================

class AdminExpenseViewSet(viewsets.ModelViewSet):
    permission_classes = [IsSuperAdmin]
    serializer_class   = AdminExpenseSerializer
    queryset           = AdminExpense.objects.order_by('-date')

    def get_queryset(self):
        qs    = super().get_queryset()
        month = self.request.query_params.get('month')
        year  = self.request.query_params.get('year')
        if month:
            qs = qs.filter(date__month=month)
        if year:
            qs = qs.filter(date__year=year)
        return qs


# ============================================================
# TARIF REJALARI (superadmin boshqaruvi)
# ============================================================

class SuperAdminPlanViewSet(viewsets.ModelViewSet):
    permission_classes = [IsSuperAdmin]
    serializer_class   = AdminPlanSerializer
    queryset           = SubscriptionPlan.objects.order_by('price_monthly')


# ============================================================
# SUPPORT TICKETS — DO'KON EGASI
# ============================================================

class StoreTicketViewSet(viewsets.ModelViewSet):
    """Do'kon egasi o'z ticketlarini ko'radi va yaratadi."""

    def get_permissions(self):
        from rest_framework.permissions import IsAuthenticated
        return [IsAuthenticated()]

    def get_serializer_class(self):
        if self.action == 'create':
            return SupportTicketCreateSerializer
        if self.action == 'retrieve':
            return SupportTicketDetailSerializer
        return SupportTicketListSerializer

    def get_queryset(self):
        from accaunt.models import Worker
        worker = Worker.objects.filter(user=self.request.user, status='active').first()
        if not worker or not worker.store:
            return SupportTicket.objects.none()
        return SupportTicket.objects.filter(store=worker.store).order_by('-created_on')

    def perform_create(self, serializer):
        from accaunt.models import Worker
        worker = Worker.objects.filter(user=self.request.user, status='active').first()
        serializer.save(store=worker.store)

    @action(detail=True, methods=['post'])
    def reply(self, request, pk=None):
        ticket = self.get_object()
        serializer = TicketReplyCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        TicketReply.objects.create(
            ticket=ticket,
            author=request.user,
            message=serializer.validated_data['message'],
            is_admin=False,
        )
        ticket.status = 'in_progress'
        ticket.save()
        return Response({'detail': "Javob yuborildi."})


# ============================================================
# SUPPORT TICKETS — SUPERADMIN
# ============================================================

class SuperAdminTicketViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsSuperAdmin]
    queryset = SupportTicket.objects.select_related('store').order_by('-created_on')

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return SupportTicketDetailSerializer
        return SupportTicketListSerializer

    def get_queryset(self):
        qs       = super().get_queryset()
        st       = self.request.query_params.get('status')
        priority = self.request.query_params.get('priority')
        search   = self.request.query_params.get('search')
        if st:
            qs = qs.filter(status=st)
        if priority:
            qs = qs.filter(priority=priority)
        if search:
            qs = qs.filter(
                Q(title__icontains=search) | Q(store__name__icontains=search)
            )
        return qs

    @action(detail=False, methods=['get'])
    def stats(self, request):
        from django.db.models import Avg, F, ExpressionWrapper, DurationField
        qs = SupportTicket.objects.all()
        resolved = qs.filter(status='resolved', resolved_at__isnull=False)
        avg_hours = None
        if resolved.exists():
            avg_delta = resolved.annotate(
                duration=ExpressionWrapper(
                    F('resolved_at') - F('created_on'),
                    output_field=DurationField()
                )
            ).aggregate(avg=Avg('duration'))['avg']
            if avg_delta:
                avg_hours = round(avg_delta.total_seconds() / 3600, 1)

        return Response({
            'total':       qs.count(),
            'open':        qs.filter(status='open').count(),
            'in_progress': qs.filter(status='in_progress').count(),
            'resolved':    qs.filter(status='resolved').count(),
            'closed':      qs.filter(status='closed').count(),
            'urgent':      qs.filter(priority='urgent').count(),
            'avg_resolve_hours': avg_hours,
        })

    @action(detail=True, methods=['post'])
    def reply(self, request, pk=None):
        ticket = self.get_object()
        serializer = TicketReplyCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        TicketReply.objects.create(
            ticket=ticket,
            author=request.user,
            message=serializer.validated_data['message'],
            is_admin=True,
        )
        if ticket.status == 'open':
            ticket.status = 'in_progress'
            ticket.save()
        return Response({'detail': "Javob yuborildi."})

    @action(detail=True, methods=['patch'], url_path='set-status')
    def set_status(self, request, pk=None):
        ticket = self.get_object()
        serializer = TicketStatusUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        new_status = serializer.validated_data['status']
        ticket.status = new_status
        if new_status == 'resolved':
            ticket.resolved_at = timezone.now()
        ticket.save()
        return Response({'detail': f"Status '{new_status}' ga o'zgartirildi."})


# ============================================================
# REFERRAL — DO'KON EGASI
# ============================================================

class StoreReferralView(APIView):
    """Do'kon egasi o'z referral kodini ko'radi."""

    def get_permissions(self):
        from rest_framework.permissions import IsAuthenticated
        return [IsAuthenticated()]

    def _get_store(self, request):
        from accaunt.models import Worker
        worker = Worker.objects.filter(user=request.user, status='active').first()
        return worker.store if worker else None

    def get(self, request):
        store = self._get_store(request)
        if not store:
            return Response({'detail': "Do'kon topilmadi."}, status=404)
        ref_obj = StoreReferralCode.get_or_create_for_store(store)
        serializer = StoreReferralCodeSerializer(ref_obj)
        return Response(serializer.data)


class StoreMyReferralsView(APIView):
    """Do'kon egasi o'zi taklif qilganlarni ko'radi."""

    def get_permissions(self):
        from rest_framework.permissions import IsAuthenticated
        return [IsAuthenticated()]

    def get(self, request):
        from accaunt.models import Worker
        worker = Worker.objects.filter(user=request.user, status='active').first()
        if not worker or not worker.store:
            return Response({'detail': "Do'kon topilmadi."}, status=404)
        referrals = Referral.objects.filter(
            referrer_store=worker.store
        ).select_related('referred_store').order_by('-created_on')
        serializer = ReferralListSerializer(referrals, many=True)
        return Response({
            'referrals': serializer.data,
            'total':     referrals.count(),
            'rewarded':  referrals.filter(status='rewarded').count(),
        })


# ============================================================
# REFERRAL — SUPERADMIN
# ============================================================

class SuperAdminReferralView(APIView):
    permission_classes = [IsSuperAdmin]

    def get(self, request):
        referrals = Referral.objects.select_related(
            'referrer_store', 'referred_store'
        ).order_by('-created_on')
        st = request.query_params.get('status')
        if st:
            referrals = referrals.filter(status=st)
        serializer = ReferralListSerializer(referrals, many=True)
        return Response(serializer.data)


class SuperAdminReferralStatsView(APIView):
    permission_classes = [IsSuperAdmin]

    def get(self, request):
        qs = Referral.objects.all()
        total_bonus = qs.filter(status='rewarded').aggregate(
            total=Sum('reward_days')
        )['total'] or 0
        return Response({
            'total_referrals':  qs.count(),
            'confirmed':        qs.filter(status='confirmed').count(),
            'rewarded':         qs.filter(status='rewarded').count(),
            'pending':          qs.filter(status='pending').count(),
            'total_bonus_days': total_bonus,
        })


# ============================================================
# WORKERS — SUPERADMIN
# ============================================================

class SuperAdminWorkerViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsSuperAdmin]
    serializer_class   = AdminWorkerListSerializer

    def get_queryset(self):
        from accaunt.models import Worker
        qs     = Worker.objects.select_related('user', 'store').order_by('-user__date_joined')
        store  = self.request.query_params.get('store')
        role   = self.request.query_params.get('role')
        search = self.request.query_params.get('search')
        if store:
            qs = qs.filter(store_id=store)
        if role:
            qs = qs.filter(role=role)
        if search:
            qs = qs.filter(
                Q(user__first_name__icontains=search) |
                Q(user__last_name__icontains=search) |
                Q(user__email__icontains=search)
            )
        return qs

    @action(detail=True, methods=['post'])
    def block(self, request, pk=None):
        worker = self.get_object()
        worker.status = 'inactive'
        worker.save()
        return Response({'detail': f"Xodim bloklandi: {worker.user.get_full_name() or worker.user.email}"})

    @action(detail=True, methods=['post'])
    def unblock(self, request, pk=None):
        worker = self.get_object()
        worker.status = 'active'
        worker.save()
        return Response({'detail': f"Xodim blokdan chiqarildi: {worker.user.get_full_name() or worker.user.email}"})

    @action(detail=True, methods=['post'], url_path='reset-password')
    def reset_password(self, request, pk=None):
        import secrets
        worker   = self.get_object()
        new_pass = secrets.token_urlsafe(10)
        worker.user.set_password(new_pass)
        worker.user.save()
        return Response({
            'detail':       "Parol yangilandi.",
            'new_password': new_pass,
            'warning':      "Bu parolni foydalanuvchiga xavfsiz yo'l bilan yetkazing.",
        })
