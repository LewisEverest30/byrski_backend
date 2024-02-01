import requests
import datetime
from .models import Accesstoken
from django.conf import settings

getaccesstoken_url = 'https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={}&secret={}'.format(settings.APPID, settings.APPSECRET)

def update_access_token():
    try:
        response = requests.get(getaccesstoken_url)  # 向腾讯服务器发送请求
        jsrespon = response.json()
    except Exception as e:
        print(repr(e))
        return

    try:
        newtoken = jsrespon['access_token']
        exp_in = jsrespon['expires_in']
    except Exception as e:
        errcode = jsrespon['errcode']
        errmsg = jsrespon['errmsg']
        print(str(datetime.datetime.now()), repr(e), str(errcode), errmsg)
        return

    try:
        at_obj = Accesstoken.objects.get(id=1)
    except Exception as e:
        print(str(datetime.datetime.now()), repr(e))
        return

    at_obj.access_token = newtoken
    at_obj.expire_time = datetime.datetime.now()+datetime.timedelta(seconds=exp_in)
    at_obj.save()

