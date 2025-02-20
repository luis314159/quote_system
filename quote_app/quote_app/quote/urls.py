from django.urls import path
from . import views

app_name = 'quote'

urlpatterns = [
    path('', views.home, name='home'),
    path('about/', views.about, name='about'),
    path('contact/', views.contact, name='contact'),
    path('upload/', views.upload_step, name='upload'),  
    path('results/', views.results, name='results'),
    path('update-material/', views.update_material, name='update_material'),
    path('generate_quote/', views.generate_quote, name='generate_quote'),
]