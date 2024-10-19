from django.db import models
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from user.models import User
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
    
    route = models.CharField(verbose_name='路线规划', max_length=500, null=True, blank=True)

    leader = models.ForeignKey(verbose_name='领队', to=User, on_delete=models.PROTECT, null=True, blank=True)

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
    time = models.DateTimeField(verbose_name='预计途径时间', null=True)

    def __str__(self) -> str:
        return str(self.time)

    class Meta:
        verbose_name = "车-途径点-时间 对应关系"
        verbose_name_plural = "车-途径点-时间 对应关系"




# =========活动订单===========


# 雪票订单 + 行程
class TicketOrder(models.Model):
    class Status_choices(models.IntegerChoices):
        cancelled = 0, _('已取消')
        pending_payment = 1, _('待付款')
        pending_shipment = 2, _('已付款')
        pending_receipt = 3, _('已锁票')

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




# ========================================================================================
# ===================================序列化器==============================================

class OrderSerializer(serializers.ModelSerializer):
    ski_resort = serializers.CharField(source='activity.ski_resort.name')
    ski_resort_loc = serializers.CharField(source='activity.ski_resort.location')
    date_arrangement = serializers.CharField(source='activity.date_arrangement')
    bus = serializers.SerializerMethodField(method_name='getbus')
    bus_loc = serializers.CharField(source='bus_loc.loc.campus')
    bus_time = serializers.SerializerMethodField(method_name='getbus_time')

    class Meta:
        model = TicketOrder
        fields = '__all__'

    def getbus(self, order):
        if order.bus == None:
            return None
        else:
            return order.bus.car_number

    def getbus_time(self, order):
        if order.bus_time == None:
            return None
        else:
            return order.bus_time.time
