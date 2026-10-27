from django.urls import path

from . import views

urlpatterns = [
    path("readings/", views.readings),
    path("status/", views.status),
    path("chat/", views.chat_view),
]
