import json
import requests
import datetime
from django.conf import settings
from rest_framework.response import Response
from rest_framework.views import APIView

from user.models import User, Accesstoken
from user.models import *
from .auth import MyJWTAuthentication, create_token
# from .utils import cal_snowboardsize


TOKEN_EXPIRE_DAYS = 365
class login(APIView):
    login_url_mod = 'https://api.weixin.qq.com/sns/jscode2session?appid={}&secret={}&js_code={}&grant_type=authorization_code'

    def post(self,request,*args,**kwargs):
        info = json.loads(request.body)
        login_code = info['code']
        login_code_url = self.login_url_mod.format(settings.APPID, settings.APPSECRET, login_code)  # 构造url
        login_response = requests.get(login_code_url)  # 向腾讯服务器发送登录请求
        login_json = login_response.json()

        try:
            sessionkey = login_json['session_key']
            oid = login_json['openid']  # 获得的openid
        except Exception as e:
            print(repr(e))
            return Response({'ret': 500001, 'errmsg': '微信登录接口调用失败', 'openid': None, 'token': None, 
                             'is_student': None, 'identity': None,
                             'name': None, 'token_expire': None})

        user_found = User.objects.filter(openid=oid)  # users表中是否已有该用户
        if user_found.count() == 0:  # 没有该用户，尝试创建一条数据，并返回id
            newuser = User.objects.create(openid=oid)
            token_expire_time = timezone.now()+datetime.timedelta(days=TOKEN_EXPIRE_DAYS)
            token = create_token(newuser, expdays=TOKEN_EXPIRE_DAYS)
            return Response({'ret': 0, 'errmsg': None, 'openid': oid, 'token': str(token), 
                             'is_student': newuser.is_student, 'identity': newuser.identity,
                             'name': newuser.name, 'token_expire': token_expire_time})
        else:  # 已有该用户
            # 登录模式
            token_expire_time = timezone.now()+datetime.timedelta(days=TOKEN_EXPIRE_DAYS)
            token = create_token(user_found[0], expdays=TOKEN_EXPIRE_DAYS)
            # print(token)
            return Response({'ret': 0, 'errmsg': None, 'openid': oid, 'token': str(token), 
                             'is_student': user_found[0].is_student, 'identity': user_found[0].identity,
                             'name': user_found[0].name, 'token_expire': token_expire_time})


class check_student(APIView):
# https://developers.weixin.qq.com/miniprogram/dev/platform-capabilities/industry/student.html
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
                
        if at_obj.expire_time <= timezone.now():
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
        code = info['code']
        wx_access_token = at_obj.access_token
        post_data = {
            'openid': openid,
            'wx_studentcheck_code': code
        }
        stu_response = requests.post(self.checkstudent_url_mod.format(wx_access_token), json=post_data)
        jsstu_response = stu_response.json()

        errcode = jsstu_response['errcode']
        if errcode != 0:
            # 接口调用失败
            errmsg = jsstu_response['errmsg']
            wxerrcode = jsstu_response['errcode']
            return Response({'ret': 500101, 'errmsg': errmsg, 'wxerrcode':wxerrcode, 'bind_status': None, 'is_student': None})

        try:
            bind_status = jsstu_response['bind_status']
            is_student = jsstu_response['is_student']
            wxerrcode = jsstu_response['errcode']
        except Exception as e:
            print(repr(e))
            return Response({'ret': 500102, 'errmsg': 'wx响应中无学生认证信息', 'wxerrcode':wxerrcode, 'bind_status': None, 'is_student': None})
        
        # 更新该用户学生信息
        userid = request.user['userid']
        try:
            user = User.objects.get(id=userid)
        except Exception as e:
            print(repr(e))
            return Response({'ret': 400101, 'errmsg': '查找该用户失败', 'wxerrcode':None, 'bind_status': bind_status, 'is_student': is_student})
        
        user.is_student = is_student
        user.save()
        return Response({'ret': 0, 'errmsg': None, 'wxerrcode':None, 'bind_status': bind_status, 'is_student': is_student})   


