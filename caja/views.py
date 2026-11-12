from decimal import Decimal
from datetime import datetime, date, time
import calendar

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, Q
from django.utils import timezone
from django.http import JsonResponse
from django.contrib.auth import get_user_model
from .models import Caja, MovimientoCaja
from .forms import AperturaCajaForm, MovimientoCajaForm, CierreCajaForm


def _rango_fechas_local(fecha_inicio, fecha_fin):
    """Devuelve un rango datetime consistente con la zona horaria local."""
    fecha_inicio_date = fecha_inicio if isinstance(fecha_inicio, date) else datetime.strptime(fecha_inicio, '%Y-%m-%d').date()
    fecha_fin_date = fecha_fin if isinstance(fecha_fin, date) else datetime.strptime(fecha_fin, '%Y-%m-%d').date()

    tz = timezone.get_current_timezone()
    inicio_dt = timezone.make_aware(datetime.combine(fecha_inicio_date, time.min), tz)
    fin_dt = timezone.make_aware(datetime.combine(fecha_fin_date, time.max), tz)
    return inicio_dt, fin_dt


@login_required
def dashboard_caja(request):
    """Dashboard principal de caja"""
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')
    usuario_id = request.GET.get('usuario')
    hoy = timezone.localdate()
    mes_minimo = hoy.month - 2
    anio_minimo = hoy.year
    if mes_minimo <= 0:
        mes_minimo += 12
        anio_minimo -= 1
    ultimo_dia_mes = calendar.monthrange(anio_minimo, mes_minimo)[1]
    fecha_minima = date(anio_minimo, mes_minimo, min(hoy.day, ultimo_dia_mes))

    if request.user.is_staff or request.user.is_superuser:
        cajas_qs = Caja.objects.all()
        caja_abierta = Caja.objects.filter(estado='ABIERTA').order_by('-fecha_apertura').first()
        usuarios = get_user_model().objects.filter(is_active=True).order_by('username')
        if usuario_id:
            cajas_qs = cajas_qs.filter(usuario_id=usuario_id)
            caja_abierta = Caja.objects.filter(
                usuario_id=usuario_id,
                estado='ABIERTA'
            ).order_by('-fecha_apertura').first()
    else:
        cajas_qs = Caja.objects.filter(usuario=request.user)
        caja_abierta = Caja.objects.filter(
            usuario=request.user,
            estado='ABIERTA'
        ).first()
        usuarios = get_user_model().objects.none()

    if fecha_inicio:
        try:
            fecha_inicio_date = datetime.strptime(fecha_inicio, '%Y-%m-%d').date()
            fecha_inicio = max(fecha_inicio_date, fecha_minima).isoformat()
        except ValueError:
            fecha_inicio = fecha_minima.isoformat()
    else:
        fecha_inicio = fecha_minima.isoformat()

    if fecha_fin:
        try:
            fecha_fin_date = datetime.strptime(fecha_fin, '%Y-%m-%d').date()
            fecha_fin = min(fecha_fin_date, hoy).isoformat()
        except ValueError:
            fecha_fin = hoy.isoformat()
    else:
        fecha_fin = hoy.isoformat()

    if fecha_inicio:
        inicio_dt, _ = _rango_fechas_local(fecha_inicio, fecha_fin or hoy.isoformat())
        cajas_qs = cajas_qs.filter(fecha_apertura__gte=inicio_dt)
    if fecha_fin:
        _, fin_dt = _rango_fechas_local(fecha_inicio or fecha_minima.isoformat(), fecha_fin)
        cajas_qs = cajas_qs.filter(fecha_apertura__lte=fin_dt)

    # Últimas cajas cerradas
    ultimas_cajas = cajas_qs.filter(
        estado='CERRADA'
    ).order_by('-fecha_cierre')[:20]

    movimientos_rango = MovimientoCaja.objects.all()
    if request.user.is_staff or request.user.is_superuser:
        movimientos_rango = movimientos_rango.all()
        if usuario_id:
            movimientos_rango = movimientos_rango.filter(caja__usuario_id=usuario_id)
    else:
        movimientos_rango = movimientos_rango.filter(caja__usuario=request.user)

    if fecha_inicio:
        inicio_dt, _ = _rango_fechas_local(fecha_inicio, fecha_fin or hoy.isoformat())
        movimientos_rango = movimientos_rango.filter(fecha__gte=inicio_dt)
    if fecha_fin:
        _, fin_dt = _rango_fechas_local(fecha_inicio or fecha_minima.isoformat(), fecha_fin)
        movimientos_rango = movimientos_rango.filter(fecha__lte=fin_dt)

    ingresos = movimientos_rango.filter(tipo='INGRESO').aggregate(total=Sum('monto'))['total'] or Decimal('0.00')
    egresos = movimientos_rango.filter(tipo='EGRESO').aggregate(total=Sum('monto'))['total'] or Decimal('0.00')
    resumen_rango = {
        'ingresos': ingresos,
        'egresos': egresos,
        'saldo': ingresos - egresos,
        'cantidad_movimientos': movimientos_rango.count(),
        'cantidad_cajas': movimientos_rango.values('caja_id').distinct().count(),
    }

    # Movimientos recientes: si hay filtro por usuario, mostrar el historial
    # del usuario seleccionado aunque su caja esté cerrada. No se debe filtrar
    # después de aplicar el slice porque Django lanza TypeError.
    if usuario_id:
        movimientos_recientes = MovimientoCaja.objects.filter(
            caja__usuario_id=usuario_id
        )
        if fecha_inicio:
            inicio_dt, _ = _rango_fechas_local(fecha_inicio, fecha_fin or hoy.isoformat())
            movimientos_recientes = movimientos_recientes.filter(fecha__gte=inicio_dt)
        if fecha_fin:
            _, fin_dt = _rango_fechas_local(fecha_inicio or fecha_minima.isoformat(), fecha_fin)
            movimientos_recientes = movimientos_recientes.filter(fecha__lte=fin_dt)
        movimientos_recientes = movimientos_recientes.order_by('-fecha')[:10]
    elif caja_abierta:
        movimientos_recientes = MovimientoCaja.objects.filter(
            caja=caja_abierta
        ).order_by('-fecha')[:10]
    else:
        movimientos_recientes = MovimientoCaja.objects.none()

    context = {
        'caja_abierta': caja_abierta,
        'ultimas_cajas': ultimas_cajas,
        'movimientos_recientes': movimientos_recientes,
        'fecha_inicio': fecha_inicio,
        'fecha_fin': fecha_fin,
        'fecha_minima': fecha_minima.isoformat(),
        'fecha_maxima': hoy.isoformat(),
        'usuarios': usuarios,
        'usuario_seleccionado': usuario_id,
        'resumen_rango': resumen_rango,
    }
    return render(request, 'caja/dashboard.html', context)


