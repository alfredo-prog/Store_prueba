from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.db import models, transaction
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Count, Sum
from django.db.models.functions import TruncDate
from django.contrib.auth import get_user_model
from datetime import datetime, time
import json
from decimal import Decimal
from .models import Venta, DetalleVenta, Proforma, ProformaItem
from inventario.models import Producto
from clientes.models import Cliente
from .forms import VentaForm, DetalleVentaForm


def get_pos_context():
    productos = Producto.objects.filter(activo=True)
    clientes = Cliente.objects.all()
    productos_data = []
    for producto in productos:
        productos_data.append({
            'id': producto.id,
            'nombre': producto.nombre or '',
            'precio_venta': float(producto.precio_venta or 0),
            'stock': int(producto.stock or 0),
            'codigo': producto.codigo or ''
        })

    return {
        'productos': productos,
        'clientes': clientes,
        'productos_json': json.dumps(productos_data, ensure_ascii=False)
    }


def sincronizar_stock_catalogo(producto_inventario):
    """Sincroniza el stock entre inventario y catálogo"""
    try:
        from inventario.models import Producto
        producto_catalogo = Producto.objects.filter(codigo=producto_inventario.codigo).first()
        if producto_catalogo:
            producto_catalogo.stock = producto_inventario.stock
            producto_catalogo.save(update_fields=['stock'])
            print(f"✅ Stock sincronizado desde vista: {producto_inventario.nombre} -> {producto_inventario.stock}")
            return True
        else:
            print(f"⚠️ Producto no encontrado en catálogo: {producto_inventario.codigo}")
            return False
    except Exception as e:
        print(f"❌ Error sincronizando catálogo desde vista: {e}")
        return False


