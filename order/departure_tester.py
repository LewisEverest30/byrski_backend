import datetime
import random
from django.db.models import F

from order.models import TicketOrder
from activity.models import Ticket, Boardingloc, Activity

# ID_FILE = 'test_order_id.txt'
ID_FILE = '/root/byrski_backend/test_order_id.txt'
ACTIVITY_ID = 1
TICKET_ID = 1
COST = 99
WXG_ID = 1
USER_ID = 1
GOOD_BL_CHOICE = [1, 1, 1, 1, 2, 2, 3, 3, 3, 3, 5, 5, 5, 5, 5]
BAD_BL = 4

# 创建测试使用的ticketorder
def create_test_ticket_order():
    test_order_id_file = open(ID_FILE, 'w')
    
    # 随机构建200个订单
    for i in range(200):
        busloc_id = random.choice(GOOD_BL_CHOICE)
        order = TicketOrder.objects.create(
            user_id = USER_ID,
            ordernumber = ('test_trade_no_'+str(datetime.datetime.now())).replace(' ', '').replace('-', '').replace(':', '').replace('.', '')[:32],
            ticket_id = TICKET_ID,
            cost = COST,
            wxgroup_id = WXG_ID,
            bus_loc_id = busloc_id,
            status = 2,
        )
        # 上车点人数+1
        Boardingloc.objects.filter(id=busloc_id).update(choice_peoplenum=F('choice_peoplenum')+1)
        # 活动参与人数+1
        Activity.objects.filter(id=ACTIVITY_ID).update(current_participant=F('current_participant')+1)
        # 票销量+1
        Ticket.objects.filter(id=TICKET_ID).update(sales=F('sales')+1)

        test_order_id_file.write(str(order.id)+'\n')
    
    
    # 构建上车点不足的订单
    for i in range(8):
        busloc_id = BAD_BL
        order = TicketOrder.objects.create(
            user_id = USER_ID,
            ordernumber = ('test_trade_no_'+str(datetime.datetime.now())).replace(' ', '').replace('-', '').replace(':', '').replace('.', '')[:32],
            ticket_id = TICKET_ID,
            cost = COST,
            wxgroup_id = WXG_ID,
            bus_loc_id = busloc_id,
            status = 2,
        )
        # 上车点人数+1
        Boardingloc.objects.filter(id=busloc_id).update(choice_peoplenum=F('choice_peoplenum')+1)
        # 活动参与人数+1
        Activity.objects.filter(id=ACTIVITY_ID).update(current_participant=F('current_participant')+1)
        # 票销量+1
        Ticket.objects.filter(id=TICKET_ID).update(sales=F('sales')+1)

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
        if order.status == 2 or order.status == 3:
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