import json
import datetime
from django.conf import settings
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db.models import Q, F

from user.models import User
from user.auth import MyJWTAuthentication
from .models import *


WXGROUP_MAX_NUM = 180
USER_POINTS_INCREASE_DELTA = 0

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
                    

                    # 创建订单
                    ordernumber = str(userid).zfill(6)+str(datetime.datetime.now())[:24].replace(' ', '').replace('-', '').replace(':', '').replace('.', '')
                    neworder = TicketOrder.objects.create(ordernumber=ordernumber , user_id=userid, ticket_id=ticket_id, 
                                                  bus_loc_id=bus_loc_id, wxgroup_id=wxgroup_choice.id)
                    
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
                    return Response({'ret': 420008, 'errmsg': '其他错误', 
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


class get_all_itinerary(APIView):
    authentication_classes = [MyJWTAuthentication, ]

    def get(self,request,*args,**kwargs):
        try:
            userid = request.user['userid']
            current_date = timezone.now().date()
            orders = TicketOrder.objects.filter(user_id=userid, 
                                                # 不要已结束的行程
                                               ticket__activity__activity_end_date__gt=current_date)
            serializer = OrderSerializerItinerary1(instance=orders, many=True)
            return Response({'ret': 0, 'data': list(serializer.data)})
        except Exception as e:
            print(repr(e))
            return Response({'ret': 420201, 'data': None})
        

class get_detail_of_certain_itinerary(APIView):
    authentication_classes = [MyJWTAuthentication, ]

    def post(self,request,*args,**kwargs):
        info = json.loads(request.body)
        try:
            userid = request.user['userid']
            order_id = info['id']

            order = TicketOrder.objects.filter(user_id=userid, id=order_id)
            
            serializer = OrderSerializerItinerary1(instance=order[0], many=False)
            
            return Response({'ret': 0, 'data': serializer.data})
        except Exception as e:
            print(repr(e))
            return Response({'ret': 420201, 'data': None})