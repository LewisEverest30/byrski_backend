from django.db import models

# class Activity(models.Model):
#     ski_resort = models.CharField(verbose_name='滑雪场', max_length=30)
#     location = models.CharField(verbose_name='位置', max_length=200)
#     date_arrangement = models.CharField(verbose_name='日期安排(文字描述)', max_length=300)
#     duration_days = models.IntegerField(verbose_name='活动持续天数')
#     notes = models.CharField(verbose_name='备注(不超过500字)', max_length=500, null=True, blank=True)
#     price = models.IntegerField(verbose_name='价格')
#     need_rent = models.BooleanField(verbose_name='是否提供租赁雪具服务', default=False)
#     target_participant_num = models.IntegerField(verbose_name='目标报名人数')
#     current_participant_num = models.IntegerField(verbose_name='当前报名人数')

#     release_dt = models.DateTimeField(verbose_name='活动发布时间', auto_now_add=True)
#     signup_ddl_dt = models.DateTimeField(verbose_name='活动截止报名时间')

#     registration_status = models.BooleanField(verbose_name='是否可以报名', default=True)


# class Bus(models.Model):
#     ski_resort = models.CharField(verbose_name='滑雪场', max_length=30)
#     location = models.CharField(verbose_name='位置', max_length=200)


