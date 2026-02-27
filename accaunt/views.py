"""
============================================================
ACCAUNT APP — View'lar
============================================================
View'lar ikki guruhga bo'lingan:

1. AUTH view'lari (autentifikatsiya):
   - UserRegistrationView   — ro'yxatdan o'tish
   - UserLoginView          — tizimga kirish (JWT token qaytaradi)
   - LogoutAPIView          — tizimdan chiqish (token blacklist)
   - UserChangePasswordView — parol o'zgartirish
   - ProfileView            — o'z profilini ko'rish va yangilash

2. WORKER view'lari (hodimlarni boshqarish):
   - WorkerViewSet          — CRUD (list, create, retrieve, partial_update)
"""

from django.db.models import Case, IntegerField, Value, When

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework import status, viewsets, mixins
from rest_framework.filters import SearchFilter
from rest_framework_simplejwt.tokens import RefreshToken
from django_filters.rest_framework import DjangoFilterBackend

from .models import CustomUser, Worker, AuditLog, WorkerStatus
from .permissions import IsManagerOrAbove, IsOwner
from .serializers import (
    UserRegistrationSerializer,
    UserLoginSerializer,
    LogoutSerializer,
    UserChangePasswordSerializer,
    SendPasswordResetEmailSerializer,
    UserPasswordResetSerializer,
    CustomUserProfileSerializer,
    ProfileUpdateSerializer,
    WorkerListSerializer,
    WorkerDetailSerializer,
    WorkerCreateSerializer,
    WorkerUpdateSerializer,
)


# ============================================================
# YORDAMCHI FUNKSIYA
# ============================================================

def _generate_tokens(user: CustomUser) -> dict:
    """
    Foydalanuvchi uchun JWT access va refresh tokenlarini generatsiya qiladi.

    Returns:
        {'access': '...', 'refresh': '...'}
    """
    refresh = RefreshToken.for_user(user)
    return {
        'refresh': str(refresh),
        'access':  str(refresh.access_token),
    }


# ============================================================
# AUTH VIEW'LARI
# ============================================================

class UserRegistrationView(APIView):
    """
    Yangi foydalanuvchi ro'yxatdan o'tkazish.
    POST /api/v1/auth/register/

    Ruxsat: hamma (AllowAny)
    Javob: JWT tokenlar + muvaffaqiyat xabari
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = UserRegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        return Response(
            {
                'message': "Ro'yxatdan muvaffaqiyatli o'tdingiz!",
                'tokens': _generate_tokens(user),
            },
            status=status.HTTP_201_CREATED
        )


class UserLoginView(APIView):
    """
    Tizimga kirish.
    POST /api/v1/auth/login/

    Ruxsat: hamma (AllowAny)
    Javob: JWT tokenlar + foydalanuvchi profili (permission'lar bilan)
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = UserLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data['user']
        user_data = CustomUserProfileSerializer(user).data

        # AuditLog: tizimga kirish qayd etiladi
        AuditLog.objects.create(
            actor=user,
            action=AuditLog.Action.LOGIN,
            description=f"{user} tizimga kirdi.",
        )

        return Response(
            {
                **_generate_tokens(user),
                'user': user_data,
            },
            status=status.HTTP_200_OK
        )


class LogoutAPIView(APIView):
    """
    Tizimdan chiqish — refresh token blacklist ga qo'shiladi.
    POST /api/v1/auth/logout/

    Ruxsat: autentifikatsiya qilingan foydalanuvchi
    So'rov tanasi: {"refresh": "<refresh_token>"}
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        # AuditLog: tizimdan chiqish qayd etiladi
        AuditLog.objects.create(
            actor=request.user,
            action=AuditLog.Action.LOGOUT,
            description=f"{request.user} tizimdan chiqdi.",
        )

        return Response(
            {'message': "Tizimdan muvaffaqiyatli chiqdingiz!"},
            status=status.HTTP_200_OK
        )


class UserChangePasswordView(APIView):
    """
    Parolni o'zgartirish.
    POST /api/v1/auth/change-password/

    Ruxsat: autentifikatsiya qilingan foydalanuvchi
    So'rov tanasi: {current_password, password, password2}
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = UserChangePasswordSerializer(
            data=request.data,
            context={'user': request.user}
        )
        serializer.is_valid(raise_exception=True)
        return Response(
            {'message': "Parol muvaffaqiyatli o'zgartirildi!"},
            status=status.HTTP_200_OK
        )


class ProfileView(mixins.RetrieveModelMixin, mixins.UpdateModelMixin, viewsets.GenericViewSet):
    """
    O'z profilini ko'rish va yangilash.

    GET   /api/v1/auth/profil/ — profilni ko'rish
    PATCH /api/v1/auth/profil/ — ism, familiya, telefon raqamlarini yangilash

    Barcha rollar (owner, manager, seller) foydalana oladi.
    Parol o'zgartirish: /api/v1/auth/change-password/
    """
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action in ('update', 'partial_update'):
            return ProfileUpdateSerializer
        return CustomUserProfileSerializer

    def get_queryset(self):
        return CustomUser.objects.filter(id=self.request.user.id)

    def get_object(self) -> CustomUser:
        return self.request.user

    def update(self, request, *args, **kwargs):
        instance   = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {
                'message': "Profil muvaffaqiyatli yangilandi.",
                'data': CustomUserProfileSerializer(instance).data,
            },
            status=status.HTTP_200_OK,
        )


