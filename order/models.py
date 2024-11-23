from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from datetime import timedelta, datetime
from rest_framework import serializers
from django.conf import settings
from django.db.models import Q, F, Sum
from django.db import transaction
from django.core.validators import MinValueValidator
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from user.models import User, Leader, LeaderSerializer
from activity.models import Ticket, ActivityWxGroup, Activity, Boardingloc, Rentprice
from activity.utils import ACTIVITY_GUIDE

WXGROUP_MAX_NUM = 180
USER_POINTS_INCREASE_DELTA = 0
# =======================================================================================
# =====================================数据库表=============================================



# ========分车相关===========

# 大巴
class Bus(models.Model):
    activity = models.ForeignKey(verbose_name='活动', to=Activity, on_delete=models.PROTECT)

    car_number = models.CharField(verbose_name='车牌号', null=True, blank=True, max_length=10)
    driver_phone = models.CharField(verbose_name='司机手机号', max_length=11, null=True, blank=True)
    carry_peoplenum = models.IntegerField(verbose_name='车已承载人数', default=0, null=True, blank=True)  # 未上车人数 = 已承载人数 - 去程/返程上车人数
    # 实际最大承载人数-工作人员数，考虑变更上车点预留座位，比如55人车，2个工作人员，该字段为53（分车系统负责调整carry_peoplenum留出座位）
    max_people = models.IntegerField(verbose_name='车型最大承载人数', null=True, help_text='实际最大承载人数-工作人员数')
    
    arrival_time = models.TimeField(verbose_name='预计到达雪场时间', null=True, blank=False)
    route = models.CharField(verbose_name='路线规划', max_length=500, null=True, blank=True)

    go_finished = models.BooleanField(verbose_name='去程是否完成', default=False)
    ski_finished = models.BooleanField(verbose_name='滑雪是否完成', default=False)
    return_finished = models.BooleanField(verbose_name='返程是否完成', default=False)
    # leader = models.ForeignKey(verbose_name='领队', to=Leader, on_delete=models.PROTECT, null=True, blank=False)

    def __str__(self) -> str:
        return f'{self.activity} -- {self.car_number} (#{self.id})'
    
    class Meta:
        verbose_name = "大巴车"
        verbose_name_plural = "大巴车"


