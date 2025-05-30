import json
import pytz
import requests
import datetime
from django.conf import settings
from django.http import JsonResponse
from django.forms.models import model_to_dict
from rest_framework.response import Response
from rest_framework.views import APIView
from user.models import User, Area, School, Accesstoken
from user.models import UserSerializer, SchoolSerializer
from .auth import MyJWTAuthentication, create_token

class signup(APIView):
    url_mod = 'https://api.weixin.qq.com/sns/jscode2session?appid={}&secret={}&js_code={}&grant_type=authorization_code'

    def post(self,request,*args,**kwargs):
        info = json.loads(request.body)
        code = info['code']

        code_url = self.url_mod.format(settings.APPID, settings.APPSECRET, code)  # 构造url
        response = requests.get(code_url)  # 向腾讯服务器发送请求
        jsrespon = response.json()

        try:
            sessionkey = jsrespon['session_key']
            oid = jsrespon['openid']  # 获得的openid
        except Exception as e:
            print(repr(e))
            return Response({'ret': -1, 'errmsg': 'wx接口调用失败', 'session_key': None, 'openid': None, 'openid': None})

        user_found = User.objects.filter(openid=oid)  # users表中是否已有该用户
        if user_found.count() == 0:  # 没有该用户，尝试创建一条数据，并返回id
            try:
                name = info['name']
                school_id = info['school_id']
                age = info['age']
                phone = info['phone']
                newuser = User.objects.create(openid=oid, name=name, school_id=school_id, age=age,
                                            phone=phone)
                
                token = create_token(newuser)
                return Response({'ret': 0, 'errmsg': None, 'session_key': sessionkey, 'openid': oid, 'token': str(token)})
            except Exception as e:
                print(repr(e))
                return Response({'ret': -1, 'errmsg': '注册失败, 请检查提交的数据是否标准', 'session_key': None, 'openid': None, 'token': None})
        else:  # 已有该用户
            # 登录模式
            token = create_token(user_found[0])
            # print(token)
            return Response({'ret': 1, 'errmsg': '用户已存在, 成功登录', 'session_key': sessionkey, 'openid': oid, 'token': str(token)})


class login(APIView):
    url_mod = 'https://api.weixin.qq.com/sns/jscode2session?appid={}&secret={}&js_code={}&grant_type=authorization_code'

    def post(self,request,*args,**kwargs):
        info = json.loads(request.body)
        code = info['code']

        code_url = self.url_mod.format(settings.APPID, settings.APPSECRET, code)  # 构造url
        response = requests.get(code_url)  # 向腾讯服务器发送请求
        jsrespon = response.json()

        try:
            sessionkey = jsrespon['session_key']
            oid = jsrespon['openid']  # 获得的openid
        except Exception as e:
            print(repr(e))
            return Response({'ret': -1, 'errmsg': 'wx接口调用失败', 'session_key': None, 'openid': None, 'token': None})

        user_found = User.objects.filter(openid=oid)  # users表中是否已有该用户
        if user_found.count() == 0:
            return Response({'ret': 1, 'errmsg': '登录失败(未注册)', 'session_key': None, 'openid': None, 'token': None})
        else:
            token = create_token(user_found[0])
            return Response({'ret': 0, 'errmsg': None, 'session_key': sessionkey, 'openid': oid, 'token': str(token)})


# class login(APIView):
#     url_mod = 'https://api.weixin.qq.com/sns/jscode2session?appid={}&secret={}&js_code={}&grant_type=authorization_code'

#     def post(self,request,*args,**kwargs):
#         info = json.loads(request.body)
#         code = info['code']

#         code_url = self.url_mod.format(settings.APPID, settings.APPSECRET, code)  # 构造url
#         response = requests.get(code_url)  # 向腾讯服务器发送请求
#         jsrespon = response.json()

#         try:
#             sessionkey = jsrespon['session_key']
#             oid = jsrespon['openid']  # 获得的openid
#         except Exception as e:
#             print(repr(e))
#             return Response({'ret': -1, 'errmsg': 'wx接口调用失败', 'session_key': None, 'openid': None})

#         user_found = User.objects.filter(openid=oid)  # users表中是否已有该用户
#         if user_found.count() == 0:  # 没有该用户，尝试创建一条数据，并返回id
#             # 注册模式
#             try:
#                 name = info['name']
#                 school_id = info['school_id']
#                 age = info['age']
#                 gender = info['gender']
#                 phone = info['phone']
#                 newuser = User.objects.create(openid=oid, name=name, school_id=school_id, age=age,
#                                             gender=gender, phone=phone)
                
