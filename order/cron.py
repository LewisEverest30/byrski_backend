import datetime
from django.db.models import F, Q, Sum
from .models import Bus, Boardingloc, Bustype, Bus_boarding_time
from django.db import transaction

from activity.models import Activity, Bustype
from order.models import TicketOrder
from .utils import delete_invaild_boardingloc, cancel_unpaid_order, refund_invalid_order
from .departure import plan_route_top

# DEFAULT_BIG_BUS = 53
# DEFAULT_SMALL_BUS = 33
EMPTY_SEAT_BUFFER = 5
STAFF_NUM = 1
VEHICLE_CAPACITY_DEFAULT = [37,47]     # 车辆容量
VEHICLE_COST_DEFAULT = [3200, 3800]   # 费用



# 活动截止报名之时
def set_activity_expire():
    # todo 替换为logger
    
    print ('================ SET ACTIVITY EXPIRE ',str(datetime.datetime.now()), '================')
    # 将到期的活动设为不可报名
    try:
        acti_objs = Activity.objects.filter(signup_ddl_date__lt = datetime.date.today(), status=0)
        acti_objs_id = [i.id for i in acti_objs]  # 同一天可能有不止一个活动截止报名
        acti_objs.update(registration_status=False)
    except Exception as e:
        print('Fail to set activity as <prevent_signup> ', str(datetime.datetime.now()), repr(e))
    
    # 先为每个活动剔除无效的订单 和 无效的上车点
    for acti in acti_objs:
        # 清除待付款订单
        cancel_unpaid_order(acti.id)
        # 清除无效上车点
        delete_invaild_boardingloc(acti.id)        

    # 锁定订单（已付款且上车点有效的）
    with transaction.atomic():
        lock_orders = TicketOrder.objects.select_for_update().filter(Q(ticket__activity__id__in=acti_objs_id) &
                                                                     Q(status=2) &
                                                                     Q(bus_loc__isnull=False)
                                                                     )
        lock_orders.update(status=3)

    # todo-f 自动将已完成的订单设为返程已上车
    # 处理已经完成订单，将这些订单设为返程已上车(工作频率同样是每天一次，合并到一起了)
    TicketOrder.set_orders_finished()



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
    cancel_unpaid_order(acti_objs_id)

    # 退款每个活动中的无效订单
    # todo 调java接口退款
    for acti in acti_objs:
        refund_invalid_order(acti.id)

    # 锁定订单
    with transaction.atomic():
        # 已付款，有上车点 =》 锁票
        TicketOrder.objects.select_for_update().filter(ticket__activity_id__in=acti_objs_id,
                                                       status=2,
                                                       bus_loc__isnull=True).update(status=3)


    # 挨个活动生成乘车信息
    acti_objs = Activity.objects.filter(id__in=acti_objs_id)
    for acti in acti_objs:
        
        # 拿到车型信息
        bus_types = Bustype.objects.filter(activity_id=acti.id).order_by('passenger_num')
        if bus_types.count() != 2:
            print(f'Bustype wrong!(Activity #{acti.id}) Only supports two types of bus!')
            print(f'Try to use default bus type: small={VEHICLE_CAPACITY_DEFAULT[0]} big={VEHICLE_CAPACITY_DEFAULT[1]}')
            vehicle_capacity = [VEHICLE_CAPACITY_DEFAULT[0]-STAFF_NUM, VEHICLE_CAPACITY_DEFAULT[1]-STAFF_NUM]     # 车辆容量
            vehicle_costs = [VEHICLE_COST_DEFAULT[0], VEHICLE_COST_DEFAULT[1]]   # 费用
        else:
            vehicle_capacity = [i.passenger_num-STAFF_NUM for i in bus_types]
            vehicle_costs = [i.cost for i in bus_types]

        # 按区域组织上车点的信息，区域id + 总人数
        area_info = Boardingloc.objects.filter(activity_id=acti.id).values('loc__area_id').distinct().annotate(total_people_num=Sum("choice_peoplenum"))

        # 每辆车都只在区域内接人，不会跨区拼车
        for area in area_info:
            # print('area', area)
            area_id = area['loc__area_id']
            total_people_num = area['total_people_num']

            # 拿到该区域内的上车点信息，点id+人数
            loc_info = Boardingloc.objects.filter(activity_id=acti.id, loc__area_id=area_id).values('id', 'choice_peoplenum').order_by('-choice_peoplenum')
            # 将loc_info转化成id为key，人数为value的字典
            loc_info_dict = {i['id']: i['choice_peoplenum'] for i in loc_info}

            # 获取分车信息(banrenma)
            bus_allocation_objs = plan_route_top(total_people_num, loc_info_dict, vehicle_capacity, vehicle_costs)

            # 查询该活动当前区域内所有订单，并按上车点排序，得到上车点id为key，订单列表为value的字典
            all_related_orders = TicketOrder.objects.select_for_update().filter(Q(ticket__activity_id=acti.id) & Q(bus_loc__loc__area_id=area_id) & ~Q(status=6)).order_by('bus_loc__choice_peoplenum')
            if total_people_num != all_related_orders.count():
                print ('Wrong people num(total_people_num != all_related_orders.count)')
                print (f'    total_people_num={total_people_num} all_related_orders.count={all_related_orders.count()}')
                print (f'Fail to create bus for area: {area_id}')                
                return

            all_related_orders_dict = {}
            for order in all_related_orders:    # 将all_related_orders转化成id为key，订单有序列表为value的字典
                if order.bus_loc.id not in all_related_orders_dict:
                    all_related_orders_dict[order.bus_loc.id] = {
                        'allocated_num': 0,
                        'orders': [order]
                    }
                else:
                    all_related_orders_dict[order.bus_loc.id]['orders'].append(order)
            
            # 为每辆车分配订单
            for bus in bus_allocation_objs:
                # 创建车辆
                # todo 容量是bus的哪个属性？ carry_peoplenum应该等于？
                newbus = Bus.objects.create(activity_id=acti.id, carry_peoplenum=bus.capacity-bus.reserved_seats, max_people=bus.capacity)

                # 遍历这辆车经过的各个点，创建车辆-上车点-时间对应
                for loc_id, people_num in bus.route.items():  # 每个车经过几个点, 上车点id：人数
                    # 创建新的 Bus_boarding_time 实例
                    newbusloctime = Bus_boarding_time.objects.create(bus_id=newbus.id, loc_id=loc_id, bus_loc_peoplenum=people_num)

                    # 更新订单的车辆和上车点-时间对应
                    begin_index = all_related_orders_dict[loc_id]['allocated_num']
                    for order in all_related_orders_dict[loc_id]['orders'][begin_index : begin_index + people_num]:
                        order.bus_id = newbus.id
                        order.bus_time_id = newbusloctime.id
                        order.save()
                    
                    # 更新已分配人数
                    all_related_orders_dict[loc_id]['allocated_num'] += people_num                
                
                # for loc_id in bus.route:    # 每个车经过几个点, 上车点id：人数
                #     newbusloctime = Bus_boarding_time.objects.create(bus_id=newbus.id, loc_id=loc_id)
                #     # 更新上车点的人数
                #     newbusloctime.bus_loc_peoplenum = bus.route[loc_id]
                #     newbusloctime.save()

                #     # 更新订单的车辆和上车点-时间对应
                #     begin_index = all_related_orders_dict[loc_id]['allocated_num']
                #     for order in all_related_orders_dict[loc_id]['orders'][begin_index:]:
                #         order.bus_id = newbus.id
                #         order.bus_time_id = newbusloctime.id
                #         order.save()
                #     all_related_orders_dict[loc_id]['allocated_num'] += bus.route[loc_id]





            # 查找本次活动这些区的订单(排除已删除的)，按对应上车点的人数从高到低排序
            # all_related_orders = TicketOrder.objects.filter(Q(ticket__activity_id=acti.id) & Q(bus_loc__loc__area_id=area_id) & ~Q(status=6)).order_by('-bus_loc__choice_peoplenum')
            # # print('all_related_orders', all_related_orders)
            # if total_people_num != all_related_orders.count():
            #     print ('Wrong people num(total_people_num != all_related_orders.count)')
            #     print (f'    total_people_num={total_people_num} all_related_orders.count={all_related_orders.count()}')
            #     print (f'Fail to create bus for area: {area_id}')                
            #     return
            # all_related_orders_id = [i.id for i in all_related_orders]

            # begin_index = 0
            # # 先创建大号大巴
            # for j in range(n_big):
            #     # 切出这辆大巴对应的订单
            #     orderid_slice = all_related_orders_id[begin_index : begin_index+bus_big]
            #     begin_index += bus_big
                
            #     # 创建一个新大巴
            #     newbus = Bus.objects.create(activity_id=acti.id, carry_peoplenum=len(orderid_slice), max_people=bus_big_raw)

            #     buslocid_set = set()
            #     # 遍历该大巴对应的订单
            #     for orderid in orderid_slice:
            #         try:
            #             thisorder = TicketOrder.objects.get(id=orderid)
            #         except Exception as e:
            #             print(repr(e))
            #             return

            #         if thisorder.bus_loc.id not in buslocid_set:
            #             buslocid_set.add(thisorder.bus_loc.id)
            #             # 这个bus中存在一个新loc，则新创建一个bus loc time对应
            #             newbusloctime = Bus_boarding_time.objects.create(bus_id=newbus.id, loc_id=thisorder.bus_loc.id)
            #             # 补充订单信息，包括大巴车，大巴-上车点-时间对应
            #             thisorder.bus_id = newbus.id
            #             thisorder.bus_time_id = newbusloctime.id
            #             thisorder.save()
            #             # 更新bus loc time对应表的人数
            #             # newbusloctime.bus_loc_peoplenum = F('bus_loc_peoplenum') + 1
            #             newbusloctime.bus_loc_peoplenum += 1
            #             newbusloctime.save()
            #         else:
            #             try:
            #                 busloctime = Bus_boarding_time.objects.get(bus_id=newbus.id, loc_id=thisorder.bus_loc.id)
            #                 # 补充订单信息，包括大巴车，大巴-上车点-时间对应
            #                 thisorder.bus_id = newbus.id
            #                 thisorder.bus_time_id = busloctime.id
            #                 thisorder.save()
            #                 # 更新bus loc time对应表的人数
            #                 # busloctime.bus_loc_peoplenum = F('bus_loc_peoplenum') + 1
            #                 busloctime.bus_loc_peoplenum += 1
            #                 busloctime.save()
            #             except Exception as e:
            #                 print(repr(e))
            #                 return

    return



# ===================================老版分配大巴========================================================
'''
            # 查找本次活动这些区的订单(排除已删除的)，按对应上车点的人数从高到低排序
            all_related_orders = TicketOrder.objects.filter(Q(ticket__activity_id=acti.id) & Q(bus_loc__loc__area_id=area_id) & ~Q(status=6)).order_by('-bus_loc__choice_peoplenum')
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
'''