@login_required
def abrir_caja(request):
    """Abrir una nueva caja"""
    # Verificar si ya hay una caja abierta
    caja_abierta = Caja.objects.filter(
        usuario=request.user,
        estado='ABIERTA'
    ).first()
    
    if caja_abierta:
        messages.warning(request, 'Ya tienes una caja abierta. Debes cerrarla antes de abrir una nueva.')
        return redirect('caja:dashboard')
    
    if request.method == 'POST':
        form = AperturaCajaForm(request.POST, user=request.user)
        if form.is_valid():
            caja = form.save(commit=False)
            caja.usuario = request.user
            caja.save()
            
            messages.success(request, f'✅ Caja #{caja.id} abierta correctamente')
            return redirect('caja:dashboard')
    else:
        form = AperturaCajaForm(user=request.user)
    
    return render(request, 'caja/abrir_caja.html', {'form': form})


@login_required
def cerrar_caja(request, caja_id):
    """Cerrar una caja existente"""
    caja = get_object_or_404(Caja, id=caja_id, usuario=request.user, estado='ABIERTA')
    
    if request.method == 'POST':
        form = CierreCajaForm(request.POST)
        if form.is_valid():
            saldo_final_efectivo = form.cleaned_data['saldo_final_efectivo']
            saldo_final_qr = form.cleaned_data['saldo_final_qr']
            observaciones = form.cleaned_data['observaciones']
            
            caja.cerrar_caja(saldo_final_efectivo, saldo_final_qr, observaciones)
            
            messages.success(request, f'✅ Caja #{caja.id} cerrada correctamente')
            return redirect('caja:dashboard')
    else:
        # Pre-calcular saldos esperados
        form = CierreCajaForm(initial={
            'saldo_final_efectivo': caja.saldo_esperado_efectivo,
            'saldo_final_qr': caja.saldo_esperado_qr,
        })
    
    context = {
        'caja': caja,
        'form': form,
        'saldo_esperado_efectivo': caja.saldo_esperado_efectivo,
        'saldo_esperado_qr': caja.saldo_esperado_qr,
    }
    return render(request, 'caja/cerrar_caja.html', context)