# 某个大巴经过某个上车点的时间。将大巴车与途径点构建多对多关系
class Bus_boarding_time(models.Model):
    bus = models.ForeignKey(verbose_name='大巴', to=Bus, on_delete=models.CASCADE)
    loc = models.ForeignKey(verbose_name='途径点', to=Boardingloc, on_delete=models.PROTECT)
    boarding_peoplenum = models.IntegerField(verbose_name='该点该车上车人数', default=0)
    time = models.TimeField(verbose_name='预计途径时间', null=True)

    go_finished = models.BooleanField(verbose_name='去程是否完成', default=False)

    def __str__(self) -> str:
        return f'{self.loc.loc.school.name+self.loc.loc.campus+self.loc.loc.busboardloc} -- {self.bus.car_number} -- {self.time} #{self.id}' 

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
        refunded = 5, _('已退款')
        delete = 6, _('删除')

    ordernumber = models.CharField(verbose_name='订单号', max_length=50, unique=True)

    user = models.ForeignKey(verbose_name='用户', to=User, on_delete=models.CASCADE)
    ticket = models.ForeignKey(verbose_name='票', to=Ticket, on_delete=models.PROTECT)
    cost = models.DecimalField(verbose_name='实付款', null=False, blank=False, max_digits=7, decimal_places=2,
                                validators=[MinValueValidator(1)])    
    wxgroup = models.ForeignKey(verbose_name='微信群', to=ActivityWxGroup, on_delete=models.SET_NULL, null=True, blank=True)
    # 允许上车点被删，set_null
    bus_loc = models.ForeignKey(verbose_name='上车点', to=Boardingloc, null=True, on_delete=models.SET_NULL)
    
    bus = models.ForeignKey(verbose_name='大巴', to=Bus, null=True, on_delete=models.SET_NULL, blank=True)
    bus_time = models.ForeignKey(verbose_name='上车时间', to=Bus_boarding_time, null=True, on_delete=models.SET_NULL, blank=True)

    ticket_checked = models.BooleanField(verbose_name='是否完成验票', null=False, blank=False, default=False)
    go_boarded = models.BooleanField(verbose_name='去程是否上车', null=False, blank=False, default=False)
    return_boarded = models.BooleanField(verbose_name='返程是否上车（订单是否已完成）', null=False, blank=False, default=False)
    completed_steps = models.IntegerField(verbose_name='已完成步数', null=False, blank=False, default=0, 
                                          help_text='未使用教程为0，处于第1步为1，完成第1步为2')
    
    create_time = models.DateTimeField(verbose_name='下单时间', auto_now_add=True) 
    pay_time = models.DateTimeField(verbose_name='付款时间', null=True)
    status = models.IntegerField(verbose_name='订单状态', null=False, default=1, choices=Status_choices.choices)

    cost_ticket = models.DecimalField(verbose_name='购票费用', null=False, blank=False, max_digits=7, decimal_places=2, default=0,)
    cost_rent = models.DecimalField(verbose_name='租赁费用', null=False, blank=False, max_digits=7, decimal_places=2, default=0,)
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
        with transaction.atomic():
            orders = cls.objects.select_for_update().filter(status=1, create_time__lt=threshold_time)

            # todo-f 移除订单有效性时，有一套需要联动的数据
            for order in orders:
                order.status = 0
                order.save()

                # 上车点人数-1(未截止时退票需要，已截止后上车点有效不能退/无效不需要)
                if order.bus_loc is not None:
                    Boardingloc.objects.filter(id=order.bus_loc.id).update(choice_peoplenum=F('choice_peoplenum')-1)

                # 活动参与人数-1
                Activity.objects.filter(id=order.ticket.activity.id).update(current_participant=F('current_participant')-1)
                # 票销量-1
                Ticket.objects.filter(id=order.ticket.id).update(sales=F('sales')-1)
                # 用户积分-K
                User.objects.filter(id=order.user.id).update(points=F('points')-USER_POINTS_INCREASE_DELTA)
                # 用户节省金额-差价
                User.objects.filter(id=order.user.id).update(saved_money=F('saved_money')-(order.ticket.original_price - order.cost))

    @classmethod
    def set_orders_finished(cls):
        # todo-f 当前日期超过活动最后日期的，自动设置为已完成状态
        with transaction.atomic():
            today = timezone.now().date()
            cls.objects.select_for_update().filter(ticket__activity__activity_end_date__lt=today).update(return_boarded=True)


class Rentorder(models.Model):
    user = models.ForeignKey(verbose_name='用户', to=User, on_delete=models.CASCADE, null=False, blank=False)
    order = models.ForeignKey(verbose_name='对应活动订单', to=TicketOrder, on_delete=models.CASCADE, null=False, blank=False)

    rent_item = models.ForeignKey(verbose_name='租赁项目', to=Rentprice, on_delete=models.PROTECT, null=False, blank=False)

    rent_days = models.IntegerField(verbose_name='租赁天数', null=False, blank=False, validators=[MinValueValidator(1)])
    # cost = models.DecimalField(verbose_name='实付款', null=False, blank=False, max_digits=7, decimal_places=2,
    #                             validators=[MinValueValidator(1)])    

    # status 直接取order的status
    # is_active = models.BooleanField(verbose_name='是否有效(活动订单是否付款)', default=False)

    class Meta:
        verbose_name = "租赁单"
        verbose_name_plural = "租赁单"


# 领队行程
class LeaderItinerary(models.Model):
    # class Status_choices(models.IntegerChoices):
    #     cancelled = 0, _('未开始')
    #     pending_payment = 1, _('进行中')
    #     paid = 2, _('已完成')

    leader = models.ForeignKey(verbose_name='领队', to=Leader, on_delete=models.CASCADE)
    # activity = models.ForeignKey(verbose_name='活动', to=Activity, on_delete=models.PROTECT)  # bus中已经有activity
    bus = models.ForeignKey(verbose_name='大巴', to=Bus, null=False, on_delete=models.CASCADE)
    bus_loc = models.ForeignKey(verbose_name='上车点', to=Boardingloc, null=False, on_delete=models.CASCADE)

    create_time = models.DateTimeField(verbose_name='创建时间', auto_now_add=True) 
    # status = models.IntegerField(verbose_name='行程状态', null=False, default=1, choices=Status_choices.choices)

    def __str__(self) -> str:
        return f'{self.leader.user.name}的{self.bus.activity.activity_template.name}行程'
    
    class Meta:
        verbose_name = "领队行程"
        verbose_name_plural = "领队行程"
