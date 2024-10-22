import json
import datetime
from django.conf import settings
from django.forms.models import model_to_dict
from django.db.models import F
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import *
from user.auth import MyJWTAuthentication
from user.models import User


# ==================================信息获取======================================

# 获取滑雪场列表
class get_all_skiresort(APIView):
    def get(self,request,*args,**kwargs):
        all_skiresort = Skiresort.objects.all()
        serializer = SkiresortSerializer1(instance=all_skiresort, many=True)
        return Response({'ret': 0, 'data': list(serializer.data)})



class get_tickets_of_homepage_activity(APIView):
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
    def post(self,request,*args,**kwargs):
        info = json.loads(request.body)
        try:
            acti_templ_id = info['id']
            activity_templ = ActivityTemplate.objects.filter(id=acti_templ_id)
            skiresort_serializer = SkiresortSerializer3(instance=activity_templ[0].ski_resort, many=False)
            activity_templ_serializer = ActivityTemplateSerializer(instance=activity_templ[0], many=False)
            return Response({'ret': 0, 'errmsg': None, 
                             'data': {**skiresort_serializer.data, **activity_templ_serializer.data}
                            #  'data': {
                            #      'ski_resort': skiresort_serializer.data,
                            #      'activity_template': activity_templ_serializer.data
                            #  }
                             })
        except Exception as e:
            print(repr(e))
            return Response({'ret': 410201, 'errmsg': '其他错误', 'data': None})


class get_certain_ticket(APIView):
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





# =============================================================================


# ==========================================deprecated=======================================================

'''
class get_certain_activity(APIView):
    def post(self,request,*args,**kwargs):
        info = json.loads(request.body)
        try:
            acti_id = info['activity_id']
            activity = Activity.objects.get(id=acti_id)
            serializer = ActivitySerializer(instance=activity, many=False)
            return Response({'ret': 0, 'activity': serializer.data})
        except Exception as e:
            print(repr(e))
            return Response({'ret': -1, 'activity': None})
'''

'''
class get_active_activity(APIView):
    def get(self,request,*args,**kwargs):
        active_activity = Activity.objects.filter(registration_status=True)
        serializer = ActivitySerializer(instance=active_activity, many=True)
        return Response({'ret': 0, 'activity': list(serializer.data)})


'''


