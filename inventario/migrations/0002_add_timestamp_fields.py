# This migration was previously generated to add timestamp fields that already
# exist in the initial schema for Producto. Keeping it as a no-op prevents
# Django from trying to re-add the same columns during test database creation.

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('inventario', '0001_initial'),
    ]

    operations = []
