from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    username = models.CharField(
        max_length=150,
        verbose_name="ユーザー名",
    )
    email = models.EmailField(
        unique=True,
        verbose_name="メールアドレス" 
    )

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    def __str__(self) -> str:
        return self.email or self.username