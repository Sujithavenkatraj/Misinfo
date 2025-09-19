from django.urls import path
from .views import AnalyzeAPIView, home, dashboard

urlpatterns = [
    path("", home, name="home"),                 
    path("api/analyze/", AnalyzeAPIView.as_view(), name="analyze"),
    path("dashboard/", dashboard, name="dashboard"),
]
