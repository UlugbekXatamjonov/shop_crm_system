from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.validators import RegexValidator
from django.utils.text import slugify
from django.utils.html import mark_safe

from store.models import Store, Branch

# Create your models here.

phone_regex = RegexValidator(regex=r'^\+998\d{9}$', message="Telefon raqami '+998991234567' formatida kiritilishi kerak.")

STATUS_CHOICES = (
    ('active', 'Active'),
    ('deactive', 'Deactive'),
)

PERSONAL_STATUS = [
        ("director", "Direktor"),
        ("manager", "Mudir"),
        
        ("assistant", "Kotiba"),
        ("worker", "Oddiy hodim"),
        
        ('teacher',"O'qtuvchi"),
        ('assistant_teacher',"Asistent o'qtuvchi"),
        
        ('father',"Ota-ona"),
        ('student',"O'quvchi"),
]


class UserManager(BaseUserManager):
    def create_user(self, first_name, last_name, email, username, is_superuser, is_staff,
                    phone1, phone2,
                    password=None): 

        if not username:
            raise ValueError("Foydalanuvchida 'username' bo'lishi shart !")
        
        user = self.model(
            first_name=first_name,
            last_name=last_name,
            email = email,
            username = username,  
            is_superuser = is_superuser,
            is_staff = is_staff,
            
            phone1 = phone1,
            phone2 = phone2,

        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, username, password=None):

        user = self.create_user(
            password=password,
            first_name='Admin',
            last_name='Padmin',
            email = email,
            username = username, 
            is_superuser = 1,
            is_staff = 1,
            
            phone1 = '998990000000',
            phone2 = '998990000001',
        )
        user.is_admin = True
        user.save(using=self._db)
        return user


class CustomUser(AbstractUser):
    """
    User modeliga qo'shimcha maydonlar qo'shildi.
    - phone1: Telefon raqam uchun
    - phone2: Telefon raqam uchun
    - status: Foydalanuvchi statusi (aktiv yoki yo'q).
    - created_at, updated_at: Ro'yxatga olish va yangilanish vaqti. 
    """
    
    phone1 = models.CharField(validators=[phone_regex], max_length=13, verbose_name="Telefon raqam")
    phone2 = models.CharField(validators=[phone_regex], max_length=13, null=True, blank=True, verbose_name="Telefon raqam")
    
    status = models.BooleanField(default=True, verbose_name="Holati")
    created_on = models.DateTimeField(auto_now_add=True)
    
    # username = None
    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['email', ]
    
    objects = UserManager()
    
    def __str__(self):
        return f"{self.first_name} {self.last_name}"



