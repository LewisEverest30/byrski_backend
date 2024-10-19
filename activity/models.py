from django.db import models
from rest_framework import serializers
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator
from django.conf import settings


from .utils import Validator_slope, Validator_schedule, SERVICE_STRING_SHOW, Validator_service



# ===============================数据库表==================================================
# 上车点区域范围
class Area(models.Model):
    area_name = models.CharField('地区名称', max_length=100, unique=True)

    def __str__(self) -> str:
        return self.area_name

    class Meta:
        verbose_name = "区域"
        verbose_name_plural = "区域"


# 上车点可选范围 
class BoardingLocTemplate(models.Model):
    school_name = models.CharField(verbose_name='学校名称', max_length=50)

    campus = models.CharField(verbose_name='学校位置(学校名+校区)', max_length=150, unique=True)
    busboardloc  =  models.CharField(verbose_name='上车点(学校名+校区+门)', max_length=150, null=True)
    area = models.ForeignKey(verbose_name='所在地区', to=Area, on_delete=models.CASCADE)

    def __str__(self) -> str:
        return self.campus

    class Meta:
        verbose_name = "上车点可选范围"
        verbose_name_plural = "上车点可选范围"


# 雪场
class Skiresort(models.Model):
    name = models.CharField(verbose_name='滑雪场名', max_length=50, null=False, blank=False)
    location = models.CharField(verbose_name='位置', max_length=300, null=False, blank=False)
    opening = models.CharField(verbose_name='营业时间', max_length=200, null=False, blank=False)
    phone = models.CharField(verbose_name='电话', max_length=11, null=False, blank=False)

    intro = models.TextField(verbose_name='简介', null=False, blank=False)
    cover = models.ImageField(verbose_name='封面图片', null=False, blank=False,
                            upload_to='skiresortpic/')
    slope = models.CharField(verbose_name='雪道组成', max_length=200, null=False, blank=False,
                             validators=[Validator_slope, ],
                             help_text='请用形如这样的格式来表示雪道的组成: "初级道-3 中级道-5 高级道-2"')
    
    detail = models.TextField(verbose_name='详细介绍', null=True, blank=True)
    detailpic = models.ImageField(verbose_name='详细介绍（电商长图形势）', null=True, blank=True,
                            upload_to='skiresortpic/')
    website = models.CharField(verbose_name='官网URL', max_length=500, null=True, blank=True)
    
    create_time = models.DateTimeField(verbose_name='创建时间', auto_now_add=True, null=True) 
    update_time = models.DateTimeField(verbose_name='修改时间', auto_now=True, null=True)


    def __str__(self) -> str:
        return self.name
    
    class Meta:
        verbose_name = "滑雪场"
        verbose_name_plural = "滑雪场"
# 雪场摄影
class SkiresortPic(models.Model):
    gift = models.ForeignKey(verbose_name='对应的滑雪场', to=Skiresort, 
                                 null=False, blank=False, on_delete=models.CASCADE)
    pic = models.ImageField(verbose_name='图片', null=False, blank=False,
                            upload_to='skiresortpic/')
    class Meta:
        verbose_name = "滑雪场摄影"
        verbose_name_plural = "滑雪场摄影"



# 活动类别模板
class ActivityTemplate(models.Model):
    ski_resort = models.ForeignKey(verbose_name='滑雪场', to=Skiresort, on_delete=models.PROTECT)    
    duration_days = models.IntegerField(verbose_name='持续天数')
    detail = models.TextField(verbose_name='活动详情', null=True, blank=False)
    schedule_full = models.TextField(verbose_name='行程安排(详细说明)', null=True, blank=False)
    attention = models.TextField(verbose_name='注意事项', null=True, blank=True)
    notes = models.TextField(verbose_name='备注', null=True, blank=True)

    schedule_lite = models.CharField(verbose_name='行程安排文字简述 (该字段暂时弃用)', max_length=300, null=True, blank=True,
                                validators=[Validator_schedule, ],
                                help_text='请用形如这样的格式来表示行程安排: "第一天9点:出发 第一天11点:到达 第一天16点:返程"')

    create_time = models.DateTimeField(verbose_name='创建时间', auto_now_add=True, null=True) 
    update_time = models.DateTimeField(verbose_name='修改时间', auto_now=True, null=True)

    def __str__(self) -> str:
        # return str(self.id)+'_'+self.ski_resort.name
        return f'{self.ski_resort.name}-{self.duration_days}天-#{self.id}'

    class Meta:
        verbose_name = "活动模板"
        verbose_name_plural = "活动模板"


