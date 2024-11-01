from django.test import TestCase

# Create your tests here.
# import datetime

# print('ei1eija',str(datetime.datetime.now()))

import datetime
import jwt
SECRET_KEY = 'd916dac1-e79a-11eb-a95c-14f6d8e4b681'

def create_token(expdays=7):
    headers = {
        'typ': 'jwt',
        'alg': 'HS256'
    }
    payload = {
        'userid': 2,
        'openid': 'oM3pE5EaxWTFpAkzeIPzMzHbjgRI',
        'exp': datetime.datetime.utcnow() + datetime.timedelta(days=expdays)
    }
    # print(payload)
    token = jwt.encode(payload=payload, key=SECRET_KEY, headers=headers, algorithm='HS256').decode('utf-8')
    return token

print(create_token())