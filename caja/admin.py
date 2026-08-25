from datetime import datetime, time, timedelta

from django.contrib import admin
from django.db import models
from django.db.models import Count, Sum
from django.db.models.functions import TruncDate
from django.utils import timezone

from .models import Caja, MovimientoCaja


@admin.register(Caja)
class CajaAdmin(admin.ModelAdmin):
    list_display = ("id", "fecha_apertura", "fecha_cierre", "saldo_inicial_total", "saldo_final_total", "usuario", "estado")
    list_filter = ("estado", "fecha_apertura", "usuario")
    search_fields = ("usuario__username", "observaciones")
    readonly_fields = ("fecha_apertura", "fecha_cierre")


@admin.register(MovimientoCaja)
class MovimientoCajaAdmin(admin.ModelAdmin):
    change_list_template = "admin/caja/movimientocaja/change_list.html"
    list_display = ("id", "caja", "tipo", "metodo_pago", "descripcion", "monto", "fecha", "usuario")
    list_filter = ("tipo", "metodo_pago", "categoria", "fecha")
    search_fields = ("descripcion", "referencia", "caja__id")
    readonly_fields = ("fecha",)

    def get_filter_values(self, request):
        fecha_desde = (request.GET.get("fecha_desde") or "").strip()
        fecha_hasta = (request.GET.get("fecha_hasta") or "").strip()
        usuario_id = (request.GET.get("usuario") or "").strip()
        tipo = (request.GET.get("tipo") or "").strip()
        categoria = (request.GET.get("categoria") or "").strip()
        return {
            "fecha_desde": fecha_desde,
            "fecha_hasta": fecha_hasta,
            "usuario": usuario_id,
            "tipo": tipo,
            "categoria": categoria,
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

        if filters["tipo"]:
            qs = qs.filter(tipo=filters["tipo"])

        if filters["categoria"]:
            qs = qs.filter(categoria=filters["categoria"])

        return qs

    def get_user_choices(self):
        from django.contrib.auth import get_user_model

        User = get_user_model()
        return User.objects.filter(is_active=True).order_by("username")

    def get_summary(self, queryset):
        totals = queryset.aggregate(total=Sum("monto"), count=Count("id"))
        ingresos = queryset.filter(tipo="INGRESO").aggregate(total=Sum("monto"))["total"] or 0
        egresos = queryset.filter(tipo="EGRESO").aggregate(total=Sum("monto"))["total"] or 0
        daily = list(
            queryset.annotate(fecha_dia=TruncDate("fecha"))
            .values("fecha_dia")
            .annotate(
                ingresos=Sum("monto", filter=models.Q(tipo="INGRESO")),
                egresos=Sum("monto", filter=models.Q(tipo="EGRESO")),
                count=Count("id"),
            )
            .order_by("fecha_dia")
        )
        return {
            "total": totals["total"] or 0,
            "count": totals["count"] or 0,
            "ingresos": ingresos,
            "egresos": egresos,
            "saldo": ingresos - egresos,
            "daily": daily,
        }

    def changelist_view(self, request, extra_context=None):
        if extra_context is None:
            extra_context = {}

        filters = self.get_filter_values(request)
        queryset = self.get_queryset(request)

        extra_context.update(
            {
                "user_choices": self.get_user_choices(),
                "filter_values": filters,
                "has_active_filters": any(filters.values()),
                "cash_summary": self.get_summary(queryset),
                "category_choices": MovimientoCaja.CATEGORIA_CHOICES,
            }
        )
        return super().changelist_view(request, extra_context=extra_context)