@login_required
def agregar_movimiento(request):
    """Agregar un movimiento a la caja abierta"""
    # Buscar caja abierta
    caja_abierta = Caja.objects.filter(
        usuario=request.user,
        estado='ABIERTA'
    ).first()
    
    if not caja_abierta:
        messages.error(request, 'No tienes una caja abierta. Debes abrir una caja primero.')
        return redirect('caja:dashboard')
    
    if request.method == 'POST':
        form = MovimientoCajaForm(request.POST, user=request.user)
        if form.is_valid():
            movimiento = form.save(commit=False)
            movimiento.caja = caja_abierta
            movimiento.usuario = request.user
            movimiento.save()
            
            messages.success(request, f'✅ Movimiento registrado correctamente')
            return redirect('caja:dashboard')
    else:
        # Pre-establecer tipo según el parámetro GET
        tipo = request.GET.get('tipo', 'INGRESO')
        form = MovimientoCajaForm(initial={'tipo': tipo}, user=request.user)
    
    return render(request, 'caja/agregar_movimiento.html', {
        'form': form,
        'caja': caja_abierta
    })


@login_required
def traspaso_caja(request):
    """Registrar un traspaso entre efectivo y QR de forma separada de ventas."""
    caja = Caja.objects.filter(usuario=request.user, estado='ABIERTA').first()

    if not caja:
        messages.error(request, 'No tienes una caja abierta. Debes abrir una caja primero.')
        return redirect('caja:dashboard')

    origen = request.GET.get('origen', 'QR').upper()
    destino = request.GET.get('destino', 'EFECTIVO').upper()

    if request.method == 'POST':
        origen = request.POST.get('origen', origen).upper()
        destino = request.POST.get('destino', destino).upper()
        monto = request.POST.get('monto')
        descripcion = request.POST.get('descripcion', '').strip() or f'Traspaso {origen} a {destino}'

        try:
            monto_decimal = Decimal(str(monto))
        except Exception:
            messages.error(request, 'El monto del traspaso es inválido.')
            return redirect('caja:dashboard')

        if monto_decimal <= 0:
            messages.error(request, 'El monto debe ser mayor a cero.')
            return redirect('caja:dashboard')

        MovimientoCaja.objects.create(
            caja=caja,
            tipo='INGRESO',
            metodo_pago=destino,
            categoria='TRASPASO',
            descripcion=descripcion,
            monto=monto_decimal,
            usuario=request.user,
            referencia=f'TRASPA-{origen}-{destino}'
        )

        MovimientoCaja.objects.create(
            caja=caja,
            tipo='EGRESO',
            metodo_pago=origen,
            categoria='TRASPASO',
            descripcion=descripcion,
            monto=monto_decimal,
            usuario=request.user,
            referencia=f'TRASPA-{origen}-{destino}'
        )

        messages.success(
            request,
            f'✅ Traspaso registrado: {origen} → {destino}. '
            f'Ingreso en {destino}: Qr {monto_decimal:.2f} | '
            f'Egreso en {origen}: Qr {monto_decimal:.2f}'
        )
        return redirect('caja:dashboard')

    if origen not in ['QR', 'EFECTIVO'] or destino not in ['QR', 'EFECTIVO']:
        messages.error(request, 'El traspaso solo puede ser entre QR y Efectivo.')
        return redirect('caja:dashboard')

    if origen == destino:
        messages.error(request, 'El origen y destino del traspaso deben ser distintos.')
        return redirect('caja:dashboard')

    context = {
        'caja': caja,
        'origen': origen,
        'destino': destino,
    }
    return render(request, 'caja/traspaso_caja.html', context)


