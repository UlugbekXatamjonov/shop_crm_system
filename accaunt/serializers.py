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
   - WorkerUpdateSerializer     — hodimni yangilash (user+worker+permissions bitta PATCH da)
"""

from django.contrib.auth import authenticate
from django.utils.encoding import smart_str, force_bytes, DjangoUnicodeDecodeError
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.db import transaction

from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken, TokenError

from .models import CustomUser, Worker, WorkerRole, ALL_PERMISSIONS, ROLE_PERMISSIONS, phone_regex
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
        label="Parolni tasdiqlash",
        error_messages={
            'required': "Parolni tasdiqlash kiritilishi shart.",
            'blank':    "Parolni tasdiqlash bo'sh bo'lishi mumkin emas.",
        }
    )

    class Meta:
        model = CustomUser
        fields = (
            'username', 'first_name', 'last_name',
            'email', 'phone1', 'phone2',
            'password', 'password2',
        )
        extra_kwargs = {
            'password': {
                'write_only': True,
                'error_messages': {
                    'required': "Parol kiritilishi shart.",
                    'blank':    "Parol bo'sh bo'lishi mumkin emas.",
                },
            },
            'username': {
                'error_messages': {
                    'required':   "Login (username) kiritilishi shart.",
                    'blank':      "Login bo'sh bo'lishi mumkin emas.",
                    'max_length': "Login 150 belgidan oshmasligi kerak.",
                    'unique':     "Bu login allaqachon band.",
                },
            },
            'first_name': {
                'required': True,
                'error_messages': {
                    'required': "Ism kiritilishi shart.",
                    'blank':    "Ism bo'sh bo'lishi mumkin emas.",
                },
            },
            'last_name': {
                'required': True,
                'error_messages': {
                    'required': "Familiya kiritilishi shart.",
                    'blank':    "Familiya bo'sh bo'lishi mumkin emas.",
                },
            },
            'email': {
                'required': True,
                'error_messages': {
                    'required': "Email manzil kiritilishi shart.",
                    'blank':    "Email manzil bo'sh bo'lishi mumkin emas.",
                    'invalid':  "To'g'ri email manzil kiriting (masalan: ism@example.com).",
                },
            },
            'phone1': {
                'error_messages': {
                    'required': "Telefon raqami kiritilishi shart.",
                    'blank':    "Telefon raqami bo'sh bo'lishi mumkin emas.",
                    'invalid':  "Telefon raqami '+998901234567' formatida bo'lishi kerak.",
                },
            },
            'phone2': {
                'error_messages': {
                    'invalid': "Telefon raqami '+998901234567' formatida bo'lishi kerak.",
                },
            },
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
            permissions=list(ROLE_PERMISSIONS.get(WorkerRole.OWNER, [])),
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
# PROFIL YANGILASH SERIALIZERI
# ============================================================

class ProfileUpdateSerializer(serializers.ModelSerializer):
    """
    Foydalanuvchi o'z shaxsiy ma'lumotlarini yangilash.
    PATCH /api/v1/auth/profil/ da ishlatiladi.

    Barcha rollar (owner, manager, seller) foydalana oladi.
    Faqat o'z profilini tahrirlash mumkin.
    Parol o'zgartirish uchun: /api/v1/auth/change-password/
    """

    class Meta:
        model  = CustomUser
        fields = ('first_name', 'last_name', 'phone1', 'phone2')

    def validate_phone1(self, value: str) -> str:
        """Telefon raqami boshqa foydalanuvchida band emasligini tekshiradi."""
        qs = CustomUser.objects.filter(phone1=value).exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError(
                "Bu telefon raqami allaqachon boshqa foydalanuvchida band."
            )
        return value

    def validate_phone2(self, value: str) -> str:
        """Qo'shimcha telefon raqami — format va band emasligi tekshiriladi."""
        import re
        if not value:
            return value
        if not re.match(r'^\+998\d{9}$', value):
            raise serializers.ValidationError(
                "Telefon raqami '+998901234567' formatida bo'lishi kerak."
            )
        qs = CustomUser.objects.filter(phone2=value).exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError(
                "Bu telefon raqami allaqachon boshqa foydalanuvchida band."
            )
        return value


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

    class Meta:
        model = Worker
        fields = (
            'id',
            'full_name', 'username', 'email', 'phone1', 'phone2',
            'role', 'role_display',
            'branch_name', 'salary', 'status',
            'permissions',
            'created_on',
        )

    def get_full_name(self, obj: Worker) -> str:
        return str(obj.user)


