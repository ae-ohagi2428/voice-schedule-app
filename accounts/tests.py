from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.test import TestCase
from django.urls import reverse

from schedules.models import Setting

from .factories import UserFactory

User =get_user_model()

class UserFactoryTest(TestCase):
    def test_create_user(self):
        user = UserFactory()
        self.assertTrue(user.email.endswith('@example.com'))
        self.assertTrue(user.check_password('password123'))

    def test_emails_are_unique(self):
        user1 = UserFactory()
        user2 = UserFactory()
        self.assertNotEqual(user1.email, user2.email)

class UserModelTest(TestCase):
    def test_email_must_be_unique(self):
        UserFactory(email='same@example.com')

        with self.assertRaises(IntegrityError):
            UserFactory(email='same@example.com')

    def test_password_must_be_hashed(self):
        user = UserFactory(password='password123')

        self.assertNotEqual(user.password, 'password123')
        self.assertTrue(user.check_password('password123'))

    def test_can_login_with_email(self):
        UserFactory(email='login@example.com', password='password123')

        self.assertTrue(
            self.client.login(username='login@example.com', password='password123')
        )

    def test_register_creates_setting(self):
        user_data = {
            'username': 'テストユーザー',
            'email': 'register@example.com',
            'password1': 'Tokiyomi2026!',
            'password2': 'Tokiyomi2026!'
        }
        self.client.post(reverse('accounts:register'), user_data)
        user = User.objects.get(email='register@example.com')
        self.assertTrue(Setting.objects.filter(user=user).exists())


