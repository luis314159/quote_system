from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html
from django.utils import timezone
from django.urls import reverse
from django.contrib import messages
from .models import (
    User, Company, RegistrationCode, MaterialDensity,
    Finish, CompanyMaterialPrice, CompanyFinishPrice
)


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    """Configuración personalizada del panel de admin para usuarios."""
    list_display = ('username', 'email', 'user_type', 'company', 'is_active', 'date_joined')
    list_filter = ('user_type', 'is_active', 'company')
    search_fields = ('username', 'email', 'company__name')
    ordering = ('-date_joined',)
    
    fieldsets = UserAdmin.fieldsets + (
        ('Información Adicional', {
            'fields': ('user_type', 'company'),
        }),
    )
    
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Información Adicional', {
            'fields': ('user_type', 'company'),
        }),
    )


class CompanyMaterialPriceInline(admin.TabularInline):
    """Inline admin for material prices"""
    model = CompanyMaterialPrice
    extra = 1
    fields = ('material', 'price_per_lb', 'is_active')


class CompanyFinishPriceInline(admin.TabularInline):
    """Inline admin for finish prices"""
    model = CompanyFinishPrice
    extra = 1
    fields = ('finish', 'price_multiplier', 'is_active')


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    """Configuración personalizada del panel de admin para empresas."""
    list_display = ('name', 'rfc', 'contact_name', 'is_active', 'view_employees_link', 
                   'view_materials_count', 'view_finishes_count')
    list_filter = ('is_active',)
    search_fields = ('name', 'rfc', 'contact_name')
    ordering = ('name',)
    inlines = [CompanyMaterialPriceInline, CompanyFinishPriceInline]

    def view_employees_link(self, obj):
        """Crea un enlace en el admin para ver los empleados de la empresa."""
        count = obj.employees.count()
        url = reverse('admin:quote_user_changelist') + f'?company__id__exact={obj.id}'
        return format_html('<a href="{}">{} empleados</a>', url, count)
    view_employees_link.short_description = 'Empleados'

    def view_materials_count(self, obj):
        """Muestra la cantidad de materiales con precio configurado"""
        count = obj.material_prices.filter(is_active=True).count()
        return f"{count} materiales"
    view_materials_count.short_description = 'Materiales'

    def view_finishes_count(self, obj):
        """Muestra la cantidad de acabados con precio configurado"""
        count = obj.finish_prices.filter(is_active=True).count()
        return f"{count} acabados"
    view_finishes_count.short_description = 'Acabados'


@admin.register(RegistrationCode)
class RegistrationCodeAdmin(admin.ModelAdmin):
    """Configuración personalizada del panel de admin para códigos de registro."""
    list_display = ('code', 'company', 'created_by', 'is_used', 'expires_at', 'status')
    list_filter = ('is_used', 'company')
    search_fields = ('code', 'company__name')
    readonly_fields = ('code', 'created_by', 'created_at', 'used_at')
    ordering = ('-created_at',)

    def status(self, obj):
        """Muestra el estado del código de registro."""
        if obj.is_used:
            return format_html('<span style="color: red;">Usado</span>')
        if obj.expires_at < timezone.now():
            return format_html('<span style="color: orange;">Expirado</span>')
        return format_html('<span style="color: green;">Válido</span>')
    status.short_description = 'Estado'

    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
            if not obj.expires_at:
                obj.expires_at = timezone.now() + timezone.timedelta(days=30)
        super().save_model(request, obj, form, change)

    def delete_queryset(self, request, queryset):
        count = queryset.count()
        queryset.delete()
        self.message_user(request, f'Se eliminaron {count} códigos de registro.', level=messages.SUCCESS)


@admin.register(MaterialDensity)
class MaterialDensityAdmin(admin.ModelAdmin):
    """Configuración del panel de admin para materiales."""
    list_display = ('name', 'density', 'is_active', 'updated_at', 'view_companies_count')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'description')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        (None, {
            'fields': ('name', 'description', 'density')
        }),
        ('Estado', {
            'fields': ('is_active', 'created_at', 'updated_at')
        }),
    )

    def view_companies_count(self, obj):
        """Muestra la cantidad de empresas que usan este material"""
        count = obj.company_prices.filter(is_active=True).count()
        return f"{count} empresas"
    view_companies_count.short_description = 'Empresas usando'


@admin.register(Finish)
class FinishAdmin(admin.ModelAdmin):
    """Configuración del panel de admin para acabados."""
    list_display = ('name', 'description', 'view_companies_count')
    search_fields = ('name',)

    def view_companies_count(self, obj):
        """Muestra la cantidad de empresas que usan este acabado"""
        count = obj.company_prices.filter(is_active=True).count()
        return f"{count} empresas"
    view_companies_count.short_description = 'Empresas usando'


@admin.register(CompanyMaterialPrice)
class CompanyMaterialPriceAdmin(admin.ModelAdmin):
    """Configuración del panel de admin para precios de materiales."""
    list_display = ('company', 'material', 'price_per_lb', 'is_active', 'updated_at')
    list_filter = ('company', 'material', 'is_active')
    search_fields = ('company__name', 'material__material_type')


@admin.register(CompanyFinishPrice)
class CompanyFinishPriceAdmin(admin.ModelAdmin):
    """Configuración del panel de admin para precios de acabados."""
    list_display = ('company', 'finish', 'price_multiplier', 'is_active', 'updated_at')
    list_filter = ('company', 'finish', 'is_active')
    search_fields = ('company__name', 'finish__name')