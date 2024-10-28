import json
import datetime
from django.conf import settings
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db.models import Q, F, Sum
from django.db import transaction

from user.models import User
from user.auth import MyJWTAuthentication
from .models import *
from activity.utils import ACTIVITY_GUIDE


# 下单
class create_ticket_order(APIView):
    authentication_classes = [MyJWTAuthentication, ]

    @staticmethod
    def get_client_ip(request):

        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')

        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[-1].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')

        return ip

    def post(self,request,*args,**kwargs):
        userid = request.user['userid']

        ip = self.get_client_ip(request)

        try:
            user = User.objects.get(id=userid)
            if user.is_student == False:
                return Response({'ret': 420003, 'errmsg': '用户未通过学生认证', 
                                'data': {
                                    'order_id':None, 
                                    'ordernumber':None, 
                                    'ip': ip
                                    },
                                })
            if user.is_active == False:
                return Response({'ret': 420004, 'errmsg': '用户尚未激活', 
                                'data': {
                                    'order_id':None, 
                                    'ordernumber':None, 
                                    'ip': ip
                                    },
                                })
        except:
            return Response({'ret': 420007, 'errmsg': '其他错误', 
                             'data': {
                                 'order_id':None, 
                                 'ordernumber':None, 
                                 'ip': ip
                             },
                             })

        info = json.loads(request.body)

        try:
            ticket_id = info['ticket_id']
            bus_loc_id = info['boardingloc_id']

            # 录入用户数据
            user.name = info['name']
            user.gender = info['gender']
            user.phone = info['phone']
            user.idnumber = info['idnumber']
            user.save()

            # 判断可报名状态
            ticket = Ticket.objects.get(id=ticket_id)  # post进来的雪票
            if ticket.activity.status != 0:
                    return Response({'ret': 420002, 'errmsg': '已不允许报名', 
                                        'data': {
                                        'order_id':None, 
                                        'ordernumber':None, 
                                        'ip': ip
                                        },
                                    })


            # 保证同一个用户只有一个有效订单
            TicketOrder.cancel_paid_timeout_orders()  # 先检查超时未支付订单
            order_found = TicketOrder.objects.filter(Q(user_id=userid) & Q(ticket__activity_id=ticket.activity.id) &
                                                     (Q(status=1) | Q(status=2) | Q(status=3) | Q(status=4)))  # 已取消和完成退款的为无效的
            if order_found.count() == 0:
                try:
                    # 绑定微信群（取消和退款的也会占用群名额）
                    this_acti_order_num = TicketOrder.objects.filter(ticket__activity_id=ticket.activity.id).count()
                    wxgroup_index = int(this_acti_order_num / WXGROUP_MAX_NUM)
                    wxgroup_choice = ActivityWxGroup.objects.filter(activity_id=ticket.activity.id).order_by('id')[wxgroup_index]
                    
                    
                    # try:
                    #     wxgroup_choice = ActivityWxGroup.objects.filter(activity_id=ticket.activity.id).order_by('id')[wxgroup_index]
                    # except Exception as e:
                    #     print(repr(e))
                    #     return Response({'ret': 420008, 'errmsg': '其他错误，请检查提交的数据是否合法', 
                    #                     'data': {
                    #                         'order_id':None, 
                    #                         'ordernumber':None, 
                    #                         'ip': ip
                    #                     },
                    # 绑定微信群（取消和退款的也会占用群名额）                    
                    #                     })
                    
                    
                    # 创建订单
                    # ordernumber = str(userid).zfill(6)+str(datetime.datetime.now())[2:20].replace(' ', '').replace('-', '').replace(':', '').replace('.', '')
                    ordernumber = ('out_trade_no_'+str(datetime.datetime.now())).replace(' ', '').replace('-', '').replace(':', '').replace('.', '')[:32]
                    
                    neworder = TicketOrder.objects.create(ordernumber=ordernumber , user_id=userid, ticket_id=ticket_id, 
                                                  bus_loc_id=bus_loc_id, wxgroup_id=wxgroup_choice.id)
                    
                    # 上车点人数+1
                    Boardingloc.objects.filter(id=bus_loc_id).update(choice_peoplenum=F('choice_peoplenum')+1)
                    # 活动参与人数+1
                    Activity.objects.filter(id=ticket.activity.id).update(current_participant=F('current_participant')+1)
                    # 票销量+1
                    Ticket.objects.filter(id=ticket_id).update(sales=F('sales')+1)
                    # 用户积分+K
                    User.objects.filter(id=userid).update(points=F('points')+USER_POINTS_INCREASE_DELTA)

                    return Response({'ret': 0, 'errmsg': None, 
                                     'data': {
                                         'order_id':neworder.id, 
                                         'ordernumber':ordernumber, 
                                         'ip': ip
                                     }
                                     })
                except Exception as e:
                    print(repr(e))
                    return Response({'ret': 420008, 'errmsg': '其他错误，请检查提交的数据是否合法', 
                                    'data': {
                                        'order_id':None, 
                                        'ordernumber':None, 
                                        'ip': ip
                                    },
                                    })
            else:
                return Response({'ret': 420005, 'errmsg': '该用户在该活动中的订单已存在，不能重复购买多张雪票', 
                                 'data': {
                                     'order_id':order_found[0].id, 
                                     'ordernumber':order_found[0].ordernumber, 
                                     'ip': ip
                                 }
                                 })

        except Exception as e:
            print(repr(e))
            return Response({'ret': 420009, 'errmsg': '其他错误', 
                             'data': {
                                 'order_id':None, 
                                 'ordernumber':None, 
                                 'ip': ip
                             },
                             })


