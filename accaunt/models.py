from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.validators import RegexValidator
from django.utils.text import slugify
from django.utils.html import mark_safe


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
        
        # ("cook", "Oshpaz"),
        # ("kitchen_staff", "Oshxona hodimi"),
        # ("cleaner", "Tozalovchi"),
        # ("guard", "Qorovul"),
]


class UserManager(BaseUserManager):
    def create_user(self, first_name, last_name, email, 
                    passport, date_of_bith, phone1, phone2, gender, address, personal_status,
                    password=None): 

        if not passport:
            raise ValueError("Foydalanuvchida 'passport' bo'lishi shart !")
        user = self.model(
            first_name=first_name,
            last_name=last_name,
            email = email,
            passport = passport, 
            date_of_bith = date_of_bith,
            phone1 = phone1,
            phone2 = phone2,
            gender = gender,
            address = address,
            personal_status = personal_status
        )
        user.set_password(password)
        user.save(using=self._db)
        return user


    """ ❗❗❗ Bazani toza qilib yangi superadmin yaratgandan keyin, 
    bazani ochib is_superuser va is_staff maydoniga 1 qiymatini berish kerak  ❗❗❗ """
    def create_superuser(self, email, passport, password=None):

        user = self.create_user(
            password=password,
            first_name='Admin',
            last_name='Padmin',
            email = email,
            passport = passport, 
            date_of_bith = "2000-01-01", # bu xuddi shu YYYY-MM-DD formatda bo'lishi shart ! 
            phone1 = '998990000000',
            phone2 = '998990000001',
            gender = "male",
            address = "Address",
            personal_status = 'director'
        )
        user.is_admin = True
        user.save(using=self._db)
        return user



class CustomUser(AbstractUser):
    """
    Foydalanuvchi modeliga qo'shimcha maydonlar qo'shildi.
    - passport: Foydalanuvchining pasport/tug'ilganlik haqida guvohnoma raqami.
    - date_of_bith: Tug'ilgan sanasi.
    - phone1, phone2: Aloqa telefon raqamlari (validator bilan tekshirilgan).
    - gender: Foydalanuvchining jinsi Erkak/Ayol (tanlov bilan).
    - address: Foydalanuvchining manzili.
    - status: Foydalanuvchi statusi (aktiv yoki yo'q).
    - created_at, updated_at: Ro'yxatga olish va yangilanish vaqti. 
    """
    

    passport = models.CharField(max_length=15, unique=True, null=True, blank=True, verbose_name="Passport")
    phone1 = models.CharField(validators=[phone_regex], max_length=13, null=True, blank=True, verbose_name="Telefon raqam")
    phone2 = models.CharField(validators=[phone_regex], max_length=13, null=True, blank=True, verbose_name="Telefon raqam")
    personal_status = models.CharField(max_length=30, null=True, blank=True, choices=PERSONAL_STATUS, default="teacher", verbose_name="Shaxsiy status")
    salary = models.PositiveIntegerField()
    store = models.ForeignKey()
    branch = models.ForeignKey()


    status = models.BooleanField(default=True, verbose_name="Holati")
    created_on = models.DateTimeField(auto_now_add=True)
    
    # username = None
    USERNAME_FIELD = 'passport'
    REQUIRED_FIELDS = ['email', ]
    
    
    
    objects = UserManager()
    
    def __str__(self):
        return f"{self.first_name} {self.last_name}"



