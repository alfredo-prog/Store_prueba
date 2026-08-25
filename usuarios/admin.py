from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Usuario


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ("Información adicional", {"fields": ("telefono", "direccion")}),
    )
    list_display = ["username", "email", "first_name", "last_name", "telefono", "is_active"]
    list_filter = UserAdmin.list_filter + ("is_active",)
