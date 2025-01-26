from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator
from django.utils import timezone
import uuid


class User(AbstractUser):
    """Extended user model"""
    USER_TYPE_CHOICES = [
        ('ADMIN', 'Administrador'),
        ('COMPANY_USER', 'Usuario de Empresa'),
    ]
    
    user_type = models.CharField(
        max_length=20,
        choices=USER_TYPE_CHOICES,
        default='COMPANY_USER'
    )
    company = models.ForeignKey(
        'Company',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='employees'
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        permissions = [
            ("can_generate_codes", "Puede generar códigos de registro"),
            ("can_manage_companies", "Puede gestionar empresas"),
            ("can_manage_users", "Puede gestionar usuarios"),
        ]


class Company(models.Model):
    """Empresas cliente"""
    name = models.CharField("Nombre", max_length=200)
    rfc = models.CharField("RFC", max_length=13, unique=True, blank=True)
    address = models.TextField("Dirección", blank=True)
    contact_name = models.CharField("Nombre de Contacto", max_length=200)
    contact_email = models.EmailField("Email de Contacto")
    contact_phone = models.CharField("Teléfono de Contacto", max_length=20)
    stainless_steel_price = models.DecimalField(
        "Precio Acero Inoxidable por Kg",
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    carbon_steel_price = models.DecimalField(
        "Precio Acero al Carbono por Kg",
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    is_active = models.BooleanField("Activa", default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def generate_registration_code(self, created_by, expires_at):
        """Generate a new registration code for the company"""
        return RegistrationCode.objects.create(
            company=self,
            created_by=created_by,
            expires_at=expires_at
        )

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Empresa"
        verbose_name_plural = "Empresas"


class RegistrationCode(models.Model):
    """Códigos de registro de un solo uso"""
    code = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name='registration_codes',
        verbose_name="Empresa"
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_codes',
        verbose_name="Creado por"
    )
    created_at = models.DateTimeField("Fecha de Creación", auto_now_add=True)
    used_at = models.DateTimeField("Fecha de Uso", null=True, blank=True)
    is_used = models.BooleanField("Utilizado", default=False)
    expires_at = models.DateTimeField("Fecha de Expiración")

    def is_valid(self):
        """Check if the registration code is still valid"""
        if self.is_used:
            return False
        if self.expires_at < timezone.now():
            return False
        return True

    def __str__(self):
        return f"Código para {self.company.name}"

    class Meta:
        verbose_name = "Código de Registro"
        verbose_name_plural = "Códigos de Registro"
        ordering = ['-created_at']

class MaterialDensity(models.Model):
    MATERIAL_CHOICES = [
        ('stainless_steel', 'Acero Inoxidable'),
        ('carbon_steel', 'Acero al Carbono'),
    ]

    material_type = models.CharField(
        max_length=50,
        choices=MATERIAL_CHOICES,
        unique=True,
        verbose_name="Tipo de Material"
    )
    density = models.FloatField(
        verbose_name="Densidad (g/cm³)",
        help_text="Ingrese la densidad en gramos por centímetro cúbico."
    )
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Última Actualización")

    def __str__(self):
        return f"{self.get_material_type_display()} - {self.density} lb/in³"

    class Meta:
        verbose_name = "Densidad de Material"
        verbose_name_plural = "Densidades de Materiales"