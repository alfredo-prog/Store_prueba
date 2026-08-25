from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.cache import cache
from .models import Producto
import logging

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Producto)
def sincronizar_stock_catalogo_signal(sender, instance, created, **kwargs):
    """Sincroniza automáticamente el stock con el catálogo cuando se actualiza un producto"""
    try:
        if not instance.codigo:
            return

        from inventario.models import Producto
        producto_catalogo = Producto.objects.filter(codigo=instance.codigo).exclude(pk=instance.pk).first()
        if producto_catalogo:
            # Solo sincronizar si el stock realmente cambió
            if producto_catalogo.stock != instance.stock:
                producto_catalogo.stock = instance.stock
                producto_catalogo.save(update_fields=['stock'])
                print(f"Stock sincronizado por signal: {instance.nombre} -> {instance.stock}")
        
        # Limpiar caché para forzar actualización en interfaz
        cache.delete('productos_lista')
        cache.delete('categorias_lista')
        cache.set('producto_actualizado', True, timeout=60)
        
        if created:
            logger.info(f"Producto creado en admin: {instance.nombre} (ID: {instance.id})")
            print(f"Nuevo producto desde admin: {instance.nombre} - Interfaz actualizada")
        else:
            logger.info(f"Producto actualizado en admin: {instance.nombre} (ID: {instance.id})")
            print(f"Producto actualizado desde admin: {instance.nombre} - Interfaz sincronizada")
            
    except Exception as e:
        logger.error(f"Error en signal de sincronización: {e}")
        print(f"Error en signal: {e}")


@receiver(post_delete, sender=Producto)
def producto_eliminado_signal(sender, instance, **kwargs):
    """Signal que se dispara cuando un producto se elimina desde admin"""
    try:
        from inventario.models import Producto
        producto_catalogo = Producto.objects.filter(codigo=instance.codigo).first()
        if producto_catalogo:
            producto_catalogo.delete()
            print(f"🗑️ Producto eliminado del catálogo: {instance.nombre}")
        
        # Limpiar caché para forzar actualización en interfaz
        cache.delete('productos_lista')
        cache.delete('categorias_lista')
        cache.set('producto_actualizado', True, timeout=60)
        
        logger.info(f"Producto eliminado desde admin: {instance.nombre} (ID: {instance.id})")
        print(f"🔄 Producto eliminado desde admin: {instance.nombre} - Interfaz actualizada")
        
    except Exception as e:
        logger.error(f"Error en signal de producto eliminado: {e}")
        print(f"❌ Error en signal de eliminación: {e}")


# Signal para sincronizar desde catálogo hacia inventario
@receiver(post_save, sender=None)
def sincronizar_desde_catalogo(sender, instance, created, **kwargs):
    """Sincroniza productos desde catálogo hacia inventario"""
    try:
        # Solo procesar si es un producto del catálogo
        if sender.__name__ == 'Product' and hasattr(instance, 'nombre'):
            from .models import Producto
            
            # Buscar si el producto ya existe en inventario
            inv_producto = Producto.objects.filter(nombre=instance.nombre).first()
            
            if not inv_producto and created:
                # Crear el producto en inventario
                from proveedores.models import Proveedor
                proveedor = Proveedor.objects.first()
                
                inv_producto = Producto.objects.create(
                    nombre=instance.nombre,
                    codigo=instance.codigo,
                    codigo_barras=instance.codigo_barras,
                    categoria=instance.categoria,
                    precio_costo=instance.precio_costo,
                    precio_venta=instance.precio_venta,
                    stock=int(instance.stock),
                    stock_minimo=int(instance.stock_minimo),
                    descripcion=instance.descripcion,
                    imagen=instance.imagen,
                    activo=instance.activo,
                    proveedor=proveedor,
                )
                print(f"🔄 Producto sincronizado desde catálogo: {instance.nombre} -> Inventario (ID: {inv_producto.id})")
                
                # Limpiar caché para forzar actualización en interfaz
                cache.delete('productos_lista')
                cache.delete('categorias_lista')
                cache.set('producto_actualizado', True, timeout=60)
                
    except Exception as e:
        # Silenciar errores para evitar problemas con otros signals
        pass
