"""
============================================================
ACCAUNT APP — Serializerlar
============================================================
Serializer'lar ikki guruhga bo'lingan:

1. AUTH serializerlari (foydalanuvchi autentifikatsiyasi):
   - UserRegistrationSerializer
   - UserLoginSerializer
   - LogoutSerializer
   - UserChangePasswordSerializer
   - UserPasswordResetSerializer

2. WORKER serializerlari (hodimlarni boshqarish):
   - WorkerProfileSerializer    — o'z profilini ko'rish (login da)
   - CustomUserProfileSerializer — user + worker birgalikda
   - WorkerListSerializer       — ro'yxat uchun (qisqa)
   - WorkerDetailSerializer     — to'liq ma'lumot
   - WorkerCreateSerializer     — hodim qo'shish
   - WorkerUpdateSerializer     — hodimni yangilash
   - WorkerPermissionSerializer — individual permission o'zgartirish
"""

from django.contrib.auth import authenticate
from django.utils.encoding import smart_str, force_bytes, DjangoUnicodeDecodeError
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.db import transaction

from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken, TokenError

from .models import CustomUser, Worker, WorkerRole, WorkerStatus, ALL_PERMISSIONS, ROLE_PERMISSIONS
from .utils import Util


# ============================================================
# AUTH SERIALIZERLARI
# ============================================================

class UserRegistrationSerializer(serializers.ModelSerializer):
    """
    Yangi foydalanuvchi ro'yxatdan o'tkazish.
    password va password2 mos kelishi tekshiriladi.
    """
    password2 = serializers.CharField(
        style={'input_type': 'password'},
        write_only=True,
        label="Parolni tasdiqlash"
    )

    class Meta:
        model = CustomUser
        fields = (
            'username', 'first_name', 'last_name',
            'email', 'phone1', 'phone2',
            'password', 'password2',
        )
        extra_kwargs = {
            'password': {'write_only': True},
        }

    def validate(self, attrs: dict) -> dict:
        if attrs['password'] != attrs.pop('password2'):
            raise serializers.ValidationError("Kiritilgan parollar bir xil emas!")
        return attrs

    @transaction.atomic
    def create(self, validated_data: dict) -> CustomUser:
        """
        CustomUser yaratiladi va avtomatik 'owner' Worker profili biriktiriladi.
        Faqat do'kon egasi ro'yxatdan o'tadi — do'kon keyinchalik qo'shiladi.
        """
        user = CustomUser.objects.create_user(**validated_data)
        Worker.objects.create(
            user=user,
            role=WorkerRole.OWNER,
            store=None,
            branch=None,
        )
        return user


class UserLoginSerializer(serializers.Serializer):
    """
    Foydalanuvchi tizimga kirishi.
    username va password orqali autentifikatsiya qilinadi.
    """
    username = serializers.CharField(label="Foydalanuvchi nomi")
    password = serializers.CharField(
        write_only=True,
        style={'input_type': 'password'},
        label="Parol"
    )

    def validate(self, attrs: dict) -> dict:
        user = authenticate(
            username=attrs.get('username'),
            password=attrs.get('password')
        )
        if not user:
            raise serializers.ValidationError("Username yoki parol noto'g'ri!")
        if not user.status:
            raise serializers.ValidationError("Hisobingiz bloklangan. Admin bilan bog'laning.")
        attrs['user'] = user
        return attrs


class LogoutSerializer(serializers.Serializer):
    """
    Tizimdan chiqish — refresh tokenni blacklist ga qo'shadi.
    """
    refresh = serializers.CharField(label="Refresh token")

    def validate(self, attrs: dict) -> dict:
        self.token = attrs['refresh']
        return attrs

    def save(self, **kwargs) -> None:
        try:
            RefreshToken(self.token).blacklist()
        except TokenError:
            raise serializers.ValidationError(
                "Token yaroqsiz yoki allaqachon ishlatilgan!"
            )


class UserChangePasswordSerializer(serializers.Serializer):
    """
    Parolni o'zgartirish.
    Joriy parol to'g'riligini tekshirib, yangi parol o'rnatiladi.
    """
    current_password = serializers.CharField(
        write_only=True,
        style={'input_type': 'password'},
        label="Joriy parol"
    )
    password = serializers.CharField(
        write_only=True,
        style={'input_type': 'password'},
        label="Yangi parol"
    )
    password2 = serializers.CharField(
        write_only=True,
        style={'input_type': 'password'},
        label="Yangi parolni tasdiqlash"
    )

    def validate_current_password(self, value: str) -> str:
        user = self.context['user']
        if not user.check_password(value):
            raise serializers.ValidationError("Joriy parol noto'g'ri!")
        return value

    def validate(self, attrs: dict) -> dict:
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError("Yangi parollar bir xil emas!")
        user = self.context['user']
        user.set_password(attrs['password'])
        user.save()
        return attrs


