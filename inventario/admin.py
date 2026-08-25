from django.contrib import admin
from django.contrib.admin import ModelAdmin
from .models import Producto


@admin.register(Producto)
class ProductoAdmin(ModelAdmin):
    list_display = ["nombre", "proveedor", "precio_costo", "precio_venta", "stock", "activo", "categoria"]
    list_filter = ["proveedor", "activo", "categoria"]
    search_fields = ["nombre", "categoria__name", "proveedor__nombre"]
    list_editable = ["activo"]
    fieldsets = (
        ("Información del Producto", {
            "fields": ("nombre", "proveedor", "categoria", "activo")
        }),
        ("Precios", {
            "fields": ("precio_costo", "precio_venta")
        }),
        ("Stock y Descripción", {
            "fields": ("stock", "descripcion")
        }),
    )
    
    def has_add_permission(self, request):
        # Solo superusuarios y staff pueden agregar productos
        return request.user.is_superuser or request.user.is_staff
    
    def has_change_permission(self, request, obj=None):
        # Solo superusuarios y staff pueden modificar productos
        return request.user.is_superuser or request.user.is_staff
    
    def has_delete_permission(self, request, obj=None):
        # Solo superusuarios pueden eliminar productos
        return request.user.is_superuser
    
    def has_view_permission(self, request, obj=None):
        # Todos los usuarios autenticados pueden ver productos
        return request.user.is_authenticated
    
    def get_readonly_fields(self, request, obj=None):
        # Si el usuario no es staff ni superusuario, hacer todos los campos de solo lectura
        if not (request.user.is_staff or request.user.is_superuser):
            readonly_fields = []
            for field in self.model._meta.fields:
                readonly_fields.append(field.name)
            return readonly_fields
        return self.readonly_fields