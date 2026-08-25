from django.contrib import admin
from .models import Compra, DetalleCompra


class DetalleCompraInline(admin.TabularInline):
    model = DetalleCompra
    extra = 1
    fields = ["producto", "cantidad", "precio_unitario"]


@admin.register(Compra)
class CompraAdmin(admin.ModelAdmin):
    list_display = ["id", "proveedor", "fecha"]
    list_filter = ["fecha", "proveedor"]
    search_fields = ["proveedor__nombre"]
    inlines = [DetalleCompraInline]
    fieldsets = (
        ("Información de Compra", {
            "fields": ("proveedor", "fecha")
        }),
    )
    readonly_fields = ["fecha"]


@admin.register(DetalleCompra)
class DetalleCompraAdmin(admin.ModelAdmin):
    list_display = ["compra", "producto", "cantidad", "precio_unitario", "subtotal"]
    list_filter = ["compra", "producto"]
    search_fields = ["producto__nombre"]

    def subtotal(self, obj):
        return f"${obj.subtotal:.2f}"
    subtotal.short_description = "Subtotal"