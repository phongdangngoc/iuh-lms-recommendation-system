from django.urls import path
from . import views

urlpatterns = [
    path('api/', views.Index.as_view())
]