# 获取下单后的行程卡
class get_itinerary_of_certain_order(APIView):
    authentication_classes = [MyJWTAuthentication, ]
    
    def post(self,request,*args,**kwargs):
        info = json.loads(request.body)
        try:
            order_id = info['id']
            order = TicketOrder.objects.get(id=order_id)
            serializer = OrderSerializer2(instance=order, many=False)
            return Response({'ret': 0, 'data': serializer.data})
        except Exception as e:
            print(repr(e))
            return Response({'ret': 420101, 'data': None})


# 获取行程列表
class get_all_itinerary(APIView):
    authentication_classes = [MyJWTAuthentication, ]

    def get(self,request,*args,**kwargs):
        try:
            # 先取消那些超时未付款的
            TicketOrder.cancel_paid_timeout_orders()

            userid = request.user['userid']
            current_date = timezone.now().date()
            orders = TicketOrder.objects.filter(Q(user_id=userid) & 
                                            (Q(status=2) | Q(status=3)) &
                                            Q(ticket__activity__activity_end_date__gte=current_date))  # 不要已结束的行程
            serializer = OrderSerializerItinerary1(instance=orders, many=True)
            return Response({'ret': 0, 'data': list(serializer.data)})
        except Exception as e:
            print(repr(e))
            return Response({'ret': 420201, 'data': None})
        

# 获取行程的详情
# todo 返程
class get_detail_of_certain_itinerary(APIView):
    authentication_classes = [MyJWTAuthentication, ]

    def post(self,request,*args,**kwargs):
        info = json.loads(request.body)
        try:
            userid = request.user['userid']
            order_id = info['id']

            order = TicketOrder.objects.filter(user_id=userid, id=order_id)
            
            serializer = OrderSerializerItinerary2(instance=order[0], many=False)
            
            return Response({'ret': 0, 'data': serializer.data})
        except Exception as e:
            print(repr(e))
            return Response({'ret': 420301, 'data': None})