# =======================================================购票相关===========================================================
'''
class get_a_activity_order_by_activityid(APIView):  # 点到一个activity后先加载一下有没有对应的订单
    authentication_classes = [MyJWTAuthentication, ]

    def post(self,request,*args,**kwargs):
        userid = request.user['userid']
        info = json.loads(request.body)
        try:
            acti_id = info['activity_id']
            order_found = TicketOrder.objects.get(user_id=userid, activity_id=acti_id)
            serializer = OrderSerializer(instance=order_found, many=False)
            return Response({'ret': 0, 'order': serializer.data})
        except Exception as e:
            print(repr(e))
            return Response({'ret': -1, 'order': None})


class get_a_activity_order_by_orderid(APIView):  # 点到一个activity后先加载一下有没有对应的订单
    authentication_classes = [MyJWTAuthentication, ]

    def post(self,request,*args,**kwargs):
        userid = request.user['userid']
        info = json.loads(request.body)
        try:
            order_id = info['order_id']
            order_found = TicketOrder.objects.get(id=order_id)
            serializer = OrderSerializer(instance=order_found, many=False)
            return Response({'ret': 0, 'order': serializer.data})
        except Exception as e:
            print(repr(e))
            return Response({'ret': -1, 'order': None})


class get_all_activity_order(APIView):  # 一个用户的所有订单
    authentication_classes = [MyJWTAuthentication, ]

    def get(self,request,*args,**kwargs):
        userid = request.user['userid']
        try:
            order_found = TicketOrder.objects.filter(user_id=userid)
            serializer = OrderSerializer(instance=order_found, many=True)
            return Response({'ret': 0, 'order': list(serializer.data)})
        except Exception as e:
            print(repr(e))
            return Response({'ret': -1, 'order': None})



class create_activity_order(APIView):
    authentication_classes = [MyJWTAuthentication, ]

    def post(self,request,*args,**kwargs):
        userid = request.user['userid']

        ip = get_client_ip(request)

        try:
            user = User.objects.get(id=userid)
            # if user.is_student==False:
                # return Response({'ret': 3, 'errmsg': '用户不合法', 'activity_order_id':None, 'ordernumber':None})
        except:
            return Response({'ret': 3, 'errmsg': '用户不合法', 'activity_order_id':None, 'ordernumber':None, 'ip': ip})

        info = json.loads(request.body)

        try:
            acti_id = info['activity_id']

            acti = Activity.objects.get(id=acti_id)
            if acti.registration_status==False:
                    return Response({'ret': 2, 'errmsg': '已截止报名', 'activity_order_id':None, 'ordernumber':None, 'ip': ip})

            # need_rent = info['need_rent']
            bus_loc = info['bus_loc_id']

            order_found = TicketOrder.objects.filter(user_id=userid, activity_id=acti_id)  # 该用户对该活动的订单是否已经提交
            
            if order_found.count() == 0:
                try:
                    ordernumber = str(acti_id)+str(userid)+str(datetime.datetime.now())[:19].replace(' ', '').replace('-', '').replace(':', '')
                    neworder = TicketOrder.objects.create(ordernumber=ordernumber , user_id=userid, activity_id=acti_id, 
                                                  bus_loc_id=bus_loc)
                    
                    return Response({'ret': 0, 'errmsg': None, 'activity_order_id':neworder.id, 'ordernumber':ordernumber, 'ip': ip})
                except Exception as e:
                    print(repr(e))
                    return Response({'ret': -1, 'errmsg': '请检查提交的数据', 'activity_order_id':None, 'ordernumber':None, 'ip': ip})
            else:
                return Response({'ret': 1, 'errmsg': '订单已存在', 'activity_order_id':order_found[0].id, 'ordernumber':order_found[0].ordernumber, 'ip': ip})

        except Exception as e:
            print(repr(e))
            return Response({'ret': -1, 'errmsg': '请检查提交的数据', 'activity_order_id':None, 'ordernumber':None, 'ip': ip})


class set_activity_order_paid(APIView):
    authentication_classes = [MyJWTAuthentication, ]
    def post(self,request,*args,**kwargs):
        userid = request.user['userid']
        info = json.loads(request.body)

        try:
            order_id = info['activity_order_id']
            order_found = TicketOrder.objects.get(id=order_id, user_id=userid)
            
            if order_found.activity.registration_status==False:
                    return Response({'ret': 2, 'errmsg': '已截止报名'})

            order_found.activity.current_participant_num = F('current_participant_num') + 1  # 活动参与人数+1
            order_found.activity.save()
            order_found.is_paid = True
            order_found.save()

            order_found.bus_loc.loc_peoplenum = F('loc_peoplenum') + 1  # 上车点人数+1
            order_found.bus_loc.save()


            return Response({'ret': 0, 'errmsg': None})
        except Exception as e:
            print(repr(e))
            return Response({'ret': -1, 'errmsg': '订单不存在'})


class cancel_order(APIView):
    authentication_classes = [MyJWTAuthentication, ]
    def post(self,request,*args,**kwargs):
        userid = request.user['userid']
        info = json.loads(request.body)

        try:
            order_id = info['activity_order_id']
            order_found = TicketOrder.objects.get(id=order_id, user_id=userid)
            
            if order_found.activity.registration_status==False:  # 针对已付款，禁止退款
                    return Response({'ret': 2, 'errmsg': '已截止报名'})

            if order_found.is_paid == True:
                order_found.activity.current_participant_num = F('current_participant_num') - 1  # 活动参与人数-1
                order_found.activity.save()

                order_found.bus_loc.loc_peoplenum = F('loc_peoplenum') - 1  # 上车点人数-1
                order_found.bus_loc.save()


            order_found.delete()
            return Response({'ret': 0, 'errmsg': None})
        except Exception as e:
            print(repr(e))
            return Response({'ret': -1, 'errmsg': '订单不存在'})
'''

# =================================================================================================================










'''
class get_home_page(APIView):
    authentication_classes = [MyJWTAuthentication, ]
    def get(self,request,*args,**kwargs):
        userid = request.user['userid']
        try:
            user = User.objects.get(id=userid)
            return Response({'ret': 0, 'user_data': user_serializer.data, 'activity_data':})
        except Exception as e:
            print(repr(e))
            return Response({'ret': 410001, 'data': None})        
'''


