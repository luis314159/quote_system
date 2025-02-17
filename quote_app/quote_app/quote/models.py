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


from django.utils import timezone

class MaterialDensity(models.Model):
    """Material densities and types"""
    material_type = models.CharField(
        max_length=50,
        choices=[
            ('stainless_steel', 'Acero Inoxidable'),
            ('carbon_steel', 'Acero al Carbono'),
        ],
        null=True,  # Permitimos null temporalmente
        blank=True,
        verbose_name="Tipo de Material"
    )
    name = models.CharField(
        max_length=100,
        null=True,  # Permitimos null temporalmente
        blank=True,
        verbose_name="Nombre del Material"
    )
    description = models.TextField(
        verbose_name="Descripción",
        blank=True,
        help_text="Descripción opcional del material"
    )
    density = models.FloatField(
        verbose_name="Densidad (lb/in³)",
        help_text="Ingrese la densidad en libras por pulgada cúbica"
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Activo"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha de Creación"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Última Actualización"
    )

    def __str__(self):
        if self.name:
            return f"{self.name} - {self.density} lb/in³"
        return f"{self.get_material_type_display()} - {self.density} lb/in³"

    class Meta:
        verbose_name = "Material"
        verbose_name_plural = "Materiales"
        ordering = ['name']

        
class Finish(models.Model):
    """Available finishes for materials"""
    name = models.CharField("Nombre del Acabado", max_length=100, unique=True)
    description = models.TextField("Descripción", blank=True)
    
    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Acabado"
        verbose_name_plural = "Acabados"


class Company(models.Model):
    """Client companies"""
    name = models.CharField("Nombre", max_length=200)
    rfc = models.CharField("RFC", max_length=13, unique=True, blank=True)
    address = models.TextField("Dirección", blank=True)
    contact_name = models.CharField("Nombre de Contacto", max_length=200)
    contact_email = models.EmailField("Email de Contacto")
    contact_phone = models.CharField("Teléfono de Contacto", max_length=20)
    is_active = models.BooleanField("Activa", default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Many-to-many relationships through price tables
    finishes = models.ManyToManyField(
        Finish,
        through='CompanyFinishPrice',
        related_name='companies'
    )
    materials = models.ManyToManyField(
        MaterialDensity,
        through='CompanyMaterialPrice',
        related_name='companies'
    )

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


class CompanyMaterialPrice(models.Model):
    """Material prices per company"""
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name='material_prices'
    )
    material = models.ForeignKey(
        MaterialDensity,
        on_delete=models.CASCADE,
        related_name='company_prices'
    )
    price_per_lb = models.DecimalField(
        "Precio por libra",
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    is_active = models.BooleanField("Activo", default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['company', 'material']
        verbose_name = "Precio de Material por Empresa"
        verbose_name_plural = "Precios de Materiales por Empresa"

    def __str__(self):
        return f"{self.company.name} - {self.material.get_material_type_display()} - ${self.price_per_lb}/lb"


class CompanyFinishPrice(models.Model):
    """Finish prices per company"""
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name='finish_prices'
    )
    finish = models.ForeignKey(
        Finish,
        on_delete=models.CASCADE,
        related_name='company_prices'
    )
    price_multiplier = models.DecimalField(
        "Multiplicador de Precio",
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text="Factor por el que se multiplicará el precio base"
    )
    is_active = models.BooleanField("Activo", default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['company', 'finish']
        verbose_name = "Precio de Acabado por Empresa"
        verbose_name_plural = "Precios de Acabados por Empresa"

    def __str__(self):
        return f"{self.company.name} - {self.finish.name} - x{self.price_multiplier}"


class RegistrationCode(models.Model):
    """Single-use registration codes"""
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