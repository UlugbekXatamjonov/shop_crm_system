from django.contrib.auth.backends import ModelBackend
from .models import CustomUser

class CustomBackend(ModelBackend):
    def authenticate(self, request, passport=None, password=None, **kwargs):
        try:
            # Foydalanuvchini passport orqali olish
            user = CustomUser.objects.get(passport=passport)
            if user.check_password(password):
                return user
        except CustomUser.DoesNotExist:
            return None
