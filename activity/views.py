import json
import requests
import datetime
from django.conf import settings
from django.http import JsonResponse
from django.forms.models import model_to_dict
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import *

# Create your views here.

class get_activity_all(APIView):
    def get(self,request,*args,**kwargs):
        all_activity = Activity.objects.all()
        serializer = ActivitySerializer(instance=all_activity, many=True)
        return Response({'ret': 0, 'activity': list(serializer.data)})


class get_activity_active(APIView):
    def get(self,request,*args,**kwargs):
        active_activity = Activity.objects.filter(registration_status=True)
        serializer = ActivitySerializer(instance=active_activity, many=True)
        return Response({'ret': 0, 'activity': list(serializer.data)})


class get_rentprice(APIView):
    def post(self,request,*args,**kwargs):
        info = json.loads(request.body)
        ski_resort_id = info['ski_resort_id']
        try:
            activity = Rentprice.objects.get(ski_resort_id=ski_resort_id)
            return Response({'ret': 0, 'activity': model_to_dict(activity)})
        except Exception as e:
            print(repr(e))
            return Response({'ret': -1, 'activity': None})


class create_activity_order(APIView):
    def get(self,request,*args,**kwargs):
        all_activity = Activity.objects.all()
        serializer = ActivitySerializer(instance=all_activity, many=True)
        return Response({'ret': 0, 'activity': list(serializer.data)})
