from django.urls import path
from .views import current_user_view

urlpatterns = [
    path('me/', current_user_view, name='current-user'),
]