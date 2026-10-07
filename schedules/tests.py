from datetime import datetime, time, timedelta

from django.test import SimpleTestCase, TestCase
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

from .ai import ScheduleItem
from .factories import ScheduleFactory
from .forms import ScheduleEditForm
from .models import Schedule

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
        # 編集ページ→入力ページへのリンクについてモードが2種類ある
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertContains(response, f"{reverse('schedules:input')}?mode=restart")
        self.assertContains(response, f"{reverse('schedules:input')}?mode=edit")

        

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

    def test_shows_db_and_session_schedules(self):
        # 画面にDBとセッションの予定が表示される
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
        response = self.client.get(self.url)
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
