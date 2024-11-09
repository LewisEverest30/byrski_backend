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
from activity.models import Activity
from .qrverif import QRVerif, QR_VALID_PERIOD


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
            user.school_id = info['school_id']
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
                    # 绑定微信群（取消和退款的和删除的也会占用群名额）
                    this_acti_order_num = TicketOrder.objects.filter(ticket__activity_id=ticket.activity.id).count()
                    wxgroup_index = int(this_acti_order_num / WXGROUP_MAX_NUM)
                    # wxgroup_choice = ActivityWxGroup.objects.filter(activity_id=ticket.activity.id).order_by('id')[wxgroup_index]
                    
                    try:
                        wxgroup_choice = ActivityWxGroup.objects.filter(activity_id=ticket.activity.id).order_by('id')[wxgroup_index]
                    except Exception as e:
                        print(repr(e))
                        return Response({'ret': 420010, 'errmsg': '可用微信群数量不足', 
                                        'data': {
                                            'order_id':None, 
                                            'ordernumber':None, 
                                            'ip': ip
                                        },
                                        })
                    
                    
                    # 创建订单
                    # ordernumber = str(userid).zfill(6)+str(datetime.datetime.now())[2:20].replace(' ', '').replace('-', '').replace(':', '').replace('.', '')
                    ordernumber = ('out_trade_no_'+str(datetime.datetime.now())).replace(' ', '').replace('-', '').replace(':', '').replace('.', '')[:32]
                    
                    neworder = TicketOrder.objects.create(ordernumber=ordernumber , user_id=userid, ticket_id=ticket_id, 
                                                  bus_loc_id=bus_loc_id, wxgroup_id=wxgroup_choice.id,
                                                  cost=ticket.price)
                    
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
            order = TicketOrder.objects.get(Q(id=order_id) & ~Q(status=6))
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
                                            Q(ticket__activity__activity_end_date__gte=current_date)).order_by('-create_time')  # 不要已结束的行程
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

            order = TicketOrder.objects.get(Q(id=order_id) & ~Q(status=6))
            
            serializer = OrderSerializerItinerary2(instance=order, many=False)
            
            return Response({'ret': 0, 'data': serializer.data})
        except Exception as e:
            print(repr(e))
            return Response({'ret': 420301, 'data': None})


# 尝试发起退款
class try_refund_ticket_order(APIView):
    authentication_classes = [MyJWTAuthentication, ]

    def post(self,request,*args,**kwargs):
        userid = request.user['userid']

        info = json.loads(request.body)

        try:
            order_id = info['order_id']

            order = TicketOrder.objects.get(Q(id=order_id) & ~Q(status=6))
            # 对于已发起退款或已退款的，不要重复退款
            if order.status == 0:
                return Response({'ret': 420506, 'errmsg': '该订单已取消'})
            elif order.status == 1:
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

            order = TicketOrder.objects.get(Q(id=order_id) & ~Q(status=6))
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

            # 检查新上车点是否合法
            try:
                bus_loc = Boardingloc.objects.get(id=boardingloc_id)
            except:
                return Response({'ret': 420608, 'errmsg': '上车点不合法'})
            
            # 原上车点如果存在，原上车点人数-1
            if order.bus_loc is not None:
                Boardingloc.objects.filter(id=order.bus_loc.id).update(choice_peoplenum=F('choice_peoplenum')-1)

            # 新上车点人数+1
            Boardingloc.objects.filter(id=boardingloc_id).update(choice_peoplenum=F('choice_peoplenum')+1)

            # 更新订单上车点
            order.bus_loc_id = bus_loc.id
            order.save()

            return Response({'ret': 0, 'errmsg': None})

        except Exception as e:
            print(repr(e))
            return Response({'ret': 420601, 'errmsg': '其他错误'})


