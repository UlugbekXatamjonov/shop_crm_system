from django.test import TestCase
from django.urls import reverse

from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

from .models import CustomUser, Permission, Role, Worker


# =====================================================================
# Helper — testlarda qayta-qayta user yaratib o'tirmaslik uchun
# =====================================================================

def create_user(
    username='testuser',
    password='Test@12345',
    email='test@example.com',
    phone1='+998901234567',
    first_name='Test',
    last_name='User',
):
    return CustomUser.objects.create_user(
        username=username,
        password=password,
        email=email,
        phone1=phone1,
        first_name=first_name,
        last_name=last_name,
        is_superuser=False,
        is_staff=False,
        phone2=None,
    )


# =====================================================================
# 1. MODEL TESTLAR
# =====================================================================

class CustomUserModelTest(TestCase):

    def test_user_created_successfully(self):
        """ User to'g'ri yaratilganini tekshirish """
        user = create_user()
        self.assertEqual(user.username, 'testuser')
        self.assertEqual(user.email, 'test@example.com')
        self.assertTrue(user.check_password('Test@12345'))

    def test_user_str(self):
        """ __str__ metodi to'g'ri ishlashini tekshirish """
        user = create_user(first_name='Ali', last_name='Valiyev')
        self.assertEqual(str(user), 'Ali Valiyev')

    def test_user_status_default_true(self):
        """ Status default True bo'lishini tekshirish """
        user = create_user()
        self.assertTrue(user.status)

    def test_phone_saved_correctly(self):
        """ Telefon raqam to'g'ri saqlanishini tekshirish """
        user = create_user(phone1='+998991112233')
        self.assertEqual(user.phone1, '+998991112233')

    def test_username_is_unique(self):
        """ Bir xil username ikki marta yaratilmasligi kerak """
        create_user(username='uniqueuser')
        with self.assertRaises(Exception):
            create_user(username='uniqueuser')


# =====================================================================
# 2. REGISTER TESTLAR
# =====================================================================