def nueva_venta(request):
    """Vista para procesar el formulario del POS"""
    if request.method == 'POST':
        is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest'
        try:
            with transaction.atomic():
                # Obtener datos del formulario
                productos_nombres = request.POST.getlist('producto[]')
                cantidades = request.POST.getlist('cantidad[]')
                precios = request.POST.getlist('precio[]')
                subtotales = request.POST.getlist('subtotal[]')
                
                # Validar que haya productos
                if not productos_nombres or not cantidades:
                    msg = 'Debe agregar al menos un producto'
                    if is_ajax:
                        return JsonResponse({'success': False, 'message': msg})
                    messages.error(request, msg)
                    return render(request, 'ventas/pos_venta.html', get_pos_context())
                
                # Obtener datos adicionales
                cliente_id = request.POST.get('cliente')
                metodo_pago = request.POST.get('metodo_pago')
                descuento = float(request.POST.get('descuento', 0))
                
                # Validar cliente
                cliente = None
                if cliente_id:
                    try:
                        cliente = Cliente.objects.get(id=cliente_id)
                    except Cliente.DoesNotExist:
                        msg = 'El cliente seleccionado no existe'
                        if is_ajax:
                            return JsonResponse({'success': False, 'message': msg})
                        messages.error(request, msg)
                        return render(request, 'ventas/pos_venta.html', get_pos_context())
                
                # Validar método de pago
                if not metodo_pago:
                    msg = 'Debe seleccionar un método de pago'
                    if is_ajax:
                        return JsonResponse({'success': False, 'message': msg})
                    messages.error(request, msg)
                    return render(request, 'ventas/pos_venta.html', get_pos_context())
                
                # Crear la venta principal
                venta = Venta.objects.create(
                    cliente=cliente,
                    usuario=request.user,
                    metodo_pago=metodo_pago,
                    descuento=Decimal(str(descuento)),
                    estado='BORRADOR'
                )

                total = Decimal('0')
                items_procesados = 0
                
                # Procesar cada item
                for i, (producto_nombre, cantidad, precio, subtotal) in enumerate(zip(productos_nombres, cantidades, precios, subtotales)):
                    if producto_nombre and cantidad and precio:
                        try:
                            producto = Producto.objects.filter(nombre__icontains=producto_nombre, activo=True).first()
                            if not producto:
                                msg = f'Producto "{producto_nombre}" no encontrado'
                                if is_ajax:
                                    return JsonResponse({'success': False, 'message': msg})
                                messages.error(request, msg)
                                continue
                            cantidad_decimal = Decimal(str(cantidad))
                            precio_decimal = Decimal(str(precio))
                            subtotal_decimal = Decimal(str(subtotal))
                            if producto.stock < cantidad_decimal:
                                msg = f'Stock insuficiente para {producto.nombre}. Disponible: {producto.stock}, Solicitado: {cantidad}'
                                if is_ajax:
                                    return JsonResponse({'success': False, 'message': msg})
                                messages.error(request, msg)
                                continue
                            DetalleVenta.objects.create(
                                venta=venta,
                                producto=producto,
                                cantidad=cantidad_decimal,
                                precio_unitario=precio_decimal,
                                descuento_porcentaje=Decimal('0')
                            )
                            producto.stock -= cantidad_decimal
                            producto.save(update_fields=['stock'])
                            sincronizar_stock_catalogo(producto)
                            total += subtotal_decimal
                            items_procesados += 1
                        except Exception as e:
                            print(f"Error procesando item {i}: {e}")
                            if is_ajax:
                                return JsonResponse({'success': False, 'message': f'Error procesando {producto_nombre}: {str(e)}'})
                            messages.error(request, f'Error procesando {producto_nombre}: {str(e)}')
                            continue
                
                # Confirmar la venta si se procesaron items
                if items_procesados > 0:
                    venta.subtotal = total
                    venta.descuento = total * (Decimal(str(descuento)) / Decimal('100'))
                    venta.total = total - venta.descuento
                    if metodo_pago == 'EFECTIVO':
                        monto_efectivo = Decimal(str(request.POST.get('monto_efectivo', '0') or '0'))
                        if monto_efectivo < venta.total:
                            msg = 'El monto recibido en efectivo debe ser mayor o igual al total.'
                            if is_ajax:
                                return JsonResponse({'success': False, 'message': msg})
                            messages.error(request, msg)
                            venta.delete()
                            return render(request, 'ventas/pos_venta.html', get_pos_context())
                        venta.monto_recibido = monto_efectivo
                        venta.cambio = monto_efectivo - venta.total
                    else:
                        venta.monto_recibido = None
                        venta.cambio = None
                    venta._stock_procesado = True
                    venta.estado = 'CONFIRMADO'
                    venta.save()
                    crear_movimiento_venta(venta, request.user)
                    msg = f'Venta #{venta.id} procesada exitosamente con {items_procesados} productos'
                    if is_ajax:
                        return JsonResponse({'success': True, 'message': msg, 'venta_id': venta.id})
                    messages.success(request, msg)
                    return redirect('ventas:lista')
                else:
                    venta.delete()
                    msg = 'No se pudo procesar ningún producto. Verifique los datos.'
                    if is_ajax:
                        return JsonResponse({'success': False, 'message': msg})
                    messages.error(request, msg)
                    return render(request, 'ventas/pos_venta.html', get_pos_context())
                    
        except Exception as e:
            print(f"❌ Error en nueva_venta: {e}")
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'message': f'Error al procesar la venta: {str(e)}'})
            messages.error(request, f'Error al procesar la venta: {str(e)}')
            return render(request, 'ventas/pos_venta.html', get_pos_context())
    
    # GET: mostrar el formulario
    productos = Producto.objects.filter(activo=True)
    clientes = Cliente.objects.all()
    
    # Preparar datos JSON para el JavaScript
    productos_data = []
    for producto in productos:
        productos_data.append({
            'id': producto.id,
            'nombre': producto.nombre or '',
            'precio_venta': float(producto.precio_venta or 0),
            'stock': int(producto.stock or 0),
            'codigo': producto.codigo or ''
        })
    
    context = {
        'productos': productos,
        'clientes': clientes,
        'productos_json': json.dumps(productos_data, ensure_ascii=False)
    }
    
    return render(request, 'ventas/pos_venta.html', context)