class SendPasswordResetEmailSerializer(serializers.Serializer):
    """Parolni tiklash uchun email yuborish."""
    email = serializers.EmailField(label="Email manzil")

    def validate(self, attrs: dict) -> dict:
        email = attrs['email']
        try:
            user = CustomUser.objects.get(email=email)
        except CustomUser.DoesNotExist:
            raise serializers.ValidationError("Bu email bilan foydalanuvchi topilmadi.")

        uid   = urlsafe_base64_encode(force_bytes(user.id))
        token = PasswordResetTokenGenerator().make_token(user)
        link  = f'http://localhost:3000/reset-password/{uid}/{token}'

        Util.send_email({
            'subject': 'Parolni tiklash',
            'body': f'Parolni tiklash uchun: {link}',
            'to_email': user.email,
        })
        return attrs


class UserPasswordResetSerializer(serializers.Serializer):
    """Email orqali yuborilgan token yordamida yangi parol o'rnatish."""
    password  = serializers.CharField(write_only=True, style={'input_type': 'password'})
    password2 = serializers.CharField(write_only=True, style={'input_type': 'password'})

    def validate(self, attrs: dict) -> dict:
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError("Parollar bir xil emas!")
        try:
            uid     = self.context['uid']
            token   = self.context['token']
            user_id = smart_str(urlsafe_base64_decode(uid))
            user    = CustomUser.objects.get(id=user_id)
            if not PasswordResetTokenGenerator().check_token(user, token):
                raise serializers.ValidationError("Token yaroqsiz yoki muddati o'tgan.")
            user.set_password(attrs['password'])
            user.save()
        except (DjangoUnicodeDecodeError, CustomUser.DoesNotExist):
            raise serializers.ValidationError("Token yaroqsiz yoki muddati o'tgan.")
        return attrs


# ============================================================
# WORKER SERIALIZERLARI
# ============================================================

class WorkerProfileSerializer(serializers.ModelSerializer):
    """
    Hodim profili — login javobida va /profil/ endpointida ishlatiladi.
    Hodimning barcha permission'lari get_permissions() orqali hisoblanadi.
    """
    role_display = serializers.CharField(source='get_role_display', read_only=True)
    permissions  = serializers.SerializerMethodField()
    store_id     = serializers.IntegerField(source='store.id',   read_only=True)
    store_name   = serializers.CharField(source='store.name',    read_only=True)
    branch_id    = serializers.IntegerField(source='branch.id',  read_only=True)
    branch_name  = serializers.CharField(source='branch.name',   read_only=True)

    class Meta:
        model = Worker
        fields = (
            'id', 'role', 'role_display', 'permissions',
            'store_id', 'store_name',
            'branch_id', 'branch_name',
            'status',
        )

    def get_permissions(self, obj: Worker) -> list[str]:
        """Hodimning yakuniy permission ro'yxati (rol + individual o'zgarishlar)."""
        return obj.get_permissions()


class CustomUserProfileSerializer(serializers.ModelSerializer):
    """
    Foydalanuvchi profili — Worker ma'lumotlari bilan birga.
    Login va GET /api/v1/auth/profil/ da qaytariladi.
    """
    worker = WorkerProfileSerializer(read_only=True)

    class Meta:
        model = CustomUser
        fields = (
            'id', 'username',
            'first_name', 'last_name',
            'email', 'phone1', 'phone2',
            'status', 'worker',
        )


class WorkerListSerializer(serializers.ModelSerializer):
    """
    Hodimlar ro'yxati uchun qisqa serializer.
    GET /api/v1/workers/ da ishlatiladi.
    """
    full_name    = serializers.SerializerMethodField()
    role_display = serializers.CharField(source='get_role_display', read_only=True)
    branch_name  = serializers.CharField(source='branch.name', read_only=True)
    phone1       = serializers.CharField(source='user.phone1', read_only=True)

    class Meta:
        model = Worker
        fields = (
            'id', 'full_name', 'phone1', 'role', 'role_display',
            'branch_name', 'salary', 'status',
        )

    def get_full_name(self, obj: Worker) -> str:
        return str(obj.user)


