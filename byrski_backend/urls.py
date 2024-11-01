"""
URL configuration for byrski_backend project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from django.conf.urls.static import static

from user.views import *
from activity.views  import *
from order.views  import *

urlpatterns = [
    path('admin/', admin.site.urls),

    path('python/login', login.as_view()),
    path('python/check_student', check_student.as_view()),
    path('python/get_user_basic_info', get_user_basic_info.as_view()),
    path('python/update_user_basic_info', update_user_basic_info.as_view()),

    path('python/get_tickets_of_homepage_activity', get_tickets_of_homepage_activity.as_view()),
    path('python/get_all_skiresort', get_all_skiresort.as_view()),
    path('python/get_tickets_of_certain_skiresort', get_tickets_of_certain_skiresort.as_view()),
    path('python/get_certain_activity_template', get_certain_activity_template.as_view()),
    path('python/get_certain_ticket', get_certain_ticket.as_view()),
    path('python/get_boardingloc', get_boardingloc.as_view()),

    path('python/create_ticket_order', create_ticket_order.as_view()),
    path('python/get_itinerary_of_certain_order', get_itinerary_of_certain_order.as_view()),
    path('python/get_all_itinerary', get_all_itinerary.as_view()),
    path('python/get_detail_of_certain_itinerary', get_detail_of_certain_itinerary.as_view()),
    path('python/get_available_boardingloc_of_certain_itinerary', get_available_boardingloc_of_certain_itinerary.as_view()),
    path('python/try_refund_ticket_order', try_refund_ticket_order.as_view()),
    path('python/select_new_boardingloc', select_new_boardingloc.as_view()),
    path('python/set_go_boarded', set_go_boarded.as_view()),
    path('python/set_return_boarded', set_return_boarded.as_view()),
    path('python/get_activity_guide_step', get_activity_guide_step.as_view()),
    path('python/next_activity_guide_step', next_activity_guide_step.as_view()),
    path('python/set_activity_guide_finished', set_activity_guide_finished.as_view()),

    path('python/get_ticket_order_list_by_status', get_ticket_order_list_by_status.as_view()),
    path('python/get_detail_of_certain_ticket_order', get_detail_of_certain_ticket_order.as_view()),
    path('python/cancel_ticket_order', cancel_ticket_order.as_view()),
    path('python/delete_ticket_order', delete_ticket_order.as_view()),

    path('python/get_itinerary_qrcode',get_itinerary_qrcode.as_view()),
    path('verify_itinerary_qrcode',verify_itinerary_qrcode.as_view()),
    # path('python/get_bus_boarding_list', get_bus_boarding_passenger_list.as_view()),

    # path('get_busloc', get_busloc.as_view()),
    # path('create_activity_order', create_activity_order.as_view()),
    # path('set_activity_order_paid', set_activity_order_paid.as_view()),
    # path('cancel_order', cancel_order.as_view()),
    # path('get_a_activity_order_by_activityid', get_a_activity_order_by_activityid.as_view()),
    # path('get_a_activity_order_by_orderid', get_a_activity_order_by_orderid.as_view()),
    # path('get_all_activity_order', get_all_activity_order.as_view()),
        
    # path('get_rentprice', get_rentprice.as_view()),
    # path('create_rent_order', create_rent_order.as_view()),
    # path('get_a_rent_order', get_a_rent_order.as_view()),
    # path('cancel_rent_order', cancel_rent_order.as_view()),


]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)