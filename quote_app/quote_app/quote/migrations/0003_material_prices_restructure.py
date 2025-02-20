# migrations/0003_material_prices_restructure.py
from django.db import migrations, models
import django.db.models.deletion

def preserve_material_prices(apps, schema_editor):
    Company = apps.get_model('quote', 'Company')
    MaterialDensity = apps.get_model('quote', 'MaterialDensity')
    CompanyMaterialPrice = apps.get_model('quote', 'CompanyMaterialPrice')
    
    # Asegurarse que existan los materiales base
    stainless_steel, _ = MaterialDensity.objects.get_or_create(
        material_type='stainless_steel',
        defaults={'density': 0.290}
    )
    carbon_steel, _ = MaterialDensity.objects.get_or_create(
        material_type='carbon_steel',
        defaults={'density': 0.284}
    )
    
    # Migrar precios existentes
    for company in Company.objects.all():
        if hasattr(company, 'stainless_steel_price'):
            CompanyMaterialPrice.objects.create(
                company=company,
                material=stainless_steel,
                price_per_lb=company.stainless_steel_price,
                is_active=True
            )
        if hasattr(company, 'carbon_steel_price'):
            CompanyMaterialPrice.objects.create(
                company=company,
                material=carbon_steel,
                price_per_lb=company.carbon_steel_price,
                is_active=True
            )

class Migration(migrations.Migration):
    dependencies = [
        ('quote', '0002_materialdensity_alter_company_address_and_more'),
    ]

    operations = [
        # 1. Crear el modelo Finish primero
        migrations.CreateModel(
            name='Finish',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, unique=True, verbose_name='Nombre del Acabado')),
                ('description', models.TextField(blank=True, verbose_name='Descripción')),
            ],
            options={
                'verbose_name': 'Acabado',
                'verbose_name_plural': 'Acabados',
            },
        ),
        # 2. Crear CompanyMaterialPrice
        migrations.CreateModel(
            name='CompanyMaterialPrice',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('price_per_lb', models.DecimalField(decimal_places=2, max_digits=10, validators=[django.core.validators.MinValueValidator(0)], verbose_name='Precio por libra')),
                ('is_active', models.BooleanField(default=True, verbose_name='Activo')),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('company', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='material_prices', to='quote.company')),
                ('material', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='company_prices', to='quote.materialdensity')),
            ],
            options={
                'verbose_name': 'Precio de Material por Empresa',
                'verbose_name_plural': 'Precios de Materiales por Empresa',
                'unique_together': {('company', 'material')},
            },
        ),
        # 3. Crear CompanyFinishPrice
        migrations.CreateModel(
            name='CompanyFinishPrice',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('price_multiplier', models.DecimalField(decimal_places=2, help_text='Factor por el que se multiplicará el precio base', max_digits=5, validators=[django.core.validators.MinValueValidator(0)], verbose_name='Multiplicador de Precio')),
                ('is_active', models.BooleanField(default=True, verbose_name='Activo')),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('company', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='finish_prices', to='quote.company')),
                ('finish', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='company_prices', to='quote.finish')),
            ],
            options={
                'verbose_name': 'Precio de Acabado por Empresa',
                'verbose_name_plural': 'Precios de Acabados por Empresa',
                'unique_together': {('company', 'finish')},
            },
        ),
        # 4. Agregar campos many-to-many a Company
        migrations.AddField(
            model_name='company',
            name='finishes',
            field=models.ManyToManyField(related_name='companies', through='quote.CompanyFinishPrice', to='quote.finish'),
        ),
        migrations.AddField(
            model_name='company',
            name='materials',
            field=models.ManyToManyField(related_name='companies', through='quote.CompanyMaterialPrice', to='quote.materialdensity'),
        ),
        # 5. Ejecutar la función de migración de datos
        migrations.RunPython(
            preserve_material_prices,
            reverse_code=migrations.RunPython.noop
        ),
        # 6. Finalmente, eliminar los campos antiguos
        migrations.RemoveField(
            model_name='company',
            name='carbon_steel_price',
        ),
        migrations.RemoveField(
            model_name='company',
            name='stainless_steel_price',
        ),
    ]