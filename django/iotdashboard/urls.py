from django.urls import path
from .views import (
    home,
    overview_data,
    monitoring,
    monitoring_data,
    alert,
    alert_data,
    nodes,
    nodes_data,
    summary,
    summary_data,
    maintenance,
    maintenance_clear_protocol_metrics,
    maintenance_clear_snort_alerts,
    maintenance_clear_all_influx_data,
    notification_data,
)

urlpatterns = [
    path("notification_data/", notification_data, name="notification_data"),
    path('', home, name='home'),
    path('overview_data/', overview_data, name='overview_data'),

    path('monitoring/', monitoring, name='monitoring'),
    path('monitoring_data/', monitoring_data, name='monitoring_data'),

    path('alert/', alert, name='alert'),
    path('alert_data/', alert_data, name='alert_data'),

    path('nodes/', nodes, name='nodes'),
    path('nodes_data/', nodes_data, name='nodes_data'),

    path('summary/', summary, name='summary'),
    path('summary_data/', summary_data, name='summary_data'),

    path('maintenance/', maintenance, name='maintenance'),
    path('maintenance/clear_protocol_metrics/', maintenance_clear_protocol_metrics, name='clear_protocol_metrics'),
    path('maintenance/clear_snort_alerts/', maintenance_clear_snort_alerts, name='clear_snort_alerts'),
    path('maintenance/clear_all_influx_data/', maintenance_clear_all_influx_data, name='clear_all_influx_data'),
]
