from django.urls import path, include
urlpatterns = [
    path("", include("ai_misinfo.analyzer.urls")),
]