# 去程上车
class set_go_boarded(APIView):
    authentication_classes = [MyJWTAuthentication, ]

    def post(self,request,*args,**kwargs):
        userid = request.user['userid']
        info = json.loads(request.body)

        try:
            order_id = info['order_id']
            TicketOrder.objects.filter(Q(user_id=userid) & Q(id=order_id) & ~Q(status=6)).update(go_boarded=True)
            return Response({'ret':0})
        except Exception as e:
            print(repr(e))
            return Response({'ret': 420701})


# 返程上车
class set_return_boarded(APIView):
    authentication_classes = [MyJWTAuthentication, ]

    def post(self,request,*args,**kwargs):
        userid = request.user['userid']
        info = json.loads(request.body)

        try:
            order_id = info['order_id']
            order = TicketOrder.objects.filter(Q(user_id=userid) & Q(id=order_id) & ~Q(status=6))
            
            current_date = timezone.now().date()
            one_hour_later = (timezone.now() + timedelta(minutes=30)).time()
            if order[0].ticket.activity.activity_end_date == current_date and \
                one_hour_later > order[0].ticket.activity.activity_return_time:      # 返程时间半小时内
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
            order = TicketOrder.objects.get(Q(id=order_id) & ~Q(status=6))
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
        userid = request.user['userid']
        info = json.loads(request.body)

        try:
            order_id = info['order_id']
            total_step = len(ACTIVITY_GUIDE) - 1  # 0不算在内

            order = TicketOrder.objects.filter(Q(user_id=userid) & Q(id=order_id) & ~Q(status=6))
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
        userid = request.user['userid']
        info = json.loads(request.body)

        try:
            order_id = info['order_id']
            TicketOrder.objects.filter(Q(user_id=userid) & Q(id=order_id) & ~Q(status=6)).update(completed_steps=len(ACTIVITY_GUIDE))
            return Response({'ret':0})
        except Exception as e:
            print(repr(e))
            return Response({'ret': 421101})


# ===================================================订单相关===============================================
# 获取所有订单
class get_ticket_order_list_by_type(APIView):
    authentication_classes = [MyJWTAuthentication, ]

    def post(self,request,*args,**kwargs):
        userid = request.user['userid']
        info = json.loads(request.body)

        try:
            # 待付款 1  === 待付款
            # 进行中 2  === 已付款+已锁票 且未完成
            # 退款售后 3 === 退款中/已退款

            print(userid)
            status_type = info['type']
            if status_type == 0:  # 全部（不包括已删除的）
                orders = TicketOrder.objects.filter(Q(user_id=userid) & ~Q(status=6)).order_by('-create_time')
            elif status_type == 1:  # 待付款
                orders = TicketOrder.objects.filter(Q(user_id=userid) & Q(status=1)).order_by('-create_time')
            elif status_type == 2:  # 进行中
                orders = TicketOrder.objects.filter(Q(user_id=userid) & (Q(status=2) | Q(status=3)) & Q(return_boarded=False)).order_by('-create_time')
            elif status_type == 3:  # 已完成
                orders = TicketOrder.objects.filter(Q(user_id=userid) & Q(status=3) & Q(return_boarded=True)).order_by('-create_time')
            elif status_type == 4:  # 退款售后
                orders = TicketOrder.objects.filter(Q(user_id=userid) & (Q(status=4) | Q(status=5))).order_by('-create_time')
            
            serializer = OrderSerializer3(instance=orders, many=True)
            data = serializer.data                
            return Response({'ret':0, 'data':data})
        except Exception as e:
            print(repr(e))
            return Response({'ret': 421201, 'data':None})


# 获取订单详情
class get_detail_of_certain_ticket_order(APIView):
    authentication_classes = [MyJWTAuthentication, ]

    def post(self,request,*args,**kwargs):
        userid = request.user['userid']
        info = json.loads(request.body)

        try:
            TicketOrder.cancel_paid_timeout_orders()
            order_id = info['order_id']
            order = TicketOrder.objects.get(Q(id=order_id) & ~Q(status=6))
            
            serializer = OrderSerializer4(instance=order, many=False)
            data = serializer.data                
            return Response({'ret':0, 'data':data})
        except Exception as e:
            print(repr(e))
            return Response({'ret': 421301, 'data':None})


