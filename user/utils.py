import requests
import datetime
from django.utils import timezone
from django.conf import settings

from .models import Accesstoken


GET_ACCESSTOKEN_URL = 'https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={}&secret={}'.format(settings.APPID, settings.APPSECRET)

def get_access_token():
    try:
        at_obj = Accesstoken.objects.get(id=1)
    except:
        # 还没有access token
        response = requests.get(GET_ACCESSTOKEN_URL)  # 向腾讯服务器发送请求
        jsrespon = response.json()
        newtoken = jsrespon['access_token']
        exp_in = jsrespon['expires_in']
        at_obj = Accesstoken.objects.create(access_token=newtoken, expire_time=datetime.datetime.now()+datetime.timedelta(seconds=exp_in))
        return at_obj.access_token
            
    if at_obj.expire_time <= timezone.now():
        # access token 过期了
        response = requests.get(GET_ACCESSTOKEN_URL)  # 向腾讯服务器发送请求
        jsrespon = response.json()
        newtoken = jsrespon['access_token']
        exp_in = jsrespon['expires_in']
        print('token过期', newtoken)
        at_obj.access_token = newtoken
        at_obj.expire_time = datetime.datetime.now()+datetime.timedelta(seconds=exp_in)
        at_obj.save()
    return at_obj.access_token





# ========================== 雪具相关 ==========================

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

