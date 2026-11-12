from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Q, Sum
from django.http import JsonResponse
from .models import Producto
from catalogo.models import Category
from .forms import ProductoForm
from django.core.cache import cache
from django.http import HttpResponse
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
from datetime import datetime, timedelta
from django.utils import timezone


def puede_editar_inventario(user):
    """Verificar si el usuario puede editar el inventario"""
    # Usuarios que NO pueden editar el inventario
    usuarios_restringidos = ['venta1', 'bruno']
    
    # Si el usuario no está autenticado, no puede editar
    if not user.is_authenticated:
        return False
    
    # Si el usuario está en la lista de restringidos, no puede editar
    if user.username.lower() in [u.lower() for u in usuarios_restringidos]:
        return False
    
    # Si es superusuario o staff, puede editar
    if user.is_superuser or user.is_staff:
        return True
    
    # Por defecto, permitir edición (puedes ajustar esta lógica)
    return True


def lista(request):
    from django.core.cache import cache

    productos = Producto.objects.all()
    
    # Verificar si hay productos actualizados recientemente
    producto_actualizado = cache.get('producto_actualizado', False)
    
    # Obtener parámetros de búsqueda y filtros
    search = request.GET.get('search', '')
    query = request.GET.get('q', '')
    category_id = request.GET.get('category', '')
    sort_by = request.GET.get('sort', 'nombre')
    vista = request.GET.get('vista', '')
    
    # Usar el parámetro search si existe, sino usar q
    if search:
        query = search
    
    # Búsqueda por nombre o descripción
    if query:
        productos = productos.filter(
            Q(nombre__icontains=query) |
            Q(descripcion__icontains=query) |
            Q(codigo__icontains=query)
        )
    
    # Filtro por categoría
    if category_id:
        productos = productos.filter(categoria_id=category_id)

    desde = timezone.now() - timedelta(days=30)
    productos = productos.annotate(
        unidades_vendidas=Sum(
            'detalleventa__cantidad',
            filter=Q(
                detalleventa__venta__estado='CONFIRMADO',
                detalleventa__venta__fecha__gte=desde,
            ),
        )
    )

    # Las vistas rapidas usan ventas confirmadas de los ultimos 30 dias.
    productos_destacados = productos.filter(unidades_vendidas__gt=0).order_by(
        '-unidades_vendidas', 'nombre'
    )[:10]
    alta_rotacion = productos.filter(unidades_vendidas__gt=0).count()
    baja_rotacion = productos.filter(unidades_vendidas__isnull=True).filter(stock__gt=0).count()
    stock_bajo_total = productos.filter(stock__lte=5, stock__gt=0).count()
    sin_stock_total = productos.filter(stock=0).count()

    if vista == 'bajo_stock':
        productos = productos.filter(stock__lte=5, stock__gt=0)
    elif vista == 'sin_stock':
        productos = productos.filter(stock=0)
    elif vista == 'alta_rotacion':
        productos = productos.filter(unidades_vendidas__gt=0)
        sort_by = 'rotacion'
    elif vista == 'baja_rotacion':
        productos = productos.filter(unidades_vendidas__isnull=True, stock__gt=0)
    
    # Ordenamiento
    if sort_by == 'nombre':
        productos = productos.order_by('nombre')
    elif sort_by == 'precio':
        productos = productos.order_by('precio_venta')
    elif sort_by == 'stock':
        productos = productos.order_by('-stock')
    elif sort_by == 'categoria':
        productos = productos.order_by('categoria__name', 'nombre')
    elif sort_by == 'rotacion':
        productos = productos.order_by('-unidades_vendidas', 'nombre')
    else:
        productos = productos.order_by('nombre')
    
    # Calcular estadísticas
    productos_activos = productos.filter(activo=True).count()
    stock_bajo = stock_bajo_total
    sin_stock = sin_stock_total
    stock_total = sum(p.stock for p in productos)
    valor_inventario = sum(p.precio_costo * p.stock for p in productos if p.precio_costo)
    valor_venta = sum(p.precio_venta * p.stock for p in productos if p.precio_venta)
    
    # Calcular margen promedio
    margen_promedio = 0
    productos_con_precios = productos.filter(precio_costo__gt=0, precio_venta__gt=0)
    if productos_con_precios.exists():
        total_margen = 0
        count = 0
        for p in productos_con_precios:
            margen = ((p.precio_venta - p.precio_costo) / p.precio_costo) * 100
            total_margen += margen
            count += 1
        margen_promedio = total_margen / count if count > 0 else 0
    
    # Obtener categorías para el filtro
    categories = Category.objects.all()
    
    # Mostrar mensaje si hay productos actualizados
    if producto_actualizado:
        messages.info(request, ' Los productos han sido actualizados desde el panel de administración. La lista está sincronizada.')
        # Limpiar la bandera después de mostrar el mensaje
        cache.delete('producto_actualizado')
    
    context = {
        'productos': productos,
        'productos_activos': productos_activos,
        'stock_bajo': stock_bajo,
        'sin_stock': sin_stock,
        'stock_total': stock_total,
        'valor_inventario': valor_inventario,
        'valor_venta': valor_venta,
        'margen_promedio': margen_promedio,
        'query': query,
        'search': search,
        'category_id': category_id,
        'sort_by': sort_by,
        'vista': vista,
        'alta_rotacion': alta_rotacion,
        'baja_rotacion': baja_rotacion,
        'productos_destacados': productos_destacados,
        'categories': categories,
        'puede_editar': puede_editar_inventario(request.user),
    }
    return render(request, 'inventario/lista_mejorada.html', context)


