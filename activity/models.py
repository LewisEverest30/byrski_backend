from django.db import models
from rest_framework import serializers
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator
from django.conf import settings
from django.db.models import Min, Sum
from django.core.exceptions import ValidationError

from .utils import SERVICES
from .utils import Validator_slope, Validator_schedule, SERVICE_STRING_SHOW, Validator_service


# ===============================数据库表==================================================
# 上车点区域范围
class Area(models.Model):
    area_name = models.CharField('地区名称', max_length=100, unique=True)
    city_name = models.CharField('所属城市名称', max_length=100, null=False, blank=False)

    def __str__(self) -> str:
        return self.area_name

    class Meta:
        verbose_name = "区域"
        verbose_name_plural = "区域"

# 合作院校
class School(models.Model):
    name = models.CharField('学校名称', max_length=100, unique=True)
    def __str__(self) -> str:
        return self.name
    class Meta:
        verbose_name = "合作院校"
        verbose_name_plural = "合作院校"

# 上车点可选范围 
class BoardingLocTemplate(models.Model):
    school = models.ForeignKey(verbose_name='学校名称', to=School, on_delete=models.PROTECT)

    campus = models.CharField(verbose_name='校区', max_length=150)
    busboardloc  =  models.CharField(verbose_name='上车点(如：北门)', max_length=150)
    area = models.ForeignKey(verbose_name='所在地区', to=Area, on_delete=models.CASCADE)

    def __str__(self) -> str:
        return self.school.name + self.campus + self.busboardloc

    class Meta:
        verbose_name = "上车点可选范围"
        verbose_name_plural = "上车点可选范围"
        unique_together = (("school", "campus", "busboardloc", ),)

# 雪场
class Skiresort(models.Model):
    name = models.CharField(verbose_name='滑雪场名', max_length=50, null=False, blank=False)
    area = models.ForeignKey(verbose_name='所在地区', to=Area, on_delete=models.CASCADE, null=False, blank=False)
    location = models.CharField(verbose_name='位置', max_length=300, null=False, blank=False)
    opening = models.CharField(verbose_name='营业时间', max_length=200, null=False, blank=False)
    phone = models.CharField(verbose_name='电话', max_length=11, null=False, blank=False)

    intro = models.CharField(verbose_name='简介', max_length=25, null=False, blank=False)
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
    skiresort = models.ForeignKey(verbose_name='对应的滑雪场', to=Skiresort, 
                                 null=False, blank=False, on_delete=models.CASCADE)
    pic = models.ImageField(verbose_name='图片', null=False, blank=False,
                            upload_to='skiresortpic/')
    class Meta:
        verbose_name = "滑雪场摄影"
        verbose_name_plural = "滑雪场摄影"