class WorkerCreateSerializer(serializers.Serializer):
    """
    Yangi hodim qo'shish.
    CustomUser va Worker birgalikda yaratiladi (atomic transaction).
    Do'kon — JWT token orqali aniqlanadi (view da beriladi).

    POST /api/v1/workers/ da ishlatiladi.

    permissions (ixtiyoriy):
      - Yuborilmasa → ROLE_PERMISSIONS[role] dan avtomatik to'ldiriladi
      - Yuborilsa   → berilgan ro'yxat ishlatiladi (to'liq almashtiradi)
    """
    # --- CustomUser maydonlari ---
    first_name = serializers.CharField(
        max_length=150, label="Ismi",
        error_messages={
            'required': "Ism kiritilishi shart.",
            'blank':    "Ism bo'sh bo'lishi mumkin emas.",
            'max_length': "Ism 150 belgidan oshmasligi kerak.",
        }
    )
    last_name = serializers.CharField(
        max_length=150, label="Familiyasi",
        error_messages={
            'required': "Familiya kiritilishi shart.",
            'blank':    "Familiya bo'sh bo'lishi mumkin emas.",
            'max_length': "Familiya 150 belgidan oshmasligi kerak.",
        }
    )
    username = serializers.CharField(
        max_length=150, label="Login (username)",
        error_messages={
            'required':   "Login kiritilishi shart.",
            'blank':      "Login bo'sh bo'lishi mumkin emas.",
            'max_length': "Login 150 belgidan oshmasligi kerak.",
        }
    )
    phone1 = serializers.CharField(
        max_length=13, label="Telefon raqami",
        validators=[phone_regex],
        error_messages={
            'required': "Telefon raqami kiritilishi shart.",
            'blank':    "Telefon raqami bo'sh bo'lishi mumkin emas.",
            'max_length': "Telefon raqami 13 belgidan oshmasligi kerak.",
        }
    )
    email = serializers.EmailField(
        required=False, allow_blank=True, default='', label="Email",
        error_messages={
            'invalid': "To'g'ri email manzil kiriting (masalan: ism@example.com).",
        }
    )
    password = serializers.CharField(
        write_only=True,
        min_length=6,
        style={'input_type': 'password'},
        label="Parol",
        error_messages={
            'required':   "Parol kiritilishi shart.",
            'blank':      "Parol bo'sh bo'lishi mumkin emas.",
            'min_length': "Parol kamida 6 belgidan iborat bo'lishi kerak.",
        }
    )

    # --- Worker maydonlari ---
    role = serializers.ChoiceField(
        choices=WorkerRole.choices, label="Roli",
        error_messages={
            'required':       "Rol kiritilishi shart.",
            'invalid_choice': "'{input}' noto'g'ri rol. Mavjud rollar: owner, manager, seller.",
        }
    )
    branch = serializers.IntegerField(
        required=False, allow_null=True, label="Filial ID",
        error_messages={
            'invalid': "Filial ID butun son bo'lishi kerak.",
        }
    )
    salary = serializers.DecimalField(
        max_digits=12, decimal_places=2,
        default=0, label="Maoshi (UZS)",
        error_messages={
            'invalid':     "Maosh to'g'ri raqam formatida kiritilishi kerak.",
            'max_digits':  "Maosh 12 raqamdan oshmasligi kerak.",
            'max_decimal_places': "Maoshda 2 tadan ko'p kasr raqam bo'lishi mumkin emas.",
        }
    )

    # --- Ruxsatlar (ixtiyoriy) ---
    permissions = serializers.ListField(
        child=serializers.ChoiceField(
            choices=ALL_PERMISSIONS,
            error_messages={
                'invalid_choice': "'{input}' noto'g'ri ruxsat kodi.",
            }
        ),
        required=False,
        allow_empty=True,
        label="Ruxsatlar ro'yxati (ixtiyoriy — bo'sh qolsa rol asosida to'ldiriladi)",
    )

    def validate_username(self, value: str) -> str:
        if CustomUser.objects.filter(username=value).exists():
            raise serializers.ValidationError("Bu login allaqachon band.")
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

    def validate_permissions(self, value: list) -> list:
        """Noto'g'ri permission kodlarini qaytaradi."""
        invalid = [p for p in value if p not in ALL_PERMISSIONS]
        if invalid:
            raise serializers.ValidationError(
                f"Noto'g'ri ruxsat kodlari: {invalid}. Mavjud kodlar: {ALL_PERMISSIONS}"
            )
        return sorted(set(value))

    @transaction.atomic
    def create(self, validated_data: dict) -> Worker:
        """
        CustomUser va Worker birgalikda yaratiladi.
        Xato yuz bersa — ikkalasi ham bekor qilinadi (atomic transaction).
        """
        from store.models import Branch

        store            = validated_data.pop('store')          # view da beriladi
        branch_id        = validated_data.pop('branch', None)
        role             = validated_data.pop('role')
        salary           = validated_data.pop('salary', 0)
        permissions_data = validated_data.pop('permissions', None)

        # Branch — faqat shu do'konning filiallari qabul qilinadi
        branch = None
        if branch_id:
            try:
                branch = Branch.objects.get(id=branch_id, store=store)
            except Branch.DoesNotExist:
                raise serializers.ValidationError(
                    {'branch': "Bu filial sizning do'koningizga tegishli emas yoki topilmadi."}
                )

        # 1. CustomUser yaratish
        user = CustomUser.objects.create_user(
            username   = validated_data['username'],
            email      = validated_data.get('email', ''),
            phone1     = validated_data['phone1'],
            password   = validated_data['password'],
            first_name = validated_data['first_name'],
            last_name  = validated_data['last_name'],
        )

        # 2. Permissions: berilsa — berilgani, aks holda rol asosida
        if permissions_data is not None:
            permissions = sorted(set(permissions_data))
        else:
            permissions = list(ROLE_PERMISSIONS.get(role, []))

        # 3. Worker yaratish
        worker = Worker.objects.create(
            user        = user,
            role        = role,
            store       = store,
            branch      = branch,
            salary      = salary,
            permissions = permissions,
        )
        return worker


