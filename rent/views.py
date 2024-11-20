import json
import requests
import datetime
from django.conf import settings
from django.forms.models import model_to_dict
from django.db.models import F
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import *
from user.auth import MyJWTAuthentication

# Create your views here.

class get_busloc(APIView):
    def post(self,request,*args,**kwargs):
        info = json.loads(request.body)
        try:
            acti_id = info['activity_id']
            busloc = Busloc.objects.filter(activity_id=acti_id)
            if busloc.count() == 0:
                return Response({'ret': -1, 'activity': None})
            serializer = BuslocSerializer(instance=busloc, many=True)
            return Response({'ret': 0, 'activity': list(serializer.data)})
        except Exception as e:
            print(repr(e))
            return Response({'ret': -1, 'activity': None})


class get_activity_all(APIView):
    def get(self,request,*args,**kwargs):
        all_activity = Activity.objects.all()
        serializer = ActivitySerializer(instance=all_activity, many=True)
        return Response({'ret': 0, 'activity': list(serializer.data)})


class get_activity_active(APIView):
    def get(self,request,*args,**kwargs):
        active_activity = Activity.objects.filter(registration_status=True)
        serializer = ActivitySerializer(instance=active_activity, many=True)
        return Response({'ret': 0, 'activity': list(serializer.data)})


class get_a_activity(APIView):
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


class get_rentprice(APIView):
    def post(self,request,*args,**kwargs):
        info = json.loads(request.body)
        ski_resort_id = info['ski_resort_id']
        try:
            activity = Rentprice.objects.get(ski_resort_id=ski_resort_id)
            return Response({'ret': 0, 'rentprice': model_to_dict(activity)})
        except Exception as e:
            print(repr(e))
            return Response({'ret': -1, 'rentprice': None})


class get_a_activity_order_by_activityid(APIView):  # 点到一个activity后先加载一下有没有对应的订单
    authentication_classes = [MyJWTAuthentication, ]

    def post(self,request,*args,**kwargs):
        userid = request.user['userid']
        info = json.loads(request.body)
        try:
            acti_id = info['activity_id']
            order_found = Order.objects.get(user_id=userid, activity_id=acti_id)
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
            order_found = Order.objects.get(id=order_id)
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
            order_found = Order.objects.filter(user_id=userid)
            serializer = OrderSerializer(instance=order_found, many=True)
            return Response({'ret': 0, 'order': list(serializer.data)})
        except Exception as e:
            print(repr(e))
            return Response({'ret': -1, 'order': None})


def get_client_ip(request):

    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')

    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[-1].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')

    return ip

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

            order_found = Order.objects.filter(user_id=userid, activity_id=acti_id)  # 该用户对该活动的订单是否已经提交
            
            if order_found.count() == 0:
                try:
                    ordernumber = str(acti_id)+str(userid)+str(datetime.datetime.now())[:19].replace(' ', '').replace('-', '').replace(':', '')
                    neworder = Order.objects.create(ordernumber=ordernumber , user_id=userid, activity_id=acti_id, 
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
            order_found = Order.objects.get(id=order_id, user_id=userid)
            
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
                    rentorder_found = Rentorder.objects.get(user_id=userid, order_id=order_id)
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


class cancel_order(APIView):
    authentication_classes = [MyJWTAuthentication, ]
    def post(self,request,*args,**kwargs):
        userid = request.user['userid']
        info = json.loads(request.body)

        try:
            order_id = info['activity_order_id']
            order_found = Order.objects.get(id=order_id, user_id=userid)
            
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


class create_rent_order(APIView):  # 租赁和活动订单绑定（和某个activity绑定）
    authentication_classes = [MyJWTAuthentication, ]

    def post(self,request,*args,**kwargs):
        userid = request.user['userid']
        info = json.loads(request.body)
        try:
            activity_order_id = info['activity_order_id']
            order_found = Order.objects.get(id=activity_order_id, user_id=userid)
            
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

            newrentorder = Rentorder.objects.create(user_id=userid, activity_id=acti_id, order_id=activity_order_id,
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
            rentorder_found = Rentorder.objects.get(user_id=userid, order_id=activity_order_id)
            
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
            rentorder_found = Rentorder.objects.get(id=rent_order_id, user_id=userid)
            
            if rentorder_found.activity.registration_status==False:
                    return Response({'ret': 2, 'errmsg': '已截止报名'})

            rentorder_found.delete()

            rentorder_found.order.need_rent = False  # 标记该订单没有对应的租赁单
            rentorder_found.order.save()

            return Response({'ret': 0, 'errmsg': None})
        except Exception as e:
            print(repr(e))
            return Response({'ret': -1, 'errmsg': '租赁单不存在'})
