from openpyxl import Workbook
from django.contrib import admin
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



class UserAdmin(admin.ModelAdmin, ExportExcelMixin):
    list_display = ("id", "name", 'phone', 'gender', 'is_student', 'identity', 'is_active')
    readonly_fields = ('phone', 'idnumber')

    list_display_links = ['name']
    list_filter = ("is_student", 'is_active', 'gender')
    search_fields = ("name", "phone")
    actions = ['export_as_excel']

    def has_delete_permission(self, request, obj=None):
        return False


class LeaderAdmin(admin.ModelAdmin, ExportExcelMixin):
    list_display = ("id", "user_name", 'phone', 'is_active')
    readonly_fields = ()

    list_display_links = ['user_name']
    list_filter = ()
    # todo 修复search
    search_fields = ("name", "phone")
    actions = ['export_as_excel']

    def user_name(self, obj):
        if obj.user:
            return obj.user.name
        else:
            return '-'



admin.site.register(User, UserAdmin)
admin.site.register(Leader, LeaderAdmin)
