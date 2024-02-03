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
from user.views import *
from activity.views  import *

urlpatterns = [
    path('admin/', admin.site.urls),
    path('signup', signup.as_view()),
    path('login', login.as_view()),
    path('get_area', area.as_view()),
    path('get_school', school.as_view()),
    path('get_user_info', user_info.as_view()),
    path('checkstudentidentity', check_student.as_view()),
    path('update_user_ski_info', update_user_ski_info.as_view()),
    path('update_user_basic_info', update_user_basic_info.as_view()),

    path('get_activity_all', get_activity_all.as_view()),
    path('get_activity_active', get_activity_active.as_view()),
    path('get_rentprice', get_rentprice.as_view()),

]
