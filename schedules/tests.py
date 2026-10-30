import json
from datetime import datetime, time, timedelta
from unittest.mock import patch

import httpx
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from pydantic import ValidationError

from accounts.factories import UserFactory
from schedules.formatting import (
    correct_end,
    correct_start,
    format_schedules,
    round_up_to_5min,
    to_datetime,
)

from .ai import ScheduleItem, ScheduleList
from .factories import ScheduleFactory
from .forms import ScheduleEditForm
from .models import Schedule, Setting
from .status import get_schedule_status
from .usage import get_today_usage

NOW = timezone.make_aware(datetime(2026, 10, 1, 15, 5))

class ScheduleFactoryTest(TestCase):
    def test_create_schedule(self):
        schedule = ScheduleFactory()
        self.assertLess(schedule.start_at, schedule.end_at)
        self.assertIsNotNone(schedule.user)

class ScheduleItemValidationTest(SimpleTestCase):
    def test_valid_time_passes(self):
        item = ScheduleItem(title='カフェ', start='15:00', end=None, duration_minutes=None)
        self.assertEqual(item.start, '15:00')

    def test_invalid_start_time_raises_error(self):
        with self.assertRaises(ValidationError):
            ScheduleItem(title='カフェ', start='25:00', end=None, duration_minutes=None)

    def test_invalid_end_time_raises_error(self):
        with self.assertRaises(ValidationError):
            ScheduleItem(title='ヨガ', start=None, end='25:00', duration_minutes=None)

    def test_start_invalid_format_raises_error(self):
        with self.assertRaises(ValidationError):
            ScheduleItem(title='勉強', start='15時', end=None, duration_minutes=None)

    def test_end_invalid_format_raises_error(self):
        with self.assertRaises(ValidationError):
            ScheduleItem(title='外出', start=None, end='18時', duration_minutes=None)

    def test_valid_title_passes(self):
        item = ScheduleItem(title='予定あり', start=None, end=None, duration_minutes=None)
        self.assertEqual(item.title, '予定あり')

    def test_empty_title_is_complemented(self):
        item = ScheduleItem(title='', start=None, end=None, duration_minutes=None)
        self.assertEqual(item.title, '(名前なし)')

    def test_valid_duration_minutes_passes(self):
        item = ScheduleItem(title='皿洗い', start=None, end=None, duration_minutes=15)
        self.assertEqual(item.duration_minutes, 15)

    def test_none_duration_minutes_passes(self):
        item = ScheduleItem(title='図書館', start=None, end=None, duration_minutes=None)
        self.assertIsNone(item.duration_minutes)

    def test_zero_duration_minutes_becomes_none(self):
        item = ScheduleItem(title='買い物', start=None, end=None, duration_minutes=0)
        self.assertIsNone(item.duration_minutes)

    def test_minus_duration_minutes_becomes_none(self):
        item = ScheduleItem(title='Pythonの勉強', start=None, end=None, duration_minutes=-10)
        self.assertIsNone(item.duration_minutes)

    def test_dm_over_1440_becomes_1440(self):
        item = ScheduleItem(title='旅行', start=None, end=None, duration_minutes=1441)
        self.assertEqual(item.duration_minutes, 1440)

    def test_dm_equal_1440_passes(self):
        item = ScheduleItem(title='出張', start=None, end=None, duration_minutes=1440)
        self.assertEqual(item.duration_minutes, 1440)


class FormattingFunctionTest(SimpleTestCase):
    # to_datetime
    def test_to_datetime_converts_time_string(self):
        dt = NOW.replace(hour=15, minute=0, second=0, microsecond=0)
        self.assertEqual(to_datetime('15:00', NOW), dt)

    def test_to_datetime_returns_none_for_none(self):
        self.assertIsNone(to_datetime(None, NOW))

    # round_up_to_5min
    def test_round_up_to_5min_rounds_up(self):
        dt = NOW.replace(hour=14, minute=7)
        self.assertEqual(
            round_up_to_5min(dt),
            NOW.replace(hour=14, minute=10, second=0, microsecond=0)
        )

    def test_round_up_to_5min_keeps_exact_5min(self):
        dt = NOW.replace(hour=14, minute=10)
        self.assertEqual(round_up_to_5min(dt), dt)

    def test_round_up_to_5min_carries_over_to_next_hour(self):
        dt = NOW.replace(hour=14, minute=58)
        self.assertEqual(
            round_up_to_5min(dt),
            NOW.replace(hour=15, minute=0,  second=0, microsecond=0)
        )

    # correct_start
    def test_correct_start_keeps_time_within_1_hour_before(self):
        dt = NOW.replace(hour=14, minute=30)
        self.assertEqual(correct_start(dt, NOW), dt)

    def test_correct_start_adds_12_hours_to_morning_time(self):
        dt = NOW.replace(hour=10, minute=0)
        self.assertEqual(
            correct_start(dt, NOW),
            NOW.replace(hour=22, minute=0, second=0, microsecond=0)  
        )

    def test_correct_start_returns_none_for_none(self):
        self.assertIsNone(correct_start(None, NOW))

    # correct_end
    def test_correct_end_adds_12_hours(self):
        start = NOW.replace(hour=22, minute=30)
        end = NOW.replace(hour=11, minute=0)
        self.assertEqual(correct_end(start, end), NOW.replace(hour=23, minute=0))
    
    def test_correct_end_adds_1_day_when_crossing_midnight(self):
        start = NOW.replace(hour=23, minute=0)
        end = NOW.replace(hour=1, minute=0)
        self.assertEqual(
            correct_end(start, end),
            NOW.replace(hour=1, minute=0) + timedelta(days=1)
        )

    def test_correct_end_keeps_same_time_as_start(self):
        start = NOW.replace(hour=12, minute=0)
        end = NOW.replace(hour=12, minute=0)
        self.assertEqual(correct_end(start, end), end)

class FormatSchedulesTest(SimpleTestCase):
    def test_case6_corrected(self):
        schedules = [
            ScheduleItem(title='テレビを見る', start='10:00', end=None, duration_minutes=30),
            ScheduleItem(title='風呂に入る', start=None, end='11:00', duration_minutes=None),
        ]
        result = format_schedules(schedules, NOW)
        self.assertEqual(result[0]['start'], NOW.replace(hour=22, minute=0, second=0, microsecond=0))
        self.assertEqual(result[0]['end'], NOW.replace(hour=22, minute=30, second=0, microsecond=0))
        self.assertEqual(result[1]['start'], NOW.replace(hour=22, minute=30, second=0, microsecond=0))
        self.assertEqual(result[1]['end'], NOW.replace(hour=23, minute=0, second=0, microsecond=0))

    def test_first_start_none_uses_rounded_now(self):
        now = NOW.replace(minute=7)
        schedules = [
            ScheduleItem(title='買い物', start=None, end='16:00', duration_minutes=None),
            ScheduleItem(title='掃除', start='17:00', end='18:00', duration_minutes=None)
        ]
        result = format_schedules(schedules, now)
        self.assertEqual(result[0]['start'], NOW.replace(minute=10, second=0, microsecond=0))
        
    def test_sorted_by_start_time(self):
        now = NOW.replace(hour=6, minute=30)
        schedules = [
            ScheduleItem(title='勉強', start='07:00', end='08:00', duration_minutes=None),
            ScheduleItem(title='洗濯を回す', start='10:00', end=None, duration_minutes=60),
            ScheduleItem(title='病院の予約', start='09:00', end=None, duration_minutes=60)
        ]
        result = format_schedules(schedules, now)
        self.assertEqual(result[0]['title'], '勉強')
        self.assertEqual(result[1]['title'], '病院の予約')
        self.assertEqual(result[2]['title'], '洗濯を回す')

    def test_last_end_none_becomes_start_plus_1_hour(self):
        schedules = [
            ScheduleItem(title='夜ご飯を作る', start='18:00', end='19:00', duration_minutes=None),
            ScheduleItem(title='夜ご飯', start='19:00', end=None, duration_minutes=None)
        ]
        result = format_schedules(schedules, NOW)
        self.assertEqual(result[1]['end'], NOW.replace(hour=20, minute=0))

    def test_same_start_and_end_adds_1_minute(self):
        schedules = [
            ScheduleItem(title='炊飯予約', start='17:00', end='17:00', duration_minutes=None),
        ]
        result = format_schedules(schedules, NOW)
        self.assertEqual(result[0]['end'], NOW.replace(hour=17, minute=1))

