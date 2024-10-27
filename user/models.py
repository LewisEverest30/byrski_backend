from django.db import models
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from django.utils import timezone
from django.db.models.signals import post_save
from django.dispatch import receiver




class Accesstoken(models.Model):
    access_token = models.CharField(max_length=1024, unique=True)
    expire_time = models.DateTimeField()



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
        yexue = 4, _('野雪')
    
    class SkiBoard_choices(models.IntegerChoices):
        Dan = 0, _('单板')
        Shuang = 1, _('双板')
    
    class Gender_choices(models.IntegerChoices):
        male = 0, _('男')
        female = 1, _('女')

    class Identity_choices(models.IntegerChoices):
        normal = 0, _('普通用户')
        leader = 1, _('领队')
    
    openid = models.CharField(verbose_name='openid', max_length=28, unique=True, db_index=True)

    name = models.CharField(verbose_name='姓名', max_length=15, null=True, blank=True)
    school = models.CharField(verbose_name='学校', max_length=50, null=True, blank=True)
    # age = models.IntegerField(verbose_name='年龄', null=True, blank=True)
    phone = models.CharField(verbose_name='手机号', max_length=11, null=True, blank=True)
    # wxaccount = models.CharField(verbose_name='微信号', max_length=22)
    idnumber = models.CharField(verbose_name='身份证号', max_length=18, null=True, blank=True)
    profile = models.ImageField(verbose_name='头像', null=True, blank=True,
                            upload_to='user/profile/')
    points = models.IntegerField(verbose_name='积分', null=True, blank=True, default=0)

    identity = models.IntegerField(verbose_name='身份', null=False, blank=False, choices=Identity_choices.choices, default=0)
    intro = models.TextField(verbose_name='个人介绍', null=True, blank=True)
    is_student = models.BooleanField(verbose_name='是否通过学生认证', default=False, null=False, blank=False)
    is_active = models.BooleanField(verbose_name='是否激活', default=True, null=False, blank=False)

    ski_board = models.IntegerField(verbose_name='单板or双板', null=True, choices=SkiBoard_choices.choices, blank=True)
    ski_level = models.IntegerField(verbose_name='滑雪水平', null=True, choices=SkiLevel_choices.choices, blank=True)
    ski_favor = models.IntegerField(verbose_name='滑雪喜好', null=True, choices=SkiStyle_choices.choices, blank=True)

    gender = models.IntegerField(verbose_name='性别', choices=Gender_choices.choices, null=True, blank=True)
    height = models.IntegerField(verbose_name='身高(cm)', null=True, blank=True)
    weight = models.IntegerField(verbose_name='体重(kg)', null=True, blank=True)
    foot_length = models.IntegerField(verbose_name='足长(mm)', null=True, blank=True)
    skiboots_size = models.IntegerField(verbose_name='鞋码', null=True, blank=True)
    # skiboots_size_1 = models.IntegerField(verbose_name='单板雪鞋尺码', null=True, blank=True)
    # skiboots_size_2 = models.IntegerField(verbose_name='双板雪鞋尺码', null=True, blank=True)
    snowboard_size_1 = models.IntegerField(verbose_name='单板板长', null=True, blank=True)
    snowboard_size_2 = models.IntegerField(verbose_name='双板板长', null=True, blank=True)
    snowboard_hardness = models.IntegerField(verbose_name='雪鞋硬度', null=True, blank=True)
    skipole_size = models.IntegerField(verbose_name='雪仗长度', null=True, blank=True)

    create_time = models.DateTimeField(verbose_name='创建时间', auto_now_add=True) 
    update_time = models.DateTimeField(verbose_name='修改时间', auto_now=True)

    def __str__(self) -> str:
        return f'{self.name}-#{self.id}'

    class Meta:
        verbose_name = "用户"
        verbose_name_plural = "用户"


class Leader(models.Model):
    user = models.ForeignKey(verbose_name='用户', to=User, on_delete=models.CASCADE)
    intro = models.TextField(verbose_name='领队介绍', null=True, blank=True)
    phone = models.CharField(verbose_name='手机号', max_length=11, null=True, blank=True)
    profile = models.ImageField(verbose_name='照片', null=True, blank=True,
                            upload_to='user/profile/')
    leadtimes = models.IntegerField(verbose_name='参与活动次数', default=0)
    
    is_active = models.BooleanField(verbose_name='是否激活', default=True, null=False, blank=False)
    create_time = models.DateTimeField(verbose_name='创建时间', auto_now_add=True) 
    update_time = models.DateTimeField(verbose_name='修改时间', auto_now=True)

    def __str__(self) -> str:
        return self.user.name

    class Meta:
        verbose_name = "领队"
        verbose_name_plural = "领队"
# 创建领队时通过信号机制来设置User表的内容
@receiver(post_save, sender=Leader)
def set_user_subject(sender, instance, created, **kwargs):
    if created:  # 如果是新创建的
        instance.user.identity = 1
        instance.user.phone = instance.phone
        instance.user.profile = instance.profile
        instance.user.intro = instance.intro
        instance.user.save()
    else:  # 如果是修改
        instance.user.phone = instance.phone
        instance.user.profile = instance.profile
        instance.user.intro = instance.intro
        instance.user.save()


class UserSerializer(serializers.ModelSerializer):
    school = serializers.CharField(source='school.school_name')
    school_id = serializers.IntegerField(source='school.id')
    class Meta:
        model = User
        fields = '__all__'


class UserSerializerSki(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'name', 'height', 'weight', 'foot_length', 'skiboots_size', 
                  'snowboard_size_1', 'snowboard_size_2', 'snowboard_hardness', 'skipole_size'
                  ]

class UserSerializerBasic(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'name', 'gender', 'phone', 
                  'height', 'weight', 'foot_length',  
                  'ski_board', 'ski_level', 'ski_favor'
                  ]


class LeaderSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    phone = serializers.SerializerMethodField()
    # user_id = serializers.SerializerMethodField()

    def get_name(self, obj):
        return obj.user.name

    def get_phone(self, obj):
        return obj.phone

    def get_user_id(self, obj):
        return obj.user.id

    class Meta:
        model = Leader
        fields = ['id', 'name', 'phone', 'profile', 'intro']



# ===============================================================================
'''
class UserSerializerHome(serializers.ModelSerializer):
    registration_time = serializers.SerializerMethodField()
    
    def get_registration_time(self, obj):
        time_now = timezone.now()
        time_regi = obj.create_time
        # todo
        return str((time_now - time_regi).days)
    
    
    class Meta:
        model = User
        fields = ['name', 'intro', 'registration_time', ]
'''

