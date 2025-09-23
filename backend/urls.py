from django.contrib import admin
from django.urls import path
from . import views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("health/", views.healthcheck),
    path("creators/", views.creators_list),
    path("teams/", views.teams_list),
    path("", views.root),
]
