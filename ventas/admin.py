from collections import defaultdict
from datetime import datetime, time, timedelta

from django.contrib import admin
from django.db.models import Count, Q, Sum
from django.utils import timezone
from .models import Venta, DetalleVenta


class DetalleVentaInline(admin.TabularInline):
    model = DetalleVenta
    extra = 1
    fields = ["producto", "cantidad", "precio_unitario", "descuento_porcentaje", "subtotal"]
    readonly_fields = ["subtotal"]


@admin.register(Venta)
class VentaAdmin(admin.ModelAdmin):
    change_list_template = "admin/ventas/venta/change_list.html"

    def usuario_display(self, obj):
        return obj.usuario.username if obj.usuario else "—"

    usuario_display.short_description = "Usuario"

    list_display = ["id", "cliente", "usuario_display", "fecha", "estado", "metodo_pago", "subtotal", "descuento", "total"]
    list_filter = ["estado", "metodo_pago", "usuario", "fecha"]
    list_per_page = 25
    search_fields = ["id", "cliente__nombre", "usuario__username", "detalles__producto__nombre"]
    inlines = [DetalleVentaInline]
    readonly_fields = ["fecha", "subtotal", "descuento", "total"]

    def lookup_allowed(self, lookup, value, request=None):
        if lookup in {"fecha_desde", "fecha_hasta", "usuario", "producto", "usuario_busqueda"}:
            return True
        return super().lookup_allowed(lookup, value, request)

    def get_filter_values(self, request):
        fecha_desde = (request.GET.get("fecha_desde") or "").strip()
        fecha_hasta = (request.GET.get("fecha_hasta") or "").strip()
        usuario_id = (request.GET.get("usuario") or "").strip()
        producto = (request.GET.get("producto") or "").strip()
        usuario_busqueda = (request.GET.get("usuario_busqueda") or "").strip()
        return {
            "fecha_desde": fecha_desde,
            "fecha_hasta": fecha_hasta,
            "usuario": usuario_id,
            "producto": producto,
            "usuario_busqueda": usuario_busqueda,
        }

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        filters = self.get_filter_values(request)

        if filters["fecha_desde"]:
            try:
                fecha_desde = datetime.strptime(filters["fecha_desde"], "%Y-%m-%d").date()
                inicio = timezone.make_aware(datetime.combine(fecha_desde, time.min), timezone.get_current_timezone())
                qs = qs.filter(fecha__gte=inicio)
            except ValueError:
                pass

        if filters["fecha_hasta"]:
            try:
                fecha_hasta = datetime.strptime(filters["fecha_hasta"], "%Y-%m-%d").date()
                fin = timezone.make_aware(datetime.combine(fecha_hasta, time.max), timezone.get_current_timezone())
                qs = qs.filter(fecha__lte=fin)
            except ValueError:
                pass

        if filters["usuario"]:
            qs = qs.filter(usuario_id=filters["usuario"])
        if filters["producto"]:
            qs = qs.filter(detalles__producto__nombre__icontains=filters["producto"])
        if filters["usuario_busqueda"]:
            qs = qs.filter(usuario__username__icontains=filters["usuario_busqueda"])

        return qs.distinct()

    def get_sales_summary(self, queryset):
        totals = queryset.aggregate(total=Sum("total"), count=Count("id"))
        daily_summary = defaultdict(lambda: {"total": 0, "count": 0})
        for fecha, total in queryset.values_list("fecha", "total"):
            fecha_dia = timezone.localtime(fecha).date() if timezone.is_aware(fecha) else fecha.date()
            daily_summary[fecha_dia]["total"] += total or 0
            daily_summary[fecha_dia]["count"] += 1

        daily_totals = [
            {
                "fecha_dia": fecha_dia,
                "total": values["total"],
                "count": values["count"],
            }
            for fecha_dia, values in sorted(daily_summary.items())
        ]

        return {
            "total": totals["total"] or 0,
            "count": totals["count"] or 0,
            "average": (totals["total"] / totals["count"]) if totals["count"] else 0,
            "daily_totals": daily_totals,
        }

    def get_user_totals(self, queryset):
        # Devuelve suma total y cantidad de ventas por usuario en el queryset dado
        return list(
            queryset.values('usuario__id', 'usuario__username')
            .annotate(total=Sum('total'), count=Count('id'))
            .order_by('-total')
        )

    def get_user_choices(self):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        return User.objects.filter(is_active=True).order_by("username")

    def changelist_view(self, request, extra_context=None):
        if extra_context is None:
            extra_context = {}

        filters = self.get_filter_values(request)
        queryset = self.get_queryset(request)

        extra_context.update({
            'user_choices': self.get_user_choices(),
            'filter_values': filters,
            'has_active_filters': any(filters.values()),
            'sales_summary': self.get_sales_summary(queryset),
            'user_totals': self.get_user_totals(queryset),
            'fecha_desde': filters['fecha_desde'],
            'fecha_hasta': filters['fecha_hasta'],
            'usuario_filter': filters['usuario'],
            'producto_filter': filters['producto'],
            'usuario_search': filters['usuario_busqueda'],
        })

        # No eliminamos los parámetros GET aquí: si se borran antes de que
        # Django construya el ChangeList, el filtro de fechas deja de aplicarse.
        return super().changelist_view(request, extra_context=extra_context)
    
    fieldsets = (
        (None, {
            'fields': ('cliente', 'metodo_pago')
        }),
        ('Información de Venta', {
            'fields': ('estado', 'fecha', 'subtotal', 'descuento', 'total'),
            'classes': ('collapse',)
        }),
        ('Detalles de Pago', {
            'fields': ('monto_recibido', 'cambio'),
            'classes': ('collapse',)
        }),
    )