# 取消订单
class cancel_ticket_order(APIView):
    authentication_classes = [MyJWTAuthentication, ]

    def post(self,request,*args,**kwargs):
        userid = request.user['userid']
        info = json.loads(request.body)

        try:
            order_id = info['order_id']

            order = TicketOrder.objects.get(Q(id=order_id) & ~Q(status=6))
            # 订单状态，只有待付款状态下可以取消
            if order.status == 0:
                return Response({'ret': 421406, 'errmsg': '该订单已取消'})
            elif order.status == 2:
                return Response({'ret': 421408, 'errmsg': '该订单已付款'})
            elif order.status == 3:
                return Response({'ret': 421407, 'errmsg': '该订单已锁定'})
            elif order.status == 4:
                return Response({'ret': 421404, 'errmsg': '该订单正在退款中'})
            elif order.status == 5:
                return Response({'ret': 421405, 'errmsg': '该订单已退款'})

            # 活动状态(其实不会走这个分支，在活动状态)
            if order.ticket.activity.status == 1:  # 截止报名
                return Response({'ret': 421402, 'errmsg': '活动已经进入截止报名阶段，无法取消'})
            if order.ticket.activity.status == 2:  # 锁票
                return Response({'ret': 421403, 'errmsg': '活动已经进入锁票阶段，无法取消'})

            # =================下面是可取消的情况================
            order.status = 0
            order.save()
            # 上车点人数-1
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
            return Response({'ret': 421401, 'errmsg': '其他错误'})


# 删除订单
class delete_ticket_order(APIView):
    authentication_classes = [MyJWTAuthentication, ]

    def post(self,request,*args,**kwargs):
        userid = request.user['userid']

        info = json.loads(request.body)

        try:
            order_id = info['order_id']

            order = TicketOrder.objects.get(Q(id=order_id))
            # 订单状态
            # 已取消，已退款和已完成的可以删除
            if order.status == 6:
                return Response({'ret': 421502, 'errmsg': '该订单已被删除'})
            elif (order.status == 0) or (order.status == 5) or (order.return_boarded == True):
                # 可删除的情况
                order.status = 6
                order.save()
                return Response({'ret': 0, 'errmsg': None})
            else:
                 return Response({'ret': 421503, 'errmsg': '该订单不能被删除'})

        except Exception as e:
            print(repr(e))
            return Response({'ret': 421501, 'errmsg': '其他错误'})



# ================================二维码验证相关================================
class get_itinerary_qrcode(APIView):
    authentication_classes = [MyJWTAuthentication, ]
    def post(self,request,*args,**kwargs):
        userid = request.user['userid']
        # userid = request.query_params['userid']   #本地测试无验证使用
        info = json.loads(request.body)
        try:
            order_id = info['order_id']
            order = TicketOrder.objects.get(Q(id=order_id) & ~Q(status=6))
        except:
            return Response({'ret': 421901, 'errmsg':"行程不存在",'data':None})

        if order.ticket_checked == True:
            return Response({'ret': 421902, 'errmsg':"已验票",'data':None})
        qr_encode = None
        orderNumber = order.ordernumber
        qr_encode = QRVerif.encrypt_info(order_id=orderNumber)
        if qr_encode:
            return Response({'ret': 0, 'data':qr_encode})
        else:
            return Response({'ret': 421903, 'errmsg': "加密错误",'data':None})


