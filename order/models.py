from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from datetime import timedelta
from rest_framework import serializers
from django.conf import settings


from user.models import User, Leader, LeaderSerializer
from activity.models import Ticket, ActivityWxGroup
from activity.models import Activity, Boardingloc


# =======================================================================================
# =====================================数据库表=============================================

# 大巴类型
class Bustype(models.Model):
    passenger_num = models.IntegerField(verbose_name='可承载人数')

    def __str__(self) -> str:
        return '可承载'+str(self.passenger_num)+'人'
    
    class Meta:
        verbose_name = "大巴车类型(只支持两种类型)"
        verbose_name_plural = "大巴车类型(只支持两种类型)"


# ========分车相关===========

# 大巴
class Bus(models.Model):
    activity = models.ForeignKey(verbose_name='活动', to=Activity, on_delete=models.PROTECT)

    car_number = models.CharField(verbose_name='车牌号', null=True, blank=True, max_length=10)
    driver_phone = models.CharField(verbose_name='司机手机号', max_length=11, null=True, blank=True)
    carry_peoplenum = models.IntegerField(verbose_name='车已承载人数', default=0, null=True, blank=True)  # 未上车人数 = 已承载人数 - 去程/返程上车人数
    max_people = models.IntegerField(verbose_name='车型最大承载人数', null=True)
    
    arrival_time = models.TimeField(verbose_name='预计到达雪场时间', null=True, blank=False)
    route = models.CharField(verbose_name='路线规划', max_length=500, null=True, blank=True)

    leader = models.ForeignKey(verbose_name='领队', to=Leader, on_delete=models.PROTECT, null=True, blank=True)

    def __str__(self) -> str:
        return str(self.car_number) + ' ( id: ' + str(self.id) + ', 乘客数: ' + str(self.bus_peoplenum) + ')'
    
    class Meta:
        verbose_name = "大巴车"
        verbose_name_plural = "大巴车"


# 某个大巴经过某个上车点的时间
class Bus_boarding_time(models.Model):
    bus = models.ForeignKey(verbose_name='大巴', to=Bus, on_delete=models.CASCADE)
    loc = models.ForeignKey(verbose_name='途径点', to=Boardingloc, on_delete=models.PROTECT)
    boarding_peoplenum = models.IntegerField(verbose_name='该点该车上车人数', default=0)
    time = models.TimeField(verbose_name='预计途径时间', null=True)

    def __str__(self) -> str:
        return str(self.time)

    class Meta:
        verbose_name = "车-途径点-时间 对应关系"
        verbose_name_plural = "车-途径点-时间 对应关系"




# =========活动订单===========


# 雪票订单 + 行程
class TicketOrder(models.Model):
    class Status_choices(models.IntegerChoices):
        cancelled = 0, _('已取消(交易关闭)')
        pending_payment = 1, _('待付款')
        paid = 2, _('已付款')
        locked = 3, _('已锁票')
        refund = 4, _('发起退款中')
        refund_in = 5, _('已退款')

    ordernumber = models.CharField(verbose_name='订单号', max_length=50, unique=True)

    user = models.ForeignKey(verbose_name='用户', to=User, on_delete=models.CASCADE)
    ticket = models.ForeignKey(verbose_name='票', to=Ticket, on_delete=models.PROTECT)
    wxgroup = models.ForeignKey(verbose_name='微信群', to=ActivityWxGroup, on_delete=models.SET_NULL, null=True, blank=True)
    bus_loc = models.ForeignKey(verbose_name='上车点', to=Boardingloc, on_delete=models.PROTECT)
    
    bus = models.ForeignKey(verbose_name='大巴', to=Bus, null=True, on_delete=models.SET_NULL, blank=True)
    bus_time = models.ForeignKey(verbose_name='上车时间', to=Bus_boarding_time, null=True, on_delete=models.SET_NULL, blank=True)

    go_boarded = models.BooleanField(verbose_name='去程是否上车', null=False, blank=False, default=False)
    return_boarded = models.BooleanField(verbose_name='返程是否上车', null=False, blank=False, default=False)
    completed_steps = models.IntegerField(verbose_name='已完成步数', null=False, blank=False, default=0)
    
    create_time = models.DateTimeField(verbose_name='下单时间', auto_now_add=True) 
    status = models.IntegerField(verbose_name='订单状态', null=False, default=1, choices=Status_choices.choices)

    def __str__(self) -> str:
        return self.ordernumber
    
    class Meta:
        verbose_name = "雪票订单"
        verbose_name_plural = "雪票订单"

    @classmethod
    def cancel_paid_timeout_orders(cls):
        # 获取当前时间
        now = timezone.now()
        # 计算20分钟前的时间
        threshold_time = now - timedelta(minutes=20)
        # 所有 create_time 小于 threshold_time 的记录，
        # 即20分钟前创建且未付款的订单，自动取消
        cls.objects.filter(status=1, create_time__lt=threshold_time).update(status=0)


# ========================================================================================
# ===================================序列化器==============================================