# 活动类别模板
class ActivityTemplate(models.Model):
    ski_resort = models.ForeignKey(verbose_name='滑雪场', to=Skiresort, on_delete=models.PROTECT)
    name = models.CharField(verbose_name='活动票名', max_length=12, null=True, blank=False, help_text='示例：“金山岭两日住滑票” (12字以内)')
    duration_days = models.IntegerField(verbose_name='持续天数')
    detail = models.TextField(verbose_name='活动详情', null=True, blank=False)
    schedule = models.TextField(verbose_name='行程安排(详细说明)', null=True, blank=False)
    attention = models.TextField(verbose_name='注意事项', null=True, blank=True)
    notes = models.TextField(verbose_name='备注', null=True, blank=True)
    leader_notice = models.TextField(verbose_name='领队须知', null=True, blank=False)

    schedule_lite = models.CharField(verbose_name='行程安排文字简述 (该字段暂时弃用)', max_length=300, null=True, blank=True,
                                validators=[Validator_schedule, ],
                                help_text='请用形如这样的格式来表示行程安排: "第一天9点:出发 第一天11点:到达 第一天16点:返程"')

    create_time = models.DateTimeField(verbose_name='创建时间', auto_now_add=True, null=True) 
    update_time = models.DateTimeField(verbose_name='修改时间', auto_now=True, null=True)

    def __str__(self) -> str:
        # return str(self.id)+'_'+self.ski_resort.name
        return f'{self.name}-{self.ski_resort.name}-{self.duration_days}天-ID#{self.id}'

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
    # 返程时间、地点
    activity_return_time = models.TimeField(verbose_name='返程集合时间', null=True, blank=False)
    activity_return_loc = models.CharField(verbose_name='返程集合位置', max_length=70, null=True, blank=False)

    signup_ddl_date = models.DateField(verbose_name='截止报名日期(当天23:59截止报名)', null=False, blank=False)
    lock_ddl_date = models.DateField(verbose_name='锁票日期(当天23:59锁票)', null=False, blank=False)
    status = models.IntegerField(verbose_name='活动状态', choices=Status_choices.choices, default=0)
    success_departue = models.BooleanField(verbose_name='是否成功运行分车系统', default=False)

    target_participant = models.IntegerField(verbose_name='报名人数上限', null=True, blank=False, default=9999)
    current_participant = models.IntegerField(verbose_name='当前报名人数', default=0)

    create_time = models.DateTimeField(verbose_name='创建时间', auto_now_add=True) 
    update_time = models.DateTimeField(verbose_name='修改时间', auto_now=True)

    def __str__(self) -> str:
        return f'T({self.activity_template})T - {self.activity_begin_date} - ID#{self.id}'

    # def save(self, *args, **kwargs):
    #     if not self.ticket_set.exists():
    #         raise ValidationError("每个活动必须至少有一个票")
    #     if not self.boardingloc_set.exists():
    #         raise ValidationError("每个活动必须至少有一个上车点")
    #     if not self.activitywxgroup_set.exists():
    #         raise ValidationError("每个活动必须至少有一个微信群")
    #     super().save(*args, **kwargs)
    
    # def clean(self):
    #     # cleaned_data = super().clean()
    #     # activity = self.instance
    #     super().clean()
    #     if self.ticket_set.count() == 0:
    #         raise ValidationError("每个活动必须至少有一个票")
    #     if self.boardingloc_set.count() == 0:
    #         raise ValidationError("每个活动必须至少有一个上车点")
    #     if self.activitywxgroup_set.count() == 0:
    #         raise ValidationError("每个活动必须至少有一个微信群")
    
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
# 区域内所有上车点总下限
class AreaBoardingLowerLimit(models.Model):
    activity = models.ForeignKey(verbose_name='活动', to=Activity, on_delete=models.PROTECT)
    area = models.ForeignKey(verbose_name='所在地区', to=Area, on_delete=models.CASCADE, null=True, blank=False)
    lower_limit = models.IntegerField(verbose_name='下限人数', null=False, blank=False)
    def __str__(self) -> str:
        return f'活动(#{self.activity.id})-地区({self.area.area_name})-#{self.id}'
    class Meta:
        verbose_name = "区域上车下限"
        verbose_name_plural = "区域上车下限"

# 活动微信群
class ActivityWxGroup(models.Model):
    activity = models.ForeignKey(verbose_name='活动', to=Activity, on_delete=models.CASCADE)
    qrcode = models.ImageField(verbose_name='二维码', null=False, blank=False,
                                upload_to='activity/wxgroup/')
    
    create_time = models.DateTimeField(verbose_name='创建时间', auto_now_add=True) 
    update_time = models.DateTimeField(verbose_name='修改时间', auto_now=True)

    def __str__(self) -> str:
        return f'{self.activity} #{self.id}'

    class Meta:
        verbose_name = "微信群二维码"
        verbose_name_plural = "微信群二维码"

# 大巴类型
class Bustype(models.Model):
    activity = models.ForeignKey(verbose_name='活动', to=Activity, on_delete=models.PROTECT)
    passenger_num = models.IntegerField(verbose_name='可承载人数', validators=[MinValueValidator(1),])
    price = models.DecimalField(verbose_name='单价', null=False, blank=False, max_digits=7, decimal_places=2,
                                validators=[MinValueValidator(1),])    

    def __str__(self) -> str:
        return '可承载'+str(self.passenger_num)+'人'
    
    class Meta:
        verbose_name = "大巴车类型(只支持两种类型)"
        verbose_name_plural = "大巴车类型(只支持两种类型)"

# 雪票
class Ticket(models.Model):
    class Hotel_choices(models.IntegerChoices):
        not_provide_allocation = 0, _('不提供分配')
        provide_allocation = 1, _('提供分配')
    
    activity = models.ForeignKey(verbose_name='活动', to=Activity, on_delete=models.PROTECT)
    intro = models.CharField(verbose_name='简介', max_length=25, null=True, blank=False)
    
    service = models.CharField(verbose_name='提供的服务', max_length=100, null=False, blank=False,
                                validators=[Validator_service, ],
                                help_text='请使用空格分隔各个服务。可选服务有：'+SERVICE_STRING_SHOW)
    
    hotel_type = models.IntegerField(verbose_name='住宿类型（是否提供分房服务）', null=False, blank=False, default=0,
                                     choices=Hotel_choices.choices)
    hotel = models.CharField(verbose_name='酒店', max_length=25, null=True, blank=True)

    price = models.DecimalField(verbose_name='单价', null=False, blank=False, max_digits=7, decimal_places=2,
                                validators=[MinValueValidator(1)])    
    original_price = models.DecimalField(verbose_name='原价', null=True, blank=False, max_digits=7, decimal_places=2,
                                validators=[MinValueValidator(1)])    
    sales = models.IntegerField(verbose_name='已售出个数', default=0)

    create_time = models.DateTimeField(verbose_name='创建时间', auto_now_add=True, null=True) 
    update_time = models.DateTimeField(verbose_name='修改时间', auto_now=True, null=True)

    def __str__(self) -> str:
        return f'A{self.activity}A -- #{self.id}'
    
    class Meta:
        verbose_name = "票"
        verbose_name_plural = "票"


