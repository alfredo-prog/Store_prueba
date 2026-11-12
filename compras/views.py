import re

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from inventario.models import Producto
from .models import Compra, DetalleCompra
from .forms import CompraForm, DetalleCompraFormSet, DetalleCompraFormSetEdicion


def _extraer_filas_detalle(post):
    """Obtiene filas de detalle desde POST sin depender de TOTAL_FORMS, que puede desincronizarse."""
    filas = {}
    for key in post.keys():
        match = re.match(r'^detalles-(\d+)-(.+)$', key)
        if not match:
            continue
        index, campo = match.groups()
        filas.setdefault(int(index), {})[campo] = post.get(key)
    return dict(sorted(filas.items()))


def _resolver_precio_detalle(fila):
    """Usa el precio del producto como fallback cuando el usuario deja el campo vacío."""
    producto_id = fila.get('producto')
    precio_unitario = fila.get('precio_unitario')
    precio_venta = fila.get('precio_venta_unitario')

    if not producto_id:
        return precio_unitario, precio_venta

    try:
        producto = Producto.objects.get(pk=int(producto_id))
    except (Producto.DoesNotExist, ValueError):
        return precio_unitario, precio_venta

    if not precio_unitario and producto.precio_costo:
        precio_unitario = str(producto.precio_costo)
    if not precio_venta and producto.precio_venta:
        precio_venta = str(producto.precio_venta)

    return precio_unitario, precio_venta

def lista(request):
    compras = Compra.objects.all()
    return render(request, 'compras/lista.html', {'compras': compras})

def index(request):
    return render(request, 'compras/index.html')

def crear_compra(request):
    if request.method == 'POST':
        form = CompraForm(request.POST)
        formset = DetalleCompraFormSet(request.POST)
        
        print(f"=== DEPURACIÓN CREAR COMPRA ===")
        print(f"Form válido: {form.is_valid()}")
        print(f"Formset válido: {formset.is_valid()}")
        print(f"POST data keys: {list(request.POST.keys())}")
        
        if form.is_valid():
            actualizar_precios = form.cleaned_data.get('actualizar_precios', True)
            # Guardar compra primero con estado COMPLETADO
            compra = form.save(commit=False)
            compra.estado = 'COMPLETADO'  # Forzar estado completado
            compra.save()
            print(f"Compra guardada: #{compra.id}, estado: {compra.estado}, metodo_pago: {compra.metodo_pago}, actualizar_precios={actualizar_precios}")
            
            # Procesar manualmente los datos del formset para evitar errores de formularios vacíos
            detalles_guardados = 0
            total_compra = 0
            
            filas_detalle = _extraer_filas_detalle(request.POST)
            print(f"Procesando {len(filas_detalle)} formularios reales desde POST...")

            for i, fila in filas_detalle.items():
                producto_id = fila.get('producto')
                cantidad = fila.get('cantidad')
                precio_unitario, precio_venta_unitario = _resolver_precio_detalle(fila)
                DELETE = fila.get('DELETE')

                print(f"  -> Formulario {i}: producto={producto_id}, cantidad={cantidad}, precio={precio_unitario}, precio_venta={precio_venta_unitario}, DELETE={DELETE}")

                if not producto_id or not cantidad or not precio_unitario:
                    print(f"  -> Formulario {i} vacío, omitiendo")
                    continue

                if DELETE in ('on', 'true', '1', 'True', 'yes'):
                    print(f"  -> Formulario {i} marcado para eliminar, omitiendo")
                    continue

                try:
                    producto_id = int(producto_id)
                    cantidad = float(cantidad)
                    precio_unitario = float(precio_unitario)
                    precio_venta_unitario = float(precio_venta_unitario) if precio_venta_unitario not in (None, '', '0', '0.00') else 0

                    detalle = DetalleCompra.objects.create(
                        compra=compra,
                        producto_id=producto_id,
                        cantidad=cantidad,
                        precio_unitario=precio_unitario,
                        precio_venta_unitario=precio_venta_unitario
                    )

                    subtotal = cantidad * precio_unitario
                    total_compra += subtotal
                    detalles_guardados += 1

                    print(f"  -> Detalle guardado: {detalle.producto.nombre} (stock será actualizado por el modelo)")

                except (ValueError, TypeError) as e:
                    print(f"  -> Error procesando formulario {i}: {e}")
                    continue
            
            if detalles_guardados > 0:
                # Actualizar total de la compra
                compra.total = total_compra
                compra.save()
                compra.actualizar_precios_productos(actualizar=actualizar_precios)
                messages.success(request, f'Compra #{compra.id} creada exitosamente ({detalles_guardados} productos)')
                print(f"Compra #{compra.id} guardada exitosamente con {detalles_guardados} productos, total: {total_compra}")
                print("Redirigiendo a lista de compras...")
                
                # Actualizar stock manualmente para asegurar sincronización
                for detalle in compra.detalles.all():
                    producto = detalle.producto
                    producto.stock += detalle.cantidad
                    producto.save()
                    print(f"Stock actualizado manualmente: {producto.nombre} +{detalle.cantidad} = {producto.stock}")
                
                # Limpiar caché para forzar actualización
                from django.core.cache import cache
                cache.delete('producto_actualizado')
                cache.set('producto_actualizado', True, 60)  # Marcar por 60 segundos
                print("Caché limpiado y marcado para actualización")
                
                # Crear movimiento automático en caja
                crear_movimiento_compra(compra, request.user)
                
                # Limpiar datos de sesión
                if 'compraFormData' in request.session:
                    del request.session['compraFormData']
                if 'compraFormAction' in request.session:
                    del request.session['compraFormAction']
                    
                return redirect('compras:lista')
            else:
                # Eliminar compra si no se guardaron detalles
                compra.delete()
                messages.warning(request, 'Debe agregar al menos un producto a la compra')
                print("No se guardaron detalles, eliminando compra")
        else:
            print(f"Formulario principal inválido: {form.errors}")
            print(f"Formset inválido: {formset.errors}")
    
    else:
        # Restaurar datos si viene de crear producto
        restored_data = None
        if request.GET.get('restored') == 'true':
            restored_data = request.session.get('compraFormData', None)
            if restored_data:
                print("Restaurando datos del formulario desde sesión")
                # Limpiar sesión
                if 'compraFormData' in request.session:
                    del request.session['compraFormData']
                if 'compraFormAction' in request.session:
                    del request.session['compraFormAction']
        
        # Crear formularios pasando el usuario
        form = CompraForm(user=request.user)
        formset = DetalleCompraFormSet()
        
        if restored_data:
            messages.info(request, 'Datos del formulario restaurados. El nuevo producto ha sido agregado al inventario.')
    
    return render(request, 'compras/crear.html', {
        'form': form,
        'formset': formset,
        'titulo': 'Nueva Compra'
    })

