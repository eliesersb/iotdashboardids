from iotdashboard.views import notification_data
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("notification_data/", notification_data, name="notification_data"),
    path('admin/', admin.site.urls),
    path('', include('iotdashboard.urls')),
]
