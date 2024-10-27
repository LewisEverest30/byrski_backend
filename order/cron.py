import datetime
from django.db.models import F, Q, Sum
from .models import Bus, Boardingloc, Bustype, Bus_boarding_time
from django.db import transaction

from activity.models import Activity, AreaBoardingLowerLimit, Ticket
from order.models import TicketOrder, USER_POINTS_INCREASE_DELTA
from user.models import User
import datetime


DEFAULT_BIG_BUS = 53
DEFAULT_SMALL_BUS = 33
EMPTY_SEAT_BUFFER = 5
STAFF_NUM = 1

def get_bus_allocation(big, small, people):
    n_big = 0
    n_small = 0

    if big >= 2*small:  # 大车承载人数超过了小车的两倍
        q, r = divmod(people, big)
        if r==0:    # 大车刚好够用
            n_big = q
            n_small = 0
            return (n_big, n_small)
        if r > small:  
            # 余下的人小车装不下，这时选择使用大车
            # （如果把前面的人放一起用更多的小车，至少会拆出来4小）（至少4小vs至多2大）
            n_big = q + 1
            n_small = 0
            return (n_big, n_small)
        else:
            n_big = q
            n_small = 1
            return (n_big, n_small)
    else:
        # 下面只考虑两种拆大换小的情况：‘一大化两小’，‘两大化三小’
        # 一大（加余数）有三种种可能，两大 or 一大一小 or 两小
        # 两个以上大（加余数）
            # 先考虑从q中拿出两大加余数，种可能，三小 or 一大两小 or 两大一小 or  三大
            # 如果q中还剩下，直接使用大车，不继续深入考虑替换策略了（这是无穷的，有优化空间，后面可以改进）
        k = 2*small - big
        m = 3*small - 2*big
        q, r = divmod(people, big)

        if r==0:
            n_big = q
            n_small = 0
            return (n_big, n_small)
        if q == 1:   # 拿不出2个大车，只考虑一大化两小
            if r <= k:
                n_big = q - 1
                n_small = 2
            elif r > k and r <= small:
                n_big = q
                n_small = 1
            else:
                n_big = q + 1
                n_small = 0
        elif q > 1:  # 能拿出2个大车，考虑两大化三小
            if r <= m:
                n_big = q - 2
                n_small = 3
            elif r > m and r <= k:
                n_big = q - 1
                n_small = 2
            elif r > k and r <= small:
                n_big = q
                n_small = 1
            else:
                n_big = q + 1
                n_small = 0

        else:  # 凑不齐一辆大车
            if r <= small:
                n_big = 0
                n_small = 1
            else:
                n_big = 1
                n_small = 0

    return (n_big, n_small)


