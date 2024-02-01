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

# AccessToken = ''

class login(APIView):
    login_url_mod = 'https://api.weixin.qq.com/sns/jscode2session?appid={}&secret={}&js_code={}&grant_type=authorization_code'

    def post(self,request,*args,**kwargs):
        info = json.loads(request.body)
        code = info['code']

        code_url = self.login_url_mod.format(settings.APPID, settings.APPSECRET, code)  # 构造url
        response = requests.get(code_url)  # 向腾讯服务器发送请求
        jsrespon = response.json()

        try:
            sessionkey = jsrespon['session_key']
            oid = jsrespon['openid']  # 获得的openid
        except Exception as e:
            print(repr(e))
            return Response({'ret': -1, 'session_key': None, 'openid': None})

        user_found = User.objects.filter(openid=oid)  # users表中是否已有该用户
        if user_found.count() == 0:  # 没有该用户，创建一条数据，并返回id
            try:
                name = info['name']
                school_id = info['school_id']
                age = info['age']
                gender = info['gender']
                phone = info['phone']
                wxaccount = info['wxaccount']
                newuser = User.objects.create(openid=oid, name=name, school_id=school_id, age=age,
                                            gender=gender, phone=phone, wxaccount=wxaccount)
                
                token = create_token(newuser)
                print(token)
                
                return Response({'ret': 0, 'session_key': sessionkey, 'token': token})
            except Exception as e:
                print(repr(e))
                return Response({'ret': -1, 'session_key': None, 'token': None})
        else:  # 已有该用户，直接返回id
            userid = user_found[0].id
            
            token = create_token(user_found[0])
            print(token)
            
            return Response({'ret': 0, 'session_key': sessionkey, 'token': str(token)})


class user_info(APIView):
    authentication_classes = [MyJWTAuthentication, ]
    def get(self,request,*args,**kwargs):
        # info = json.loads(request.body)
        # userid= info['userid']
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
        return Response({'ret': 0, 'areas': list(all_areas)})


class school(APIView):
    def get(self,request,*args,**kwargs):
        all_schools = School.objects.all()
        serializer = SchoolSerializer(instance=all_schools, many=True)
        return Response({'ret': 0, 'areas': list(serializer.data)})
        # return Response({'ret': 0, 'areas': list(all_schools)})


class check_student(APIView):
    authentication_classes = [MyJWTAuthentication, ]

    checkstudent_url_mod = 'https://api.weixin.qq.com/intp/quickcheckstudentidentity?access_token={}'
    getaccesstoken_url = 'https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={}&secret={}'.format(settings.APPID, settings.APPSECRET)
    def post(self,request,*args,**kwargs):
        try:
            at_obj = Accesstoken.objects.get(id=1)
        except:
            # 还没有access token
            response = requests.get(self.getaccesstoken_url)  # 向腾讯服务器发送请求
            jsrespon = response.json()
            newtoken = jsrespon['access_token']
            exp_in = jsrespon['expires_in']
            newat = Accesstoken.objects.create(access_token=newtoken, expire_time=datetime.datetime.now()+datetime.timedelta(seconds=exp_in))
            return Response({'ret':0, 'acesstoken':model_to_dict(newat)})
                
        if at_obj.expire_time.replace(tzinfo=None) <= datetime.datetime.utcnow():
            # access token 过期了
            response = requests.get(self.getaccesstoken_url)  # 向腾讯服务器发送请求
            jsrespon = response.json()
            newtoken = jsrespon['access_token']
            exp_in = jsrespon['expires_in']
            
            at_obj.access_token = newtoken
            at_obj.expire_time = datetime.datetime.now()+datetime.timedelta(seconds=exp_in)
            at_obj.save()
            return Response({'ret':0, 'acesstoken':model_to_dict(at_obj)})
        
        else:
            print(str(model_to_dict(at_obj)))
            return Response({'ret':0})
        
        # stu_response = requests.get(self.checkstudent_url_mod.)  # 向腾讯服务器发送请求