# 创建LeaderItinerary时通过信号机制来设置Leader表的内容
@receiver(post_save, sender=LeaderItinerary)
def set_leader_subject(sender, instance, created, **kwargs):
    if created:  # 如果是新创建的
        instance.leader.leadtimes += 1
        instance.leader.save()
# 删除LeaderItinerary时通过信号机制来设置Leader表的内容
@receiver(post_delete, sender=LeaderItinerary)
def unset_leader_subject(sender, instance, **kwargs):
    instance.leader.leadtimes -= 1
    instance.leader.save()

















# ========================================================================================
# ===================================序列化器==============================================

# ==============================行程相关==============================================


# 用于下单后的行程卡
class OrderSerializer2(serializers.ModelSerializer):
    ski_resort_name = serializers.CharField(source='ticket.activity.activity_template.ski_resort.name')
    location = serializers.CharField(source='ticket.activity.activity_template.ski_resort.location')
    ski_resort_phone = serializers.CharField(source='ticket.activity.activity_template.ski_resort.phone')
    hotel = serializers.SerializerMethodField()

    from_area = serializers.CharField(source='bus_loc.loc.area.area_name')
    to_area = serializers.CharField(source='ticket.activity.activity_template.ski_resort.area.area_name')

    # bus = serializers.SerializerMethodField(method_name='getbus')
    # boardingloc = serializers.CharField(source='bus_loc.loc.busboardloc')
    boardingloc = serializers.SerializerMethodField()
    boardingtime = serializers.SerializerMethodField()

    name = serializers.CharField(source='user.name')
    gender = serializers.IntegerField(source='user.gender')
    phone = serializers.CharField(source='user.phone')

    qrcode = serializers.SerializerMethodField()

    def get_boardingloc(self, obj):
        if obj.bus_loc is None or obj.bus_loc.loc is None:
            return None
        else:
            return obj.bus_loc.loc.school.name + obj.bus_loc.loc.campus + obj.bus_loc.loc.busboardloc

    def get_boardingtime(self, obj):
        if obj.bus_time is None or obj.bus_time.time is None:
            return None
        else:
            return obj.bus_time.time.strftime('%H:%M')

    def get_qrcode(self, obj):
        actiwxgroup = obj.wxgroup.qrcode
        return settings.MEDIA_URL + str(actiwxgroup)

    def get_hotel(self, obj):
        if obj.ticket.hotel is None:
            return None
        else:
            return obj.ticket.hotel

    class Meta:
        model = TicketOrder
        fields = ['ski_resort_name', 'location', 'ski_resort_phone', 'hotel',
                  'from_area', 'to_area', 'boardingloc', 'boardingtime',
                  'name', 'gender', 'phone', 'qrcode']


# 用于行程列表
class OrderSerializerItinerary1(serializers.ModelSerializer):
    name = serializers.CharField(source='ticket.activity.activity_template.name')
    ski_resort_location = serializers.CharField(source='ticket.activity.activity_template.ski_resort.location')
    begin_date = serializers.SerializerMethodField()
    to_area = serializers.CharField(source='ticket.activity.activity_template.ski_resort.area.area_name')
    ticket_intro = serializers.CharField(source='ticket.intro')

    boardingtime = serializers.SerializerMethodField()
    boardingloc = serializers.SerializerMethodField()

    def get_begin_date(self, obj):
        begin_date_raw = obj.ticket.activity.activity_begin_date
        begin_date = begin_date_raw.strftime('%Y年%m月%d日')

        return begin_date

    def get_boardingloc(self, obj):
        if obj.bus_loc is None or obj.bus_loc.loc is None:
            return None
        else:
            if obj.status == 3:  # 已锁票
                return obj.bus_loc.loc.school.name + obj.bus_loc.loc.campus + obj.bus_loc.loc.busboardloc
            else:  # 未锁票
                return obj.bus_loc.loc.school.name + obj.bus_loc.loc.campus + obj.bus_loc.loc.busboardloc + '(待定)'
    def get_boardingtime(self, obj):
        if obj.bus_time is None or obj.bus_time.time is None:
            return None
        else:
            return obj.bus_time.time.strftime('%H:%M')

    class Meta:
        model = TicketOrder
        fields = ['id', 'name', 'ski_resort_location', 'begin_date',
                  'to_area', 'ticket_intro', 
                  'boardingtime', 'boardingloc']