def ver_compra(request, pk):
    compra = get_object_or_404(Compra, pk=pk)
    detalles = compra.detalles.all()
    return render(request, 'compras/ver.html', {
        'compra': compra,
        'detalles': detalles
    })

def editar_compra(request, pk):
    compra = get_object_or_404(Compra, pk=pk)
    
    if request.method == 'POST':
        form = CompraForm(request.POST, instance=compra)
        formset = DetalleCompraFormSetEdicion(request.POST, instance=compra)
        
        print(f"=== DEPURACIÓN EDICIÓN COMPRA {pk} ===")
        print(f"Form válido: {form.is_valid()}")
        print(f"Formset válido: {formset.is_valid()}")
        print(f"POST data: {request.POST}")
        
        if form.is_valid():
            actualizar_precios = form.cleaned_data.get('actualizar_precios', True)
            # Guardar compra primero
            compra = form.save()
            
            # Procesar manualmente los datos del formset para evitar errores de formularios vacíos
            detalles_guardados = 0
            total_compra = 0
            detalles_eliminados = []
            
            # Obtener el número real de formularios del POST
            total_forms = int(request.POST.get('detalles-TOTAL_FORMS', 0))
            initial_forms = int(request.POST.get('detalles-INITIAL_FORMS', 0))
            print(f"Procesando {total_forms} formularios ({initial_forms} iniciales)...")
            
            # Primero, procesar eliminaciones de detalles existentes
            for i in range(initial_forms):
                DELETE = request.POST.get(f'detalles-{i}-DELETE')
                detalle_id = request.POST.get(f'detalles-{i}-id')
                
                if DELETE and detalle_id:
                    try:
                        detalle = DetalleCompra.objects.get(pk=int(detalle_id))
                        # Devolver stock al inventario
                        producto = detalle.producto
                        producto.stock -= detalle.cantidad
                        producto.save()
                        print(f"  -> Eliminando detalle: {producto.nombre} (-{detalle.cantidad})")
                        detalles_eliminados.append(detalle)
                        detalle.delete()
                    except (DetalleCompra.DoesNotExist, ValueError):
                        continue
            
            # Luego, procesar todos los formularios (existentes y nuevos)
            for i in range(total_forms):
                producto_id = request.POST.get(f'detalles-{i}-producto')
                cantidad = request.POST.get(f'detalles-{i}-cantidad')
                precio_unitario = request.POST.get(f'detalles-{i}-precio_unitario')
                precio_venta_unitario = request.POST.get(f'detalles-{i}-precio_venta_unitario')
                detalle_id = request.POST.get(f'detalles-{i}-id')
                DELETE = request.POST.get(f'detalles-{i}-DELETE')
                
                print(f"  -> Formulario {i}: producto={producto_id}, cantidad={cantidad}, precio={precio_unitario}, precio_venta={precio_venta_unitario}, id={detalle_id}, DELETE={DELETE}")
                
                # Solo procesar si tiene datos y no está marcado para eliminar
                if producto_id and cantidad and precio_unitario and not DELETE:
                    try:
                        producto_id = int(producto_id)
                        cantidad = float(cantidad)
                        precio_unitario = float(precio_unitario)
                        precio_venta_unitario = float(precio_venta_unitario) if precio_venta_unitario not in (None, '', '0', '0.00') else 0
                        
                        if detalle_id:
                            # Actualizar detalle existente
                            try:
                                detalle = DetalleCompra.objects.get(pk=int(detalle_id))
                                cantidad_anterior = detalle.cantidad
                                
                                # Actualizar campos
                                detalle.producto_id = producto_id
                                detalle.cantidad = cantidad
                                detalle.precio_unitario = precio_unitario
                                detalle.precio_venta_unitario = precio_venta_unitario
                                detalle.save()
                                
                                # Ajustar stock según diferencia
                                diferencia = cantidad - cantidad_anterior
                                if diferencia != 0:
                                    producto = detalle.producto
                                    producto.stock += diferencia
                                    producto.save()
                                    print(f"  -> Detalle ACTUALIZADO: {producto.nombre} (diff: {diferencia})")
                                else:
                                    print(f"  -> Detalle ACTUALIZADO: {detalle.producto.nombre} (sin cambio de stock)")
                                
                            except DetalleCompra.DoesNotExist:
                                # Si no existe, crear nuevo
                                detalle = DetalleCompra.objects.create(
                                    compra=compra,
                                    producto_id=producto_id,
                                    cantidad=cantidad,
                                    precio_unitario=precio_unitario,
                                    precio_venta_unitario=precio_venta_unitario
                                )
                                # Agregar stock
                                producto = detalle.producto
                                producto.stock += cantidad
                                producto.save()
                                print(f"  -> Detalle NUEVO (tratado como existente): {producto.nombre} (+{cantidad})")
                        else:
                            # Crear nuevo detalle
                            detalle = DetalleCompra.objects.create(
                                compra=compra,
                                producto_id=producto_id,
                                cantidad=cantidad,
                                precio_unitario=precio_unitario,
                                precio_venta_unitario=precio_venta_unitario
                            )
                            # Agregar stock
                            producto = detalle.producto
                            producto.stock += cantidad
                            producto.save()
                            print(f"  -> Detalle NUEVO: {producto.nombre} (+{cantidad})")
                        
                        subtotal = cantidad * precio_unitario
                        total_compra += subtotal
                        detalles_guardados += 1
                            
                    except (ValueError, TypeError) as e:
                        print(f"  -> Error procesando formulario {i}: {e}")
                        continue
                else:
                    print(f"  -> Formulario {i} vacío o marcado para eliminar, omitiendo")
            
            # Actualizar total de la compra
            if detalles_guardados > 0 or detalles_eliminados:
                compra.total = total_compra
                compra.save()
                compra.actualizar_precios_productos(actualizar=actualizar_precios)
                messages.success(request, f'Compra #{compra.id} actualizada exitosamente ({detalles_guardados} productos)')
                print(f"Compra #{compra.id} actualizada con {detalles_guardados} productos, total: {total_compra}")
                return redirect('compras:lista')
            else:
                messages.warning(request, 'No se encontraron cambios en los detalles para guardar')
                print("No se guardaron detalles")
                return redirect('compras:lista')
        else:
            print(f"Formulario principal inválido: {form.errors}")
    
    else:
        form = CompraForm(instance=compra, user=request.user)
        # Solo mostrar los detalles existentes, sin formularios vacíos
        formset = DetalleCompraFormSetEdicion(instance=compra, queryset=compra.detalles.all())
    
    # Obtener productos disponibles para el select
    from inventario.models import Producto
    productos_disponibles = Producto.objects.all()
    
    return render(request, 'compras/editar.html', {
        'form': form,
        'formset': formset,
        'titulo': f'Editar Compra #{compra.id}',
        'compra': compra,
        'productos_disponibles': productos_disponibles
    })

