from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html
from django.utils import timezone
from django.urls import reverse
from .models import User, Company, RegistrationCode, MaterialDensity
from django.contrib import messages


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    """Configuración personalizada del panel de admin para usuarios."""
    list_display = ('username', 'email', 'user_type', 'company', 'is_active', 'date_joined')
    list_filter = ('user_type', 'is_active', 'company')
    search_fields = ('username', 'email', 'company__name')
    ordering = ('-date_joined',)
    
    # Extiende los fieldsets del modelo User para agregar nuevos campos
    fieldsets = UserAdmin.fieldsets + (
        ('Información Adicional', {
            'fields': ('user_type', 'company'),
        }),
    )
    
    # Personalización de campos en el formulario de creación
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Información Adicional', {
            'fields': ('user_type', 'company'),
        }),
    )


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    """Configuración personalizada del panel de admin para empresas."""
    list_display = ('name', 'rfc', 'contact_name', 'is_active', 'view_employees_link')
    list_filter = ('is_active',)
    search_fields = ('name', 'rfc', 'contact_name')
    ordering = ('name',)

    def view_employees_link(self, obj):
        """Crea un enlace en el admin para ver los empleados de la empresa."""
        count = obj.employees.count()  # Usa el related_name 'employees'
        url = reverse('admin:quote_user_changelist') + f'?company__id__exact={obj.id}'
        return format_html('<a href="{}">{} empleados</a>', url, count)



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
        """Guarda el modelo con valores predeterminados si es un nuevo registro."""
        if not change:  # Solo si es un nuevo registro
            obj.created_by = request.user
            # Establece una fecha de expiración predeterminada de 30 días
            if not obj.expires_at:
                obj.expires_at = timezone.now() + timezone.timedelta(days=30)
        super().save_model(request, obj, form, change)

    def delete_queryset(self, request, queryset):
        """Personaliza el mensaje al eliminar códigos en masa."""
        count = queryset.count()
        queryset.delete()
        self.message_user(request, f'Se eliminaron {count} códigos de registro.', level=messages.SUCCESS)

@admin.register(MaterialDensity)
class MaterialDensityAdmin(admin.ModelAdmin):
    list_display = ('material_type', 'density', 'updated_at')
    list_filter = ('material_type',)
    search_fields = ('material_type',)