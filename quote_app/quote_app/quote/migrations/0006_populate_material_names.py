from django.db import migrations

def populate_names(apps, schema_editor):
    MaterialDensity = apps.get_model('quote', 'MaterialDensity')
    for material in MaterialDensity.objects.all():
        if material.material_type == 'stainless_steel':
            material.name = 'Acero Inoxidable'
        elif material.material_type == 'carbon_steel':
            material.name = 'Acero al Carbono'
        else:
            material.name = material.get_material_type_display()
        material.save()

def reverse_populate(apps, schema_editor):
    MaterialDensity = apps.get_model('quote', 'MaterialDensity')
    MaterialDensity.objects.all().update(name=None)

class Migration(migrations.Migration):
    dependencies = [
        ('quote', '0005_alter_materialdensity_options_and_more'),
    ]

    operations = [
        migrations.RunPython(populate_names, reverse_populate),
    ]