class DetalleVentaFechaFiltro(admin.SimpleListFilter):
    title = "Fecha de venta"
    parameter_name = "fecha_venta"

    def lookups(self, request, model_admin):
        return [
            ("hoy", "Hoy"),
            ("ayer", "Ayer"),
            ("3_dias", "Hace 3 días"),
            ("7_dias", "Hace 1 semana"),
            ("30_dias", "Hace 1 mes"),
            ("todos", "Todos"),
        ]

    def queryset(self, request, queryset):
        if self.value() in [None, "todos"]:
            return queryset

        ahora_local = timezone.localtime(timezone.now())
        hoy = ahora_local.date()
        tz = timezone.get_current_timezone()

        if self.value() == "hoy":
            inicio = timezone.make_aware(datetime.combine(hoy, time.min), tz)
            fin = timezone.make_aware(datetime.combine(hoy, time.max), tz)
            return queryset.filter(venta__fecha__gte=inicio, venta__fecha__lte=fin)

        if self.value() == "ayer":
            fecha = hoy - timedelta(days=1)
            inicio = timezone.make_aware(datetime.combine(fecha, time.min), tz)
            fin = timezone.make_aware(datetime.combine(fecha, time.max), tz)
            return queryset.filter(venta__fecha__gte=inicio, venta__fecha__lte=fin)

        if self.value() == "3_dias":
            desde = hoy - timedelta(days=3)
            inicio = timezone.make_aware(datetime.combine(desde, time.min), tz)
            fin = timezone.make_aware(datetime.combine(hoy, time.max), tz)
            return queryset.filter(venta__fecha__gte=inicio, venta__fecha__lte=fin)

        if self.value() == "7_dias":
            desde = hoy - timedelta(days=7)
            inicio = timezone.make_aware(datetime.combine(desde, time.min), tz)
            fin = timezone.make_aware(datetime.combine(hoy, time.max), tz)
            return queryset.filter(venta__fecha__gte=inicio, venta__fecha__lte=fin)

        if self.value() == "30_dias":
            desde = hoy - timedelta(days=30)
            inicio = timezone.make_aware(datetime.combine(desde, time.min), tz)
            fin = timezone.make_aware(datetime.combine(hoy, time.max), tz)
            return queryset.filter(venta__fecha__gte=inicio, venta__fecha__lte=fin)

        return queryset


@admin.register(DetalleVenta)
class DetalleVentaAdmin(admin.ModelAdmin):
    list_display = ["id", "venta", "venta_usuario", "venta_fecha", "producto", "cantidad", "precio_unitario", "descuento_porcentaje", "subtotal"]
    list_filter = ["venta__usuario", DetalleVentaFechaFiltro]
    search_fields = ["venta__id", "venta__usuario__username"]
    readonly_fields = ["subtotal"]

    def venta_usuario(self, obj):
        return obj.venta.usuario.username if obj.venta.usuario else "—"
    venta_usuario.short_description = "Usuario"
    
    def venta_fecha(self, obj):
        if not obj.venta.fecha:
            return "—"
        return timezone.localtime(obj.venta.fecha).strftime("%d/%m/%Y %H:%M")
    venta_fecha.short_description = "Fecha Venta"