class WorkerUpdateSerializer(serializers.ModelSerializer):
    """
    Hodim ma'lumotlarini yangilash — faqat do'kon egasi uchun.
    PATCH /api/v1/workers/{id}/ da ishlatiladi.

    User ma'lumotlari (first_name, last_name, phone1, phone2) va
    Worker ma'lumotlari (role, branch, salary, status, permissions)
    bitta PATCH so'rovda tahrirlanadi. Yuborilmagan maydonlar o'zgarmaydi.

    Misol:
      {"first_name": "Ali", "role": "manager", "permissions": ["sotuv", "ombor"]}
    """
    # --- CustomUser maydonlari (source='user.*' orqali) ---
    first_name = serializers.CharField(
        source='user.first_name', required=False, allow_blank=True, label="Ismi",
        error_messages={
            'blank':      "Ism bo'sh bo'lishi mumkin emas.",
            'max_length': "Ism 150 belgidan oshmasligi kerak.",
        }
    )
    last_name = serializers.CharField(
        source='user.last_name', required=False, allow_blank=True, label="Familiyasi",
        error_messages={
            'blank':      "Familiya bo'sh bo'lishi mumkin emas.",
            'max_length': "Familiya 150 belgidan oshmasligi kerak.",
        }
    )
    phone1 = serializers.CharField(
        source='user.phone1', required=False, label="Asosiy telefon",
        validators=[phone_regex],
        error_messages={
            'blank': "Telefon raqami bo'sh bo'lishi mumkin emas.",
        }
    )
    phone2 = serializers.CharField(
        source='user.phone2', required=False, allow_blank=True, allow_null=True,
        label="Qo'shimcha telefon",
    )

    # --- Ruxsatlar ro'yxati ---
    permissions = serializers.ListField(
        child=serializers.ChoiceField(
            choices=ALL_PERMISSIONS,
            error_messages={
                'invalid_choice': "'{input}' noto'g'ri ruxsat kodi.",
            }
        ),
        required=False,
        label="Ruxsatlar ro'yxati"
    )

    class Meta:
        model  = Worker
        fields = (
            'first_name', 'last_name', 'phone1', 'phone2',
            'role', 'branch', 'salary', 'status', 'permissions',
        )
        extra_kwargs = {
            'role': {
                'error_messages': {
                    'invalid_choice': "'{input}' noto'g'ri rol. Mavjud rollar: owner, manager, seller.",
                }
            },
            'status': {
                'error_messages': {
                    'invalid_choice': "'{input}' noto'g'ri holat. Mavjud holatlar: active, tatil, ishdan_ketgan.",
                }
            },
            'salary': {
                'error_messages': {
                    'invalid':            "Maosh to'g'ri raqam formatida kiritilishi kerak.",
                    'max_digits':         "Maosh 12 raqamdan oshmasligi kerak.",
                    'max_decimal_places': "Maoshda 2 tadan ko'p kasr raqam bo'lishi mumkin emas.",
                }
            },
        }

    # --- Validatsiyalar ---

    def validate_phone1(self, value: str) -> str:
        """Telefon raqami boshqa foydalanuvchida band emasligini tekshiradi."""
        qs = CustomUser.objects.filter(phone1=value).exclude(pk=self.instance.user.pk)
        if qs.exists():
            raise serializers.ValidationError(
                "Bu telefon raqami allaqachon boshqa foydalanuvchida band."
            )
        return value

    def validate_phone2(self, value: str) -> str:
        """Qo'shimcha telefon raqami — format va band emasligi tekshiriladi."""
        import re
        if not value:
            return value
        if not re.match(r'^\+998\d{9}$', value):
            raise serializers.ValidationError(
                "Telefon raqami '+998901234567' formatida bo'lishi kerak."
            )
        qs = CustomUser.objects.filter(phone2=value).exclude(pk=self.instance.user.pk)
        if qs.exists():
            raise serializers.ValidationError(
                "Bu telefon raqami allaqachon boshqa foydalanuvchida band."
            )
        return value

    def validate_branch(self, value):
        """Filial shu hodimning do'koniga tegishli ekanligini tekshiradi."""
        if value is None:
            return value
        if self.instance and value.store_id != self.instance.store_id:
            raise serializers.ValidationError(
                "Bu filial sizning do'koningizga tegishli emas."
            )
        return value

    def validate_role(self, value: str) -> str:
        """Owner rolini faqat do'kon egasi yoki superadmin belgilay oladi."""
        if value == WorkerRole.OWNER:
            request    = self.context.get('request')
            cur_worker = getattr(request.user, 'worker', None)
            is_owner   = cur_worker and cur_worker.role == WorkerRole.OWNER
            if not request.user.is_superuser and not is_owner:
                raise serializers.ValidationError(
                    "Owner rolini faqat do'kon egasi yoki superadmin belgilay oladi."
                )
        return value

    def validate_permissions(self, value: list) -> list:
        """Faqat mavjud permission kodlarini qabul qiladi, takrorlanishlarni olib tashlaydi."""
        invalid = [p for p in value if p not in ALL_PERMISSIONS]
        if invalid:
            raise serializers.ValidationError(
                f"Noto'g'ri ruxsat kodlari: {invalid}. Mavjud kodlar: {ALL_PERMISSIONS}"
            )
        return sorted(set(value))

    # --- Saqlash ---

    @transaction.atomic
    def update(self, instance: Worker, validated_data: dict) -> Worker:
        """
        CustomUser va Worker ma'lumotlarini birgalikda yangilaydi.
        Faqat yuborilgan maydonlar o'zgaradi (partial=True).
        """
        # User maydonlarini ajratib olamiz (source='user.*' → 'user' kalitida keladi)
        user_data = validated_data.pop('user', {})
        if user_data:
            user = instance.user
            for attr, value in user_data.items():
                setattr(user, attr, value)
            user.save(update_fields=list(user_data.keys()))

        # Worker maydonlarini yangilaymiz
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        return instance
