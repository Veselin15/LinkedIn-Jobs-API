from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('register/', views.register, name='register'),
    path('jobs/', views.job_list, name='job_list'),
    path('regenerate-key/', views.regenerate_api_key, name='regenerate_api_key'),
]