# 活动（具体）
class Activity(models.Model):
    class Status_choices(models.IntegerChoices):
        permit_signup = 0, _('未截止报名')
        prevent_signup = 1, _('已截止未锁票')
        locked = 2, _('已锁票')

    activity_template = models.ForeignKey(verbose_name='对应活动模板', to=ActivityTemplate, on_delete=models.PROTECT)
    activity_begin_date = models.DateField(verbose_name='活动开始日期(活动第一天)', null=False, blank=False)
    activity_end_date = models.DateField(verbose_name='活动结束日期(活动最后一天)', null=False, blank=False)

    signup_ddl_date = models.DateField(verbose_name='截止报名日期(当天23:59截止报名)', null=False, blank=False)
    lock_ddl_date = models.DateField(verbose_name='锁票日期(当天23:59锁票)', null=False, blank=False)
    status = models.IntegerField(verbose_name='活动状态', choices=Status_choices.choices, default=0)

    target_participant = models.IntegerField(verbose_name='目标报名人数', null=False, blank=False)
    current_participant = models.IntegerField(verbose_name='当前报名人数', default=0)

    create_time = models.DateTimeField(verbose_name='创建时间', auto_now_add=True) 
    update_time = models.DateTimeField(verbose_name='修改时间', auto_now=True)

    def __str__(self) -> str:
        return f'{self.activity_template} - {self.activity_begin_date} - #{self.id}'

    class Meta:
        verbose_name = "活动"
        verbose_name_plural = "活动"


# 活动上车点
class Boardingloc(models.Model):
    activity = models.ForeignKey(verbose_name='活动', to=Activity, on_delete=models.PROTECT)
    loc = models.ForeignKey(verbose_name='上车点', to=BoardingLocTemplate, on_delete=models.PROTECT)
    choice_peoplenum = models.IntegerField(verbose_name='已选择人数', default=0)
    target_peoplenum = models.IntegerField(verbose_name='最低选择人数', null=False, blank=False)

    def __str__(self) -> str:
        return f'{self.loc}-活动(#{self.activity.id})-#{self.id}'
    
    class Meta:
        verbose_name = "上车点"
        verbose_name_plural = "上车点"
        unique_together = (("activity", "loc"),)


# 活动微信群
class ActivityWxGroup(models.Model):
    activity = models.ForeignKey(verbose_name='活动', to=Activity, on_delete=models.CASCADE)
    qrcode = models.ImageField(verbose_name='二维码', null=False, blank=False,
                                upload_to='activity/wxgroup/')
    
    create_time = models.DateTimeField(verbose_name='创建时间', auto_now_add=True) 
    update_time = models.DateTimeField(verbose_name='修改时间', auto_now=True)

    def __str__(self) -> str:
        return f'{self.activity}'

    class Meta:
        verbose_name = "活动"
        verbose_name_plural = "活动"


# 雪票
class Ticket(models.Model):
    activity = models.ForeignKey(verbose_name='活动', to=Activity, on_delete=models.PROTECT)
    service = models.CharField(verbose_name='提供的服务', max_length=100, null=False, blank=False,
                                validators=[Validator_service, ],
                                help_text='请使用空格分隔各个服务。可选服务有：'+SERVICE_STRING_SHOW)
    
    price = models.DecimalField(verbose_name='单价', null=False, blank=False, max_digits=7, decimal_places=2,
                                validators=[MinValueValidator(1)])    
    sales = models.IntegerField(verbose_name='已售出个数', default=0)

    create_time = models.DateTimeField(verbose_name='创建时间', auto_now_add=True, null=True) 
    update_time = models.DateTimeField(verbose_name='修改时间', auto_now=True, null=True)

    def __str__(self) -> str:
        return str(self.id)+'_'+str(self.activity)

    class Meta:
        verbose_name = "票"
        verbose_name_plural = "票"





