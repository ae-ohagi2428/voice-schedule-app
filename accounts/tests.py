from django.test import TestCase

from .factories import UserFactory


class UserFactoryTest(TestCase):
    def test_create_user(self):
        user = UserFactory()
        self.assertTrue(user.email.endswith('@example.com'))
        self.assertTrue(user.check_password('password123'))

    def test_emails_are_unique(self):
        user1 = UserFactory()
        user2 = UserFactory()
        self.assertNotEqual(user1.email, user2.email)