# 用于行程详情
class OrderSerializerItinerary2(serializers.ModelSerializer):
    activity_id = serializers.IntegerField(source='ticket.activity.id')
    name = serializers.CharField(source='ticket.activity.activity_template.name')
    ski_resort_location = serializers.CharField(source='ticket.activity.activity_template.ski_resort.location')
    begin_date = serializers.SerializerMethodField()
    to_area = serializers.CharField(source='ticket.activity.activity_template.ski_resort.area.area_name')
    ticket_intro = serializers.CharField(source='ticket.intro')
    hotel = serializers.SerializerMethodField()

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
    is_activity_expired = serializers.SerializerMethodField()

    def get_hotel(self, obj):
        if obj.ticket.hotel is None:
            return None
        else:
            return obj.ticket.hotel

    def get_begin_date(self, obj):
        begin_date_raw = obj.ticket.activity.activity_begin_date
        begin_date = begin_date_raw.strftime('%m月%d日')
        return begin_date
    def get_boardingloc(self, obj):
        if obj.bus_loc is None or obj.bus_loc.loc is None:
            return None
        else:
            return obj.bus_loc.loc.school.name + obj.bus_loc.loc.campus + obj.bus_loc.loc.busboardloc
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
        if obj.bus is None:
            return None
        leader_itinerary = LeaderItinerary.objects.filter(bus_id=obj.bus.id)
        if leader_itinerary.count() == 0:
            return None
        else:
            leader = leader_itinerary[0].leader
            serializer = LeaderSerializer(instance=leader, many=False)
            return serializer.data
        # if obj.bus is None or obj.bus.leader is None:
        #     return None
        # else:
        #     serializer = LeaderSerializer(instance=obj.bus.leader, many=False)
        #     return serializer.data

    def get_boardingloc_available(self, obj):
        if obj.bus_loc is None :
            return False
        else:
            return True

    def get_itinerary_status(self, obj):
        # 0 -- 上车点有效且未到 始发点时间0.5小时内  ，不显示上车按钮
        # 1 -- 报名截止，且上车点无效，需要调用获取替换的上车点
        # 2 -- 活动当天始发站0.5小时内，显示上车按钮和验票按钮
        # 7 -- 已上车后且未验票，验票页面
        # 3 -- 已上车且已完成验票，未启动活动指引，显示活动指引启动按钮
        # 4 -- 活动指引已开始，显示活动指引各个步骤
        # 5 -- 已完成/跳过活动指引,，显示返程信息，直接显示返程上车按钮
        # 6 -- 返程已上车，返程上车按钮变灰色
    

        # 活动第一天前
            # 上车点有效 0
            # 上车点无效 1

        # 活动第一天到最后一天
            # 去程未上车且距离站点预计到达时间0.5小时以外 1
            # 去程未上车且距离站点预计到达时间0.5小时内 2
            # 去程已上车，且返程上车了 6
            # 去程上车了，且返程未上车，且未验票，7
            # 去程已上车，返程未上车，未启动教程 3
            # 去程已上车，返程未上车，已启动活动指引 4
            # 去程已上车，返程未上车，已完成/跳过活动指引 5

        current_date = timezone.now().date()
        # current_time = timezone.now().time()
        # one_hour_later = (timezone.now() + timedelta(minutes=30)).time()
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
                if obj.bus_time is not None and obj.bus_time.time is not None :
                    bus_datetime = datetime.combine(
                        obj.ticket.activity.activity_begin_date,  # 活动开始日期
                        obj.bus_time.time  # 预计上车时间
                    )
                    if bus_datetime < (timezone.now() + timedelta(minutes=30)):  # 上车时间半小时内
                        return 2
                    else:
                        return 0
                else:
                    return 0
            else:                        # 上车了
                if obj.return_boarded == True:  # 返程已上车
                    return 6
                elif obj.ticket_checked == False:  # 去程上车了，且返程未上车，且未验票
                    return 7
                elif obj.completed_steps == 0:   # 去程上车了，且返程未上车，且已经完成验票，未启动活动指引
                    return 3
                elif obj.completed_steps == len(ACTIVITY_GUIDE):  # 去程上车了，且返程未上车，且已经完成验票，已完成/跳过活动指引
                    return 5
                else:  # 去程上车了，且返程未上车，且已经完成验票，且处在活动指引中
                    return 4

    def get_is_activity_expired(self, obj):
        if obj.ticket.activity.status >= 1:
            return True
        else:
            return False
        
    
    class Meta:
        model = TicketOrder
        fields = ['activity_id', 'ordernumber', 'name', 'ski_resort_location', 'begin_date', 'busnumber',
                  'to_area', 'ticket_intro', 'boardingtime', 'arrivaltime',
                  'boardingloc', 'arrivalloc', 'return_time', 'return_loc', 'schedule', 'attention',
                  'qrcode', 'leader_info', 'boardingloc_available', 'itinerary_status', 'is_activity_expired']


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



