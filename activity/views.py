import json
import datetime
from django.conf import settings
from django.forms.models import model_to_dict
from django.db.models import F, Q
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import *
from user.auth import MyJWTAuthentication
from user.models import User


# ==================================信息获取======================================

# 获取滑雪场列表
class get_all_skiresort(APIView):
    authentication_classes = [MyJWTAuthentication, ]

    def get(self,request,*args,**kwargs):
        all_skiresort = Skiresort.objects.all()
        serializer = SkiresortSerializer1(instance=all_skiresort, many=True)
        return Response({'ret': 0, 'data': list(serializer.data)})



class get_tickets_of_homepage_activity(APIView):
    authentication_classes = [MyJWTAuthentication, ]

    def get(self,request,*args,**kwargs):
        try:
            activity_found = Activity.objects.filter().order_by('-create_time')
            skiresort_id = activity_found[0].activity_template.ski_resort.id
            skiresort_found = Skiresort.objects.filter(id=skiresort_id)
            ticket_found = Ticket.objects.filter(activity__activity_template__ski_resort__id=skiresort_id)
            skiresort_serializer = SkiresortSerializer2(instance=skiresort_found[0], many=False)
            ticket_serializer = TicketSerializer1(instance=ticket_found, many=True)

            return Response({'ret': 0, 'errmsg': None, 
                             'data': {
                                 'ski_resort': skiresort_serializer.data,
                                 'ticket': list(ticket_serializer.data)
                             }
                             })
        except Exception as e:
            print(repr(e))
            return Response({'ret': 410001, 'errmsg': '其他错误', 'data': None})


class get_tickets_of_certain_skiresort(APIView):
    authentication_classes = [MyJWTAuthentication, ]

    def post(self,request,*args,**kwargs):
        info = json.loads(request.body)
        try:
            skiresort_id = info['id']
            skiresort_found = Skiresort.objects.filter(id=skiresort_id)
            ticket_found = Ticket.objects.filter(activity__activity_template__ski_resort__id=skiresort_id)
            skiresort_serializer = SkiresortSerializer2(instance=skiresort_found[0], many=False)
            ticket_serializer = TicketSerializer1(instance=ticket_found, many=True)

            return Response({'ret': 0, 'errmsg': None, 
                             'data': {
                                 'ski_resort': skiresort_serializer.data,
                                 'ticket': list(ticket_serializer.data)
                             }
                             })
        except Exception as e:
            print(repr(e))
            return Response({'ret': 410101, 'errmsg': '其他错误', 'data': None})


class get_certain_activity_template(APIView):
    authentication_classes = [MyJWTAuthentication, ]

    def post(self,request,*args,**kwargs):
        userid = request.user['userid']
        info = json.loads(request.body)
        try:
            acti_templ_id = info['activitytemplate_id']
            activity_id = info['activity_id']
            activity_templ = ActivityTemplate.objects.filter(id=acti_templ_id)
            skiresort_serializer = SkiresortSerializer3(instance=activity_templ[0].ski_resort, many=False)
            activity_templ_serializer = ActivityTemplateSerializer(instance=activity_templ[0], many=False)
            
            # 判断是否可以购票
            # 是否截止报名
            activity = Activity.objects.get(id=activity_id)
            is_available = True if activity.status==0 else False
            # 是否已有有效订单
            from order.models import TicketOrder
            TicketOrder.cancel_paid_timeout_orders()  # 先检查超时未支付订单
            order_found = TicketOrder.objects.filter(Q(user_id=userid) & Q(ticket__activity_id=activity_id) &
                                                     (Q(status=1) | Q(status=2) | Q(status=3) | Q(status=4)))  # 已取消和完成退款的以及已经删了的为无效的
            if order_found.count() == 0:
                have_valid_order = False
            else:
                have_valid_order = True

            return Response({'ret': 0, 'errmsg': None, 
                             'data': {**skiresort_serializer.data, **activity_templ_serializer.data,
                                      'is_available': is_available, 'have_valid_order': have_valid_order}
                            #  'data': {
                            #      'ski_resort': skiresort_serializer.data,
                            #      'activity_template': activity_templ_serializer.data
                            #  }
                             })
        except Exception as e:
            print(repr(e))
            return Response({'ret': 410201, 'errmsg': '其他错误', 'data': None})


class get_certain_ticket(APIView):
    authentication_classes = [MyJWTAuthentication, ]

    def post(self,request,*args,**kwargs):
        info = json.loads(request.body)
        try:
            ticket_id = info['id']
            ticket = Ticket.objects.get(id=ticket_id)
            serializer = TicketSerializer2(instance=ticket, many=False)
            return Response({'ret': 0, 'data': serializer.data})
        except Exception as e:
            print(repr(e))
            return Response({'ret': 410301, 'data': None})


class get_boardingloc(APIView):
    authentication_classes = [MyJWTAuthentication, ]

    def post(self,request,*args,**kwargs):
        info = json.loads(request.body)
        try:
            activity_id = info['id']
            boardingloc = Boardingloc.objects.filter(activity_id=activity_id)
            serializer = BoardinglocSerializer(instance=boardingloc, many=True)
            raw_data = list(serializer.data)

            # 按area分区重新组织上车点
            ret_dict = {}
            for bloc in raw_data:
                if bloc['area'] in list(ret_dict.keys()):
                    ret_dict[bloc['area']].append(bloc)
                else:
                    ret_dict[bloc['area']] = [bloc, ]
            
            # return Response({'ret': 0, 'data': ret_list})
            return Response({'ret': 0, 'data': ret_dict})
        except Exception as e:
            print(repr(e))
            return Response({'ret': 410401, 'data': None})

            # # 按area分区重新组织上车点
            # ret_list = []
            # for bloc in raw_data:
            #     if bloc['area'] in [i['area'] for i in ret_list]:  # 该区域已录入
            #         for index, r_dict in enumerate(ret_list):
            #             if bloc['area'] == r_dict['area']:
            #                 r_dict['data'].append(bloc)
            #     else:   # 该区域未录入
            #         ret_list.append(
            #             {
            #                 'area': bloc['area'],
            #                 'data': [bloc]
            #             }
            #         )


# 获取合作学校的列表
class get_parner_school(APIView):
    authentication_classes = [MyJWTAuthentication, ]

    def get(self,request,*args,**kwargs):
        all_school = School.objects.all().order_by('-id')
        return Response({'ret': 0, 'data': list(all_school.values())})