class ScheduleEditViewTest(TestCase):
    def setUp(self):
        self.user = UserFactory()
        self.url = reverse('schedules:edit')
    
    def test_redirects_when_not_logged_in(self):
    # ログインしていない状態で開く→ログインページへ移動する
        response = self.client.get(self.url)
        self.assertRedirects(response, f"{reverse('accounts:login')}?next={self.url}")
        

    def test_shows_today_own_schedules(self):
    # 今日の自分の予定がある→表示される
        now = timezone.localtime()
        ScheduleFactory(
            user=self.user,
            title='カフェ',
            start_at=now,
            end_at=now + timedelta(hours=1),
        )
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        titles = [form['title'].value() for form in response.context['formset']]
        self.assertEqual(titles, ['カフェ'])

    def test_hides_other_day_and_other_user_schedules(self):
    # 昨日の予定・ほかの人の予定がある→表示されない
        now = timezone.localtime().replace(minute=0, second=0, microsecond=0)
        yesterday = now - timedelta(days=1)
        other_user = UserFactory()
        
        ScheduleFactory(
            user=self.user,
            title='今日の予定',
            start_at=now,
            end_at=now + timedelta(hours=1),
        )
        ScheduleFactory(
            user=self.user,
            title='昨日の予定',
            start_at=yesterday,
            end_at=yesterday + timedelta(hours=1),
        )
        ScheduleFactory(
            user=other_user,
            title='ほかの人の予定',
            start_at=now,
            end_at=now + timedelta(hours=1)
        )
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        titles = [form['title'].value() for form in response.context['formset']]
        self.assertIn('今日の予定', titles)
        self.assertNotIn('昨日の予定', titles)
        self.assertNotIn('ほかの人の予定', titles)

    def test_sorted_by_start_time(self):
    # 予定が時刻の順でない順に入っている→時刻の順に並ぶ  
        today = timezone.localtime().replace(minute=0, second=0, microsecond=0)
        ScheduleFactory(
            user=self.user,
            title='夕方',
            start_at=today.replace(hour=17),
            end_at=today.replace(hour=18),
        )
        ScheduleFactory(
            user=self.user,
            title='朝',
            start_at=today.replace(hour=9),
            end_at=today.replace(hour=10),
        )
        ScheduleFactory(
            user=self.user,
            title='昼',
            start_at=today.replace(hour=12),
            end_at=today.replace(hour=13),
        )
        self.client.force_login(self.user)

        response = self.client.get(self.url)

        titles = [form['title'].value() for form in response.context['formset']]
        self.assertEqual(titles, ['朝', '昼', '夕方'])
        

    def test_includes_new_schedules_from_session(self):
    # 新しい予定は ID がない状態で並ぶ
        today = timezone.localtime().replace(minute=0, second=0, microsecond=0)

        ScheduleFactory(
            user=self.user,
            title='既存の予定',
            start_at=today.replace(hour=9),
            end_at=today.replace(hour=10),
        )
        self.client.force_login(self.user)

        session = self.client.session
        session['new_schedules'] = [
            {
                'title': '新しい予定',
                'start_at': today.replace(hour=11).isoformat(),
                'end_at': today.replace(hour=12).isoformat(),
            },
        ]
        session['new_schedules_date'] = today.date().isoformat()
        session.save()

        response = self.client.get(self.url)

        formset = response.context['formset']
        self.assertEqual([form['title'].value() for form in formset], ['既存の予定', '新しい予定'])
        self.assertIsNotNone(formset[0].instance.pk)
        self.assertIsNone(formset[1].instance.pk)

    def test_post_saves_and_redirects(self):
        # 保存・実行画面へ移動・セッションが消える
        self.client.force_login(self.user)

        today = timezone.localtime().replace(minute=0, second=0, microsecond=0)
        session = self.client.session
        session['new_schedules'] = [{
            'title': '記事を書く',
            'start_at': today.replace(hour=10).isoformat(),
            'end_at': today.replace(hour=12).isoformat(),
        }, ]
        session['new_schedules_date'] = today.date().isoformat()
        session.save()

        data = {
            'form-TOTAL_FORMS': '1',
            'form-INITIAL_FORMS': '0',
            'form-0-title': '記事を書く',
            'form-0-start_time': '10:00',
            'form-0-end_time': '11:00',
        }

        response = self.client.post(self.url, data)
        self.assertRedirects(response, reverse('schedules:task_run'))
        self.assertTrue(
            Schedule.objects.filter(user=self.user, title='記事を書く').exists()
        )
        self.assertNotIn('new_schedules', self.client.session)

    def test_post_invalid_stays_on_page(self):
        # エラーなら保存されず編集画面に残る
        self.client.force_login(self.user)
        data = {
            'form-TOTAL_FORMS': '1',
            'form-INITIAL_FORMS': '0',
            'form-0-title': '朝ごはん',
            'form-0-start_time': '07:00',
            'form-0-end_time': '07:00',
        }
        response = self.client.post(self.url, data)
        self.assertContains(response, '開始時刻と終了時刻は一緒にはできないよ')
        self.assertFalse(
            Schedule.objects.filter(user=self.user, title='朝ごはん').exists()
        )

    def test_post_saves_unchanged_new_schedules(self):
        # 何も直さなくても新しい予定が保存される
        self.client.force_login(self.user)
        today = timezone.localtime().replace(minute=0, second=0, microsecond=0)
        session = self.client.session
        session['new_schedules'] = [{
            'title': '書類作成',
            'start_at': today.replace(hour=16).isoformat(),
            'end_at': today.replace(hour=17).isoformat(),
        }, ]
        session['new_schedules_date'] = today.date().isoformat()
        session.save()
        data = {
            'form-TOTAL_FORMS': '1',
            'form-INITIAL_FORMS': '0',
            'form-0-title': '書類作成',
            'form-0-start_time': '16:00',
            'form-0-end_time': '17:00',
        }
        self.client.post(self.url, data)
        self.assertTrue(
            Schedule.objects.filter(user=self.user, title='書類作成').exists()
        )

    def test_excludes_new_schedules_from_other_day(self):
        # セッションの日付が今日でなければ並ばない
        today = timezone.localtime().replace(minute=0, second=0, microsecond=0)
        session_date = (timezone.localdate() - timedelta(days=1)).isoformat()

        self.client.force_login(self.user)
        session = self.client.session
        session['new_schedules'] = [{
            'title': '銀行へ行く',
            'start_at': today.replace(hour=14).isoformat(),
            'end_at': today.replace(hour=15).isoformat(),
        }, ]
        session['new_schedules_date'] = session_date
        session.save()
        response = self.client.get(self.url)
        titles = [form['title'].value() for form in response.context['formset']]
        self.assertNotIn('銀行へ行く', titles)

    def test_post_add_saves_and_redirects_to_input(self):
        # 「声で予定を追加」ボタン押下→DB保存→入力ページへ推移
        self.client.force_login(self.user)

        today = timezone.localtime().replace(minute=0, second=0, microsecond=0)
        session = self.client.session
        session['new_schedules'] = [{
            'title': '風呂に入る',
            'start_at': today.replace(hour=20).isoformat(),
            'end_at': today.replace(hour=21).isoformat(),
        }, ]
        session['new_schedules_date'] = today.date().isoformat()
        session.save()

        data = {
            'form-TOTAL_FORMS': '1',
            'form-INITIAL_FORMS': '0',
            'form-0-title': '風呂に入る',
            'form-0-start_time': '20:00',
            'form-0-end_time': '21:00',
            'action': 'add'
        }

        response = self.client.post(self.url, data)
        self.assertRedirects(response, f"{reverse('schedules:input')}?mode=add")
        self.assertTrue(
            Schedule.objects.filter(user=self.user, title='風呂に入る').exists()
        )
        self.assertNotIn('new_schedules', self.client.session)


    def test_shows_links_to_input_with_mode(self):
        # 編集ページ→入力ページへのリンクについてモード付きのリンクが2つある
        today = timezone.localtime().replace(minute=0, second=0, microsecond=0)
        
        self.client.force_login(self.user)
        session = self.client.session
        session['new_schedules'] = [{
            'title': '日用品の買い出し',
            'start_at': today.replace(hour=13).isoformat(),
            'end_at': today.replace(hour=14).isoformat(),
        }, ]
        session['new_schedules_date'] = today.date().isoformat()
        session.save()

        response = self.client.get(self.url)
        self.assertContains(response, f"{reverse('schedules:input')}?mode=restart")
        self.assertContains(response, f"{reverse('schedules:input')}?mode=edit")

    def test_hides_edit_link_without_new_schedules(self):
        # 新しい予定がない場合は「声で編集」ボタンがない
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertNotContains(response, f"{reverse('schedules:input')}?mode=edit")

    def test_post_saves_manually_added_schedule(self):
        self.client.force_login(self.user)
        data = {
            'form-TOTAL_FORMS': '1',
            'form-INITIAL_FORMS': '0',
            'form-0-title': '皿洗い',
            'form-0-start_time': '21:00',
            'form-0-end_time': '21:20'
        }
        response = self.client.post(self.url, data)
        self.assertRedirects(response, reverse('schedules:task_run'))
        self.assertTrue(Schedule.objects.filter(user=self.user, title='皿洗い').exists())
        
    def test_post_ignores_deleted_new_row(self):
        # 編集ページで×を押した予定は保存されず、エラー表示もされない
        self.client.force_login(self.user)
        data = {
            'form-TOTAL_FORMS': '1',
            'form-INITIAL_FORMS': '0',
            'form-0-title': '',
            'form-0-start_time': '',
            'form-0-end_time': '',
            'form-0-DELETE': 'on'
        }
        response = self.client.post(self.url, data)
        self.assertRedirects(response, reverse('schedules:task_run'), fetch_redirect_response=False)
        self.assertFalse(Schedule.objects.filter(user=self.user).exists())

    def test_shows_add_button_and_empty_form(self):
        self.client.force_login(user=self.user)
        response = self.client.get(self.url)
        self.assertContains(response, 'add-btn')
        self.assertContains(response, 'empty-form')
        self.assertContains(response, '__prefix__')

    def test_post_deletes_marked_existing_schedule(self):
        # 既存の予定にDELETEフラグを付けると、DBから削除される
        today = timezone.localtime().replace(minute=0, second=0, microsecond=0)
        self.client.force_login(user=self.user)
        schedule = ScheduleFactory(
            user=self.user,
            title='百均に行く',
            start_at=today.replace(hour=11),
            end_at=today.replace(hour=11, minute=30)
        )
        data = {
            'form-TOTAL_FORMS': '1',
            'form-INITIAL_FORMS': '1',
            'form-0-id': str(schedule.pk),
            'form-0-title': schedule.title,
            'form-0-start_time': '11:00',
            'form-0-end_time': '11:30',
            'form-0-DELETE': 'on',
        }
        self.client.post(self.url, data)
        self.assertFalse(Schedule.objects.filter(pk=schedule.pk).exists())

    def test_hides_restart_button_without_schedules(self):
        # 予定がない場合には、編集画面に「入れなおす」ボタンが表示されない
        self.client.force_login(user=self.user)
        response = self.client.get(self.url)
        self.assertNotContains(response, 'id="restart-btn"')

    def test_post_overlap_in_formset_is_invalid(self):
        # 予定の時間が重なっている場合はエラーになり、保存されない
        self.client.force_login(self.user)
        data = {
            'form-TOTAL_FORMS': '2',
            'form-INITIAL_FORMS': '0',
            'form-0-title': '散歩',
            'form-0-start_time': '10:00',
            'form-0-end_time': '11:00',
            'form-1-title': '昼ごはん',
            'form-1-start_time': '10:30',
            'form-1-end_time': '11:30',
        }
        response = self.client.post(self.url, data)
        self.assertContains(response, '時間が重なってるみたい')
        self.assertFalse(Schedule.objects.filter(user=self.user).exists())

    def test_post_overlap_is_formset_error(self):
        # 予定の時間が重なっている場合、エラーが各予定の欄ではなく編集ページ全体のエラーとしてまとめて出る
        self.client.force_login(self.user)
        data = {
            'form-TOTAL_FORMS': '2',
            'form-INITIAL_FORMS': '0',
            'form-0-title': '散歩',
            'form-0-start_time': '10:00',
            'form-0-end_time': '11:00',
            'form-1-title': '昼ごはん',
            'form-1-start_time': '10:30',
            'form-1-end_time': '11:30',
        }
        response = self.client.post(self.url, data)
        formset = response.context['formset']
        self.assertIn(
            '散歩(10:00～11:00)と昼ごはん(10:30～11:30)の時間が重なってるみたい。重ならない時間に直してね',
            formset.non_form_errors()
        )
        for form in formset.forms:
            self.assertFalse(form.errors)

    def test_post_adjacent_schedules_are_valid(self):
        # 前の予定の終了時刻と次の予定の開始時刻が同じ場合にはエラーにならない
        self.client.force_login(self.user)
        data = {
            'form-TOTAL_FORMS': '2',
            'form-INITIAL_FORMS': '0',
            'form-0-title': '散歩',
            'form-0-start_time': '10:00',
            'form-0-end_time': '11:00',
            'form-1-title': '昼ごはん',
            'form-1-start_time': '11:00',
            'form-1-end_time': '12:00',
        }
        response = self.client.post(self.url, data)
        self.assertRedirects(response, reverse('schedules:task_run'))
        self.assertEqual(Schedule.objects.filter(user=self.user).count(), 2)
    
    def test_post_save_stays_on_edit(self):
        # 「予定を保存」ボタンで予定が保存される。画面は編集ページにとどまる
        self.client.force_login(self.user)
        data = {
            'form-TOTAL_FORMS': '1',
            'form-INITIAL_FORMS': '0',
            'form-0-title': '読書',
            'form-0-start_time': '16:00',
            'form-0-end_time': '17:00',
            'action': 'save',
        }
        response = self.client.post(self.url, data)
        self.assertRedirects(response, reverse('schedules:edit'))
        self.assertTrue(Schedule.objects.filter(user=self.user, title='読書').exists())

    def test_post_overlap_with_deleted_row_is_valid(self):
        # 時間帯が重なっている場合でも、削除された予定の場合はエラーにならず保存される
        self.client.force_login(self.user)
        data = {
            'form-TOTAL_FORMS': '2',
            'form-INITIAL_FORMS': '0',
            'form-0-title': '散歩',
            'form-0-start_time': '10:00',
            'form-0-end_time': '11:00',
            'form-1-title': '昼ごはん',
            'form-1-start_time': '10:30',
            'form-1-end_time': '11:30',
            'form-1-DELETE': 'on'
        }
        response = self.client.post(self.url, data)
        self.assertRedirects(response, reverse('schedules:task_run'))
        self.assertTrue(Schedule.objects.filter(user=self.user, title='散歩').exists())
        self.assertFalse(Schedule.objects.filter(user=self.user, title='昼ごはん').exists())

    def test_post_overlap_with_db_schedule_is_invalid(self):
        # DBにある予定と新しく送った予定の時間が重なっている場合はエラーになり、新しい予定は保存されない
        today = timezone.localtime().replace(minute=0, second=0, microsecond=0)
        self.client.force_login(user=self.user)
        ScheduleFactory(
            user=self.user,
            title='カフェへ行く',
            start_at=today.replace(hour=10),
            end_at=today.replace(hour=12),
        )
        data = {
            'form-TOTAL_FORMS': '1',
            'form-INITIAL_FORMS': '0',
            'form-0-title': 'カフェへ行く',
            'form-0-start_time': '10:00',
            'form-0-end_time': '12:00',
        }
        response = self.client.post(self.url, data)
        self.assertContains(response, '時間が重なってるみたい')
        self.assertEqual(Schedule.objects.filter(user=self.user).count(), 1)

    def test_post_overlap_with_db_schedule_shows_both_titles(self):
        # 全体のエラー文には、重なっている両方の予定の名前が出力される
        today = timezone.localtime().replace(minute=0, second=0, microsecond=0)
        self.client.force_login(user=self.user)
        ScheduleFactory(
            user=self.user,
            title='カフェへ行く',
            start_at=today.replace(hour=10),
            end_at=today.replace(hour=12),
        )
        data = {
            'form-TOTAL_FORMS': '1',
            'form-INITIAL_FORMS': '0',
            'form-0-title': '散歩',
            'form-0-start_time': '11:00',
            'form-0-end_time': '11:30',
        }
        response = self.client.post(self.url, data)
        formset = response.context['formset']
        self.assertIn(
            'カフェへ行く(10:00～12:00)と散歩(11:00～11:30)の時間が重なってるみたい。重ならない時間に直してね',
            formset.non_form_errors()
        )

    def test_shows_auto_shift_button(self):
        # 編集画面に、時刻をまとめて変更するためのボタンが置かれている
        today = timezone.localtime().replace(minute=0, second=0, microsecond=0)
        self.client.force_login(user=self.user)
        ScheduleFactory(
            user=self.user,
            title='WEB会議',
            start_at=today.replace(hour=13),
            end_at=today.replace(hour=14),
        )
        response = self.client.get(self.url)
        self.assertContains(response, 'class="auto-shift-btn')

    def test_shows_row_editor_parts(self):
        # 予定がある場合、HTMLには'row-summary'（各予定カードの閉じた状態）・'close-btn'（ＯＫボタン）・
        # 'shift-notice'（予定繰り下げメッセージ）・'overlap-error'（時間が重複した場合のエラー文の場所）・
        # 'cancel-btn'（キャンセルボタン）が入っている
        today = timezone.localtime().replace(minute=0, second=0, microsecond=0)
        self.client.force_login(user=self.user)
        ScheduleFactory(
            user=self.user,
            title='研修動画視聴',
            start_at=today.replace(hour=13),
            end_at=today.replace(hour=14),
        )
        response = self.client.get(self.url)
        self.assertContains(response, 'row-summary')
        self.assertContains(response, 'close-btn')
        self.assertContains(response, 'shift-notice')
        self.assertContains(response, 'overlap-error')
        self.assertContains(response, 'cancel-btn')

    def test_page_is_not_cached(self):
        # 編集ページではブラウザにキャッシュさせず、ブラウザの「戻る」が押された場合でも古い画面を表示しない
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertIn('no-cache', response['Cache-Control'])

