from django.shortcuts import render, get_object_or_404, redirect
from catalogo.models import Category
from inventario.models import Producto
from django.core.paginator import Paginator
from django.db.models import Q, Count, Min, Max, Avg
from django.contrib import messages
from decimal import Decimal

def product_list(request):
    query = request.GET.get('q', '')
    category_id = request.GET.get('category', '')
    sort_by = request.GET.get('sort', 'nombre')
    
    # Obtener productos del catálogo con información actualizada
    products = Producto.objects.filter(activo=True).select_related('categoria')
    
    # Obtener categorías únicas con conteo de productos
    categories = Category.objects.filter(is_active=True).annotate(
        product_count=Count('producto', filter=Q(producto__activo=True))
    ).order_by('name')
    
    # Estadísticas del inventario
    stats = {
        'total_products': products.count(),
        'total_categories': categories.count(),
        'low_stock': products.filter(stock__lte=5).count(),
        'avg_price': products.aggregate(avg_price=Avg('precio_venta'))['avg_price'] or Decimal('0'),
    }
    
    # Aplicar filtros
    if query:
        products = products.filter(
            Q(nombre__icontains=query) | 
            Q(codigo__icontains=query) | 
            Q(codigo_barras__icontains=query) |
            Q(descripcion__icontains=query)
        )
    if category_id:
        products = products.filter(categoria=category_id)
    
    # Aplicar ordenamiento
    sort_options = {
        'nombre': 'nombre',
        'precio': 'precio_venta',
        'stock': 'stock',
        'categoria': 'categoria__name',
        'codigo': 'codigo'
    }
    if sort_by in sort_options:
        products = products.order_by(sort_options[sort_by])
    
    paginator = Paginator(products, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'catalogo/product_list.html', {
        'page_obj': page_obj,
        'categories': categories,
        'query': query,
        'category_id': category_id,
        'sort_by': sort_by,
        'stats': stats,
    })

def product_detail(request, pk):
    product = get_object_or_404(Producto, pk=pk, activo=True)
    # Productos relacionados (misma categoría)
    related_products = []
    if product.categoria:
        related_products = Producto.objects.filter(
            categoria=product.categoria, 
            activo=True
        ).exclude(pk=pk)[:4]
    
    # Historial de movimientos (si existe)
    from compras.models import DetalleCompra
    from ventas.models import DetalleVenta
    
    try:
        recent_purchases = DetalleCompra.objects.filter(
            producto=product
        ).order_by('-compra__fecha')[:5]
    except:
        recent_purchases = []
    
    try:
        recent_sales = DetalleVenta.objects.filter(
            producto=product
        ).order_by('-venta__fecha')[:5]
    except:
        recent_sales = []
    
    return render(request, 'catalogo/product_detail.html', {
        'product': product,
        'related_products': related_products,
        'recent_purchases': recent_purchases,
        'recent_sales': recent_sales,
    })

