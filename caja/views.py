from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, Q
from django.utils import timezone
from django.http import JsonResponse
from .models import Caja, MovimientoCaja
from .forms import AperturaCajaForm, MovimientoCajaForm, CierreCajaForm
from datetime import datetime, date


@login_required
def dashboard_caja(request):
    """Dashboard principal de caja"""
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')

    if request.user.is_staff or request.user.is_superuser:
        cajas_qs = Caja.objects.all()
        caja_abierta = Caja.objects.filter(estado='ABIERTA').order_by('-fecha_apertura').first()
    else:
        cajas_qs = Caja.objects.filter(usuario=request.user)
        caja_abierta = Caja.objects.filter(
            usuario=request.user,
            estado='ABIERTA'
        ).first()

    if fecha_inicio:
        cajas_qs = cajas_qs.filter(fecha_apertura__date__gte=fecha_inicio)
    if fecha_fin:
        cajas_qs = cajas_qs.filter(fecha_apertura__date__lte=fecha_fin)
    
    # Últimas cajas cerradas
    ultimas_cajas = cajas_qs.filter(
        estado='CERRADA'
    ).order_by('-fecha_cierre')[:20]
    
    # Movimientos recientes
    if caja_abierta:
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