def crear_producto(request):
    # Verificar permisos de edición
    if not puede_editar_inventario(request.user):
        messages.error(request, '❌ No tienes permisos para crear productos en el inventario.')
        return redirect('inventario:lista')
    
    if request.method == 'POST':
        is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest'
        return_to = request.POST.get('return_to') or request.GET.get('return_to', '')
        form = ProductoForm(request.POST, request.FILES)
        # Validación personalizada para detectar duplicados
        nombre_producto = request.POST.get('nombre', '').strip()
        if nombre_producto:
            if Producto.objects.filter(nombre__iexact=nombre_producto).exists():
                msg = f'❌ Ya existe un producto con el nombre "{nombre_producto}". Por favor, usa un nombre diferente.'
                form.add_error('nombre', 'Este nombre de producto ya está en uso.')
                if is_ajax:
                    return JsonResponse({'success': False, 'message': msg, 'errors': form.errors}, status=400)
                messages.error(request, msg)
        if form.is_valid():
            producto = form.save(commit=False)
            # Asegurar que tenga código generado
            if not producto.codigo:
                from django.utils import timezone
                from django.db.models import Max
                max_id = Producto.objects.aggregate(max_id=Max('id'))['max_id'] or 0
                producto.codigo = f"PROD-{max_id + 1:04d}"
            producto.save()
            msg = f'✅ Producto "{producto.nombre}" creado correctamente'
            if is_ajax:
                redirect_url = f'/compras/crear/?restored=true&selected_product_id={producto.id}' if return_to == 'compras' else '/inventario/'
                if return_to == 'compras':
                    request.session['compraFormData'] = request.POST.get('compra_form_data', '')
                    request.session['compraFormAction'] = request.POST.get('compra_form_action', '')
                return JsonResponse({'success': True, 'message': msg, 'producto_id': producto.id, 'redirect_url': redirect_url})
            messages.success(request, msg)
            if return_to == 'compras':
                request.session['compraFormData'] = request.POST.get('compra_form_data', '')
                request.session['compraFormAction'] = request.POST.get('compra_form_action', '')
                messages.info(request, f'📦 Producto "{producto.nombre}" agregado al inventario. Ahora puedes continuar con tu compra.')
                return redirect(f'/compras/crear/?restored=true&selected_product_id={producto.id}')
            return redirect('inventario:lista')
        else:
            msg = '❌ Corrige los errores en el formulario'
            if is_ajax:
                return JsonResponse({'success': False, 'message': msg, 'errors': form.errors}, status=400)
            messages.error(request, msg)
    else:
        # Verificar si viene de creación de compra
        return_to = request.GET.get('return_to', '')
        compra_form_data = request.GET.get('compra_form_data', '')
        
        # Verificar si existen productos, si no, crear algunos básicos
        if Producto.objects.count() == 0:
            from catalogo.models import Category
            from proveedores.models import Proveedor
            
            # Crear categorías básicas si no existen
            categorias_basicas = [
                {"name": "Electrónicos", "description": "Productos electrónicos"},
                {"name": "Alimentos", "description": "Productos alimenticios"},
                {"name": "Ropa", "description": "Prendas de vestir"},
                {"name": "Hogar", "description": "Artículos para el hogar"}
            ]
            
            for cat_data in categorias_basicas:
                categoria, created = Category.objects.get_or_create(
                    name=cat_data["name"],
                    defaults={"description": cat_data["description"], "is_active": True}
                )
                if created:
                    messages.info(request, f'📁 Categoría "{categoria.name}" creada automáticamente')
            
            # Crear proveedor básico si no existe
            proveedor, created = Proveedor.objects.get_or_create(
                nombre="Proveedor General",
                defaults={
                    "direccion": "Dirección por defecto",
                    "telefono": "0000000000",
                    "email": "proveedor@ejemplo.com"
                }
            )
            if created:
                messages.info(request, f'🏢 Proveedor "{proveedor.nombre}" creado automáticamente')
        
        form = ProductoForm()
        
        # Si viene de compras, mostrar mensaje informativo
        if return_to == 'compras':
            messages.info(request, '🛒 Estás creando un producto desde la creación de compra. El producto estará disponible inmediatamente después de guardarlo.')
    
    # Obtener categorías del admin
    from catalogo.models import Category
    categorias = Category.objects.filter(is_active=True).order_by('name')
    
    return render(request, 'inventario/crear_producto.html', {
        'form': form,
        'titulo': 'Nuevo Producto',
        'categorias': categorias,
        'tiene_productos': Producto.objects.exists(),
        'producto': None,  # Para evitar errores en template
        'return_to': request.GET.get('return_to', ''),
        'compra_form_data': request.GET.get('compra_form_data', '')
    })