# 获取可以替换的上车点
class get_available_boardingloc_of_certain_itinerary(APIView):
    authentication_classes = [MyJWTAuthentication, ]

    def post(self,request,*args,**kwargs):
        info = json.loads(request.body)
        try:
            userid = request.user['userid']
            order_id = info['id']

            ret_dic = {}  # key-上车点，value-大巴车
            # 先查上车点
            activity_id = TicketOrder.objects.get(id=order_id).ticket.activity.id
            boardinglocs = Boardingloc.objects.filter(activity_id=activity_id)
            for bl in boardinglocs:  # 对于所有的目前可用的上车点
                # print(bl)
                related_bus_ids = Bus_boarding_time.objects.filter(loc_id=bl.id).values_list('bus_id', flat=True).distinct()
                # print(related_bus_ids)
                related_bus = Bus.objects.filter(id__in=related_bus_ids)
                availible_bus = []
                for bus in related_bus:
                    if (bus.carry_peoplenum is not None) and (bus.max_people is not None) and \
                        (bus.max_people - bus.carry_peoplenum) > 0:
                        bus_serializer = BusSerializer(instance=bus, many=False)

                        # todo-f 加入上车点id，上车点上车时间
                        this_bus_data = dict(bus_serializer.data)
                        this_bus_data['boardingtime'] = Bus_boarding_time.objects.filter(loc_id=bl.id, bus_id=bus.id)[0].time.strftime('%H:%M')
                        this_bus_data['boardingloc_id'] = Bus_boarding_time.objects.filter(loc_id=bl.id, bus_id=bus.id)[0].loc.id
                        availible_bus.append(this_bus_data)
                # print(availible_bus)

                if len(availible_bus) > 0:
                    ret_dic[str(bl.loc.busboardloc)] = availible_bus

            return Response({'ret': 0, 'data': ret_dic})
        except Exception as e:
            print(repr(e))
            return Response({'ret': 420401, 'data': None})


# 尝试发起退款
class try_refund_ticket_order(APIView):
    authentication_classes = [MyJWTAuthentication, ]

    def post(self,request,*args,**kwargs):
        userid = request.user['userid']

        info = json.loads(request.body)

        try:
            order_id = info['order_id']

            order = TicketOrder.objects.get(id=order_id)
            # 对于已发起退款或已退款的，不要重复退款
            if order.status == 0:
                return Response({'ret': 420506, 'errmsg': '该订单已取消'})
            elif order.status == 0:
                return Response({'ret': 420508, 'errmsg': '该订单未付款'})
            elif order.status == 3:
                return Response({'ret': 420507, 'errmsg': '该订单已锁定'})
            elif order.status == 4:
                return Response({'ret': 420504, 'errmsg': '该订单正在退款中'})
            elif order.status == 5:
                return Response({'ret': 420505, 'errmsg': '该订单已退款'})

            # 判断可报名状态
            if order.ticket.activity.status == 1:  # 截止报名
                if order.bus_loc is not None:  # 上车点可用
                    return Response({'ret': 420502, 'errmsg': '活动截止报名且上车点可用，无法退票'})
            elif order.ticket.activity.status == 2:  # 锁票
                return Response({'ret': 420503, 'errmsg': '活动已经进入锁票阶段，无法退票'})

            # =================下面是可退票的情况================
            order.status = 4
            order.save()
            # todo 退款逻辑 ？？  调用退款？？


            # todo-f 移除订单有效性时，有一套需要联动的数据
            # 上车点人数-1(未截止时退票需要，已截止后上车点有效不能退/无效不需要)
            if order.bus_loc is not None:
                Boardingloc.objects.filter(id=order.bus_loc.id).update(choice_peoplenum=F('choice_peoplenum')-1)

            # 活动参与人数-1
            Activity.objects.filter(id=order.ticket.activity.id).update(current_participant=F('current_participant')-1)
            # 票销量-1
            Ticket.objects.filter(id=order.ticket.id).update(sales=F('sales')-1)
            # 用户积分-K
            User.objects.filter(id=userid).update(points=F('points')-USER_POINTS_INCREASE_DELTA)
            
            return Response({'ret': 0, 'errmsg': None})

        except Exception as e:
            print(repr(e))
            return Response({'ret': 420501, 'errmsg': '其他错误'})