class ScheduleEditFormTest(TestCase):
    def setUp(self):
        self.user = UserFactory()

    def test_same_start_and_end_is_invalid(self):
        # 開始と終了が同じならエラー
        form = ScheduleEditForm(data={'title': '外食', 'start_time': '19:00', 'end_time': '19:00'})
        self.assertFalse(form.is_valid())
        self.assertIn('開始時刻と終了時刻は一緒にはできないよ', form.non_field_errors())

    def test_save_combines_today_and_time(self):
        # 今日の日付と時刻で日時が入る
        today = timezone.localdate()
        form = ScheduleEditForm(data={'title': '散歩', 'start_time': '10:00', 'end_time': '11:00'}, user=self.user)
        self.assertTrue(form.is_valid())
        schedule = form.save()
        start_date = timezone.localdate(schedule.start_at)
        start_time = timezone.localtime(schedule.start_at).time()
        end_date = timezone.localdate(schedule.end_at)
        end_time = timezone.localtime(schedule.end_at).time()
        self.assertEqual(start_date, today)
        self.assertEqual(start_time, time(10, 0))
        self.assertEqual(end_date, today)
        self.assertEqual(end_time, time(11, 0))

    def test_save_moves_end_to_next_day(self):
        # 終了が前なら翌日になる
        today = timezone.localdate()
        next_day = today + timedelta(days=1)

        form = ScheduleEditForm(
            data={'title': '勉強', 'start_time': '23:00', 'end_time': '00:30'},
            user=self.user
        )
        self.assertTrue(form.is_valid())
        schedule = form.save()
        start_date = timezone.localdate(schedule.start_at)
        start_time = timezone.localtime(schedule.start_at).time()
        end_date = timezone.localdate(schedule.end_at)
        end_time = timezone.localtime(schedule.end_at).time()
        self.assertEqual(start_date, today)
        self.assertEqual(start_time, time(23, 0))
        self.assertEqual(end_date, next_day)
        self.assertEqual(end_time, time(0, 30))

    def test_save_sets_user_for_new_schedule(self):
        # 新しい予定に利用者が入る
        form = ScheduleEditForm(
            data={'title': 'ランニング', 'start_time': '18:00', 'end_time': '19:00'},
            user=self.user
        )
        self.assertTrue(form.is_valid())
        schedule = form.save()
        self.assertEqual(schedule.user, self.user)

    def test_empty_times_no_same_time_error(self):
        # 開始時刻・終了時刻どちらも空欄の場合に「～は一緒にはできないよ」というエラーメッセージは表示されない
        form = ScheduleEditForm(
            data={'title': '読書', 'start_time': '', 'end_time': ''},
            user=self.user
        )
        self.assertFalse(form.is_valid())
        self.assertNotIn('開始時刻と終了時刻は一緒にはできないよ', form.non_field_errors())


    def test_required_error_messages(self):
        form = ScheduleEditForm(
            data={'title': '', 'start_time': '', 'end_time': ''},
            user=self.user
        )
        self.assertFalse(form.is_valid())
        self.assertIn('タスク名を入れてね', form.errors['title'])
        self.assertIn('開始時刻を入れてね', form.errors['start_time'])
        self.assertIn('終了時刻を入れてね', form.errors['end_time'])


