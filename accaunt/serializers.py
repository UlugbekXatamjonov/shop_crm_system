from django.utils.encoding import smart_str, force_bytes, DjangoUnicodeDecodeError
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth import authenticate

from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken, TokenError

from .models import CustomUser, Worker, Role, Permission
from .utils import Util



""" Serialization for CustomUser Authentification """
class UserRegistrationSerializer(serializers.ModelSerializer):
    
  # Ro'yhatdan o'tish vaqtida parolni tekshirish uchun password2 maydoni yaratib olindi
    password2 = serializers.CharField(style={'input_type':'password'}, write_only=True)
    class Meta:
        model = CustomUser
        fields = (
            "password",
            "password2", 
            "first_name",
            "last_name",
            "email",
            "username",
            "phone1",
            "phone2",
            )
        extra_kwargs={
        'password':{'write_only':True}
        }

    # parollarni validatsiyadan o'tkazish va bir biriga mosligini tekshirib chiqamiz
    def validate(self, attrs):
        password = attrs.get('password')
        password2 = attrs.get('password2')
        if password != password2:
            raise serializers.ValidationError("Kiritilgan parollar birxil emas !!!")
        return attrs

    def create(self, validate_data):
        validate_data.pop('password2') 
        return CustomUser.objects.create_user(**validate_data)


class UserLoginSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=15)
    password = serializers.CharField(max_length=128, write_only=True)

    def validate(self, attrs):
        username = attrs.get('username')
        password = attrs.get('password')

        # Foydalanuvchini username va password orqali autentifikatsiya qilishi kerak
        user = authenticate(username=username, password=password)
        if not user:
            raise serializers.ValidationError("Username yoki parol noto'g'ri !")
        attrs['user'] = user
        return attrs
      
        
class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()

    # Tokenni blacklist ga qo'shish
    def validate(self, attrs):
        self.token = attrs['refresh']
        return attrs

    def save(self, **kwargs):
        try:
            token = RefreshToken(self.token)
            token.blacklist()
        except Exception as e:
            raise serializers.ValidationError("Tokenni blacklist ga qo'shib bo'lmadi, yoki bu token avval ishlatilgan !")
      

class UserChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(max_length=255, style={'input_type':'password'}, write_only=True)
    password = serializers.CharField(max_length=255, style={'input_type':'password'}, write_only=True)
    password2 = serializers.CharField(max_length=255, style={'input_type':'password'}, write_only=True)

    class Meta:
        fields = ['current_password', 'password', 'password2']

    def validate_current_password(self, value):
        user = self.context.get('user')
        if not user.check_password(value):
            raise serializers.ValidationError("Joriy parol noto'g'ri kiritildi !")
        return value

    def validate(self, attrs):
        password = attrs.get('password')
        password2 = attrs.get('password2')
        if password != password2:
            raise serializers.ValidationError("Kiritilgan parollar bir xil emas !")
        user = self.context.get('user')
        user.set_password(password)
        user.save()
        return attrs


class SendPasswordResetEmailSerializer(serializers.Serializer):
    email = serializers.EmailField(max_length=255)
    class Meta:
        fields = ['email']

    def validate(self, attrs):
        email = attrs.get('email')
        # print(f"attrs ---- {email}")
        
        if CustomUser.objects.filter(email=email).exists():
            user = CustomUser.objects.get(email = email)
            # print(f"user ---- {user.email}")
            uid = urlsafe_base64_encode(force_bytes(user.id))
            # print("--------------------------------------------------------------------------------")
            # print('Encoded UID', uid)
            token = PasswordResetTokenGenerator().make_token(user)
            # print('Password Reset Token', token)
            link = 'http://localhost:3000/api/user/reset/'+uid+'/'+token
            # print('Password Reset Link', link)
            # print("-------------------------------------------------------------------------------")
            # Send EMail
            body = 'Parolingizni tiklash uchun quyidagi havolani bosing '+link
            data = {
                'subject':'Reset Your Password',
                'body':body,
                'to_email':user.email
            }
            Util.send_email(data)
            return attrs
        else:
            raise serializers.ValidationError("Siz ro'yhatdan o'tmagansiz")