def editar_producto(request, pk):
    # Verificar permisos de edición
    if not puede_editar_inventario(request.user):
        messages.error(request, '❌ No tienes permisos para editar productos en el inventario.')
        return redirect('inventario:lista')
    
    producto = get_object_or_404(Producto, pk=pk)
    
    # Guardar los filtros actuales para redirigir correctamente
    filtros = ''
    if request.method == 'POST':
        form = ProductoForm(request.POST, request.FILES, instance=producto)
        # Validación personalizada para detectar duplicados (excluyendo el producto actual)
        nombre_producto = request.POST.get('nombre', '').strip()
        if nombre_producto and nombre_producto.lower() != producto.nombre.lower():
            if Producto.objects.filter(nombre__iexact=nombre_producto).exists():
                messages.error(request, f'❌ Ya existe otro producto con el nombre "{nombre_producto}". Por favor, usa un nombre diferente.')
                form.add_error('nombre', 'Este nombre de producto ya está en uso por otro producto.')
        # Recuperar filtros de la URL (GET params ocultos en el form)
        filtros = request.GET.urlencode() or request.POST.get('filtros', '')
        if form.is_valid():
            producto = form.save()
            messages.success(request, f'✅ Producto "{producto.nombre}" actualizado correctamente')
            if filtros:
                return redirect(f"/inventario/?{filtros}")
            else:
                return redirect('inventario:lista')
        else:
            messages.error(request, '❌ Corrige los errores en el formulario')
    else:
        form = ProductoForm(instance=producto)
        filtros = request.GET.urlencode()
    return render(request, 'inventario/crear_producto.html', {
        'form': form,
        'titulo': f'Editar Producto: {producto.nombre}',
        'producto': producto,
        'filtros': filtros
    })


