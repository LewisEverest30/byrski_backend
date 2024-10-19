import json
import datetime
from django.conf import settings
from rest_framework.response import Response
from rest_framework.views import APIView

from user.models import User, Accesstoken, UserSerializer
from user.auth import MyJWTAuthentication, create_token
from .models import *


class get_area(APIView):
    def get(self,request,*args,**kwargs):
        all_areas = Area.objects.all().values()
        return Response({'ret': 0, 'area': list(all_areas)})


class get_school(APIView):
    def get(self,request,*args,**kwargs):
        all_schools = BoardingLocTemplate.objects.all()
        serializer = BoardingLocTemplateSerializer(instance=all_schools, many=True)
        return Response({'ret': 0, 'school': list(serializer.data)})
        # return Response({'ret': 0, 'areas': list(all_schools)})


class get_busloc(APIView):
    def post(self,request,*args,**kwargs):
        info = json.loads(request.body)
        try:
            acti_id = info['activity_id']
            busloc = Boardingloc.objects.filter(activity_id=acti_id)
            if busloc.count() == 0:
                return Response({'ret': -1, 'activity': None})
            serializer = BoardinglocSerializer(instance=busloc, many=True)
            return Response({'ret': 0, 'activity': list(serializer.data)})
        except Exception as e:
            print(repr(e))
            return Response({'ret': -1, 'activity': None})