# 选择新的上车点
class select_new_boardingloc(APIView):
    authentication_classes = [MyJWTAuthentication, ]

    def post(self,request,*args,**kwargs):
        userid = request.user['userid']

        info = json.loads(request.body)

        try:
            order_id = info['order_id']
            boardingloc_id = info['boardingloc_id']
            bus_id = info['bus_id']

            order = TicketOrder.objects.get(id=order_id)
            # 对于已发起退款或已退款的，修改上车点无效
            if order.status == 0:
                return Response({'ret': 420606, 'errmsg': '该订单已取消'})
            elif order.status == 3:
                return Response({'ret': 420607, 'errmsg': '该订单已锁定'})
            elif order.status == 4:
                return Response({'ret': 420604, 'errmsg': '该订单正在退款中'})
            elif order.status == 5:
                return Response({'ret': 420605, 'errmsg': '该订单已退款'})

            # 判断可报名状态
            if order.ticket.activity.status == 1:  # 截止报名
                if order.bus_loc is not None:  # 原上车点可用
                    return Response({'ret': 420602, 'errmsg': '活动截止报名且原上车点可用，不允许更换'})
            elif order.ticket.activity.status == 2:  # 锁票
                return Response({'ret': 420603, 'errmsg': '活动已经进入锁票阶段，无法操作'})


            # 判断所选大巴是否有空位
            with transaction.atomic():
                select_bus = Bus.objects.select_for_update().filter(id=bus_id)
                # 检查剩余名额# todo 注意检查空位数量，行锁！！
                if select_bus[0].max_people - select_bus[0].carry_peoplenum <= 0:
                    return Response({'ret': 420609, 'errmsg': '该车已经没有空位'})
                else:
                    # 设置bus
                    order.bus = select_bus[0]  # 订单绑定
                    select_bus[0].carry_peoplenum += 1  # 车上人数+1
                    select_bus[0].save()
                    # 设置boardingloc
                    select_boardingloc = Boardingloc.objects.select_for_update().filter(id=boardingloc_id)
                    order.bus_loc = select_boardingloc[0]  # 订单绑定
                    select_boardingloc.update(choice_peoplenum=F('choice_peoplenum')+1)  # 上车点人数+
                    # 设置上车时间，该车该点上车人数
                    select_bus_loc_time = Bus_boarding_time.objects.select_for_update().filter(bus_id=select_bus[0].id, loc_id=boardingloc_id)
                    order.bus_time = select_bus_loc_time[0]  # 订单绑定
                    select_bus_loc_time.update(boarding_peoplenum=F('boarding_peoplenum')+1)  # 该车经过该点上车人数+1
                    
                    # 将订单锁定
                    order.status = 3
                    order.save()

            return Response({'ret': 0, 'errmsg': None})

        except Exception as e:
            print(repr(e))
            return Response({'ret': 420601, 'errmsg': '其他错误'})


# 去程上车
class set_go_boarded(APIView):
    authentication_classes = [MyJWTAuthentication, ]

    def post(self,request,*args,**kwargs):
        # userid = request.user['userid']
        info = json.loads(request.body)

        try:
            order_id = info['order_id']
            TicketOrder.objects.filter(id=order_id).update(go_boarded=True)
            return Response({'ret':0})
        except Exception as e:
            print(repr(e))
            return Response({'ret': 420701})


# 返程上车
class set_return_boarded(APIView):
    authentication_classes = [MyJWTAuthentication, ]

    def post(self,request,*args,**kwargs):
        # userid = request.user['userid']
        info = json.loads(request.body)

        try:
            order_id = info['order_id']
            order = TicketOrder.objects.filter(id=order_id)
            
            current_date = timezone.now().date()
            one_hour_later = (timezone.now() + timedelta(minutes=30)).time()
            if order[0].ticket.activity.activity_end_date == current_date and \
                one_hour_later > order.ticket.activity.activity_return_time:      # 返程时间半小时内
                order.update(return_boarded=True)
                return Response({'ret':0, 'errmsg':None})
            else:
                return Response({'ret': 420803, 'errmsg':'集合时间前半小时可以上车签到'})
            
        except Exception as e:
            print(repr(e))
            return Response({'ret': 420801, 'errmsg':'其他错误'})