class WorkerDetailSerializer(serializers.ModelSerializer):
    """
    Hodimning to'liq ma'lumoti.
    GET /api/v1/workers/{id}/ da ishlatiladi.
    """
    full_name    = serializers.SerializerMethodField()
    username     = serializers.CharField(source='user.username', read_only=True)
    phone1       = serializers.CharField(source='user.phone1',   read_only=True)
    phone2       = serializers.CharField(source='user.phone2',   read_only=True)
    email        = serializers.CharField(source='user.email',    read_only=True)
    role_display = serializers.CharField(source='get_role_display', read_only=True)
    branch_name  = serializers.CharField(source='branch.name',  read_only=True)
    # Yakuniy permission ro'yxati (rol standart + qo'shilgan − olib tashlangan)
    permissions  = serializers.SerializerMethodField()

    class Meta:
        model = Worker
        fields = (
            'id',
            'full_name', 'username', 'email', 'phone1', 'phone2',
            'role', 'role_display',
            'branch_name', 'salary', 'status',
            'permissions',
            'extra_permissions',  # {"added": [...], "removed": [...]}
            'created_on',
        )

    def get_full_name(self, obj: Worker) -> str:
        return str(obj.user)

    def get_permissions(self, obj: Worker) -> list[str]:
        return obj.get_permissions()


class WorkerCreateSerializer(serializers.Serializer):
    """
    Yangi hodim qo'shish.
    CustomUser va Worker birgalikda yaratiladi (atomic transaction).
    Do'kon — JWT token orqali aniqlanadi (view da beriladi).

    POST /api/v1/workers/ da ishlatiladi.
    """
    # --- CustomUser maydonlari ---
    first_name = serializers.CharField(max_length=150, label="Ismi")
    last_name  = serializers.CharField(max_length=150, label="Familiyasi")
    username   = serializers.CharField(max_length=150, label="Login (username)")
    phone1     = serializers.CharField(max_length=13,  label="Telefon raqami")
    email      = serializers.EmailField(required=False, allow_blank=True, default='', label="Email")
    password   = serializers.CharField(
        write_only=True,
        min_length=6,
        style={'input_type': 'password'},
        label="Parol"
    )

    # --- Worker maydonlari ---
    role   = serializers.ChoiceField(choices=WorkerRole.choices, label="Roli")
    branch = serializers.IntegerField(required=False, allow_null=True, label="Filial ID")
    salary = serializers.DecimalField(
        max_digits=12, decimal_places=2,
        default=0, label="Maoshi (UZS)"
    )

    def validate_username(self, value: str) -> str:
        if CustomUser.objects.filter(username=value).exists():
            raise serializers.ValidationError("Bu username allaqachon band.")
        return value

    def validate_phone1(self, value: str) -> str:
        if CustomUser.objects.filter(phone1=value).exists():
            raise serializers.ValidationError("Bu telefon raqami allaqachon ro'yxatdan o'tgan.")
        return value

    def validate_role(self, value: str) -> str:
        """Owner rolini faqat do'kon egasi yoki superadmin tayinlay oladi."""
        if value == WorkerRole.OWNER:
            request = self.context.get('request')
            cur_worker = getattr(request.user, 'worker', None)
            is_owner   = cur_worker and cur_worker.role == WorkerRole.OWNER
            if not request.user.is_superuser and not is_owner:
                raise serializers.ValidationError(
                    "Owner rolini faqat do'kon egasi yoki superadmin tayinlay oladi."
                )
        return value

    @transaction.atomic
    def create(self, validated_data: dict) -> Worker:
        """
        CustomUser va Worker birgalikda yaratiladi.
        Xato yuz bersa — ikkalasi ham bekor qilinadi (atomic transaction).
        """
        from store.models import Branch

        store     = validated_data.pop('store')       # view da beriladi
        branch_id = validated_data.pop('branch', None)
        role      = validated_data.pop('role')
        salary    = validated_data.pop('salary', 0)

        branch = None
        if branch_id:
            try:
                branch = Branch.objects.get(id=branch_id)
            except Branch.DoesNotExist:
                raise serializers.ValidationError({'branch': "Bunday filial topilmadi."})

        # 1. CustomUser yaratish
        user = CustomUser.objects.create_user(
            username   = validated_data['username'],
            email      = validated_data.get('email', ''),
            phone1     = validated_data['phone1'],
            password   = validated_data['password'],
            first_name = validated_data['first_name'],
            last_name  = validated_data['last_name'],
        )

        # 2. Worker yaratish
        worker = Worker.objects.create(
            user   = user,
            role   = role,
            store  = store,
            branch = branch,
            salary = salary,
        )
        return worker