# ===================================订单相关====================================
# 用于获取雪具租赁单信息
class RentorderSerializer(serializers.ModelSerializer):
    rent_order_item_id = serializers.IntegerField(source='id')

    name = serializers.CharField(source='rent_item.name')
    price = serializers.CharField(source='rent_item.price')
    deposit = serializers.CharField(source='rent_item.deposit')
    
    class Meta:
        model = Rentorder
        fields = ['rent_order_item_id', 'name', 'price', 'deposit', 'rent_days']

# 用于订单列表
class OrderSerializer3(serializers.ModelSerializer):
    activity_name = serializers.SerializerMethodField()
    begin_date = serializers.SerializerMethodField()
    intro = serializers.CharField(source='ticket.intro')
    cover = serializers.SerializerMethodField()
    original_price = serializers.CharField(source='ticket.original_price')
    
    def get_activity_name(self, obj):
        # todo 增加hotel
        if obj.ticket.hotel is None:
            return obj.ticket.activity.activity_template.name
        else:
            return obj.ticket.activity.activity_template.name + ' | ' + obj.ticket.hotel

    def get_begin_date(self, obj):
        begin_date_raw = obj.ticket.activity.activity_begin_date
        begin_date = begin_date_raw.strftime('%m月%d日')
        return begin_date

    def get_cover(self, obj):
        return settings.MEDIA_URL + str(obj.ticket.activity.activity_template.ski_resort.cover)

    class Meta:
        model = TicketOrder
        fields = ['id', 'activity_name', 'begin_date', 'intro', 'cover', 'original_price', 'cost']


