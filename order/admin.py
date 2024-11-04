from django.contrib import admin
from openpyxl import Workbook
from django.http import HttpResponse
from django.forms import BaseInlineFormSet, ValidationError

from .models import *


# 导出Excel
class ExportExcelMixin(object):
    def export_as_excel(self, request, queryset):
        meta = self.model._meta
        field_names = [field.name for field in meta.fields]

        response = HttpResponse(content_type='application/msexcel')
        response['Content-Disposition'] = f'attachment; filename={meta.object_name}.xlsx'
        wb = Workbook()
        ws = wb.active
        ws.append(field_names)
        for obj in queryset:
            for field in field_names:
                data = [f'{getattr(obj, field)}' for field in field_names]
            row = ws.append(data)

        wb.save(response)
        return response
    export_as_excel.short_description = '导出Excel'


# 导出Excel，专用于订单
class ExportOrderExcelMixin(object):
    def export_as_excel(self, request, queryset):
        meta = self.model._meta
        # field_names = ["ordernumber", 'user_name', 'ticket', 'ticket__price', 'return_boarded', 'create_time']

        response = HttpResponse(content_type='application/msexcel')
        response['Content-Disposition'] = f'attachment; filename={meta.object_name}.xlsx'
        wb = Workbook()
        ws = wb.active
        ws.append(['订单号', '报名人', '身份证号', '手机号', '性别', '学校', '上车点', '实付金额', '雪场名称', '活动名称',
                   '活动开始日期', '活动结束日期'
                #    , '', '', '', '', 
                   ])
        for obj in queryset:
            if obj.status==2 or obj.status==3:
                data = [
                    f'{obj.ordernumber}',
                    f'{obj.user.name}',
                    f'{obj.user.idnumber}',
                    f'{obj.user.phone}',
                    '男' if obj.user.gender==0 else '女',
                    f'{obj.user.school.name}',
                    f'{obj.bus_loc.loc.busboardloc}',
                    f'{obj.cost}',
                    f'{obj.ticket.activity.activity_template.ski_resort.name}',
                    f'{obj.ticket.activity.activity_template.name}',
                    f'{obj.ticket.activity.activity_begin_date}',
                    f'{obj.ticket.activity.activity_end_date}',
                    ]
                row = ws.append(data)

        wb.save(response)
        return response
    export_as_excel.short_description = '将所选订单中有效的导出为xlsx文件'

# ========================================Admin==================================================
# 每次活动的具体的大巴车
class Bus_boarding_timeInline(admin.TabularInline):
    fields = ('bus', 'loc', 'boarding_peoplenum', 'time')
    model = Bus_boarding_time
    extra = 0  # 默认显示 0 个 
    # todo 恢复
    # readonly_fields = ('bus', 'loc', 'boarding_peoplenum',)
class LeaderItineraryInlineFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()
        if any(self.errors):
            return
        # 如果没有至少一个ticket，抛出错误
        valid_form_num = 0
        for form in self.forms:
            if form.cleaned_data and not form.cleaned_data.get('DELETE', False):
                valid_form_num += 1
        if valid_form_num != 1:
            raise ValidationError('每个大巴车必须有一个领队')
class LeaderItineraryInline(admin.TabularInline):
    formset = LeaderItineraryInlineFormSet
    fields = ('bus', 'leader', 'bus_loc')
    model = LeaderItinerary
    extra = 0  # 默认显示 0 个 
    readonly_fields = ('bus',)
    # def save_formset(self, request, form, formset, change):
    #     instances = formset.save(commit=False)
    #     for instance in instances:
    #         if instance.bus_loc_id is None:  # 只设置新添加的实例
    #             instance.bus_loc_id = 1
    #         instance.save()
    #     formset.save_m2m()
class BusAdmin(admin.ModelAdmin, ExportExcelMixin):
    list_display = ('id', 'activity', 'car_number', 'driver_phone', 'carry_peoplenum', 'max_people', 'route', 'leader')
    # todo 恢复
    # readonly_fields = ('activity', 'max_people')
    # readonly_fields = ('max_people', )
    list_display_links = ['activity']
    list_filter = ("activity", )
    search_fields = ('activity__activity_template', 'car_number', 'driver_phone')
    actions = ['export_as_excel']
    inlines = [Bus_boarding_timeInline, LeaderItineraryInline,]
    # def save_model(self, request, obj, form, change):
    #     super().save_model(request, obj, form, change)
    #     # 获取所有新添加的LeaderItinerary实例并设置bus_loc_id为1
    #     for itinerary in obj.leaderitinerary_set.all():
    #         if itinerary.bus_loc_id is None:  # 只设置新添加的实例
    #             itinerary.bus_loc_id = 1
    #             itinerary.save()


# 每次活动的大巴车-所经站点-时间-没站搭载人数
class Bus_boarding_timeAdmin(admin.ModelAdmin, ExportExcelMixin):
    list_display = ("id", "bus", 'loc', 'boarding_peoplenum', 'time')
    readonly_fields = ("bus", 'loc', 'boarding_peoplenum')
    search_fields = ('bus__activity__activity_template', 'bus__car_number', 'bus__driver_phone')
    actions = ['export_as_excel']


# 雪票订单
class TicketOrderAdmin(admin.ModelAdmin, ExportOrderExcelMixin):
    list_display = ('id', "ordernumber", 'user', 'ticket', 'go_boarded', 'return_boarded', 'cost',
                     'bus_loc', 'create_time', 'status')
    # readonly_fields = ("ordernumber", 'user', 'activity', 'need_rent',
    #                  'bus_loc', 'create_time', 'is_paid')
    list_display_links = ['ordernumber']
    actions = ['export_as_excel']

    list_filter = ('status', 'go_boarded', 'return_boarded', 'ticket__activity__activity_begin_date')
    search_fields = ('user__name', 'ordernumber', 'ticket__activity__activity_template__name', 'bus_loc__loc__busboardloc',
                     'ticket__activity__activity_begin_date')


# 雪票订单
class LeaderItineraryAdmin(admin.ModelAdmin, ExportOrderExcelMixin):
    list_display = ('id', 'leader', 'bus', 'create_time', 'bus_loc')
    # readonly_fields = ("ordernumber", 'user', 'activity', 'need_rent',
    #                  'bus_loc', 'create_time', 'is_paid')
    # list_display_links = ['ordernumber']
    actions = ['export_as_excel']

    list_filter = ('bus__activity__activity_begin_date',)
    search_fields = ('user__name', 'activity__activity_template__name', 'bus_loc__loc__busboardloc',
                     'activity__activity_begin_date')


admin.site.register(Bus, BusAdmin)
admin.site.register(Bus_boarding_time, Bus_boarding_timeAdmin)
admin.site.register(TicketOrder, TicketOrderAdmin)
admin.site.register(LeaderItinerary, LeaderItineraryAdmin)  # todo