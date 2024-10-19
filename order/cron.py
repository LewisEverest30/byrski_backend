import datetime
from django.db.models import Sum
from django.db.models import F
from .models import Bus, Boardingloc, Bustype, Bus_boarding_time
from activity.models import TicketOrder, Activity
import datetime

def get_bus_allocation(big, small, people):
    n_big = 0
    n_small = 0

    if big >= 2*small:  # 大车承载人数超过了小车的两倍
        q, r = divmod(people, big)

        if r==0:
            n_big = q
            n_small = 0
            return (n_big, n_small)


        if r > small:
            n_big = q + 1
            n_small = 0
        else:
            n_big = q
            n_small = 1
    else:
        k = 2*small - big
        m = 3*small - 2*big
        q, r = divmod(people, big)

        if r==0:
            n_big = q
            n_small = 0
            return (n_big, n_small)

        if q == 1:
            if r <= k:
                n_big = q - 1
                n_small = 2
            elif r > k and r <= small:
                n_big = q
                n_small = 1
            else:
                n_big = q + 1
                n_small = 0
        elif q > 1:
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

        else:
            if r <= small:
                n_big = 0
                n_small = 1
            else:
                n_big = 1
                n_small = 0

    return (n_big, n_small)


def set_activity_expire():
    print ('-----', str(datetime.datetime.now()), '-----')
    # 将到期的活动设为不可报名
    try:
        acti_objs = Activity.objects.filter(signup_ddl_d__lt = datetime.date.today(), registration_status=True)
        acti_objs_id = [i.id for i in acti_objs]
        acti_objs.update(registration_status=False)
    except Exception as e:
        print(str(datetime.datetime.now()), repr(e))
    
    # 清除该活动的所有未付款订单
    for acti in acti_objs:
        unpaid_orders = TicketOrder.objects.filter(activity_id=acti.id, is_paid=False)
        unpaid_orders.delete()

    # 生成乘车信息
    bustypes = Bustype.objects.all()
    bustype_list = []
    for bust in bustypes:
        bustype_list.append(bust.passenger_num)
    bustype_list.sort(reverse=True)
    # print(bustype_list)

    if len(bustype_list)!=2:
        print('bustype wrong!')
        return
    
    bus_big = bustype_list[0]
    bus_small = bustype_list[1]
        
    acti_objs = Activity.objects.filter(id__in=acti_objs_id)

    # print(acti_objs)
    for acti in acti_objs:
        busloc_info = Boardingloc.objects.filter(activity_id=acti.id).values('loc__area_id')
        areainfo = busloc_info.annotate(total_people_num=Sum("loc_peoplenum"))

        # print('areainfo,',areainfo)
        for area in areainfo:
            # print('area', area)
            area_id = area['loc__area_id']
            total_people_num = area['total_people_num']

            # 计算分配方法
            n_big, n_small = get_bus_allocation(bus_big, bus_small, total_people_num)
            # print('分配：', n_big, n_small)

            # 查找本次活动这些区的订单，按对应上车点的人数从高到低排序
            all_related_orders = TicketOrder.objects.filter(activity_id=acti.id, bus_loc__loc__area_id=area_id)
            # print('all_related_orders', all_related_orders)
            if total_people_num != all_related_orders.count():
                print ('wrong people num in line 105')
                return
            all_related_orders_ordered = all_related_orders.order_by('-bus_loc__loc_peoplenum')
            all_related_orders_ordered_id = [i.id for i in all_related_orders_ordered]

            begin_index = 0
            # 先创建大号大巴
            for j in range(n_big):
                # 切出这辆大巴对应的订单
                orderid_slice = all_related_orders_ordered_id[begin_index : begin_index+bus_big]
                begin_index += bus_big
                
                # 创建一个新大巴
                newbus = Bus.objects.create(activity_id=acti.id, bus_peoplenum=len(orderid_slice), max_people=bus_big)

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
                        newbusloctime.bus_loc_peoplenum = F('bus_loc_peoplenum') + 1
                        newbusloctime.save()
                    else:
                        try:
                            busloctime = Bus_boarding_time.objects.get(bus_id=newbus.id, loc_id=thisorder.bus_loc.id)
                            # 补充订单信息，包括大巴车，大巴-上车点-时间对应
                            thisorder.bus_id = newbus.id
                            thisorder.bus_time_id = busloctime.id
                            thisorder.save()
                            # 更新bus loc time对应表的人数
                            busloctime.bus_loc_peoplenum = F('bus_loc_peoplenum') + 1
                            busloctime.save()
                        except Exception as e:
                            print(repr(e))
                            return

            # 再创建小号大巴
            for j in range(n_small):
                # 切出这辆大巴对应的订单
                orderid_slice = all_related_orders_ordered_id[begin_index : begin_index+bus_small]
                begin_index += bus_small
                
                # 创建一个新大巴
                newbus = Bus.objects.create(activity_id=acti.id, bus_peoplenum=len(orderid_slice), max_people=bus_small)

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
                        newbusloctime.bus_loc_peoplenum = F('bus_loc_peoplenum') + 1
                        newbusloctime.save()
                    else:
                        try:
                            busloctime = Bus_boarding_time.objects.get(bus_id=newbus.id, loc_id=thisorder.bus_loc.id)
                            # 补充订单信息，包括大巴车，大巴-上车点-时间对应
                            thisorder.bus_id = newbus.id
                            thisorder.bus_time_id = busloctime.id
                            thisorder.save()
                            # 更新bus loc time对应表的人数
                            busloctime.bus_loc_peoplenum = F('bus_loc_peoplenum') + 1
                            busloctime.save()
                        except Exception as e:
                            print(repr(e))
                            return
