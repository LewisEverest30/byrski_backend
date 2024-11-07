import datetime
import random
from django.db.models import F

from order.models import TicketOrder
from activity.models import Ticket, Boardingloc, Activity

# 创建测试使用的ticketorder
def create_test_ticket_order():
    test_order_id_file = open('test_order_id.txt', 'w')
    
    # 随机构建200个订单
    for i in range(200):
        busloc_id = random.choice([1, 1, 1, 1, 2, 2, 3, 3, 3, 3, 5, 5, 5, 5, 5])
        order = TicketOrder.objects.create(
            user_id = 1,
            ordernumber = ('test_trade_no_'+str(datetime.datetime.now())).replace(' ', '').replace('-', '').replace(':', '').replace('.', '')[:32],
            ticket_id = 1,
            cost = 99,
            wxgroup_id = 1,
            bus_loc_id = busloc_id,
            status = 2,
        )
        # 上车点人数+1
        Boardingloc.objects.filter(id=busloc_id).update(choice_peoplenum=F('choice_peoplenum')+1)
        # 活动参与人数+1
        Activity.objects.filter(id=1).update(current_participant=F('current_participant')+1)
        # 票销量+1
        Ticket.objects.filter(id=1).update(sales=F('sales')+1)

        test_order_id_file.write(str(order.id)+'\n')
    
    
    # 构建上车点不足的订单
    for i in range(8):
        busloc_id = 4
        order = TicketOrder.objects.create(
            user_id = 1,
            ordernumber = ('test_trade_no_'+str(datetime.datetime.now())).replace(' ', '').replace('-', '').replace(':', '').replace('.', '')[:32],
            ticket_id = 1,
            cost = 99,
            wxgroup_id = 1,
            bus_loc_id = busloc_id,
            status = 2,
        )
        # 上车点人数+1
        Boardingloc.objects.filter(id=busloc_id).update(choice_peoplenum=F('choice_peoplenum')+1)
        # 活动参与人数+1
        Activity.objects.filter(id=1).update(current_participant=F('current_participant')+1)
        # 票销量+1
        Ticket.objects.filter(id=1).update(sales=F('sales')+1)

        test_order_id_file.write(str(order.id)+'\n')
    
    test_order_id_file.close()


# 从test_order_id.txt中读取订单id，删除这些订单
def delete_test_ticket_order():
    test_order_id_file = open('test_order_id.txt', 'r')
    for line in test_order_id_file:
        order_id = int(line)
        order = TicketOrder.objects.get(id=order_id)
        # 上车点人数-1
        if order.bus_loc is not None:
            Boardingloc.objects.filter(id=order.bus_loc.id).update(choice_peoplenum=F('choice_peoplenum')-1)
        # 活动参与人数-1
        Activity.objects.filter(id=order.ticket.activity.id).update(current_participant=F('current_participant')-1)
        # 票销量-1
        Ticket.objects.filter(id=order.ticket.id).update(sales=F('sales')-1)
        order.delete()
    test_order_id_file.close()


# 从test_order_id.txt中读取订单id，将这些订单设为paid 2
def set_status2_test_ticket_order():
    test_order_id_file = open('test_order_id.txt', 'r')
    for line in test_order_id_file:
        order_id = int(line)
        order = TicketOrder.objects.get(id=order_id)
        order.status = 2
        order.save()
    test_order_id_file.close()