class ScheduleInputViewTest(TestCase):
    def setUp(self):
        self.user = UserFactory()
        self.url = reverse('schedules:input')

    def test_back_link_to_dashboard_without_mode(self):
        # URLにmodeがない場合→「もどる」でダッシュボードに遷移
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertContains(response, reverse('schedules:dashboard'))

    def test_back_link_to_edit_with_mode(self):
        # URLにmodeがある場合→「編集ページにもどる」が表示され編集ページにもどる
        self.client.force_login(self.user)
        response = self.client.get(f"{reverse('schedules:input')}?mode=edit")
        self.assertContains(response, reverse('schedules:edit'))

    def test_back_link_to_task_run_from_run(self):
        # ?mode=add&from=runで開く（実行ページ→「声で予定を追加」ボタン押下）と、
        # context['return_url']に実行ページのURLが入る
        self.client.force_login(self.user)
        response = self.client.get(f"{self.url}?mode=add&from=run")
        self.assertEqual(response.context['return_url'], reverse('schedules:task_run'))

    def test_shows_db_and_session_schedules(self):
        # mode=add の場合、画面にDBとセッションの予定が表示される
        today = timezone.localtime().replace(minute=0, second=0, microsecond=0)
        self.client.force_login(user=self.user)
        ScheduleFactory(
            user=self.user,
            title='図書館へ行く',
            start_at=today.replace(hour=10),
            end_at=today.replace(hour=12),
        )
        session = self.client.session
        session['new_schedules'] = [{
            'title': 'お昼ごはん',
            'start_at': today.replace(hour=12).isoformat(),
            'end_at': today.replace(hour=13).isoformat(),
        }, ]
        session['new_schedules_date'] = today.date().isoformat()
        session.save()
        response = self.client.get(f"{self.url}?mode=add")
        titles = [s['title'] for s in response.context['schedules']]
        self.assertIn('図書館へ行く', titles)
        self.assertIn('お昼ごはん', titles)
         
    def test_restart_hides_session_schedules(self):
        # mode='restart'の場合、セッションの予定が表示されない
        today = timezone.localtime().replace(minute=0, second=0, microsecond=0)
        self.client.force_login(user=self.user)
        ScheduleFactory(
            user=self.user,
            title='図書館へ行く',
            start_at=today.replace(hour=10),
            end_at=today.replace(hour=12),
        )
        session = self.client.session
        session['new_schedules'] = [{
            'title': 'お昼ごはん',
            'start_at': today.replace(hour=12).isoformat(),
            'end_at': today.replace(hour=13).isoformat(),
        }, ]
        session['new_schedules_date'] = today.date().isoformat()
        session.save()
        response = self.client.get(f"{reverse('schedules:input')}?mode=restart")
        titles = [s['title'] for s in response.context['schedules']]
        self.assertIn('図書館へ行く', titles)
        self.assertNotIn('お昼ごはん', titles)

    def test_hides_session_schedules_without_mode(self):
        # modeなしでURLを開いた場合、保存済みの予定は出るがセッションの予定は出ない
        today = timezone.localtime().replace(minute=0, second=0, microsecond=0)
        self.client.force_login(user=self.user)
        ScheduleFactory(
            user=self.user,
            title='外出準備',
            start_at=today.replace(hour=9),
            end_at=today.replace(hour=9, minute=20),
        )
        session = self.client.session
        session['new_schedules'] = [{
            'title': '外出',
            'start_at': today.replace(hour=9, minute=20).isoformat(),
            'end_at': today.replace(hour=12).isoformat(),
        }, ]
        session['new_schedules_date'] = today.date().isoformat()
        session.save()
        response = self.client.get(self.url)
        titles = [s['title'] for s in response.context['schedules']]
        self.assertIn('外出準備', titles)
        self.assertNotIn('外出', titles)

    def test_marks_current_and_finished_schedules(self):
        # 終わった予定はis_finishedがTrue、今の予定はis_currentがTrueになる
        now = timezone.localtime()
        self.client.force_login(self.user)
        ScheduleFactory(
            user=self.user,
            title='猫カフェ',
            start_at=now - timedelta(minutes=120),
            end_at=now - timedelta(minutes=30),
        )
        ScheduleFactory(
            user=self.user,
            title='ランチ',
            start_at=now - timedelta(minutes=30),
            end_at=now + timedelta(minutes=30),
        )
        response = self.client.get(self.url)
        schedules = response.context['schedules']
        self.assertTrue(schedules[0]['is_finished'])
        self.assertFalse(schedules[0]['is_current'])
        self.assertTrue(schedules[1]['is_current'])
        self.assertFalse(schedules[1]['is_finished'])

    def test_sets_duration_minutes(self):
        # 10時〜11時半の予定のduration_minutesが90である
        today = timezone.localtime().replace(minute=0, second=0, microsecond=0)
        self.client.force_login(self.user)
        ScheduleFactory(
            user=self.user,
            title='資格試験',
            start_at=today.replace(hour=10),
            end_at=today.replace(hour=11, minute=30),
        )
        response = self.client.get(self.url)
        schedules = response.context['schedules']
        self.assertEqual(schedules[0]['duration_minutes'], 90)
        
    def test_sets_gap_minutes_only_when_gap_exists(self):
        # 間が空いた予定にはgap_minutesが入り、すぐ次が始まる予定には入らない
        today = timezone.localtime().replace(minute=0, second=0, microsecond=0)
        self.client.force_login(self.user)
        ScheduleFactory(
            user=self.user,
            title='銀行へ行く',
            start_at=today.replace(hour=9),
            end_at=today.replace(hour=10),
        )
        ScheduleFactory(
            user=self.user,
            title='役所へ行く',
            start_at=today.replace(hour=10),
            end_at=today.replace(hour=11),
        )
        ScheduleFactory(
            user=self.user,
            title='郵便局へ行く',
            start_at=today.replace(hour=11, minute=30),
            end_at=today.replace(hour=12),
        ) 
        response = self.client.get(self.url)
        schedules = response.context['schedules']
        self.assertNotIn('gap_minutes', schedules[0])
        self.assertEqual(schedules[1]['gap_minutes'], 30)
        self.assertNotIn('gap_minutes', schedules[2])

    def test_page_is_not_cached(self):
        # ブラウザにキャッシュさせず、ブラウザの「戻る」が押された場合でも古い画面を表示しない
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertIn('no-cache', response['Cache-Control'])