class Rentprice(models.Model):
    activity = models.ForeignKey(verbose_name='活动', to=Activity, on_delete=models.PROTECT)

    name = models.CharField(verbose_name='雪具名称', max_length=50, null=False, blank=False)
    price = models.DecimalField(verbose_name='价格（整个活动时间的总价，不分天数）', max_digits=5, decimal_places=2, null=False, blank=False)
    deposit = models.DecimalField(verbose_name='押金', max_digits=5, decimal_places=2, null=False, blank=False)


    def __str__(self) -> str:
        return f'{self.name} -- {self.price}元'

    class Meta:
        verbose_name = "雪具租赁信息"
        verbose_name_plural = "雪具租赁信息"
        unique_together = (("activity", "name",),)



# ===============================序列化器============================================

# 用于获取所有滑雪场
class SkiresortSerializer1(serializers.ModelSerializer):
    min_price = serializers.SerializerMethodField()

    def get_min_price(self, obj):
        tickets_min_price = Ticket.objects.filter(activity__activity_template__ski_resort__id=obj.id).aggregate(Min('price'))
        try:
            return tickets_min_price['price__min']
        except Exception as e:
            print(repr(e))
            return None

    class Meta:
        model = Skiresort
        fields = ['id', 'name', 'cover', 'intro', 'min_price']


# 用于获取滑雪场详细信息
class SkiresortSerializer2(serializers.ModelSerializer):
    class Meta:
        model = Skiresort
        fields = ['id', 'name', 'cover', 'intro', 'opening', 'location', 'slope']


# 用于活动模板详情页获取滑雪场详细信息
class SkiresortPicSerializer(serializers.ModelSerializer):
    class Meta:
        model = SkiresortPic
        exclude = ['id', 'skiresort']
class SkiresortSerializer3(serializers.ModelSerializer):
    pics = serializers.SerializerMethodField()

    def get_pics(self, obj):
        found = SkiresortPic.objects.filter(skiresort_id=obj.id)
        if found.count() > 0:
            serializer = SkiresortPicSerializer(instance=found, many=True)            
            return serializer.data
        else:
            return None

    class Meta:
        model = Skiresort
        fields = ['location', 'cover', 'pics']


# 用于获取雪具租赁信息
class RentpriceSerializer(serializers.ModelSerializer):
    rent_item_id = serializers.IntegerField(source='id')
    days = serializers.SerializerMethodField()
    def get_days(self, obj):
        return obj.activity.activity_template.duration_days
    
    class Meta:
        model = Rentprice
        fields = ['rent_item_id', 'name', 'price', 'deposit', 'days']


WEEKDAY_MAP = {
    "Monday": "周一",
    "Tuesday": "周二",
    "Wednesday": "周三",
    "Thursday": "周四",
    "Friday": "周五",
    "Saturday": "周六",
    "Sunday": "周日"
}
# 用于获取滑雪场下面的所有票
class TicketSerializer1(serializers.ModelSerializer):
    ticket_id = serializers.SerializerMethodField()
    activity_id = serializers.SerializerMethodField()
    activitytemplate_id = serializers.SerializerMethodField()
    activity_name = serializers.SerializerMethodField()
    begin_end = serializers.SerializerMethodField()

    def get_ticket_id(self, obj):
        return obj.id

    def get_activity_id(self, obj):
        return obj.activity.id
    
    def get_activitytemplate_id(self, obj):
        return obj.activity.activity_template.id

    def get_activity_name(self, obj):
        # todo-f 增加hotel
        if obj.hotel is None:
            return obj.activity.activity_template.name
        else:
            return obj.activity.activity_template.name + ' | ' + obj.hotel

    def get_begin_end(self, obj):
        begin_date_raw = obj.activity.activity_begin_date
        end_date_raw = obj.activity.activity_end_date
        begin_date = begin_date_raw.strftime('%Y年%m月%d日')
        end_date = end_date_raw.strftime('%Y年%m月%d日')
        begin_day = WEEKDAY_MAP[begin_date_raw.strftime('%A')]
        end_day = WEEKDAY_MAP[end_date_raw.strftime('%A')]

        return {
            'date': f'{begin_date}-{end_date}',
            'day': f'{begin_day}-{end_day}',
        }
        

    class Meta:
        model = Ticket
        fields = ['ticket_id', 'activity_id', 'activitytemplate_id', 'activity_name', 'begin_end', 'intro', 'price']