#                 token = create_token(newuser)
#                 return Response({'ret': 0, 'errmsg': None, 'session_key': sessionkey, 'token': str(token)})
#             except Exception as e:
#                 print(repr(e))
#                 return Response({'ret': -1, 'errmsg': '登录失败(未注册or注册失败)', 'session_key': None, 'token': None})
#         else:  # 已有该用户，直接返回id
#             # 登录模式
#             token = create_token(user_found[0])
#             return Response({'ret': 0, 'errmsg': None, 'session_key': sessionkey, 'token': str(token)})


class user_info(APIView):
    authentication_classes = [MyJWTAuthentication, ]
    def get(self,request,*args,**kwargs):
        userid = request.user['userid']
        # print(userid)
        try:
            user = User.objects.get(id=userid)
        except Exception as e:
            print(repr(e))
            return Response({'ret': -1, 'userinfo': None})
        serializer = UserSerializer(instance=user, many=False)
        return Response({'ret': 0, 'userinfo': serializer.data})


class area(APIView):
    def get(self,request,*args,**kwargs):
        all_areas = Area.objects.all().values()
        return Response({'ret': 0, 'area': list(all_areas)})


class school(APIView):
    def get(self,request,*args,**kwargs):
        all_schools = School.objects.all()
        serializer = SchoolSerializer(instance=all_schools, many=True)
        return Response({'ret': 0, 'school': list(serializer.data)})
        # return Response({'ret': 0, 'areas': list(all_schools)})


# https://developers.weixin.qq.com/miniprogram/dev/platform-capabilities/industry/student.html
class check_student(APIView):
    authentication_classes = [MyJWTAuthentication, ]

    checkstudent_url_mod = 'https://api.weixin.qq.com/intp/quickcheckstudentidentity?access_token={}'
    getaccesstoken_url = 'https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={}&secret={}'.format(settings.APPID, settings.APPSECRET)
    def post(self,request,*args,**kwargs):
        # 先获得access token
        try:
            at_obj = Accesstoken.objects.get(id=1)
        except:
            # 还没有access token
            response = requests.get(self.getaccesstoken_url)  # 向腾讯服务器发送请求
            jsrespon = response.json()
            newtoken = jsrespon['access_token']
            exp_in = jsrespon['expires_in']
            at_obj = Accesstoken.objects.create(access_token=newtoken, expire_time=datetime.datetime.now()+datetime.timedelta(seconds=exp_in))
            # return Response({'ret':0, 'acesstoken':model_to_dict(newat)})
                
        if at_obj.expire_time.replace(tzinfo=None) <= datetime.datetime.utcnow():
            # access token 过期了
            response = requests.get(self.getaccesstoken_url)  # 向腾讯服务器发送请求
            jsrespon = response.json()
            newtoken = jsrespon['access_token']
            exp_in = jsrespon['expires_in']
            print('token过期', newtoken)
            at_obj.access_token = newtoken
            at_obj.expire_time = datetime.datetime.now()+datetime.timedelta(seconds=exp_in)
            at_obj.save()
            # return Response({'ret':0, 'acesstoken':model_to_dict(at_obj)})
        
        # 进行学生认证
        info = json.loads(request.body)
        openid = request.user['openid']
        print(openid)
        code = info['wx_studentcheck_code']
        wx_access_token = at_obj.access_token
        post_data = {
            'openid': openid,
            'wx_studentcheck_code': code
        }
        stu_response = requests.post(self.checkstudent_url_mod.format(wx_access_token), data=post_data)
        jsstu_response = stu_response.json()

        errcode = jsstu_response['errcode']
        if errcode != 0:
            # 接口调用失败
            errmsg = jsstu_response['errmsg']
            return Response({'ret': -1, 'errmsg': errmsg, 'bind_status': None, 'is_student': None})

        try:
            bind_status = jsstu_response['bind_status']
            is_student = jsstu_response['is_student']
        except Exception as e:
            print(repr(e))
            return Response({'ret': -1, 'errmsg': 'wx响应中无学生认证信息', 'bind_status': None, 'is_student': None})
        
        # 更新该用户学生信息
        userid = request.user['userid']
        try:
            user = User.objects.get(id=userid)
        except Exception as e:
            print(repr(e))
            return Response({'ret': -1, 'errmsg': '查找该用户失败', 'bind_status': bind_status, 'is_student': is_student})
        
        user.is_student = is_student
        user.save()
        return Response({'ret': 0, 'errmsg': None, 'bind_status': bind_status, 'is_student': is_student})   


SNOWBOARD_SIZE_1 = [[146, 148, 151, 154, 155, 158, 159],
                    [147, 150, 152, 155, 156, 159, 160],
                    [149, 151, 154, 156, 159, 160, 163],
                    [150, 152, 155, 158, 159, 162, 163],
                    [151, 154, 156, 159, 160, 163, 165]]