# =======================================================================================



# ===============================序列化器============================================
class BoardingLocTemplateSerializer(serializers.ModelSerializer):
    area = serializers.CharField(source='area.area_name')
    area_id = serializers.IntegerField(source='area.id')
    class Meta:
        model = BoardingLocTemplate
        fields = '__all__'


class SkiresortPicSerializer(serializers.ModelSerializer):
    class Meta:
        model = Skiresort
        exclude = ['id', 'gift']


class ActivitySerializer(serializers.ModelSerializer):
    ski_resort_id = serializers.IntegerField(source='ski_resort.id')
    ski_resort = serializers.CharField(source='ski_resort.name')
    ski_resort_loc = serializers.CharField(source='ski_resort.location')
    class Meta:
        model = Activity
        fields = '__all__'


class BoardinglocSerializer(serializers.ModelSerializer):
    loc = serializers.CharField(source='loc.busboardloc')
    loc_id = serializers.IntegerField(source='loc.id')
    class Meta:
        model = Boardingloc
        fields = '__all__'

# ======================================================================================



# ⬇️雪具租赁相关表
'''

class RentPrice(models.Model):
    ski_resort = models.ForeignKey(verbose_name='滑雪场', to=Skiresort, on_delete=models.CASCADE)

    helmet_price = models.IntegerField(verbose_name='头盔单价')
    helmet_deposit = models.IntegerField(verbose_name='头盔押金')
    glasses_price = models.IntegerField(verbose_name='雪镜单价')
    glasses_deposit = models.IntegerField(verbose_name='雪镜押金')
    gloves_price = models.IntegerField(verbose_name='手套单价')
    gloves_deposit = models.IntegerField(verbose_name='手套押金')
    hippad_price = models.IntegerField(verbose_name='护臀单价')
    hippad_deposit = models.IntegerField(verbose_name='护臀押金')
    kneepad_price = models.IntegerField(verbose_name='护膝单价')
    kneepad_deposit = models.IntegerField(verbose_name='护膝押金')
    wristpad_price = models.IntegerField(verbose_name='护腕单价')
    wristpad_deposit = models.IntegerField(verbose_name='护腕押金')
    # snowboard_price = models.IntegerField(verbose_name='雪板单价')
    # snowboard_deposit = models.IntegerField(verbose_name='雪板押金')
    snowboard1_price = models.IntegerField(verbose_name='单板单价')
    snowboard1_deposit = models.IntegerField(verbose_name='单板押金')
    snowboard2_price = models.IntegerField(verbose_name='双板单价')
    snowboard2_deposit = models.IntegerField(verbose_name='双板押金')
    skiboots_price = models.IntegerField(verbose_name='雪鞋单价')
    skiboots_deposit = models.IntegerField(verbose_name='雪鞋押金')

    def __str__(self) -> str:
        return self.ski_resort.name

    class Meta:
        verbose_name = "雪具租赁价格"
        verbose_name_plural = "雪具租赁价格"


# 先有一个order，再可能有对应的rentorder
class RentOrder(models.Model):
    user = models.ForeignKey(verbose_name='用户', to=User, on_delete=models.CASCADE)
    order = models.ForeignKey(verbose_name='对应活动订单', to=TicketOrder, on_delete=models.CASCADE)
    activity = models.ForeignKey(verbose_name='活动', to=Activity, on_delete=models.PROTECT, default=1)

    duration_days = models.IntegerField(verbose_name='租赁天数')

    helmet = models.BooleanField(verbose_name='头盔')
    glasses = models.BooleanField(verbose_name='学镜')
    gloves = models.BooleanField(verbose_name='手套')
    hippad = models.BooleanField(verbose_name='护臀')
    kneepad = models.BooleanField(verbose_name='护膝')
    wristpad = models.BooleanField(verbose_name='护腕')
    snowboard = models.BooleanField(verbose_name='雪板')
    skiboots = models.BooleanField(verbose_name='雪鞋')

    is_active = models.BooleanField(verbose_name='是否有效(活动订单是否付款)', default=False)

    class Meta:
        verbose_name = "租赁单"
        verbose_name_plural = "租赁单"



'''