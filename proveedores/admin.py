from django.contrib import admin
from .models import Proveedor


@admin.register(Proveedor)
class ProveedorAdmin(admin.ModelAdmin):
    list_display = ["nombre", "email", "telefono", "direccion"]
    list_filter = ["nombre"]
    search_fields = ["nombre", "email", "telefono"]
    fieldsets = (
        ("Información Empresa", {
            "fields": ("nombre", "email")
        }),
        ("Contacto", {
            "fields": ("telefono", "direccion")
        }),
    )