class verify_itinerary_qrcode(APIView):
    authentication_classes = [MyJWTAuthentication, ]
    def post(self,request,*args,**kwargs):
        # userid = request.user['userid']    # 领队ID
        info = json.loads(request.body)
        try:
            qr_code = info['qr_code']
            timestamp, ordernumber, cur_time = QRVerif.decrypt_info(qr_code)
            if int(cur_time) - int(timestamp) < QR_VALID_PERIOD:
                orders = TicketOrder.objects.filter(Q(ordernumber=ordernumber) & Q(ticket_checked=0))
                if len(orders):
                    TicketOrder.objects.filter(Q(ordernumber=ordernumber)).update(ticket_checked=1)
                    return Response({'ret': 0, 'data':'Success'})
                else:
                    return Response({'ret': 422001,'errmsg':"已验票",'data':None})
            else:
                return Response({'ret': 422002,'errmsg':"二维码超时",'data':None})
        except:
            return Response({'ret': 422003,'errmsg':"加密密钥错误",'data':None})


# ================================领队相关================================
# 获取领队的行程列表
class get_all_leader_itinerary(APIView):
    authentication_classes = [MyJWTAuthentication, ]

    def get(self,request,*args,**kwargs):
        try:
            userid = request.user['userid']
            current_date = timezone.now().date()
            orders = LeaderItinerary.objects.filter(Q(leader__user_id=userid) & 
                                            Q(bus__activity__activity_end_date__gte=current_date))  # 不要已结束的行程
            serializer = LeaderItinerarySerializer1(instance=orders, many=True)
            return Response({'ret': 0, 'data': list(serializer.data)})
        except Exception as e:
            print(repr(e))
            return Response({'ret': 422101, 'data': None})


# 获取领队的行程详情
class get_detail_of_leader_itinerary(APIView):
    authentication_classes = [MyJWTAuthentication, ]

    def post(self,request,*args,**kwargs):
        info = json.loads(request.body)
        try:
            userid = request.user['userid']
            itin_id = info['leader_itinerary_id']

            order = LeaderItinerary.objects.get(Q(id=itin_id))
            
            serializer = LeaderItinerarySerializer2(instance=order, many=False)
            
            return Response({'ret': 0, 'data': serializer.data})
        except Exception as e:
            print(repr(e))
            return Response({'ret': 422201, 'data': None})


# 获取去程各站上车人数
class get_go_bus_boarding_passenger_num(APIView):
    authentication_classes = [MyJWTAuthentication, ]

    def post(self,request,*args,**kwargs):
        userid = request.user['userid']

        info = json.loads(request.body)

        try:
            leader_itinerary_id = info['leader_itinerary_id']
            boardingloc_id= info['boardingloc_id']

            try:
                leader_itinerary = LeaderItinerary.objects.get(Q(id=leader_itinerary_id))
            except:
                return Response({'ret': 422702, 'errmsg': '没有找到对应的领队行程'})

            # 所有去程未上车的订单
            orders_unboarded = TicketOrder.objects.filter(Q(bus_id=leader_itinerary.bus.id) & Q(go_boarded=False) & Q(status=3))
            # 从orders_unboarded中筛选该站的订单（不重新查询数据库）
            orders_this_stop_unboarded = [order for order in orders_unboarded if order.bus_loc_id == boardingloc_id]
            # orders_this_stop_unboarded = TicketOrder.objects.filter(Q(bus_id=leader_itinerary.bus.id) & Q(bus_loc_id=boardingloc_id) & Q(go_boarded=False)
            bus_time = Bus_boarding_time.objects.get(bus_id=leader_itinerary.bus.id, loc_id=boardingloc_id)

            ret_data = {
                'this_stop_unboarded_passenger_num': len(orders_this_stop_unboarded),
                'this_stop_passenger_num': bus_time.boarding_peoplenum,
                'total_unboarded_passenger_num': orders_unboarded.count(),
                'total_passenger_num': leader_itinerary.bus.carry_peoplenum,
            }

            return Response({'ret': 0, 'data': ret_data})

        except Exception as e:
            print(repr(e))
            return Response({'ret': 422701, 'errmsg': '其他错误'})



