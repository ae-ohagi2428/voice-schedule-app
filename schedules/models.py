from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class Schedule(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name="ユーザー"
    )
    title = models.CharField(
        max_length=200,
        verbose_name="タイトル"
    )
    start_at = models.DateTimeField(
        verbose_name="開始予定時刻"
    )
    end_at = models.DateTimeField(
        verbose_name="終了予定時刻"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="作成日時"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="更新日時"
    )
    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(end_at__gt=models.F("start_at")),
                name="end_at_after_start_at",                
            )
        ]
    def __str__(self):
        return f"{self.start_at:%m/%d %H:%M} {self.title}"
    


class Setting(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        verbose_name="ユーザー"
    )
    time_left_alert = models.BooleanField(
        default=True,
        verbose_name="残り時間通知"
    )

    class AlertInterval(models.IntegerChoices):
        FIVE = 5, "5分"
        TEN = 10, "10分"
        FIFTEEN = 15, "15分"
        THIRTY = 30, "30分"

    alert_interval = models.PositiveIntegerField(
        choices=AlertInterval.choices,
        default=AlertInterval.FIFTEEN,
        verbose_name="お知らせ間隔（分）"    
    )

class ApiUsage(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        verbose_name="ユーザー"
    )
    last_used_on = models.DateField(
        verbose_name="前回使用日"
    )
    count = models.PositiveIntegerField(
        default=0,
        verbose_name="本日の使用回数"
    )