@login_required
def detalle_caja(request, caja_id):
    """Ver detalle de una caja específica"""
    caja = get_object_or_404(Caja, id=caja_id)
    movimientos = caja.movimientos.all().order_by('-fecha')
    
    # Resumen por método de pago
    resumen_efectivo = {
        'saldo_inicial': caja.saldo_inicial_efectivo,
        'ingresos': caja.total_ingresos_efectivo,
        'egresos': caja.total_egresos_efectivo,
        'saldo_esperado': caja.saldo_esperado_efectivo,
        'saldo_final': caja.saldo_final_efectivo,
        'diferencia': caja.diferencia_efectivo,
    }
    
    resumen_qr = {
        'saldo_inicial': caja.saldo_inicial_qr,
        'ingresos': caja.total_ingresos_qr,
        'egresos': caja.total_egresos_qr,
        'saldo_esperado': caja.saldo_esperado_qr,
        'saldo_final': caja.saldo_final_qr,
        'diferencia': caja.diferencia_qr,
    }
    
    context = {
        'caja': caja,
        'movimientos': movimientos,
        'resumen_efectivo': resumen_efectivo,
        'resumen_qr': resumen_qr,
    }
    return render(request, 'caja/detalle_caja.html', context)


@login_required
def reporte_caja(request):
    """Mostrar para impresión solo los resúmenes de caja filtrados."""
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')
    usuario_id = request.GET.get('usuario')
    hoy = timezone.localdate()
    mes_minimo = hoy.month - 2
    anio_minimo = hoy.year
    if mes_minimo <= 0:
        mes_minimo += 12
        anio_minimo -= 1
    ultimo_dia_mes = calendar.monthrange(anio_minimo, mes_minimo)[1]
    fecha_minima = date(anio_minimo, mes_minimo, min(hoy.day, ultimo_dia_mes))

    if request.user.is_staff or request.user.is_superuser:
        cajas_qs = Caja.objects.all()
        caja_abierta = Caja.objects.filter(estado='ABIERTA').order_by('-fecha_apertura').first()
        if usuario_id:
            cajas_qs = cajas_qs.filter(usuario_id=usuario_id)
            caja_abierta = Caja.objects.filter(
                usuario_id=usuario_id, estado='ABIERTA'
            ).order_by('-fecha_apertura').first()
    else:
        cajas_qs = Caja.objects.filter(usuario=request.user)
        caja_abierta = Caja.objects.filter(
            usuario=request.user, estado='ABIERTA'
        ).first()
        usuario_id = str(request.user.id)

    try:
        fecha_inicio_date = datetime.strptime(fecha_inicio, '%Y-%m-%d').date() if fecha_inicio else fecha_minima
    except (TypeError, ValueError):
        fecha_inicio_date = fecha_minima
    try:
        fecha_fin_date = datetime.strptime(fecha_fin, '%Y-%m-%d').date() if fecha_fin else hoy
    except (TypeError, ValueError):
        fecha_fin_date = hoy
    fecha_inicio_date = max(fecha_inicio_date, fecha_minima)
    fecha_fin_date = min(fecha_fin_date, hoy)
    fecha_inicio = fecha_inicio_date.isoformat()
    fecha_fin = fecha_fin_date.isoformat()

    inicio_dt, fin_dt = _rango_fechas_local(fecha_inicio, fecha_fin)
    cajas_qs = cajas_qs.filter(
        fecha_apertura__gte=inicio_dt,
        fecha_apertura__lte=fin_dt,
    )
    ultimas_cajas = cajas_qs.filter(estado='CERRADA').order_by('-fecha_cierre')[:20]

    movimientos_rango = MovimientoCaja.objects.filter(
        fecha__gte=inicio_dt,
        fecha__lte=fin_dt,
    )
    if request.user.is_staff or request.user.is_superuser:
        if usuario_id:
            movimientos_rango = movimientos_rango.filter(caja__usuario_id=usuario_id)
    else:
        movimientos_rango = movimientos_rango.filter(caja__usuario=request.user)

    ingresos = movimientos_rango.filter(tipo='INGRESO').aggregate(total=Sum('monto'))['total'] or Decimal('0.00')
    egresos = movimientos_rango.filter(tipo='EGRESO').aggregate(total=Sum('monto'))['total'] or Decimal('0.00')
    resumen_rango = {
        'ingresos': ingresos,
        'egresos': egresos,
        'saldo': ingresos - egresos,
        'cantidad_movimientos': movimientos_rango.count(),
        'cantidad_cajas': movimientos_rango.values('caja_id').distinct().count(),
    }

    response = render(request, 'caja/reporte_caja.html', {
        'caja_abierta': caja_abierta,
        'ultimas_cajas': ultimas_cajas,
        'resumen_rango': resumen_rango,
        'fecha_inicio': fecha_inicio,
        'fecha_fin': fecha_fin,
        'usuario_seleccionado': usuario_id,
    })
    if request.GET.get('descargar') == '1':
        response['Content-Disposition'] = 'attachment; filename="resumen_caja.html"'
    return response


