from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.views import LoginView
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.contrib import messages
from django.utils import timezone
from .forms import LoginForm, CompanyUserRegistrationForm, AdminUserCreationForm
from quote.models import User, Company, RegistrationCode

class CustomLoginView(LoginView):
    form_class = LoginForm
    template_name = 'session/login.html'
    
    def get_success_url(self):
        if self.request.user.user_type == 'ADMIN':
            return reverse_lazy('session:admin_dashboard')
        return reverse_lazy('quote:home')

def register_view(request):
    if request.method == 'POST':
        form = CompanyUserRegistrationForm(request.POST)
        if form.is_valid():
            registration_code = form.cleaned_data['registration_code']
            try:
                code = RegistrationCode.objects.get(
                    code=registration_code,
                    is_used=False,
                    expires_at__gt=timezone.now()
                )
                user = form.save(commit=False)
                user.user_type = 'COMPANY_USER'
                user.company = code.company
                user.save()
                
                code.is_used = True
                code.used_at = timezone.now()
                code.save()
                
                login(request, user)
                return redirect('quote:home')
                
            except RegistrationCode.DoesNotExist:
                form.add_error('registration_code', 'Código inválido o expirado')
    else:
        form = CompanyUserRegistrationForm()
    
    return render(request, 'session/register.html', {'form': form})

def logout_view(request):
    logout(request)
    return redirect('session:login')

# Admin views
def is_admin(user):
    return user.user_type == 'ADMIN'

@login_required
@user_passes_test(is_admin)
def admin_dashboard(request):
    total_companies = Company.objects.count()
    active_companies = Company.objects.filter(is_active=True).count()
    total_users = User.objects.filter(user_type='COMPANY_USER').count()
    active_codes = RegistrationCode.objects.filter(
        is_used=False,
        expires_at__gt=timezone.now()
    ).count()
    
    context = {
        'total_companies': total_companies,
        'active_companies': active_companies,
        'total_users': total_users,
        'active_codes': active_codes
    }
    return render(request, 'session/admin/dashboard.html', context)

# Company Management Views
class CompanyListView(ListView):
    model = Company
    template_name = 'session/admin/company_list.html'
    context_object_name = 'companies'
    
    def get_queryset(self):
        return Company.objects.all().order_by('-created_at')

class CompanyCreateView(CreateView):
    model = Company
    template_name = 'session/admin/company_form.html'
    fields = ['name', 'rfc', 'address', 'contact_name', 'contact_email', 
              'contact_phone', 'stainless_steel_price', 'carbon_steel_price']
    success_url = reverse_lazy('session:company_list')

class CompanyUpdateView(UpdateView):
    model = Company
    template_name = 'session/admin/company_form.html'
    fields = ['name', 'rfc', 'address', 'contact_name', 'contact_email', 
              'contact_phone', 'stainless_steel_price', 'carbon_steel_price', 'is_active']
    success_url = reverse_lazy('session:company_list')

# User Management Views
class UserListView(ListView):
    model = User
    template_name = 'session/admin/user_list.html'
    context_object_name = 'users'
    
    def get_queryset(self):
        return User.objects.filter(user_type='COMPANY_USER').order_by('-date_joined')

class AdminUserCreateView(CreateView):
    model = User
    form_class = AdminUserCreationForm
    template_name = 'session/admin/user_form.html'
    success_url = reverse_lazy('session:user_list')

class UserUpdateView(UpdateView):
    model = User
    template_name = 'session/admin/user_form.html'
    fields = ['username', 'email', 'first_name', 'last_name', 'is_active']
    success_url = reverse_lazy('session:user_list')

# Registration Code Management
@login_required
@user_passes_test(is_admin)
def generate_registration_code(request, company_id):
    company = Company.objects.get(id=company_id)
    code = RegistrationCode.objects.create(
        company=company,
        created_by=request.user,
        expires_at=timezone.now() + timezone.timedelta(days=30)
    )
    messages.success(request, f'Código generado: {code.code}')
    return redirect('session:company_detail', pk=company_id)