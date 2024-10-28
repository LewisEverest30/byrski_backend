from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from datetime import timedelta
from rest_framework import serializers
from django.conf import settings
from django.db.models import Q, F, Sum

from user.models import User, Leader, LeaderSerializer
from activity.models import Ticket, ActivityWxGroup, Activity, Boardingloc
from activity.utils import ACTIVITY_GUIDE

WXGROUP_MAX_NUM = 180
USER_POINTS_INCREASE_DELTA = 0
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
    # todo 实际最大承载人数-工作人员数，考虑变更上车点预留座位，比如55人车，2个工作人员，该字段为53（分车系统负责调整carry_peoplenum留出座位）
    max_people = models.IntegerField(verbose_name='车型最大承载人数', null=True, help_text='实际最大承载人数-工作人员数')
    
    arrival_time = models.TimeField(verbose_name='预计到达雪场时间', null=True, blank=False)
    route = models.CharField(verbose_name='路线规划', max_length=500, null=True, blank=True)

    leader = models.ForeignKey(verbose_name='领队', to=Leader, on_delete=models.PROTECT, null=True, blank=True)

    def __str__(self) -> str:
        return str(self.car_number) + '(ID#' + str(self.id) + '), 乘客数: ' + str(self.carry_peoplenum) + ')'
    
    class Meta:
        verbose_name = "大巴车"
        verbose_name_plural = "大巴车"


