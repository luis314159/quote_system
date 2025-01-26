from django.urls import path
from . import views

app_name = 'session'

urlpatterns = [
    # Auth URLs
    path('login/', views.CustomLoginView.as_view(), name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    
    # Admin Dashboard
    path('admin/dashboard/', views.admin_dashboard, name='admin_dashboard'),
    
    # Company Management
    path('admin/companies/', views.CompanyListView.as_view(), name='company_list'),
    path('admin/companies/create/', views.CompanyCreateView.as_view(), name='company_create'),
    path('admin/companies/<int:pk>/update/', views.CompanyUpdateView.as_view(), name='company_update'),
    path('admin/companies/<int:company_id>/generate-code/', views.generate_registration_code, name='generate_code'),
    
    # User Management
    path('admin/users/', views.UserListView.as_view(), name='user_list'),
    path('admin/users/create/', views.AdminUserCreateView.as_view(), name='user_create'),
    path('admin/users/<int:pk>/update/', views.UserUpdateView.as_view(), name='user_update'),
]