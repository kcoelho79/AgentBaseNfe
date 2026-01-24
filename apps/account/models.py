from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models


class UserManager(BaseUserManager):
    '''Manager customizado para User com email como identificador.'''

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('O email é obrigatório')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    '''
    Usuário customizado com autenticação por email.
    Cada usuário pertence a uma contabilidade (tenant).
    '''
    username = None
    email = models.EmailField('e-mail', unique=True)

    contabilidade = models.ForeignKey(
        'contabilidade.Contabilidade',
        on_delete=models.CASCADE,
        related_name='usuarios',
        null=True,
        blank=True,
        verbose_name='contabilidade'
    )

    ROLE_CHOICES = [
        ('admin', 'Administrador'),
        ('gerente', 'Gerente'),
        ('atendente', 'Atendente'),
    ]
    role = models.CharField(
        'função',
        max_length=20,
        choices=ROLE_CHOICES,
        default='atendente'
    )

    phone = models.CharField('telefone', max_length=20, blank=True)

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    class Meta:
        verbose_name = 'usuário'
        verbose_name_plural = 'usuários'

    def __str__(self):
        return self.email
