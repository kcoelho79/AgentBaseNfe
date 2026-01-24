from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model

User = get_user_model()


class EmailBackend(ModelBackend):
    '''Backend de autenticação usando email ao invés de username.'''

    def authenticate(self, request, username=None, email=None, password=None, **kwargs):
        # Aceita tanto 'username' quanto 'email' para compatibilidade com Django Admin
        email = email or username
        if not email:
            return None

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return None

        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
