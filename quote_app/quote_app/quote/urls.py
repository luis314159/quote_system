from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('about/', views.about, name='about'),
    path('upload/', views.upload_step, name='upload'),  
    path('result/', views.results, name='results'),  
]