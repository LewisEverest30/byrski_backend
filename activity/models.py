from django.db import models
from user.models import User, School
from rest_framework import serializers


class Skiresort(models.Model):
    name = models.CharField(verbose_name='滑雪场名', max_length=30)
    location = models.CharField(verbose_name='位置', max_length=200)

    def __str__(self) -> str:
        return self.name

class Activity(models.Model):
    ski_resort = models.ForeignKey(verbose_name='滑雪场', to=Skiresort, on_delete=models.PROTECT)
    # location = models.CharField(verbose_name='位置', max_length=200)

    date_arrangement = models.CharField(verbose_name='日期安排(文字描述)', max_length=300)
    duration_days = models.IntegerField(verbose_name='活动持续天数')
    notes = models.CharField(verbose_name='备注(不超过500字)', max_length=500, null=True, blank=True)
    price = models.IntegerField(verbose_name='活动价格')
    need_rent = models.BooleanField(verbose_name='是否提供租赁雪具服务', default=False)
    target_participant_num = models.IntegerField(verbose_name='目标报名人数')
    current_participant_num = models.IntegerField(verbose_name='当前报名人数', default=0)

    release_dt = models.DateTimeField(verbose_name='活动发布时间', auto_now_add=True)
    signup_ddl_d = models.DateField(verbose_name='活动截止报名日期(当天23:59截止报名)')

    registration_status = models.BooleanField(verbose_name='是否可以报名', default=True)

    def __str__(self) -> str:
        return self.ski_resort.name+' '+self.date_arrangement


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
    wrist_price = models.IntegerField(verbose_name='护腕单价')
    wrist_deposit = models.IntegerField(verbose_name='护腕押金')
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


class Bus(models.Model):
    activity = models.ForeignKey(verbose_name='活动', to=Activity, on_delete=models.PROTECT)

    car_number = models.CharField(verbose_name='车牌号', max_length=10)
    people_num = models.IntegerField(verbose_name='人数', default=0)
    route = models.CharField(verbose_name='路线规划', max_length=500, null=True)

class Bus_loc_time(models.Model):
    bus = models.ForeignKey(verbose_name='大巴', to=Bus, on_delete=models.CASCADE)
    loc = models.ForeignKey(verbose_name='途径点', to=School, on_delete=models.PROTECT)
    time = models.DateTimeField(verbose_name='途径时间')


class Order(models.Model):
    user = models.ForeignKey(verbose_name='用户', to=User, on_delete=models.CASCADE)
    activity = models.ForeignKey(verbose_name='活动', to=Activity, on_delete=models.PROTECT)
    
    need_rent = models.BooleanField(verbose_name='是否租赁')
    # rent_order = models.OneToOneField(verbose_name='租赁单', to=Rentorder, null=True, on_delete=models.SET_NULL)

    bus_loc = models.ForeignKey(verbose_name='上车点', to=School, on_delete=models.PROTECT)

    bus = models.ForeignKey(verbose_name='大巴', to=Bus, null=True, on_delete=models.CASCADE)
    bus_time = models.DateTimeField(verbose_name='上车时间', null=True)

    create_time = models.DateTimeField(verbose_name='下单时间', auto_now_add=True) 
    is_active = models.BooleanField(verbose_name='是否有效', default=True)


# 先有一个order，再可能有对应的rentorder
class Rentorder(models.Model):
    user = models.ForeignKey(verbose_name='用户', to=User, on_delete=models.CASCADE)
    price = models.ForeignKey(verbose_name='价格', to=Rentprice, on_delete=models.CASCADE)
    order = models.ForeignKey(verbose_name='对应活动订单', to=Order, on_delete=models.CASCADE)

    duration_days = models.IntegerField(verbose_name='租赁天数')

    helmet = models.BooleanField(verbose_name='头盔')
    glasses = models.BooleanField(verbose_name='学镜')
    gloves = models.BooleanField(verbose_name='手套')
    hippad = models.BooleanField(verbose_name='护臀')
    kneepad = models.BooleanField(verbose_name='护膝')
    wrist = models.BooleanField(verbose_name='护腕')
    snowboard = models.BooleanField(verbose_name='雪板')
    skiboots = models.BooleanField(verbose_name='雪鞋')


class ActivitySerializer(serializers.ModelSerializer):
    ski_resort_id = serializers.IntegerField(source='ski_resort.id')
    ski_resort = serializers.CharField(source='ski_resort.name')
    ski_resort_loc = serializers.CharField(source='ski_resort.location')
    class Meta:
        model = Activity
        fields = '__all__'

