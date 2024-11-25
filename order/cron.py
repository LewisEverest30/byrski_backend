import datetime
from django.db.models import F, Q, Sum
from django.db import transaction

from activity.models import Activity, Bustype
from order.models import TicketOrder, Bus, Boardingloc, Bus_boarding_time
from .utils import delete_invaild_boardingloc, cancel_unpaid_order, refund_invalid_order, lock_order
from .departure import plan_route_top

# DEFAULT_BIG_BUS = 53
# DEFAULT_SMALL_BUS = 33
EMPTY_SEAT_BUFFER = 5
STAFF_NUM = 1
VEHICLE_CAPACITY_DEFAULT = [37,47]     # 车辆容量
VEHICLE_COST_DEFAULT = [3200, 3800]   # 费用
AREA_Beijing = {1: "Haidian", 
                2: "Changping",
                3: "Fengtai",
                7: "Xicheng", 
                8: "Dongcheng",
                9: "Miyun",
                10: "Fangshan",
                11: "Shijingshan",
                12: "Daxing", 
                13: "Huairou",
                14: "Tongzhou", 
                15: "Shunyi", 
                }



# 活动截止报名之时
def set_activity_expire():
    
    print ('================ SET ACTIVITY EXPIRE ',str(datetime.datetime.now()), '================')
    # 将到期的活动设为不可报名
    try:
        with transaction.atomic():
            acti_objs = Activity.objects.select_for_update().filter(signup_ddl_date__lt = datetime.date.today(), status=0)
            acti_objs_id = [i.id for i in acti_objs]  # 同一天可能有不止一个活动截止报名
            acti_objs.update(status=1)
            print(f'$ Success to set activity as <prevent_signup> #{acti_objs_id}')
    except Exception as e:
        print('$ Fail to set activity as <prevent_signup> ', str(datetime.datetime.now()), repr(e))
    
    acti_objs = Activity.objects.filter(id__in=acti_objs_id)
    # 先为每个活动剔除无效的订单 和 无效的上车点
    for acti in acti_objs:
        # 清除待付款订单
        cancel_unpaid_order(acti.id)
        # 清除无效上车点
        delete_invaild_boardingloc(acti.id)
        # 锁定订单
        lock_order(acti.id)

    # todo-f 自动将已完成的订单设为返程已上车
    # 处理已经完成订单，将这些订单设为返程已上车(工作频率同样是每天一次，合并到一起了)
    TicketOrder.set_orders_finished()
    print ('================ SET ACTIVITY EXPIRE FINISHED ===================================\n')



