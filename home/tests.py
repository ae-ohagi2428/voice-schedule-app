from django.test import TestCase
from django.urls import reverse

from accounts.factories import UserFactory


class HomeViewTest(TestCase):
    def setUp(self):
        self.user = UserFactory()
        self.url = reverse('home:index')

    def test_shows_speech_unsupported_notice(self):
        # 音声入力非対応のブラウザ向けのお知らせと、speech-support.jsがある
        response = self.client.get(self.url)
        self.assertContains(response, 'id="speech-unsupported"')
        self.assertContains(response, 'speech-support.js')

    def test_shows_sound_notice_and_qr_code(self):
        # 音量のお知らせとQRコードがある
        response = self.client.get(self.url)
        self.assertContains(response, 'id="sound-notice"')
        self.assertContains(response, 'qr_code.webp')
    
    def test_shows_character(self):
        # るるるとcharacter.js・home.jsがある
        response = self.client.get(self.url)
        self.assertContains(response, 'id="chara"')
        self.assertContains(response, 'character.js')
        self.assertContains(response, 'home.js')

    def test_logged_out_shows_register_and_login(self):
        # ログアウト中：「新規登録」・「ログイン」ボタンがあり、ダッシュボードはない
        response = self.client.get(self.url)
        self.assertContains(response, f'href="{reverse("accounts:register")}"')
        self.assertContains(response, f'href="{reverse("accounts:login")}"')
        self.assertNotContains(response, f'href="{reverse("schedules:dashboard")}"')
    
    def test_logged_in_shows_dashboard(self):
        # ログイン中：「ダッシュボード」ボタンがあり、「新規登録」ボタンはない
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertContains(response, f'href="{reverse("schedules:dashboard")}"')
        self.assertNotContains(response, f'href="{reverse("accounts:register")}"')

    def test_shows_screenshots(self):
        # スクリーンショット2枚が入っている
        response = self.client.get(self.url)
        self.assertContains(response, 'dashboard_image.webp')
        self.assertContains(response, 'task_run_image.webp')