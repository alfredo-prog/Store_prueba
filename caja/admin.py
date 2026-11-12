from datetime import date, datetime, time, timedelta

from django.contrib import admin
from django.db import models
from django.db.models import Count, Sum
from django.db.models.functions import TruncDate
from django.http import HttpResponse
from django.urls import path, reverse
from django.utils import timezone

from .models import Caja, MovimientoCaja


class FechaAperturaFilter(admin.SimpleListFilter):
    title = "Por fecha de apertura"
    parameter_name = "fecha_apertura_periodo"

    def lookups(self, request, model_admin):
        return (
            ("hoy", "Hoy"),
            ("ayer", "Ayer"),
            ("hace_3_dias", "Hace 3 días"),
            ("hace_7_dias", "Hace 7 días"),
            ("mes_actual", "Mes actual"),
            ("mes_anterior", "Mes anterior"),
        )

    def queryset(self, request, queryset):
        periodo = self.value()
        periodos_dia = {
            "hoy": 0,
            "ayer": 1,
            "hace_3_dias": 3,
            "hace_7_dias": 7,
        }
        if periodo in periodos_dia:
            fecha = timezone.localdate() - timedelta(days=periodos_dia[periodo])
            return queryset.filter(fecha_apertura__date=fecha)

        if periodo not in {"mes_actual", "mes_anterior"}:
            return queryset

        hoy = timezone.localdate()
        primer_dia_mes_actual = date(hoy.year, hoy.month, 1)
        if periodo == "mes_anterior":
            ultimo_dia = primer_dia_mes_actual - timedelta(days=1)
            primer_dia = date(ultimo_dia.year, ultimo_dia.month, 1)
        else:
            primer_dia = primer_dia_mes_actual
            ultimo_dia = hoy

        return queryset.filter(
            fecha_apertura__date__gte=primer_dia,
            fecha_apertura__date__lte=ultimo_dia,
        )


class MovimientoCajaInline(admin.TabularInline):
    model = MovimientoCaja
    extra = 0
    can_delete = False
    fields = ("fecha", "tipo", "metodo_pago", "categoria", "descripcion", "monto", "usuario")
    readonly_fields = fields