def cal_snowboardsize(skibo, style, height, weight):
    if skibo==0:
        # danban
        w = 0
        h = 0
        if weight<=49:
            w = 0
        elif weight>49 and weight<=59:
            w = 1
        elif weight>59 and weight<=69:
            w = 2
        elif weight>69 and weight<=79:
            w = 3
        elif weight>79 and weight<=89:
            w = 4
        elif weight>89 and weight<=95:
            w = 5
        elif weight>95:
            w = 6
        
        if height<=154:
            h = 0
        elif height>154 and height<=169:
            h = 1
        elif height>169 and height<=183:
            h = 2
        elif height>183 and height<=196:
            h = 3
        elif height>196:
            h = 4
        
        raw_size = SNOWBOARD_SIZE_1[h][w]

        if style==0:
            # jichu
            return raw_size
        elif style==1:
            # kehua
            return raw_size+5
        elif style==2:
            # pinghua
            return raw_size-3
        elif style==3:
            # gongyuan
            return raw_size-2
        else:
            return raw_size

    else:
        # shuangban

        raw_size = 114
        if (height<=137 ) or (weight<=30):
            raw_size = 114
        elif (height>182 ) or (weight>77):
            raw_size = 165
        else:
            byh = height-17
            byw = weight+88
            raw_size = int((byh+byw)/2)
        
        return raw_size


class update_user_ski_info(APIView):
    authentication_classes = [MyJWTAuthentication, ]
    def post(self,request,*args,**kwargs):
        userid = request.user['userid']
        info = json.loads(request.body)
        
        try:
            gender = info['gender']
            ski_board = info['ski_board']
            ski_level = info['ski_level']
            ski_style = info['ski_style']
            height = info['height']
            weight = info['weight']
            skiboots_size = info['skiboots_size']
            # snowboard_size = info['snowboard_size']
            snowboard_size = cal_snowboardsize(skibo=ski_board, style=ski_style, height=height, weight=weight)

            if ski_board == 0:
                # 单板
                user = User.objects.filter(id=userid).update(gender=gender, ski_board=ski_board, ski_level=ski_level,
                                                          ski_style=ski_style, height=height, weight=weight,
                                                          skiboots_size_1=skiboots_size, snowboard_size_1=snowboard_size)
                return Response({'ret': 0, 'errmsg': None})   
            else:
                # 双板
                try:
                    # skipole_size = info['skipole_size']
                    user = User.objects.filter(id=userid).update(gender=gender, ski_board=ski_board, ski_level=ski_level,
                                                            ski_style=ski_style, height=height, weight=weight,
                                                            skiboots_size_2=skiboots_size, snowboard_size_2=snowboard_size,
                                                            )
                    return Response({'ret': 0, 'errmsg': None})   
                except Exception as e:
                    print(repr(e))
                    return Response({'ret': -1, 'errmsg': '更新失败, 请检查提交的数据是否标准'})   

        except Exception as e:
            print(repr(e))
            return Response({'ret': -1, 'errmsg': '更新失败, 请检查提交的数据是否标准'})   


class get_skiboard_size(APIView):
    authentication_classes = [MyJWTAuthentication, ]
    def get(self,request,*args,**kwargs):
        userid = request.user['userid']
        try:
            user = User.objects.get(id=userid)
            if user.ski_board==0:
                # danban
                return Response({'ret': 0, 'snowboard_size': user.snowboard_size_1})
            else:
                # shuangban
                return Response({'ret': 0, 'snowboard_size': user.snowboard_size_2})
        except Exception as e:
            print(repr(e))
            return Response({'ret': -1, 'snowboard_size': None})


class set_skiboard_size(APIView):
    authentication_classes = [MyJWTAuthentication, ]
    def post(self,request,*args,**kwargs):
        userid = request.user['userid']
        info = json.loads(request.body)
        try:
            snowb_size = info['snowboard_size']
            user = User.objects.get(id=userid)
            if user.ski_board==0:
                # danban
                user.snowboard_size_1 = snowb_size
                user.save()
                return Response({'ret': 0})
            else:
                # shuangban
                user.snowboard_size_2 = snowb_size
                user.save()
                return Response({'ret': 0})
        except Exception as e:
            print(repr(e))
            return Response({'ret': -1})


class update_user_basic_info(APIView):
    authentication_classes = [MyJWTAuthentication, ]
    def post(self,request,*args,**kwargs):
        userid = request.user['userid']
        info = json.loads(request.body)
        try:
            name = info['name']
            school = info['school']
            age = info['age']
            phone = info['phone']
            user = User.objects.filter(id=userid).update(name=name, school_id=school, age=age, phone=phone)
            return Response({'ret': 0, 'errmsg': None})   
        except Exception as e:
            print(repr(e))
            return Response({'ret': -1, 'errmsg': '更新失败, 请检查提交的数据是否标准'})   

