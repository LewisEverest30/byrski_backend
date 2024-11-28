from django.db import models
from user.models import User, School
from rest_framework import serializers


class Skiresort(models.Model):
    name = models.CharField(verbose_name='滑雪场名', max_length=30)
    location = models.CharField(verbose_name='位置', max_length=200)

    def __str__(self) -> str:
        return self.name
    
    class Meta:
        verbose_name = "滑雪场"
        verbose_name_plural = "滑雪场"

class Activity(models.Model):
    ski_resort = models.ForeignKey(verbose_name='滑雪场', to=Skiresort, on_delete=models.PROTECT)
    # location = models.CharField(verbose_name='位置', max_length=200)

    date_arrangement = models.CharField(verbose_name='日期安排(文字描述)', max_length=300)
    duration_days = models.IntegerField(verbose_name='持续天数')
    notes = models.CharField(verbose_name='备注(不超过500字)', max_length=500, null=True, blank=True)
    price = models.IntegerField(verbose_name='价格')
    need_rent = models.BooleanField(verbose_name='提供租赁', default=False)
    target_participant_num = models.IntegerField(verbose_name='目标报名人数')
    current_participant_num = models.IntegerField(verbose_name='当前报名人数', default=0)

    release_dt = models.DateTimeField(verbose_name='发布时间', auto_now_add=True)
    signup_ddl_d = models.DateField(verbose_name='截止报名日期\n(当天23:59截止报名)')

    registration_status = models.BooleanField(verbose_name='是否可以报名', default=True)

    def __str__(self) -> str:
        return str(self.id)+'_'+self.ski_resort.name+'_'+self.date_arrangement

    class Meta:
        verbose_name = "活动"
        verbose_name_plural = "活动"


class Rentprice(models.Model):
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
    snowboard_price = models.IntegerField(verbose_name='雪板单价')
    snowboard_deposit = models.IntegerField(verbose_name='雪板押金')
    # snowboard1_price = models.IntegerField(verbose_name='单板单价')
    # snowboard1_deposit = models.IntegerField(verbose_name='单板押金')
    # snowboard2_price = models.IntegerField(verbose_name='双板单价')
    # snowboard2_deposit = models.IntegerField(verbose_name='双板押金')
    skiboots_price = models.IntegerField(verbose_name='雪鞋单价')
    skiboots_deposit = models.IntegerField(verbose_name='雪鞋押金')

    def __str__(self) -> str:
        return self.ski_resort.name

    class Meta:
        verbose_name = "雪具租赁价格"
        verbose_name_plural = "雪具租赁价格"


class Busloc(models.Model):
    activity = models.ForeignKey(verbose_name='活动', to=Activity, on_delete=models.PROTECT)
    loc = models.ForeignKey(verbose_name='上车点', to=School, on_delete=models.PROTECT)
    loc_peoplenum = models.IntegerField(verbose_name='人数', default=0)

    def __str__(self) -> str:
        return str(self.loc)+' ('+str(self.activity)+')'
    
    class Meta:
        verbose_name = "上车点"
        verbose_name_plural = "上车点"
        unique_together = (("activity", "loc"),)


class Bus(models.Model):
    activity = models.ForeignKey(verbose_name='活动', to=Activity, on_delete=models.PROTECT)

    car_number = models.CharField(verbose_name='车牌号', null=True, max_length=10)
    bus_peoplenum = models.IntegerField(verbose_name='该车总人数', default=0)
    route = models.CharField(verbose_name='路线规划', max_length=500, null=True)
    max_people = models.IntegerField(verbose_name='车型最大承载人数', null=True)

    def __str__(self) -> str:
        return str(self.car_number) + ' ( id: ' + str(self.id) + ', 乘客数: ' + str(self.bus_peoplenum) + ')'
    
    class Meta:
        verbose_name = "大巴车"
        verbose_name_plural = "大巴车"


class Bus_loc_time(models.Model):
    bus = models.ForeignKey(verbose_name='大巴', to=Bus, on_delete=models.CASCADE)
    loc = models.ForeignKey(verbose_name='途径点', to=Busloc, on_delete=models.PROTECT)
    bus_loc_peoplenum = models.IntegerField(verbose_name='该点该车上车人数', default=0)
    time = models.DateTimeField(verbose_name='途径时间', null=True)

    def __str__(self) -> str:
        return str(self.time)

    class Meta:
        verbose_name = "车-途径点-时间 对应关系"
        verbose_name_plural = "车-途径点-时间 对应关系"



class Order(models.Model):
    ordernumber = models.CharField(verbose_name='订单号', max_length=50, unique=True)

    user = models.ForeignKey(verbose_name='用户', to=User, on_delete=models.CASCADE)
    activity = models.ForeignKey(verbose_name='活动', to=Activity, on_delete=models.PROTECT)
    
    need_rent = models.BooleanField(verbose_name='是否租赁', default=False)
    # rent_order = models.OneToOneField(verbose_name='租赁单', to=Rentorder, null=True, on_delete=models.SET_NULL)

    bus_loc = models.ForeignKey(verbose_name='上车点', to=Busloc, on_delete=models.PROTECT)
    bus = models.ForeignKey(verbose_name='大巴', to=Bus, null=True, on_delete=models.SET_NULL, blank=True)
    bus_time = models.ForeignKey(verbose_name='上车时间', to=Bus_loc_time, null=True, on_delete=models.SET_NULL, blank=True)

    create_time = models.DateTimeField(verbose_name='下单时间', auto_now_add=True) 
    is_paid = models.BooleanField(verbose_name='是否支付', default=False)

    def __str__(self) -> str:
        return self.ordernumber
    
    class Meta:
        verbose_name = "活动订单"
        verbose_name_plural = "活动订单"


# 先有一个order，再可能有对应的rentorder
class Rentorder(models.Model):
    user = models.ForeignKey(verbose_name='用户', to=User, on_delete=models.CASCADE)
    order = models.ForeignKey(verbose_name='对应活动订单', to=Order, on_delete=models.CASCADE)
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


class ActivitySerializer(serializers.ModelSerializer):
    ski_resort_id = serializers.IntegerField(source='ski_resort.id')
    ski_resort = serializers.CharField(source='ski_resort.name')
    ski_resort_loc = serializers.CharField(source='ski_resort.location')
    class Meta:
        model = Activity
        fields = '__all__'


class BuslocSerializer(serializers.ModelSerializer):
    loc = serializers.CharField(source='loc.busboardloc')
    loc_id = serializers.IntegerField(source='loc.id')
    class Meta:
        model = Busloc
        fields = '__all__'


class OrderSerializer(serializers.ModelSerializer):
    ski_resort = serializers.CharField(source='activity.ski_resort.name')
    ski_resort_loc = serializers.CharField(source='activity.ski_resort.location')
    date_arrangement = serializers.CharField(source='activity.date_arrangement')
    bus = serializers.SerializerMethodField(method_name='getbus')
    bus_loc = serializers.CharField(source='bus_loc.loc.campus')
    bus_time = serializers.SerializerMethodField(method_name='getbus_time')

    class Meta:
        model = Order
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

