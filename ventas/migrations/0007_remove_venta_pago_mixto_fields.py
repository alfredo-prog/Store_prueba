from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('ventas', '0006_venta_pago_mixto'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='venta',
            name='metodo_pago_electronico',
        ),
        migrations.RemoveField(
            model_name='venta',
            name='monto_efectivo',
        ),
        migrations.RemoveField(
            model_name='venta',
            name='monto_electronico',
        ),
    ]
