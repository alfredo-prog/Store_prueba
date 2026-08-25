from django.contrib import admin
from .models import Cliente


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ["nombre", "email", "telefono", "direccion"]
    list_filter = ["nombre"]
    search_fields = ["nombre", "email", "telefono"]
    fieldsets = (
        ("Información Personal", {
            "fields": ("nombre", "email")
        }),
        ("Contacto", {
            "fields": ("telefono", "direccion")
        }),
    )
