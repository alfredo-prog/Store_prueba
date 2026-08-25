# Generated manually to add missing timestamp fields

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('inventario', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='producto',
            name='fecha_creacion',
            field=models.DateTimeField(auto_now_add=True, null=True, verbose_name='Fecha de creación'),
        ),
        migrations.AddField(
            model_name='producto',
            name='fecha_actualizacion',
            field=models.DateTimeField(auto_now=True, verbose_name='Fecha de actualización'),
        ),
    ]