# 活动截止报名之时
def set_activity_expire():
    print ('================ SET ACTIVITY EXPIRE ',str(datetime.datetime.now()), '================')
    # 将到期的活动设为不可报名
    try:
        acti_objs = Activity.objects.filter(signup_ddl_date__lt = datetime.date.today(), status=0)
        acti_objs_id = [i.id for i in acti_objs]  # 同一天可能有不止一个活动截止报名
        acti_objs.update(registration_status=False)
    except Exception as e:
        print('Fail to set activity as <prevent_signup> ', str(datetime.datetime.now()), repr(e))
    
    # 在实际分车前，先为每个活动剔除无效的订单 和 无效的上车点
    for acti in acti_objs:
        # 清除待付款订单
        with transaction.atomic():
            unpaid_orders = TicketOrder.objects.select_for_update().filter(status=1, ticket__activity__id=acti.id)
            unpaid_orders.update(status=0)
            for order in unpaid_orders:
                # 上车点人数-1，先于区域和上车点合法性检查
                if order.bus_loc is not None:
                    Boardingloc.objects.filter(id=order.bus_loc.id).update(choice_peoplenum=F('choice_peoplenum')-1)
                Activity.objects.filter(id=order.ticket.activity.id).update(current_participant=F('current_participant')-1)
                Ticket.objects.filter(id=order.ticket.id).update(sales=F('sales')-1)
                User.objects.filter(id=order.user.id).update(points=F('points')-USER_POINTS_INCREASE_DELTA)

            # 区域下限检查
            arealimits = AreaBoardingLowerLimit.objects.select_for_update().filter(activity_id=acti.id)
            for limit in arealimits:
                this_area_boardingloc = Boardingloc.objects.select_for_update().filter(activity_id=acti.id,
                                                            loc__area__id=limit.area.id,)
                area_people_num = this_area_boardingloc.aaggregate(Sum('choice_peoplenum'))
                if area_people_num < limit.lower_limit:  # 区域内各个上车点总人数少于区域下限
                    this_area_boardingloc.delete()  # 删除这些上车点
            # 上车点下限检查
            bad_boardingloc = Boardingloc.objects.select_for_update().filter(activity_id=acti.id,
                                                        choice_peoplenum__lt=F('target_peoplenum'))
            bad_boardingloc.delete()
        

    # 锁定订单（已付款且上车点有效的）
    with transaction.atomic():
        lock_orders = TicketOrder.objects.select_for_update().filter(Q(ticket__activity__id__in=acti_objs_id) &
                                                                     Q(status=2) &
                                                                     Q(bus_loc__isnull=False)
                                                                     )
        lock_orders.update(status=3)


    # 生成乘车信息
    bustype_list = list(Bustype.objects.values('passenger_num').order_by('-passenger_num'))
    bus_big_raw = bustype_list[0] - STAFF_NUM
    bus_small_raw = bustype_list[1] - STAFF_NUM

    if len(bustype_list)!=2:
        print('Bustype wrong! Only supports two types of bus!')
        print(f'Try to use default bus type: big={DEFAULT_BIG_BUS} small={DEFAULT_SMALL_BUS}')
        bus_big = DEFAULT_BIG_BUS
        bus_small = DEFAULT_SMALL_BUS
        return
    bus_big = bus_big_raw - EMPTY_SEAT_BUFFER  # 减去换车缓冲量和工作人员数为实际的车型承载能力
    bus_small = bus_small_raw - EMPTY_SEAT_BUFFER


    acti_objs = Activity.objects.filter(id__in=acti_objs_id)
    for acti in acti_objs:
        # 按区域组织上车点的信息，区域id + 总人数
        area_info = Boardingloc.objects.filter(activity_id=acti.id).values('loc__area_id').distinct().annotate(total_people_num=Sum("choice_peoplenum"))

        # 每辆车都只在区域内接人，不会跨区拼车
        for area in area_info:
            # print('area', area)
            area_id = area['loc__area_id']
            total_people_num = area['total_people_num']

            # 计算分配方法
            n_big, n_small = get_bus_allocation(bus_big, bus_small, total_people_num)
            print('分配：', n_big, n_small)

            # 查找本次活动这些区的订单，按对应上车点的人数从高到低排序
            all_related_orders = TicketOrder.objects.filter(ticket__activity_id=acti.id, bus_loc__loc__area_id=area_id).order_by('-bus_loc__choice_peoplenum')
            # print('all_related_orders', all_related_orders)
            if total_people_num != all_related_orders.count():
                print ('Wrong people num(total_people_num != all_related_orders.count)')
                print (f'    total_people_num={total_people_num} all_related_orders.count={all_related_orders.count()}')
                print (f'Fail to create bus for area: {area_id}')                
                return
            all_related_orders_id = [i.id for i in all_related_orders]

            begin_index = 0
            # 先创建大号大巴
            for j in range(n_big):
                # 切出这辆大巴对应的订单
                orderid_slice = all_related_orders_id[begin_index : begin_index+bus_big]
                begin_index += bus_big
                
                # 创建一个新大巴
                newbus = Bus.objects.create(activity_id=acti.id, carry_peoplenum=len(orderid_slice), max_people=bus_big_raw)

                buslocid_set = set()
                # 遍历该大巴对应的订单
                for orderid in orderid_slice:
                    try:
                        thisorder = TicketOrder.objects.get(id=orderid)
                    except Exception as e:
                        print(repr(e))
                        return

                    if thisorder.bus_loc.id not in buslocid_set:
                        buslocid_set.add(thisorder.bus_loc.id)
                        # 这个bus中存在一个新loc，则新创建一个bus loc time对应
                        newbusloctime = Bus_boarding_time.objects.create(bus_id=newbus.id, loc_id=thisorder.bus_loc.id)
                        # 补充订单信息，包括大巴车，大巴-上车点-时间对应
                        thisorder.bus_id = newbus.id
                        thisorder.bus_time_id = newbusloctime.id
                        thisorder.save()
                        # 更新bus loc time对应表的人数
                        # newbusloctime.bus_loc_peoplenum = F('bus_loc_peoplenum') + 1
                        newbusloctime.bus_loc_peoplenum += 1
                        newbusloctime.save()
                    else:
                        try:
                            busloctime = Bus_boarding_time.objects.get(bus_id=newbus.id, loc_id=thisorder.bus_loc.id)
                            # 补充订单信息，包括大巴车，大巴-上车点-时间对应
                            thisorder.bus_id = newbus.id
                            thisorder.bus_time_id = busloctime.id
                            thisorder.save()
                            # 更新bus loc time对应表的人数
                            # busloctime.bus_loc_peoplenum = F('bus_loc_peoplenum') + 1
                            busloctime.bus_loc_peoplenum += 1
                            busloctime.save()
                        except Exception as e:
                            print(repr(e))
                            return

            # 再创建小号大巴
            for j in range(n_small):
                # 切出这辆大巴对应的订单
                orderid_slice = all_related_orders_id[begin_index : begin_index+bus_small]
                begin_index += bus_small
                
                # 创建一个新大巴
                newbus = Bus.objects.create(activity_id=acti.id, carry_peoplenum=len(orderid_slice), max_people=bus_small_raw)

                buslocid_set = set()
                # 遍历该大巴对应的订单
                for orderid in orderid_slice:
                    try:
                        thisorder = TicketOrder.objects.get(id=orderid)
                    except Exception as e:
                        print(repr(e))
                        return

                    if thisorder.bus_loc.id not in buslocid_set:
                        buslocid_set.add(thisorder.bus_loc.id)
                        # 这个bus中存在一个新loc，则新创建一个bus loc time对应
                        newbusloctime = Bus_boarding_time.objects.create(bus_id=newbus.id, loc_id=thisorder.bus_loc.id)
                        # 补充订单信息，包括大巴车，大巴-上车点-时间对应
                        thisorder.bus_id = newbus.id
                        thisorder.bus_time_id = newbusloctime.id
                        thisorder.save()
                        # 更新bus loc time对应表的人数
                        # newbusloctime.bus_loc_peoplenum = F('bus_loc_peoplenum') + 1
                        newbusloctime.bus_loc_peoplenum += 1
                        newbusloctime.save()
                    else:
                        try:
                            busloctime = Bus_boarding_time.objects.get(bus_id=newbus.id, loc_id=thisorder.bus_loc.id)
                            # 补充订单信息，包括大巴车，大巴-上车点-时间对应
                            thisorder.bus_id = newbus.id
                            thisorder.bus_time_id = busloctime.id
                            thisorder.save()
                            # 更新bus loc time对应表的人数
                            # busloctime.bus_loc_peoplenum = F('bus_loc_peoplenum') + 1
                            busloctime.bus_loc_peoplenum += 1
                            busloctime.save()
                        except Exception as e:
                            print(repr(e))
                            return