# 当前活动指引所在步骤
class get_activity_guide_step(APIView):
    authentication_classes = [MyJWTAuthentication, ]

    def post(self,request,*args,**kwargs):
        # userid = request.user['userid']
        info = json.loads(request.body)

        try:
            order_id = info['order_id']
            order = TicketOrder.objects.get(id=order_id)
            current_step = order.completed_steps
            total_step = len(ACTIVITY_GUIDE) - 1  # 0不算在内
            
            if order.completed_steps == 0:  # 未启用
                return Response({'ret': 420902, 
                                 'errmsg': '未启用活动指引',
                                 'data':{
                                    'current_step': current_step,
                                    'total_step': total_step,
                                    'content': None,
                                }
                                })
            elif order.completed_steps == total_step + 1:
                return Response({'ret': 420903, 
                                 'errmsg': '活动指引已完成',
                                 'data':{
                                    'current_step': total_step+1,
                                    'total_step': total_step,
                                    'content': '活动指引已完成'
                                }
                                })
            else:
                content = ACTIVITY_GUIDE[current_step]
                return Response({'ret':0,
                                'errmsg': None, 
                                'data':{
                                    'current_step': current_step,
                                    'total_step': total_step,
                                    'content': content
                                }
                                })
        except Exception as e:
            print(repr(e))
            return Response({'ret': 420901, 'errmsg': '其他错误', 'data': None})


# 活动指引下一步
class next_activity_guide_step(APIView):
    authentication_classes = [MyJWTAuthentication, ]

    def post(self,request,*args,**kwargs):
        # userid = request.user['userid']
        info = json.loads(request.body)

        try:
            order_id = info['order_id']
            total_step = len(ACTIVITY_GUIDE) - 1  # 0不算在内

            order = TicketOrder.objects.filter(id=order_id)
            if order[0].completed_steps == total_step + 1:  # 已完成
                return Response({'ret': 421002, 
                                 'errmsg': '在这步前已完成所有活动指引',
                                 'data':{
                                    'current_step': total_step + 1,
                                    'total_step': total_step,
                                    'content': '在这步前已完成所有活动指引'
                                }
                    })
            elif order[0].completed_steps == total_step:  # 这步完成即完成
                order.update(completed_steps=F('completed_steps')+1)
                return Response({'ret': 421003, 
                                 'errmsg': '成功完成所有活动指引',
                                 'data':{
                                        'current_step': total_step + 1,
                                        'total_step': total_step,
                                        'content': '成功完成所有活动指引'
                                    }
                    })

            else:
                order.update(completed_steps=F('completed_steps')+1)
                current_step = order[0].completed_steps
                content = ACTIVITY_GUIDE[current_step]
                return Response({'ret':0, 
                                 'errmsg': None,
                                'data':{
                                    'current_step': current_step,
                                    'total_step': total_step,
                                    'content': content
                                }
                                })
        except Exception as e:
            print(repr(e))
            return Response({'ret': 421001, 'errmsg': '其他错误', 'data': None})
        

# 跳过教程
class set_activity_guide_finished(APIView):
    authentication_classes = [MyJWTAuthentication, ]

    def post(self,request,*args,**kwargs):
        # userid = request.user['userid']
        info = json.loads(request.body)

        try:
            order_id = info['order_id']
            TicketOrder.objects.filter(id=order_id).update(completed_steps=len(ACTIVITY_GUIDE))
            return Response({'ret':0})
        except Exception as e:
            print(repr(e))
            return Response({'ret': 421101})