'''
class get_rentprice(APIView):
    def post(self,request,*args,**kwargs):
        info = json.loads(request.body)
        ski_resort_id = info['ski_resort_id']
        try:
            activity = RentPrice.objects.get(ski_resort_id=ski_resort_id)
            return Response({'ret': 0, 'rentprice': model_to_dict(activity)})
        except Exception as e:
            print(repr(e))
            return Response({'ret': -1, 'rentprice': None})


class create_rent_order(APIView):  # 租赁和活动订单绑定（和某个activity绑定）
    authentication_classes = [MyJWTAuthentication, ]

    def post(self,request,*args,**kwargs):
        userid = request.user['userid']
        info = json.loads(request.body)
        try:
            activity_order_id = info['activity_order_id']
            order_found = TicketOrder.objects.get(id=activity_order_id, user_id=userid)
            
            if order_found.activity.registration_status==False:
                return Response({'ret': 2, 'errmsg': '已截止报名', 'rent_order_id':None})
            if order_found.activity.need_rent==False:
                return Response({'ret': 3, 'errmsg': '不提供租赁', 'rent_order_id':None})
            if order_found.need_rent==True:
                return Response({'ret': 4, 'errmsg': '该订单已存在对应的租赁单', 'rent_order_id':None})

            acti_id = order_found.activity.id
            duration_days = order_found.activity.duration_days
            helmet = info['helmet']
            glasses = info['glasses']
            gloves = info['gloves']
            hippad = info['hippad']
            kneepad = info['kneepad']
            wristpad = info['wristpad']
            snowboard = info['snowboard']
            skiboots = info['skiboots']

            newrentorder = RentOrder.objects.create(user_id=userid, activity_id=acti_id, order_id=activity_order_id,
                                            duration_days=duration_days, helmet=helmet, glasses=glasses,
                                            gloves=gloves, hippad=hippad, kneepad=kneepad, wristpad=wristpad,
                                            snowboard=snowboard, skiboots=skiboots, is_active=order_found.is_paid)
            order_found.need_rent = True  # 标记该订单有对应的租赁单
            order_found.save()

            return Response({'ret': 0, 'errmsg': None, 'rent_order_id':newrentorder.id})
        except Exception as e:
            print(repr(e))
            return Response({'ret': -1, 'errmsg': '请检查提交的数据', 'rent_order_id':None})


class get_a_rent_order(APIView):  # 一个activity order对应的rent order
    authentication_classes = [MyJWTAuthentication, ]

    def post(self,request,*args,**kwargs):
        userid = request.user['userid']
        info = json.loads(request.body)
        
        try:
            activity_order_id = info['activity_order_id']  # 用orderid
            rentorder_found = RentOrder.objects.get(user_id=userid, order_id=activity_order_id)
            
            if rentorder_found.activity.need_rent==False:
                return Response({'ret': 3, 'errmsg': '不提供租赁', 'rentorder': None})

            return Response({'ret': 0, 'errmsg': None, 'rentorder': model_to_dict(rentorder_found)})
        except Exception as e:
            print(repr(e))
            return Response({'ret': -1, 'errmsg': '租赁单不存在', 'rentorder': None})


class cancel_rent_order(APIView):  # 一个activity order对应的rent order
    authentication_classes = [MyJWTAuthentication, ]

    def post(self,request,*args,**kwargs):
        userid = request.user['userid']
        info = json.loads(request.body)
        try:
            rent_order_id = info['rent_order_id']
            rentorder_found = RentOrder.objects.get(id=rent_order_id, user_id=userid)
            
            if rentorder_found.activity.registration_status==False:
                    return Response({'ret': 2, 'errmsg': '已截止报名'})

            rentorder_found.delete()

            rentorder_found.order.need_rent = False  # 标记该订单没有对应的租赁单
            rentorder_found.order.save()

            return Response({'ret': 0, 'errmsg': None})
        except Exception as e:
            print(repr(e))
            return Response({'ret': -1, 'errmsg': '租赁单不存在'})

class set_activity_order_paid(APIView):
    authentication_classes = [MyJWTAuthentication, ]
    def post(self,request,*args,**kwargs):
        userid = request.user['userid']
        info = json.loads(request.body)

        try:
            order_id = info['activity_order_id']
            order_found = TicketOrder.objects.get(id=order_id, user_id=userid)
            
            if order_found.activity.registration_status==False:
                    return Response({'ret': 2, 'errmsg': '已截止报名'})

            order_found.activity.current_participant_num = F('current_participant_num') + 1  # 活动参与人数+1
            order_found.activity.save()
            order_found.is_paid = True
            order_found.save()

            order_found.bus_loc.loc_peoplenum = F('loc_peoplenum') + 1  # 上车点人数+1
            order_found.bus_loc.save()

            if order_found.need_rent==True:
                # 激活对应的租赁单
                try:
                    rentorder_found = RentOrder.objects.get(user_id=userid, order_id=order_id)
                    rentorder_found.is_active = True
                    rentorder_found.save()
                except Exception as e:
                    print(repr(e))
                    order_found.need_rent = False
                    order_found.save()

            return Response({'ret': 0, 'errmsg': None})
        except Exception as e:
            print(repr(e))
            return Response({'ret': -1, 'errmsg': '订单不存在'})            
'''