@admin.register(Caja)
class CajaAdmin(admin.ModelAdmin):
    change_list_template = "admin/caja/caja/change_list.html"
    inlines = (MovimientoCajaInline,)
    list_display = (
        "id",
        "fecha_apertura",
        "fecha_cierre",
        "tiempo_atencion",
        "usuario",
        "estado",
        "saldo_inicial_total",
        "total_ingresos",
        "total_egresos",
        "saldo_esperado_total",
        "resultado_bruto_total",
        "saldo_final_total",
    )
    list_filter = ("estado", FechaAperturaFilter, "usuario")
    search_fields = ("usuario__username", "observaciones")
    readonly_fields = ("fecha_apertura", "fecha_cierre")

    @admin.display(description="Tiempo abierta")
    def tiempo_atencion(self, obj):
        momento_fin = obj.fecha_cierre or timezone.now()
        duracion = momento_fin - obj.fecha_apertura
        total_segundos = max(0, int(duracion.total_seconds()))
        horas, resto = divmod(total_segundos, 3600)
        minutos = resto // 60
        estado = " (activa)" if not obj.fecha_cierre else ""
        return f"{horas} h {minutos:02d} min{estado}"

    @admin.display(description="Ingresos")
    def total_ingresos(self, obj):
        return obj.total_ingresos_efectivo + obj.total_ingresos_qr

    @admin.display(description="Egresos")
    def total_egresos(self, obj):
        return obj.total_egresos_efectivo + obj.total_egresos_qr

    @admin.display(description="Saldo esperado")
    def saldo_esperado_total(self, obj):
        return obj.saldo_esperado_efectivo + obj.saldo_esperado_qr

    @admin.display(description="Resultado bruto")
    def resultado_bruto_total(self, obj):
        return obj.resultado_bruto_total

    def get_filter_values(self, request):
        return {
            "fecha_desde": (request.GET.get("fecha_desde") or "").strip(),
            "fecha_hasta": (request.GET.get("fecha_hasta") or "").strip(),
            "usuario": (request.GET.get("usuario") or "").strip(),
        }

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        filters = self.get_filter_values(request)

        if filters["fecha_desde"]:
            try:
                fecha_desde = datetime.strptime(filters["fecha_desde"], "%Y-%m-%d").date()
                queryset = queryset.filter(fecha_apertura__date__gte=fecha_desde)
            except ValueError:
                pass

        if filters["fecha_hasta"]:
            try:
                fecha_hasta = datetime.strptime(filters["fecha_hasta"], "%Y-%m-%d").date()
                queryset = queryset.filter(fecha_apertura__date__lte=fecha_hasta)
            except ValueError:
                pass

        if filters["usuario"]:
            queryset = queryset.filter(usuario_id=filters["usuario"])

        return queryset

    def get_summary(self, queryset):
        resumen = {
            "cajas": queryset.count(),
            "apertura": 0,
            "ingresos": 0,
            "egresos": 0,
            "esperado": 0,
            "bruto": 0,
            "cierre": 0,
        }
        for caja in queryset:
            resumen["apertura"] += caja.saldo_inicial_total
            resumen["ingresos"] += self.total_ingresos(caja)
            resumen["egresos"] += self.total_egresos(caja)
            resumen["esperado"] += self.saldo_esperado_total(caja)
            resumen["bruto"] += self.resultado_bruto_total(caja)
            resumen["cierre"] += caja.saldo_final_total
        return resumen

    def get_user_choices(self):
        from django.contrib.auth import get_user_model

        return get_user_model().objects.filter(is_active=True).order_by("username")

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "exportar-pdf/",
                self.admin_site.admin_view(self.export_pdf),
                name="caja_caja_export_pdf",
            ),
        ]
        return custom_urls + urls

    def export_pdf(self, request):
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib.units import mm
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

        queryset = self.get_queryset(request).prefetch_related("movimientos")
        filters = self.get_filter_values(request)
        response = HttpResponse(content_type="application/pdf")
        response["Content-Disposition"] = (
            f'attachment; filename="reporte_cajas_{timezone.now():%Y%m%d_%H%M%S}.pdf"'
        )
        document = SimpleDocTemplate(
            response,
            pagesize=landscape(A4),
            rightMargin=10 * mm,
            leftMargin=10 * mm,
            topMargin=10 * mm,
            bottomMargin=10 * mm,
        )
        styles = getSampleStyleSheet()
        story = [Paragraph("Reporte de cajas", styles["Title"])]
        filtro_texto = []
        if filters["fecha_desde"]:
            filtro_texto.append(f"Desde: {filters['fecha_desde']}")
        if filters["fecha_hasta"]:
            filtro_texto.append(f"Hasta: {filters['fecha_hasta']}")
        if filters["usuario"]:
            usuario = queryset.first().usuario if queryset.exists() else None
            filtro_texto.append(f"Usuario: {usuario.username if usuario else filters['usuario']}")
        story.append(Paragraph(" | ".join(filtro_texto) or "Todas las cajas", styles["Normal"]))
        story.append(Spacer(1, 6 * mm))

        resumen = self.get_summary(queryset)
        resumen_data = [
            ["Cajas", "Apertura", "Ingresos", "Egresos", "Saldo esperado", "Resultado bruto", "Cierre"],
            [
                resumen["cajas"],
                f"Bs. {resumen['apertura']:.2f}",
                f"Bs. {resumen['ingresos']:.2f}",
                f"Bs. {resumen['egresos']:.2f}",
                f"Bs. {resumen['esperado']:.2f}",
                f"Bs. {resumen['bruto']:.2f}",
                f"Bs. {resumen['cierre']:.2f}",
            ],
        ]
        resumen_table = Table(resumen_data, repeatRows=1)
        resumen_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2f4154")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("PADDING", (0, 0), (-1, -1), 5),
        ]))
        story.append(resumen_table)
        story.append(Spacer(1, 8 * mm))

        for caja in queryset.order_by("-fecha_apertura"):
            cierre_texto = caja.fecha_cierre.strftime("%d/%m/%Y %H:%M") if caja.fecha_cierre else "Abierta"
            story.append(Paragraph(
                f"Caja #{caja.id} | Usuario: {caja.usuario.username if caja.usuario else 'N/A'} | "
                f"Apertura: {caja.fecha_apertura:%d/%m/%Y %H:%M} | "
                f"Cierre: {cierre_texto} | Tiempo abierta: {self.tiempo_atencion(caja)}",
                styles["Heading3"],
            ))
            caja_data = [
                ["Saldo apertura", "Ingresos", "Egresos", "Saldo esperado", "Resultado bruto", "Saldo cierre", "Tiempo abierta"],
                [
                    f"Bs. {caja.saldo_inicial_total:.2f}",
                    f"Bs. {self.total_ingresos(caja):.2f}",
                    f"Bs. {self.total_egresos(caja):.2f}",
                    f"Bs. {self.saldo_esperado_total(caja):.2f}",
                    f"Bs. {self.resultado_bruto_total(caja):.2f}",
                    f"Bs. {caja.saldo_final_total:.2f}",
                    self.tiempo_atencion(caja),
                ],
            ]
            caja_table = Table(caja_data, repeatRows=1)
            caja_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e9eef2")),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("PADDING", (0, 0), (-1, -1), 4),
            ]))
            story.append(caja_table)
            movimientos = caja.movimientos.all().order_by("fecha")
            if movimientos:
                movimientos_data = [["Fecha", "Tipo", "Método", "Categoría", "Descripción", "Monto"]]
                for movimiento in movimientos:
                    movimientos_data.append([
                        movimiento.fecha.strftime("%d/%m/%Y %H:%M"),
                        movimiento.get_tipo_display(),
                        movimiento.get_metodo_pago_display(),
                        movimiento.get_categoria_display(),
                        Paragraph(movimiento.descripcion or "", styles["Normal"]),
                        f"Bs. {movimiento.monto:.2f}",
                    ])
                movimientos_table = Table(movimientos_data, repeatRows=1, colWidths=[28 * mm, 20 * mm, 24 * mm, 24 * mm, 105 * mm, 25 * mm])
                movimientos_table.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f3f4f6")),
                    ("GRID", (0, 0), (-1, -1), 0.3, colors.grey),
                    ("FONTSIZE", (0, 0), (-1, -1), 7),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("PADDING", (0, 0), (-1, -1), 3),
                ]))
                story.append(movimientos_table)
            story.append(Spacer(1, 6 * mm))

        document.build(story)
        return response

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        filters = self.get_filter_values(request)
        extra_context.update({
            "user_choices": self.get_user_choices(),
            "filter_values": filters,
            "has_active_filters": any(filters.values()),
            "cash_summary": self.get_summary(self.get_queryset(request)),
            "export_pdf_url": reverse("admin:caja_caja_export_pdf")
            + (f"?{request.GET.urlencode()}" if request.GET else ""),
        })
        return super().changelist_view(request, extra_context=extra_context)


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