@login_required
def eliminar_movimiento(request, movimiento_id):
    """Eliminar un movimiento"""
    movimiento = get_object_or_404(MovimientoCaja, id=movimiento_id)
    
    # Verificar que la caja esté abierta y sea del usuario
    if movimiento.caja.usuario != request.user or movimiento.caja.estado != 'ABIERTA':
        messages.error(request, 'No puedes eliminar este movimiento.')
        return redirect('caja:dashboard')
    
    if request.method == 'POST':
        descripcion = f"{movimiento.tipo}: {movimiento.descripcion}"
        movimiento.delete()
        messages.warning(request, f'🗑️ Movimiento eliminado: {descripcion}')
        return redirect('caja:dashboard')
    
    return render(request, 'caja/eliminar_movimiento.html', {'movimiento': movimiento})


@login_required
def api_caja_status(request):
    """API para obtener estado actual de la caja"""
    caja_abierta = Caja.objects.filter(
        usuario=request.user,
        estado='ABIERTA'
    ).first()
    
    if caja_abierta:
        data = {
            'caja_abierta': True,
            'caja_id': caja_abierta.id,
            'saldo_inicial_efectivo': float(caja_abierta.saldo_inicial_efectivo),
            'saldo_inicial_qr': float(caja_abierta.saldo_inicial_qr),
            'total_ingresos_efectivo': float(caja_abierta.total_ingresos_efectivo),
            'total_ingresos_qr': float(caja_abierta.total_ingresos_qr),
            'total_egresos_efectivo': float(caja_abierta.total_egresos_efectivo),
            'total_egresos_qr': float(caja_abierta.total_egresos_qr),
            'saldo_esperado_efectivo': float(caja_abierta.saldo_esperado_efectivo),
            'saldo_esperado_qr': float(caja_abierta.saldo_esperado_qr),
        }
    else:
        data = {'caja_abierta': False}
    
    return JsonResponse(data)


def lista_cajas(request):
    cajas = Caja.objects.all()
    return render(request, "caja/lista_cajas.html", {"cajas": cajas})


def lista_movimientos(request, caja_id):
    movimientos = MovimientoCaja.objects.filter(caja_id=caja_id)
    return render(request, "caja/lista_movimientos.html", {"movimientos": movimientos})