# 获取去程某站上车名单
class get_go_bus_boarding_passenger_list(APIView):
    authentication_classes = [MyJWTAuthentication, ]

    def post(self,request,*args,**kwargs):
        userid = request.user['userid']

        info = json.loads(request.body)

        try:
            leader_itinerary_id = info['leader_itinerary_id']
            boardingloc_id= info['boardingloc_id']

            try:
                leader_itinerary = LeaderItinerary.objects.get(Q(id=leader_itinerary_id))
            except:
                return Response({'ret': 422802, 'errmsg': '没有找到对应的领队行程'})

            orders = TicketOrder.objects.filter(Q(bus_id=leader_itinerary.bus.id) & Q(bus_loc_id=boardingloc_id) & Q(status=3)).order_by('go_boarded')
            bus_time = Bus_boarding_time.objects.get(bus_id=leader_itinerary.bus.id, loc_id=boardingloc_id)

            ret_data = {
                'this_stop_unboarded_passenger_num': 0,
                'this_stop_passenger_num': bus_time.boarding_peoplenum,
                'unboarded': [],
                'total': [],
            }
            for order in orders:
                if order.go_boarded == False:    # 未上车
                    ret_data['this_stop_unboarded_passenger_num'] += 1
                    unboarded_order_dict = {
                        'passenger_name': order.user.name,
                        'gender': order.user.gender,
                        'phone': order.user.phone,
                        'boarding_loc': order.bus_loc.loc.busboardloc,
                        'boarded': order.go_boarded
                    }
                    ret_data['unboarded'].append(unboarded_order_dict)
                total_order_dict = {
                    'passenger_name': order.user.name,
                    'gender': order.user.gender,
                    'phone': order.user.phone,
                    'boarding_loc': order.bus_loc.loc.busboardloc,
                    'boarded': order.go_boarded
                }
                ret_data['total'].append(total_order_dict)
            return Response({'ret': 0, 'data': ret_data})

        except Exception as e:
            print(repr(e))
            return Response({'ret': 422801, 'errmsg': '其他错误'})



# 获取返程上车人数
class get_return_bus_boarding_passenger_num(APIView):
    authentication_classes = [MyJWTAuthentication, ]

    def post(self,request,*args,**kwargs):
        userid = request.user['userid']

        info = json.loads(request.body)

        try:
            leader_itinerary_id = info['leader_itinerary_id']

            try:
                leader_itinerary = LeaderItinerary.objects.get(Q(id=leader_itinerary_id))
            except:
                return Response({'ret': 422902, 'errmsg': '没有找到对应的领队行程'})

            # 所有返程未上车的订单
            orders_unboarded = TicketOrder.objects.filter(Q(bus_id=leader_itinerary.bus.id) & Q(return_boarded=False) & Q(status=3))

            ret_data = {
                'unboarded_passenger_num': orders_unboarded.count(),
                'total_passenger_num': leader_itinerary.bus.carry_peoplenum,
                'boarded_passenger_num': leader_itinerary.bus.carry_peoplenum - orders_unboarded.count(),
            }

            return Response({'ret': 0, 'data': ret_data})

        except Exception as e:
            print(repr(e))
            return Response({'ret': 422901, 'errmsg': '其他错误'})


# 获取返程上车名单
class get_return_bus_boarding_passenger_list(APIView):
    authentication_classes = [MyJWTAuthentication, ]

    def post(self,request,*args,**kwargs):
        userid = request.user['userid']

        info = json.loads(request.body)

        try:
            leader_itinerary_id = info['leader_itinerary_id']

            try:
                leader_itinerary = LeaderItinerary.objects.get(Q(id=leader_itinerary_id))
            except:
                return Response({'ret': 423002, 'errmsg': '没有找到对应的领队行程'})

            orders = TicketOrder.objects.filter(Q(bus_id=leader_itinerary.bus.id) & Q(status=3)).order_by('return_boarded', 'bus_loc_id')

            ret_data = {
                'unboarded_passenger_num': 0,
                'total_passenger_num': leader_itinerary.bus.carry_peoplenum,
                'unboarded': [],
                'total': [],
            }
            for order in orders:
                if order.return_boarded == False:    # 未上车
                    ret_data['unboarded_passenger_num'] += 1
                    unboarded_order_dict = {
                        'passenger_name': order.user.name,
                        'gender': order.user.gender,
                        'phone': order.user.phone,
                        'boarding_loc': order.bus_loc.loc.busboardloc,
                        'boarded': order.go_boarded
                    }
                    ret_data['unboarded'].append(unboarded_order_dict)
                total_order_dict = {
                    'passenger_name': order.user.name,
                    'gender': order.user.gender,
                    'phone': order.user.phone,
                    'boarding_loc': order.bus_loc.loc.busboardloc,
                    'boarded': order.go_boarded
                }
                ret_data['total'].append(total_order_dict)
            return Response({'ret': 0, 'data': ret_data})

        except Exception as e:
            print(repr(e))
            return Response({'ret': 423001, 'errmsg': '其他错误'})