def eliminar_producto(request, pk):
    # Verificar permisos de edición
    if not puede_editar_inventario(request.user):
        messages.error(request, '❌ No tienes permisos para eliminar productos en el inventario.')
        return redirect('inventario:lista')
    
    producto = get_object_or_404(Producto, pk=pk)
    
    if request.method == 'POST':
        nombre_producto = producto.nombre
        
        # Verificar si el producto tiene ventas asociadas
        from ventas.models import DetalleVenta
        from compras.models import DetalleCompra
        
        ventas_asociadas = DetalleVenta.objects.filter(producto=producto).exists()
        compras_asociadas = DetalleCompra.objects.filter(producto=producto).exists()
        
        if ventas_asociadas or compras_asociadas:
            # Si tiene ventas o compras, solo desactivar
            producto.activo = False
            producto.save()
            
            if ventas_asociadas and compras_asociadas:
                messages.warning(request, f'⚠️ Producto "{nombre_producto}" tiene ventas y compras asociadas. Se ha desactivado en lugar de eliminar para mantener la integridad de los datos.')
            elif ventas_asociadas:
                messages.warning(request, f'⚠️ Producto "{nombre_producto}" tiene ventas asociadas. Se ha desactivado en lugar de eliminar para mantener el historial de ventas.')
            else:
                messages.warning(request, f'⚠️ Producto "{nombre_producto}" tiene compras asociadas. Se ha desactivado en lugar de eliminar para mantener el historial de compras.')
        else:
            # Si no tiene ventas ni compras, se puede eliminar
            producto.delete()
            messages.success(request, f'✅ Producto "{nombre_producto}" eliminado correctamente')
        
        return redirect('inventario:lista')
    
    # Verificar si tiene ventas o compras asociadas para mostrar en el template
    from ventas.models import DetalleVenta
    from compras.models import DetalleCompra
    
    tiene_ventas = DetalleVenta.objects.filter(producto=producto).exists()
    tiene_compras = DetalleCompra.objects.filter(producto=producto).exists()
    
    return render(request, 'inventario/eliminar_producto.html', {
        'producto': producto,
        'tiene_ventas': tiene_ventas,
        'tiene_compras': tiene_compras,
        'puede_eliminar': not (tiene_ventas or tiene_compras)
    })


def cambiar_estado_producto(request, pk):
    # Verificar permisos de edición
    if not puede_editar_inventario(request.user):
        messages.error(request, '❌ No tienes permisos para cambiar el estado de productos en el inventario.')
        return redirect('inventario:lista')
    
    producto = get_object_or_404(Producto, pk=pk)
    producto.activo = not producto.activo
    producto.save()
    
    estado = "activado" if producto.activo else "desactivado"
    messages.success(request, f'✅ Producto "{producto.nombre}" {estado} correctamente')
    
    return redirect('inventario:lista')


def check_updates(request):
    """Vista para verificar si hay actualizaciones de productos desde admin"""
    producto_actualizado = cache.get('producto_actualizado', False)
    
    return JsonResponse({
        'has_updates': producto_actualizado,
        'timestamp': cache.get('last_update_timestamp', None)
    })


# Vistas para exportación e impresión
def exportar_inventario_excel(request):
    """Exportar el inventario a un archivo Excel XLSX."""
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment
    from openpyxl.utils import get_column_letter

    search = request.GET.get('search', '').strip()
    category_id = request.GET.get('category', '').strip()
    productos = Producto.objects.select_related('categoria', 'proveedor').order_by('nombre')

    if search:
        productos = productos.filter(
            Q(nombre__icontains=search) |
            Q(codigo__icontains=search) |
            Q(categoria__name__icontains=search) |
            Q(proveedor__nombre__icontains=search)
        )
    if category_id:
        productos = productos.filter(categoria_id=category_id)

    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = 'Inventario'
    headers = [
        'ID', 'Código', 'Nombre', 'Categoría', 'Proveedor',
        'Precio Costo', 'Precio Venta', 'Stock', 'Stock Mínimo',
        'Estado', 'Fecha Creación', 'Última Actualización'
    ]
    worksheet.append(headers)

    header_fill = PatternFill('solid', fgColor='2F4154')
    for cell in worksheet[1]:
        cell.font = Font(bold=True, color='FFFFFF')
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal='center')

    for producto in productos:
        worksheet.append([
            producto.id,
            producto.codigo or '',
            producto.nombre,
            producto.categoria.name if producto.categoria else '',
            producto.proveedor.nombre if producto.proveedor else '',
            float(producto.precio_costo or 0),
            float(producto.precio_venta or 0),
            producto.stock,
            producto.stock_minimo or 0,
            'Activo' if producto.activo else 'Inactivo',
            producto.fecha_creacion.strftime('%d/%m/%Y %H:%M') if producto.fecha_creacion else '',
            producto.fecha_actualizacion.strftime('%d/%m/%Y %H:%M') if producto.fecha_actualizacion else ''
        ])

    for column_cells in worksheet.columns:
        column_letter = get_column_letter(column_cells[0].column)
        max_length = max(len(str(cell.value or '')) for cell in column_cells)
        worksheet.column_dimensions[column_letter].width = min(max(max_length + 2, 12), 30)
    worksheet.freeze_panes = 'A2'
    worksheet.auto_filter.ref = worksheet.dimensions

    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = (
        f'attachment; filename="inventario_{datetime.now():%Y%m%d_%H%M%S}.xlsx"'
    )
    workbook.save(response)
    return response


