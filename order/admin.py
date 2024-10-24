from django.contrib import admin
from openpyxl import Workbook
from django.http import HttpResponse

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



# ========================================Admin==================================================
# 每次活动的具体的大巴车
class Bus_boarding_timeInline(admin.TabularInline):
    fields = ('bus', 'loc', 'boarding_peoplenum', 'time')
    model = Bus_boarding_time
    extra = 0  # 默认显示 0 个 
    readonly_fields = ('bus', 'loc', 'boarding_peoplenum',)
class BusAdmin(admin.ModelAdmin, ExportExcelMixin):
    list_display = ('id', 'activity', 'car_number', 'driver_phone', 'carry_peoplenum', 'max_people', 'route', 'leader')
    # todo readonly_fields = ('activity', 'max_people')
    readonly_fields = ('max_people', )
    list_display_links = ['activity']
    list_filter = ("activity", )
    search_fields = ('activity__activity_template', 'car_number', 'driver_phone')
    actions = ['export_as_excel']
    inlines = [Bus_boarding_timeInline, ]


# 每次活动的大巴车-所经站点-时间-没站搭载人数
class Bus_boarding_timeAdmin(admin.ModelAdmin, ExportExcelMixin):
    list_display = ("id", "bus", 'loc', 'boarding_peoplenum', 'time')
    readonly_fields = ("bus", 'loc', 'boarding_peoplenum')
    search_fields = ('bus__activity__activity_template', 'bus__car_number', 'bus__driver_phone')
    actions = ['export_as_excel']


# 雪票订单
class TicketOrderAdmin(admin.ModelAdmin, ExportExcelMixin):
    list_display = ('id', "ordernumber", 'user', 'ticket', 'go_boarded', 'return_boarded',
                     'bus_loc', 'create_time', 'status')
    # readonly_fields = ("ordernumber", 'user', 'activity', 'need_rent',
    #                  'bus_loc', 'create_time', 'is_paid')
    list_display_links = ['ordernumber']
    actions = ['export_as_excel']

    list_filter = ('status', 'go_boarded', 'return_boarded', )
    search_fields = ('user__name', 'ordernumber', 'ticket__activity', 'bus_loc__loc__campus')


admin.site.register(Bustype)
admin.site.register(Bus, BusAdmin)
admin.site.register(Bus_boarding_time, Bus_boarding_timeAdmin)
admin.site.register(TicketOrder, TicketOrderAdmin)