def lista(request):
    """Vista para mostrar el historial de ventas con estadísticas"""
    # Los administradores ven todas las ventas; los usuarios normales solo ven las suyas.
    if request.user.is_staff or request.user.is_superuser:
        ventas = Venta.objects.all()
    else:
        ventas = Venta.objects.filter(usuario=request.user)

    ventas = ventas.order_by('-fecha')

    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')
    estado = request.GET.get('estado')
    metodo_pago = request.GET.get('metodo_pago')
    buscar = request.GET.get('buscar')
    usuario_id = request.GET.get('usuario')

    if fecha_inicio:
        try:
            fecha_inicio_date = datetime.strptime(fecha_inicio, '%Y-%m-%d').date()
            fecha_inicio_dt = timezone.make_aware(datetime.combine(fecha_inicio_date, time.min), timezone.get_current_timezone())
            ventas = ventas.filter(fecha__gte=fecha_inicio_dt)
        except ValueError:
            pass
    if fecha_fin:
        try:
            fecha_fin_date = datetime.strptime(fecha_fin, '%Y-%m-%d').date()
            fecha_fin_dt = timezone.make_aware(datetime.combine(fecha_fin_date, time.max), timezone.get_current_timezone())
            ventas = ventas.filter(fecha__lte=fecha_fin_dt)
        except ValueError:
            pass
    if estado:
        ventas = ventas.filter(estado=estado)
    if metodo_pago:
        ventas = ventas.filter(metodo_pago=metodo_pago)
    if usuario_id and (request.user.is_staff or request.user.is_superuser):
        ventas = ventas.filter(usuario_id=usuario_id)
    if buscar:
        ventas = ventas.filter(
            models.Q(id__icontains=buscar) |
            models.Q(cliente__nombre__icontains=buscar)
        )

    # Calcular estadísticas
    
    hoy = timezone.localdate()
    hoy_inicio = timezone.make_aware(datetime.combine(hoy, time.min), timezone.get_current_timezone())
    hoy_fin = timezone.make_aware(datetime.combine(hoy, time.max), timezone.get_current_timezone())
    ventas_hoy = ventas.filter(fecha__gte=hoy_inicio, fecha__lte=hoy_fin)
    
    # Calcular totales
    total_ventas = ventas.aggregate(
        total=Sum('total')
    )['total'] or 0
    
    total_ventas_hoy = ventas_hoy.aggregate(
        total=Sum('total')
    )['total'] or 0
    
    # Calcular conteo de ventas hoy
    count_ventas_hoy = ventas_hoy.count()
    
    # Calcular promedio entre ventas confirmadas del conjunto filtrado
    ventas_confirmadas = ventas.filter(estado='CONFIRMADO')
    count_ventas = ventas_confirmadas.count()
    promedio_ventas = total_ventas / count_ventas if count_ventas > 0 else 0
    
    # Totales por día del rango filtrado
    daily_totals = list(
        ventas.annotate(fecha_dia=TruncDate('fecha'))
        .values('fecha_dia')
        .annotate(total=Sum('total'), count=Count('id'))
        .order_by('fecha_dia')
    )

    paginator = Paginator(ventas, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    ventas = page_obj
    is_paginated = paginator.num_pages > 1
    ventas_count = paginator.count
    
    usuarios = None
    if request.user.is_staff or request.user.is_superuser:
        Usuario = get_user_model()
        usuarios = Usuario.objects.filter(is_active=True).order_by('username')

    query_params = request.GET.copy()
    if 'page' in query_params:
        query_params.pop('page')
    query_string = query_params.urlencode()

    context = {
        'ventas': ventas,
        'total_ventas': total_ventas,
        'ventas_hoy': ventas_hoy,
        'total_ventas_hoy': total_ventas_hoy,
        'count_ventas_hoy': count_ventas_hoy,
        'promedio_ventas': promedio_ventas,
        'count_ventas': count_ventas,
        'daily_totals': daily_totals,
        'caja_status': verificar_estado_caja(request),
        'fecha_inicio': fecha_inicio,
        'fecha_fin': fecha_fin,
        'estado': estado,
        'metodo_pago': metodo_pago,
        'buscar': buscar,
        'usuario': usuario_id,
        'usuarios': usuarios,
        'query_string': query_string,
        'page_obj': page_obj,
        'is_paginated': is_paginated,
        'ventas_count': ventas_count,
        'active_filters': {
            'fecha_inicio': fecha_inicio,
            'fecha_fin': fecha_fin,
            'estado': estado,
            'metodo_pago': metodo_pago,
            'buscar': buscar,
            'usuario': usuario_id,
        },
    }
    
    return render(request, 'ventas/lista_mejorada.html', context)


def pos_view(request):
    # Debug: imprimir productos disponibles
    productos = Producto.objects.filter(activo=True)
    print(f"Productos disponibles: {list(productos.values('id', 'nombre', 'activo'))}")
    return render(request, 'ventas/pos_venta.html', get_pos_context())


@csrf_exempt
@require_http_methods(["POST"])
def agregar_producto_temporal(request):
    try:
        data = json.loads(request.body)
        producto_id = data.get('producto_id')
        cantidad = data.get('cantidad', 1)
        
        producto = get_object_or_404(Producto, id=producto_id, activo=True)
        
        if producto.stock < cantidad:
            return JsonResponse({
                'success': False,
                'error': f'Stock insuficiente. Disponible: {producto.stock}'
            })
        
        subtotal = float(producto.precio_venta) * cantidad
        
        return JsonResponse({
            'success': True,
            'producto': {
                'id': producto.id,
                'name': producto.nombre,
                'price': float(producto.precio_venta),
                'cantidad': cantidad,
                'subtotal': subtotal
            }
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@csrf_exempt
def confirmar_venta(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body.decode("utf-8"))
            print(f"Datos recibidos: {data}")

            cliente_id = data.get("cliente")
            metodo_pago = data.get("metodo_pago")
            monto_efectivo = Decimal(str(data.get("monto_efectivo", 0) or 0))
            items = data.get("items", [])

            # Validar que haya items
            if not items:
                return JsonResponse({"success": False, "message": "Debe agregar al menos un producto"})

            # Validar método de pago
            if not metodo_pago:
                return JsonResponse({"success": False, "message": "Debe seleccionar un método de pago"})

            # Validar cliente (opcional)
            cliente = None
            if cliente_id:
                try:
                    cliente = Cliente.objects.get(id=cliente_id)
                except Cliente.DoesNotExist:
                    return JsonResponse({"success": False, "message": "El cliente seleccionado no existe"})

            # Crear la venta
            from decimal import Decimal
            venta = Venta.objects.create(
                cliente=cliente,
                usuario=request.user,
                metodo_pago=metodo_pago,
                estado='BORRADOR',
                fecha=timezone.now()
            )

            # Crear ítems de la venta (el stock se descuenta automáticamente al guardar la venta)
            for item in items:
                try:
                    producto = Producto.objects.get(id=item["id"])
                    
                    # Validar stock (sin descontar aquí)
                    if producto.stock < item["quantity"]:
                        return JsonResponse({
                            "success": False, 
                            "message": f"Stock insuficiente para {producto.nombre}. Disponible: {producto.stock}, Solicitado: {item['quantity']}"
                        })
                    
                    # Crear detalle de venta
                    DetalleVenta.objects.create(
                        venta=venta,
                        producto=producto,
                        cantidad=item["quantity"],
                        precio_unitario=Decimal(str(item["price"])),
                        descuento_porcentaje=Decimal(str(item.get("discount", 0)))
                    )

                except Producto.DoesNotExist:
                    return JsonResponse({"success": False, "message": f"El producto con ID {item['id']} no existe"})

            # Calcular totales
            venta.calcular_totales()
            
            # Validar pagos según método
            if metodo_pago == 'EFECTIVO':
                if monto_efectivo < Decimal(str(venta.total)):
                    return JsonResponse({
                        "success": False,
                        "message": f"Monto insuficiente. Total: Bs.{venta.total}, Pagado: Bs.{monto_efectivo}"
                    })
                venta.monto_recibido = monto_efectivo
                venta.cambio = monto_efectivo - venta.total
                cambio = float(venta.cambio)
            else:
                venta.monto_recibido = None
                venta.cambio = None
                cambio = 0

            # Confirmar venta
            venta.estado = 'CONFIRMADO'
            venta.save()
            crear_movimiento_venta(venta, request.user)

            return JsonResponse({
                "success": True,
                "venta_id": venta.id,
                "total": float(venta.total),
                "cambio": cambio,
                "message": f"Venta #{venta.id} confirmada exitosamente. Stock actualizado."
            })

        except json.JSONDecodeError:
            return JsonResponse({"success": False, "message": "Error en el formato de datos"})
        except Exception as e:
            print(f"Error en confirmar_venta: {e}")
            return JsonResponse({"success": False, "message": str(e)})

    return JsonResponse({"success": False, "message": "Método no permitido"})


def detalle_venta(request, venta_id):
    """API para obtener detalles de una venta en formato JSON"""
    try:
        venta = get_object_or_404(Venta, id=venta_id)
        
        detalles = []
        for detalle in venta.detalles.all():
            detalles.append({
                'producto': detalle.producto.nombre,
                'cantidad': float(detalle.cantidad) if detalle.cantidad else 0,
                'precio_unitario': float(detalle.precio_unitario) if detalle.precio_unitario else 0,
                'descuento_porcentaje': float(detalle.descuento_porcentaje) if detalle.descuento_porcentaje else 0,
                'subtotal': float(detalle.subtotal) if detalle.subtotal else 0
            })
        
        data = {
            'id': venta.id,
            'fecha': venta.fecha.strftime('%d/%m/%Y %H:%M'),
            'estado': venta.estado,
            'cliente': venta.cliente.nombre if venta.cliente else 'Cliente ocasional',
            'metodo_pago': venta.get_metodo_pago_display() if venta.metodo_pago else 'No definido',
            'subtotal': float(venta.subtotal) if venta.subtotal else 0,
            'descuento': float(venta.descuento) if venta.descuento else 0,
            'total': float(venta.total) if venta.total else 0,
            'cambio': float(venta.cambio) if venta.cambio else None,
            'detalles': detalles
        }
        
        return JsonResponse(data)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


def anular_venta(request, venta_id):
    """Vista para anular una venta"""
    try:
        venta = get_object_or_404(Venta, id=venta_id)
        
        if venta.estado != 'CONFIRMADO':
            return JsonResponse({
                'success': False, 
                'message': 'Solo se pueden anular ventas confirmadas'
            })
        
        # Cambiar estado y devolver stock
        venta.estado = 'ANULADO'
        venta.save()
        
        # El método save del modelo ya se encarga de devolver el stock
        return JsonResponse({
            'success': True,
            'message': f'Venta #{venta.id} anulada exitosamente. Stock devuelto.'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False, 
            'message': f'Error al anular venta: {str(e)}'
        })


def editar_venta(request, venta_id):
    """Vista para editar una venta (solo si está en borrador)"""
    try:
        venta = get_object_or_404(Venta, id=venta_id)
        
        if venta.estado != 'BORRADOR':
            return JsonResponse({
                'success': False, 
                'message': 'Solo se pueden editar ventas en borrador'
            })
        
        # Aquí podrías redirigir a una página de edición
        # Por ahora, solo devolvemos los datos para edición
        detalles = []
        for detalle in venta.detalles.all():
            detalles.append({
                'id': detalle.producto.id,
                'nombre': detalle.producto.nombre,
                'cantidad': float(detalle.cantidad) if detalle.cantidad else 0,
                'precio_unitario': float(detalle.precio_unitario) if detalle.precio_unitario else 0,
                'descuento_porcentaje': float(detalle.descuento_porcentaje) if detalle.descuento_porcentaje else 0,
                'stock': detalle.producto.stock
            })
        
        data = {
            'id': venta.id,
            'cliente_id': venta.cliente.id if venta.cliente else None,
            'metodo_pago': venta.metodo_pago,
            'subtotal': float(venta.subtotal) if venta.subtotal else 0,
            'descuento': float(venta.descuento) if venta.descuento else 0,
            'total': float(venta.total) if venta.total else 0,
            'detalles': detalles
        }
        
        return JsonResponse(data)
        
    except Exception as e:
        return JsonResponse({
            'success': False, 
            'message': f'Error al obtener datos de la venta: {str(e)}'
        })


# Vistas para Proformas
def lista_proformas(request):
    proformas = Proforma.objects.all().order_by('-fecha')
    return render(request, 'ventas/proforma_lista.html', {'proformas': proformas})


def nueva_proforma(request):
    productos = Producto.objects.filter(activo=True)
    clientes = Cliente.objects.all()

    if request.method == "POST":
        cliente_id = request.POST.get("cliente")
        metodo_pago = request.POST.get("metodo_pago")
        descuento = float(request.POST.get("descuento", 0))
        pago = float(request.POST.get("pago", 0))
        observaciones = request.POST.get("observaciones", "")

        try:
            with transaction.atomic():
                cliente = Cliente.objects.get(id=cliente_id) if cliente_id else None
                proforma = Proforma.objects.create(
                    cliente=cliente,
                    metodo_pago=metodo_pago,
                    descuento=descuento,
                    observaciones=observaciones,
                    fecha=timezone.now()
                )

                # Recorrer items enviados desde el formulario
                items = request.POST.getlist("producto_id")
                cantidades = request.POST.getlist("cantidad")
                precios = request.POST.getlist("precio_unitario")
                
                for i, prod_id in enumerate(items):
                    if prod_id:  # Solo procesar si hay un producto seleccionado
                        producto = Producto.objects.get(id=prod_id)
                        cantidad = float(cantidades[i]) if i < len(cantidades) else 1
                        precio = float(precios[i]) if i < len(precios) else producto.precio_venta
                        
                        ProformaItem.objects.create(
                            proforma=proforma,
                            producto=producto,
                            cantidad=cantidad,
                            precio_unitario=precio
                        )

                # Calcular totales
                proforma.calcular_totales()
                total = proforma.total
                cambio = pago - total

                return render(request, "ventas/proforma_detalle.html", {
                    "proforma": proforma,
                    "items": proforma.items.all(),
                    "total": total,
                    "pago": pago,
                    "cambio": cambio
                })
        except Exception as e:
            messages.error(request, f'Error al crear proforma: {str(e)}')
            return render(request, "ventas/nueva_proforma.html", {
                "productos": productos,
                "clientes": clientes
            })

    return render(request, "ventas/nueva_proforma.html", {
        "productos": productos,
        "clientes": clientes
    })


def detalle_proforma(request, pk):
    proforma = get_object_or_404(Proforma, pk=pk)
    return render(request, 'ventas/proforma_detalle.html', {
        'proforma': proforma,
        'items': proforma.items.all()
    })


def convertir_proforma_a_venta(request, pk):
    proforma = get_object_or_404(Proforma, pk=pk)
    
    if proforma.estado == 'CONVERTIDA_A_VENTA':
        messages.warning(request, 'Esta proforma ya fue convertida a venta')
        return redirect('ventas:detalle_proforma', pk=pk)
    
    try:
        with transaction.atomic():
            venta = proforma.convertir_a_venta()
            messages.success(request, f'Proforma convertida a venta #{venta.id}')
            return redirect('ventas:detalle', pk=venta.id)
    except Exception as e:
        messages.error(request, f'Error al convertir proforma: {str(e)}')
        return redirect('ventas:detalle_proforma', pk=pk)


def eliminar_proforma(request, pk):
    proforma = get_object_or_404(Proforma, pk=pk)
    
    if request.method == 'POST':
        proforma.estado = 'ANULADA'
        proforma.save()
        messages.success(request, 'Proforma anulada correctamente')
        return redirect('ventas:lista_proformas')
    
    return render(request, 'ventas/proforma_eliminar.html', {'proforma': proforma})


# Vistas para exportación e impresión
def exportar_ventas_excel(request):
    """Exportar ventas a formato Excel"""
    import csv
    from django.http import HttpResponse
    
    # Obtener parámetros de filtros
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')
    estado = request.GET.get('estado')
    metodo_pago = request.GET.get('metodo_pago')
    buscar = request.GET.get('buscar')
    usuario_id = request.GET.get('usuario')
    
    # Filtrar ventas
    ventas = Venta.objects.all().order_by('-fecha')
    
    if fecha_inicio:
        try:
            fecha_inicio_date = datetime.strptime(fecha_inicio, '%Y-%m-%d').date()
            fecha_inicio_dt = timezone.make_aware(datetime.combine(fecha_inicio_date, time.min), timezone.get_current_timezone())
            ventas = ventas.filter(fecha__gte=fecha_inicio_dt)
        except ValueError:
            pass
    if fecha_fin:
        try:
            fecha_fin_date = datetime.strptime(fecha_fin, '%Y-%m-%d').date()
            fecha_fin_dt = timezone.make_aware(datetime.combine(fecha_fin_date, time.max), timezone.get_current_timezone())
            ventas = ventas.filter(fecha__lte=fecha_fin_dt)
        except ValueError:
            pass
    if estado:
        ventas = ventas.filter(estado=estado)
    if metodo_pago:
        ventas = ventas.filter(metodo_pago=metodo_pago)
    if usuario_id:
        ventas = ventas.filter(usuario_id=usuario_id)
    if buscar:
        ventas = ventas.filter(
            models.Q(id__icontains=buscar) |
            models.Q(cliente__nombre__icontains=buscar)
        )
    
    # Crear respuesta HTTP
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="ventas_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"'
    
    # Crear writer CSV
    writer = csv.writer(response)
    
    # Escribir encabezados
    writer.writerow([
        'ID', 'Fecha', 'Hora', 'Cliente', 'Estado', 
        'Método Pago', 'Subtotal', 'Descuento', 'Total', 
        'Monto Recibido', 'Cambio'
    ])
    
    # Escribir datos
    for venta in ventas:
        writer.writerow([
            venta.id,
            venta.fecha.strftime('%d/%m/%Y'),
            venta.fecha.strftime('%H:%M:%S'),
            venta.cliente.nombre if venta.cliente else 'Cliente ocasional',
            venta.estado,
            venta.metodo_pago or '',
            f'{venta.subtotal:.2f}',
            f'{venta.descuento:.2f}',
            f'{venta.total:.2f}',
            f'{venta.monto_recibido:.2f}' if venta.monto_recibido else '',
            f'{venta.cambio:.2f}' if venta.cambio else ''
        ])
    
    return response


def imprimir_reporte_ventas(request):
    """Generar reporte de ventas para impresión"""
    
    # Obtener parámetros de filtros
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')
    estado = request.GET.get('estado')
    metodo_pago = request.GET.get('metodo_pago')
    buscar = request.GET.get('buscar')
    usuario_id = request.GET.get('usuario')
    
    # Filtrar ventas
    ventas = Venta.objects.all().order_by('-fecha')
    
    if fecha_inicio:
        try:
            fecha_inicio_date = datetime.strptime(fecha_inicio, '%Y-%m-%d').date()
            fecha_inicio_dt = timezone.make_aware(datetime.combine(fecha_inicio_date, time.min), timezone.get_current_timezone())
            ventas = ventas.filter(fecha__gte=fecha_inicio_dt)
        except ValueError:
            pass
    if fecha_fin:
        try:
            fecha_fin_date = datetime.strptime(fecha_fin, '%Y-%m-%d').date()
            fecha_fin_dt = timezone.make_aware(datetime.combine(fecha_fin_date, time.max), timezone.get_current_timezone())
            ventas = ventas.filter(fecha__lte=fecha_fin_dt)
        except ValueError:
            pass
    if estado:
        ventas = ventas.filter(estado=estado)
    if metodo_pago:
        ventas = ventas.filter(metodo_pago=metodo_pago)
    if usuario_id:
        ventas = ventas.filter(usuario_id=usuario_id)
    if buscar:
        ventas = ventas.filter(
            models.Q(id__icontains=buscar) |
            models.Q(cliente__nombre__icontains=buscar)
        )
    
    # Calcular totales
    total_ventas = sum(venta.total for venta in ventas if venta.estado == 'CONFIRMADO')
    total_ventas_count = ventas.filter(estado='CONFIRMADO').count()
    
    context = {
        'ventas': ventas,
        'total_ventas': total_ventas,
        'total_ventas_count': total_ventas_count,
        'fecha_inicio': fecha_inicio,
        'fecha_fin': fecha_fin,
        'estado': estado,
        'metodo_pago': metodo_pago,
        'buscar': buscar,
        'usuario': usuario_id,
    }
    
    return render(request, 'ventas/reporte_ventas.html', context)


def crear_movimiento_venta(venta, usuario):
    """Crear movimiento automático en caja cuando se confirma una venta"""
    from caja.models import Caja, MovimientoCaja
    
    # Buscar caja abierta del usuario
    caja_abierta = Caja.objects.filter(
        usuario=usuario,
        estado='ABIERTA'
    ).first()
    
    if caja_abierta and venta.metodo_pago:
        MovimientoCaja.objects.create(
            caja=caja_abierta,
            tipo='INGRESO',
            metodo_pago=venta.metodo_pago,
            categoria='VENTA',
            descripcion=f'Venta #{venta.id} - {venta.cliente.nombre if venta.cliente else "Cliente ocasional"}',
            monto=venta.total,
            usuario=usuario,
            referencia=f'VE#{venta.id}'
        )
        print(f"✅ Movimiento automático creado: Venta #{venta.id} - {venta.metodo_pago} - Bs.{venta.total}")
    else:
        if not caja_abierta:
            print(f"⚠️ No hay caja abierta para el usuario {usuario.username}")
        if not venta.metodo_pago:
            print(f"⚠️ La venta #{venta.id} no tiene método de pago definido")


def verificar_estado_caja(request):
    """Verificar estado de caja para mostrar en dashboard"""
    from caja.models import Caja
    
    # Verificar si el usuario está autenticado
    if not request.user.is_authenticated:
        return {'caja_abierta': False}
    
    caja_abierta = Caja.objects.filter(
        usuario=request.user,
        estado='ABIERTA'
    ).first()
    
    if caja_abierta:
        return {
            'caja_abierta': True,
            'caja_id': caja_abierta.id,
            'saldo_inicial_efectivo': float(caja_abierta.saldo_inicial_efectivo),
            'saldo_inicial_qr': float(caja_abierta.saldo_inicial_qr),
            'total_ingresos_efectivo': float(caja_abierta.total_ingresos_efectivo),
            'total_ingresos_qr': float(caja_abierta.total_ingresos_qr),
            'saldo_esperado_efectivo': float(caja_abierta.saldo_esperado_efectivo),
            'saldo_esperado_qr': float(caja_abierta.saldo_esperado_qr),
        }
    else:
        return {'caja_abierta': False}