class get_user_basic_info(APIView):
    authentication_classes = [MyJWTAuthentication, ]
    def get(self,request,*args,**kwargs):
        userid = request.user['userid']

        try:
            user = User.objects.get(id=userid)
            serializer = UserSerializerBasic(instance=user, many=False)
            return Response({'ret': 0, 'data': serializer.data})
        except Exception as e:
            print(repr(e))
            return Response({'ret': 400201, 'data': None})


class update_user_basic_info(APIView):
    authentication_classes = [MyJWTAuthentication, ]
    def post(self,request,*args,**kwargs):
        userid = request.user['userid']
        info = json.loads(request.body)
        try:
            name = info['name']
            gender = info['gender']   # 0男 1女
            phone = info['phone']
            school_id = info['school_id']
            height = info['height']
            weight = info['weight']
            skiboots_size = info['skiboots_size']
            ski_board = info['ski_board']   # 0单 1双
            ski_level = info['ski_level']   # 0小白 1新手 2走刃 3大佬
            ski_favor = info['ski_favor']   # 0基础 1刻滑 2平花 3公园 4野雪


            user = User.objects.filter(id=userid).update(name=name, gender=gender, phone=phone, school_id=school_id,
                                                         height=height, weight=weight,
                                                         skiboots_size=skiboots_size, ski_board=ski_board,
                                                         ski_level=ski_level, ski_favor=ski_favor)
            return Response({'ret': 0, 'errmsg': None})   
        except Exception as e:
            print(repr(e))
            return Response({'ret': 400301, 'errmsg': '更新失败, 请检查提交的数据是否标准'})   


# --------------------------------下面的初版先不用-------------------------------------------

'''
class get_user_ski_info(APIView):
    authentication_classes = [MyJWTAuthentication, ]
    def get(self,request,*args,**kwargs):
        userid = request.user['userid']
        # print(userid)
        try:
            user = User.objects.get(id=userid)
        except Exception as e:
            print(repr(e))
            return Response({'ret': 400401, 'data': None})
        serializer = UserSerializerSki(instance=user, many=False)
        return Response({'ret': 0, 'data': serializer.data})


class update_user_ski_info(APIView):
    authentication_classes = [MyJWTAuthentication, ]
    def post(self,request,*args,**kwargs):
        userid = request.user['userid']
        info = json.loads(request.body)
        try:
            height = info['height']
            weight = info['weight']
            skiboots_size = info['skiboots_size']
            skiboots_size = info['skiboots_size']
            snowboard_size_1 = info['snowboard_size_1']
            snowboard_size_2 = info['snowboard_size_2']
            snowboard_hardness = info['snowboard_hardness']
            skipole_size = info['skipole_size'] 

            User.objects.filter(id=userid).update(height=height, weight=weight,
                                                         skiboots_size=skiboots_size, skiboots_size=skiboots_size,
                                                         snowboard_size_1=snowboard_size_1,
                                                         snowboard_size_2=snowboard_size_2,
                                                         snowboard_hardness=snowboard_hardness,
                                                         skipole_size=skipole_size)
            return Response({'ret': 0})
        except Exception as e:
            print(repr(e))
            return Response({'ret': 400501})

'''


# 雪板长度数据
'''
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


'''

# deprecated ⬇️
'''class login(APIView):
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
            return Response({'ret': -1, 'errmsg': 'wx接口调用失败', 'session_key': None, 'openid': None})

        user_found = User.objects.filter(openid=oid)  # users表中是否已有该用户
        if user_found.count() == 0:  # 没有该用户，尝试创建一条数据，并返回id
            # 注册模式
            try:
                name = info['name']
                school_id = info['school_id']
                age = info['age']
                gender = info['gender']
                phone = info['phone']
                newuser = User.objects.create(openid=oid, name=name, school_id=school_id, age=age,
                                            gender=gender, phone=phone)
                
                token = create_token(newuser)
                return Response({'ret': 0, 'errmsg': None, 'session_key': sessionkey, 'token': str(token)})
            except Exception as e:
                print(repr(e))
                return Response({'ret': -1, 'errmsg': '登录失败(未注册or注册失败)', 'session_key': None, 'token': None})
        else:  # 已有该用户，直接返回id
            # 登录模式
            token = create_token(user_found[0])
            return Response({'ret': 0, 'errmsg': None, 'session_key': sessionkey, 'token': str(token)})
'''

# 注册+登录的模式 ⬇️
'''class signup(APIView):
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
'''