class TranscriptViewTest(TestCase):
    def setUp(self):
        self.user = UserFactory()
        self.url = reverse('schedules:transcript')

    @patch('schedules.views.ask_ai')
    def test_edit_mode_passes_current_schedules(self, mock_ask_ai):
        # 編集モードなら、セッションの予定をask_aiに渡す
        today = timezone.localtime().replace(minute=0, second=0, microsecond=0)
        self.client.force_login(self.user)

        new_schedules = [{
            'title': '散歩',
            'start_at': today.replace(hour=11).isoformat(),
            'end_at': today.replace(hour=12).isoformat(),
        }, ]

        session = self.client.session
        session['new_schedules'] = new_schedules
        session['new_schedules_date'] = today.date().isoformat()
        session.save()

        mock_ask_ai.return_value = ScheduleList(schedules=[
            ScheduleItem(title='散歩', start='12:00', end='13:00', duration_minutes=None),
        ])

        # 編集モードで送る
        self.client.post(
            self.url,
            data=json.dumps({'text': '散歩を12時からにして', 'mode': 'edit'}),
            content_type='application/json',
        )

        self.assertEqual(mock_ask_ai.call_args.kwargs['current_schedules'], new_schedules)
    
    @patch('schedules.views.ask_ai')
    def test_edit_mode_without_schedules_returns_400(self, mock_ask_ai):
        # 編集モードで予定がなければ 400、AI を呼ばず、回数も減らない
        self.client.force_login(self.user)
        response = self.client.post(
            self.url,
            data=json.dumps({'text': '映画を14時からにして', 'mode': 'edit'}),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 400)
        mock_ask_ai.assert_not_called()
        usage = get_today_usage(self.user, timezone.localdate())
        self.assertEqual(usage.count, 0)

    
    @patch('schedules.views.ask_ai')
    def test_add_mode_passes_no_schedules(self, mock_ask_ai):
        # モードがない場合、ask_aiに予定を渡さない(None)
        self.client.force_login(self.user)

        mock_ask_ai.return_value = ScheduleList(schedules=[
            ScheduleItem(title='映画', start='14:00', end='16:00', duration_minutes=None),
        ])

        self.client.post(
            self.url,
            data=json.dumps({'text': '14時から16時まで映画'}),
            content_type='application/json',
        )
        self.assertIsNone(mock_ask_ai.call_args.kwargs['current_schedules'])


@override_settings(ELEVENLABS_API_KEY='test-key')
class SpeechViewTest(TestCase):
    def setUp(self):
        self.user = UserFactory()
        self.url = reverse('schedules:speech')

    def post_text(self, text):
        return self.client.post(
            self.url,
            data=json.dumps({'text': text}),
            content_type='application/json',
        )

    def test_redirects_when_not_logged_in(self):
        # ユーザーがログインしていない場合はリダイレクトされる
        response = self.post_text('いっしょにがんばろう')
        self.assertEqual(response.status_code, 302)

    @patch('schedules.views.httpx.post')
    def test_empty_text_returns_400(self, mock_post):
        # 文が空白だけなら400を返し、ElevenLabsには送らない
        self.client.force_login(self.user)
        response = self.post_text('   ')
        self.assertEqual(response.status_code, 400)
        mock_post.assert_not_called()

    @override_settings(ELEVENLABS_API_KEY='')
    @patch('schedules.views.httpx.post')
    def test_no_api_key_returns_503(self, mock_post):
        # APIキーが設定されていなければ503を返し、ElevenLabsには送らない
        self.client.force_login(self.user)
        response = self.post_text('いっしょにがんばろう')
        self.assertEqual(response.status_code, 503)
        mock_post.assert_not_called()

    @patch('schedules.views.httpx.post')
    def test_timeout_returns_502(self, mock_post):
        # ElevenLabsから時間内に返事が来なければ502エラーを返す
        self.client.force_login(self.user)
        mock_post.side_effect = httpx.TimeoutException('timeout')
        response = self.post_text('いっしょにがんばろう')
        self.assertEqual(response.status_code, 502)

    @patch('schedules.views.httpx.post')
    def test_success_returns_audio(self, mock_post):
        # ElevenLabsが成功したら、返ってきた音声をaudio/mpeg形式でで返す
        self.client.force_login(self.user)
        mock_post.return_value.status_code = 200
        mock_post.return_value.content = b'fake-mp3'
        response = self.post_text('いっしょにがんばろう')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'audio/mpeg')
        self.assertEqual(response.content, b'fake-mp3')