class WorkerUpdateSerializer(serializers.ModelSerializer):
    """
    Hodim ma'lumotlarini yangilash.
    PATCH /api/v1/workers/{id}/ da ishlatiladi.
    Faqat rol, filial, maosh va holat o'zgartirilishi mumkin.

    Status o'zgartirish qoidalari:
      - Faqat do'kon egasi (owner) statusni o'zgartira oladi
      - Do'kon egasini 'ishdan_ketgan' ga o'tkazib bo'lmaydi
    """
    class Meta:
        model = Worker
        fields = ('role', 'branch', 'salary', 'status')

    def validate_role(self, value: str) -> str:
        """Owner rolini faqat do'kon egasi yoki superadmin belgilay oladi."""
        if value == WorkerRole.OWNER:
            request = self.context.get('request')
            cur_worker = getattr(request.user, 'worker', None)
            is_owner   = cur_worker and cur_worker.role == WorkerRole.OWNER
            if not request.user.is_superuser and not is_owner:
                raise serializers.ValidationError(
                    "Owner rolini faqat do'kon egasi yoki superadmin belgilay oladi."
                )
        return value

    def validate_status(self, value: str) -> str:
        """Statusni faqat do'kon egasi o'zgartira oladi."""
        request    = self.context.get('request')
        cur_worker = getattr(request.user, 'worker', None)
        if not cur_worker or cur_worker.role != WorkerRole.OWNER:
            raise serializers.ValidationError(
                "Hodim statusini faqat do'kon egasi o'zgartira oladi."
            )
        # Eganing o'zini ishdan chiqarib bo'lmaydi
        if value == WorkerStatus.ISHDAN_KETGAN and self.instance.role == WorkerRole.OWNER:
            raise serializers.ValidationError(
                "Do'kon egasini ishdan chiqarib bo'lmaydi."
            )
        return value


class WorkerPermissionSerializer(serializers.Serializer):
    """
    Hodimning individual permission'larini o'zgartirish.
    PATCH /api/v1/workers/{id}/permissions/ da ishlatiladi.

    add    — qo'shish kerak bo'lgan permission kodlar ro'yxati
    remove — olib tashlash kerak bo'lgan permission kodlar ro'yxati

    Misol so'rov:
        {"add": ["sozlamalar"], "remove": ["sklad"]}

    Natija: hodimning extra_permissions maydoni yangilanadi.
    """
    add = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        default=list,
        label="Qo'shilayotgan ruxsatlar"
    )
    remove = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        default=list,
        label="Olib tashlanayotgan ruxsatlar"
    )

    def _validate_codes(self, value: list, field_name: str) -> list:
        """Faqat mavjud permission kodlarini qabul qiladi."""
        invalid = [code for code in value if code not in ALL_PERMISSIONS]
        if invalid:
            raise serializers.ValidationError(
                f"Noto'g'ri permission kodlar: {invalid}. "
                f"Mavjud kodlar: {ALL_PERMISSIONS}"
            )
        return value

    def validate_add(self, value: list) -> list:
        return self._validate_codes(value, 'add')

    def validate_remove(self, value: list) -> list:
        return self._validate_codes(value, 'remove')

    def validate(self, attrs: dict) -> dict:
        """add va remove da bir xil kod bo'lmasligi kerak."""
        conflict = set(attrs.get('add', [])) & set(attrs.get('remove', []))
        if conflict:
            raise serializers.ValidationError(
                f"Bir vaqtda qo'shib va olib tashlab bo'lmaydi: {sorted(conflict)}"
            )
        return attrs

    def update(self, worker: Worker, validated_data: dict) -> Worker:
        """
        Worker.extra_permissions ni yangilaydi.

        Mantiq:
          - Qo'shilayotganlar 'removed' dan chiqariladi (agar oldin olib tashlangan bo'lsa)
          - Olib tashlanayotganlar 'added' dan chiqariladi (agar oldin qo'shilgan bo'lsa)
          - Rolda standart mavjud permission'larni 'added' da saqlash keraksiz — tozalanadi
          - Rolda mavjud bo'lmagan permission'larni 'removed' da saqlash keraksiz — tozalanadi
        """
        extra = worker.extra_permissions or {}
        cur_added   = set(extra.get('added',   []))
        cur_removed = set(extra.get('removed', []))

        new_add    = set(validated_data.get('add',    []))
        new_remove = set(validated_data.get('remove', []))

        # Qo'shilayotganlar 'removed' dan o'chiriladi
        cur_removed -= new_add
        cur_added   |= new_add

        # Olib tashlanayotganlar 'added' dan o'chiriladi
        cur_added   -= new_remove
        cur_removed |= new_remove

        # Rolning standart permission'lari 'added' da bo'lishi keraksiz
        default = set(ROLE_PERMISSIONS.get(worker.role, []))
        cur_added   -= default
        # Rolda bo'lmagan permission'lar 'removed' da bo'lishi keraksiz
        cur_removed &= default

        worker.extra_permissions = {
            'added':   sorted(cur_added),
            'removed': sorted(cur_removed),
        }
        worker.save(update_fields=['extra_permissions'])
        return worker