# 锁票日期
def set_activity_locked():
    print ('================ SET ACTIVITY LOCKED ',str(datetime.datetime.now()), '================')
    # 将到期的活动设为锁票
    try:
        with transaction.atomic():
            acti_objs = Activity.objects.select_for_update().filter(Q(lock_ddl_date__lt = datetime.date.today()) & ( Q(status=0) | Q(status=1)))
            acti_objs_id = [i.id for i in acti_objs]  # 同一天可能有不止一个活动锁票
            acti_objs.update(status=2)
            print(f'$ Success to set activity as <locked> #{acti_objs_id}')
    except Exception as e:
        print('Fail to set activity as <locked> ', str(datetime.datetime.now()), repr(e))

    acti_objs = Activity.objects.filter(id__in=acti_objs_id)
    for acti in acti_objs:
        # 取消未付款订单（如果日期设置没问题，这里不会出现未付款订单）
        cancel_unpaid_order(acti.id)

        # 退款每个活动中的无效订单（已付款但没有上车点）
        # todo-f 调java接口退款
        refund_invalid_order(acti.id)

        # 锁定订单（如果日期设置没问题，这里不会出现未锁定的订单）
        lock_order(acti.id)


    # 挨个活动生成乘车信息
    for acti in acti_objs:
        print(f'# trying to run the departure allocation program(BRM) for activity#{acti.id}')

        # 拿到车型信息
        bus_types = Bustype.objects.filter(activity_id=acti.id).order_by('passenger_num')
        if bus_types.count() != 2:  # 使用默认车型
            print(f'Bustype wrong!(Activity #{acti.id}) Only supports two types of bus!')
            print(f'Try to use default bus type: small={VEHICLE_CAPACITY_DEFAULT[0]} big={VEHICLE_CAPACITY_DEFAULT[1]}')
            vehicle_capacity = [VEHICLE_CAPACITY_DEFAULT[0]-STAFF_NUM, VEHICLE_CAPACITY_DEFAULT[1]-STAFF_NUM]     # 车辆容量
            vehicle_costs = [VEHICLE_COST_DEFAULT[0], VEHICLE_COST_DEFAULT[1]]   # 费用
        else:
            vehicle_capacity = [i.passenger_num-STAFF_NUM for i in bus_types]
            vehicle_costs = [float(i.price) for i in bus_types]  # 转成float，与BRM中的数据类型一致

        # 按区域组织上车点的信息，区域id + 总人数
        area_info = Boardingloc.objects.filter(activity_id=acti.id).values('loc__area_id').distinct().annotate(total_people_num=Sum("choice_peoplenum"))

        area_loc_info = {}  # 所有区域的上车点信息
        # 每辆车都只在区域内接人，不会跨区拼车
        for area in area_info:
            print(f'  # trying to run the departure allocation program(BRM) for area#{area["loc__area_id"]}')
            area_id = area['loc__area_id']
            area_input_name = AREA_Beijing[area_id]
            # total_people_num = area['total_people_num']

            # 拿到该区域内的上车点信息，点id+人数
            loc_info = Boardingloc.objects.filter(activity_id=acti.id, loc__area_id=area_id).values('id', 'choice_peoplenum').order_by('-choice_peoplenum')
            # 将loc_info转化成id为key，人数为value的字典
            loc_info_dict = {i['id']: i['choice_peoplenum'] for i in loc_info}
            area_loc_info[area_input_name] = loc_info_dict

        # 获取分车信息(banrenma)
        print('====BRM START====')
        # print('    total_people_num:', total_people_num)
        print('area_loc_info:', area_loc_info)
        print('vehicle_capacity:', vehicle_capacity)
        print('vehicle_costs:', vehicle_costs)
        bus_allocation_objs = plan_route_top(area_loc_info, vehicle_capacity, vehicle_costs)
        bus_list = []
        for areabus in bus_allocation_objs:
            bus_list += areabus.bus_list
            print('    areabus:', areabus)
        print('====BRM END====')

        # 为活动的所有订单分配车辆
        # 查询该活动当前区域内所有订单，并按上车点排序，得到上车点id为key，订单列表为value的字典
        with transaction.atomic():
            # all_related_orders = TicketOrder.objects.select_for_update().filter(Q(ticket__activity_id=acti.id) & Q(bus_loc__loc__area_id=area_id) & ~Q(status=6)).order_by('bus_loc__choice_peoplenum')
            all_related_orders = TicketOrder.objects.select_for_update().filter(Q(ticket__activity_id=acti.id) & ~Q(status=6)).order_by('bus_loc__choice_peoplenum')
            # if total_people_num != all_related_orders.count():
            #     print ('Wrong people num(total_people_num != all_related_orders.count)')
            #     print (f'    total_people_num={total_people_num} all_related_orders.count={all_related_orders.count()}')
            #     print (f'Fail to create bus for area: {area_id}')                
            #     return

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
            for bus in bus_list:
                # 创建车辆
                # todo-f 容量是bus的哪个属性？ carry_peoplenum应该等于？
                newbus = Bus.objects.create(activity_id=acti.id, carry_peoplenum=bus.capity-bus.empty_seats, max_people=bus.capity)

                # 遍历这辆车经过的各个点，创建车辆-上车点-时间对应
                for loc_id, people_num in bus.route.items():  # 每个车经过几个点, 上车点id：人数
                    # 创建新的 Bus_boarding_time 实例
                    newbusloctime = Bus_boarding_time.objects.create(bus_id=newbus.id, loc_id=loc_id, boarding_peoplenum=people_num)

                    # 更新订单的车辆和上车点-时间对应
                    begin_index = all_related_orders_dict[loc_id]['allocated_num']
                    for order in all_related_orders_dict[loc_id]['orders'][begin_index : begin_index + people_num]:
                        order.bus_id = newbus.id
                        order.bus_time_id = newbusloctime.id
                        order.save()
                    
                    # 更新已分配人数
                    all_related_orders_dict[loc_id]['allocated_num'] += people_num                
        # print(f'  # success to run the departure allocation program(BRM) for area#{area["loc__area_id"]}')


        acti.success_departue = True
        acti.save()
        print(f'$ success to run the departure allocation program(BRM) for activity#{acti.id}')
    print ('================ SET ACTIVITY LOCKED FINISHED ===================================\n')

    return
