from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.validators import RegexValidator
from django.utils.text import slugify
from django.utils.html import mark_safe

from store.models import Store, Branch

# Create your models here.

phone_regex = RegexValidator(regex=r'^\+998\d{9}$', message="Telefon raqami '+998991234567' formatida kiritilishi kerak.")


WORKER_STATUS = (
    ('active',"Active"),
    ('deactive',"Deactive"),
)

class UserManager(BaseUserManager):
    def create_user(self, username, email, phone1, password=None,
                first_name='', last_name='', 
                is_superuser=False, is_staff=False, phone2=None): 

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
            
            phone1 = '+998990000000',
            phone2 = '+998990000001',
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



""" ------------------- Permissions ------------------- """
class Permission(models.Model):
    """ Frontend va backend uchun permissionlar """

    name = models.CharField(max_length=100)
    code = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.code
    

class Role(models.Model):
    """ Hodimlarning rol lari """
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=50, unique=True)
    permissions = models.ManyToManyField(
        Permission, 
        related_name='roles', 
        blank=True
    )

    def __str__(self):
        return self.name


class Worker(models.Model):
    """ Do'konda ishlovchi xodim """

    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE)
    role = models.ForeignKey(
        Role,
        on_delete=models.SET_NULL,
        null=True,
        related_name='workers'
    )

    # Maxsus individual permissionlar (role’dan tashqari)
    extra_permissions = models.ManyToManyField(
        Permission,
        blank=True,
        related_name='workers'
    )

    store = models.ForeignKey(
        Store, 
        on_delete=models.CASCADE, 
        related_name='workers',
        null=True,
        blank=True

    )

    branch = models.ForeignKey(
        Branch, 
        on_delete=models.CASCADE, 
        related_name='workers',
        null=True,
        blank=True

    )

    salary = models.DecimalField(max_digits=12, decimal_places=2, default=100)
    
    status = models.CharField(max_length=10, choices=WORKER_STATUS, default='active')
    created_on = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.first_name} {self.user.last_name}"

    def get_permissions(self):
        role_permissions = self.role.permissions.all() if self.role else Permission.objects.none()
        extra_permissions = self.extra_permissions.all()
        return set(role_permissions) | set(extra_permissions)

    def has_permission(self, code):
        return any(p.code == code for p in self.get_permissions())










