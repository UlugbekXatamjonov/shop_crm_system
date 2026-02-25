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

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework import status, viewsets, mixins
from rest_framework_simplejwt.tokens import RefreshToken

from .models import CustomUser, Worker, AuditLog
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

    PATCH bir so'rovda barchasini o'zgartiradi:
      - User: first_name, last_name, phone1, phone2
      - Worker: role, branch, salary, status
      - Permissions: permissions = ["sotuv", "ombor", ...]

    Multi-tenant xavfsizlik:
      Faqat o'z do'konining hodimlarini ko'radi va boshqaradi.
    """
    http_method_names = ['get', 'post', 'patch']

    def get_permissions(self):
        """
        list/retrieve  → IsManagerOrAbove  (manager va seller ham ko'ra oladi)
        create/update  → IsOwner           (faqat ega qo'shadi va o'zgartiradi)
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
        Worker bo'lmagan foydalanuvchilar (masalan superadmin) uchun — bo'sh.
        """
        worker = getattr(self.request.user, 'worker', None)
        if not worker or not worker.store:
            return Worker.objects.none()
        return (
            Worker.objects
            .filter(store=worker.store)
            .select_related('user', 'branch')
            .order_by('user__first_name', 'user__last_name')
        )

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
            context={'request': request}
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
            context={'request': request},
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