class ScheduleClearViewTest(TestCase):
    def setUp(self):
        self.user = UserFactory()
        self.url = reverse('schedules:clear')

    def test_clear_deletes_today_schedules_and_session(self):
        # 「今日の予定を最初から入れなおす」ボタンを押すと、今日の予定がDBから消え、セッションのデータも消える
        self.client.force_login(user=self.user)
        today = timezone.localtime().replace(minute=0, second=0, microsecond=0)
        schedule = ScheduleFactory(
            user=self.user,
            title='ごみ捨て',
            start_at=today.replace(hour=7),
            end_at=today.replace(hour=7, minute=10)
        )
        session = self.client.session
        session['new_schedules'] = [{
            'title': '朝ごはんの準備',
            'start_at': today.replace(hour=7, minute=10).isoformat(),
            'end_at': today.replace(hour=7, minute=45).isoformat(),
        }, ]
        session['new_schedules_date'] = today.date().isoformat()
        session.save()
        response = self.client.post(self.url)
        self.assertRedirects(response, f"{reverse('schedules:input')}?mode=restart")
        self.assertFalse(Schedule.objects.filter(pk=schedule.pk).exists())
        self.assertNotIn('new_schedules', self.client.session)

    def test_clear_keeps_other_day_and_other_user(self):
        # 今日の予定を削除した場合でも、同ユーザーの別日程のスケジュールや別ユーザーのスケジュールは削除されない
        today = timezone.localtime().replace(minute=0, second=0, microsecond=0)
        self.client.force_login(user=self.user)
        other_user = UserFactory()
        other_user_schedule = ScheduleFactory(
            user=other_user,
            title='犬の散歩',
            start_at=today.replace(hour=7),
            end_at=today.replace(hour=7, minute=30),
        )
        my_schedule_tomorrow = ScheduleFactory(
            user=self.user,
            title='ホームセンターに行く',
            start_at=today.replace(hour=10) + timedelta(days=1),
            end_at=today.replace(hour=12) + timedelta(days=1),
        )
        self.client.post(self.url)
        self.assertTrue(Schedule.objects.filter(pk=other_user_schedule.pk).exists())
        self.assertTrue(Schedule.objects.filter(pk=my_schedule_tomorrow.pk).exists())

    def test_clear_rejects_get(self):
        # /clearのURLを直接開いても405エラーとなり、予定も消えない
        self.client.force_login(user=self.user)
        today = timezone.localtime().replace(minute=0, second=0, microsecond=0)
        schedule = ScheduleFactory(
            user=self.user,
            title='友達に会う',
            start_at=today.replace(hour=12),
            end_at=today.replace(hour=17),
        )
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 405)
        self.assertTrue(Schedule.objects.filter(pk=schedule.pk).exists())

class DashBoardViewTest(TestCase):
    def setUp(self):
        self.user = UserFactory()
        self.url = reverse('schedules:dashboard')

    def test_shows_today_own_schedules_in_order(self):
        # 今日の自分の予定が、開始時刻の順にschedulesに入る(ほかの日・ほかの人の予定は入らない)
        today = timezone.localtime().replace(minute=0, second=0, microsecond=0)
        self.client.force_login(self.user)
        ScheduleFactory(
            user=self.user,
            title='統計の学習',
            start_at=today.replace(hour=13),
            end_at=today.replace(hour=16)
        )
        ScheduleFactory(
            user=self.user,
            title='布団を干す',
            start_at=today.replace(hour=9),
            end_at=today.replace(hour=11)
        )
        ScheduleFactory(
            user=self.user,
            title='昼ごはん',
            start_at=today.replace(hour=12),
            end_at=today.replace(hour=13)
        )
        ScheduleFactory(
            user=self.user,
            title='実家の掃除',
            start_at=today.replace(hour=9) - timedelta(days=1),
            end_at=today.replace(hour=15) - timedelta(days=1)
        )
        other_user = UserFactory()
        ScheduleFactory(
            user=other_user,
            title='会議',
            start_at=today.replace(hour=15),
            end_at=today.replace(hour=16)
        )
        response = self.client.get(self.url)
        titles = [s.title for s in response.context['schedules']]
        self.assertEqual(titles, ['布団を干す', '昼ごはん', '統計の学習'])
    
    def test_current_schedule(self):
        # 進行中の予定がcurrent_scheduleに入り、画面に「いま」という文字が表示される
        now = timezone.localtime()
        self.client.force_login(self.user)
        schedule = ScheduleFactory(
            user=self.user, title='散歩',
            start_at=now - timedelta(minutes=30),
            end_at=now + timedelta(minutes=30)
        )
        response = self.client.get(self.url)
        self.assertEqual(response.context['current_schedule'], schedule)
        self.assertContains(response, '<span class="next-bar-time">いま')
    
    def test_next_schedule(self):
        # 進行中の予定がない場合、次の予定がnext_scheduleに入り、画面に「つぎ」という文字が表示される
        now = timezone.localtime()
        self.client.force_login(self.user)
        schedule = ScheduleFactory(
            user=self.user, title='買い物',
            start_at=now + timedelta(minutes=30),
            end_at=now + timedelta(minutes=90)
        )
        response = self.client.get(self.url)
        self.assertEqual(response.context['next_schedule'], schedule)
        self.assertContains(response, '<span class="next-bar-time">つぎ')
        self.assertContains(response, '買い物')
    
    def test_all_schedules_finished(self):
        # 予定が全て完了している場合、画面に「今日の予定は全部おわったよ」という文字が表示される
        now = timezone.localtime()
        self.client.force_login(self.user)
        ScheduleFactory(
            user=self.user, title='ショッピング',
            start_at=now - timedelta(minutes=90),
            end_at=now - timedelta(minutes=30)
        )
        response = self.client.get(self.url)
        self.assertIsNone(response.context['next_schedule'])
        self.assertIsNone(response.context['current_schedule'])
        self.assertContains(response, '今日の予定は全部おわったよ')
    
    def test_no_schedules(self):
        # 今日の予定が登録されていない場合、画面に「まだ予定がないよ」という文字が表示される
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertIsNone(response.context['next_schedule'])
        self.assertIsNone(response.context['current_schedule'])
        self.assertContains(response, 'まだ予定がないよ')
        self.assertContains(response, '＋ボタンから予定を追加してみよう！')

    def test_gap_minutes_only_between_separated_schedules(self):
        # 予定と予定の間に空き時間がある場合だけ、gap_minutesに値が入る
        now = timezone.localtime().replace(minute=0, second=0, microsecond=0)
        self.client.force_login(self.user)
        ScheduleFactory(
            user=self.user,
            title='打ち合わせ',
            start_at=now.replace(hour=9),
            end_at=now.replace(hour=10),
        )
        ScheduleFactory(
            user=self.user,
            title='資料作成',
            start_at=now.replace(hour=10, minute=30),
            end_at=now.replace(hour=11),
        )
        ScheduleFactory(
            user=self.user,
            title='研修動画の視聴',
            start_at=now.replace(hour=11),
            end_at=now.replace(hour=12),
        )
        response = self.client.get(self.url)
        timeline = response.context['timeline']
        self.assertEqual(timeline[0].gap_minutes, 30)
        self.assertFalse(hasattr(timeline[1], 'gap_minutes'))
        self.assertFalse(hasattr(timeline[2], 'gap_minutes'))

    def test_start_button_shown_when_running_or_waiting(self):
        # 実行中・待っているときは、バーに実行ページへのリンクが出る
        now = timezone.localtime()
        self.client.force_login(self.user)
        schedule = ScheduleFactory(
            user=self.user,
            title='データの集計作業',
            start_at=now - timedelta(minutes=30),
            end_at=now + timedelta(minutes=30),
        )
        response = self.client.get(self.url)
        task_run_link = f'href="{reverse("schedules:task_run")}"'
        self.assertContains(response, task_run_link)
        schedule.delete()
        ScheduleFactory(
            user=self.user,
            title='コードチェック',
            start_at=now + timedelta(minutes=30),
            end_at=now + timedelta(minutes=90),
        )
        response = self.client.get(self.url)
        self.assertContains(response, task_run_link)

    def test_start_button_hidden_when_finished_or_none(self):
        # 一日終了・予定がないときは、バーに実行ページへのリンクが出ない
        now = timezone.localtime()
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        task_run_link = f'href="{reverse("schedules:task_run")}"'
        self.assertNotContains(response, task_run_link)
        ScheduleFactory(
            user=self.user,
            title='コードチェック',
            start_at=now - timedelta(minutes=90),
            end_at=now - timedelta(minutes=30),
        )
        response = self.client.get(self.url)
        self.assertNotContains(response, task_run_link)

    def test_timeline_now_marked_when_running(self):
        # 実行中のタスクがある場合、HTMLにid="timeline-now"（実行中タスクの目印）があること
        now = timezone.localtime()
        self.client.force_login(self.user)
        ScheduleFactory(
            user=self.user,
            title='統計学の模擬テスト',
            start_at=now - timedelta(minutes=30),
            end_at=now + timedelta(minutes=30),
        )
        response = self.client.get(self.url)
        self.assertContains(response, 'id="timeline-now"')

    def test_shows_edit_link_count_and_speech_notice(self):
        # HTMLに、編集ページへのリンク・その日のタスクの件数・id="speech-unsupported"（音声入力不可時の案内）があること
        today = timezone.localtime().replace(minute=0, second=0, microsecond=0)
        self.client.force_login(self.user)
        ScheduleFactory(
            user=self.user,
            title='資料の確認',
            start_at=today.replace(hour=9),
            end_at=today.replace(hour=10),
        )
        ScheduleFactory(
            user=self.user,
            title='スピーチ練習',
            start_at=today.replace(hour=13),
            end_at=today.replace(hour=14),
        )
        response = self.client.get(self.url)
        self.assertContains(response, f'href="{reverse("schedules:edit")}"')
        self.assertContains(response, '・2件')
        self.assertContains(response, 'id="speech-unsupported"')