def completar_compra(request, pk):
    """Vista para completar una compra y actualizar el inventario"""
    compra = get_object_or_404(Compra, pk=pk)
    
    if request.method == 'POST':
        if compra.estado == 'PENDIENTE':
            # Cambiar estado a COMPLETADO
            compra.estado = 'COMPLETADO'
            compra.save()  # El modelo actualizará el inventario automáticamente
            
            messages.success(request, f'Compra #{compra.id} completada exitosamente. Stock actualizado.')
        else:
            messages.warning(request, f'La compra #{compra.id} ya está {compra.get_estado_display()}.')
        
        return redirect('compras:lista')
    
    return render(request, 'compras/completar.html', {'compra': compra})

def eliminar_compra(request, pk):
    compra = get_object_or_404(Compra, pk=pk)
    
    if request.method == 'POST':
        # Verificar si hay productos que quedarían con stock negativo
        productos_con_stock_negativo = []
        stock_actualizado = {}
        
        for detalle in compra.detalles.all():
            producto = detalle.producto
            nuevo_stock = producto.stock - detalle.cantidad
            stock_actualizado[producto.nombre] = nuevo_stock
            
            if nuevo_stock < 0:
                productos_con_stock_negativo.append({
                    'producto': producto.nombre,
                    'stock_actual': producto.stock,
                    'cantidad_restar': detalle.cantidad,
                    'nuevo_stock': nuevo_stock
                })
        
        # Si hay productos con stock negativo, mostrar advertencia y permitir eliminación
        if productos_con_stock_negativo:
            # Construir mensaje de advertencia
            mensaje_advertencia = " Advertencia: Los siguientes productos quedarán con stock negativo:<br><br>"
            for item in productos_con_stock_negativo:
                mensaje_advertencia += f"• <strong>{item['producto']}</strong>: {item['stock_actual']} - {item['cantidad_restar']} = <span style='color: red;'>{item['nuevo_stock']}</span><br>"
            mensaje_advertencia += "<br>La compra se eliminará igualmente. Por favor, revise y ajuste el inventario manualmente."
            
            messages.warning(request, mensaje_advertencia)
            
            # Devolver stock (incluso si queda negativo)
            for detalle in compra.detalles.all():
                producto = detalle.producto
                producto.stock -= detalle.cantidad
                producto.save()
                print(f"  -> Stock actualizado: {producto.nombre} ({producto.stock})")
        else:
            # Si no hay problemas de stock, proceder normalmente
            messages.success(request, f'Stock actualizado correctamente al eliminar la compra #{compra.id}')
            
            # Devolver stock al inventario
            for detalle in compra.detalles.all():
                producto = detalle.producto
                producto.stock -= detalle.cantidad
                producto.save()
                print(f"  -> Stock actualizado: {producto.nombre} ({producto.stock})")
        
        # Eliminar la compra
        compra_id = compra.id
        compra.delete()
        
        # Mensaje final de éxito
        if productos_con_stock_negativo:
            messages.success(request, f' Compra #{compra_id} eliminada. Revise el inventario para ajustar el stock negativo.')
        else:
            messages.success(request, f' Compra #{compra_id} eliminada exitosamente')
        
        return redirect('compras:lista')
    
    return render(request, 'compras/eliminar.html', {'compra': compra})


def crear_movimiento_compra(compra, usuario):
    """Crear movimiento automático en caja cuando se confirma una compra"""
    from caja.models import Caja, MovimientoCaja
    
    # Buscar caja abierta del usuario
    caja_abierta = Caja.objects.filter(
        usuario=usuario,
        estado='ABIERTA'
    ).first()
    
    if caja_abierta:
        # Crear movimiento de egreso por compra con el método de pago correcto
        MovimientoCaja.objects.create(
            caja=caja_abierta,
            tipo='EGRESO',
            metodo_pago=compra.metodo_pago,  # Usar el método de pago de la compra
            categoria='COMPRA',
            descripcion=f'Compra #{compra.id} - {compra.proveedor.nombre}',
            monto=compra.total,
            usuario=usuario,
            referencia=f'CO#{compra.id}'
        )
        print(f" Movimiento automático creado: Compra #{compra.id} - Egreso - {compra.metodo_pago} - Bs.{compra.total}")
    else:
        print(f" No hay caja abierta para el usuario {usuario.username}")