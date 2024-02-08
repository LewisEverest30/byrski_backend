from openpyxl import Workbook
from django.contrib import admin
from django.http import HttpResponse
from .models import *

# Register your models here.
admin.site.site_header = 'BYRSKI 后台管理'
admin.site.index_title = 'BYRSKI 后台管理'
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


class ReadOnlyAdminMixin:
    def has_add_permission(self, request):
        return True

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return True


class ActivityAdmin(admin.ModelAdmin, ExportExcelMixin):
    list_display = ("id", "ski_resort", 'date_arrangement', 'duration_days', 'price', 'need_rent',
                     'target_participant_num', 'current_participant_num', 'registration_status',
                     'signup_ddl_d', 'release_dt', 'notes')
    actions = ['export_as_excel']

    list_filter = ("ski_resort", "release_dt", 'registration_status', 'signup_ddl_d')
    # search_fields = ()


    # def get_readonly_fields(self, request, obj=None):
    #     if obj:
    #         return ["ski_resort", 'date_arrangement', 'duration_days',
    #                 'price', 'need_rent', "current_participant_num", 'release_dt', 'signup_ddl_d', 'registration_status']
    #     else:
    #         return ["current_participant_num", 'release_dt', 'registration_status']
    
    # readonly_fields = ("current_participant_num", 'release_dt', 'registration_status') 
    # list_display_links = ("ski_resort", 'date_arrangement', 'duration_days',
    #                        'price', 'need_rent', 'target_participant_num') #禁用编辑链接
    # List_display_links
    # @admin.display(description="滑雪场名称")
    # def skiresort_name(self, obj):
    #     return obj.ski_resort.name if obj.ski_resort.name else ''


class SkiresortAdmin(admin.ModelAdmin, ExportExcelMixin):
    list_display = ("id", "name", 'location')
    readonly_fields = ()


class RentpriceAdmin(admin.ModelAdmin, ExportExcelMixin):
    list_display = ('id', 'ski_resort')
    readonly_fields = ()
    
    actions = ['export_as_excel']


class RentorderAdmin(admin.ModelAdmin, ExportExcelMixin):
    list_display = ('id', 'user', 'order', 'activity', 'duration_days', 'helmet', 'glasses', 'gloves',
                     'hippad', 'kneepad', 'wristpad', 'snowboard', 'skiboots', 'is_active')
    readonly_fields = ('user', 'order', 'activity', 'duration_days', 'helmet', 'glasses', 'gloves',
                     'hippad', 'kneepad', 'wristpad', 'snowboard', 'skiboots', 'is_active')

    actions = ['export_as_excel']

    list_filter = ("activity", 'is_active')
    search_fields = ('user__name', 'order__ordernumber', 'activity__ski_resort__name')


class BusAdmin(admin.ModelAdmin, ExportExcelMixin):
    list_display = ('id', 'activity', 'car_number', 'bus_peoplenum', 'max_people', 'route')
    readonly_fields = ('activity', 'bus_peoplenum', 'max_people')
    list_display_links = ['activity']
    actions = ['export_as_excel']


class Bus_loc_timeAdmin(admin.ModelAdmin, ExportExcelMixin):
    list_display = ("id", "bus", 'loc', 'bus_loc_peoplenum', 'time')
    readonly_fields = ("bus", 'loc', 'bus_loc_peoplenum')

    actions = ['export_as_excel']


class BuslocAdmin(admin.ModelAdmin, ExportExcelMixin):
    list_display = ("id", "activity", 'loc', 'loc_peoplenum')

    readonly_fields = ['loc_peoplenum']
    actions = ['export_as_excel']
    list_filter = ("activity", 'loc')



class OrderAdmin(admin.ModelAdmin, ExportExcelMixin):
    list_display = ('id', "ordernumber", 'user', 'activity', 'need_rent',
                     'bus_loc', 'bus', 'bus_time', 'create_time', 'is_paid')
    # readonly_fields = ("ordernumber", 'user', 'activity', 'need_rent',
    #                  'bus_loc', 'create_time', 'is_paid')
    list_display_links = ['ordernumber']
    actions = ['export_as_excel']

    list_filter = ("activity", 'is_paid', 'bus_loc', 'need_rent')
    search_fields = ('user__name', 'ordernumber', 'activity__ski_resort__name', 'bus_loc__loc__campus')


admin.site.register(Activity, ActivityAdmin)
admin.site.register(Skiresort, SkiresortAdmin)
admin.site.register(Rentprice, RentpriceAdmin)
admin.site.register(Rentorder, RentorderAdmin)
admin.site.register(Bus, BusAdmin)
admin.site.register(Bus_loc_time, Bus_loc_timeAdmin)
admin.site.register(Busloc, BuslocAdmin)
admin.site.register(Order, OrderAdmin)
