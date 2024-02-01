import requests
import datetime
from .models import Accesstoken

APPID ='wx2b4fa660ea71d1a5'
APPSECRET = 'c9811b45b61ecab06bf595101741eb0c'

getaccesstoken_url = 'https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={}&secret={}'.format(APPID, APPSECRET)

def update_access_token():
    try:
        at_obj = Accesstoken.objects.get(id=1)
    except Exception as e:
        print(repr(e))
        return

    response = requests.get(getaccesstoken_url)  # 向腾讯服务器发送请求
    jsrespon = response.json()
    newtoken = jsrespon['access_token']
    exp_in = jsrespon['expires_in']
    
    print('###expire',newtoken)

    at_obj.access_token = newtoken
    at_obj.expire_time = datetime.datetime.now()+datetime.timedelta(seconds=exp_in)
    at_obj.save()