class UserRegistrationTest(APITestCase):

    def setUp(self):
        self.url = reverse('register')  # urls.py dagi name='register'
        self.valid_data = {
            'username': 'newuser',
            'password': 'Test@12345',
            'password2': 'Test@12345',
            'email': 'newuser@example.com',
            'first_name': 'Yangi',
            'last_name': 'Foydalanuvchi',
            'phone1': '+998901234567',
        }

    def test_register_success(self):
        """ To'g'ri ma'lumotlar bilan ro'yhatdan o'tish """
        response = self.client.post(self.url, self.valid_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('token', response.data)
        self.assertTrue(CustomUser.objects.filter(username='newuser').exists())

    def test_register_password_mismatch(self):
        """ Parollar mos kelmasa xato berishi kerak """
        data = self.valid_data.copy()
        data['password2'] = 'WrongPassword'
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_missing_username(self):
        """ Username bo'lmasa xato berishi kerak """
        data = self.valid_data.copy()
        data.pop('username')
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_missing_phone(self):
        """ phone1 bo'lmasa xato berishi kerak """
        data = self.valid_data.copy()
        data.pop('phone1')
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_duplicate_username(self):
        """ Bir xil username bilan ikki marta ro'yhatdan o'tib bo'lmaydi """
        self.client.post(self.url, self.valid_data, format='json')
        response = self.client.post(self.url, self.valid_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_invalid_email(self):
        """ Noto'g'ri email bilan ro'yhatdan o'tib bo'lmaydi """
        data = self.valid_data.copy()
        data['email'] = 'notanemail'
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


# =====================================================================
# 3. LOGIN TESTLAR
# =====================================================================

class UserLoginTest(APITestCase):

    def setUp(self):
        self.url = reverse('login')
        self.user = create_user(username='loginuser', password='Test@12345')

    def test_login_success(self):
        """ To'g'ri ma'lumotlar bilan login bo'lish """
        response = self.client.post(self.url, {
            'username': 'loginuser',
            'password': 'Test@12345',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
        self.assertIn('user', response.data)

    def test_login_wrong_password(self):
        """ Noto'g'ri parol bilan login bo'lib bo'lmaydi """
        response = self.client.post(self.url, {
            'username': 'loginuser',
            'password': 'WrongPassword',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login_wrong_username(self):
        """ Mavjud bo'lmagan username bilan login bo'lib bo'lmaydi """
        response = self.client.post(self.url, {
            'username': 'nouser',
            'password': 'Test@12345',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login_empty_fields(self):
        """ Bo'sh maydonlar bilan login bo'lib bo'lmaydi """
        response = self.client.post(self.url, {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login_returns_valid_jwt(self):
        """ Qaytgan access token haqiqiy JWT ekanligini tekshirish """
        response = self.client.post(self.url, {
            'username': 'loginuser',
            'password': 'Test@12345',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # JWT 3 qismdan iborat bo'ladi: header.payload.signature
        access = response.data.get('access', '')
        self.assertEqual(len(access.split('.')), 3)


# =====================================================================
# 4. LOGOUT TESTLAR
# =====================================================================

class UserLogoutTest(APITestCase):

    def setUp(self):
        self.url = reverse('logout')
        self.user = create_user(username='logoutuser', password='Test@12345')
        refresh = RefreshToken.for_user(self.user)
        self.refresh_token = str(refresh)
        self.access_token = str(refresh.access_token)

    def test_logout_success(self):
        """ Token bilan logout bo'lish """
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
        response = self.client.post(self.url, {
            'refresh': self.refresh_token
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_logout_without_token(self):
        """ Token bo'lmasa logout bo'lib bo'lmaydi (401) """
        response = self.client.post(self.url, {
            'refresh': self.refresh_token
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_logout_used_token_again(self):
        """ Blacklist ga tushgan tokenni qayta ishlatib bo'lmaydi """
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
        # Birinchi logout
        self.client.post(self.url, {'refresh': self.refresh_token}, format='json')
        # Ikkinchi marta xato berishi kerak
        response = self.client.post(self.url, {'refresh': self.refresh_token}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


# =====================================================================
# 5. CHANGE PASSWORD TESTLAR
# =====================================================================

class UserChangePasswordTest(APITestCase):

    def setUp(self):
        self.url = reverse('change-password')
        self.user = create_user(username='changepassuser', password='OldPass@123')
        refresh = RefreshToken.for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {str(refresh.access_token)}')

    def test_change_password_success(self):
        """ To'g'ri ma'lumotlar bilan parolni o'zgartirish """
        response = self.client.post(self.url, {
            'current_password': 'OldPass@123',
            'password': 'NewPass@456',
            'password2': 'NewPass@456',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Yangi parol bilan login bo'lishni tekshirish
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('NewPass@456'))

    def test_change_password_wrong_current(self):
        """ Joriy parol noto'g'ri bo'lsa xato berishi kerak """
        response = self.client.post(self.url, {
            'current_password': 'WrongOldPass',
            'password': 'NewPass@456',
            'password2': 'NewPass@456',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_change_password_mismatch(self):
        """ Yangi parollar mos kelmasa xato berishi kerak """
        response = self.client.post(self.url, {
            'current_password': 'OldPass@123',
            'password': 'NewPass@456',
            'password2': 'DifferentPass@789',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_change_password_unauthenticated(self):
        """ Token bo'lmasa parol o'zgartirb bo'lmaydi """
        self.client.credentials()  # Tokenni olib tashlash
        response = self.client.post(self.url, {
            'current_password': 'OldPass@123',
            'password': 'NewPass@456',
            'password2': 'NewPass@456',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


# =====================================================================
# 6. PERMISSION VA ROLE TESTLAR
# =====================================================================

class WorkerPermissionTest(TestCase):

    def setUp(self):
        self.perm1 = Permission.objects.create(name='Mahsulot qo\'shish', code='product.add')
        self.perm2 = Permission.objects.create(name='Mahsulot o\'chirish', code='product.delete')
        self.role = Role.objects.create(name='Menejer', code='manager')
        self.role.permissions.add(self.perm1)

        self.user = create_user(username='workeruser')
        self.worker = Worker.objects.create(user=self.user, role=self.role)

    def test_worker_has_role_permission(self):
        """ Rol orqali berilgan permission ishlashini tekshirish """
        self.assertTrue(self.worker.has_permission('product.add'))

    def test_worker_no_permission(self):
        """ Berilmagan permission False qaytarishini tekshirish """
        self.assertFalse(self.worker.has_permission('product.delete'))

    def test_worker_extra_permission(self):
        """ Extra (individual) permission ishlashini tekshirish """
        self.worker.extra_permissions.add(self.perm2)
        self.assertTrue(self.worker.has_permission('product.delete'))

    def test_worker_no_role(self):
        """ Role yo'q bo'lsa permission False qaytarishi kerak """
        self.worker.role = None
        self.worker.save()
        self.assertFalse(self.worker.has_permission('product.add'))

    def test_get_permissions_combines_role_and_extra(self):
        """ get_permissions() rol va extra permissionlarni birlashtirishi kerak """
        self.worker.extra_permissions.add(self.perm2)
        all_perms = self.worker.get_permissions()
        codes = {p.code for p in all_perms}
        self.assertIn('product.add', codes)
        self.assertIn('product.delete', codes)