# 锁票日期
def set_activity_locked():
    print ('================ SET ACTIVITY LOCKED ',str(datetime.datetime.now()), '================')
    # 将到期的活动设为锁票
    try:
        acti_objs = Activity.objects.filter(Q(lock_ddl_date__lt = datetime.date.today()) & ( Q(status=0) | Q(status=1)))
        acti_objs_id = [i.id for i in acti_objs]  # 同一天可能有不止一个活动锁票
        acti_objs.update(registration_status=False)
    except Exception as e:
        print('Fail to set activity as <locked> ', str(datetime.datetime.now()), repr(e))

    # 取消未付款订单（如果日期设置没问题，这里不会出现未付款订单）
    with transaction.atomic():
        unpaid_orders = TicketOrder.objects.select_for_update().filter(ticket__activity_id__in=acti_objs_id,
                                                       status=1,
                                                       bus_loc__isnull=True)
        unpaid_orders.update(status=0)
        for order in unpaid_orders:
            # 上车点人数-1，先于区域和上车点合法性检查
            if order.bus_loc is not None:
                Boardingloc.objects.filter(id=order.bus_loc.id).update(choice_peoplenum=F('choice_peoplenum')-1)
            Activity.objects.filter(id=order.ticket.activity.id).update(current_participant=F('current_participant')-1)
            Ticket.objects.filter(id=order.ticket.id).update(sales=F('sales')-1)
            User.objects.filter(id=order.user.id).update(points=F('points')-USER_POINTS_INCREASE_DELTA)

    # 退款无效订单
    with transaction.atomic():
        # todo 已付款，但没上车点 =》退票
        refund_orders = TicketOrder.objects.select_for_update().filter(ticket__activity_id__in=acti_objs_id,
                                                       status=2,
                                                       bus_loc__isnull=True)
        refund_orders.update(status=4)
        for order in refund_orders:
            # 上车点人数-1，先于区域和上车点合法性检查
            # if order.bus_loc is not None:  (filter已经筛选出了上车点为null的)
            #     Boardingloc.objects.filter(id=order.bus_loc.id).update(choice_peoplenum=F('choice_peoplenum')-1)
            Activity.objects.filter(id=order.ticket.activity.id).update(current_participant=F('current_participant')-1)
            Ticket.objects.filter(id=order.ticket.id).update(sales=F('sales')-1)
            User.objects.filter(id=order.user.id).update(points=F('points')-USER_POINTS_INCREASE_DELTA)

    # 锁定订单
    with transaction.atomic():
        # 已付款，有上车点 =》锁票
        TicketOrder.objects.select_for_update().filter(ticket__activity_id__in=acti_objs_id,
                                                       status=2,
                                                       bus_loc__isnull=True).update(status=3)


    return