# 用于订单详情
class OrderSerializer4(serializers.ModelSerializer):
    ticket_id = serializers.IntegerField(source='ticket.id')
    # status_description = serializers.SerializerMethodField()
    pay_ddl = serializers.SerializerMethodField()

    activity_name = serializers.SerializerMethodField()
    begin_date = serializers.SerializerMethodField()
    intro = serializers.CharField(source='ticket.intro')
    cover = serializers.SerializerMethodField()
    original_price = serializers.CharField(source='ticket.original_price')

    name = serializers.CharField(source='user.name')
    gender = serializers.IntegerField(source='user.gender')
    phone = serializers.CharField(source='user.phone')
    idnumber = serializers.CharField(source='user.idnumber')

    status = serializers.SerializerMethodField()
    can_refund = serializers.SerializerMethodField()

    rent_order = serializers.SerializerMethodField()
    def get_rent_order(self, obj):
        rent_order_item = Rentorder.objects.filter(order_id=obj.id)
        if rent_order_item.count() > 0:
            rent_order_item_serializer = RentorderSerializer(instance=rent_order_item, many=True)
            return {
                'rent_order_item': list(rent_order_item_serializer.data),
                'total_price': rent_order_item.aggregate(Sum('rent_item__price'))['rent_item__price__sum'],
                'total_deposit': rent_order_item.aggregate(Sum('rent_item__deposit'))['rent_item__deposit__sum']
            }
        else:
            return None

    def get_activity_name(self, obj):
        # todo 增加hotel
        if obj.ticket.hotel is None:
            return obj.ticket.activity.activity_template.name
        else:
            return obj.ticket.activity.activity_template.name + ' | ' + obj.ticket.hotel

    def get_status(self, obj):
        if obj.status == 3 and obj.return_boarded == True:  # 已完成=已锁票+返程已上车
            return 8
        elif obj.status == 2 and obj.bus_loc is None:   # 待确认=已付款+上车点无效
            return 7
        else:
            return obj.status
    # def get_status_description(self, obj):
    #     if obj.status == 0:
    #         return "交易关闭"
    #     elif obj.status == 1:
    #         return "待付款"
    #     elif (obj.status == 2 or obj.status == 3):
    #         if obj.return_boarded==False:
    #             return "进行中"
    #         else:
    #             return "已完成"
    #     elif obj.status == 4:
    #         return "退款中"
    #     elif obj.status == 5:
    #         return "已退款"
    #     else:
    #         return "异常状态"
    def get_can_refund(self, obj):
        if obj.status == 2:
            if obj.ticket.activity.status == 1 and obj.bus_loc is not None:  # 活动截止报名，且上车点有效
                return False
            if obj.ticket.activity.status == 2:  # 活动已锁票
                return False
            return True
        else:
            return False
        
    def get_pay_ddl(self, obj):
        ddl = obj.create_time + timedelta(minutes=19)
        return ddl.strftime('%H:%M')

    def get_begin_date(self, obj):
        begin_date_raw = obj.ticket.activity.activity_begin_date
        begin_date = begin_date_raw.strftime('%m月%d日')
        return begin_date

    def get_cover(self, obj):
        return settings.MEDIA_URL + str(obj.ticket.activity.activity_template.ski_resort.cover)

    class Meta:
        model = TicketOrder
        fields = ['id', 'status', 'pay_ddl', 'activity_name', 'begin_date', 'intro', 
                  'cover', 'original_price', 'cost', 'status','can_refund',
                #   'status_description',
                  'name', 'gender', 'phone', 'idnumber', 'cost_rent', 'rent_order',
                  'ordernumber', 'create_time', 'pay_time', 'ticket_id']





# ===================================领队相关====================================

# 用于行程列表
class LeaderItinerarySerializer1(serializers.ModelSerializer):
    activity_name = serializers.CharField(source='bus.activity.activity_template.name')
    skiresort_location = serializers.CharField(source='bus.activity.activity_template.ski_resort.location')
    begin_date = serializers.SerializerMethodField()
    to_area = serializers.CharField(source='bus.activity.activity_template.ski_resort.area.area_name')

    boardingtime = serializers.SerializerMethodField()
    boardingloc = serializers.SerializerMethodField()

    def get_boardingloc(self, obj):
        if obj.bus_loc is None or obj.bus_loc.loc is None:
            return None
        else:
            return obj.bus_loc.loc.school.name + obj.bus_loc.loc.campus + obj.bus_loc.loc.busboardloc
    def get_boardingtime(self, obj):
        bus_time = Bus_boarding_time.objects.filter(bus_id=obj.bus.id, loc_id=obj.bus_loc.id).first()
        if bus_time is None or bus_time.time is None:
            return None
        else:
            return bus_time.time.strftime('%H:%M')

    def get_begin_date(self, obj):
        begin_date_raw = obj.bus.activity.activity_begin_date
        begin_date = begin_date_raw.strftime('%Y年%m月%d日')

        return begin_date

    class Meta:
        model = LeaderItinerary
        fields = ['id', 'activity_name', 'skiresort_location', 'begin_date', 'to_area',
                  'boardingtime', 'boardingloc']