class UserPasswordResetSerializer(serializers.Serializer):
    password = serializers.CharField(max_length=255, style={'input_type':'password'}, write_only=True)
    password2 = serializers.CharField(max_length=255, style={'input_type':'password'}, write_only=True)
    class Meta:
        fields = ['password', 'password2']

    def validate(self, attrs):
        try:
            password = attrs.get('password')
            password2 = attrs.get('password2')
            uid = self.context.get('uid')
            token = self.context.get('token')
            if password != password2:
                raise serializers.ValidationError("Password and Confirm Password doesn't match")
            id = smart_str(urlsafe_base64_decode(uid))
            user = CustomUser.objects.get(id=id)
            if not PasswordResetTokenGenerator().check_token(user, token):
                raise serializers.ValidationError('Token is not Valid or Expired')
            user.set_password(password)
            user.save()
            return attrs
        except (DjangoUnicodeDecodeError, CustomUser.DoesNotExist):
            raise serializers.ValidationError('Token is not Valid or Expired')
     
  
  
  
""" ---------------- Serialization for User ---------------- """
class Worker_Profile_Serializer(serializers.ModelSerializer): 
    """ User login bo'lganda, tokenga qo'shimcha ravishda uning ma'lumotlarini yuborish uchun serializer """
    
    class Meta:
        model = Worker
        fields = '__all__'
        # fields = (
        #     "id",
        #     # "user__first_name",
        #     "role",
        #     "extra_permissions",
        #     "store",
        #     "branch",
        #     "salary",
        #     "status",           
        # )  
        
        
class CustomUser_Profile_Serializer(serializers.ModelSerializer): 
    """ User login bo'lganda, tokenga qo'shimcha ravishda uning ma'lumotlarini yuborish uchun serializer """
    worker = Worker_Profile_Serializer(many=True, read_only=True)
    
    class Meta:
        model = CustomUser
        fields = (
            "id",
            "username",
            "first_name",
            "last_name",
            "email",
            "phone1",
            "phone2",
            "status",
            'worker'         
        )
        

    
  
# class CustomUser_Create_Serializer(serializers.ModelSerializer):
#   """
#   OnetoOneField bog'lanish bo'yicha ulangan modellarda O'qtuvchi, Xodim, O'quvchi, Ota-ona ni qo'shish vaqtida,
#   CustomUser ni ham yaratib ketish uchun ushbu serializerdan foydalanildi.
#   """
  
#   class Meta:
#       model = CustomUser
#       fields = ['passport', 'password', 'email', 'first_name', 'last_name', 'date_of_bith', 'phone1', 'phone2', 
#                   'gender', 'personal_status', 'address', 'status']


# class CustomUser_List_Serializer(serializers.ModelSerializer):
#   """
#   OnetoOneField bog'lanish bo'yicha ulangan modellarda O'qtuvchi, Xodim, O'quvchi, Ota-ona ning malumotlarini olish
#     uchun ushbu serializerdan foydalanildi.
#   """
  
#   class Meta:
#       model = CustomUser
#       fields = ['id','passport', 'first_name', 'last_name', 'date_of_bith', 'phone1', 'phone2', 
#                   'gender', 'personal_status', 'status']


# class CustomUser_datas_for_Teachers_list_Serializer(serializers.ModelSerializer):
#   """
#   OnetoOneField bog'lanish bo'yicha ulangan O'quvchi malumotlarini Teachers list bo'limiga olish
#   uchun ushbu serializerdan foydalanildi.
#   """
  
#   class Meta:
#       model = CustomUser
#       fields = ['first_name', 'last_name','phone1', 'phone2', 
#                 'gender', 'personal_status', 'status']
      
      
      