class ScheduleStatusTest(TestCase):
    def setUp(self):
        self.now = timezone.now()
        self.user = UserFactory()
    
    def test_no_schedules_returns_none(self):
        # 予定がない場合はstateが'none'になる
        schedules = Schedule.objects.filter(user=self.user).order_by('start_at')
        state, current_schedule, next_schedule = get_schedule_status(schedules, self.now)
        self.assertEqual(state, 'none')

    def test_current_schedule_returns_running(self):
        # 予定を実行中の場合はstateが'running'になる
        ScheduleFactory(
            user=self.user,
            title='模様替え',
            start_at=self.now - timedelta(minutes=60),
            end_at=self.now + timedelta(minutes=60)
        )
        schedules = Schedule.objects.filter(user=self.user).order_by('start_at')
        state, current_schedule, next_schedule = get_schedule_status(schedules, self.now)
        self.assertEqual(state, 'running')

    def test_starts_within_15_minutes_returns_soon(self):
        # 予定がもうすぐ始まる場合はstateが'soon'になる
        ScheduleFactory(
            user=self.user,
            title='メールチェック・返信',
            start_at=self.now + timedelta(minutes=10),
            end_at=self.now + timedelta(minutes=30)
        )
        schedules = Schedule.objects.filter(user=self.user).order_by('start_at')
        state, current_schedule, next_schedule = get_schedule_status(schedules, self.now)
        self.assertEqual(state, 'soon')
        
    def test_starts_after_15_minutes_returns_waiting(self):
        # 予定がまだ始まらない場合にはstateが'waiting'になる
        ScheduleFactory(
            user=self.user,
            title='玄関の掃除',
            start_at=self.now + timedelta(minutes=30),
            end_at=self.now + timedelta(minutes=45)
        )
        schedules = Schedule.objects.filter(user=self.user).order_by('start_at')
        state, current_schedule, next_schedule = get_schedule_status(schedules, self.now)
        self.assertEqual(state, 'waiting')

    def test_all_schedules_ended_returns_finished(self):
        # 全ての予定が終了した場合にはstateが'finished'になる
        ScheduleFactory(
            user=self.user,
            title='ピラティス',
            start_at=self.now - timedelta(minutes=90),
            end_at=self.now - timedelta(minutes=10)
        )
        schedules = Schedule.objects.filter(user=self.user).order_by('start_at')
        state, current_schedule, next_schedule = get_schedule_status(schedules, self.now)
        self.assertEqual(state, 'finished')