class SendPasswordResetEmailView(APIView):
    """
    Parolni tiklash uchun email yuborish.
    POST /api/v1/auth/send-reset-email/

    Ruxsat: hamma (AllowAny)
    So'rov tanasi: {"email": "user@example.com"}
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = SendPasswordResetEmailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(
            {'message': "Parolni tiklash uchun havola emailga yuborildi."},
            status=status.HTTP_200_OK,
        )


class UserPasswordResetView(APIView):
    """
    Email orqali yuborilgan havola yordamida yangi parol o'rnatish.
    POST /api/v1/auth/reset-password/<uid>/<token>/

    Ruxsat: hamma (AllowAny)
    So'rov tanasi: {"password": "...", "password2": "..."}
    """
    permission_classes = [AllowAny]

    def post(self, request, uid, token):
        serializer = UserPasswordResetSerializer(
            data=request.data,
            context={'uid': uid, 'token': token},
        )
        serializer.is_valid(raise_exception=True)
        return Response(
            {'message': "Parol muvaffaqiyatli o'zgartirildi!"},
            status=status.HTTP_200_OK,
        )


# ============================================================
# WORKER VIEW'LARI
# ============================================================

class WorkerViewSet(viewsets.ModelViewSet):
    """
    Hodimlarni boshqarish.

    Endpointlar:
      GET    /api/v1/workers/      — ro'yxat        (manager/seller ham ko'ra oladi)
      POST   /api/v1/workers/      — hodim qo'shish  (faqat owner)
      GET    /api/v1/workers/{id}/ — hodim ma'lumoti (manager/seller ham ko'ra oladi)
      PATCH  /api/v1/workers/{id}/ — hodimni yangilash (faqat owner)
      DELETE /api/v1/workers/{id}/ — hodimni ishdan chiqarish (faqat owner, soft delete)

    PATCH bir so'rovda barchasini o'zgartiradi:
      - User: first_name, last_name, phone1, phone2
      - Worker: role, branch, salary, status
      - Permissions: permissions = ["sotuv", "ombor", ...]

    Multi-tenant xavfsizlik:
      Faqat o'z do'konining hodimlarini ko'radi va boshqaradi.
    """
    http_method_names = ['get', 'post', 'patch', 'delete']

    # Search va filter
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields  = {
        'status': ['exact'],
        'role':   ['exact'],
        'branch': ['exact'],
    }
    search_fields = [
        'user__first_name',
        'user__last_name',
        'user__username',
        'user__phone1',
    ]

    def get_permissions(self):
        """
        list/retrieve  → IsManagerOrAbove  (manager va seller ham ko'ra oladi)
        create/update/destroy → IsOwner   (faqat ega)
        """
        if self.action in ('list', 'retrieve'):
            return [IsAuthenticated(), IsManagerOrAbove()]
        return [IsAuthenticated(), IsOwner()]

    def get_serializer_class(self):
        """So'rov turiga qarab to'g'ri serializer tanlanadi."""
        if self.action == 'list':
            return WorkerListSerializer
        if self.action == 'create':
            return WorkerCreateSerializer
        if self.action in ('update', 'partial_update'):
            return WorkerUpdateSerializer
        return WorkerDetailSerializer

    def get_queryset(self):
        """
        Faqat o'z do'konining hodimlarini qaytaradi (multi-tenant).
        Tartib: avval faollar, keyin tatildalgilar, oxirida ishdan ketganlar.
        Worker bo'lmagan foydalanuvchilar (masalan superadmin) uchun — bo'sh.
        """
        worker = getattr(self.request.user, 'worker', None)
        if not worker or not worker.store:
            return Worker.objects.none()
        return (
            Worker.objects
            .filter(store=worker.store)
            .select_related('user', 'store', 'branch')
            .annotate(
                status_order=Case(
                    When(status=WorkerStatus.ACTIVE,        then=Value(0)),
                    When(status=WorkerStatus.TATIL,         then=Value(1)),
                    When(status=WorkerStatus.ISHDAN_KETGAN, then=Value(2)),
                    default=Value(3),
                    output_field=IntegerField(),
                )
            )
            .order_by('status_order', 'user__first_name', 'user__last_name')
        )

    def get_serializer_context(self):
        """store kontekstini serializer ga uzatish (branch validatsiyasi uchun)."""
        context = super().get_serializer_context()
        worker = getattr(self.request.user, 'worker', None)
        if worker:
            context['store'] = worker.store
        return context

    def perform_create(self, serializer):
        """
        Hodim qo'shish — do'kon avtomatik belgilanadi.
        Faqat o'z do'koniga hodim qo'sha oladi.
        """
        worker = self.request.user.worker
        return serializer.save(store=worker.store)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(
            data=request.data,
            context=self.get_serializer_context(),
        )
        serializer.is_valid(raise_exception=True)
        worker = self.perform_create(serializer)

        AuditLog.objects.create(
            actor=request.user,
            action=AuditLog.Action.CREATE,
            target_model='Worker',
            target_id=worker.id if worker else None,
            description=f"Yangi hodim qo'shildi: {serializer.validated_data.get('username')}",
        )

        return Response(
            {
                'message': "Yangi hodim muvaffaqiyatli qo'shildi!",
                'data': WorkerDetailSerializer(worker, context={'request': request}).data,
            },
            status=status.HTTP_201_CREATED
        )

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(
            instance, data=request.data, partial=True,
            context=self.get_serializer_context(),
        )
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        AuditLog.objects.create(
            actor=request.user,
            action=AuditLog.Action.UPDATE,
            target_model='Worker',
            target_id=instance.id,
            description=f"Hodim ma'lumotlari yangilandi: {instance.user}",
        )

        return Response(
            {
                'message': "Hodim ma'lumotlari muvaffaqiyatli yangilandi.",
                'data': WorkerDetailSerializer(instance, context={'request': request}).data,
            },
            status=status.HTTP_200_OK
        )

    def destroy(self, request, *args, **kwargs):
        """
        Hodimni ishdan chiqarish — o'chirish o'rniga status='ishdan_ketgan' ga o'tkaziladi.
        DELETE /api/v1/workers/{id}/
        """
        instance = self.get_object()
        instance.status = WorkerStatus.ISHDAN_KETGAN
        instance.save(update_fields=['status'])

        AuditLog.objects.create(
            actor=request.user,
            action=AuditLog.Action.DELETE,
            target_model='Worker',
            target_id=instance.id,
            description=f"Hodim ishdan chiqarildi: {instance.user}",
        )

        return Response(
            {'message': "Hodim ishdan chiqarildi."},
            status=status.HTTP_200_OK,
        )

