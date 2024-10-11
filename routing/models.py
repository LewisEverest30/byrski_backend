from django.db import models
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from activity.models import Activity



class Area(models.Model):
    area_name = models.CharField('地区名称', max_length=100, unique=True)

    def __str__(self) -> str:
        return self.area_name

    class Meta:
        verbose_name = "地区"
        verbose_name_plural = "地区"


class School(models.Model):
    school_name = models.CharField(verbose_name='学校名称', max_length=50)

    campus = models.CharField(verbose_name='学校位置(学校名+校区)', max_length=150, unique=True)
    busboardloc  =  models.CharField(verbose_name='上车点(学校名+校区+门)', max_length=150, null=True)
    area = models.ForeignKey(verbose_name='所在地区', to=Area, on_delete=models.CASCADE)

    def __str__(self) -> str:
        return self.campus

    class Meta:
        verbose_name = "学校(校区)"
        verbose_name_plural = "学校(校区)"


class Bustype(models.Model):
    passenger_num = models.IntegerField(verbose_name='可承载人数')

    def __str__(self) -> str:
        return '可承载'+str(self.passenger_num)+'人'
    
    class Meta:
        verbose_name = "大巴车类型(只支持两种类型)"
        verbose_name_plural = "大巴车类型(只支持两种类型)"


# --------------------------------------------------------------------------------------------------

class Boardingloc(models.Model):
    activity = models.ForeignKey(verbose_name='活动', to=Activity, on_delete=models.PROTECT)
    loc = models.ForeignKey(verbose_name='上车点', to=School, on_delete=models.PROTECT)
    loc_peoplenum = models.IntegerField(verbose_name='人数', default=0)

    def __str__(self) -> str:
        return str(self.loc)+' ('+str(self.activity)+')'
    
    class Meta:
        verbose_name = "上车点"
        verbose_name_plural = "上车点"
        unique_together = (("activity", "loc"),)


class Bus(models.Model):
    activity = models.ForeignKey(verbose_name='活动', to=Activity, on_delete=models.PROTECT)

    car_number = models.CharField(verbose_name='车牌号', null=True, max_length=10)
    bus_peoplenum = models.IntegerField(verbose_name='该车总人数', default=0)
    route = models.CharField(verbose_name='路线规划', max_length=500, null=True)
    max_people = models.IntegerField(verbose_name='车型最大承载人数', null=True)

    def __str__(self) -> str:
        return str(self.car_number) + ' ( id: ' + str(self.id) + ', 乘客数: ' + str(self.bus_peoplenum) + ')'
    
    class Meta:
        verbose_name = "大巴车"
        verbose_name_plural = "大巴车"


class Bus_boarding_time(models.Model):
    bus = models.ForeignKey(verbose_name='大巴', to=Bus, on_delete=models.CASCADE)
    loc = models.ForeignKey(verbose_name='途径点', to=Boardingloc, on_delete=models.PROTECT)
    boarding_peoplenum = models.IntegerField(verbose_name='该点该车上车人数', default=0)
    time = models.DateTimeField(verbose_name='途径时间', null=True)

    def __str__(self) -> str:
        return str(self.time)

    class Meta:
        verbose_name = "车-途径点-时间 对应关系"
        verbose_name_plural = "车-途径点-时间 对应关系"



class SchoolSerializer(serializers.ModelSerializer):
    area = serializers.CharField(source='area.area_name')
    area_id = serializers.IntegerField(source='area.id')
    class Meta:
        model = School
        fields = '__all__'


class BuslocSerializer(serializers.ModelSerializer):
    loc = serializers.CharField(source='loc.busboardloc')
    loc_id = serializers.IntegerField(source='loc.id')
    class Meta:
        model = Boardingloc
        fields = '__all__'