# 用于领队行程详情
class LeaderItinerarySerializer2(serializers.ModelSerializer):
    activity_name = serializers.CharField(source='bus.activity.activity_template.name')
    ski_resort_location = serializers.CharField(source='bus.activity.activity_template.ski_resort.location')
    begin_date = serializers.SerializerMethodField()
    to_area = serializers.CharField(source='bus.activity.activity_template.ski_resort.area.area_name')

    boardingtime = serializers.SerializerMethodField()
    arrivaltime = serializers.SerializerMethodField()
    boardingloc = serializers.SerializerMethodField()
    arrivalloc = serializers.CharField(source='bus.activity.activity_template.ski_resort.name')
    busnumber = serializers.SerializerMethodField()
    return_time = serializers.SerializerMethodField()
    return_loc = serializers.CharField(source='bus.activity.activity_return_loc')

    notice = serializers.CharField(source='bus.activity.activity_template.leader_notice')
    schedule = serializers.CharField(source='bus.activity.activity_template.schedule')
    attention = serializers.CharField(source='bus.activity.activity_template.attention')

    itinerary_status = serializers.SerializerMethodField()

    bus_stop = serializers.SerializerMethodField()
    

    def get_begin_date(self, obj):
        begin_date_raw = obj.bus.activity.activity_begin_date
        begin_date = begin_date_raw.strftime('%m月%d日')
        return begin_date
    def get_boardingloc(self, obj):
        if obj.bus_loc is None or obj.bus_loc.loc is None:
            return None
        else:
            return obj.bus_loc.loc.school.name + obj.bus_loc.loc.campus + obj.bus_loc.loc.busboardloc
    def get_boardingtime(self, obj):
        bus_time = Bus_boarding_time.objects.filter(bus_id=obj.bus.id, loc_id=obj.bus_loc.id).first()
        if bus_time is None or bus_time.time is None:
            return None
        else:
            return bus_time.time.strftime('%H:%M')
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
        if obj.bus.activity.activity_return_time is None:
            return None
        else:
            return obj.bus.activity.activity_return_time.strftime('%H:%M')
    def get_itinerary_status(self, obj):
        # 0 -- 未到行程第一天。不显示上车情况
        # 1 -- 有去程未上车的人。显示去程上车情况，以及验票按钮（万一有人没来，人不齐也能验票）
        # 2 -- 去程全部上车。不显示去程上车情况，显示验票按钮和验票人数情况
        # 3 -- 点击了结束滑雪，开始显示返程上车情况
        # 4 -- 点击了开始返程，“开始返程”按钮变灰色

        current_date = timezone.now().date()
        if obj.bus.activity.activity_begin_date > current_date:              # 出发日期前
            return 0
        elif obj.bus.return_finished == True:      # 点击了完成返程
            return 4
        elif obj.bus.ski_finished == True:      # 点击了结束滑雪
            return 3
        else:
            if obj.bus.go_finished == False:          # 去程未全部上车
                return 1
            else:
                return 2
    def get_bus_stop(self, obj):
        # 上车点id+上车点名
        stop_set = Bus_boarding_time.objects.filter(bus_id=obj.bus.id).order_by('time').values('loc__id', 'loc__loc__school__name', 
                                                                                               'loc__loc__campus', 'loc__loc__busboardloc',
                                                                                               'go_finished', 'time')
        
        for stop in stop_set:
            stop['id'] = stop.pop('loc__id')    # 把loc__id重命名为id
            stop['bus_stop'] = {
                'school': stop.pop('loc__loc__school__name'),
                'campus': stop.pop('loc__loc__campus'),
                'busboardloc': stop.pop('loc__loc__busboardloc'),
                'go_finished': stop.pop('go_finished'),
                'time': stop.pop('time').strftime('%H:%M'),
            }
        return stop_set


    class Meta:
        model = LeaderItinerary
        fields = ['activity_name', 'ski_resort_location', 'begin_date', 'to_area', 
                  'busnumber', 'boardingtime', 'arrivaltime','boardingloc', 'arrivalloc', 'return_time', 'return_loc',
                  'notice', 'schedule', 'attention',
                  'itinerary_status', 'bus_stop',
                  'bus_id', ]


    # def get_go_boarding_info(self, obj):
    #     boarded_passenger_num = TicketOrder.objects.filter(bus_id=obj.bus.id, go_boarded=True).count()
    #     ret_dict = {
    #         "total_passenger": obj.bus.carry_peoplenum,
    #         "boarded_passenger": boarded_passenger_num,
    #         "unboarded_passenger": obj.bus.carry_peoplenum - boarded_passenger_num,
    #     }
    #     return ret_dict

    # def get_return_boarding_info(self, obj):
    #     boarded_passenger_num = TicketOrder.objects.filter(bus_id=obj.bus.id, return_boarded=True).count()
    #     ret_dict = {
    #         "total_passenger": obj.bus.carry_peoplenum,
    #         "boarded_passenger": boarded_passenger_num,
    #         "unboarded_passenger": obj.bus.carry_peoplenum - boarded_passenger_num,
    #     }
    #     return ret_dict
