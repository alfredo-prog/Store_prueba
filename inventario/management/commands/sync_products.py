from django.core.management.base import BaseCommand
from django.db import transaction
from inventario.models import Producto
from inventario.models import Producto
from catalogo.models import Category
from proveedores.models import Proveedor

class Command(BaseCommand):
    help = 'Sincroniza productos entre catálogo e inventario'

    def handle(self, *args, **options):
        self.stdout.write('=== Iniciando sincronización de productos ===')
        
        # Obtener todos los productos del catálogo
        catalogo_products = Product.objects.all()
        
        synced_count = 0
        created_count = 0
        error_count = 0
        
        for cat_product in catalogo_products:
            try:
                with transaction.atomic():
                    # Buscar si el producto ya existe en inventario
                    inv_producto = Producto.objects.filter(
                        nombre=cat_product.nombre
                    ).first()
                    
                    if not inv_producto:
                        # Crear el producto en inventario
                        proveedor = Proveedor.objects.first()  # Usar primer proveedor disponible
                        
                        inv_producto = Producto.objects.create(
                            nombre=cat_product.nombre,
                            codigo=cat_product.codigo,
                            codigo_barras=cat_product.codigo_barras,
                            categoria=cat_product.categoria,
                            precio_costo=cat_product.precio_costo,
                            precio_venta=cat_product.precio_venta,
                            stock=int(cat_product.stock),  # Convertir a entero
                            stock_minimo=int(cat_product.stock_minimo),  # Convertir a entero
                            descripcion=cat_product.descripcion,
                            imagen=cat_product.imagen,
                            activo=cat_product.activo,
                            proveedor=proveedor,
                        )
                        created_count += 1
                        self.stdout.write(
                            self.style.SUCCESS(
                                f'✅ Creado: {cat_product.nombre} -> Inventario (ID: {inv_producto.id})'
                            )
                        )
                    else:
                        # Actualizar el producto existente
                        inv_producto.codigo = cat_product.codigo
                        inv_producto.codigo_barras = cat_product.codigo_barras
                        inv_producto.categoria = cat_product.categoria
                        inv_producto.precio_costo = cat_product.precio_costo
                        inv_producto.precio_venta = cat_product.precio_venta
                        inv_producto.stock = int(cat_product.stock)
                        inv_producto.stock_minimo = int(cat_product.stock_minimo)
                        inv_producto.descripcion = cat_product.descripcion
                        inv_producto.imagen = cat_product.imagen
                        inv_producto.activo = cat_product.activo
                        inv_producto.save()
                        
                        synced_count += 1
                        self.stdout.write(
                            self.style.WARNING(
                                f'🔄 Actualizado: {cat_product.nombre} (ID: {inv_producto.id})'
                            )
                        )
                        
            except Exception as e:
                error_count += 1
                self.stdout.write(
                    self.style.ERROR(
                        f'❌ Error procesando {cat_product.nombre}: {str(e)}'
                    )
                )
        
        # Estadísticas finales
        total_catalogo = catalogo_products.count()
        total_inventario = Producto.objects.count()
        
        self.stdout.write('\n=== Resumen de sincronización ===')
        self.stdout.write(f'📊 Productos en catálogo: {total_catalogo}')
        self.stdout.write(f'📦 Productos en inventario: {total_inventario}')
        self.stdout.write(f'➕ Productos creados: {created_count}')
        self.stdout.write(f'🔄 Productos actualizados: {synced_count}')
        self.stdout.write(f'❌ Errores: {error_count}')
        
        if created_count > 0 or synced_count > 0:
            self.stdout.write(
                self.style.SUCCESS(
                    f'✅ Sincronización completada: {created_count + synced_count} productos procesados'
                )
            )
        else:
            self.stdout.write(
                self.style.WARNING(
                    '⚠️ No se realizaron cambios'
                )
            )