class TaskRunViewTest(TestCase):
    def setUp(self):
        self.now = timezone.now()
        self.user = UserFactory()
        self.url = reverse('schedules:task_run')

    def test_running_shows_current_schedule(self):
        # stateが'running'（実行中のタスクがある）の場合、実行画面に実行中のタスク名が表示される
        self.client.force_login(self.user)
        ScheduleFactory(
            user=self.user,
            title='弁当作り',
            start_at=self.now - timedelta(minutes=10),
            end_at=self.now + timedelta(minutes=10)
        )
        response = self.client.get(self.url)
        self.assertContains(response, '弁当作り')
        self.assertEqual(response.context['state'], 'running')

    def test_waiting_shows_start_now_button(self):
        # stateが'soon'か'waiting'（開始待ち）の場合、
        # 「今すぐ始める」ボタンが表示される
        self.client.force_login(self.user)
        ScheduleFactory(
            user=self.user,
            title='庭の手入れ',
            start_at=self.now + timedelta(minutes=10),
            end_at=self.now + timedelta(minutes=30)
        )
        response = self.client.get(self.url)
        self.assertEqual(response.context['state'], 'soon')
        self.assertContains(response, 'id="start-now-btn"')

    def test_finished_shows_back_button(self):
        # stateが'finished'（全てのタスクが終了済み）の場合、
        # 「今日の予定は全部おわったよ」の文字と「ダッシュボードにもどる」ボタンが表示される
        self.client.force_login(self.user)
        ScheduleFactory(
            user=self.user,
            title='ごみ出し',
            start_at=self.now - timedelta(minutes=10),
            end_at=self.now - timedelta(minutes=5)
        )
        response = self.client.get(self.url)
        self.assertContains(response, '今日の予定は全部おわったよ')
        self.assertContains(response, 'ダッシュボードにもどる')
        self.assertEqual(response.context['state'], 'finished')

    def test_no_schedules_shows_back_button(self):
        # stateが'none'（予定なし）の場合、
        # 「まだ予定が入ってないよ」の文字と「ダッシュボードにもどる」ボタンが出る
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertContains(response, 'まだ予定が入ってないよ')
        self.assertContains(response, 'ダッシュボードにもどる')
        self.assertEqual(response.context['state'], 'none')

    def test_creates_setting_if_not_exists(self):
        # Settingテーブルにレコードがない利用者が実行画面を開くと、レコードが作られる
        self.client.force_login(self.user)
        self.assertEqual(Setting.objects.filter(user=self.user).count(), 0)
        self.client.get(self.url)
        self.assertEqual(Setting.objects.filter(user=self.user).count(), 1)
    
    def test_settings_data_uses_defaults(self):
        # 新しいレコードについて、値は初期値（オン・通知間隔15分）となり、初期値がcontextに入る
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertEqual(
            response.context['settings_data'],
            {'time_left_alert': True, 'alert_interval': 15}
        )

    def test_settings_data_uses_existing_setting(self):
        # 既にSettingsテーブルにレコードがある利用者は、その値がcontextに入る
        self.client.force_login(self.user)
        Setting.objects.create(
            user=self.user,
            time_left_alert=False,
            alert_interval=5,
        )
        response = self.client.get(self.url)
        self.assertEqual(response.context['settings_data'], {'time_left_alert': False, 'alert_interval': 5})

            
    def test_shows_link_to_edit_page(self):
        # 実行ページ内に編集ページへのリンクがある
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertContains(response, f'href="{reverse("schedules:edit")}"')

    def test_timeline_sets_gap_minutes(self):
        # context['timeline']の予定のうち、次の予定の開始時刻と間隔が空いている場合にだけgap_minutes属性が入る
        self.client.force_login(self.user)
        today = timezone.localtime().replace(minute=0, second=0, microsecond=0)
        ScheduleFactory(
            user=self.user,
            title='パン屋へ行く',
            start_at=today.replace(hour=9),
            end_at=today.replace(hour=10),
        )
        ScheduleFactory(
            user=self.user,
            title='銀行へ行く',
            start_at=today.replace(hour=10, minute=30),
            end_at=today.replace(hour=11),
        )
        ScheduleFactory(
            user=self.user,
            title='荷物箱詰め作業',
            start_at=today.replace(hour=11),
            end_at=today.replace(hour=12),
        )
        response = self.client.get(self.url)
        timeline = response.context['timeline']
        self.assertEqual(timeline[0].gap_minutes, 30)
        self.assertFalse(hasattr(timeline[1], 'gap_minutes'))
        self.assertFalse(hasattr(timeline[2], 'gap_minutes'))

    def test_timeline_rows_have_schedule_ids(self):
        # 一覧の各行を表すHTMLに、各予定のpkと同じdata-idが付いている
        self.client.force_login(self.user)
        today = timezone.localtime().replace(minute=0, second=0, microsecond=0)
        schedule1 = ScheduleFactory(
            user=self.user,
            title='ＤＩＹストアへ行く',
            start_at=today.replace(hour=14),
            end_at=today.replace(hour=15),
        )
        schedule2 = ScheduleFactory(
            user=self.user,
            title='組立作業',
            start_at=today.replace(hour=15),
            end_at=today.replace(hour=16),
        )
        response = self.client.get(self.url)
        self.assertContains(response, f'data-id="{schedule1.pk}"')
        self.assertContains(response, f'data-id="{schedule2.pk}"')

    def test_no_timeline_when_no_schedules(self):
        # 予定がないときは、HTMLにid="timeline"がない
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertNotContains(response, 'id="timeline"')

    def test_shows_link_to_input_page(self):
        # HTMLに「声で予定を追加」のリンク（?mode=add&from=run）がある
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertContains(response, f'href="{reverse("schedules:input")}?mode=add&from=run"')

    def test_shows_character_when_no_schedules(self):
        # 予定が入っていない日でも、キャラクターが表示される
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertContains(response, 'id="chara"')
        self.assertContains(response, 'schedules/js/character.js')
        self.assertContains(response, 'schedules/css/character.css')

    def test_watching_hidden_on_load(self):
        # タスク実行中の場合でも、実行ページを開いた段階では「みまもり中」の表示が隠れている
        now = timezone.localtime()
        self.client.force_login(self.user)
        ScheduleFactory(
            user=self.user,
            title='本屋へ行く',
            start_at=now - timedelta(minutes=10),
            end_at=now + timedelta(minutes=10),
        )
        response = self.client.get(self.url)
        self.assertContains(response, 'id="watching" class="watching hidden"')

    def test_bubbles_hidden_when_finished(self):
        # タスクが全て終了している場合、実行ページを開いた段階では
        # id="speech-bubble"とid="volume-note"の吹き出しが隠れている
        now = timezone.localtime()
        self.client.force_login(self.user)
        ScheduleFactory(
            user=self.user,
            title='手紙を発送する',
            start_at=now - timedelta(minutes=10),
            end_at=now - timedelta(minutes=5),
        )
        response = self.client.get(self.url)
        self.assertContains(response, 'id="speech-bubble" class="bubble hidden"')
        self.assertContains(response, 'id="volume-note" class="bubble hidden"')

    def test_timeline_shows_end_time(self):
        # 予定の一覧に終了時刻が出ている
        today = timezone.localtime().replace(minute=0, second=0, microsecond=0)
        self.client.force_login(self.user)
        ScheduleFactory(
            user=self.user,
            title='読書',
            start_at=today.replace(hour=9),
            end_at=today.replace(hour=10),
        )
        response = self.client.get(self.url)
        self.assertContains(response, '～10:00')
    
    def test_actions_on_top_when_finished(self):
        # 一日の予定が全て終了している場合、各種ボタンがキャラクターの上（id="actions-top"）に出ている
        now = timezone.localtime()
        self.client.force_login(self.user)
        ScheduleFactory(
            user=self.user,
            title='ゴミ出し',
            start_at=now - timedelta(minutes=10),
            end_at=now - timedelta(minutes=5),
        )
        response = self.client.get(self.url)
        self.assertContains(response, 'id="actions-top" class=""')
        self.assertContains(response, 'id="actions-bottom" class="hidden"')

class StartNowViewTest(TestCase):
    def setUp(self):
        self.now = timezone.now()
        self.user = UserFactory()
        self.url = reverse('schedules:start_now')

    def test_starts_next_schedule_now(self):
        # 次の予定のidを送ると、その予定の開始時刻が今の時刻に上書きされる
        self.client.force_login(self.user)
        schedule = ScheduleFactory(
            user=self.user,
            title='風呂の掃除',
            start_at=self.now + timedelta(minutes=20),
            end_at=self.now + timedelta(minutes=40),
        )
        response = self.client.post(self.url, {'id': schedule.pk}, content_type='application/json')
        self.assertEqual(response.status_code, 200)
        schedule.refresh_from_db()
        self.assertGreaterEqual(schedule.start_at, self.now)
        self.assertLess(schedule.start_at, self.now + timedelta(minutes=1))

    def test_rejects_schedule_that_is_not_next(self):
        # 次の予定以外のidを入れた場合、400エラーとなり時刻は上書きされない
        self.client.force_login(self.user)
        ScheduleFactory(
            user=self.user,
            title='ドラッグストアへ行く',
            start_at=self.now + timedelta(minutes=20),
            end_at=self.now + timedelta(minutes=40),
        )
        schedule = ScheduleFactory(
            user=self.user,
            title='来客対応',
            start_at=self.now + timedelta(minutes=60),
            end_at=self.now + timedelta(minutes=90)
        )
        original_start_at = schedule.start_at
        response = self.client.post(self.url, {'id': schedule.pk}, content_type='application/json')
        self.assertEqual(response.status_code, 400)
        schedule.refresh_from_db()
        self.assertEqual(schedule.start_at, original_start_at)

    def test_rejects_while_running(self):
        # 実行中の予定がある時に「今すぐ始める」を送った場合でも処理されず、次の予定の時刻は変わらない
        self.client.force_login(self.user)
        ScheduleFactory(
            user=self.user,
            title='メール確認',
            start_at=self.now - timedelta(minutes=10),
            end_at=self.now + timedelta(minutes=10)
        )
        schedule = ScheduleFactory(
            user=self.user,
            title='書類確認',
            start_at=self.now + timedelta(minutes=20),
            end_at=self.now + timedelta(minutes=40)
        )
        original_start_at = schedule.start_at
        response = self.client.post(self.url, {'id': schedule.pk}, content_type='application/json')
        self.assertEqual(response.status_code, 400)
        schedule.refresh_from_db()
        self.assertEqual(schedule.start_at, original_start_at)

    def test_rejects_other_users_schedule(self):
        # 他の利用者の予定idを送った場合でも、処理されず、データが書き換わらない
        self.client.force_login(self.user)
        other_user = UserFactory()
        schedule = ScheduleFactory(
            user=other_user,
            title='郵便局へ行く',
            start_at=self.now + timedelta(minutes=20),
            end_at=self.now + timedelta(minutes=40)
        )
        original_start_at = schedule.start_at
        response = self.client.post(self.url, {'id': schedule.pk}, content_type='application/json')
        self.assertEqual(response.status_code, 400)
        schedule.refresh_from_db()
        self.assertEqual(schedule.start_at, original_start_at)
        

    def test_redirects_when_not_logged_in(self):
        # ユーザーがログインしていない場合はリダイレクトされる
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 302)

class ScheduleModelTest(TestCase):
    def setUp(self):
        self.user = UserFactory()

    def test_duration_minutes_returns_total_minutes(self):
        # タスクにかかる時間は「分」単位で表される
        now = timezone.now().replace(minute=0, second=0, microsecond=0)
        schedule = ScheduleFactory(
            user=self.user,
            title='映画鑑賞',
            start_at=now.replace(hour=13),
            end_at=now.replace(hour=14, minute=30),
        )
        self.assertEqual(schedule.duration_minutes, 90)