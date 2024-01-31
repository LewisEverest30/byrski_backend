from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
import jwt
from django.conf import settings
import datetime


def create_token(user, expdays=7):
    headers = {
        'typ': 'jwt',
        'alg': 'HS256'
    }
    payload = {
        'userid': user.id,
        'exp': datetime.datetime.utcnow() + datetime.timedelta(days=expdays)
    }
    # print(payload)
    token = jwt.encode(payload=payload, key=settings.SECRET_KEY, headers=headers, algorithm='HS256').decode('utf-8')
    return token

# class MyJWTAuthentication(JWTAuthentication):
class MyJWTAuthentication(BaseAuthentication):

    def authenticate(self, request):
        token = request.headers['Authorization']
        try:
            # print(token)
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
            # print(payload)
        except Exception as e:
            print(repr(e))
            raise AuthenticationFailed({'error': 'Token Authentication Failed'})

        return payload, token

    # user_model = User
	# # get_user用于返回用户，重写后在其它地方使用request.user时可以直接得到自定义的小程序用户
    # def get_user(self, validated_token):
    #     try:
    #         decode_data = jwt.decode(validated_token, secret_key=settings.SECRET_KEY, verify=True, algorithms=['HS256'])
    #         print(decode_data)
    #     except:
    #         raise AuthenticationFailed({'error': 'Token Authentication Failed'})

    #     userid = decode_data['user_id']
    #     print(userid)

    #     try:
    #         user = User.objects.get(id = userid)
    #     except User.DoesNotExist:
    #         raise AuthenticationFailed({'error': 'Invalid User'})
    #     if not user.is_active:
    #         raise AuthenticationFailed({'error': 'User is not active'})

    #     return user