def imprimir_reporte_inventario(request):
    """Generar y descargar un reporte PDF del inventario."""
    search = request.GET.get('search', '').strip()
    category_id = request.GET.get('category', '').strip()
    productos = Producto.objects.select_related('categoria', 'proveedor').order_by('nombre')

    if search:
        productos = productos.filter(
            Q(nombre__icontains=search) |
            Q(codigo__icontains=search) |
            Q(categoria__name__icontains=search) |
            Q(proveedor__nombre__icontains=search)
        )
    if category_id:
        productos = productos.filter(categoria_id=category_id)

    total_productos = productos.count()
    productos_activos = productos.filter(activo=True).count()
    stock_total = sum(producto.stock for producto in productos)
    valor_inventario = sum(
        producto.precio_costo * producto.stock
        for producto in productos
        if producto.precio_costo
    )
    stock_bajo = productos.filter(stock__lte=5, stock__gt=0).count()
    sin_stock = productos.filter(stock=0).count()

    response = HttpResponse(content_type='application/pdf')
    filename = f'inventario_{datetime.now():%Y%m%d_%H%M%S}.pdf'
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    document = SimpleDocTemplate(
        response,
        pagesize=landscape(A4),
        rightMargin=12 * mm,
        leftMargin=12 * mm,
        topMargin=12 * mm,
        bottomMargin=12 * mm,
    )
    styles = getSampleStyleSheet()
    content = [
        Paragraph('REPORTE DE INVENTARIO', styles['Title']),
        Paragraph(
            f'Generado: {datetime.now():%d/%m/%Y %H:%M} | '
            f'Productos: {total_productos} | Activos: {productos_activos} | '
            f'Stock total: {stock_total} | Valor: Bs. {valor_inventario:.2f} | '
            f'Stock bajo: {stock_bajo} | Sin stock: {sin_stock}',
            styles['Normal'],
        ),
        Spacer(1, 8 * mm),
    ]

    if search:
        content.append(Paragraph(f'Búsqueda: {search}', styles['Normal']))
        content.append(Spacer(1, 4 * mm))

    table_data = [[
        'ID', 'Código', 'Producto', 'Categoría', 'Proveedor',
        'Costo', 'Venta', 'Stock', 'Mínimo', 'Estado'
    ]]
    for producto in productos:
        table_data.append([
            str(producto.id),
            producto.codigo or '',
            producto.nombre,
            producto.categoria.name if producto.categoria else 'Sin categoría',
            producto.proveedor.nombre if producto.proveedor else 'Sin proveedor',
            f'Bs. {producto.precio_costo:.2f}',
            f'Bs. {producto.precio_venta:.2f}',
            str(producto.stock),
            str(producto.stock_minimo),
            'Activo' if producto.activo else 'Inactivo',
        ])

    table = Table(table_data, repeatRows=1, colWidths=[12 * mm, 25 * mm, 48 * mm, 35 * mm, 40 * mm, 24 * mm, 24 * mm, 18 * mm, 18 * mm, 20 * mm])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2f4154')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 7),
        ('GRID', (0, 0), (-1, -1), 0.35, colors.HexColor('#b8c0c8')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f2f4f6')]),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    content.append(table)
    document.build(content)
    return response