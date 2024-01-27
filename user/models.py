from django.db import models
from django.utils.translation import gettext_lazy as _

class Area(models.Model):
    area_name = models.CharField('地区名称', max_length=100)


class School(models.Model):
    school_name = models.CharField(verbose_name='学校名称', max_length=50)

    campus = models.CharField(verbose_name='学校位置(校区)', max_length=150)

    area = models.ForeignKey(verbose_name='所在地区', to=Area, on_delete=models.CASCADE)


class User(models.Model):
    class SkiLevel_choices(models.IntegerChoices):
        Xiaobai = 0, _('小白')
        Xinshou = 1, _('新手')
        Zouren = 2, _('走刃')
        Dalao = 3, _('大佬')
    
    class SkiStyle_choices(models.IntegerChoices):
        Jichu = 0, _('基础')
        Kehua = 1, _('刻滑')
        Pinghua = 2, _('平花')
        Gongyuan = 3, _('公园')
    class SkiBoard_choices(models.IntegerChoices):
        Dan = 0, _('单板')
        Shuang = 1, _('双板')
    
    openid = models.CharField(verbose_name='openid', max_length=28, unique=True)

    name = models.CharField(verbose_name='姓名', max_length=15)
    school = models.ForeignKey(verbose_name='学校_id', to=School, on_delete=models.CASCADE, null=False)
    age = models.IntegerField(verbose_name='年龄', null=False)
    gender = models.BooleanField(verbose_name='性别', null=False)
    phone = models.CharField(verbose_name='手机号', null=False, max_length=11)
    wxaccount = models.CharField(verbose_name='微信号', max_length=22)

    hight = models.IntegerField(verbose_name='身高(cm)', null=True)
    wight = models.IntegerField(verbose_name='体重(kg)', null=True)
    skiboots_size_1 = models.IntegerField(verbose_name='单板雪鞋尺码', null=True)
    skiboots_size_2 = models.IntegerField(verbose_name='双板雪鞋尺码', null=True)
    snowboard_size_1 = models.IntegerField(verbose_name='单板板长', null=True)
    snowboard_size_2 = models.IntegerField(verbose_name='双板板长', null=True)
    skipole_size = models.IntegerField(verbose_name='雪仗长度', null=True)
    ski_level = models.IntegerField(verbose_name='滑雪水平', null=True, choices=SkiLevel_choices.choices)
    ski_style = models.IntegerField(verbose_name='滑雪风格', null=True, choices=SkiStyle_choices.choices)
    ski_board = models.IntegerField(verbose_name='单板or双板', null=True, choices=SkiBoard_choices.choices)

    is_student = models.BooleanField(verbose_name='是否通过学生认证', null=False, default=False)
    is_active = models.BooleanField(verbose_name='是否激活', null=False, default=True)

    create_time = models.DateTimeField(verbose_name='创建时间', auto_now_add=True) 
    update_time = models.DateTimeField(verbose_name='修改时间', auto_now=True)

    
    