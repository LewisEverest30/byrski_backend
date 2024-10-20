from openpyxl import Workbook
from django.contrib import admin
from django.http import HttpResponse
from django.utils.safestring import mark_safe

from .models import *

# ==================全局设置========================
admin.site.site_header = 'BYRSKI 后台管理'
admin.site.index_title = 'BYRSKI 后台管理'


# ======================================工具类=================================================
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


# ===========================================Admin==========================================
# 服务区域
class AreaAdmin(admin.ModelAdmin, ExportExcelMixin):
    list_display = ("id", "area_name")
    readonly_fields = ()
    list_display_links = ['area_name']


# 可选上车点
class BoardingLocTemplateAdmin(admin.ModelAdmin, ExportExcelMixin):
    list_display = ("id", "campus", "busboardloc")
    readonly_fields = ()
    list_display_links = ['busboardloc']


# 雪场
class SkiresortPicInline(admin.TabularInline):
    fields = ('pic','thumbnail',)
    model = SkiresortPic
    extra = 0  # 默认显示 0 个 
    
    readonly_fields = ('thumbnail',)
    @admin.display(description="缩略图")
    def thumbnail(self, obj):
        if obj.pic:
            return mark_safe(f'<img src="{obj.pic.url}" height="80" />')
        else:
            return '-'
class SkiresortAdmin(admin.ModelAdmin, ExportExcelMixin):
    list_display = ("id", "name", 'location', 'opening', 'phone')
    readonly_fields = ()
    actions = ['export_as_excel']
    inlines = [SkiresortPicInline]
    list_display_links = ['name']


# 活动模板
class ActivityTemplateAdmin(admin.ModelAdmin, ExportExcelMixin):
    list_display = ("id", "ski_resort", 'duration_days', )
    actions = ['export_as_excel']
    list_filter = ("ski_resort", )


# 活动-票-群-上车点
class TicketInline(admin.TabularInline):
    fields = ('intro', 'service', 'price', 'original_price')
    model = Ticket
    extra = 0  # 默认显示 0 个 
    readonly_fields = ('sales',)
class BoardinglocInline(admin.TabularInline):
    fields = ('loc','target_peoplenum',)
    model = Boardingloc
    extra = 0  # 默认显示 0 个 
    readonly_fields = ('choice_peoplenum',)
class ActivityWxGroupInline(admin.TabularInline):
    fields = ('qrcode','thumbnail',)
    model = ActivityWxGroup
    extra = 0  # 默认显示 0 个 
    readonly_fields = ('thumbnail',)
    
    @admin.display(description="缩略图")
    def thumbnail(self, obj):
        if obj.qrcode:
            return mark_safe(f'<img src="{obj.qrcode.url}" height="80" />')
        else:
            return '-'
class ActivityAdmin(admin.ModelAdmin, ExportExcelMixin):
    list_display = ("id", "activity_template", 'activity_begin_date', 'signup_ddl_date',
                     'lock_ddl_date', 'status', 'target_participant', 'current_participant')
    actions = ['export_as_excel']

    list_filter = ("activity_template", "status")

    readonly_fields = ('current_participant', )
    inlines = [TicketInline, ActivityWxGroupInline, BoardinglocInline]


# 上车点
class BoardinglocAdmin(admin.ModelAdmin, ExportExcelMixin):
    list_display = ("id", "activity", 'loc', 'choice_peoplenum', 'target_peoplenum')
    actions = ['export_as_excel']
    search_fields = ("activity", )
    readonly_fields = ('choice_peoplenum',)


# 雪票
class TicketAdmin(admin.ModelAdmin, ExportExcelMixin):
    list_display = ("id", "activity", 'price', 'sales', )
    actions = ['export_as_excel']
    search_fields = ("activity", )
    readonly_fields = ('sales',)


admin.site.register(Area, AreaAdmin)
admin.site.register(BoardingLocTemplate, BoardingLocTemplateAdmin)
admin.site.register(Skiresort, SkiresortAdmin)
admin.site.register(ActivityTemplate, ActivityTemplateAdmin)
admin.site.register(Activity, ActivityAdmin)
admin.site.register(Boardingloc, BoardinglocAdmin)



'''
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


admin.site.register(RentPrice, RentpriceAdmin)
admin.site.register(RentOrder, RentorderAdmin)
'''