class OrderSerializer1(serializers.ModelSerializer):
    ski_resort_name = serializers.CharField(source='ticket.activity.activity_template.ski_resort.name')
    location = serializers.CharField(source='ticket.activity.activity_template.ski_resort.location')
    ski_resort_phone = serializers.CharField(source='ticket.activity.activity_template.ski_resort.phone')
    
    from_area = serializers.CharField(source='bus_loc.loc.area.area_name')
    to_area = serializers.CharField(source='ticket.activity.activity_template.ski_resort.area.area_name')

    # bus = serializers.SerializerMethodField(method_name='getbus')
    boardingloc = serializers.CharField(source='bus_loc.loc.busboardloc')
    boardingtime = serializers.SerializerMethodField()

    name = serializers.CharField(source='user.name')
    gender = serializers.IntegerField(source='user.gender')
    phone = serializers.CharField(source='user.phone')

    qrcode = serializers.SerializerMethodField()

    def get_boardingtime(self, obj):
        if obj.bus_time == None:
            return None
        else:
            return obj.bus_time.time.strftime('%H:%M')

    def get_qrcode(self, obj):
        actiwxgroup = obj.wxgroup.qrcode
        return settings.MEDIA_URL + str(actiwxgroup)

    class Meta:
        model = TicketOrder
        fields = ['ski_resort_name', 'location', 'ski_resort_phone', 
                  'from_area', 'to_area', 'boardingloc', 'boardingtime',
                  'name', 'gender', 'phone', 'qrcode']


# 用于下单后的行程卡
class OrderSerializer2(serializers.ModelSerializer):
    ski_resort_name = serializers.CharField(source='ticket.activity.activity_template.ski_resort.name')
    location = serializers.CharField(source='ticket.activity.activity_template.ski_resort.location')
    ski_resort_phone = serializers.CharField(source='ticket.activity.activity_template.ski_resort.phone')
    
    from_area = serializers.CharField(source='bus_loc.loc.area.area_name')
    to_area = serializers.CharField(source='ticket.activity.activity_template.ski_resort.area.area_name')

    # bus = serializers.SerializerMethodField(method_name='getbus')
    boardingloc = serializers.CharField(source='bus_loc.loc.busboardloc')
    boardingtime = serializers.SerializerMethodField()

    name = serializers.CharField(source='user.name')
    gender = serializers.IntegerField(source='user.gender')
    phone = serializers.CharField(source='user.phone')

    qrcode = serializers.SerializerMethodField()

    def get_boardingtime(self, obj):
        if obj.bus_time == None:
            return None
        else:
            return obj.bus_time.time.strftime('%H:%M')

    def get_qrcode(self, obj):
        actiwxgroup = obj.wxgroup.qrcode
        return settings.MEDIA_URL + str(actiwxgroup)

    class Meta:
        model = TicketOrder
        fields = ['ski_resort_name', 'location', 'ski_resort_phone', 
                  'from_area', 'to_area', 'boardingloc', 'boardingtime',
                  'name', 'gender', 'phone', 'qrcode']

    # def getbus(self, order):
    #     if order.bus == None:
    #         return None
    #     else:
    #         return order.bus.car_number


# 用于行程列表
class OrderSerializerItinerary1(serializers.ModelSerializer):
    name = serializers.CharField(source='ticket.activity.activity_template.name')
    ski_resort_location = serializers.CharField(source='ticket.activity.activity_template.ski_resort.location')
    begin_date = serializers.SerializerMethodField()
    to_area = serializers.CharField(source='ticket.activity.activity_template.ski_resort.area.area_name')
    ticket_intro = serializers.CharField(source='ticket.intro')

    def get_begin_date(self, obj):
        begin_date_raw = obj.ticket.activity.activity_begin_date
        begin_date = begin_date_raw.strftime('%m月%d日')

        return begin_date

    class Meta:
        model = TicketOrder
        fields = ['id', 'name', 'ski_resort_location', 'begin_date',
                  'to_area', 'ticket_intro']


# 用于行程详情
class OrderSerializerItinerary2(serializers.ModelSerializer):
    name = serializers.CharField(source='ticket.activity.activity_template.name')
    ski_resort_location = serializers.CharField(source='ticket.activity.activity_template.ski_resort.location')
    begin_date = serializers.SerializerMethodField()
    to_area = serializers.CharField(source='ticket.activity.activity_template.ski_resort.area.area_name')
    ticket_intro = serializers.CharField(source='ticket.intro')

    def get_begin_date(self, obj):
        begin_date_raw = obj.ticket.activity.activity_begin_date
        begin_date = begin_date_raw.strftime('%m月%d日')

        return begin_date

    boardingtime = serializers.SerializerMethodField()
    arrivaltime = serializers.SerializerMethodField()
    boardingloc = serializers.CharField(source='bus_loc.loc.busboardloc')
    arrivalloc = serializers.CharField(source='ticket.activity.activity_template.busboardloc')


    schedule = serializers.CharField(source='ticket.activity.activity_template.schedule')
    attention = serializers.IntegerField(source='ticket.activity.activity_template.attention')
    qrcode = serializers.SerializerMethodField()
    leader_info = serializers.SerializerMethodField()
    

    def get_boardingtime(self, obj):
        if obj.bus_time == None or obj.bus_time.time == None:
            return None
        else:
            return obj.bus_time.time.strftime('%H:%M')

    def get_arrivaltime(self, obj):
        if obj.bus == None or obj.bus.arrival_time == None:
            return None
        else:
            return obj.bus.arrival_time.strftime('%H:%M')

    def get_qrcode(self, obj):
        actiwxgroup = obj.wxgroup.qrcode
        return settings.MEDIA_URL + str(actiwxgroup)

    def get_leader_info(self, obj):
        if obj.bus == None or obj.bus.leader == None:
            return None
        else:
            serializer = LeaderSerializer(instance=obj.bus.leader, many=False)
            return serializer.data

    class Meta:
        model = TicketOrder
        fields = ['ski_resort_name', 'location', 'ski_resort_phone', 
                  'from_area', 'to_area', 'boardingloc', 'boardingtime',
                  'name', 'gender', 'phone', 'qrcode']

    # def getbus(self, order):
    #     if order.bus == None:
    #         return None
    #     else:
    #         return order.bus.car_number