# 获取返程上车总名单
class get_go_bus_boarding_total_passenger_list(APIView):
    authentication_classes = [MyJWTAuthentication, ]

    def post(self,request,*args,**kwargs):
        userid = request.user['userid']

        info = json.loads(request.body)

        try:
            leader_itinerary_id = info['leader_itinerary_id']

            try:
                leader_itinerary = LeaderItinerary.objects.get(Q(id=leader_itinerary_id))
            except:
                return Response({'ret': 423102, 'errmsg': '没有找到对应的领队行程'})

            orders = TicketOrder.objects.filter(Q(bus_id=leader_itinerary.bus.id) & Q(status=3)).order_by('go_boarded', 'bus_loc_id')

            ret_data = {
                'unboarded_passenger_num': 0,
                'total_passenger_num': leader_itinerary.bus.carry_peoplenum,
                'unboarded': [],
                'total': [],
            }
            for order in orders:
                if order.go_boarded == False:    # 未去程上车
                    ret_data['unboarded_passenger_num'] += 1
                    unboarded_order_dict = {
                        'passenger_name': order.user.name,
                        'gender': order.user.gender,
                        'phone': order.user.phone,
                        'boarding_loc': order.bus_loc.loc.busboardloc,
                        'boarded': order.go_boarded
                    }
                    ret_data['unboarded'].append(unboarded_order_dict)
                total_order_dict = {
                    'passenger_name': order.user.name,
                    'gender': order.user.gender,
                    'phone': order.user.phone,
                    'boarding_loc': order.bus_loc.loc.busboardloc,
                    'boarded': order.go_boarded
                }
                ret_data['total'].append(total_order_dict)
            return Response({'ret': 0, 'data': ret_data})

        except Exception as e:
            print(repr(e))
            return Response({'ret': 423101, 'errmsg': '其他错误'})


# ========================================= Depreceted ===========================================

# 获取可以替换的上车点
# class get_available_boardingloc_of_certain_itinerary(APIView):
#     authentication_classes = [MyJWTAuthentication, ]

#     def post(self,request,*args,**kwargs):
#         info = json.loads(request.body)
#         try:
#             userid = request.user['userid']
#             order_id = info['id']

#             ret_dic = {}  # key-上车点，value-大巴车
#             # 先查上车点
#             activity_id = TicketOrder.objects.get(Q(id=order_id) & ~Q(status=6)).ticket.activity.id
#             boardinglocs = Boardingloc.objects.filter(activity_id=activity_id)
#             for bl in boardinglocs:  # 对于所有的目前可用的上车点
#                 # print(bl)
#                 related_bus_ids = Bus_boarding_time.objects.filter(loc_id=bl.id).values_list('bus_id', flat=True).distinct()
#                 # print(related_bus_ids)
#                 related_bus = Bus.objects.filter(id__in=related_bus_ids)
#                 availible_bus = []
#                 for bus in related_bus:
#                     if (bus.carry_peoplenum is not None) and (bus.max_people is not None) and \
#                         (bus.max_people - bus.carry_peoplenum) > 0:
#                         bus_serializer = BusSerializer(instance=bus, many=False)

