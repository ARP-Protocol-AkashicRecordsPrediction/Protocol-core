from django.urls import path

from . import ui_views

urlpatterns = [
    path("", ui_views.dashboard, name="ui-dashboard"),
    path("agendas/<uuid:agenda_id>/", ui_views.agenda_detail, name="ui-agenda-detail"),
    path("runs/<uuid:run_id>/", ui_views.run_detail, name="ui-run-detail"),
]