# 用于购票页面的票详情展示
class TicketSerializer2(serializers.ModelSerializer):
    ticket_id = serializers.SerializerMethodField()
    activity_id = serializers.SerializerMethodField()
    activitytemplate_id = serializers.SerializerMethodField()
    name = serializers.SerializerMethodField()
    begin_end = serializers.SerializerMethodField()
    service = serializers.SerializerMethodField()
    cover = serializers.SerializerMethodField()
    hotel = serializers.SerializerMethodField()

    rent_info = serializers.SerializerMethodField()
    def get_rent_info(self, obj):
        rent_item = Rentprice.objects.filter(activity=obj.activity)
        if rent_item.count() > 0:
            rent_item_serializer = RentpriceSerializer(instance=rent_item, many=True)
            return rent_item_serializer.data
        else:
            return []

    def get_ticket_id(self, obj):
        return obj.id

    def get_activity_id(self, obj):
        return obj.activity.id
    
    def get_activitytemplate_id(self, obj):
        return obj.activity.activity_template.id

    def get_name(self, obj):
        # todo-f 增加hotel
        if obj.hotel is None:
            return obj.activity.activity_template.name
        else:
            return obj.activity.activity_template.name + ' | ' + obj.hotel

    def get_hotel(self, obj):
        if obj.hotel is None:
            return None
        else:
            return obj.hotel

    def get_begin_end(self, obj):
        begin_date_raw = obj.activity.activity_begin_date
        end_date_raw = obj.activity.activity_end_date
        begin_date = begin_date_raw.strftime('%Y年%m月%d日')
        end_date = end_date_raw.strftime('%Y年%m月%d日')
        begin_day = WEEKDAY_MAP[begin_date_raw.strftime('%A')]
        end_day = WEEKDAY_MAP[end_date_raw.strftime('%A')]

        return {
            'date': f'{begin_date}-{end_date}',
            'day': f'{begin_day}-{end_day}',
        }
    
    def get_service(self, obj):
        services = obj.service.split()
        service_dict = [SERVICES[s] for s in services]
        return service_dict

    def get_cover(self, obj):
        return settings.MEDIA_URL + str(obj.activity.activity_template.ski_resort.cover)


    class Meta:
        model = Ticket
        fields = ['ticket_id', 'activity_id', 'activitytemplate_id', 
                  'name', 'service', 'cover', 'begin_end', 
                  'price', 'original_price', 'hotel', 'hotel_type', 
                  'rent_info']


# 用于获取模板详情
class ActivityTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ActivityTemplate
        fields = ['name', 'detail', 'schedule', 'attention']


class BoardinglocSerializer(serializers.ModelSerializer):
    area = serializers.CharField(source='loc.area.area_name')
    # loc = serializers.CharField(source='loc.busboardloc')
    loc = serializers.SerializerMethodField()

    def get_loc(self, obj):
        return obj.loc.school.name + obj.loc.campus + obj.loc.busboardloc
    
    class Meta:
        model = Boardingloc
        fields = ['id', 'area', 'loc', 'choice_peoplenum', 'target_peoplenum']

class BoardinglocSerializer2(serializers.ModelSerializer):
    area = serializers.CharField(source='loc.area.area_name')
    # loc = serializers.CharField(source='loc.busboardloc')
    loc = serializers.SerializerMethodField()

    def get_loc(self, obj):
        return {
            'school': obj.loc.school.name,
            'campus': obj.loc.campus,
            'busboardloc': obj.loc.busboardloc
        }
    
    class Meta:
        model = Boardingloc
        fields = ['id', 'area', 'loc', 'choice_peoplenum', 'target_peoplenum']

# ======================================================================================


'''

class ActivitySerializer(serializers.ModelSerializer):
    ski_resort_id = serializers.IntegerField(source='ski_resort.id')
    ski_resort = serializers.CharField(source='ski_resort.name')
    ski_resort_loc = serializers.CharField(source='ski_resort.location')
    class Meta:
        model = Activity
        fields = '__all__'

'''


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