# 某个大巴经过某个上车点的时间。将大巴车与途径点构建多对多关系
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
    # 允许上车点被删，回set_null
    bus_loc = models.ForeignKey(verbose_name='上车点', to=Boardingloc, null=True, on_delete=models.SET_NULL)
    
    bus = models.ForeignKey(verbose_name='大巴', to=Bus, null=True, on_delete=models.SET_NULL, blank=True)
    bus_time = models.ForeignKey(verbose_name='上车时间', to=Bus_boarding_time, null=True, on_delete=models.SET_NULL, blank=True)

    go_boarded = models.BooleanField(verbose_name='去程是否上车', null=False, blank=False, default=False)
    return_boarded = models.BooleanField(verbose_name='返程是否上车', null=False, blank=False, default=False)
    completed_steps = models.IntegerField(verbose_name='已完成步数', null=False, blank=False, default=0, 
                                          help_text='未使用教程为0，处于第1步为1，完成第1步为2')
    
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
        orders = cls.objects.filter(status=1, create_time__lt=threshold_time)
        orders.update(status=0)

        # todo-f 移除订单有效性时，有一套需要联动的数据
        for order in orders:
            # 上车点人数-1(未截止时退票需要，已截止后上车点有效不能退/无效不需要)
            if order.bus_loc is not None:
                Boardingloc.objects.filter(id=order.bus_loc.id).update(choice_peoplenum=F('choice_peoplenum')-1)

            # 活动参与人数-1
            Activity.objects.filter(id=order.ticket.activity.id).update(current_participant=F('current_participant')-1)
            # 票销量-1
            Ticket.objects.filter(id=order.ticket.id).update(sales=F('sales')-1)
            # 用户积分-K
            User.objects.filter(id=order.user.id).update(points=F('points')-USER_POINTS_INCREASE_DELTA)



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
        if obj.bus_time is None:
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
        if obj.bus_time is None:
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
    #     if order.bus is None:
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

    boardingtime = serializers.SerializerMethodField()
    arrivaltime = serializers.SerializerMethodField()
    boardingloc = serializers.SerializerMethodField()
    arrivalloc = serializers.CharField(source='ticket.activity.activity_template.ski_resort.name')
    busnumber = serializers.SerializerMethodField()
    return_time = serializers.SerializerMethodField()
    return_loc = serializers.CharField(source='ticket.activity.activity_return_loc')

    schedule = serializers.CharField(source='ticket.activity.activity_template.schedule')
    attention = serializers.CharField(source='ticket.activity.activity_template.attention')
    qrcode = serializers.SerializerMethodField()
    leader_info = serializers.SerializerMethodField()
    
    boardingloc_available = serializers.SerializerMethodField()

    itinerary_status = serializers.SerializerMethodField()

    def get_begin_date(self, obj):
        begin_date_raw = obj.ticket.activity.activity_begin_date
        begin_date = begin_date_raw.strftime('%m月%d日')
        return begin_date
    def get_boardingloc(self, obj):
        if obj.bus_loc is None or obj.bus_loc.loc.busboardloc is None:
            return None
        else:
            return obj.bus_loc.loc.busboardloc
    def get_boardingtime(self, obj):
        if obj.bus_time is None or obj.bus_time.time is None:
            return None
        else:
            return obj.bus_time.time.strftime('%H:%M')
    def get_arrivaltime(self, obj):
        if obj.bus is None or obj.bus.arrival_time is None:
            return None
        else:
            return obj.bus.arrival_time.strftime('%H:%M')
    def get_busnumber(self, obj):
        if obj.bus is None or obj.bus.car_number is None:
            return None
        else:
            return obj.bus.car_number
    def get_return_time(self, obj):
        if obj.ticket.activity.activity_return_time is None:
            return None
        else:
            return obj.ticket.activity.activity_return_time.strftime('%H:%M')

    def get_qrcode(self, obj):
        actiwxgroup = obj.wxgroup.qrcode
        return settings.MEDIA_URL + str(actiwxgroup)
    def get_leader_info(self, obj):
        if obj.bus is None or obj.bus.leader is None:
            return None
        else:
            serializer = LeaderSerializer(instance=obj.bus.leader, many=False)
            return serializer.data

    def get_boardingloc_available(self, obj):
        if obj.bus_loc is None :
            return False
        else:
            return True

    def get_itinerary_status(self, obj):
        # 0 -- 上车点有效且未到行程第一天，不显示上车按钮
        # 1 -- 报名截止，且上车点无效，需要调用获取替换的上车点
        # 2 -- 活动当天，显示上车按钮
        # 3 -- 已上车未启动活动指引，显示活动指引启动按钮
        # 4 -- 活动指引已开始，显示活动指引各个步骤
        # 5 -- 已完成/跳过活动指引,，显示返程信息，不显示返程上车按钮
        # 6 -- 临近返程集合，显示返程信息和返程已上车按钮

        # 活动第一天前
            # 上车点有效 0
            # 上车点无效 1

        # 活动第一天
            # 去程未上车 2
            # 去程已上车，且返程以上车 6
            # 去程已上车，返程未上车，未启动教程 3
            # 去程已上车，返程未上车，已启动活动指引 4
            # 去程已上车，返程未上车，已完成/跳过活动指引 5

        current_date = timezone.now().date()
        # current_time = timezone.now().time()
        one_hour_later = (timezone.now() + timedelta(minutes=30)).time()
        if obj.ticket.activity.activity_begin_date > current_date:              # 出发日期前
            if obj.bus_loc is None:  # 上车点无效了
                return 1
            else:                    # 上车点有效
                return 0
        # elif obj.ticket.activity.activity_end_date == current_date and \
        #         one_hour_later > obj.ticket.activity.activity_return_time:      # 返程时间半小时内
        #     return 6
        else:                                                                   # 其他时间内
            if obj.go_boarded == False:  # 去程还未上车
                return 2
            else:                        # 上车了
                if obj.return_boarded == True:  # 返程已上车
                    return 6
                elif obj.completed_steps == 0:   # 未启动活动指引
                    return 3
                elif obj.completed_steps == len(ACTIVITY_GUIDE):  # 已完成/跳过活动指引
                    return 5
                else:
                    return 4

    class Meta:
        model = TicketOrder
        fields = ['name', 'ski_resort_location', 'begin_date', 'busnumber',
                  'to_area', 'ticket_intro', 'boardingtime', 'arrivaltime',
                  'boardingloc', 'arrivalloc', 'return_time', 'return_loc', 'schedule', 'attention',
                  'qrcode', 'leader_info', 'boardingloc_available', 'itinerary_status']

    # def getbus(self, order):
    #     if order.bus is None:
    #         return None
    #     else:
    #         return order.bus.car_number


class BusSerializer(serializers.ModelSerializer):
    bus_id = serializers.IntegerField(source='id')
    vacant_seat_num = serializers.SerializerMethodField()
    busnumber = serializers.CharField(source='car_number')
    # boardingtime = serializers.SerializerMethodField()

    def get_vacant_seat_num(self, obj):
        if (obj.carry_peoplenum is None) or (obj.max_people is None):
            return None
        else:
            return obj.max_people - obj.carry_peoplenum
    
    # def get_boardingtime(self, obj):
    #     if obj.car_number:
    #         return None
    #     else:
    #         return obj.car_number

    class Meta:
        model = Activity
        fields = ['bus_id', 'vacant_seat_num', 'busnumber']