#                         # todo-f 加入上车点id，上车点上车时间
#                         this_bus_data = dict(bus_serializer.data)
#                         this_bus_data['boardingtime'] = Bus_boarding_time.objects.filter(loc_id=bl.id, bus_id=bus.id)[0].time.strftime('%H:%M')
#                         this_bus_data['boardingloc_id'] = Bus_boarding_time.objects.filter(loc_id=bl.id, bus_id=bus.id)[0].loc.id
#                         availible_bus.append(this_bus_data)
#                 # print(availible_bus)

#                 if len(availible_bus) > 0:
#                     ret_dic[str(bl.loc.busboardloc)] = availible_bus

#             return Response({'ret': 0, 'data': ret_dic})
#         except Exception as e:
#             print(repr(e))
#             return Response({'ret': 420401, 'data': None})
        

# 选择替换的上车点
# class select_new_boardingloc(APIView):
#     authentication_classes = [MyJWTAuthentication, ]

#     def post(self,request,*args,**kwargs):
#         userid = request.user['userid']

#         info = json.loads(request.body)

#         try:
#             order_id = info['order_id']
#             boardingloc_id = info['boardingloc_id']
#             bus_id = info['bus_id']

#             order = TicketOrder.objects.get(Q(id=order_id) & ~Q(status=6))
#             # 对于已发起退款或已退款的，修改上车点无效
#             if order.status == 0:
#                 return Response({'ret': 420606, 'errmsg': '该订单已取消'})
#             elif order.status == 3:
#                 return Response({'ret': 420607, 'errmsg': '该订单已锁定'})
#             elif order.status == 4:
#                 return Response({'ret': 420604, 'errmsg': '该订单正在退款中'})
#             elif order.status == 5:
#                 return Response({'ret': 420605, 'errmsg': '该订单已退款'})

#             # 判断可报名状态
#             if order.ticket.activity.status == 1:  # 截止报名
#                 if order.bus_loc is not None:  # 原上车点可用
#                     return Response({'ret': 420602, 'errmsg': '活动截止报名且原上车点可用，不允许更换'})
#             elif order.ticket.activity.status == 2:  # 锁票
#                 return Response({'ret': 420603, 'errmsg': '活动已经进入锁票阶段，无法操作'})


#             # 判断所选大巴是否有空位
#             with transaction.atomic():
#                 select_bus = Bus.objects.select_for_update().filter(id=bus_id)
#                 # 检查剩余名额
#                 if select_bus[0].max_people - select_bus[0].carry_peoplenum <= 0:
#                     return Response({'ret': 420609, 'errmsg': '该车已经没有空位'})
#                 else:
#                     # 设置bus
#                     order.bus = select_bus[0]  # 订单绑定
#                     select_bus[0].carry_peoplenum += 1  # 车上人数+1
#                     select_bus[0].save()
#                     # 设置boardingloc
#                     select_boardingloc = Boardingloc.objects.select_for_update().filter(id=boardingloc_id)
#                     order.bus_loc = select_boardingloc[0]  # 订单绑定
#                     select_boardingloc.update(choice_peoplenum=F('choice_peoplenum')+1)  # 上车点人数+
#                     # 设置上车时间，该车该点上车人数
#                     select_bus_loc_time = Bus_boarding_time.objects.select_for_update().filter(bus_id=select_bus[0].id, loc_id=boardingloc_id)
#                     order.bus_time = select_bus_loc_time[0]  # 订单绑定
#                     select_bus_loc_time.update(boarding_peoplenum=F('boarding_peoplenum')+1)  # 该车经过该点上车人数+1
                    
#                     # 将订单锁定
#                     order.status = 3
#                     order.save()

#             return Response({'ret': 0, 'errmsg': None})

#         except Exception as e:
#             print(repr(e))
#             return Response({'ret': 420601, 'errmsg': '其他错误'})
