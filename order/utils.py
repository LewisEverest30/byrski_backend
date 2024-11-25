from django.db.models import Sum, F
from django.db import transaction
import requests

from .models import TicketOrder, USER_POINTS_INCREASE_DELTA
from user.models import User
from activity.models import Ticket, Boardingloc, AreaBoardingLowerLimit, Activity

# =====================================订单处理工具============================================================

# 取消未付款订单
def cancel_unpaid_order(activity_id: int):
    print(f'# cancelling unpaid order of activity#{activity_id}')
    with transaction.atomic():
        unpaid_orders = TicketOrder.objects.select_for_update().filter(status=1, ticket__activity__id=activity_id)
        for order in unpaid_orders:
            order.status = 0
            order.save()

            # 上车点人数-1，先于区域和上车点合法性检查
            if order.bus_loc is not None:
                Boardingloc.objects.filter(id=order.bus_loc.id).update(choice_peoplenum=F('choice_peoplenum')-1)
            Activity.objects.filter(id=order.ticket.activity.id).update(current_participant=F('current_participant')-1)
            Ticket.objects.filter(id=order.ticket.id).update(sales=F('sales')-1)
            User.objects.filter(id=order.user.id).update(points=F('points')-USER_POINTS_INCREASE_DELTA)
            User.objects.filter(id=order.user.id).update(saved_money=F('saved_money')-(order.ticket.original_price - order.cost))
    print(f'$ {len(unpaid_orders)} orders have been canceled')


# 检查某个活动涉及的上车点是否符合下限要求
def delete_invaild_boardingloc(activity_id: int):
    print(f'# deleting invalid boardingloc of activity#{activity_id}')
    # 区域下限检查
    with transaction.atomic():
        arealimits = AreaBoardingLowerLimit.objects.select_for_update().filter(activity_id=activity_id)
        for limit in arealimits:
            this_area_boardingloc = Boardingloc.objects.select_for_update().filter(activity_id=activity_id,
                                                        loc__area__id=limit.area.id,)
            area_people_num = this_area_boardingloc.aggregate(total=Sum('choice_peoplenum'))['total'] or 0
            if area_people_num < limit.lower_limit:  # 区域内各个上车点总人数少于区域下限
                this_area_boardingloc_id = [b.id for b in this_area_boardingloc]
                this_area_boardingloc.delete()  # 删除这些上车点
                print(f'$ delete unsatisfied area limit boardingloc#{this_area_boardingloc_id} of area#{limit.area.id}')
    # 上车点下限检查
    with transaction.atomic():
        bad_boardingloc = Boardingloc.objects.select_for_update().filter(activity_id=activity_id,
                                                    choice_peoplenum__lt=F('target_peoplenum'))
        bad_boardingloc_id = [b.id for b in bad_boardingloc]
        bad_boardingloc.delete()
        print(f'$ delete unsatisfied loc limit boardingloc#{bad_boardingloc_id}')


# 退款无效的订单
def refund_invalid_order(activity_id: int):
    print(f'# trying to refund invalid order of activity#{activity_id}')
    # with transaction.atomic():
    # bug: 加锁可能导致java无法设置订单状态
    # 已付款，但没上车点 =》退票
    # refund_orders = TicketOrder.objects.filter(ticket__activity_id=activity_id,
    #                                                 status=2,
    #                                                 bus_loc__isnull=True)
    
    refund_orders = TicketOrder.objects.filter(id=6)
    for order in refund_orders:
        # order.status = 4
        # order.save()

        # todo 调java退款
        java_refund_response = requests.post(url=f'https://gxski.top/java/api/payment/wechat/refund/call?outTradeNo={order.ordernumber}')
        java_refund_response_json = java_refund_response.json()
        if 'code' in java_refund_response_json and java_refund_response_json['code'] == 0:
            print(f'    $ success to refund order#{order.id}')
        else:
            print(f'    $ fail to refund order#{order.id} due to {java_refund_response_json}')

        Activity.objects.filter(id=order.ticket.activity.id).update(current_participant=F('current_participant')-1)
        Ticket.objects.filter(id=order.ticket.id).update(sales=F('sales')-1)
        User.objects.filter(id=order.user.id).update(points=F('points')-USER_POINTS_INCREASE_DELTA)
        User.objects.filter(id=order.user.id).update(saved_money=F('saved_money')-(order.ticket.original_price - order.cost))
    print(f'$ {len(refund_orders)} orders have been refunded')


def lock_order(activity_id: int):
    # 锁定订单（已付款且上车点有效的）
    print(f'# trying to lock orders of activity#{activity_id}')
    with transaction.atomic():
        lock_orders = TicketOrder.objects.select_for_update().filter(ticket__activity_id=activity_id,
                                                                     status=2,
                                                                     bus_loc__isnull=False,
                                                                     )
        lock_orders_count = lock_orders.count()
        lock_orders.update(status=3)
        print(f'$ {lock_orders_count} orders have been set as <locked>')




# =====================================旧版分车============================================================


'''
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


'''
